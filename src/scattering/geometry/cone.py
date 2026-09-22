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


def bin_bands(layout, r_detect, half_width_deg=0.12, azimuth=np.pi / 2,
              half_span_deg=4.0):
    """A tick mark at every bin edge of a detector layout, so the
    histogram's bins are visible on the sphere (pseudocode 7.7): a
    short band, `2 * half_span_deg` of azimuth wide, centred on one
    meridian. Ticks along a meridian, not bands round the sphere, so
    that forty-one bin edges do not read as lines of latitude beside
    the graticule (design 11.12)."""
    half_width = np.radians(half_width_deg)
    half_span = np.radians(half_span_deg)
    span = (azimuth - half_span, azimuth + half_span)
    bands = []
    for edge in layout.edges:
        low = max(0.0, edge - half_width)
        high = min(np.pi, edge + half_width)
        bands.append(SphereBand(_ORIGIN, float(r_detect), float(low),
                                float(high), span))
    return bands


def beam_axis(r_detect):
    return Segment(start=np.array([0.0, 0.0, -r_detect]),
                   end=np.array([0.0, 0.0, r_detect]))


def entry_plane(r_max, half_extent):
    """The tangent plane z = -R_max on which the beam is a pulse at
    t = 0 (design 4.6)."""
    return Plane(center=np.array([0.0, 0.0, -r_max]), normal=_Z_AXIS,
                 half_extent=float(half_extent))
