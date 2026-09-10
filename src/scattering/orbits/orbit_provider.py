"""The orbit-provider contract and its two implementations
(pseudocode 4.1-4.4, design 4.2).

One operation: given a potential, an energy, and an impact
parameter, return an `Orbit`. `AnalyticProvider` uses a potential's
closed-form orbit; `NumericalProvider` integrates the equations of
motion. Every consumer sees only the `Orbit` and may not ask which
provider produced it (VISION P12). The driver chooses by capability.

Orbit time versus scene time: every `Orbit` method takes ORBIT time,
whose zero is the provider's convenience (pericenter for the
analytic provider, the start of integration for the numerical one).
Scene time, on which the whole beam is one planar pulse at t = 0, is
orbit time minus `time_offset`; the results store does that
subtraction and nothing here knows about scene time (design 4.6).

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
from scipy.optimize import brentq

from scattering.core.natural_units import (angular_momentum,
                                           asymptotic_speed, total_energy)
from scattering.orbits.equations_of_motion import equations_of_motion
from scattering.orbits.integrators import exit_event, integrate

# Number of dense-output samples on which the numerical provider
# measures its conservation drift (pseudocode 4.3).
_DRIFT_SAMPLES = 512


@dataclass(frozen=True)
class OrbitSettings:
    """The fidelity settings the providers need (pseudocode 4.1).
    `entry_plane_z` is Z_0 = r_max, the plane tangent to the sphere on
    the beam's side (design 4.6); the driver sets it."""
    r_max: float
    integrator: str = 'dop853'
    rtol: float = 1e-10
    atol: float = 1e-12
    step: Optional[float] = None
    asymptote_tolerance: float = 1e-6
    trace_angle: float = np.radians(2.0)
    trace_points_max: int = 2000
    orbit_provider: str = 'auto'
    entry_plane_z: float = 0.0


@dataclass(frozen=True)
class Orbit:
    """One particle's orbit (pseudocode 4.1). Times are orbit times.

    `state_at(times)` returns an (n, 4) array of (x_p, y_p, v_x, v_y)
    in the beam frame; `trace()` returns an (m, 2) polyline of the
    path, dense where it curves (design 4.10).
    """
    energy: float
    impact: float
    turning_point: float
    pericenter_time: float
    pericenter_direction: np.ndarray
    time_offset: float
    entry_time: float
    exit_time: float
    exit_state: np.ndarray
    energy_drift: float
    angmom_drift: float
    provider_name: str
    state_at: Callable
    trace: Callable


class AnalyticProvider:
    """Orbits from a potential's closed form (pseudocode 4.2)."""

    name = 'analytic'

    def provide(self, potential, energy, impact, settings):
        analytic = potential.closed_form_orbit(energy, impact)
        anomaly_in = analytic.anomaly_of_radius(settings.r_max,
                                                outbound=False)
        anomaly_out = -anomaly_in
        entry_time = float(analytic.time_of_anomaly(anomaly_in))
        exit_time = float(analytic.time_of_anomaly(anomaly_out))

        def state_at(times):
            anomaly = analytic.anomaly_of_time(np.asarray(times, float))
            return np.stack(analytic.beam_frame_state(anomaly), axis=-1)

        time_offset = entry_plane_time(state_at([entry_time])[0],
                                       entry_time, settings, energy)

        def trace():
            # Uniform in the pericenter-frame polar angle between the
            # entry and exit, which is dense at pericenter by
            # construction (design 4.10). The head-on orbit is a
            # radial line in and out, for which r(phi) is undefined.
            if impact == 0.0:
                return np.array([[0.0, -settings.r_max],
                                 [0.0, -analytic.turning_point]])
            polar_in = float(analytic.polar_of_anomaly(anomaly_in))
            count = int(min(settings.trace_points_max,
                            max(16, np.ceil(2.0 * abs(polar_in)
                                            / settings.trace_angle))))
            polar = np.linspace(polar_in, -polar_in, count)
            return np.stack(analytic.beam_frame_polar(polar), axis=-1)

        exit_state = state_at([exit_time])[0]
        return Orbit(float(energy), float(impact), analytic.turning_point,
                     0.0, analytic.pericenter_direction(), time_offset,
                     entry_time, exit_time, exit_state, 0.0, 0.0,
                     self.name, state_at, trace)


class NumericalProvider:
    """Orbits by integrating the equations of motion (pseudocode
    4.3), from an exact start where the potential offers one and a
    corrected straight-line start otherwise (design 4.4)."""

    name = 'numerical'

    def provide(self, potential, energy, impact, settings):
        initial = initial_state(potential, energy, impact, settings)
        solution = integrate(equations_of_motion(potential), initial,
                             settings, exit_event(settings.r_max))
        exit_time = solution.t_exit

        def state_at(times):
            return solution.sol(times).T

        # Pericenter: the step of minimum r brackets the root of the
        # radial velocity r . v, refined on the dense output.
        pericenter_time = _locate_pericenter(solution, exit_time)
        x_p, y_p = state_at([pericenter_time])[0, :2]
        r_min = float(np.hypot(x_p, y_p))
        pericenter_direction = np.array([x_p, y_p]) / r_min

        time_offset = entry_plane_time(initial, 0.0, settings, energy)

        samples = state_at(np.linspace(0.0, exit_time, _DRIFT_SAMPLES))
        energy_drift, angmom_drift = _conservation_drift(
            potential, energy, impact, samples)

        def trace():
            return adaptive_trace(solution, settings)

        return Orbit(float(energy), float(impact), r_min, pericenter_time,
                     pericenter_direction, time_offset, 0.0, exit_time,
                     state_at([exit_time])[0], energy_drift, angmom_drift,
                     self.name, state_at, trace)


