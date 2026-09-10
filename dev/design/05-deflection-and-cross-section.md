# Design 5. The Deflection Function and the Cross Section

> **Parent:** [`../DESIGN.md`](../DESIGN.md) — design index.
> **Status:** draft.
> **Serves:** G1 (annulus to cone), G3, G8, G11, P4 (same modules
> both directions), P12; ARCHITECTURE A2 (the chain), A4.5
> (`deflection/`).
> **Depends on:** Sections 1, 2, 3, 4.
> **Implemented by:** pseudocode section 5.

---

## 5.1 Purpose and scope

This is the middle of the chain in both directions (A2). Forward, it
turns a potential and a beam into a deflection function `Θ(b̃)` at
each energy, a cross section `dσ/dΩ(θ)`, and the annulus-to-cone map
of G1. Backward (Section 8), the same objects are what the inversion
recovers, and the deflection integral defined here is the very
integral the inversion inverts. That symmetry is why the deflection
function is computed *from the potential by quadrature*, not read
off the integrated orbits (Section 4.7).

It does not bin anything (Section 7) or draw anything (Section 11).

---

## 5.2 The deflection integral

For a particle of energy `Ẽ` and impact parameter `b̃` in a central
potential `Ṽ(r̃)`, conservation of energy and angular momentum give
the polar angle swept from the turning point to infinity, and the
signed deflection is twice that subtracted from `π`:

```
  Θ(b̃) = π − 2 b̃ ∫_{r̃_min}^{∞}  dr̃ / ( r̃² sqrt(g(r̃)) )       (5.1)

  g(r̃) = 1 − b̃² / r̃² − Ṽ(r̃) / Ẽ                              (5.2)
```

`r̃_min` is the largest root of `g(r̃) = 0`. `g` is the squared
radial speed over the asymptotic speed squared, so it is positive
outside the turning point and vanishes there as `(r̃ − r̃_min)` to
first order, which makes the integrand's singularity a
square-root one — integrable, but not something a naive quadrature
rule handles.

Two properties matter:

- **The sign comes out by itself.** For an attractive potential the
  swept angle `φ_∞` exceeds `π / 2` and (5.1) gives `Θ < 0` with no
  case analysis. For Coulomb this reproduces (2.7) exactly, and
  that is a test.

- **It is the object the inversion inverts.** With the substitution
  `u = 1 / r̃`, (5.1) is an Abel-type transform of `Ṽ`; Section 8
  recovers `Ṽ` from `Θ(b̃)` by the inverse transform. Computing `Θ`
  any other way would leave the forward and inverse tools using
  different definitions of the same quantity.

**The turning point.** `r̃_min` is found by bracketing the largest
root of `g`: `g → 1` as `r̃ → ∞`, and for a repulsive potential
`g < 0` at small `r̃`, so a bracket from a large radius inward to the
first sign change and a root-finder (`brentq`) gives `r̃_min` to
machine precision. For Coulomb it is checked against (2.3). For a
potential with a well (FD3), `g` may have several roots and the
largest one is the physical turning point; a root-finder started at
large `r̃` and marching inward finds it first. Where `g` has a
double root — `g = 0` and `dg/dr̃ = 0` together — the particle
orbits the center indefinitely and `Θ` diverges; the design detects
this by the root's multiplicity and records `Θ = ±∞` for that `b̃`
rather than a spurious number. This is the *orbiting* singularity
and is out of scope for the first version except for being caught.

---

## 5.3 Evaluating the integral

The square-root singularity is removed by substitution before any
quadrature rule sees it. With `r̃ = r̃_min + ρ²`, `dr̃ = 2ρ dρ`:

```
  Θ = π − 4 b̃ ∫_0^∞  ρ dρ / ( (r̃_min + ρ²)² sqrt(g(r̃_min + ρ²)) )
                                                                (5.3)
```

Near `ρ = 0`, `g ≈ g'(r̃_min) ρ²`, so `ρ / sqrt(g) → 1 /
sqrt(g'(r̃_min))`, finite; the integrand is smooth on `[0, ∞)` and
decays as `ρ⁻³`. It is then handed to `scipy.integrate.quad` on the
semi-infinite interval, which maps it to a finite one internally and
converges rapidly. Tolerances `epsabs = 1e-12`, `epsrel = 1e-12` are
requested; the achieved estimate is kept and reported.

At `ρ = 0` exactly, `g = 0` and the expression is `0 / 0`; the
implementation evaluates the limit `1 / sqrt(g'(r̃_min))` there,
with `g'` from the potential's `dṼ/dr̃` (A6.1):

```
  g'(r̃) = 2 b̃² / r̃³ − (dṼ/dr̃) / Ẽ                              (5.4)
```

which is also the quantity whose vanishing signals orbiting (5.2).

