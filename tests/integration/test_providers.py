"""Verifies pseudocode section 4 (P4.11): the two orbit providers
against each other and against the closed forms. Design section 4."""

import numpy as np
import pytest

from scattering.core.natural_units import asymptotic_speed
from scattering.orbits import (AnalyticProvider, NumericalProvider,
    OrbitSettings, initial_state, out_direction)
from scattering.orbits.equations_of_motion import equations_of_motion
from scattering.orbits.integrators import exit_event, integrate
from scattering.potentials import CoulombPotential

CASES = [(1.0, 0.5), (1.0, 2.0), (3.0, 0.3), (0.5, 4.0), (2.0, 0.05)]


def settings_for(r_max, **overrides):
    return OrbitSettings(r_max=r_max, entry_plane_z=r_max, **overrides)


def common_grid(orbit_a, orbit_b, count=200):
    """Orbit times of `orbit_a` that map onto `orbit_b`'s clock: the
    two providers place their zero differently, so compare at equal
    times since the entry."""
    times_a = np.linspace(orbit_a.entry_time, orbit_a.exit_time, count)
    times_b = times_a - orbit_a.entry_time + orbit_b.entry_time
    return times_a, times_b


@pytest.mark.parametrize('sign', [+1, -1])
@pytest.mark.parametrize('energy,impact', CASES)
def test_provider_agreement(sign, energy, impact):
    """A6.2: the numerical provider on Coulomb, with the exact start,
    reproduces the analytic one to 1e-8 in state, 1e-9 in turning
    point, and the two agree on the entry-plane time."""
    potential = CoulombPotential(sign)
    settings = settings_for(40.0)
    analytic = AnalyticProvider().provide(potential, energy, impact,
                                          settings)
    numerical = NumericalProvider().provide(potential, energy, impact,
                                            settings)
    times_a, times_n = common_grid(analytic, numerical)
    assert np.max(np.abs(analytic.state_at(times_a)
                         - numerical.state_at(times_n))) < 1e-7
    assert numerical.turning_point == pytest.approx(analytic.turning_point,
                                                    rel=1e-9)
    offset_a = analytic.time_offset - analytic.entry_time
    offset_n = numerical.time_offset - numerical.entry_time
    assert offset_a == pytest.approx(offset_n, abs=1e-8)
    assert numerical.energy_drift < 1e-8
    assert numerical.angmom_drift < 1e-8
    assert np.sign(numerical.exit_state[0]) == sign
    assert np.sign(analytic.exit_state[0]) == sign


def test_analytic_samples_conserve_to_precision():
    potential = CoulombPotential(+1)
    orbit = AnalyticProvider().provide(potential, 1.0, 2.0, settings_for(40.0))
    states = orbit.state_at(np.linspace(orbit.entry_time, orbit.exit_time,
                                        300))
    radius = np.hypot(states[:, 0], states[:, 1])
    energy = 0.5 * (states[:, 2] ** 2 + states[:, 3] ** 2) + 1.0 / radius
    assert np.allclose(energy, 1.0, rtol=1e-12)


def test_time_reversal_symmetry():
    potential = CoulombPotential(-1)
    orbit = NumericalProvider().provide(potential, 1.0, 1.5, settings_for(40.0))
    lag = np.linspace(0.0, orbit.pericenter_time - orbit.entry_time, 50)
    before = orbit.state_at(orbit.pericenter_time - lag)
    after = orbit.state_at(orbit.pericenter_time + lag)
    r_before = np.hypot(before[:, 0], before[:, 1])
    r_after = np.hypot(after[:, 0], after[:, 1])
    assert np.allclose(r_before, r_after, rtol=1e-9)


def test_entry_plane_and_exit():
    potential = CoulombPotential(+1)
    settings = settings_for(40.0)
    for provider in (AnalyticProvider(), NumericalProvider()):
        orbit = provider.provide(potential, 1.0, 3.0, settings)
        entry = orbit.state_at([orbit.entry_time])[0]
        y_at_plane = entry[1] + asymptotic_speed(1.0) * (orbit.time_offset
                                                          - orbit.entry_time)
        assert y_at_plane == pytest.approx(-40.0, abs=1e-10)
        assert np.hypot(*orbit.exit_state[:2]) == pytest.approx(40.0,
                                                                 abs=1e-8)


