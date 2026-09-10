"""Time-stepping schemes for one orbit (pseudocode 4.6, design 4.9).

Three are offered, selected per run:

- dop853: Dormand-Prince 8(5,3), adaptive, dense output. Production.
- rk45: Dormand-Prince 4(5), adaptive, dense output. Cheaper.
- verlet: velocity Verlet, fixed step, second order, symplectic. A
  teaching option: its energy error is visibly bounded rather than
  secular, and a coarse step makes the drift readout move (P2).

The adaptive schemes are scipy's `solve_ivp` with `dense_output`, which is what
lets the entry-plane crossing, the pericenter, and the exit be LOCATED to
tolerance rather than to a sample spacing. Every scheme returns an object
exposing `.t` (its own step times) and `.sol(t)` (state at any time), and
nothing else, so the provider is indifferent to which ran.

Integration stops at the event r = R_max crossed OUTWARD. A safety cap on the
span guards against an orbit that never exits, which is impossible for E > 0 in
a potential that vanishes at infinity and therefore a sign of a bad potential
implementation.

Attribution: this module is part of the scattering teaching tool.
"""

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicHermiteSpline

# The span cap, as a multiple of the free-flight crossing time of the sphere
# (design 4.9).
_SPAN_CAP_FACTOR = 20.0

_SCIPY_METHODS = {'dop853': 'DOP853', 'rk45': 'RK45'}


def exit_event(r_max):
    """The terminal event 'r crosses r_max going outward'."""

    def event(_time, state):
        return np.hypot(state[0], state[1]) - r_max

    event.terminal = True
    event.direction = +1
    return event


class DenseSolution:
    """Adapter over a `solve_ivp` result: `.t`, `.sol(t)`, `.t_exit`."""

    def __init__(self, result, t_exit):
        self._result = result
        self.t = result.t
        self.t_exit = float(t_exit)

    def sol(self, times):
        """State (4, n) at the requested times, via dense output."""
        return self._result.sol(np.asarray(times, dtype=float))


class HermiteSolution:
    """Adapter over fixed-step samples: `.sol(t)` is a per-interval
    cubic Hermite using the stored velocities as slopes for the positions, and a
    plain cubic through the velocities. Good enough for locating the plane
    crossing and pericenter between steps,
    and the display says 'interpolated' when this is in use."""

    def __init__(self, times, states, t_exit):
        self.t = np.asarray(times, dtype=float)
        states = np.asarray(states, dtype=float)      # (n, 4)
        self.t_exit = float(t_exit)
        self._position = CubicHermiteSpline(self.t, states[:, :2],
                                            states[:, 2:], axis=0)
        self._velocity = CubicHermiteSpline(self.t, states[:, 2:],
            np.gradient(states[:, 2:], self.t, axis=0), axis=0)

    def sol(self, times):
        times = np.asarray(times, dtype=float)
        position = self._position(times)
        velocity = self._velocity(times)
        return np.concatenate([position, velocity], axis=-1).T


def integrate(right_hand_side, initial_state, settings, stop):
    """Integrate from `initial_state` until `stop` fires (pseudocode
    4.6). `settings` carries integrator, rtol, atol, step, r_max."""
    speed = np.hypot(initial_state[2], initial_state[3])
    t_cap = _SPAN_CAP_FACTOR * settings.r_max / speed
    if settings.integrator in _SCIPY_METHODS:
        result = solve_ivp(right_hand_side, (0.0, t_cap), initial_state,
            method=_SCIPY_METHODS[settings.integrator], rtol=settings.rtol,
            atol=settings.atol, dense_output=True, events=stop)
        if result.status != 1:
            raise RuntimeError('orbit did not exit R_max before the span '
                               'cap: is the potential implemented '
                               'correctly?')
        return DenseSolution(result, result.t_events[0][0])
    if settings.integrator == 'verlet':
        return integrate_verlet(right_hand_side, initial_state, settings,
                                stop, t_cap)
    raise ValueError(f'unknown integrator {settings.integrator!r}')


def integrate_verlet(right_hand_side, initial_state, settings, stop,
                     t_cap):
    """Velocity Verlet at fixed step `settings.step` until the exit
    event, then linear interpolation of r across the last step for
    the exit time (pseudocode 4.6)."""
    step = settings.step
    if not step or step <= 0.0:
        raise ValueError('verlet needs a positive [fidelity].step')
    x_position, y_position, x_velocity, y_velocity = initial_state
    _, _, x_accel, y_accel = right_hand_side(0.0, initial_state)
    times, states = [0.0], [tuple(initial_state)]
    time = 0.0
    previous_radius = np.hypot(x_position, y_position)
    while time < t_cap:
        x_position += x_velocity * step + 0.5 * x_accel * step ** 2
        y_position += y_velocity * step + 0.5 * y_accel * step ** 2
        _, _, x_accel_new, y_accel_new = right_hand_side(
            time + step, (x_position, y_position, x_velocity, y_velocity))
        x_velocity += 0.5 * (x_accel + x_accel_new) * step
        y_velocity += 0.5 * (y_accel + y_accel_new) * step
        x_accel, y_accel = x_accel_new, y_accel_new
        time += step
        state = (x_position, y_position, x_velocity, y_velocity)
        times.append(time)
        states.append(state)
        radius = np.hypot(x_position, y_position)
        if stop(time, state) > 0.0 and previous_radius <= settings.r_max:
            # Linear interpolation of r across the last step.
            fraction = ((settings.r_max - previous_radius)
                        / (radius - previous_radius))
            t_exit = time - step + fraction * step
            return HermiteSolution(times, states, t_exit)
        previous_radius = radius
    raise RuntimeError('orbit did not exit R_max before the span cap')
