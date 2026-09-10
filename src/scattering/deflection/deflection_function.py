"""The deflection function Theta(b) (pseudocode 5.2-5.4, 5.6, 5.8;
design 5.2-5.4, 5.6, 5.8).

For a particle of energy E and impact parameter b in a central
potential V, the signed deflection is

##   Theta(b) = pi - 2 b int_{r_min}^inf dr / (r^2 sqrt(g(r)))    (5.1)
##   g(r)     = 1 - b^2 / r^2 - V(r) / E                          (5.2)

The integrand has a square-root singularity at the turning point.
The substitution r = r_min + rho^2 removes it:

##   Theta = pi - 4 b int_0^inf rho drho / ((r_min + rho^2)^2 sqrt(g))
##                                                                 (5.3)

whose integrand is smooth on [0, inf) and decays as rho^-3, so
`scipy.integrate.quad` converges to tolerance. The sign comes out by
itself: an attractive potential sweeps more than pi / 2 and gives
Theta < 0 with no case analysis. Verified against the Rutherford
closed form to 2e-12 in dev/spikes/coulomb_closed_forms.py.

Every particle's Theta is evaluated directly at its own b -- never
interpolated from a table -- because it is what places the particle
on the detector (design 5.4).

Attribution: the deflection integral follows Goldstein, Poole and
Safko section 3.10 and Landau and Lifshitz section 18. This module
is part of the scattering teaching tool; derived code should cite
it and those sources.
"""

from dataclasses import dataclass

import numpy as np
from scipy.integrate import quad

from scattering.orbits.embedding import out_direction
from scattering.orbits.turning_point import (g_derivative, g_function,
                                             turning_point_from_g)

# Relative half-width of the centered difference for dTheta/db
# (design 5.4): its O(delta^2) truncation sits below the quadrature
# tolerance, as the spike measured (7e-9 in the cross section).
_DERIVATIVE_DELTA = 1e-4

# The floor of the log-spaced impact grid when the beam reaches
# b = 0, as a fraction of b_max (pseudocode 5.4).
_GRID_FLOOR_FRACTION = 1e-3


@dataclass(frozen=True)
class DeflectionTable:
    """Theta(b) tabulated on a grid at one energy (pseudocode 5.1)."""
    energy: float
    impact: np.ndarray
    deflection: np.ndarray
    d_deflection: np.ndarray
    turning_point: np.ndarray
    monotone: bool
    source: str
    check: float


def deflection_by_quadrature(potential, energy, impact):
    """Return (Theta, r_min, error_estimate) by eq. (5.3).

    b = 0 is the head-on case, Theta = pi without evaluation, so that
    the prefactor b = 0 never multiplies a 0 / 0 integrand. A double
    root of g (orbiting) yields an infinite Theta with the sign of
    the force at the turning point, and no quadrature.
    """
    if impact == 0.0:
        r_min, _ = turning_point_from_g(potential, energy, impact)
        return np.pi, r_min, 0.0
    r_min, orbiting = turning_point_from_g(potential, energy, impact)
    if orbiting:
        force_sign = -np.sign(potential.derivative(r_min))
        return float(np.copysign(np.inf, force_sign)), r_min, 0.0
    slope_at_turning = g_derivative(potential, energy, impact, r_min)

    def integrand(rho):
        if rho == 0.0:
            # The limit rho / sqrt(g) -> 1 / sqrt(g'(r_min)).
            return 1.0 / (np.sqrt(slope_at_turning) * r_min ** 2)
        radius = r_min + rho * rho
        return rho / (radius ** 2
                      * np.sqrt(g_function(potential, energy, impact,
                                           radius)))

    with np.errstate(divide='ignore', invalid='ignore'):
        integral, error = quad(integrand, 0.0, np.inf, epsabs=1e-12,
                               epsrel=1e-12, limit=200)
    if not np.isfinite(integral):
        # A double root the slope test did not resolve: the integral
        # itself diverges, which is the orbiting signature (design 5.2).
        force_sign = -np.sign(potential.derivative(r_min))
        return float(np.copysign(np.inf, force_sign)), r_min, np.inf
    return np.pi - 4.0 * impact * integral, r_min, error


def deflection_of(potential, energy, impact):
    """Signed Theta at one (E, b): the closed form when the potential
    offers one, the quadrature otherwise (design 5.4). Consumers do
    not know which (VISION P12)."""
    if potential.has_closed_form_deflection:
        return float(potential.closed_form_deflection(energy, impact))
    return deflection_by_quadrature(potential, energy, impact)[0]


