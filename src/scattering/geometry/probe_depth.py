"""The probe-depth sphere (pseudocode 11.3, design 11.4): the radius
inside which no orbit at this energy goes. For a potential that admits a head-on
orbit it is the head-on turning point -- for repulsive Coulomb, 1 / E, the
classical distance of closest approach -- and it shrinks as the energy slider
rises, which is VISION G5 seen in the scene before the inversion panel draws it
as a limit. For a potential with no head-on orbit the marker sits at the turning
point of the smallest impact parameter actually thrown.

Attribution: this module is part of the scattering teaching tool.
"""

import numpy as np

from scattering.geometry.shapes import Points, Sphere
from scattering.orbits.turning_point import turning_point_from_g


def probe_depth(potential, energy, smallest_impact, glyph_radius=0.05):
    """Return (geometry, label) for the probe-depth drawable."""
    if potential.admits_center():
        r_min, _ = turning_point_from_g(potential, energy, 0.0)
        return Sphere(np.zeros(3), float(r_min)), 'no orbit enters'
    r_min, _ = turning_point_from_g(potential, energy, smallest_impact)
    # The marker is placed on the beam axis at the reach radius; the tracked
    # orbit's own turning-point marker shows where its pericenter is.
    return (Points(np.array([[0.0, 0.0, -float(r_min)]]), glyph_radius),
            'smallest impact parameter thrown')
