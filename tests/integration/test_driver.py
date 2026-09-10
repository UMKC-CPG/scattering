"""Verifies pseudocode section 6 (P6.6), the driver half: a whole
store from the rutherford example, its invariants, and the
determinism guarantee of ARCHITECTURE 8.6(3)."""

import time

import numpy as np
import pytest

from scattering.beam.beam_spec import AnnulusSpec, BeamSpec
from scattering.run import (FidelitySpec, PotentialSpec, RcSettings,
                            RunSpec, build_results_store, check_budget)


def rutherford_spec(n_samples=200, **fidelity):
    """runs/rutherford.toml, built in code (pseudocode 6.3)."""
    return RunSpec(
        potential=PotentialSpec(kind='coulomb', preset='alpha_on_gold'),
        beam=BeamSpec(energies=['3 MeV', '5 MeV', '8 MeV'], layout='annuli',
                      annuli=(AnnulusSpec(0.0, 0.05, 1),
                              AnnulusSpec(0.25, 0.05, 8),
                              AnnulusSpec(1.0, 0.05, 8),
                              AnnulusSpec(4.0, 0.05, 8))),
        fidelity=FidelitySpec(r_max=40.0, n_samples=n_samples,
                              n_deflection_points=100, **fidelity))


@pytest.fixture(scope='module')
def store():
    return build_results_store(rutherford_spec())


def test_builds_quickly(store):
    """A wall-clock guard, marked as such: the example must build in
    well under ten seconds on a login node."""
    start = time.time()
    build_results_store(rutherford_spec())
    assert time.time() - start < 10.0


def test_phase_structure(store):
    K, N = store.n_energies, store.n_particles
    for k in range(K):
        for i in range(N):
            phase = store.phase[k, i]
            assert np.all(np.diff(phase) >= 0)
            assert (phase == 0).any() and (phase == 1).any()
            if store.impact_parameter[i] > 0:
                assert (phase == -1).any()


def test_free_flight_is_straight(store):
    k, i = 1, 5
    phase = store.phase[k, i]
    for leg in (-1, +1):
        points = store.position[k, i, phase == leg]
        if len(points) < 3:
            continue
        direction = points[-1] - points[0]
        direction /= np.linalg.norm(direction)
        offsets = points - points[0]
        residual = offsets - np.outer(offsets @ direction, direction)
        assert np.max(np.abs(residual)) < 1e-10


def test_entry_and_exit_samples_bracket_r_max(store):
    for k in range(store.n_energies):
        step = store.time_grid[k, 1] - store.time_grid[k, 0]
        speed = np.sqrt(2 * store.energies[k])
        for i in range(store.n_particles):
            r_entry = store.polar[k, i, store.entry_index[k, i], 0]
            assert 40.0 - speed * step < r_entry <= 40.0 + 1e-9
            exit_index = store.exit_index[k, i]
            if exit_index < store.n_samples:
                r_exit = store.polar[k, i, exit_index, 0]
                assert 40.0 - 1e-9 <= r_exit < 40.0 + speed * step


def test_polar_radius_matches_position(store):
    radius = np.linalg.norm(store.position, axis=-1)
    assert np.allclose(store.polar[..., 0], radius, rtol=1e-12)


def test_turning_points_and_deflections(store):
    assert np.allclose(store.turning_point, store.turning_point_q, rtol=1e-9)
    from scattering.potentials import CoulombPotential
    potential = CoulombPotential(+1)
    for k, energy in enumerate(store.energies):
        expected = potential.closed_form_deflection(energy,
                                                    store.impact_parameter)
        assert np.allclose(store.deflection[k], expected)
        assert store.theta_min[k] == pytest.approx(
            abs(potential.closed_form_deflection(energy, 4.0)))
        assert store.theta_head[k] == pytest.approx(np.pi)


def test_measured_range_written_to_beam(store):
    assert np.allclose(store.beam.theta_min, store.theta_min)
    assert np.allclose(store.beam.theta_head, store.theta_head)


def test_determinism():
    """ARCHITECTURE 8.6(3): two builds are bit-identical, and a read
    sequence leaves every array unchanged."""
    first = build_results_store(rutherford_spec(n_samples=50))
    second = build_results_store(rutherford_spec(n_samples=50))
    for name in ('position', 'velocity', 'polar', 'phase', 'deflection',
                 'turning_point', 'time_offset', 'out_direction'):
        assert np.array_equal(getattr(first, name), getattr(second, name))
    snapshot = first.position.copy()
    for n in (0, 10, 49, 3, 25):
        first.frame(0, n)
        first.frame_polar(2, n)
    first.particle(1, 2)
    first.trace(0, 0)
    first.tables(1)
    assert np.array_equal(first.position, snapshot)


def test_budget_refusal_names_the_setting():
    spec = rutherford_spec(n_samples=100_000)
    with pytest.raises(MemoryError) as caught:
        check_budget(spec, RcSettings(max_store_bytes=1_000_000))
    assert 'max_store_bytes' in str(caught.value)


def test_batch_mode_store():
    store = build_results_store(rutherford_spec(n_samples=0))
    assert store.position is None
    assert store.out_direction.shape == (3, 25, 3)
    assert np.isfinite(store.deflection).all()


def test_provenance(store):
    assert store.provider == ['analytic'] * 3
    assert store.versions['numpy']
    assert store.created