def d_deflection_of(potential, energy, impact, delta=_DERIVATIVE_DELTA):
    """dTheta/db by a centered difference of the INTEGRAL (or closed
    form) at b (1 +/- delta) -- not of the table, whose spacing is
    set for display and would put interpolation error into the cross
    section (design 5.10)."""
    upper = deflection_of(potential, energy, impact * (1.0 + delta))
    lower = deflection_of(potential, energy, impact * (1.0 - delta))
    return (upper - lower) / (2.0 * impact * delta)


def build_deflection_table(potential, energy, b_min, b_max, n_points,
                           admits_center):
    """Tabulate Theta, dTheta/db, and r_min on a grid log-spaced in
    b (the deflection changes fastest at small b), with the head-on
    node prepended when the beam reaches an admissible center
    (pseudocode 5.4)."""
    floor = b_min if b_min > 0.0 else _GRID_FLOOR_FRACTION * b_max
    grid = np.geomspace(floor, b_max, n_points)
    if admits_center and b_min == 0.0:
        grid = np.concatenate([[0.0], grid])
    deflection = np.array([deflection_of(potential, energy, b) for b in grid])
    d_deflection = np.array([d_deflection_of(potential, energy, b)
                             if b > 0.0 else np.nan for b in grid])
    turning = np.array([turning_point_from_g(potential, energy, b)[0]
                        for b in grid])
    # |Theta| must decrease along increasing b for a monotone
    # potential; the sign of Theta is that of its last (large-b) node.
    magnitude = deflection * np.sign(deflection[-1])
    monotone = bool(np.all(np.diff(magnitude) <= 0.0))
    check = np.nan
    if potential.has_closed_form_deflection:
        subset = grid[::max(1, n_points // 20)]
        check = max(abs(potential.closed_form_deflection(energy, b)
                        - deflection_by_quadrature(potential, energy, b)[0])
                    for b in subset if b > 0.0)
    source = 'closed_form' if potential.has_closed_form_deflection \
        else 'quadrature'
    return DeflectionTable(float(energy), grid, deflection, d_deflection,
                           turning, monotone, source, float(check))


def particle_deflections(potential, energy, impacts):
    """Theta for every particle, each evaluated directly."""
    return np.array([deflection_of(potential, energy, b) for b in impacts])


def mirror_check(potential, energy, table, n_points, admits_center):
    """The sign-independence check of design 5.6: the mirror
    potential's table on the same grid, and the largest relative
    difference of the two cross sections at ok nodes (zero to
    precision for Coulomb). Returns (mirror_table, max_rel_diff)."""
    if not potential.has_mirror:
        return None, np.nan
    from scattering.deflection.cross_section import (
        build_cross_section_table)
    mirror = potential.mirror()
    b_min = float(table.impact[0])
    b_max = float(table.impact[-1])
    mirror_table = build_deflection_table(
        mirror, energy, b_min, b_max, n_points,
        admits_center and mirror.admits_center())
    # One table may carry a head-on node the other cannot (the
    # attractive mirror of a repulsive potential admits no b = 0), so
    # the comparison is made on the positive-b nodes, which are the
    # same log-spaced grid in both.
    ours = build_cross_section_table(_positive_nodes(table))
    theirs = build_cross_section_table(_positive_nodes(mirror_table))
    ok = (ours.flags == 'ok') & (theirs.flags == 'ok')
    if ok.sum() == 0:
        return mirror_table, np.nan
    difference = np.max(np.abs(ours.dsdo[ok] - theirs.dsdo[ok])
                        / ours.dsdo[ok])
    return mirror_table, float(difference)


def _positive_nodes(table):
    """The table restricted to b > 0."""
    keep = table.impact > 0.0
    return DeflectionTable(table.energy, table.impact[keep],
                           table.deflection[keep], table.d_deflection[keep],
                           table.turning_point[keep], table.monotone,
                           table.source, table.check)


def particle_outputs(potential, energy, beam):
    """Per-particle Theta, |Theta|, the asymptotic out-direction, and
    the turning point from the root of g (pseudocode 5.8). The
    out-direction is what the detector bins and what the outbound
    free flight follows (design 4.6, 4.7)."""
    deflection = particle_deflections(potential, energy,
                                      beam.impact_parameter)
    turning = np.array([turning_point_from_g(potential, energy, b)[0]
                        for b in beam.impact_parameter])
    return {
        'deflection': deflection,
        'scattering_angle': np.abs(deflection),
        'out_direction': out_direction(deflection, beam.azimuth),
        'turning_point_q': turning,
    }
