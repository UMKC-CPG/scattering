"""Verifies pseudocode section 12.3 and 12.4 (P12.8), the pure part:
state transitions and the bindings table."""

import numpy as np
import pytest

from scattering.ui.controls import BINDINGS, COMMANDS, control_legend_lines
from scattering.ui.session_state import (SessionState, advance, cycle_tracked,
    jump, set_energy, set_rate, step)


def playing(**overrides):
    return SessionState(playing=True, **overrides)


def test_advance_stops_at_ends_without_loop():
    state = playing(frame_index=98, rate=4)
    state = advance(state, 100)
    assert state.frame_index == 99 and not state.playing
    state = playing(frame_index=1, rate=4, direction=-1)
    state = advance(state, 100)
    assert state.frame_index == 0 and not state.playing


def test_advance_wraps_with_loop():
    state = playing(frame_index=98, rate=4, loop=True)
    assert advance(state, 100).frame_index == 2
    state = playing(frame_index=1, rate=4, direction=-1, loop=True)
    assert advance(state, 100).frame_index == 97


def test_advance_paused_is_identity():
    state = SessionState(frame_index=5)
    assert advance(state, 100) is state


def test_step_pauses_and_clamps():
    state = step(playing(frame_index=0), 100, -1)
    assert state.frame_index == 0 and not state.playing
    assert step(state, 100, +3).frame_index == 3


def test_jump_clamps():
    assert jump(SessionState(), 100, 500).frame_index == 99
    assert jump(SessionState(), 100, -5).frame_index == 0


def test_set_rate_bounds():
    state = SessionState(rate=1)
    for _ in range(10):
        state = set_rate(state, 2.0)
    assert state.rate == 16
    for _ in range(10):
        state = set_rate(state, 0.5)
    assert state.rate == 1


def test_set_energy_preserves_fraction():
    state = SessionState(frame_index=50)
    moved = set_energy(state, 2, 101)
    assert moved.energy_index == 2 and moved.frame_index == 50
    state = SessionState(frame_index=99)
    assert set_energy(state, 1, 100).frame_index == 99


class FakeStore:
    def __init__(self, layout, impacts):
        self.n_particles = len(impacts)
        self.impact_parameter = np.array(impacts)

        class Beam:
            pass
        self.beam = Beam()
        self.beam.layout = layout


def test_cycle_tracked_visits_every_particle_once():
    for layout, impacts in (('annuli', [1, 1, 1, 3, 3, 3]),
                            ('disc', [0.7, 0.1, 5.0, 2.2, 0.3])):
        store = FakeStore(layout, impacts)
        state = SessionState(tracked=0)
        seen = []
        for _ in range(store.n_particles):
            seen.append(state.tracked)
            state = cycle_tracked(state, store, +1)
        assert sorted(seen) == list(range(store.n_particles))
        assert state.tracked == 0
        if layout == 'disc':
            # The visiting order is the sorted order of b, rotated to start at
            # the tracked particle (design 12.6).
            order = list(np.argsort(impacts, kind='stable'))
            start = order.index(0)
            assert seen == order[start:] + order[:start]


def test_bindings_table_is_consistent():
    """Design 12.15: every key is a Ctrl chord (bar VTK's own q and
    Escape), aliases are not listed in the legend, and the legend names
    every distinct command once."""
    assert 'quit' in COMMANDS and 'play_pause' in COMMANDS
    for key in BINDINGS:
        assert key.startswith('Ctrl+') or key in ('q', 'Escape'), key
    lines = control_legend_lines()
    with_help = [key for key, (_, help_text) in BINDINGS.items()
                 if help_text is not None]
    assert len(lines) == len(with_help)
    assert any('play / pause' in line for line in lines)
    assert any('Ctrl+[' in line for line in lines)
    assert any('Ctrl+Shift+s' in line for line in lines)
    commands_with_help = {BINDINGS[key][0] for key in with_help}
    assert commands_with_help == COMMANDS - {
        f'ring_{i}' for i in range(2, 10)}


def test_ring_toggles_and_graticule():
    """Pseudocode 12.3: toggle_ring, toggle_all_rings, set_graticule."""
    from scattering.ui.session_state import (GRATICULE_MAX, GRATICULE_MIN,
        set_graticule, toggle_all_rings, toggle_ring)
    state = SessionState()
    assert toggle_ring(toggle_ring(state, 2, 5), 2, 5) == state
    assert toggle_ring(state, 7, 5) == state           # no such ring
    hidden = toggle_all_rings(state, 5)
    assert hidden.hidden_rings == frozenset(range(5))
    assert toggle_all_rings(hidden, 5).hidden_rings == frozenset()
    assert toggle_all_rings(toggle_ring(state, 1, 5), 5).hidden_rings == \
        frozenset()                                    # any hidden -> all
    low = set_graticule(state, -100)
    assert low.graticule_lines == GRATICULE_MIN
    assert set_graticule(low, +1000).graticule_lines == GRATICULE_MAX
