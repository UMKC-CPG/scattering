"""Verifies pseudocode section 5 (P5.9). Design section 5."""

import numpy as np
import pytest

from scattering.beam import AnnulusSpec, BeamSpec, generate_beam
from scattering.deflection import (annulus_map, build_cross_section_table,
                                   build_deflection_table,
                                   deflection_by_quadrature, mirror_check,
                                   particle_outputs)
from scattering.orbits import turning_point_from_g
from scattering.potentials import CoulombPotential
from scattering.potentials.coulomb import (rutherford_cross_section,
                                           turning_point)


@pytest.mark.parametrize('sign', [+1, -1])
@pytest.mark.parametrize('energy', [0.3, 1.0, 3.0])
@pytest.mark.parametrize('impact', [0.05, 0.3, 1.0, 3.0, 10.0, 50.0])
def test_quadrature_reproduces_rutherford(sign, energy, impact):
    potential = CoulombPotential(sign)
    theta, r_min, _ = deflection_by_quadrature(potential, energy, impact)
    assert theta == pytest.approx(
        potential.closed_form_deflection(energy, impact), abs=1e-10)
    assert r_min == pytest.approx(turning_point(sign, energy, impact),
                                  rel=1e-12)


def test_no_orbiting_for_coulomb():
    for impact in (0.05, 1.0, 20.0):
        assert turning_point_from_g(CoulombPotential(+1), 1.0, impact)[1] \
            is False


class BarrierPotential(CoulombPotential):
    """A test-only potential with an effective barrier, V = 1/r -
    2/r^2 + 1.2/r^3, on which g has a double root at some (E, b)."""

    has_closed_form_deflection = False
    has_closed_form_orbit = False
    has_mirror = False

    def __init__(self):
        super().__init__(+1)

    def value(self, radius):
        radius = np.asarray(radius, dtype=float)
        return 1 / radius - 2 / radius ** 2 + 1.2 / radius ** 3

    def derivative(self, radius):
        radius = np.asarray(radius, dtype=float)
        return -1 / radius ** 2 + 4 / radius ** 3 - 3.6 / radius ** 4


def test_orbiting_is_detected_on_a_barrier():
    """Orbiting happens where the effective potential's barrier top
    equals the energy (design 5.2). The bare potential has a barrier
    of height ~0.157 at r ~ 2.6, so at E = 0.2 the head-on particle
    passes over it and a growing impact parameter raises the barrier
    until its top reaches E: solve for that critical b, then the
    largest root of g is double and the detector must flag it, or
    the deflection must come out infinite. (At higher energy the
    barrier merges with the well before its top reaches E and no
    orbiting occurs; 0.16 sits just above the bare barrier's 0.157.)
    """
    from scipy.optimize import brentq
    potential = BarrierPotential()
    energy = 0.16
    radii = np.geomspace(1.2, 40.0, 8000)

    def barrier_minus_energy(impact):
        # V_eff = V + E b^2 / r^2 (unit mass, L^2 = 2 E b^2); the
        # barrier is the largest INTERIOR local maximum.
        effective = (potential.value(radii)
                     + energy * impact ** 2 / radii ** 2)
        interior = (effective[1:-1] > effective[:-2]) \
            & (effective[1:-1] > effective[2:])
        if not interior.any():
            return -energy
        return effective[1:-1][interior].max() - energy

    low, high = 0.05, 0.6
    assert barrier_minus_energy(low) < 0 < barrier_minus_energy(high)
    critical = brentq(barrier_minus_energy, low, high, xtol=1e-10)
    _, orbiting = turning_point_from_g(potential, energy, critical)
    theta, _, _ = deflection_by_quadrature(potential, energy, critical)
    assert orbiting or not np.isfinite(theta)


def test_cross_section_table_matches_rutherford():
    potential = CoulombPotential(+1)
    table = build_deflection_table(potential, 1.0, 0.0, 12.0, 400, True)
    xsec = build_cross_section_table(table)
    ok = xsec.flags == 'ok'
    reference = rutherford_cross_section(1.0, xsec.theta[ok])
    assert np.allclose(xsec.dsdo[ok], reference, rtol=1e-8)
    head = xsec.flags == 'extrapolated'
    assert head.sum() == 1
    assert xsec.dsdo[head][0] == pytest.approx(1.0 / 16.0, rel=1e-4)
    assert xsec.theta_head == pytest.approx(np.pi)


def test_non_monotone_table_is_refused():
    potential = CoulombPotential(+1)
    table = build_deflection_table(potential, 1.0, 0.1, 5.0, 50, False)
    bent = table.deflection.copy()
    bent[10] = bent[9] + 0.1
    from scattering.deflection.deflection_function import DeflectionTable
    bad = DeflectionTable(table.energy, table.impact, bent,
                          table.d_deflection, table.turning_point, False,
                          table.source, table.check)
    with pytest.raises(ValueError):
        build_cross_section_table(bad)


def test_mirror_check_is_zero_for_coulomb():
    potential = CoulombPotential(+1)
    table = build_deflection_table(potential, 1.0, 0.0, 12.0, 100, True)
    _, difference = mirror_check(potential, 1.0, table, 100, True)
    assert difference <= 1e-14


def test_annulus_ratio_converges_second_order():
    potential = CoulombPotential(+1)
    table = build_deflection_table(potential, 1.0, 0.0, 12.0, 400, True)
    xsec = build_cross_section_table(table)
    gaps = []
    for width in (0.08, 0.04, 0.02):
        record = annulus_map(potential, 1.0, AnnulusSpec(1.0, width, 1),
                             xsec)
        gaps.append(abs(record.ratio - record.dsdo_mid))
    assert gaps[0] / gaps[1] == pytest.approx(4.0, rel=0.15)
    assert gaps[1] / gaps[2] == pytest.approx(4.0, rel=0.15)


def test_particle_outputs():
    potential = CoulombPotential(+1)
    spec = BeamSpec(energies=np.array([1.0]), layout='disc',
                    n_particles=50, b_min=0.0, b_max=12.0, seed=3)
    beam = generate_beam(spec, potential)
    outputs = particle_outputs(potential, 1.0, beam)
    n_out = outputs['out_direction']
    assert np.allclose(np.linalg.norm(n_out, axis=1), 1.0)
    assert np.allclose(n_out[:, 2], np.cos(outputs['deflection']))
    largest = beam.impact_parameter.argmax()
    assert outputs['scattering_angle'][largest] == pytest.approx(
        abs(potential.closed_form_deflection(1.0, beam.impact_parameter.max())))
