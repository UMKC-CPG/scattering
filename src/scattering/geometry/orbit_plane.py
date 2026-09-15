"""The tracked particle's orbital plane (pseudocode 11.3, design
11.2): the plane through the beam axis and the particle's transverse direction
e_rho = (cos phi, sin phi, 0), whose normal is therefore (-sin phi, cos phi, 0).
Every position of that particle lies in it, which is the planar nature of
central-force motion made visible.

Attribution: this module is part of the scattering teaching tool.
"""

import numpy as np

from scattering.geometry.shapes import Plane


def orbit_plane(azimuth, half_extent):
    normal = np.array([-np.sin(azimuth), np.cos(azimuth), 0.0])
    return Plane(center=np.zeros(3), normal=normal,
                 half_extent=float(half_extent))
