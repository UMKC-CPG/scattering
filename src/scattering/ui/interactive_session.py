"""The session loop (pseudocode 12.6, design 12.3): advance, build
the frame, draw once, pump events, apply commands. No physics runs here --
building a frame is array slicing on the frozen store -- so the frame rate may
float freely and the ratio of scene time to wall time is reported rather than
corrected.

Attribution: this module is part of the scattering teaching tool.
"""

import sys
import time
from dataclasses import replace
from pathlib import Path

from scattering.analysis import build_error_budget
from scattering.detector import build_detector_result

from scattering.render.palettes import BACKGROUNDS, PALETTES
from scattering.render.panel_windows import PanelWindows
from scattering.render.panels import build_panel
from scattering.render.scene_description import (Scene, build_frame,
    build_static, glyph_radius, ring_legend_lines)
from scattering.run.serialization import write_back
from scattering.ui.controls import apply, control_legend_lines
from scattering.ui.session_state import SessionState


class Session:
    """What the loop owns (pseudocode 12.2)."""

    def __init__(self, resolved, store, state, renderer, controls, rc):
        self.resolved = resolved
        self.store = store
        self.state = state
        self.renderer = renderer
        self.controls = controls
        self.rc = rc
        self.static_cache = {}
        self.detector_cache = {}
        self.running = True
        self.frames_drawn = 0

    def save(self):
        """Write the resolved run file with the current view
        (pseudocode 12.4 'save')."""
        from dataclasses import replace
        from scattering.run.run_spec import ViewSpec
        view = ViewSpec(palette=self.state.palette,
            camera=dict(self.state.camera), tracked_particle=self.state.tracked,
            panels=tuple(self.state.panels))
        resolved = replace(self.resolved,
                           spec=replace(self.resolved.spec, view=view))
        source = self.resolved.spec.meta.source \
            if self.resolved.spec.meta else None
        stem = Path(source).stem if source else 'run'
        path = Path(self.rc.output_dir) / f'{stem}.resolved.toml'
        # A save that cannot be written must not end the session: the
        # tool is routinely run from a shared, read-only installation
        # (pseudocode 12.4). Say where, say the remedy, and carry on.
        try:
            write_back(resolved, path)
        except OSError as problem:
            print(f'save: cannot write {path} ({problem.strerror}). Run '
                  'from a directory you can write, or set output_dir in '
                  'a scsimrc.py there.', file=sys.stderr)
            return None
        print(f'save: wrote {path}', file=sys.stderr)
        return path


def initial_state(resolved):
    """The run file's [view], and playing from the start (design 12.4:
    a student who opens the tool sees the beam in flight)."""
    view = resolved.spec.view
    return SessionState(tracked=view.tracked_particle, palette=view.palette,
                        camera=dict(view.camera), panels=tuple(view.panels),
                        playing=True)


class _SliderView:
    """What the renderer's sliders need to know of the state and the
    store, without the renderer importing either (pseudocode 11.6)."""

    def __init__(self, state, store):
        self.frame_index = state.frame_index
        self.energy_index = state.energy_index
        self.n_samples = store.n_samples
        self.n_energies = store.n_energies


def run_session(resolved, store, controls, renderer, rc, state=None):
    """Run the loop until quit, window close, or the controls source
    reports itself done. Returns the final state."""
    state = state or initial_state(resolved)
    session = Session(resolved, store, state, renderer, controls, rc)
    glyph = glyph_radius(resolved, rc)
    # The 2D panels are matplotlib windows of their own (design 11.10);
    # the renderer draws the key legend and takes slider commands.
    panels = PanelWindows(state.panels, PALETTES[state.palette],
                          BACKGROUNDS[state.palette],
                          offscreen=getattr(renderer, 'offscreen', True))
    if hasattr(renderer, 'set_legend'):
        renderer.set_legend(control_legend_lines())
    if hasattr(renderer, 'command_sink') and hasattr(controls, 'push'):
        renderer.command_sink = controls.push
    wall_start = time.time()
    scene_advanced = 0.0
    from scattering.ui.session_state import advance
    while session.running and not controls.window_closed():
        state = session.state
        k = state.energy_index
        previous = state.frame_index
        state = advance(state, store.n_samples)
        scene_advanced += abs(store.time_of(k, state.frame_index)
                              - store.time_of(k, previous))
        session.state = state
        static_key = (k, state.palette, state.tracked,
                      state.detector_layout, state.detector_mode,
                      state.hidden_rings, state.graticule_lines)
        detector_key = (k, state.detector_layout, state.detector_mode)
        if detector_key not in session.detector_cache:
            spec = replace(resolved.spec.detector, mode=state.detector_mode,
                layout=state.detector_layout)
            session.detector_cache[detector_key] = build_detector_result(
                store, resolved, k, spec)
        detector = session.detector_cache[detector_key]
        if static_key not in session.static_cache:
            session.static_cache[static_key] = build_static(store, resolved, k,
                state.tracked, glyph, detector, state.hidden_rings)
        budget = build_error_budget(store, resolved, k, state.tracked,
                                    detector)
        dynamic, telemetry = build_frame(store, resolved, k, state.frame_index,
            state.tracked, glyph, resolved.scales, state.hidden_rings)
        ring_lines = ring_legend_lines(store, resolved, k, state.hidden_rings)
        elapsed = max(1e-9, time.time() - wall_start)
        telemetry = telemetry.__class__(**{
            **telemetry.__dict__,
            'ratio_of_scene_to_wall_time': scene_advanced / elapsed})
        scene = Scene(session.static_cache[static_key], dynamic, telemetry)
        renderer.render(scene, state.camera, static_key, resolved=resolved,
                        state=_SliderView(state, store),
                        ring_lines=ring_lines)
        # The panels redraw only when what they show has changed.
        panel_key = (k, state.tracked, state.show_mirror,
                     state.detector_layout, state.detector_mode,
                     state.palette)
        if panels.palette is not PALETTES[state.palette]:
            panels.set_palette(PALETTES[state.palette],
                               BACKGROUNDS[state.palette])
        for name in state.panels:
            panels.update(name, build_panel(name, store, resolved, k,
                state.tracked, state.show_mirror, detector, budget),
                panel_key)
        session.frames_drawn += 1
        controls.pump()
        panels.pump()
        for command in controls.read():
            session = apply(command, session)
    panels.close()
    return session.state
