# Pseudocode 4. Orbit Providers

> **Parent:** [`../PSEUDOCODE.md`](../PSEUDOCODE.md) — index.
> **Specifies:** design section 4,
> [`../design/04-orbit-integration.md`](../design/04-orbit-integration.md).
> **Governs:** `src/scattering/orbits/orbit_provider.py`,
> `src/scattering/orbits/equations_of_motion.py`,
> `src/scattering/orbits/integrators.py`,
> `src/scattering/orbits/analytic_orbits.py`,
> `src/scattering/orbits/turning_point.py`,
> `src/scattering/orbits/embedding.py`.
> **Status:** draft.

---

## 4.1 Records and the provider contract (D4.2)

All in-plane quantities are in the **beam frame** of D4.3: `x_p`
transverse (the particle starts at `+b̃`), `y_p` along the beam.

```
record OrbitSettings:               # from [fidelity] (P10)
    r_max               R~_max
    integrator          "dop853" | "rk45" | "verlet"
    rtol, atol          floats
    step                float, verlet only
    asymptote_tolerance float
    trace_angle         radians
    trace_points_max    int
    entry_plane_z       Z~_0 = sqrt(r_max^2 - b_max^2)        (D4.6)

record Orbit:
    energy, impact
    turning_point       r~_min
    pericenter_time     t_p, orbit time of pericenter
    pericenter_dir      unit vector in the plane
    time_offset         tau: orbit time at which y_p = -Z~_0   (D4.6)
    entry_time          orbit time at which r = R~_max inbound
    exit_time           orbit time at which r = R~_max outbound
    exit_state          (x_p, y_p, v_x, v_y) at exit_time
    drift               (energy_drift, angmom_drift)  max relative
    provider_name       "analytic" | "numerical"
    # Callables, evaluated lazily:
    state_at(orbit_times: array) -> array (n, 4)
    trace() -> array (m, 2)         in-plane polyline

protocol OrbitProvider:
    provide(potential, energy, impact, settings) -> Orbit

function choose_provider(potential, settings) -> OrbitProvider:
    forced = settings.orbit_provider   # "auto" | "analytic" | "numerical"
    if forced == "analytic":
        if not potential.has_closed_form_orbit: fail "no closed form"
        return AnalyticProvider()
    if forced == "numerical":  return NumericalProvider()
    return AnalyticProvider() if potential.has_closed_form_orbit \
           else NumericalProvider()
```

**Orbit time vs scene time.** Every `Orbit` method takes *orbit
time*, whose zero is the provider's convenience (pericenter for the
analytic one, the start of integration for the numerical one).
Scene time `t̃` (D4.6) is `orbit_time − time_offset`; the store
(P6) does that subtraction and nothing below it knows about scene
time.

---

## 4.2 The analytic provider

```
class AnalyticProvider:
    provide(potential, energy, impact, settings):
        A = potential.closed_form_orbit(energy, impact)     # P2.3
        R = pericenter_to_beam_rotation(A)                  # P2 (2.13)
        H_in  = anomaly_of_radius(A, settings.r_max, outbound=False)
        H_out = -H_in
        entry_time = time_of_anomaly(A, H_in)
        exit_time  = time_of_anomaly(A, H_out)

        # Entry-plane crossing: solve y_p(H) = -Z_0 for H in [H_in, 0]
        # (y_p is monotone there). Bisect on H, then Newton-polish.
        def y_of(H): return (R @ position of state_at_anomaly(A, H)).y
        H_tau = root of (y_of(H) + settings.entry_plane_z) on [H_in, 0]
        tau = time_of_anomaly(A, H_tau)

        state_at(times):
            H = anomaly_of_time(A, t) for each t          # P2.3, vectorized
            return rotate(R, state_at_anomaly(A, H))
        trace():
            # Uniform in phi between the asymptotes, clipped to r <= r_max;
            # dense at pericenter by construction (D4.10).
            phi = linspace(-phi_in, +phi_in, m) where phi_in is the
                  polar angle at H_in and m = min(trace_points_max,
                  ceil(2 phi_in / trace_angle))
            r = 2 E b^2 / (e cos phi - s)                        (2.1)
            return rotate(R, (r cos phi, r sin phi))
        return Orbit(... turning_point = A.r_min, pericenter_time = 0,
                     pericenter_dir = R @ (1, 0), drift = (0, 0),
                     provider_name = "analytic", ...)
```

The drift is reported as zero and the panel says *"closed-form
orbit"* (D9.3); the residuals are still computed by the monitor
(P9) from the stored samples, which is the test of this provider.

---

## 4.3 The numerical provider

