"""Verifies pseudocode section 2 (P2.5): the Coulomb closed forms
and the analytic orbit, mirroring dev/spikes/coulomb_closed_forms.py.
Design section 2."""

import numpy as np
import pytest

from scattering.potentials import CoulombPotential
from scattering.potentials.coulomb import (eccentricity, impact_of_angle,
    rutherford_cross_section, turning_point)

CASES = [(1.0, 0.5), (1.0, 2.0), (3.0, 0.3), (0.5, 4.0), (2.0, 0.05)]


@pytest.mark.parametrize('energy,impact', CASES)
def test_turning_point_forms_agree(energy, impact):
    for sign in (+1, -1):
        e = eccentricity(energy, impact)
        other_form = 2.0 * energy * impact ** 2 / (e - sign)
        assert turning_point(sign, energy, impact) == \
            pytest.approx(other_form, rel=1e-12)


def test_head_on_turning_point_is_probe_depth():
    assert turning_point(+1, 2.0, 0.0) == pytest.approx(0.5)


@pytest.mark.parametrize('energy,impact', CASES)
def test_deflection_is_odd_in_the_sign(energy, impact):
    plus = CoulombPotential(+1).closed_form_deflection(energy, impact)
    minus = CoulombPotential(-1).closed_form_deflection(energy, impact)
    assert plus == pytest.approx(-minus, abs=1e-15)
    assert 0.0 < plus < np.pi


def test_head_on_deflection_and_forbidden_center():
    assert CoulombPotential(+1).closed_form_deflection(1.0, 0.0) == np.pi
    with pytest.raises(ValueError):
        CoulombPotential(-1).closed_form_deflection(1.0, 0.0)


def test_cross_section_matches_definition():
    """(2.11) equals (b / sin theta) |db/dtheta| from (2.9) by finite
    difference, to 1e-8."""
    energy = 1.3
    theta = np.linspace(0.3, 2.8, 20)
    step = 1e-6
    slope = (impact_of_angle(energy, theta + step)
             - impact_of_angle(energy, theta - step)) / (2 * step)
    by_definition = impact_of_angle(energy, theta) / np.sin(theta) \
        * np.abs(slope)
    assert np.allclose(by_definition, rutherford_cross_section(energy, theta),
                       rtol=1e-8)


@pytest.mark.parametrize('sign', [+1, -1])
@pytest.mark.parametrize('energy,impact', CASES)
def test_anomaly_parametrization(sign, energy, impact):
    """Along H in [-5, 5]: r(H) equals (2.1) at phi(H); energy and
    angular momentum from the state are exact; t(H) inverts."""
    orbit = CoulombPotential(sign).closed_form_orbit(energy, impact)
    anomaly = np.linspace(-5.0, 5.0, 401)
    radius = orbit.radius_of_anomaly(anomaly)
    polar = orbit.polar_of_anomaly(anomaly)
    from_orbit_equation = (2.0 * energy * impact ** 2
                           / (orbit.eccentricity * np.cos(polar) - sign))
    assert np.allclose(from_orbit_equation, radius, rtol=1e-12)
    x, y, vx, vy = orbit.state_at_anomaly(anomaly)
    total_energy = 0.5 * (vx ** 2 + vy ** 2) + sign / radius
    assert np.allclose(total_energy, energy, rtol=1e-11)
    angmom = x * vy - y * vx
    assert np.allclose(angmom, np.sqrt(2 * energy) * impact, rtol=1e-11)
    recovered = orbit.anomaly_of_time(orbit.time_of_anomaly(anomaly))
    assert np.allclose(recovered, anomaly, atol=1e-12)


@pytest.mark.parametrize('sign', [+1, -1])
def test_beam_frame_conventions(sign):
    """The exact start at large R sits at x = +b moving +y at the
    asymptotic speed, and the exit velocity direction equals the closed-form
    deflection, with the exit on the near side for repulsion and the far side
    for attraction (design 4.8). This is
    the test that would catch a wrong rotation in (2.13)."""
    energy, impact, radius = 1.0, 2.0, 1e4
    potential = CoulombPotential(sign)
    x, y, vx, vy = potential.asymptotic_state(energy, impact, radius)
    assert x == pytest.approx(impact, abs=1e-3)
    assert y == pytest.approx(-radius, rel=1e-6)
    assert vx == pytest.approx(0.0, abs=1e-6)
    # The speed at finite R is sqrt(2 (E - V(R))), design 1.2.
    assert vy == pytest.approx(np.sqrt(2 * (energy - sign / radius)),
                               rel=1e-8)
    orbit = potential.closed_form_orbit(energy, impact)
    exit_anomaly = orbit.anomaly_of_radius(radius, outbound=True)
    ex, _, evx, evy = orbit.beam_frame_state(exit_anomaly)
    angle = np.arctan2(evx, evy)
    assert angle == pytest.approx(potential.closed_form_deflection(
        energy, impact), abs=1e-3)
    assert np.sign(ex) == sign


def test_turning_point_product_is_impact_squared():
    energy, impact = 1.3, 0.7
    product = turning_point(+1, energy, impact) * turning_point(-1, energy,
                                                                impact)
    assert product == pytest.approx(impact ** 2, rel=1e-12)