def choose_provider(potential, settings):
    """By capability, unless the run file forces one (pseudocode
    4.1)."""
    forced = settings.orbit_provider
    if forced == 'analytic':
        if not potential.has_closed_form_orbit:
            raise ValueError(f'{potential.describe()} has no closed-form '
                             f'orbit; use orbit_provider = "numerical"')
        return AnalyticProvider()
    if forced == 'numerical':
        return NumericalProvider()
    if forced != 'auto':
        raise ValueError(f'unknown orbit_provider {forced!r}')
    return AnalyticProvider() if potential.has_closed_form_orbit \
        else NumericalProvider()


def initial_state(potential, energy, impact, settings,
                  force_corrected=False):
    """Where the numerical integration starts (pseudocode 4.4).

    Exact start: on the true orbit at r = R_max, when the potential
    has a closed form -- no finite-radius error at all. Corrected
    start otherwise: on the straight asymptote with the speed set so
    the TOTAL energy is exactly E, eq. (4.2); this removes the
    wrong-energy half of the finite-radius effect and leaves the
    exterior deflection, which the residual readout discloses.
    `force_corrected` is a test hook for measuring that residual.
    """
    r_max = settings.r_max
    if potential.has_closed_form_orbit and not force_corrected:
        return np.array(potential.asymptotic_state(energy, impact, r_max),
                        dtype=float)
    potential_at_edge = float(potential.value(r_max))
    if not energy > potential_at_edge:
        raise ValueError('R_max lies inside the classically forbidden '
                         'region for this energy')
    if (potential.tail_exponent() <= 1
            and settings.orbit_provider != 'numerical'
            and not force_corrected):
        raise ValueError('a 1/r tail with no closed-form orbit needs '
                         'orbit_provider = "numerical" to accept the '
                         'finite-radius residual (design 4.4)')
    y_start = -np.sqrt(r_max ** 2 - impact ** 2)
    speed = np.sqrt(2.0 * (energy - potential_at_edge))
    return np.array([impact, y_start, 0.0, speed], dtype=float)


def entry_plane_time(entry_state, entry_time, settings, energy):
    """The orbit time at which the particle crosses the entry plane
    y_p = -Z_0 (design 4.6, eq. 4.5).

    With the plane tangent to the sphere (Z_0 = R_max), every
    particle with b > 0 is still outside the sphere when it crosses,
    so the crossing lies on the straight inbound leg the scene draws
    and is an extrapolation from the entry state at the asymptotic
    speed -- exact for that leg, and needing no root-find. The
    head-on particle crosses exactly as it enters.
    """
    y_entry = entry_state[1]
    return entry_time - (y_entry + settings.entry_plane_z) \
        / asymptotic_speed(energy)


def _locate_pericenter(solution, exit_time):
    """Root of r . v (the radial velocity) bracketed by the integrator
    step of minimum radius."""
    states = solution.sol(solution.t)
    radii = np.hypot(states[0], states[1])
    index = int(np.argmin(radii))
    low = solution.t[max(index - 1, 0)]
    high = solution.t[min(index + 1, len(solution.t) - 1)]

    def radial_velocity(time):
        x_p, y_p, v_x, v_y = solution.sol(time)
        return x_p * v_x + y_p * v_y

    if radial_velocity(low) * radial_velocity(high) > 0.0:
        # The minimum is at an end of the bracket (a head-on orbit
        # sampled exactly at its turning point, say); take it.
        return float(solution.t[index])
    return float(brentq(radial_velocity, low, high, xtol=1e-13))


def _conservation_drift(potential, energy, impact, samples):
    """Max relative departure of E and L along the samples
    (pseudocode 4.3). For b = 0, L = 0 and the departure is absolute."""
    radius = np.hypot(samples[:, 0], samples[:, 1])
    speed = np.hypot(samples[:, 2], samples[:, 3])
    total = total_energy(speed, potential.value(radius))
    energy_drift = float(np.max(np.abs(total - energy)) / energy)
    angmom = samples[:, 0] * samples[:, 3] - samples[:, 1] * samples[:, 2]
    expected = angular_momentum(energy, impact)
    scale = expected if expected > 0.0 else 1.0
    angmom_drift = float(np.max(np.abs(angmom - expected)) / scale)
    return energy_drift, angmom_drift


def adaptive_trace(solution, settings):
    """A polyline of the path from dense output, refined by bisection
    wherever the turning angle between consecutive segments exceeds
    `trace_angle`, up to the point cap (pseudocode 4.7)."""
    times = list(np.asarray(solution.t, dtype=float))
    while True:
        positions = solution.sol(np.array(times))[:2].T
        segments = np.diff(positions, axis=0)
        lengths = np.linalg.norm(segments, axis=1)
        unit = segments / np.where(lengths > 0, lengths, 1.0)[:, None]
        cosines = np.clip(np.sum(unit[:-1] * unit[1:], axis=1), -1.0, 1.0)
        angles = np.arccos(cosines)
        bad = np.nonzero(angles > settings.trace_angle)[0]
        if bad.size == 0 or len(times) >= settings.trace_points_max:
            return positions
        # Refine the two segments adjacent to each bad vertex.
        new_times = set()
        for vertex in bad:
            for segment in (vertex, vertex + 1):
                new_times.add(0.5 * (times[segment] + times[segment + 1]))
        times = sorted(set(times) | new_times)
