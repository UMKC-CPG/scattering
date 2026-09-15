"""The session loop (pseudocode 12.6, design 12.3): advance, build
the frame, draw once, pump events, apply commands. No physics runs here --
building a frame is array slicing on the frozen store -- so the frame rate may
float freely and the ratio of scene time to wall time is reported rather than
corrected.

Attribution: this module is part of the scattering teaching tool.
"""

import time
from pathlib import Path

from scattering.render.scene_description import (Scene, build_frame,
                                                  build_static)
from scattering.run.serialization import write_back
from scattering.ui.controls import apply
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
        write_back(resolved, path)
        return path


def initial_state(resolved):
    view = resolved.spec.view
    return SessionState(tracked=view.tracked_particle, palette=view.palette,
                        camera=dict(view.camera), panels=tuple(view.panels))


def run_session(resolved, store, controls, renderer, rc, state=None):
    """Run the loop until quit, window close, or the controls source
    reports itself done. Returns the final state."""
    state = state or initial_state(resolved)
    session = Session(resolved, store, state, renderer, controls, rc)
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
        static_key = (k, state.palette, state.tracked)
        if static_key not in session.static_cache:
            session.static_cache[static_key] = build_static(
                store, resolved, k, state.tracked, rc.glyph_radius)
        dynamic, telemetry = build_frame(store, resolved, k, state.frame_index,
            state.tracked, rc.glyph_radius, resolved.scales)
        elapsed = max(1e-9, time.time() - wall_start)
        telemetry = telemetry.__class__(**{
            **telemetry.__dict__,
            'ratio_of_scene_to_wall_time': scene_advanced / elapsed})
        scene = Scene(session.static_cache[static_key], dynamic, telemetry)
        renderer.render(scene, state.camera, static_key, store=store,
            resolved=resolved, tracked=state.tracked,
            show_mirror=state.show_mirror)
        session.frames_drawn += 1
        controls.pump()
        for command in controls.read():
            session = apply(command, session)
    return session.state