**The head-on repulsive case, `b̃ = 0`.** The integral is zero and
`Θ = π` without evaluation. It is special-cased so that the
prefactor `b̃ = 0` does not multiply a `quad` call whose integrand is
`0 / 0` everywhere.

**Verification against Rutherford.** For Coulomb, (5.3) reproduces
(2.8) at every `Ẽ` and `b̃` in a test grid to `1e-10` or better;
this is the oracle for the quadrature machinery, and it is checked
in both signs. `dev/spikes/coulomb_closed_forms.py` already does
this: `2e-12` over 36 cases with `b̃` from 0.05 to 50, and `r̃_min`
from the root of `g` to `2e-13`.

---

## 5.4 The deflection table and per-particle evaluation

Two consumers need `Θ`: the display and the cross section need it
as a *curve* in `b̃`, and each particle needs it as a *value* at its
own `b̃`.

**The table.** At each energy, `Θ` is tabulated on a grid in `b̃`
from `b̃_min` (or a small floor when `b̃_min = 0`) to `b̃_max`, with
`n_deflection_points` (fidelity, default 400) spaced uniformly in
`log b̃` — the deflection changes fastest at small `b̃` — and the
head-on value appended when `b̃ = 0` is admissible. The grid also
carries `dΘ/db̃`, computed at each node by a centered finite
difference on the *integral*, not on the table: two extra
quadratures at `b̃ (1 ± δ)` with `δ = 1e-4`, whose truncation error
`O(δ²)` sits below the quadrature tolerance. The table is a plain
record: `(b̃, Θ, dΘ/db̃, r̃_min)` arrays plus the energy.

**Per particle.** Each particle's `Θ` is what places it on the
detector, so it must be exact for the particle's own `b̃`, not
interpolated from a table with its own error. For a run of `N`
particles at `n_energies` energies, that is `N × n_energies`
quadratures of about a hundred integrand evaluations each — of
order `10⁵` evaluations for a Tier-1 run, negligible. For a Tier-2
run of `10⁶` particles the same is still only seconds, so the design
computes every particle's `Θ` directly and does not interpolate.
Interpolation is recorded as the fallback if the batch tier ever
finds this a cost: cubic on the table, with the interpolant's
maximum error against direct quadrature at ten random `b̃` values
reported.

**Closed form when available.** When the potential offers a
closed-form deflection (A6.1) — Coulomb does — the table and the
per-particle values come from it, and the quadrature is run on a
subset as a check whose largest discrepancy is stored. Consumers do
not know which route produced the numbers (P12).

---

## 5.5 The differential cross section

For a beam of uniform flux, particles in the annulus `[b̃, b̃ + db̃]`
scatter into the cone `[θ(b̃ + db̃), θ(b̃)]`, and the ratio of the
annulus area `2π b̃ db̃` to the cone's solid angle `2π sin θ |dθ|` is
the differential cross section:

```
  dσ/dΩ (θ) = ( b̃ / sin θ ) · | db̃/dθ |            [ℓ₀²]       (5.5)
```

Computed on the deflection table: `θ = |Θ|` and `db̃/dθ = 1 /
(dΘ/db̃)` at each node, signed away. The result is a table in `θ`,
`(θ, dσ/dΩ)`, which is not uniform in `θ`; consumers that want a
uniform `θ` grid (the detector's expected counts, Section 7)
interpolate it in `log(dσ/dΩ)`, which is smooth where the cross
section itself spans many decades.

Three places need care, and the table marks each:

- **`θ → π` at `b̃ → 0` (repulsive head-on).** Both `b̃` and `sin θ`
  vanish; the ratio is finite (for Rutherford, `1 / (16 Ẽ²)`). The
  node at `b̃ = 0` is evaluated by extrapolating `log(dσ/dΩ)`
  linearly in `(π − θ)²` from the two nearest nodes — the cross
  section is even in `π − θ` there, so this is second order where
  extrapolation in `θ` would be first — and flagged as extrapolated.

- **`dΘ/db̃ = 0` (rainbow).** `dσ/dΩ` diverges. Out of scope for the
  first version's potentials (Coulomb's `dΘ/db̃` never vanishes) but
  the table stores `+∞` there rather than a large number and the
  plot marks it, so that FD3's potentials arrive into code that
  already knows what a rainbow is.

- **Multivalued `b̃(θ)`.** When several `b̃` scatter to the same `θ`
  (a potential with a well), (5.5) is the *sum* over branches. The
  first version asserts monotonicity of `Θ(b̃)` and refuses a
  non-monotonic table with a message naming the feature; the sum
  over branches is FD3 work.

**Verification.** For Coulomb the table reproduces (2.11) to the
tolerance implied by the finite-difference `dΘ/db̃`, about `1e-8`
relative, at every node not flagged. The spike measures `7e-9`
with `δ = 1e-4`, as the `O(δ²)` estimate predicts.

