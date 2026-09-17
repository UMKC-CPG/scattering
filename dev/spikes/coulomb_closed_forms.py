#!/usr/bin/env python3

"""Verify the Coulomb closed forms of dev/design/02 numerically.

This is a spike (see dev/spikes/README.md): it answers one question
and is kept so the answer can be re-checked. The question is whether
the formulas written into design section 2 -- the orbit r(phi), the
turning point, the deflection function, the cross section, and the
hyperbolic-anomaly time parametrization for BOTH signs of the
potential -- are correct as written, in the natural units fixed by
design section 1 (unit mass, V = s / r, kinetic energy v^2 / 2,
asymptotic speed sqrt(2 E), angular momentum sqrt(2 E) b).

Every check is a relative error that should sit at floating-point
precision, except the deflection-against-integration check, whose
residual is the finite-R_max effect and must scale as 1 / R_max.

Run:  python3 dev/spikes/coulomb_closed_forms.py
"""

import numpy as np
from scipy.integrate import quad, solve_ivp
from scipy.optimize import brentq


def orbit_checks(sign, energy, impact):
    """Return the worst relative error of each closed-form identity
    for one (sign, energy, impact parameter) triple."""

    eccentricity = np.sqrt(1.0 + (2.0 * energy * impact) ** 2)
    semi_major = 1.0 / (2.0 * energy)
    errors = {}

    # (2.3): the two forms of the turning point agree.
    turning_a = 2.0 * energy * impact ** 2 / (eccentricity - sign)
    turning_b = (eccentricity + sign) / (2.0 * energy)
    errors['rmin_forms'] = abs(turning_a - turning_b) / turning_b

    # (2.12): hyperbolic anomaly. The sign of the potential appears as
    #   r = a (e cosh H + s), t = a^{3/2} (e sinh H + s H), and in the
    #   coefficient k of the phi(H) relation.
    anomaly = np.linspace(-5.0, 5.0, 2001)
    radius = semi_major * (eccentricity * np.cosh(anomaly) + sign)
    d_radius = semi_major * eccentricity * np.sinh(anomaly)
    d_time = semi_major ** 1.5 * (eccentricity * np.cosh(anomaly) + sign)
    coeff = np.sqrt((eccentricity - sign) / (eccentricity + sign))
    half_tanh = coeff * np.tanh(anomaly / 2.0)
    polar = 2.0 * np.arctan(half_tanh)
    d_polar = coeff / np.cosh(anomaly / 2.0) ** 2 / (1.0 + half_tanh ** 2)

    # (2.1) evaluated at phi(H) must reproduce r(H).
    radius_from_polar = (2.0 * energy * impact ** 2
                         / (eccentricity * np.cos(polar) - sign))
    errors['orbit'] = np.max(np.abs(radius_from_polar - radius) / radius)

    # Energy and angular momentum along the parametrized orbit.
    radial_speed = d_radius / d_time
    angular_speed = radius * d_polar / d_time
    total_energy = 0.5 * (radial_speed ** 2 + angular_speed ** 2)
    total_energy += sign / radius
    errors['energy'] = np.max(np.abs(total_energy - energy)) / energy
    ang_mom = radius ** 2 * d_polar / d_time
    expected = np.sqrt(2.0 * energy) * impact
    errors['angmom'] = np.max(np.abs(ang_mom - expected)) / expected

    # (2.4): the product of the two turning points is b^2.
    product = ((eccentricity + 1.0) * (eccentricity - 1.0)
               / (4.0 * energy ** 2))
    errors['product'] = abs(product - impact ** 2) / impact ** 2

    # (2.11) against the definition (2.10) with (2.9), by a central
    #   finite difference in theta.
    theta = np.linspace(0.3, 2.8, 50)
    step = 1e-6

    def impact_of(angle):
        return 1.0 / np.tan(angle / 2.0) / (2.0 * energy)

    slope = (impact_of(theta + step) - impact_of(theta - step)) / (2 * step)
    by_definition = impact_of(theta) / np.sin(theta) * np.abs(slope)
    rutherford = 1.0 / (16.0 * energy ** 2 * np.sin(theta / 2.0) ** 4)
    errors['xsec'] = np.max(np.abs(by_definition - rutherford)
                            / by_definition)
    return errors


def deflection_vs_integration(sign, energy, impact, start_radius):
    """Difference between (2.8) and a direct integration of the planar
    equations of motion started on the straight-line asymptote at a
    finite radius. This residual is NOT a formula error: it is the
    finite-R_max effect that design section 4 must correct for."""

    exact = 2.0 * np.arctan(sign / (2.0 * energy * impact))
    speed = np.sqrt(2.0 * energy)

    def rhs(_, state):
        x, y, vx, vy = state
        inv_cube = (x * x + y * y) ** -1.5
        return [vx, vy, sign * x * inv_cube, sign * y * inv_cube]

    solution = solve_ivp(rhs, [0.0, 2.5 * start_radius / speed],
                         [impact, -start_radius, 0.0, speed],
                         rtol=1e-12, atol=1e-14)
    final_vx, final_vy = solution.y[2, -1], solution.y[3, -1]
    return exact - np.arctan2(final_vx, final_vy)


