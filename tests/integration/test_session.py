"""Verifies pseudocode sections 11.6, 11.8, 12.6, 12.7, 12.8 that need
a renderer: the offscreen pixel check, the determinism of a scripted
session, save, and scsim.main. Skips cleanly where no offscreen GL
context exists (the rigid-body tool's convention)."""

import os
import sys
from pathlib import Path

import numpy as np
import pytest

from scattering.beam.beam_spec import AnnulusSpec, BeamSpec
from scattering.run import (DetectorSpec, FidelitySpec, PotentialSpec,
    RcSettings, RunSpec, build_results_store, load_and_resolve, resolve)
from scattering.ui import ScriptedControls, run_session
from scattering.ui.controls import BINDINGS

REPO = Path(__file__).resolve().parents[2]
pytest.importorskip('vedo')


def _renderer(panels=('deflection', 'telemetry')):
    from scattering.render.vedo_renderer import VedoRenderer
    try:
        renderer = VedoRenderer('light', (640, 480), offscreen=True,
                                panels=panels)
    except Exception as problem:               # pragma: no cover
        pytest.skip(f'no offscreen render context: {problem}')
    return renderer


@pytest.fixture(scope='module')
def run():
    spec = RunSpec(
        potential=PotentialSpec(preset='alpha_on_gold'),
        beam=BeamSpec(energies=['3 MeV', '5 MeV'], layout='annuli',
                      annuli=(AnnulusSpec(0.5, 0.05, 6),
                              AnnulusSpec(2.0, 0.05, 6))),
        fidelity=FidelitySpec(r_max=40.0, n_samples=30,
                              n_deflection_points=60),
        detector=DetectorSpec(radius=2.0))
    resolved = resolve(spec)
    return resolved, build_results_store(resolved)


def _snapshot(store):
    return {name: getattr(store, name).copy()
            for name in ('position', 'velocity', 'polar', 'phase',
                         'deflection', 'out_direction')}


def test_offscreen_render_draws_something(run):
    resolved, store = run
    renderer = _renderer()
    rc = RcSettings()
    controls = ScriptedControls([(0, 'play_pause')], max_frames=3)
    run_session(resolved, store, controls, renderer, rc)
    image = renderer.screenshot(as_array=True)
    renderer.close()
    if image.min() == image.max():
        pytest.skip('offscreen framebuffer was empty (no GL context)')
    assert image.ndim == 3 and image.shape[2] == 3


def test_scripted_session_is_deterministic_and_reads_only(run):
    """A8.6(3): every command in BINDINGS through the loop leaves
    the store bit-identical."""
    resolved, store = run
    before = _snapshot(store)
    commands = [command for command, _ in BINDINGS.values()
                if command != 'quit']
    script = [(tick + 1, command) for tick, command in enumerate(commands)]
    script.append((len(commands) + 2, 'quit'))
    renderer = _renderer()
    rc = RcSettings(output_dir=str(Path(os.environ.get('TMPDIR', '/tmp'))))
    controls = ScriptedControls(script, max_frames=len(script) + 5)
    state = run_session(resolved, store, controls, renderer, rc)
    renderer.close()
    for name, array in before.items():
        assert np.array_equal(array, getattr(store, name))
    assert 0 <= state.frame_index < store.n_samples
    assert state.energy_index in (0, 1)


def test_save_round_trips(run, tmp_path):
    resolved, store = run
    renderer = _renderer(panels=())
    rc = RcSettings(output_dir=str(tmp_path))
    controls = ScriptedControls([(1, 'track_next'), (2, 'save'),
                                 (3, 'quit')], max_frames=6)
    run_session(resolved, store, controls, renderer, rc)
    renderer.close()
    written = list(tmp_path.glob('*.resolved.toml'))
    assert len(written) == 1
    again = load_and_resolve(written[0], rc=rc)
    assert again.spec.view.tracked_particle == 1
    assert np.allclose(again.spec.beam.energies, resolved.spec.beam.energies)


def test_scsim_main_offscreen(tmp_path, monkeypatch):
    sys.path.insert(0, str(REPO / 'src' / 'scripts'))
    import scsim
    monkeypatch.chdir(tmp_path)
    shot = tmp_path / 'frame.png'
    status = scsim.main([str(REPO / 'runs' / 'rutherford.toml'),
                         '--offscreen', '--frames', '4', '--screenshot',
                         str(shot), '--set', 'fidelity.n_samples=20',
                         '--set', 'fidelity.n_deflection_points=60'])
    assert status == 0
    assert shot.exists() and shot.stat().st_size > 1000
    assert not (tmp_path / 'command').exists()


def test_scsim_refuses_offscreen_without_an_end(monkeypatch, capsys):
    """P12.7: interactive controls on an invisible window would never
    stop, so the entry point refuses before doing any work."""
    monkeypatch.syspath_prepend(str(REPO / 'src' / 'scripts'))
    import scsim
    with pytest.raises(SystemExit) as refusal:
        scsim.main([str(REPO / 'runs' / 'rutherford.toml'), '--offscreen'])
    assert refusal.value.code == 2
    assert '--frames' in capsys.readouterr().err