---

## 5.6 Sign independence, made a number

At each energy the design computes `Θ(b̃)` for the potential as
given, and — if the potential offers a `mirror()` capability that
flips its sign — for the mirror as well, on the same grid. For
Coulomb both are closed forms and the cost is nothing. The tool then
displays the two deflection functions (equal and opposite) and the
two cross sections (identical), and stores their maximum relative
difference, which for Coulomb is zero to precision. This is G8
stated as a stored quantity, and it is a regression test.

---

## 5.7 The annulus-to-cone map (G1)

The tool's central image is an annulus at `b̃` of width `db̃`, and
the cone it lands on. For each annulus declared in the beam (Section
3.3) at each energy:

```
  area        ΔA = π ( (b̃ + db̃)² − b̃² ) = 2π b̃ db̃ + π db̃²
  cone edges  θ₁ = θ(b̃ + db̃),  θ₂ = θ(b̃)
  solid angle ΔΩ = 2π | cos θ₁ − cos θ₂ |                       (5.6)
  ratio       ΔA / ΔΩ
```

The finite ratio is displayed beside `dσ/dΩ` evaluated at the
annulus midpoint, with their difference. A student who narrows `db̃`
watches the finite ratio converge on the derivative — the definition
of a differential cross section seen as a limit rather than stated
as one. The cone edges use the *asymptotic* angles from the table,
so they agree with where the particles land on the detector, and
for an attractive potential the cone is on the far side of the axis
(4.8).

The record produced is per annulus per energy: `(b̃, db̃, ΔA, θ₁,
θ₂, ΔΩ, ΔA/ΔΩ, dσ/dΩ at midpoint)`, consumed by the geometry group
(A4.9) to draw the ring and cone, and by the telemetry panel.

---

## 5.8 Per-particle outputs

For every particle at every energy, this stage attaches:

```
  deflection      Θ, signed
  scattering_angle  θ = |Θ|
  out_direction   n̂_out of (4.4), a unit vector in the scene
  turning_point   r̃_min, from the root of g
```

The out-direction is what the detector bins (Section 7) and what
Section 4.6's outbound free flight follows. The turning point is
also produced by the orbit provider (4.5); the two are compared and
the discrepancy is part of the finite-radius readout.

---

## 5.9 Invariants and tests

- (5.3) reproduces (2.8) for Coulomb, both signs, over a grid of
  `(Ẽ, b̃)`, to `1e-10`.
- `Θ(b̃; mirror) = −Θ(b̃)` and `dσ/dΩ` identical, for Coulomb, to
  precision.
- `Θ` is monotone in `b̃` for a monotone repulsive potential;
  `|Θ| → 0` as `b̃ → b̃_max` and the table's last node satisfies
  `θ = θ_min` of Section 3.3.
- `dσ/dΩ` from the table reproduces (2.11) to `1e-8` at unflagged
  nodes; the flagged head-on node is within `1e-4` of the limit.
- The annulus ratio `ΔA / ΔΩ` converges to `dσ/dΩ` at the midpoint
  as `db̃ → 0`, at second order in `db̃`.
- `g(r̃_min) = 0` to machine precision and `g'(r̃_min) > 0` for every
  particle of the first version's potentials.
- The turning point from the root of `g` agrees with the orbit
  provider's, to the integrator tolerance.

---

## 5.10 Alternatives considered

**Read `Θ` off the integrated orbit.** Rejected; Section 4.7 and
5.1. It ties the inverse chain to the orbits and carries a
finite-radius error the quadrature does not.

**Finite-difference `dΘ/db̃` on the table.** Rejected in favor of
differencing the integral at each node: the table's spacing is set
for display, and a derivative from it would inherit interpolation
error into the cross section, which is the quantity the detector
and the inversion are checked against.

**Gauss–Chebyshev quadrature for the endpoint singularity.** Exact
for the Coulomb weight and elegant, but assumes the singularity's
form; rejected in favor of the `ρ²` substitution, which handles any
`g` with a simple root and lets one general-purpose rule serve every
potential.

**Interpolate per-particle `Θ` from the table.** Rejected for the
first version; see 5.4. Recorded as the batch-tier fallback.

---

## 5.11 References

- Goldstein, Poole, and Safko, *Classical Mechanics*, 3rd ed.,
  Section 3.10, eqs. (3.96)–(3.97), for the deflection integral and
  the cross-section definition.
- Landau and Lifshitz, *Mechanics*, 3rd ed., Sections 18 (scattering)
  and 20 (small-angle scattering), for the integral and its Coulomb
  evaluation.
- Ford, K. W., and Wheeler, J. A., "Semiclassical description of
  scattering," *Ann. Phys.* **7**, 259 (1959), for the rainbow,
  glory, and orbiting singularities that FD3 will meet.