def deflection_by_quadrature(sign, energy, impact):
    """Design section 5, eq. (5.3): the deflection integral with the
    rho^2 substitution that removes the turning-point singularity.
    Returns (Theta, r_min). Written for Coulomb only, as a check that
    the general machinery reproduces the closed form."""

    if impact == 0.0:
        return np.pi, 1.0 / energy

    def g(r):
        return 1.0 - impact ** 2 / r ** 2 - sign / (r * energy)

    def g_prime(r):
        return 2.0 * impact ** 2 / r ** 3 + sign / (r * r * energy)

    # Bracket the largest root of g by marching inward from far out.
    high = 1e3 * max(1.0, impact)
    low = high
    while g(low) > 0.0:
        low *= 0.5
    turning = brentq(g, low, high, xtol=1e-15, rtol=1e-15)

    def integrand(rho):
        radius = turning + rho * rho
        if rho == 0.0:
            return 1.0 / np.sqrt(g_prime(turning)) / turning ** 2
        return rho / (radius * radius * np.sqrt(g(radius)))

    integral, _ = quad(integrand, 0.0, np.inf,
                       epsabs=1e-12, epsrel=1e-12, limit=200)
    return np.pi - 4.0 * impact * integral, turning


def quadrature_checks():
    """Worst error of (5.3) against (2.8), and of the cross section
    built from a differenced integral against (2.11)."""

    worst_theta = 0.0
    worst_turning = 0.0
    for sign in (+1, -1):
        for energy in (0.3, 1.0, 3.0):
            for impact in (0.05, 0.3, 1.0, 3.0, 10.0, 50.0):
                theta, turning = deflection_by_quadrature(
                    sign, energy, impact)
                exact = 2.0 * np.arctan(sign / (2.0 * energy * impact))
                ecc = np.sqrt(1.0 + (2.0 * energy * impact) ** 2)
                exact_turning = (ecc + sign) / (2.0 * energy)
                worst_theta = max(worst_theta, abs(theta - exact))
                worst_turning = max(
                    worst_turning,
                    abs(turning - exact_turning) / exact_turning)

    # Cross section via dTheta/db from differencing the integral at
    #   b (1 +/- delta), as design section 5.4 prescribes.
    delta = 1e-4
    worst_xsec = 0.0
    for impact in (0.1, 0.5, 2.0, 8.0):
        theta = abs(deflection_by_quadrature(+1, 1.0, impact)[0])
        upper = deflection_by_quadrature(+1, 1.0, impact * (1 + delta))[0]
        lower = deflection_by_quadrature(+1, 1.0, impact * (1 - delta))[0]
        slope = (upper - lower) / (2.0 * impact * delta)
        xsec = impact / np.sin(theta) / abs(slope)
        rutherford = 1.0 / (16.0 * np.sin(theta / 2.0) ** 4)
        worst_xsec = max(worst_xsec, abs(xsec - rutherford) / rutherford)
    return worst_theta, worst_turning, worst_xsec


def main():
    worst = {}
    cases = [(1.0, 0.5), (1.0, 2.0), (3.0, 0.3), (0.5, 4.0), (2.0, 0.05)]
    for sign in (+1, -1):
        for energy, impact in cases:
            for key, value in orbit_checks(sign, energy, impact).items():
                worst[key] = max(worst.get(key, 0.0), value)

    print('Closed-form identities, worst relative error over all cases:')
    for key, value in worst.items():
        print(f'  {key:12s} {value:.2e}')

    theta_err, turning_err, xsec_err = quadrature_checks()
    print('\nDeflection integral (5.3) against the closed forms:')
    print(f'  |Theta_quad - (2.8)|      worst {theta_err:.2e}')
    print(f'  r_min from root of g      worst rel {turning_err:.2e}')
    print(f'  dsigma/dOmega vs (2.11)   worst rel {xsec_err:.2e}')

    print('\nDeflection (2.8) minus direct integration from radius R,')
    print('for s=+1, E=1, b=2. R * difference should be constant:')
    for radius in (1000.0, 2000.0, 4000.0, 8000.0):
        diff = deflection_vs_integration(+1, 1.0, 2.0, radius)
        print(f'  R = {radius:6.0f}   diff = {diff:+.3e}   '
              f'R * diff = {radius * diff:+.4f}')


if __name__ == '__main__':
    main()
