"""The beam records (pseudocode 3.1).

`BeamSpec` is what the run file says; `Beam` is what was generated from it,
frozen, with one entry per particle. The generated record carries the sampled
impact parameters and azimuths themselves, not merely the seed that produced
them: the seed is the source of reproducibility and the samples are its proof
(design 3.5).

Attribution: this module is part of the scattering teaching tool.
Derived code should cite it.
"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class AnnulusSpec:
    """One ring of the `annuli` layout: `n_azimuth` particles all at
    exactly `impact`, with `width` carried for drawing the ring and
    for the annulus-to-cone map (design 3.3, 5.7)."""
    impact: float
    width: float
    n_azimuth: int


@dataclass(frozen=True)
class BeamSpec:
    """The resolved [beam] table in natural units.

    `energies` is the sweep, in run-file order (design 3.2). Exactly one of the
    two layouts applies: `annuli` for the teaching picture, or `disc` with
    `n_particles`, `b_min`, `b_max`, and a required `seed` for uniform flux.
    `distribution` is the FD2 hook and only "delta" is accepted in the first
    version.
    """
    energies: np.ndarray
    layout: str
    annuli: tuple = ()
    n_particles: int = 0
    b_min: float = 0.0
    b_max: float = 0.0
    stratify: bool = False
    seed: Optional[int] = None
    distribution: str = 'delta'

    def largest_impact(self):
        """The largest transverse extent the beam reaches, used to
        place the entry plane (design 4.6)."""
        if self.layout == 'annuli':
            return max(ring.impact + ring.width for ring in self.annuli)
        return self.b_max

    def smallest_impact(self):
        if self.layout == 'annuli':
            return min(ring.impact for ring in self.annuli)
        return self.b_min

    def n_particles_total(self):
        """How many particles the beam throws (pseudocode 10.7)."""
        if self.layout == 'annuli':
            return sum(ring.n_azimuth for ring in self.annuli)
        return self.n_particles


def _read_only(array):
    array = np.array(array)
    array.flags.writeable = False
    return array


@dataclass(frozen=True)
class Beam:
    """The generated beam (design 3.6). Every array is read-only.

    `theta_min` and `theta_head` -- the smallest and largest scattering angles
    the beam can produce at each energy -- are consequences of the beam and the
    potential together, so they are filled in by the driver after the deflection
    stage has run (pseudocode 5.5, 6.4); they are NaN until then.
    """
    energies: np.ndarray
    impact_parameter: np.ndarray
    azimuth: np.ndarray
    annulus_index: np.ndarray
    annulus_width: np.ndarray
    flux: float
    layout: str
    seed: Optional[int]
    stratify: bool
    theta_min: np.ndarray = field(default=None)
    theta_head: np.ndarray = field(default=None)

    def __post_init__(self):
        n_energies = len(self.energies)
        for name in ('energies', 'impact_parameter', 'azimuth',
                     'annulus_index', 'annulus_width'):
            object.__setattr__(self, name, _read_only(getattr(self, name)))
        for name in ('theta_min', 'theta_head'):
            value = getattr(self, name)
            if value is None:
                value = np.full(n_energies, np.nan)
            object.__setattr__(self, name, _read_only(value))

    @property
    def n_particles(self):
        return len(self.impact_parameter)

    @property
    def n_energies(self):
        return len(self.energies)

    def with_angles(self, theta_min, theta_head):
        """A copy with the measured range filled in (the one field
        the driver adds after generation)."""
        return Beam(self.energies, self.impact_parameter, self.azimuth,
            self.annulus_index, self.annulus_width, self.flux, self.layout,
            self.seed, self.stratify, np.asarray(theta_min, dtype=float),
            np.asarray(theta_head, dtype=float))
