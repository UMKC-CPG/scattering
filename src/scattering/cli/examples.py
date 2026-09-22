"""Getting to a first run: the packaged examples, the rc copy, and the
self-check (pseudocode 12.10; design 12.13).

A student who installed the tool with `pip`, or who is using a shared
installation that someone else made and that they cannot write to, has
no idea where the example run files or the rc file are, and should not
need to. Everything in this module therefore finds its files THROUGH
THE PACKAGE, never relative to a script or to the working directory.
That one rule is what makes a clone, a linked `physdemo` suite, and an
installed copy behave identically (ARCHITECTURE 9.1).

Nothing here touches the physics. These are ways of getting to a run.

Attribution: this module is part of the scattering teaching tool.
"""

import platform
import shutil
import sys
import time
from importlib import metadata, resources
from pathlib import Path

from scattering.run.rc import PACKAGE_DEFAULTS_DIR, RC_FILENAME

# The packages `scsim --check` reports on: the ones this tool imports,
# by the names `pip` knows them by. pyproject.toml declares the same
# set, and a test keeps the two in agreement.
CHECKED_DISTRIBUTIONS = ('numpy', 'scipy', 'matplotlib', 'vedo', 'vtk',
                         'pint', 'tomli_w')


def example_files():
    """Every packaged example run file, as a dictionary from its bare
    name (`rutherford`) to its path, in name order."""
    directory = Path(str(resources.files('scattering.examples')))
    return {path.stem: path for path in sorted(directory.glob('*.toml'))}


def locate_run_file(argument):
    """Turn the command line's run-file argument into a path.

    A file that exists is returned as it is; a real file always wins.
    Otherwise a BARE name (no directory part) that matches a packaged
    example, with or without `.toml`, selects that example, and one
    line on standard error says so. The rule is deliberately narrow:
    `scsim results/rutherford.toml` with a mistyped directory must fail
    rather than quietly run something else.

    Raises FileNotFoundError with a message a student can act on.
    """
    if Path(argument).exists():
        return Path(argument)
    examples = example_files()
    if Path(argument).name == argument:
        stem = argument[:-len('.toml')] if argument.endswith('.toml') \
            else argument
        if stem in examples:
            print(f'using the packaged example {examples[stem]}',
                  file=sys.stderr)
            return examples[stem]
    names = ', '.join(examples) or '(none found)'
    raise FileNotFoundError(
        f'{argument}: no such run file. Packaged examples: {names}. Run '
        f'one by name (scsim {next(iter(examples), "NAME")}), or copy '
        'them here to edit with: scsim --examples')


def copy_without_overwriting(sources, directory):
    """Copy each source file into `directory`, never replacing a file
    that is already there, and say what happened to each. Returns an
    exit status: 0, or 1 if the directory cannot be written.

    Not overwriting is the point: a student's edited copy is worth more
    than a fresh one, and a second `scsim --examples` must be harmless.
    """
    directory = Path(directory)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        for source in sources:
            target = directory / Path(source).name
            if target.exists():
                print(f'kept   {target} (already here)')
            else:
                shutil.copyfile(source, target)
                print(f'wrote  {target}')
    except OSError as problem:
        print(f'cannot write in {directory} ({problem.strerror}). Choose '
              'a directory you can write, for example:\n'
              '    scsim --examples ~/scattering-runs', file=sys.stderr)
        return 1
    return 0


def copy_examples(directory):
    """`scsim --examples [DIR]`: the packaged run files, to edit."""
    return copy_without_overwriting(example_files().values(), directory)


def copy_rc_file(directory):
    """`scsim --write-rc`: the shipped rc defaults, to edit. A
    `scsimrc.py` in the working directory is the first place the tool
    looks (design 10.7), so the copy takes effect where it lands."""
    return copy_without_overwriting([PACKAGE_DEFAULTS_DIR / RC_FILENAME],
                                    directory)


def installed_versions():
    """The version of each checked distribution, or None if missing."""
    versions = {}
    for name in CHECKED_DISTRIBUTIONS:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def self_check():
    """`scsim --check`: can this computer run the tool and draw it?

    Reports the versions in use, builds a deliberately small run from
    the packaged `rutherford` example THROUGH THE ORDINARY CODE PATH
    (loading, resolving, building), draws two frames offscreen, and
    reads the picture back. The read-back matters: a window without a
    working OpenGL context accepts every draw call and draws nothing,
    so "it did not crash" proves nothing about the picture.

    Writes no file. Returns 0 and prints `RESULT: PASS`, or returns 1
    and prints `RESULT: FAIL -- <reason>`. Every exception is caught on
    purpose: this function's one job is to turn whatever goes wrong on
    an unfamiliar computer into a line a student can send on.
    """
    print(f'python      {platform.python_version()}  ({sys.executable})')
    print(f'platform    {platform.system()} {platform.release()} '
          f'{platform.machine()}')
    versions = installed_versions()
    for name, version in versions.items():
        print(f'{name:<11} {version or "MISSING"}')
    missing = [name for name, version in versions.items() if not version]
    if missing:
        print(f'RESULT: FAIL -- not installed: {", ".join(missing)}')
        return 1

    try:
        # Imported here, not at the top: the copiers above must work
        # even on a computer where the numerical stack is broken.
        from scattering.render.offscreen import prepare_offscreen
        from scattering.run import (build_results_store,
                                    load_and_resolve, load_rc)

        started = time.perf_counter()
        rc = load_rc()
        resolved = load_and_resolve(
            example_files()['rutherford'],
            ['fidelity.n_samples=40', 'fidelity.n_deflection_points=60'],
            rc)
        store = build_results_store(resolved)
        print(f'built       {store.n_energies} energies x '
              f'{store.n_particles} particles in '
              f'{time.perf_counter() - started:.1f} s')

        prepare_offscreen()                       # before VTK is imported
        from scattering.render.vedo_renderer import VedoRenderer
        from scattering.ui import ScriptedControls, run_session

        started = time.perf_counter()
        renderer = VedoRenderer(resolved.spec.view.palette, (640, 480),
                                offscreen=True)
        run_session(resolved, store, ScriptedControls([], 2), renderer, rc)
        image = renderer.screenshot(as_array=True)
        renderer.close()
        print(f'drew        2 frames offscreen in '
              f'{time.perf_counter() - started:.1f} s')
    except Exception as problem:                  # noqa: BLE001 (see above)
        print(f'RESULT: FAIL -- {type(problem).__name__}: {problem}')
        return 1

    if image.min() == image.max():
        print('RESULT: FAIL -- the picture is blank: no working OpenGL '
              'context for offscreen drawing on this computer')
        return 1
    print('RESULT: PASS')
    return 0
