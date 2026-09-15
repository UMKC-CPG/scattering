"""The outgoing cone and the detector sphere it sits on (pseudocode
11.3, design 11.3), plus the beam axis, the entry plane, and the unmeasured caps
of design 7.3.

The cone for an annulus is the band on the detector sphere between the
asymptotic angles of its two edges, so that it agrees with where the particles
land. For an attractive potential the band is the same in polar angle but the
particles reach it on the far side of the axis (design 4.8); the label carries
that.

Attribution: this module is part of the scattering teaching tool.
"""

import numpy as np

from scattering.geometry.shapes import Plane, Segment, Sphere, SphereBand

_ORIGIN = np.zeros(3)
_Z_AXIS = np.array([0.0, 0.0, 1.0])


def cone_band(annulus_map, r_detect):
    """The band between theta(b + db) and theta(b), eq. (5.6)."""
    low = min(annulus_map.theta_1, annulus_map.theta_2)
    high = max(annulus_map.theta_1, annulus_map.theta_2)
    return SphereBand(center=_ORIGIN, radius=float(r_detect),
                      theta_1=float(low), theta_2=float(high))


def detector_sphere(r_detect):
    return Sphere(center=_ORIGIN, radius=float(r_detect))


def unmeasured_caps(theta_min, theta_head, r_detect):
    """The forward cone below theta_min and the backward cap above
    theta_head: angles the beam cannot reach (design 7.3)."""
    return (SphereBand(_ORIGIN, float(r_detect), 0.0, float(theta_min)),
            SphereBand(_ORIGIN, float(r_detect), float(theta_head), np.pi))


def beam_axis(r_detect):
    return Segment(start=np.array([0.0, 0.0, -r_detect]),
                   end=np.array([0.0, 0.0, r_detect]))


def entry_plane(r_max, half_extent):
    """The tangent plane z = -R_max on which the beam is a pulse at
    t = 0 (design 4.6)."""
    return Plane(center=np.array([0.0, 0.0, -r_max]), normal=_Z_AXIS,
                 half_extent=float(half_extent))
