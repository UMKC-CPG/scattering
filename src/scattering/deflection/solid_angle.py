"""The annulus-to-cone map (pseudocode 5.7, design 5.7): the tool's
central image, as numbers.

An annulus at b of width db has area Delta A = pi ((b + db)^2 - b^2). It
scatters into the cone between theta(b + db) and theta(b), whose solid angle is
Delta Omega = 2 pi |cos theta_1 - cos theta_2|. The finite ratio Delta A / Delta
Omega is shown beside dsigma/dOmega at the annulus midpoint; as db -> 0 the two
converge, which is the definition of a differential cross section seen as a
limit rather than stated as one (VISION G1).

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import dataclass

import numpy as np

from scattering.deflection.cross_section import dsdo_at
from scattering.deflection.deflection_function import deflection_of


@dataclass(frozen=True)
class AnnulusMap:
    impact: float
    width: float
    area: float
    theta_1: float
    theta_2: float
    solid_angle: float
    ratio: float
    dsdo_mid: float


def annulus_map(potential, energy, annulus, xsec):
    """The record for one declared annulus at one energy, eq. (5.6).
    The cone edges use the ASYMPTOTIC angles so that they agree with
    where the particles land on the detector."""
    impact, width = annulus.impact, annulus.width
    area = np.pi * ((impact + width) ** 2 - impact ** 2)
    theta_1 = abs(deflection_of(potential, energy, impact + width))
    theta_2 = abs(deflection_of(potential, energy, impact))
    solid_angle = 2.0 * np.pi * abs(np.cos(theta_1) - np.cos(theta_2))
    midpoint = abs(deflection_of(potential, energy, impact + 0.5 * width))
    return AnnulusMap(float(impact), float(width), float(area), float(theta_1),
        float(theta_2), float(solid_angle), float(area / solid_angle),
        float(dsdo_at(xsec, midpoint)))
