# Design 4. Orbit Integration

> **Parent:** [`../DESIGN.md`](../DESIGN.md) — design index.
> **Status:** draft.
> **Serves:** G2 (real orbits), G3 (polar coordinates on screen),
> G4 (exact scrubbing), P1, P2, P5, P12; ARCHITECTURE A4.4
> (`orbits/`), A6.2 (the orbit boundary), A6.7 (the frame boundary).
> **Depends on:** Sections 1, 2, 3.
> **Implemented by:** pseudocode section 4.

---

## 4.1 Purpose and scope

This section designs how one particle's orbit is produced from
`(Ẽ, b̃)` and a potential: the equations, the integrator, where the
orbit starts and ends, how its samples are laid on a clock shared by
the whole beam, and how the planar orbit is placed in the 3D scene.
It designs both orbit providers of A6.2 — the numerical one for any
potential, the analytic one for Coulomb — behind one interface.

It does not compute the deflection function; that is Section 5, by
quadrature, and Section 4.7 says why the orbit's own exit direction
is not used for it. Storage of the result is Section 6.

---

## 4.2 The orbit-provider contract

One operation (A6.2):

```
  provide_orbit(potential, energy, impact) → Orbit
```

where `Orbit` carries, in natural units:

```
  turning_point        r̃_min
  time_offset          τ, the entry-plane crossing time (4.6)
  samples(time_grid)   (r̃, φ, ṽ_r, ṽ_φ) at requested times
  trace()              a polyline of the path, dense where curved
  exit_state           (r̃, φ, ṽ_r, ṽ_φ) at r̃ = R̃_max, outbound
  drift                max relative departure of Ẽ and L̃ (P2)
```

Every consumer sees only this. No consumer may ask which provider
produced it (P12). The driver (A4.10) chooses the provider by
capability: if the potential offers a closed-form orbit (A6.1) and
the run file has not forced `orbit_provider = "numerical"`, the
analytic provider is used; otherwise the numerical one.

---

## 4.3 Coordinates: the orbital plane

Central-force motion is planar. Each particle is integrated as a
two-degree-of-freedom problem in its own orbital plane, and the
plane is placed in the scene afterwards (4.8). The plane is spanned
by the beam axis `ẑ` and the particle's transverse direction
`ê_ρ = (cos ϕ, sin ϕ, 0)`, where `ϕ` is the beam azimuth of Section
3. In-plane coordinates are

```
  x_p   along ê_ρ    (transverse; the particle starts at x_p = b̃)
  y_p   along ẑ      (the beam direction)
```

The integrator works in `(x_p, y_p, ṽ_x, ṽ_y)`, not in `(r̃, φ)`.
Polar coordinates are what G3 displays, and they are computed from
the Cartesian state at every sample, `r̃ = sqrt(x_p² + y_p²)` and `φ`
measured from the pericenter direction (4.5). They are not what is
integrated, for the reason in 4.11.

The equations of motion in natural units (Section 1.2) are

```
  d x_p / dt̃ = ṽ_x           d ṽ_x / dt̃ = − (dṼ/dr̃) x_p / r̃
  d y_p / dt̃ = ṽ_y           d ṽ_y / dt̃ = − (dṼ/dr̃) y_p / r̃     (4.1)
```

with `dṼ/dr̃` from the potential interface (A6.1). For Coulomb,
`dṼ/dr̃ = −s / r̃²`, so the acceleration is `+s r⃗ / r̃³`: outward for
`s = +1`, inward for `s = −1`.

---

## 4.4 Where the orbit starts: the finite-`R_max` problem

The orbit is defined by its asymptotic state — a straight line at
impact parameter `b̃` with speed `ṽ_∞ = sqrt(2 Ẽ)` — but the
integrator must start somewhere finite. Starting on that straight
line at radius `R̃_max` is wrong by an amount the spike
`dev/spikes/coulomb_closed_forms.py` measured: the deflection is off
by `0.2353 / R̃_max` for `s = +1`, `Ẽ = 1`, `b̃ = 2`, scaling exactly
as `1 / R̃_max`. Two effects contribute, both first order in `1 /
R̃_max`:

