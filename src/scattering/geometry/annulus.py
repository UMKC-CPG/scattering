"""The incoming annulus (pseudocode 11.3, design 11.3): a flat ring in
the entry plane z = -R_max, inner radius b, outer radius b + db, where the
particles of that ring start.

Attribution: this module is part of the scattering teaching tool.
"""

import numpy as np

from scattering.geometry.shapes import Ring


def annulus_ring(annulus, r_max):
    """The ring for one declared annulus, in the entry plane."""
    return Ring(center=np.array([0.0, 0.0, -r_max]),
        normal=np.array([0.0, 0.0, 1.0]), inner=float(annulus.impact),
        outer=float(annulus.impact + annulus.width))
