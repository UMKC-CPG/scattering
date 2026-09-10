"""The Coulomb potential V = s / r and its closed forms.

Design section 2 collects everything that is exactly solvable about
scattering in a 1 / r potential, in the natural units of design
section 1 (unit mass, reference length |kappa| / E_ref so that the
strength is exactly one, kinetic energy v^2 / 2). Pseudocode section
2 fixes the functions. Every formula here is verified numerically by
dev/spikes/coulomb_closed_forms.py; a change to any of them must be
re-run through that spike.

The sign convention: s = +1 is repulsive (like charges; Rutherford),
s = -1 is attractive (gravity; unlike charges). The two are the same
hyperbola's two branches, and the closed forms below carry `s` so
that one function serves both.

Attribution: the closed forms follow Goldstein, Poole and Safko,
Classical Mechanics 3rd ed. sections 3.7 and 3.10, and Landau and
Lifshitz, Mechanics 3rd ed. sections 15 and 19; see design 2.10.
This module is part of the scattering teaching tool; derived code
should cite it and those sources.
"""

from dataclasses import dataclass

import numpy as np

from scattering.potentials.potential_interface import Potential

# Newton iterations for inverting t(H); the function is monotone and
# nearly exponential, so this bound is never approached in practice.
_MAX_NEWTON_ITERATIONS = 50


class CoulombPotential(Potential):
    """V(r) = s / r with s = +1 (repulsive) or -1 (attractive)."""

    has_closed_form_deflection = True
    has_closed_form_orbit = True
    has_mirror = True

    def __init__(self, sign):
        if sign not in (+1, -1):
            raise ValueError(f'sign must be +1 or -1, got {sign!r}')
        self.sign = int(sign)

    # --- Required part of the contract ---------------------------

    def value(self, radius):
        return self.sign / np.asarray(radius, dtype=float)

    def derivative(self, radius):
        return -self.sign / np.asarray(radius, dtype=float) ** 2

    def admits_center(self):
        # Design 2.3: repulsive head-on turns back at r = 1 / E;
        # attractive head-on falls to the center and is not an orbit.
        return self.sign == +1

    def default_reference_length(self, kappa, reference_energy):
        # Design 1.3: the head-on turning point at the reference
        # energy, so that V~ = s / r~ with strength exactly one.
        return abs(kappa) / reference_energy

    def tail_exponent(self):
        return 1

    def describe(self):
        return 'repulsive Coulomb' if self.sign > 0 \
            else 'attractive Coulomb'

    def mirror(self):
        return CoulombPotential(-self.sign)

    # --- Closed forms (design 2.2-2.5) ---------------------------

    def closed_form_deflection(self, energy, impact):
        """Signed deflection Theta = 2 atan(s / (2 E b)), eq. (2.8).
        At b = 0 the repulsive orbit turns straight back (Theta = pi);
        the attractive one has no orbit there."""
        impact = np.asarray(impact, dtype=float)
        if np.any(impact == 0.0):
            if self.sign < 0:
                raise ValueError('attractive Coulomb has no b = 0 orbit')
            # Elementwise so that arrays with a zero entry work too.
            with np.errstate(divide='ignore'):
                result = 2.0 * np.arctan(self.sign / (2.0 * energy * impact))
            return np.where(impact == 0.0, np.pi, result)
        return 2.0 * np.arctan(self.sign / (2.0 * energy * impact))

    def closed_form_orbit(self, energy, impact):
        return AnalyticOrbit(self.sign, float(energy), float(impact))

    def asymptotic_state(self, energy, impact, radius):
        """Exact in-plane state at `radius`, inbound, in the beam
        frame (pseudocode 2.3). Used to start a numerical integration
        with no finite-radius error at all (design 4.4)."""
        orbit = self.closed_form_orbit(energy, impact)
        anomaly = orbit.anomaly_of_radius(radius, outbound=False)
        return orbit.beam_frame_state(anomaly)


def eccentricity(energy, impact):
    """e = sqrt(1 + (2 E b)^2), eq. (2.2). Exceeds one for every b > 0,
    so every scattering orbit is a hyperbola."""
    return np.sqrt(1.0 + (2.0 * energy * np.asarray(impact)) ** 2)