1. **Wrong energy.** On the straight line at radius `R̃`, the
   particle has potential energy `Ṽ(R̃)`, so a speed of `sqrt(2 Ẽ)`
   there means total energy `Ẽ + Ṽ(R̃)`, not `Ẽ`. For Coulomb this
   alone shifts the deflection by `(dΘ/dẼ) · s / R̃`, which is half
   the measured residual in the spike's case.

2. **Wrong direction and position.** The true orbit at radius `R̃`
   has already been deflected by the part of the potential outside
   `R̃`, and its position is displaced from the asymptote.

The design uses two strategies, selected by capability (P12):

**Exact start, when the potential has a closed-form orbit.** The
potential's `asymptotic_state(Ẽ, b̃, R̃)` capability (A6.1) returns
the exact in-plane state on the true orbit at radius `R̃_max`,
inbound. For Coulomb this is (2.12) evaluated at the `H` with
`r̃(H) = R̃_max`, `H < 0`, rotated so the incoming asymptote is along
`+ẑ` at transverse offset `b̃`. Started there, the numerical orbit
has no finite-radius error at all, and its remaining error is the
integrator's. This is the default for every Coulomb run.

**Corrected start, otherwise.** For a potential without a closed
form, the particle is started on the straight asymptote at
`R̃_max` with its speed adjusted so that the *total* energy is
exactly `Ẽ`:

```
  ṽ_start = sqrt(2 (Ẽ − Ṽ(R̃_max)))                           (4.2)
```

directed along `+ẑ` at `x_p = b̃`. This removes effect 1 exactly and
leaves effect 2, which is bounded by the deflection the potential
produces outside `R̃_max`. `R̃_max` is then chosen so that bound is
below the fidelity setting `asymptote_tolerance` (Section 10): for
a potential falling faster than `1 / r̃` — Yukawa, hard sphere, a
well — the exterior deflection is negligible at modest `R̃_max`; for
a pure `1 / r̃` tail the exterior deflection is `O(b̃ / R̃_max)` and
the design refuses to run a Coulomb-tailed potential this way
without the run file saying `orbit_provider = "numerical"` and the
residual being reported on screen (P2, P14).

**The residual is disclosed either way.** The orbit's exit direction
is compared with the quadrature deflection of Section 5 for every
particle, and the largest discrepancy at each energy is on the
telemetry panel as *finite-radius residual*, separately from the
integrator drift. A student who raises `R̃_max` watches it fall as
`1 / R̃_max`, which is the spike's plot reproduced live.

---

## 4.5 The pericenter direction and `φ`

Section 2 measures `φ` from pericenter, and G3 displays `φ`. For an
analytic orbit the pericenter direction is known. For a numerical
orbit it is found after integration: the sample of minimum `r̃`,
refined by locating the root of `r⃗ · v⃗ = 0` on the dense output
between the neighboring samples. `r̃_min` is `r̃` there. The
displayed `φ` of every sample is then the in-plane angle from that
direction, signed so that the incoming asymptote sits at `φ = −φ_∞`.

For a `b̃ = 0` repulsive orbit the path is radial, `r⃗ · v⃗ = 0`
holds at the turning point as usual, and `φ` is identically zero;
the display labels it "radial" rather than showing a meaningless
angle.

---

## 4.6 The ensemble clock and the entry plane

Each orbit is a function of its own time. The scene needs one clock
(Section 2.7). The convention:

> **`t̃ = 0` is the instant the particle crosses the entry plane
> `z̃ = −Z̃₀`.** The beam is a planar pulse at `t̃ = 0`.

with `Z̃₀ = sqrt(R̃_max² − b̃_max²)`, so that every particle is inside
the sphere `r̃ ≤ R̃_max` when it is on the plane. A ring of particles
at one `b̃` shares one orbit and one crossing time, so it stays a
ring throughout the run; particles at different `b̃` differ in
crossing time by the physics (they move at different speeds at
different radii), which is correct and small.

The per-particle offset `τ` is found once, by root-finding `y_p(t) =
−Z̃₀` on the integrator's dense output (or, for the analytic
provider, on `t̃(H)`), and stored with the orbit. Every stored sample
is at scene time `t̃`, i.e. at orbit time `t̃ + τ`.

