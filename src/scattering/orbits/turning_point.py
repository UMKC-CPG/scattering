"""The turning point as the largest root of g(r) (pseudocode 5.2,
design 5.2), shared by the deflection stage and the orbit stage.

For a particle of energy E and impact parameter b,

##   g(r) = 1 - b^2 / r^2 - V(r) / E                            (5.2)

is the squared radial speed over the asymptotic speed squared: it is positive
outside the turning point and vanishes there. Its largest root is the distance
of closest approach. Where g has a DOUBLE root (g = 0 and dg/dr = 0 together)
the particle orbits the center indefinitely and the deflection diverges; that
case is detected and reported, not silently given a number (design 5.2).

Attribution: this module is part of the scattering teaching tool.
"""

import numpy as np
from scipy.optimize import brentq

# Below this radius the inward march gives up: g has no sign change, which for a
# repulsive potential cannot happen and for a later potential means something is
# wrong with its implementation.
_SMALLEST_RADIUS = 1e-12

# A double root of g is diagnosed by |g'(r_min)| below this, relative to the
# energy scale. Near a double root the slope goes as the square root of the
# distance to it, so a modest threshold is right; the deflection quadrature
# independently reports a divergent integral as the same condition.
_ORBITING_TOLERANCE = 1e-6


def g_function(potential, energy, impact, radius):
    """Eq. (5.2)."""
    return 1.0 - impact ** 2 / radius ** 2 - potential.value(radius) / energy


def g_derivative(potential, energy, impact, radius):
    """dg/dr, eq. (5.4); its value at the turning point is what the
    deflection integrand needs at rho = 0."""
    return (2.0 * impact ** 2 / radius ** 3
            - potential.derivative(radius) / energy)


def turning_point_from_g(potential, energy, impact):
    """Return (r_min, orbiting) for one (E, b).

    The head-on case with an admissible center is radial motion and the turning
    point is the root of V(r) = E. Otherwise the largest root of g is bracketed
    by marching inward from far out, halving the radius until g changes sign,
    and then found by Brent's method to machine precision. Marching inward finds
    the LARGEST root first, which is the physical turning point when g has
    several (design 5.2).
    """
    if impact == 0.0:
        if not potential.admits_center():
            raise ValueError(f'b = 0 is not an orbit for '
                             f'{potential.describe()}')
        radius = brentq(lambda r: potential.value(r) - energy, _SMALLEST_RADIUS,
            1e3 * max(1.0, 1.0 / energy), xtol=1e-15,
            rtol=4 * np.finfo(float).eps)
        return float(radius), False

    def g(radius):
        return g_function(potential, energy, impact, radius)

    high = 1e3 * max(1.0, impact)
    low = high
    while g(low) > 0.0:
        low *= 0.5
        if low < _SMALLEST_RADIUS:
            raise ValueError('no turning point: g(r) > 0 at every radius')
    radius = brentq(g, low, high, xtol=1e-15, rtol=4 * np.finfo(float).eps)
    slope = g_derivative(potential, energy, impact, radius)
    orbiting = abs(slope) < _ORBITING_TOLERANCE * max(1.0, abs(energy))
    return float(radius), bool(orbiting)
