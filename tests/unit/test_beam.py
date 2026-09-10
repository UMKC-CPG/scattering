"""Verifies pseudocode section 3 (P3.7). Design section 3."""

import numpy as np
import pytest

from scattering.beam import (AnnulusSpec, BeamSpec, check_admissible,
    generate_beam, layout_annuli, particle_energy, sample_disc)
from scattering.potentials import CoulombPotential

REFERENCE_SEED = 20260910


def test_layout_annuli():
    impact, azimuth, ring, widths = layout_annuli(
        [AnnulusSpec(1.0, 0.1, 24), AnnulusSpec(2.0, 0.2, 24)])
    assert len(impact) == 48
    assert np.all(impact[:24] == 1.0) and np.all(impact[24:] == 2.0)
    assert np.allclose(azimuth[:24], 2 * np.pi * np.arange(24) / 24)
    assert list(ring) == [0] * 24 + [1] * 24
    assert list(widths) == [0.1, 0.2]


def test_sample_disc_reference_values():
    """Regression on the first three draws at the reference seed:
    the draw order (all u, then all w) is part of the contract
    (design 3.5). Reproducibility rests on PCG64's raw stream."""
    rng = np.random.default_rng(REFERENCE_SEED)
    impact, azimuth = sample_disc(10, 0.0, 8.0, False, rng)
    expected_rng = np.random.default_rng(REFERENCE_SEED)
    u = expected_rng.random(10)
    w = expected_rng.random(10)
    assert np.allclose(impact, 8.0 * np.sqrt(u))
    assert np.allclose(azimuth, 2 * np.pi * w)
    assert np.all((impact >= 0.0) & (impact <= 8.0))
    assert np.all((azimuth >= 0.0) & (azimuth < 2 * np.pi))


def test_uniform_flux():
    """A8.4: with a fixed seed, counts in five equal-AREA annuli agree
    with n / 5 to 4 sigma. The property is seed-independent: the
    density in b is proportional to b, eq. (3.1)."""
    n = 200_000
    rng = np.random.default_rng(REFERENCE_SEED)
    impact, _ = sample_disc(n, 0.0, 8.0, False, rng)
    edges = 8.0 * np.sqrt(np.linspace(0.0, 1.0, 6))
    counts, _ = np.histogram(impact, bins=edges)
    assert np.all(np.abs(counts - n / 5) < 4 * np.sqrt(n / 5))


def test_stratified_has_one_per_stratum():
    n = 1000
    rng = np.random.default_rng(REFERENCE_SEED)
    impact, _ = sample_disc(n, 0.0, 1.0, True, rng)
    strata = np.floor(impact ** 2 * n).astype(int)
    assert sorted(strata) == list(range(n))


def test_forbidden_center_asks_the_potential():
    with pytest.raises(ValueError) as caught:
        check_admissible(np.array([0.0, 1.0]), CoulombPotential(-1))
    assert 'attractive Coulomb' in str(caught.value)
    check_admissible(np.array([0.0, 1.0]), CoulombPotential(+1))


def test_generate_beam_disc_and_flux():
    spec = BeamSpec(energies=np.array([1.0]), layout='disc', n_particles=500,
        b_min=0.0, b_max=8.0, seed=REFERENCE_SEED)
    beam = generate_beam(spec, CoulombPotential(+1))
    assert beam.n_particles == 500
    assert beam.flux == pytest.approx(500 / (np.pi * 64.0))
    assert np.all(beam.annulus_index == -1)
    assert not beam.impact_parameter.flags.writeable


def test_particle_energy_delta():
    spec = BeamSpec(energies=np.array([0.5, 1.0, 2.0]), layout='disc',
                    n_particles=3, b_max=1.0, seed=1)
    for k in range(3):
        assert particle_energy(spec, k, 0) == spec.energies[k]