```
class NumericalProvider:
    provide(potential, energy, impact, settings):
        (x0, y0, vx0, vy0) = initial_state(potential, energy, impact,
                                           settings)             # 4.4
        rhs = equations_of_motion(potential)                     # 4.5
        sol = integrate(rhs, state0 = (x0, y0, vx0, vy0),
                        settings, stop = exit_event(settings.r_max))  # 4.6
        # sol.t spans [0, t_exit]; sol.sol(t) is dense output.

        # Pericenter: minimum r on the dense output. Bracket by the
        # sample of minimum r, then find the root of r.v = 0.
        t_p = root of (x*vx + y*vy) near argmin over sol.t of r
        (xp, yp, ...) = sol.sol(t_p)
        r_min = hypot(xp, yp)
        pericenter_dir = (xp, yp) / r_min

        tau = root of (sol.sol(t).y + settings.entry_plane_z) on [0, t_p]

        # Conservation drift along the integrated span (P9.3).
        samples = sol.sol(linspace(0, t_exit, 512))
        drift = (max |energy(samples) - energy| / energy,
                 max |angmom(samples) - sqrt(2 energy) impact|
                     / (sqrt(2 energy) impact  or 1 if impact == 0))

        state_at(times): return sol.sol(times).T   # (n, 4)
        trace(): return adaptive_trace(sol, settings)            # 4.7
        return Orbit(energy, impact, r_min, t_p, pericenter_dir, tau,
                     entry_time = 0, exit_time = t_exit,
                     exit_state = sol.sol(t_exit), drift, "numerical",
                     state_at, trace)
```

---

## 4.4 The initial state (D4.4)

```
function initial_state(potential, energy, impact, settings):
    R = settings.r_max
    if potential.has_closed_form_orbit:
        # Exact start on the true orbit, inbound at r = R.
        return potential.asymptotic_state(energy, impact, R)   # P2.3
    # Corrected start: on the straight asymptote, speed fixed so
    # that the TOTAL energy is exactly `energy` (4.2).
    y0 = -sqrt(R^2 - impact^2)
    v  = sqrt(2 * (energy - potential.value(R)))
    if not (energy > potential.value(R)):
        fail "R_max is inside the classically forbidden region"
    # Exterior deflection bound (D4.4): refuse a Coulomb-like tail
    # unless the run file forced the numerical provider.
    if (potential.tail_exponent() <= 1
            and settings.orbit_provider != "numerical"):
        fail "1/r tail with no closed form: set orbit_provider =
              'numerical' to accept the finite-radius residual"
    return (impact, y0, 0.0, v)
```

`tail_exponent()` is a small addition to the potential interface
(P2.1): the power `n` in `V ~ r^{-n}` at large `r`, used only for
this check and for P8's tail model.

---

## 4.5 Equations of motion (D4.3)

```
function equations_of_motion(potential) -> rhs:
    def rhs(t, state):
        (x, y, vx, vy) = state
        r = hypot(x, y)
        a = -potential.derivative(r) / r      # radial accel / r
        return (vx, vy, a * x, a * y)                             (4.1)
    return rhs
```

For Coulomb `derivative(r) = -s / r²`, so `a = s / r³` and the
acceleration is `+s r⃗ / r³`.

---

## 4.6 Integrators (D4.9)

```
function exit_event(r_max):
    def event(t, state): return hypot(state.x, state.y) - r_max
    event.terminal  = True
    event.direction = +1                  # crossing outward only
    return event

function integrate(rhs, state0, settings, stop):
    speed = hypot(state0.vx, state0.vy)
    t_cap = 20 * settings.r_max / speed                      (D4.9)
    if settings.integrator in ("dop853", "rk45"):
        sol = scipy.integrate.solve_ivp(
                  rhs, (0, t_cap), state0,
                  method = settings.integrator.upper(),   # "DOP853"/"RK45"
                  rtol = settings.rtol, atol = settings.atol,
                  dense_output = True, events = stop)
        if sol.status != 1:               # 1 = terminated by the event
            fail "orbit did not exit R_max before the cap: bad potential?"
        t_exit = sol.t_events[0][0]
        return DenseSolution(sol, t_exit)
    if settings.integrator == "verlet":
        return integrate_verlet(rhs, state0, settings, stop, t_cap)

function integrate_verlet(rhs, state0, settings, stop, t_cap):
    h = settings.step
    states, times = [state0], [0.0]
    (x, y, vx, vy) = state0
    (_, _, ax, ay) = rhs(0, state0)
    t = 0
    while t < t_cap:
        # Velocity Verlet, second order, symplectic.
        x  += vx * h + 0.5 * ax * h^2
        y  += vy * h + 0.5 * ay * h^2
        (_, _, ax_new, ay_new) = rhs(t + h, (x, y, vx, vy))
        vx += 0.5 * (ax + ax_new) * h
        vy += 0.5 * (ay + ay_new) * h
        ax, ay = ax_new, ay_new
        t += h
        states.append((x, y, vx, vy)); times.append(t)
        if t > 0 and stop(t, (x, y, vx, vy)) > 0 and
           hypot(states[-2].x, states[-2].y) <= settings.r_max:
            break
    else: fail "orbit did not exit R_max before the cap"
    # Exit time by linear interpolation of r across the last step;
    # dense output by cubic Hermite on (states, times). The display
    # says "interpolated" for the pericenter and plane crossing.
    return HermiteSolution(times, states, t_exit_interpolated)
```

