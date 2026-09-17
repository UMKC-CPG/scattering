"""Verifies pseudocode 12.10 and the entry point of 12.7: the packaged
examples, the rc copy, the self-check, and errors that are messages.
Everything here must hold in a clone, in a linked suite, and in an
installed copy, so nothing here looks for a file except through the
package."""

import os
import sys
from pathlib import Path

import pytest

from scattering.cli import examples
from scattering.cli import scsim as cli
from scattering.run import load_and_resolve, load_rc
from scattering.run.rc import PACKAGE_DEFAULTS_DIR

REPO = Path(__file__).resolve().parents[2]


def test_packaged_examples_resolve_and_match_runs():
    packaged = examples.example_files()
    assert 'rutherford' in packaged
    for path in packaged.values():
        load_and_resolve(path)                   # raises if one is broken
    # `runs` is a link to the package directory: one set of files.
    assert {p.name for p in (REPO / 'runs').glob('*.toml')} == \
        {p.name for p in packaged.values()}


def test_locate_run_file(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    packaged = examples.example_files()['rutherford']
    assert examples.locate_run_file(str(packaged)) == packaged
    assert examples.locate_run_file('rutherford') == packaged
    assert examples.locate_run_file('rutherford.toml') == packaged
    assert 'using the packaged example' in capsys.readouterr().err
    # A real file in the working directory always wins.
    (tmp_path / 'rutherford.toml').write_text('schema = 1\n')
    assert examples.locate_run_file('rutherford.toml') == \
        Path('rutherford.toml')
    # A directory part, or an unknown name, is never rescued.
    for wrong in ('sub/rutherford', 'no_such_example'):
        with pytest.raises(FileNotFoundError, match='rutherford_disc'):
            examples.locate_run_file(wrong)


def test_copy_examples_never_overwrites(tmp_path, capsys):
    target = tmp_path / 'my runs'
    assert examples.copy_examples(target) == 0
    written = sorted(p.name for p in target.iterdir())
    assert written == sorted(p.name
                             for p in examples.example_files().values())
    edited = target / 'rutherford.toml'
    edited.write_text('# my edit\n')
    capsys.readouterr()
    assert examples.copy_examples(target) == 0
    assert edited.read_text() == '# my edit\n'
    assert capsys.readouterr().out.count('kept') == len(written)


def test_copy_into_a_read_only_directory_is_a_message(tmp_path, capsys):
    locked = tmp_path / 'shared'
    locked.mkdir()
    locked.chmod(0o555)
    if os.access(locked, os.W_OK):
        pytest.skip('this user can write a read-only directory')
    try:
        assert examples.copy_examples(locked) == 1
    finally:
        locked.chmod(0o755)
    assert 'Choose a directory you can write' in capsys.readouterr().err


def test_written_rc_file_loads_and_equals_the_defaults(tmp_path):
    assert examples.copy_rc_file(tmp_path) == 0
    assert load_rc([tmp_path]) == load_rc([PACKAGE_DEFAULTS_DIR])


def test_missing_run_file_is_status_2_not_a_traceback(tmp_path,
                                                      monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(['no_such.toml']) == 2
    assert 'Packaged examples' in capsys.readouterr().err


def test_invalid_run_file_is_status_2(tmp_path, capsys):
    broken = tmp_path / 'broken.toml'
    broken.write_text('schema = 1\n[potential]\nkind = "no_such_kind"\n')
    assert cli.main([str(broken)]) == 2
    assert 'scsim:' in capsys.readouterr().err


@pytest.mark.parametrize('arguments', [[], ['x.toml', '--examples'],
                                       ['--check', '--write-rc']])
def test_exactly_one_thing_to_do(arguments):
    with pytest.raises(SystemExit) as refusal:
        cli.main(arguments)
    assert refusal.value.code == 2


@pytest.mark.parametrize('flag', ['--examples', '--write-rc', '--check',
                                  '--help'])
def test_utility_invocations_are_not_logged(tmp_path, monkeypatch, flag):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, 'argv', ['scsim', flag])
    cli.record_command()
    assert not (tmp_path / 'command').exists()


def test_self_check_passes_and_writes_nothing(tmp_path, monkeypatch,
                                              capsys):
    monkeypatch.chdir(tmp_path)
    status = cli.main(['--check'])
    output = capsys.readouterr().out
    if 'the picture is blank' in output:
        pytest.skip('no offscreen GL context on this computer')
    assert status == 0 and 'RESULT: PASS' in output
    assert list(tmp_path.iterdir()) == []