Before the particle reaches `R̃_max` inbound, and after it leaves
outbound, it is in **free flight** along its asymptote: the potential
is below the asymptote tolerance there by construction, so a straight
line at `ṽ_∞` is the orbit to that tolerance. Free flight is how a
particle is shown approaching from beyond the scene and continuing
to the detector sphere at `R̃_detect ≥ R̃_max` (Section 7) without
integrating through empty space. The outbound free flight uses the
*asymptotic* direction from Section 5, not the exit-state direction,
so the particle lands on the detector where the deflection function
says it should (4.7).

The run's time span at energy `Ẽ_k` is from `t̃ = 0` to the time the
slowest particle reaches `R̃_detect`, and the sample grid (Section 6)
is uniform on it.

---

## 4.7 Why the exit direction is not the scattering angle

The orbit provider reports an `exit_state` at `R̃_max`. Its velocity
direction is *not* what the detector or the cross section uses:

- For a numerical orbit with a corrected start, it carries the
  residual of 4.4.
- For any orbit ending at finite radius, the direction at `R̃_max`
  differs from the asymptotic direction by the exterior deflection,
  `O(b̃ / R̃_max)` for Coulomb.

The scattering angle of a particle is the asymptotic direction,
which Section 5 computes exactly by quadrature from `(Ẽ, b̃)` and
the potential. The orbit's exit direction serves two purposes only:
the finite-radius residual readout of 4.4, and the integration test
that the two agree to the expected order. Making the deflection a
property of `(Ẽ, b̃)` rather than of the integrated path is also
what keeps the inverse chain (Section 8) independent of the orbits,
as A2 requires.

---

## 4.8 Embedding the plane in the scene

Given in-plane `(x_p, y_p)` and the particle's beam azimuth `ϕ`,

```
  r⃗ = x_p ê_ρ(ϕ) + y_p ẑ
    = (x_p cos ϕ, x_p sin ϕ, y_p)                              (4.3)
```

and velocities likewise. Repulsion pushes `x_p` more positive
(outward, away from the axis); attraction pulls it negative — the
particle crosses the beam axis and leaves on the *opposite* side.
The outgoing direction of a particle deflected by signed `Θ` is
therefore

```
  n̂_out = (sin Θ cos ϕ, sin Θ sin ϕ, cos Θ)                    (4.4)
```

which for `Θ < 0` points at azimuth `ϕ + π`. This is visible in the
scene: an attractive ring scatters to a cone on the far side of the
axis, a repulsive one to the near side. A detector that bins only
`θ = |Θ|` (Section 7) cannot see the difference, which is G8 in its
geometric form.

`core/frames.py` (A6.7) sits between (4.4) and any consumer. In the
first version it is the identity; with recoil it will carry the
CM-to-lab transform of every direction and energy.

---

## 4.9 Integrators

Selectable per run (`integrator` in the fidelity table, Section 10):

| Name | Method | Role |
| --- | --- | --- |
| `dop853` (default) | Dormand–Prince 8(5,3), adaptive | Production |
| `rk45` | Dormand–Prince 4(5), adaptive | Cheaper, coarser |
| `verlet` | Velocity Verlet, fixed step | Teaching: visible drift |

The adaptive integrators are `scipy.integrate.solve_ivp` with
`dense_output=True`, which is what makes the entry-plane crossing
(4.6), the pericenter (4.5), and the exit at `R̃_max` locatable to
tolerance rather than to a sample spacing, and what lets samples be
drawn at any time grid afterwards. Default tolerances `rtol = 1e-10`,
`atol = 1e-12` are set so that the conservation drift over a
scattering pass is far below anything visible, and they are fidelity
settings, not constants.

`verlet` exists for P2: it is second order and symplectic, its
energy error is visibly bounded rather than secular, and a student
who selects it with a coarse step *sees* the drift readout move —
which is the point. Its fixed step makes the entry-plane crossing
and pericenter interpolated rather than located, and the display
says so.

A scattering pass is a finite, non-stiff problem, so nothing more
elaborate is warranted; the integrator interface is a narrow
array-in, array-out seam so that FD5's compiled kernel can replace
it.

