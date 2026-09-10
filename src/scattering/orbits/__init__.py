"""How each particle moves: the orbit providers and their parts.

Governed by pseudocode section 4 and design section 4. Each particle
is integrated in its own orbital plane and placed in the scene
afterwards (`embedding.py`); the deflection angle is NOT read off
the integrated orbit (design 4.7) but computed by quadrature in the
deflection stage.
"""

from scattering.orbits.orbit_provider import (
    AnalyticProvider, NumericalProvider, Orbit, OrbitSettings,
    adaptive_trace, choose_provider, entry_plane_time, initial_state)
from scattering.orbits.embedding import embed, out_direction
from scattering.orbits.turning_point import turning_point_from_g

__all__ = ['AnalyticProvider', 'NumericalProvider', 'Orbit',
           'OrbitSettings', 'adaptive_trace', 'choose_provider',
           'entry_plane_time', 'initial_state', 'embed', 'out_direction',
           'turning_point_from_g']
