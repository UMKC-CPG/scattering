# Design 1. Natural Units, Scaling, and Presets

> **Parent:** [`../DESIGN.md`](../DESIGN.md) — design index.
> **Status:** draft.
> **Serves:** VISION P13 (dimensionless core, real units at the
> boundary), G5 (energy sweep), ARCHITECTURE A6.6 (the units
> boundary), A4.1 (`core/natural_units.py`, `core/units.py`).
> **Implemented by:** pseudocode section 1.

---

## 1.1 Purpose and scope

The physics inside the core is the same for an alpha particle on a
gold nucleus and a comet past the Sun, although every dimensional
quantity differs between them by tens of orders of magnitude. This
section fixes the scaling that makes one computation serve both, and
fixes the single place where real units enter and leave.

It does not design the run-file syntax for quantities (Section 10) or
the display formatting of a value (Section 11). It fixes what the
core computes in, how a real quantity becomes a core quantity, and
which named presets exist.

---

## 1.2 The three reference scales

Every run declares, or receives by default, three reference scales.
All core quantities are expressed as multiples of these.

| Scale | Symbol | Meaning |
| --- | --- | --- |
| Mass | `m` | The projectile mass |
| Energy | `E_ref` | A reference beam energy |
| Length | `ℓ₀` | A reference length |

From them follow the derived scales the core needs:

```
  v₀ = sqrt(E_ref / m)          reference speed
  t₀ = ℓ₀ / v₀                  reference time
  L₀ = m v₀ ℓ₀                  reference angular momentum
```

A quantity `x` in natural units is written `x̃ = x / x_scale`. So
`r̃ = r / ℓ₀`, `Ẽ = E / E_ref`, `Ṽ = V / E_ref`, `t̃ = t / t₀`,
`b̃ = b / ℓ₀`, `ṽ = v / v₀`, and `L̃ = L / L₀`. With this `v₀` the
mechanics reads exactly as it does in SI with unit mass:

```
  kinetic energy      ½ ṽ²
  equation of motion  d²r̃/dt̃² = − ∇̃ Ṽ
  asymptotic speed    ṽ_∞ = sqrt(2 Ẽ)
  angular momentum    L̃ = ṽ_∞ b̃ = sqrt(2 Ẽ) b̃
```

The projectile mass is `m̃ = 1` in the ordinary sense — no hidden
factor in the equations. The price is that `ṽ_∞` at the reference
energy is `sqrt(2)`, not one. The alternative, `v₀ = sqrt(2 E_ref /
m)`, makes `ṽ_∞ = 1` at `E_ref` and puts a factor of one half into
the equation of motion and a factor of two into the kinetic energy,
which every later formula would then have to carry; a scratch check
of the Section 2 closed forms against that convention is how the
inconsistency was found (Section 1.7).

**The reference length is fixed per run, not per energy.** This is
the decision that matters for G5. A tempting choice for Coulomb is
`ℓ₀ = |κ| / E`, which makes the head-on turning point exactly one
unit at every energy — and makes the whole scene rescale as the
energy slider moves, so that orbits never visibly tighten. Instead
`ℓ₀` is set once from `E_ref`, and the energies of a sweep are the
dimensionless list `Ẽ_k = E_k / E_ref`. Orbits at higher `Ẽ` then
sit visibly closer to the center in the same scene, which is the
lesson.

`E_ref` defaults to the first energy in the run's energy list, and
may be set explicitly (`reference_energy` in the run file, Section
10) so that two runs with different sweeps share a scene scale.

---

## 1.3 The default reference length, per potential

`ℓ₀` may always be set explicitly in the run file. When it is not,
each potential supplies its own natural default, and the choice is
the potential's business (A6.1), not the core's:

| Potential | Default `ℓ₀` | Why |
| --- | --- | --- |
| Coulomb `κ / r` | `|κ| / E_ref` | Head-on turning point at `E_ref` |
| Yukawa (later) | The screening length | The only intrinsic length |
| Hard sphere (later) | The sphere radius | Likewise |
| Well (later) | The well's length parameter (`σ`) | Likewise |

With the Coulomb default, the potential in natural units is

```
  Ṽ(r̃) = s / r̃          s = sgn(κ)
```

with strength exactly one, and the repulsive head-on turning point
at the reference energy is `r̃_min = 1`. Every Coulomb result then
depends on the product `Ẽ b̃` alone (Section 2), which is the
statement of P13 in its sharpest form.

---

## 1.4 The units boundary

`core/units.py` is the only module permitted to import pint (A6.6).
It offers three operations and no others:

1. **`to_natural(quantity, scales) → float`.** Parse a dimensioned
   quantity — a pint object, or a string such as `"5 MeV"` or
   `"26 km/s"` — and divide by the appropriate reference scale,
   returning a bare float. Dimension mismatch is an error naming the
   expected dimension.

2. **`from_natural(value, dimension, scales) → quantity`.** Multiply
   a bare float by the reference scale of the named dimension and
   return a pint quantity in the preset's display unit for that
   dimension (Section 1.5).

3. **`build_scales(run_spec) → scales`.** Resolve `m`, `E_ref`, and
   `ℓ₀` from a run specification, applying the defaults above, and
   return the derived scales with them.