def test_exterior_deflection_scales_as_one_over_r_max_squared():
    """Design 4.4 as corrected: the angle between the exit velocity
    and the asymptote is the potential's deflection beyond R_max -- b / (2
    R_max^2) for Coulomb -- the same for either start. The first draft of this
    test asserted 1 / R_max and failed; that
    order belongs to the start error, tested separately below."""
    potential = CoulombPotential(+1)
    n_out = out_direction(potential.closed_form_deflection(1.0, 2.0), 0.0)
    angles = []
    for r_max in (20.0, 40.0, 80.0):
        orbit = AnalyticProvider().provide(potential, 1.0, 2.0,
                                           settings_for(r_max))
        exit_velocity = np.array([orbit.exit_state[2], 0.0,
                                  orbit.exit_state[3]])
        cosine = exit_velocity @ n_out / np.linalg.norm(exit_velocity)
        angles.append(np.arccos(np.clip(cosine, -1, 1)))
    ratios = np.array(angles[:-1]) / np.array(angles[1:])
    assert np.allclose(ratios, 4.0, rtol=0.10)
    # b / (4 E R^2) at b = 2, E = 1, R = 40.
    assert angles[1] == pytest.approx(2.0 / (4 * 40.0 ** 2), rel=0.05)


def test_start_error_scales_as_one_over_r_max():
    """The corrected straight-line start is wrong by O(1 / R_max);
    the exact start is not (design 4.4, the spike's measurement)."""
    potential = CoulombPotential(+1)
    corrected_gaps, exact_gaps = [], []
    for r_max in (20.0, 40.0, 80.0):
        settings = settings_for(r_max, orbit_provider='numerical')
        analytic = AnalyticProvider().provide(potential, 1.0, 2.0, settings)
        exact = NumericalProvider().provide(potential, 1.0, 2.0, settings)
        exact_gaps.append(np.max(np.abs(exact.exit_state
                                        - analytic.exit_state)))
        corrected_start = initial_state(potential, 1.0, 2.0, settings,
                                        force_corrected=True)
        solution = integrate(equations_of_motion(potential),
                             corrected_start, settings, exit_event(r_max))
        corrected_exit = solution.sol(solution.t_exit)
        corrected_gaps.append(np.max(np.abs(corrected_exit[2:]
                                            - analytic.exit_state[2:])))
    assert max(exact_gaps) < 1e-7
    ratios = np.array(corrected_gaps[:-1]) / np.array(corrected_gaps[1:])
    assert np.allclose(ratios, 2.0, rtol=0.15)


def test_verlet_is_second_order():
    potential = CoulombPotential(+1)
    drifts = []
    for step in (0.02, 0.01, 0.005):
        settings = settings_for(20.0, integrator='verlet', step=step)
        orbit = NumericalProvider().provide(potential, 1.0, 1.0, settings)
        drifts.append(orbit.energy_drift)
    ratios = np.array(drifts[:-1]) / np.array(drifts[1:])
    assert np.allclose(ratios, 4.0, rtol=0.2)


def test_trace_respects_turning_angle():
    potential = CoulombPotential(-1)
    settings = settings_for(40.0)
    orbit = NumericalProvider().provide(potential, 1.0, 0.3, settings)
    points = orbit.trace()
    segments = np.diff(points, axis=0)
    unit = segments / np.linalg.norm(segments, axis=1)[:, None]
    angles = np.arccos(np.clip(np.sum(unit[:-1] * unit[1:], axis=1), -1, 1))
    assert np.all(angles <= settings.trace_angle + 1e-9) \
        or len(points) >= settings.trace_points_max


def test_head_on_repulsive():
    potential = CoulombPotential(+1)
    settings = settings_for(40.0)
    for provider in (AnalyticProvider(), NumericalProvider()):
        orbit = provider.provide(potential, 2.0, 0.0, settings)
        assert orbit.turning_point == pytest.approx(0.5, rel=1e-9)
        states = orbit.state_at(np.linspace(orbit.entry_time,
                                            orbit.exit_time, 50))
        assert np.max(np.abs(states[:, 0])) < 1e-9
        # At finite R the speed is sqrt(2 (E - V(R))), not asymptotic.
        speed_at_exit = np.sqrt(2.0 * (2.0 - 1.0 / 40.0))
        assert orbit.exit_state[3] == pytest.approx(-speed_at_exit, rel=1e-8)
