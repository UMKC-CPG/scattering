"""Laying out or sampling the impact parameters (pseudocode 3.2-3.5).

Two layouts (design 3.3). `annuli` places particles at exactly the declared
impact parameters, evenly in azimuth, so that a ring stays a ring as it scatters
and lands on one cone -- the teaching picture. `disc` fills a disc with UNIFORM
FLUX, the number per unit transverse area constant, which is the beam a cross
section is defined against and what the detector needs to estimate one.

Uniform flux means the probability density in b is proportional to
b, so b is drawn by inverse transform, b = sqrt(b_min^2 + u (b_max^2
- b_min^2)) with u uniform on [0, 1). Sampling b uniformly instead is
the classic beginner's error (design 3.8): it gives a flux falling as 1 / b and
counts that estimate nothing.

Only `rng.random()` is used, in a fixed order (all u, then all w), so that
reproducibility rests on NumPy's PCG64 raw stream -- which NumPy holds stable
across versions -- and not on its distribution methods, which it does not
(design 3.5).

Attribution: this module is part of the scattering teaching tool.
Derived code should cite it.
"""

import numpy as np

from scattering.beam.beam_spec import Beam


def layout_annuli(annuli):
    """Particles of each ring are contiguous in index, rings in the
    declared order, azimuth increasing within a ring (pseudocode
    3.3). Returns (impact, azimuth, ring_index, ring_width)."""
    impact, azimuth, ring_index = [], [], []
    for index, ring in enumerate(annuli):
        for j in range(ring.n_azimuth):
            impact.append(ring.impact)
            azimuth.append(2.0 * np.pi * j / ring.n_azimuth)
            ring_index.append(index)
    widths = [ring.width for ring in annuli]
    return (np.array(impact, dtype=float), np.array(azimuth, dtype=float),
            np.array(ring_index, dtype=int), np.array(widths, dtype=float))


def sample_disc(n_particles, b_min, b_max, stratify, rng):
    """Uniform-flux sampling of an annular disc, eqs. (3.1)-(3.2).

    With `stratify`, the interval of b^2 is divided into n_particles
    equal strata and one particle is placed uniformly within each:
    the flux is still uniform on average but the count in any bin has less
    variance. A stratified beam is not what an accelerator produces, and the
    display labels it as such (design 3.3).
    """
    uniform_area = rng.random(n_particles)
    uniform_angle = rng.random(n_particles)
    if stratify:
        uniform_area = (np.arange(n_particles) + uniform_area) / n_particles
    impact = np.sqrt(b_min ** 2 + uniform_area * (b_max ** 2 - b_min ** 2))
    azimuth = 2.0 * np.pi * uniform_angle
    return impact, azimuth


def check_admissible(impact, potential):
    """Refuse b = 0 where the potential says it is not an orbit --
    attractive Coulomb falls to the center (design 3.4). The
    question is put to the potential, never to its sign."""
    if not potential.admits_center() and np.any(impact == 0.0):
        raise ValueError(f'impact parameter 0 is not an orbit for '
                         f'{potential.describe()}: raise b_min or the '
                         f'annulus b')


def generate_beam(spec, potential):
    """Build the frozen Beam record from a spec (pseudocode 3.2).

    Validation of the spec (a seed present for `disc`, b_min < b_max, non-empty
    annuli, ...) is the run-file loader's job; this function assumes a valid
    spec and asserts the essentials.
    """
    if spec.layout == 'annuli':
        assert len(spec.annuli) > 0, 'annuli layout with no rings'
        impact, azimuth, ring_index, widths = layout_annuli(spec.annuli)
        flux = np.nan
    elif spec.layout == 'disc':
        assert spec.seed is not None, 'disc layout requires a seed'
        assert spec.n_particles >= 1 and spec.b_min < spec.b_max
        rng = np.random.default_rng(spec.seed)
        impact, azimuth = sample_disc(spec.n_particles, spec.b_min,
                                      spec.b_max, spec.stratify, rng)
        ring_index = np.full(spec.n_particles, -1, dtype=int)
        widths = np.array([], dtype=float)
        # Flux per unit transverse area, eq. (3.3): every cross- section
        # estimate divides by it.
        flux = spec.n_particles / (np.pi * (spec.b_max ** 2
                                            - spec.b_min ** 2))
    else:
        raise ValueError(f'unknown beam layout {spec.layout!r}')
    check_admissible(impact, potential)
    return Beam(np.asarray(spec.energies, dtype=float), impact, azimuth,
        ring_index, widths, float(flux), spec.layout, spec.seed, spec.stratify)
