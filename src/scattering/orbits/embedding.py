"""Placing an orbital plane in the three-dimensional scene
(pseudocode 4.8, design 4.8).

Each particle's plane contains the beam axis z and the particle's transverse
direction e_rho = (cos phi, sin phi, 0), where phi is its beam azimuth. In-plane
coordinates (x_p, y_p) map to the scene by

##   r = x_p e_rho + y_p z = (x_p cos phi, x_p sin phi, y_p)     (4.3)

Repulsion pushes x_p more positive (away from the axis); attraction pulls it
negative, so an attracted particle crosses the axis and leaves on the FAR side.
A detector that bins only the polar angle cannot see which -- VISION G8 in its
geometric form.

Attribution: this module is part of the scattering teaching tool.
"""

import numpy as np


def embed(x_plane, y_plane, azimuth):
    """Scene coordinates of in-plane (x_p, y_p) at beam azimuth phi.
    Applies to positions and velocities alike. Broadcasts over
    arrays of samples; `azimuth` is a scalar per particle."""
    x_plane = np.asarray(x_plane, dtype=float)
    y_plane = np.asarray(y_plane, dtype=float)
    return np.stack([x_plane * np.cos(azimuth), x_plane * np.sin(azimuth),
                     y_plane], axis=-1)


def out_direction(deflection, azimuth):
    """Unit vector of the asymptotic outgoing velocity, eq. (4.4):

    ##   n_out = (sin Theta cos phi, sin Theta sin phi, cos Theta)

    For Theta < 0 this points at azimuth phi + pi, the far side."""
    deflection = np.asarray(deflection, dtype=float)
    azimuth = np.asarray(azimuth, dtype=float)
    return np.stack([np.sin(deflection) * np.cos(azimuth),
                     np.sin(deflection) * np.sin(azimuth),
                     np.cos(deflection)], axis=-1)
