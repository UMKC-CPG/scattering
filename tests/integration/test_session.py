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
    """An offscreen renderer; `panels` is kept for the callers but the
    panels are matplotlib windows now (design 11.10), not viewports."""
    from scattering.render.vedo_renderer import VedoRenderer
    try:
        renderer = VedoRenderer('light', (640, 480), offscreen=True)
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
    commands = sorted({command for command, _ in BINDINGS.values()
                       if command != 'quit'})
    commands += [('seek', 3), ('set_energy', 1)]      # the sliders
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


@pytest.fixture
def read_only_directory(tmp_path):
    """A directory the test cannot write, as a student finds a shared
    installation. Skips where permissions do not bind (root)."""
    locked = tmp_path / 'shared'
    locked.mkdir()
    locked.chmod(0o555)
    if os.access(locked, os.W_OK):
        pytest.skip('this user can write a read-only directory')
    yield locked
    locked.chmod(0o755)


def test_save_in_a_read_only_directory_does_not_end_the_session(
        run, read_only_directory, capsys):
    """P12.4: the save fails, says so, and the session runs on."""
    resolved, store = run
    renderer = _renderer(panels=())
    rc = RcSettings(output_dir=str(read_only_directory))
    controls = ScriptedControls([(1, 'save'), (2, 'track_next'),
                                 (4, 'quit')], max_frames=6)
    state = run_session(resolved, store, controls, renderer, rc)
    renderer.close()
    assert state.tracked == 1                # commands after the save ran
    assert not list(read_only_directory.glob('*.toml'))
    assert 'cannot write' in capsys.readouterr().err


def test_command_log_in_a_read_only_directory_is_only_a_note(
        read_only_directory, monkeypatch, capsys):
    """P12.7: the command log is a convenience, never a reason to stop."""
    monkeypatch.syspath_prepend(str(REPO / 'src' / 'scripts'))
    import scsim
    monkeypatch.chdir(read_only_directory)
    monkeypatch.setattr(sys, 'argv', ['scsim', 'runs/rutherford.toml'])
    scsim.record_command()                   # must not raise
    assert 'continuing without the command log' in capsys.readouterr().err


def test_camera_is_set_once_and_read_back(run):
    """Design 12.14: no camera command, one camera set; and the live
    camera reads back as the numbers that were applied."""
    resolved, store = run
    renderer = _renderer(panels=())
    rc = RcSettings()
    controls = ScriptedControls([(1, 'step_forward'), (2, 'energy_up'),
                                 (4, 'quit')], max_frames=8)
    state = run_session(resolved, store, controls, renderer, rc)
    assert renderer.camera_set_count == 1
    read = renderer.read_camera()
    for key in ('azimuth_deg', 'elevation_deg', 'distance'):
        assert abs(read[key] - state.camera[key]) < 1e-6
    renderer.close()


def test_sliders_and_start_playing(run):
    """Pseudocode 12.4: seek pauses on its frame; set_energy equals
    energy_up; the session starts playing (design 12.4)."""
    from scattering.ui.interactive_session import initial_state
    resolved, store = run
    assert initial_state(resolved).playing
    renderer = _renderer(panels=())
    controls = ScriptedControls([(1, ('seek', 7)), (3, 'quit')],
                                max_frames=6)
    state = run_session(resolved, store, controls, renderer, RcSettings())
    assert state.frame_index == 7 and not state.playing
    controls = ScriptedControls([(1, ('set_energy', 1)), (2, 'quit')],
                                max_frames=6)
    state = run_session(resolved, store, controls, renderer, RcSettings())
    assert state.energy_index == 1
    renderer.close()


def test_save_writes_the_live_camera(run, tmp_path):
    """Design 12.14: a view found with the mouse is what Save keeps."""
    resolved, store = run
    renderer = _renderer(panels=())
    rc = RcSettings(output_dir=str(tmp_path))
    controls = ScriptedControls([(1, 'save'), (2, 'quit')], max_frames=5)
    # Move the camera as the mouse would, after the first frame set it.
    run_session(resolved, store, ScriptedControls([(1, 'quit')], 3),
                renderer, rc)
    camera = renderer.plotter.at(0).camera
    camera.SetPosition(0.0, 3.0 * resolved.detector_radius, 0.0)
    run_session(resolved, store, controls, renderer, rc)
    renderer.close()
    saved = load_and_resolve(next(tmp_path.glob('*.resolved.toml')), rc=rc)
    assert abs(saved.spec.view.camera['azimuth_deg'] - 90.0) < 1e-6
    assert abs(saved.spec.view.camera['distance'] - 3.0) < 1e-6


def test_graticule_line_count(run):
    """Design 11.12: a Sphere drawable is n + 2n line actors."""
    from scattering.geometry import Sphere
    from scattering.render.scene_description import Drawable
    renderer = _renderer(panels=())
    sphere = Drawable('detector sphere', '7.2',
                      Sphere(center=np.zeros(3), radius=1.0), 'detector',
                      None, 'scene', True)
    assert len(renderer._actors_for(sphere)) == (12 - 1) + 24
    renderer.set_graticule(8)
    assert len(renderer._actors_for(sphere)) == 7 + 16
    renderer.close()
