# Spikes

Throwaway experiments kept because their *results* are cited in the
design chain. A spike is not production code and is not held to the
architecture: it exists to answer one question, and it stays in the
repository only so that the answer can be re-checked when the
libraries, the formulas, or the conventions change.

Run every spike from the repository root inside the shared
environment (`source $CPG_VENV_RIGID`).

---

## `coulomb_closed_forms.py`

**Question it answered:** are the Coulomb closed forms in
`dev/design/02-coulomb-closed-forms.md` — orbit, turning point,
deflection function, cross section, and the hyperbolic-anomaly time
parametrization for *both* signs of the potential — correct as
written, in the natural units of `dev/design/01-natural-units.md`?

**Answer:** yes, all of them, to floating-point precision (worst
relative error `3e-13` across ten `(sign, energy, impact)` cases).
Specifically: the two forms of `r_min` agree; `r(φ(H))` from the
orbit equation reproduces `r(H)`; energy and angular momentum are
conserved along the parametrized orbit; the turning-point product
equals `b²`; and the Rutherford cross section equals the general
definition evaluated by finite difference.

**The trap it found.** The first draft of design section 1 chose the
speed scale `v₀ = sqrt(2 E_ref / m)` so that the asymptotic speed at
the reference energy would be exactly one. Under that convention the
kinetic energy in natural units is `ṽ²`, not `½ ṽ²`, and every
textbook closed form with `m = 1` is off: this spike found the
angular momentum wrong by exactly `sqrt(2)` and the deflection equal
to the value at *half* the energy. Section 1 now uses `v₀ = sqrt(E_ref
/ m)`, under which everything checks. A convention chosen for a
pretty number is not free.

**Second question (added the same day):** does the general
deflection integral of design section 5, eq. (5.3), with the `ρ²`
substitution and `scipy.integrate.quad` on `[0, ∞)`, reproduce the
Rutherford closed form — and does a cross section built by
differencing that integral reproduce (2.11)?

**Answer:** yes. `|Θ_quad − Θ_exact| ≤ 2e-12` over 36 `(sign, E, b)`
cases spanning `b` from 0.05 to 50; the turning point from the root
of `g` matches (2.3) to `2e-13`; the cross section from a
`δ = 1e-4` centered difference of the integral matches (2.11) to
`7e-9` relative, consistent with the `O(δ²)` truncation the design
predicts.

**The residual it measures.** The deflection (2.8) differs from a
direct integration of the equations of motion started on the
straight-line asymptote at finite radius `R` by an amount that scales
exactly as `1 / R` (`R × diff = 0.2353` for `s = +1`, `E = 1`, `b =
2`, constant to four figures from `R = 1000` to `16000`). This is not
a formula error; it is the finite-`R_max` effect that design section
4 must either correct for or start the orbit on the exact asymptote
to avoid. Cited from `ARCHITECTURE.md` §4.5.

```bash
python3 dev/spikes/coulomb_closed_forms.py
```

---

## `firsov_inversion.py`

**Question it answered:** is the inverse-scattering chain that
design section 8 will specify — counts → `dσ/dΩ` → `b(θ)` → `Θ(b)` →
`V(r)` — correct as derived from the deflection integral, and how
does it degrade under a finite `b_max` and finite counts?

**Answer, exact data:** the Firsov form

```
  ln(r / w) = (1/π) ∫_w^∞ Θ(b) db / sqrt(b² − w²),
  w = r sqrt(1 − V/E),   V(r) = E (1 − w²/r²)
```

recovers `V = ±1/r` from the exact Rutherford `Θ(b)` to `2e-14` in
**both** signs; and `b(θ)² = 2 ∫_θ^π (dσ/dΩ) sin θ' dθ'` recovers
(2.9) from the exact cross section to `1e-15`. The `b = w cosh t`
substitution removes the endpoint singularity and the integral is
then `(1/π) ∫_0^∞ Θ(w cosh t) dt`, smooth.

**Answer, finite `b_max`:** taking `Θ = 0` beyond `b_max` costs
`1e-2` to `3e-1` relative in `V(r)`, scaling as `1/b_max` and
growing with `r`. **Section 8 must model the tail**, not truncate
it; with a Coulomb-shaped tail joined at the last measured `b`, the
error vanishes.

**Answer, binned counts (uniform-flux disc, `b_max = 12`, 40 bins
uniform in `log θ`, repulsive sign assumed):**

| `N` | pull RMS | `V(r)` error RMS | max |
| --- | --- | --- | --- |
| 2×10⁴ | 1.05 | 1.6e-2 | 2.8e-2 |
| 2×10⁵ | 0.94 | 9.1e-3 | 2.3e-2 |
| 2×10⁶ | 1.04 | 1.6e-3 | 3.7e-3 |

Pull RMS of 1.0 means the binned estimate scatters exactly as
Poisson counting predicts, so the detector model is honest. The
recovered potential is within a percent at `2×10⁵` particles over
`r` from 1.1 to 6.5 (the reach limit is `r_min = 1`), which sets
the batch-tier scale for a convincing classroom inversion.

**Two traps it found, both for design section 7:**

1. Counts must be compared with the *bin-integrated* expectation
   `F ∫_bin (dσ/dΩ) dΩ`, never with the cross section at the bin
   center times the solid angle. For a `θ⁻⁴` law the two differ by
   orders of magnitude in a wide bin; the first attempt reported a
   pull RMS of 27 for this reason alone.
2. Bins of equal solid angle put nearly every count in the
   smallest-angle bin and leave the rest empty. Bins uniform in
   `log θ` keep every bin populated over three decades of cross
   section.

**One thing it makes explicit:** the counts carry no sign. The
inversion *assumes* repulsion; with attraction assumed, the same
counts yield `V = −1/r` (the `Θ → −Θ` symmetry of (2.7)). Section 8
must present the sign as a student's choice and show both fits.

```bash
python3 dev/spikes/firsov_inversion.py
```
