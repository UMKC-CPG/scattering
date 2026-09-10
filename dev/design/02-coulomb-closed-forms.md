# Design 2. The Coulomb Potential: Closed Forms

> **Parent:** [`../DESIGN.md`](../DESIGN.md) — design index.
> **Status:** draft; closed forms verified by
> `dev/spikes/coulomb_closed_forms.py`.
> **Serves:** G2 (real orbits), G8 (sign ambiguity), G11 (closed-form
> oracles); ARCHITECTURE A4.2 (`potentials/coulomb.py`), A4.4
> (`orbits/analytic_orbits.py`), A6.1, A6.2, A8.2.
> **Implemented by:** pseudocode section 2.

---

## 2.1 Purpose and scope

Coulomb scattering is exactly solvable, and this project leans on
that in three ways: the analytic orbit is one of the two orbit
providers (A6.2); the Rutherford deflection function and cross
section are the oracles the numerical stages are tested against
(A8.2); and the sign symmetry of the cross section is the first
inverse-scattering lesson (G8). This section collects every closed
form, in the natural units of Section 1, with its derivation sketched
far enough that a student can check it.

All results are for the potential `Ṽ(r̃) = s / r̃`, `s = ±1`, at
dimensionless energy `Ẽ > 0` and impact parameter `b̃ ≥ 0`, with the
reference length `ℓ₀ = |κ| / E_ref` of Section 1.3. The projectile
mass is `m̃ = 1`.

---

## 2.2 The orbit

The angular momentum `L̃ = sqrt(2 Ẽ) b̃` is conserved, and the standard
Binet substitution `u = 1 / r̃` turns the radial equation into a
driven harmonic oscillator in `φ`. Its solution, with `φ = 0` at
pericenter, is

```
  r̃(φ) = 2 Ẽ b̃² / (e cos φ − s)                            (2.1)

  e = sqrt(1 + (2 Ẽ b̃)²)                                    (2.2)
```

The eccentricity `e` exceeds one for every `b̃ > 0`, so every orbit
is a hyperbola; the two signs of `s` are its two branches. For `s =
+1` the center is at the *far* focus and `r̃` is finite only where
`e cos φ > 1`; for `s = −1` the center is at the near focus and the
orbit wraps around it.

**The single dimensionless group.** `Ẽ` and `b̃` enter (2.2) only as
the product `2 Ẽ b̃`. Two orbits with the same `Ẽ b̃` have the same
eccentricity, the same asymptote angles, and the same deflection;
they differ only in scale, by (2.1)'s prefactor. This is the
statement of P13 for Coulomb scattering, and it is why a single
energy sweep at fixed `b̃` and a single `b̃` sweep at fixed `Ẽ` are
the same experiment viewed differently.

---

## 2.3 Turning point

At pericenter, `φ = 0`:

```
  r̃_min = 2 Ẽ b̃² / (e − s) = (e + s) / (2 Ẽ)                (2.3)
```

The second form follows by multiplying through by `(e + s)` and
using `e² − 1 = (2 Ẽ b̃)²`; it is the one to compute with, since it
has no `0 / 0` at `b̃ = 0`. Two limits carry lessons:

- **Head-on, repulsive** (`s = +1`, `b̃ → 0`, `e → 1`): `r̃_min →
  1 / Ẽ`. In real units this is `κ / E`, the classical distance of
  closest approach, and in natural units it is exactly one at the
  reference energy. This radius is the *probe depth* of G5: at
  energy `Ẽ` no orbit of any `b̃` penetrates inside it.

- **Head-on, attractive** (`s = −1`, `b̃ → 0`): `r̃_min → 0`. The
  particle falls to the center. There is no orbit at `b̃ = 0`, and
  for small `b̃` the pericenter is at `r̃_min ≈ Ẽ b̃²` with speed
  `ṽ ≈ 1 / (sqrt(Ẽ) b̃)`, which grows without bound. The beam
  (Section 3) must therefore exclude `b̃ = 0` for `s = −1`, and the
  sampling of the orbit near pericenter (Section 4) must not assume
  a bounded speed.

A fact worth showing on screen: the product of the repulsive and
attractive turning points at the same `Ẽ` and `b̃` is

```
  r̃_min(+) · r̃_min(−) = (e² − 1) / (4 Ẽ²) = b̃²               (2.4)
```

so the impact parameter is the geometric mean of the two distances
of closest approach.

---

## 2.4 Asymptotes and the deflection angle

`r̃ → ∞` in (2.1) where `e cos φ_∞ = s`:

```
  cos φ_∞ = s / e                                            (2.5)
```

The orbit is symmetric about pericenter, so the incoming and
outgoing asymptotes lie at `φ = −φ_∞` and `φ = +φ_∞`, and the total
angle swept is `2 φ_∞`. The signed deflection, the angle between the
incoming and outgoing velocity directions, is

```
  Θ = π − 2 φ_∞                                              (2.6)
```

For `s = +1`, `φ_∞ < π / 2` and `Θ ∈ (0, π)`: the particle is
turned away. For `s = −1`, `φ_∞ > π / 2` and `Θ ∈ (−π, 0)`: it is
turned toward the center and past it. Using `arccos(−x) = π −
arccos(x)`,

```
  Θ(b̃; s = −1) = − Θ(b̃; s = +1)                              (2.7)
```

**exactly**, for every `Ẽ` and `b̃`. The two signs of the potential
deflect by equal and opposite angles.

Taking the half-angle tangent of (2.6) and using (2.5) with (2.2),

```
  tan(Θ / 2) = cot φ_∞ = s / sqrt(e² − 1) = s / (2 Ẽ b̃)      (2.8)
```

which is the Rutherford deflection function. In real units it reads
`tan(Θ / 2) = κ / (2 E b)`. Inverted for the scattering angle
`θ = |Θ|`,

```
  b̃(θ) = cot(θ / 2) / (2 Ẽ)                                 (2.9)
```

Two limits: `b̃ → 0` gives `θ → π` (back-scattering, the repulsive
head-on case), and `b̃ → ∞` gives `θ ≈ 1 / (Ẽ b̃) → 0` only as a
power law. The slow fall-off is the Coulomb tail, and it is why the
total cross section diverges (Section 2.5) and why the beam must
declare a `b̃_max` (Section 3).

---

## 2.5 Differential cross section

The general definition, for a monotonic deflection function, is

```
  dσ/dΩ = (b / sin θ) |db/dθ|                                (2.10)
```

Substituting (2.9), `db̃/dθ = −csc²(θ/2) / (4 Ẽ)`, and `sin θ = 2
sin(θ/2) cos(θ/2)`:

```
  dσ/dΩ = 1 / (16 Ẽ² sin⁴(θ/2))          [units of ℓ₀²]     (2.11)
```

In real units this is `(κ / 4E)² / sin⁴(θ/2)`, the Rutherford
formula. Three things about it matter to this project:

1. **It is independent of `s`.** By (2.7) the two signs give the
   same `θ(b̃)`, hence the same `dσ/dΩ`, hence the same detector
   counts for the same beam. This is G8: a detector cannot
   distinguish attraction from repulsion. The orbits in the scene
   look nothing alike; the histogram is identical.

2. **It diverges as `θ → 0`** like `θ⁻⁴`, and the total cross section
   `∫ (dσ/dΩ) dΩ` is infinite. Physically, every particle at every
   `b̃` is deflected by *something*, so every particle "scatters".
   Operationally, a beam of finite `b̃_max` produces no counts below
   `θ_min = 2 arctan(1 / (2 Ẽ b̃_max))`, and the detector (Section 7)
   must mark those bins as *unmeasured*, not as zero.

3. **It scales as `Ẽ⁻²`.** Doubling the energy quarters the cross
   section at every angle, uniformly. An energy sweep (G5) therefore
   moves the whole curve down without changing its shape — a fact
   that makes the sweep's *orbits* interesting (the probe depth
   changes) while its *cross sections* are merely rescaled.

---

## 2.6 Time along the orbit

Scrubbing (G4) needs the orbit against time, not against `φ`. The
standard parametrization is the hyperbolic anomaly `H`, with the
semi-major axis `ã = 1 / (2 Ẽ)` (in real units `|κ| / 2E`). With `H
= 0` at pericenter and `t̃ = 0` there:

```
  Attractive, s = −1:
    r̃(H) = ã (e cosh H − 1)
    t̃(H) = ã^{3/2} (e sinh H − H)
    tan(φ/2) = sqrt((e + 1) / (e − 1)) tanh(H/2)

  Repulsive, s = +1:                                         (2.12)
    r̃(H) = ã (e cosh H + 1)
    t̃(H) = ã^{3/2} (e sinh H + H)
    tan(φ/2) = sqrt((e − 1) / (e + 1)) tanh(H/2)
```

