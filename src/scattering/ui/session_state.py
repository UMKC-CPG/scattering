"""The viewing state and its pure transitions (pseudocode 12.2-12.3,
design 12.2-12.6).

Every function here takes a SessionState and returns a new one; none touches the
results store or the resolved run. Time controls are changes to `frame_index`;
the energy slider preserves the FRACTION of the run rather than the time,
because each energy has its own time grid (design 6.2); reverse is exact because
it reads the same stored frames backwards (VISION G4).

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import dataclass, field, replace

import numpy as np

MAX_RATE = 16


@dataclass(frozen=True)
class SessionState:
    energy_index: int = 0
    frame_index: int = 0
    rate: int = 1
    playing: bool = False
    direction: int = +1
    loop: bool = False
    tracked: int = 0
    palette: str = 'light'
    camera: dict = field(default_factory=lambda: {
        'azimuth_deg': 35.0, 'elevation_deg': 20.0, 'distance': 4.0})
    panels: tuple = ()
    detector_mode: str = 'asymptotic'
    detector_layout: str = 'log_theta'
    show_mirror: bool = False
    # Which rings (or bands of b, for a disc) are hidden; design 11.11.
    hidden_rings: frozenset = frozenset()
    # Latitude lines on the detector sphere's graticule; design 11.12.
    graticule_lines: int = 12
    legend_visible: bool = True

GRATICULE_MIN, GRATICULE_MAX = 4, 36


def _clamp(value, low, high):
    return max(low, min(high, value))


def advance(state, n_samples):
    """One tick of playback (pseudocode 12.3)."""
    if not state.playing or n_samples <= 1:
        return state
    proposed = state.frame_index + state.direction * state.rate
    if 0 <= proposed < n_samples:
        return replace(state, frame_index=proposed)
    if state.loop:
        return replace(state, frame_index=proposed % n_samples)
    return replace(state, frame_index=_clamp(proposed, 0, n_samples - 1),
                   playing=False)


def step(state, n_samples, delta):
    return replace(state, playing=False,
        frame_index=_clamp(state.frame_index + delta, 0, n_samples - 1))


def jump(state, n_samples, target):
    return replace(state, frame_index=_clamp(int(target), 0, n_samples - 1))


def set_energy(state, new_index, n_samples):
    """Preserve the fraction of the run across an energy change."""
    fraction = state.frame_index / max(1, n_samples - 1)
    return replace(state, energy_index=int(new_index),
                   frame_index=int(round(fraction * (n_samples - 1))))


def set_rate(state, factor):
    return replace(state, rate=int(_clamp(round(state.rate * factor), 1,
                                          MAX_RATE)))


def toggle_ring(state, ring, n_rings):
    """Hide ring `ring` if shown, show it if hidden (pseudocode 12.3,
    design 11.11). An index outside the beam's rings is ignored, so
    that Ctrl+7 on a three-ring beam does nothing."""
    if not 0 <= ring < n_rings:
        return state
    return replace(state, hidden_rings=state.hidden_rings ^ {ring})


def toggle_all_rings(state, n_rings):
    """Show every ring if any is hidden; otherwise hide them all (the
    tracked particle stays drawn regardless, design 11.11)."""
    if state.hidden_rings:
        return replace(state, hidden_rings=frozenset())
    return replace(state, hidden_rings=frozenset(range(n_rings)))


def set_graticule(state, delta):
    """More or fewer latitude lines, within design 11.12's bounds."""
    return replace(state, graticule_lines=_clamp(
        state.graticule_lines + delta, GRATICULE_MIN, GRATICULE_MAX))


def cycle_tracked(state, store, delta):
    """Ring-major for annuli (index order, since particles of a ring
    are contiguous); by impact parameter for a disc (design 12.6)."""
    count = store.n_particles
    if store.beam.layout == 'disc':
        order = np.argsort(store.impact_parameter, kind='stable')
        position = int(np.nonzero(order == state.tracked)[0][0])
        return replace(state, tracked=int(order[(position + delta) % count]))
    return replace(state, tracked=(state.tracked + delta) % count)