The conversion runs once on load and once on display, never inside
a stage. Below `run/`, no module imports pint, accepts a pint object,
or returns one; this is architectural test A8.6(2).

**Constants come from `scipy.constants`, never from typed literals.**
The Coulomb constant, elementary charge, the alpha-particle mass,
the gravitational constant, and the astronomical unit are all there
at CODATA or IAU values. A constant copied by hand into a preset is
a transcription error waiting to be found, and the spike record of
the rigid-body tool shows that such errors do get made.

---

## 1.5 Presets

A preset names a physically meaningful `(m, κ, E_ref)` triple and the
display units in which a student should see results. The run file
selects one by name and may override any single value. The first
version ships two, one of each sign of `κ`.

### `alpha_on_gold` — Rutherford's experiment

| Quantity | Value | Source |
| --- | --- | --- |
| Projectile | Alpha particle, `Z₁ = 2` | — |
| Target | Gold nucleus, `Z₂ = 79` | — |
| `κ` | `Z₁ Z₂ e² / (4π ε₀)` ≈ 227.6 MeV·fm | `scipy.constants` |
| `m` | Alpha-particle mass, ≈ 3727 MeV/c² | `scipy.constants` |
| `E_ref` | 5.0 MeV | Typical alpha source |
| `ℓ₀` | `κ / E_ref` ≈ 45.5 fm | Section 1.3 |
| Display | MeV, fm, MeV/c², units of `c` for speed | — |

The asymptotic speed `v_∞ = sqrt(2 E_ref / m) ≈ 0.052 c` confirms
the non-relativistic treatment is sound, and the tool states this
ratio on screen.

### `interstellar_visitor` — a hyperbolic pass by the Sun

| Quantity | Value | Source |
| --- | --- | --- |
| Projectile | A small body; `m` cancels (below) | — |
| `κ / m` | `−G M_☉` ≈ −1.327 × 10²⁰ m³/s² | IAU `GM_☉` |
| `v_∞` | 26 km/s | Order of ʻOumuamua's excess speed |
| `E_ref / m` | `½ v_∞²` | — |
| `ℓ₀` | `2 G M_☉ / v_∞²` ≈ 2.6 AU | Section 1.3 |
| `t₀` | `ℓ₀ / v₀ = sqrt(2) ℓ₀ / v_∞` ≈ 250 days | — |
| Display | AU, km/s, days | — |

For gravity `κ ∝ m`, so the orbit is independent of the projectile
mass and the preset need not name one; `m̃ = 1` is assigned and the
mass is never displayed. This is itself worth a label on screen: the
equivalence principle, visible as a mass slider that does nothing.

### `custom`

Explicit `m`, `κ`, and `E_ref` as dimensioned strings, with the
display units taken from the strings given. This is how a student
tries a different `Z₂`, or a different `v_∞`, without editing a
preset.

**Numerical values above are approximate and illustrative.** The
code computes them from `scipy.constants` at run time, and the test
suite checks the computed values against these to one percent — a
test of the preset's plumbing, not of the constants.

---

## 1.6 Invariants and failure modes

- `m > 0`, `E_ref > 0`, `ℓ₀ > 0`, checked at `build_scales`.
- Every energy in a sweep satisfies `E_k > 0`; `Ẽ_k > 0` follows.
- A quantity handed to `to_natural` with the wrong dimension is an
  error at load, naming the key, the dimension found, and the
  dimension expected. It is never coerced.
- `from_natural` on a dimension the preset does not name a display
  unit for falls back to SI and says so in the label.

---

## 1.7 Alternatives considered

**Real SI throughout, as the rigid-body tool does.** Rejected for
this project because the two presets differ by roughly thirty orders
of magnitude in every quantity, and because Coulomb scattering has an
exact scaling symmetry that SI obscures. Rigid-body rotation has no
such symmetry, so its Principle 11 was right there and P13 is right
here. Both keep pint at the boundary for the same reasons.

**`ℓ₀ = |κ| / E` per energy.** Rejected; see Section 1.2. It is the
natural choice for a single energy and the wrong one for a sweep.

**`v₀ = sqrt(2 E_ref / m)`, so that `ṽ_∞ = 1` at `E_ref`.** This was
the first draft. A numerical check of the Section 2 closed forms
found the angular momentum off by exactly `sqrt(2)` and the
deflection off by the value at half the energy: under that
convention the kinetic energy is `ṽ²` rather than `½ ṽ²`, so the
textbook forms with `m = 1` do not hold. Rejected in favor of a
convention where they do (Section 1.2).

**A fully dimensionless tool with no presets.** Rejected: it would
never let a student see that 45 femtometers and 2.6 astronomical
units are the same picture, which is the point of having two
presets.

---

## 1.8 References

- Goldstein, Poole, and Safko, *Classical Mechanics*, 3rd ed.,
  Section 3.10 (scattering in a central force field), for the
  Coulomb scaling.
- CODATA recommended values, as packaged in `scipy.constants`.
- IAU 2015 Resolution B3 nominal values for `GM_☉` and the
  astronomical unit.