def turning_point(sign, energy, impact):
    """Distance of closest approach r_min = (e + s) / (2 E), eq.
    (2.3). This form, not 2 E b^2 / (e - s), because the latter is
    0 / 0 at b = 0. Repulsive head-on gives 1 / E, the probe depth."""
    return (eccentricity(energy, impact) + sign) / (2.0 * energy)


def impact_of_angle(energy, theta):
    """b(theta) = cot(theta / 2) / (2 E), eq. (2.9), for theta in
    (0, pi]. The inverse of the deflection function's magnitude."""
    return 1.0 / np.tan(np.asarray(theta) / 2.0) / (2.0 * energy)


def rutherford_cross_section(energy, theta):
    """dsigma/dOmega = 1 / (16 E^2 sin^4(theta / 2)), eq. (2.11), in
    units of the reference length squared. Independent of the sign
    of the potential (design 2.5, VISION G8)."""
    return 1.0 / (16.0 * energy ** 2 * np.sin(np.asarray(theta) / 2.0) ** 4)


def asymptote_angle(sign, energy, impact):
    """phi_inf = acos(s / e), eq. (2.5): the polar angle of either
    asymptote measured from pericenter."""
    return np.arccos(sign / eccentricity(energy, impact))


@dataclass(frozen=True)
class AnalyticOrbit:
    """A Coulomb orbit parametrized by the hyperbolic anomaly H
    (design 2.6, pseudocode 2.3).

    With H = 0 and t = 0 at pericenter,

    ##   r(H)       = a (e cosh H + s)
    ##   t(H)       = a^(3/2) (e sinh H + s H)
    ##   tan(phi/2) = k tanh(H/2),   k = sqrt((e - s) / (e + s))

    where a = 1 / (2 E) is the semi-major axis. The coefficient k
    collapses the two sign cases of design 2.6 into one expression.
    All state functions return values in the PERICENTER frame, with
    the pericenter on +x; `beam_frame_state` rotates into the beam
    frame of design 4.3.

    The provider in orbits/analytic_orbits.py uses only the methods
    below, by name; a later potential with its own closed-form orbit
    supplies an object with the same methods.
    """
    sign: int
    energy: float
    impact: float

    @property
    def eccentricity(self):
        return float(eccentricity(self.energy, self.impact))

    @property
    def semi_major(self):
        return 1.0 / (2.0 * self.energy)

    @property
    def turning_point(self):
        return float(turning_point(self.sign, self.energy, self.impact))

    @property
    def asymptote_angle(self):
        return float(asymptote_angle(self.sign, self.energy, self.impact))

    @property
    def deflection(self):
        # Theta = pi - 2 phi_inf, eq. (2.6); signed by construction.
        return np.pi - 2.0 * self.asymptote_angle

    @property
    def coefficient(self):
        """k = sqrt((e - s) / (e + s)) in tan(phi/2) = k tanh(H/2)."""
        e = self.eccentricity
        return np.sqrt((e - self.sign) / (e + self.sign))

    # --- The anomaly parametrization, eq. (2.12) -----------------

    def radius_of_anomaly(self, anomaly):
        return self.semi_major * (self.eccentricity * np.cosh(anomaly)
                                  + self.sign)

    def time_of_anomaly(self, anomaly):
        return self.semi_major ** 1.5 * (self.eccentricity * np.sinh(anomaly)
                                         + self.sign * anomaly)

    def polar_of_anomaly(self, anomaly):
        return 2.0 * np.arctan(self.coefficient * np.tanh(anomaly / 2.0))

    def anomaly_of_time(self, time):
        """Invert t(H) by Newton's method. t(H) is monotone and nearly
        exponential in |H|, so starting from the large-|H| asymptote
        converges in a handful of steps; the iteration cap is a guard
        against a bug, not something a valid orbit reaches."""
        time = np.asarray(time, dtype=float)
        a_three_halves = self.semi_major ** 1.5
        anomaly = np.arcsinh(time / (a_three_halves * self.eccentricity))
        for _ in range(_MAX_NEWTON_ITERATIONS):
            residual = self.time_of_anomaly(anomaly) - time
            slope = a_three_halves * (self.eccentricity * np.cosh(anomaly)
                                      + self.sign)
            step = residual / slope
            anomaly = anomaly - step
            if np.all(np.abs(step) < 1e-14 * np.maximum(1.0,
                                                        np.abs(anomaly))):
                return anomaly
        raise RuntimeError('anomaly_of_time did not converge')

    def anomaly_of_radius(self, radius, outbound):
        """cosh H = (r / a - s) / e; the sign of H is the leg."""
        argument = (radius / self.semi_major - self.sign) / self.eccentricity
        if argument < 1.0:
            raise ValueError(f'radius {radius} is inside the turning '
                             f'point {self.turning_point}')
        anomaly = np.arccosh(argument)
        return anomaly if outbound else -anomaly

    def state_at_anomaly(self, anomaly):
        """In-plane (x, y, v_x, v_y) in the pericenter frame, with the
        velocity from the chain rule through H. Each returned array
        has the shape of `anomaly`."""
        anomaly = np.asarray(anomaly, dtype=float)
        e, s, k = self.eccentricity, self.sign, self.coefficient
        radius = self.radius_of_anomaly(anomaly)
        polar = self.polar_of_anomaly(anomaly)
        d_radius = self.semi_major * e * np.sinh(anomaly)
        d_time = self.semi_major ** 1.5 * (e * np.cosh(anomaly) + s)
        half_tanh = k * np.tanh(anomaly / 2.0)
        d_polar = k / np.cosh(anomaly / 2.0) ** 2 / (1.0 + half_tanh ** 2)
        radial_speed = d_radius / d_time
        polar_rate = d_polar / d_time
        cos_polar, sin_polar = np.cos(polar), np.sin(polar)
        x_position = radius * cos_polar
        y_position = radius * sin_polar
        x_velocity = radial_speed * cos_polar - radius * polar_rate * sin_polar
        y_velocity = radial_speed * sin_polar + radius * polar_rate * cos_polar
        return x_position, y_position, x_velocity, y_velocity

    # --- The beam frame, eq. (2.13) ------------------------------

    def rotation_to_beam_frame(self):
        """The rotation taking the pericenter frame to the beam frame
        of design 4.3, where the particle arrives along +y at x = +b.

        Both frames are counterclockwise (L > 0), so a pure rotation
        suffices for either sign. The inbound velocity direction in
        the pericenter frame is (-cos phi_inf, sin phi_inf); rotating
        it onto (0, 1) takes alpha = phi_inf - pi / 2 (pseudocode 2.3,
        checked numerically in both signs).
        """
        alpha = self.asymptote_angle - np.pi / 2.0
        return np.array([[np.cos(alpha), -np.sin(alpha)],
                         [np.sin(alpha), np.cos(alpha)]])

    def beam_frame_state(self, anomaly):
        """(x_p, y_p, v_x, v_y) in the beam frame, shape of `anomaly`."""
        rotation = self.rotation_to_beam_frame()
        x, y, vx, vy = self.state_at_anomaly(anomaly)
        x_p = rotation[0, 0] * x + rotation[0, 1] * y
        y_p = rotation[1, 0] * x + rotation[1, 1] * y
        vx_p = rotation[0, 0] * vx + rotation[0, 1] * vy
        vy_p = rotation[1, 0] * vx + rotation[1, 1] * vy
        return x_p, y_p, vx_p, vy_p

    def pericenter_direction(self):
        """Unit vector toward pericenter in the beam frame: the
        rotation applied to the pericenter frame's +x."""
        return self.rotation_to_beam_frame()[:, 0]

    def beam_frame_polar(self, polar):
        """Positions on the orbit at the given pericenter-frame polar
        angles, in the beam frame -- used for the trace, which is
        sampled uniformly in phi (design 4.10)."""
        polar = np.asarray(polar, dtype=float)
        radius = (2.0 * self.energy * self.impact ** 2
                  / (self.eccentricity * np.cos(polar) - self.sign))
        rotation = self.rotation_to_beam_frame()
        x, y = radius * np.cos(polar), radius * np.sin(polar)
        return (rotation[0, 0] * x + rotation[0, 1] * y,
                rotation[1, 0] * x + rotation[1, 1] * y)