**Termination.** The integration stops at the event `r̃ = R̃_max`
crossed outbound (`scipy` event with `direction = +1`), which is
exact to tolerance. A safety cap of `t̃_cap = 20 (R̃_max / ṽ_∞)` on the
span guards against a bound orbit that never exits — impossible for
`Ẽ > 0` in a potential that vanishes at infinity, and therefore a
sign of a bad potential implementation, reported as such.

---

## 4.10 Samples and traces are different products

An orbit yields two things for display, and they have different
sampling needs:

**Samples** are the particle's state on the uniform scene-time grid
of Section 6, for the scrubber. Uniform in time is what scrubbing
requires, and it is what makes the ensemble's motion honest: a
particle that is fast near pericenter *should* jump between frames.

**The trace** is the polyline of the path, drawn once. Uniform-time
points cut corners exactly where the path curves most, so the trace
is sampled separately: from dense output at points chosen so that
the turning angle between consecutive segments is below
`trace_angle` (a fidelity setting, default about 2°), with a cap on
point count. For the analytic provider the trace is uniform in `φ`,
which places points by angle around the center and is therefore
already dense at pericenter.

For an attractive orbit at small `b̃`, the pericenter speed grows as
`1 / (sqrt(Ẽ) b̃)` (Section 2.3) and the path turns through nearly
`2 φ_∞ → 2π` in a tiny region; the sample grid will show the particle
vanishing from one side and reappearing on the other, and the trace
must show the loop. Both are correct. Neither may assume a bounded
speed.

---

## 4.11 Alternatives considered

**Integrate in polar coordinates `(r̃, ṽ_r)` with `φ` by quadrature.**
Exposes the effective potential and the conserved `L̃` directly,
which is attractive pedagogically. Rejected for the integrator
because `dφ/dt̃ = L̃ / r̃²` is stiff at the small-`b̃` attractive
pericenter and the radial equation has a coordinate singularity at
`r̃ = 0`; Cartesian in-plane integration has neither. The effective
potential is still drawn (Section 11) from the stored state.

**Integrate in 3D.** Rejected: central-force motion is exactly
planar, so a 3D integration spends three extra state components
accumulating error in a direction the physics forbids motion in.
The planar problem is smaller, more accurate, and puts `(r̃, φ)`
one step from the state.

**Use the orbit's exit direction as the scattering angle.** Rejected;
see 4.7. It carries a `1 / R̃_max` error that the quadrature does
not, and it would tie the inverse chain to the orbits.

**Start every orbit on the straight asymptote and correct
afterwards.** Rejected in favor of the exact start where a closed
form exists; a correction applied after the fact is a second
approximation stacked on the first, and P2 prefers no error to a
disclosed one where no error is available.

**A single sampling for both the moving particle and its trace.**
Rejected; see 4.10.

---

## 4.12 Invariants and tests

- Energy `½ ṽ² + Ṽ(r̃)` and angular momentum `x_p ṽ_y − y_p ṽ_x`
  at every sample equal `Ẽ` and `sqrt(2 Ẽ) b̃` to a tolerance derived
  from the integrator's `rtol` and the span; the drift is stored,
  not merely asserted (P2).
- `r̃ ≥ r̃_min` at every sample, and `r̃_min` agrees with the closed
  form (2.3) for Coulomb to the same tolerance.
- **Time-reversal symmetry.** For every orbit, `r̃(t_p + τ) = r̃(t_p −
  τ)` about the pericenter time `t_p`, to tolerance. An integrator
  or an event handler that breaks this is wrong in a way
  conservation checks do not catch.
- **Provider agreement.** The numerical provider on Coulomb, with
  the exact start, reproduces the analytic provider's samples to
  the integrator tolerance. This certifies A6.2.
- **Finite-radius scaling.** With the *corrected* start forced on
  Coulomb, the exit-direction residual against Section 5's
  quadrature scales as `1 / R̃_max` across a doubling sequence, and
  with the *exact* start it is at integrator tolerance for every
  `R̃_max`. This is the spike's measurement made a regression test.
- Every particle's entry-plane crossing exists and is unique;
  every orbit terminates by the exit event, never by the cap.