`DenseSolution.sol(t)` wraps `solve_ivp`'s `sol.sol`;
`HermiteSolution.sol(t)` is a per-interval cubic Hermite using the
stored velocities as slopes. Both expose `.t` (sample times) and
`.sol(t)` and nothing else, so the provider is indifferent.

---

## 4.7 The adaptive trace (D4.10)

```
function adaptive_trace(sol, settings) -> array (m, 2):
    # Start from the integrator's own step points, which are already
    # denser where the motion is faster, then refine any segment
    # whose turning angle exceeds trace_angle by bisection on the
    # dense output, until the cap.
    t_points = list(sol.t)
    repeat:
        P = positions sol.sol(t_points)[:2]
        angles = turning angle between consecutive segments of P
        bad = indices where angles > settings.trace_angle
        if bad is empty or len(t_points) >= settings.trace_points_max:
            break
        insert midpoints of the segments adjacent to each bad vertex
    return positions at t_points
```

---

## 4.8 Embedding (D4.8)

```
function embed(x_p, y_p, azimuth) -> (x, y, z):
    return (x_p * cos(azimuth), x_p * sin(azimuth), y_p)           (4.3)

function out_direction(deflection, azimuth) -> unit vector:
    return (sin(deflection) * cos(azimuth),
            sin(deflection) * sin(azimuth),
            cos(deflection))                                     (4.4)
```

Both are pure array functions; `embed` applies to positions and to
velocities alike. `core/frames.py` sits after them and is the
identity in v1 (A6.7).

---

## 4.9 The turning-point module

`turning_point.py` holds the general root-of-`g` computation of
D5.2 and P5.2 (it is shared by the deflection stage) and the
per-orbit comparison:

```
function turning_point_from_g(potential, energy, impact) -> float:
    # See P5.2.
function compare_turning_points(orbit, r_min_q) -> float:
    return |orbit.turning_point - r_min_q| / r_min_q
```

---

## 4.10 Verification

`tests/unit/test_orbits.py` and `tests/integration/test_providers.py`:

- **Provider agreement (A6.2).** On Coulomb, both signs, five
  `(E, b)` cases: `NumericalProvider` with `dop853` at default
  tolerance reproduces `AnalyticProvider.state_at` on a common time
  grid to `1e-8` in position and velocity; turning points to `1e-9`.
- **Conservation.** `drift` from the numerical provider is below
  `1e-8` (`dop853`), and the analytic provider's samples satisfy
  the conservation identities to `1e-13`.
- **Time reversal.** `r(t_p + τ) = r(t_p − τ)` to `1e-9` for
  `τ` up to the entry time.
- **Exact start.** With the closed-form start, the angle between
  the exit velocity and `out_direction(closed_form_deflection)` is
  at integrator tolerance for `R_max` in `{20, 40, 80}`.
- **Corrected start.** With `orbit_provider = "numerical"` forced
  and the corrected start used (test hook that disables the closed
  form), the same angle scales as `1 / R_max` across the doubling
  sequence, with `R_max × angle` constant to 5 %.
- **Entry plane.** `state_at(tau).y == -Z_0` to `1e-10`; every
  particle in a beam has exactly one crossing.
- **Exit.** `hypot(exit_state.x, exit_state.y) == r_max` to the
  event tolerance; the integration status is "event", never "cap".
- **Verlet order.** Energy drift at steps `h, h/2, h/4` scales as
  `h²` (ratio 4 ± 10 %).
- **Trace.** Every consecutive turning angle in `trace()` is below
  `trace_angle`, or the point cap was hit.
- **Side of the axis.** For `s = +1` the exit `x_p > 0`; for
  `s = −1`, `x_p < 0` (D4.8), both providers.
- **Head-on.** `b = 0`, `s = +1`: the numerical provider runs,
  `x_p` stays at `0` to `1e-12`, `r_min = 1 / E` to `1e-9`, exit
  velocity is `−ẑ`.