Both `r̃(0)` values reproduce (2.3), and as `H → ∞` both give
`r̃ / t̃ → 1 / sqrt(ã) = sqrt(2 Ẽ) = ṽ_∞`, the right asymptotic
speed. The `φ(H)` relations reproduce (2.5) in the limit.

These forms were written from memory and are **verified** by
`dev/spikes/coulomb_closed_forms.py` (see `dev/spikes/README.md`):
`r̃(φ(H))` from (2.1) agrees with `r̃(H)` to `3e-13` for both signs;
energy `½ ṽ² + s / r̃ = Ẽ` and angular momentum `r̃² dφ/dt̃ =
sqrt(2 Ẽ) b̃` hold along (2.12) to floating-point precision; and the
Rutherford cross section (2.11) equals the definition (2.10). The
same spike shows that `Θ` from (2.8) differs from a direct
integration started on the straight-line asymptote at finite `R̃` by
an amount scaling exactly as `1 / R̃` — the finite-`R_max` effect
that Section 4 owes a correction for, not an error in (2.8). The
spike is to be re-run whenever Section 1's conventions change.

**Sampling at uniform time.** Given a target `t̃`, `H` is found by
solving the transcendental `t̃(H)` in (2.12) — Newton's method
converges from `H₀ = asinh(t̃ / (ã^{3/2} e))` in a few steps, since
`t̃(H)` is monotonic and nearly exponential. `r̃` and `φ` follow. The
entry and exit times are the roots of `r̃(H) = R̃_max`, which are
explicit: `cosh H_max = (R̃_max / ã ∓ 1) / e`, the sign following
`s`. The `b̃ = 0` repulsive case is handled by (2.12) with `e = 1`
with no special casing; `φ` is then undefined and irrelevant.

---

## 2.7 The ensemble clock

Each orbit's `t̃ = 0` is its own pericenter, which is convenient for
the closed form and useless for a beam: the scene needs every
particle on one clock. Section 4 fixes the convention (the natural
candidate is that all particles cross the entry plane `z̃ = −Z̃₀`
together, so the beam is a planar pulse and a ring at fixed `b̃` stays
a ring); this section only records that a per-particle time offset
is required and is a function of `(Ẽ, b̃, s)` alone, so it is computed
once and stored with the orbit.

---

## 2.8 Invariants

Asserted in code wherever the quantity is produced, and tested:

- `e ≥ 1`, with equality only at `b̃ = 0`.
- `r̃_min > 0` for every orbit that exists; `r̃_min ≥ 1 / Ẽ` for
  `s = +1`.
- `Θ(b̃; −1) = −Θ(b̃; +1)` to floating-point precision.
- `dσ/dΩ` from (2.11) equals `(b̃ / sin θ) |db̃/dθ|` evaluated
  numerically from (2.9), to a tolerance derived from the finite
  difference used.
- Energy `½ ṽ² + s / r̃ = Ẽ` and angular momentum `r̃² dφ/dt̃ =
  sqrt(2 Ẽ) b̃` hold at every sample of the analytic orbit to
  floating-point precision.

---

## 2.9 Alternatives considered

**Integrate Coulomb orbits numerically and use the closed forms
only as tests.** This is the fallback while (2.12) is unverified, and
it remains available under A6.2. It was not chosen as the *default*
because the analytic orbit is exact at every `t̃`, so the scrubber
never shows integration error, and Principle 2 is then about the
numerical provider rather than about the scene. Once the spike
passes, the analytic provider is the default for Coulomb.

**Parametrize orbits by `φ` and sample uniformly in `φ`.** Rejected:
time is what the scrubber scrubs, and uniform-`φ` samples cluster in
time near pericenter and spread near the asymptotes, the opposite of
what smooth motion needs.

**Store the Runge–Lenz vector and reconstruct the outgoing asymptote
from any state.** Exact and elegant for Coulomb, useless for every
other potential; rejected as the general mechanism in favor of the
deflection integral of Section 5, which serves all potentials and is
what the inversion (Section 8) inverts.

---

## 2.10 References

- Goldstein, Poole, and Safko, *Classical Mechanics*, 3rd ed.,
  Sections 3.7 (the Kepler problem), 3.10 (scattering in a central
  force field), and 3.11 (transformation to laboratory coordinates,
  for FD1).
- Landau and Lifshitz, *Mechanics*, 3rd ed., Sections 15 (Kepler's
  problem, including the hyperbolic-anomaly forms for both signs)
  and 19 (Rutherford's formula).
- Rutherford, E., "The Scattering of α and β Particles by Matter and
  the Structure of the Atom," *Phil. Mag.* **21**, 669 (1911).
