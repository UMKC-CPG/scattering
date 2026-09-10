# Design 8. Inversion: From Counts to the Potential

> **Parent:** [`../DESIGN.md`](../DESIGN.md) — design index.
> **Status:** draft; every formula verified by
> `dev/spikes/firsov_inversion.py`.
> **Serves:** G7 (invert from counts), G8 (ambiguities visible),
> P3, P4 (same modules both directions), P15 (unknown shown as
> unknown); ARCHITECTURE A2 (the inverse chain), A4.7
> (`inversion/`), A8.6(4) (the reachability guarantee).
> **Depends on:** Sections 2, 3, 5, 7.
> **Implemented by:** pseudocode section 8.

---

## 8.1 Purpose and scope

The forward chain ends in a histogram. This section runs it
backwards: from the detector record of Section 7.8, recover the
cross section, from it the deflection function, and from that the
potential over the range of radii the data can reach — and mark
everything the data cannot decide. It is the second traversal of
the same stages (A2), and each step below names the forward step it
inverts.

It handles the first version's case: a monotonic deflection
function, single-valued `b(θ)`, and a single energy at a time, with
the energy sweep used to stack the reachable ranges. Rainbow,
orbiting, and multivalued `b(θ)` (FD3) are detected and refused,
not handled.

---

## 8.2 Step 1 — counts to cross section

Inverts Section 7.5. The detector record already carries the
estimate `σ̂_i = N_i / (F ΔΩ_i)` and its error; this step passes
them through, propagating the mask of unmeasured bins and the
`empty` flags, and adds nothing. It exists as a stage so that the
inverse chain has the same shape as the forward one and so that a
student can substitute the *exact* cross section here (P3) and
watch every downstream quantity lose its noise. That substitution
is the tool's cleanest demonstration that the later steps are
deterministic and the scatter in the recovered potential is
counting statistics and nothing else.

---

## 8.3 Step 2 — cross section to deflection function

Inverts Section 5.5. For a monotonic deflection function the
particles scattering to angles larger than `θ` are exactly those
with impact parameter smaller than `b(θ)`, so

```
  b(θ)² = 2 ∫_θ^{θ_head} (dσ/dΩ)(θ') sin θ' dθ'                  (8.1)
```

where `θ_head` is the largest measured angle (Section 7.3), `π` for
a repulsive potential with `b̃_min = 0`. For Rutherford this
reproduces (2.9) to `1e-15` (spike).

**On binned data (8.1) is exact at the bin edges.** The integral
over a bin is `σ̂_i ΔΩ_i / 2π = N_i / (2π F)`, so

```
  b(θ_j)² = (1 / π F) Σ_{i ≥ j} N_i                              (8.2)
```

— a cumulative sum of counts from the large-angle end, with no
interpolation and no bin-center approximation. This is why Section
7 insisted on bars, not points: the inversion never needs the
cross section *at* an angle, only its integral *between* angles,
and that the histogram carries exactly. The error on `b(θ_j)²`
follows from Poisson statistics on the partial sum.

The result is `b` at every bin edge, monotone by construction
(counts are non-negative), with repeated values where large-angle
bins are empty; those are dropped, so the table is strictly
monotone.

**The sign is chosen here, and it is the student's.** The counts
carry `θ = |Θ|` and nothing else (Section 7.7). The run file's
`assume_sign` (`+1` or `−1`) sets `Θ = assume_sign · θ`, and the
panel says so in words: *"assuming a repulsive potential."* With
the other sign the same data yields the mirror potential (2.7),
equally consistent with every count. The tool offers a toggle and
shows both recovered potentials at once; that they fit the same
histogram equally well is G8's lesson delivered by the inversion
rather than merely stated by the forward tool.

**Interpolating `Θ(b)`.** Step 3 needs `Θ` at arbitrary `b` between
the edges. The table is interpolated in `log b` with a monotone
(PCHIP) interpolant, so that no overshoot can produce a
non-monotone `Θ` from monotone data. The spike found cubic
interpolation adequate on exact data (`4e-5` in `V`) and monotone
interpolation necessary on binned data.

---

## 8.4 Step 3 — deflection function to potential

Inverts Section 5.2. With the Firsov variable

```
  w(r) = r sqrt(1 − V(r) / E)                                    (8.3)
```

the deflection integral (5.1) becomes an Abel transform of
`d(ln r)/dw`, and its inverse is

```
  ln( r / w ) = (1/π) ∫_w^∞ Θ(b) db / sqrt(b² − w²)
              = (1/π) ∫_0^∞ Θ(w cosh t) dt                      (8.4)

  V(r) = E ( 1 − w² / r² )       at  r = r(w)                    (8.5)
```

The substitution `b = w cosh t` removes the endpoint singularity;
the integrand is then smooth and `quad` on `[0, ∞)` converges to
tolerance. Given `w`, (8.4) yields `r`, and (8.5) yields `V` there;
sweeping `w` sweeps out the curve `V(r)` parametrically. The spike
recovers `V = ±1 / r` from the exact Rutherford `Θ` to `2e-14` in
both signs.

**Condition of validity.** (8.4) requires `w(r)` to be monotonic in
`r`, which holds for every monotonic repulsive potential and for
attractive Coulomb, and fails for a potential with a well where
`Θ(b)` is non-monotonic. Step 2 already refuses a non-monotone
table; this step additionally checks that the recovered `r(w)` is
monotone increasing and refuses with a message naming the feature
if it is not.

**A sketch of the derivation, for the reader.** In (5.1) write
`1 − b²/r² − V/E = (1 − V/E)(1 − b²/w²)` and change variable from
`r` to `w`; the integral becomes `b ∫_b^∞ (d ln r / dw) dw /
sqrt(w² − b²)`, which is the Abel form whose inverse is standard.
The full derivation belongs in the pseudocode section's commentary
and in the source, since it is the one piece of mathematics in the
project a student is least likely to have seen.

---

## 8.5 The tail beyond the last measured `b`

(8.4) integrates to `b = ∞`, and the data stop at `b_high =
b(θ_min)`, the impact parameter of the smallest measured angle.
What `Θ` does beyond `b_high` matters: the spike found that setting
it to zero costs `1e-2` to `3e-1` relative in `V(r)`, scaling as
`1 / b_max` and *growing with `r`*, because the exterior of the
beam is exactly where the potential at large `r` is probed.

The run file's `tail_model` supplies `Θ(b)` for `b > b_high`:

- **`"coulomb"`** — `Θ(b) = 2 arctan(A / (2 E b))` with `A` fitted
  to the last few measured points. For when a `1 / r` tail is known
  or assumed; the default for the first version.
- **`"power"`** — `Θ ∝ b^{−n}`, with `n` and the prefactor fitted.
  For a faster-than-Coulomb tail (Yukawa, later).
- **`"zero"`** — `Θ = 0` beyond the data. A labeled bad example;
  the error it makes is shown.

The model is joined at `b_high` and the integral (8.4) is split
there so that the quadrature sees two smooth pieces. The panel
states the tail model in words next to the recovered curve, and the
contribution of the tail to `ln(r/w)` at each `w` is stored, so
that a student can see what fraction of the recovered potential at
each radius came from the *assumption* rather than the *data* —
which is large at large `r` and small near the reach limit (P14).

---

## 8.6 Reachability — what the data cannot decide (P15)

At energy `Ẽ` no orbit went inside the head-on turning point
`r̃_min(b̃ = 0)`, or inside `r̃_min(b̃_min)` when the beam excludes
the center. In the Firsov variable that radius is `w = b_low`, the
smallest measured impact parameter, and (8.4) below it would need
`Θ` at `b < b_low`, where there are no counts.

`reachability.py` therefore reports, per energy,

```
  r_reach     the smallest radius the recovered potential is
              defined at: r(w = b_low) by (8.4)
  w_low       b_low itself
  fraction    of ln(r/w) at each w that came from the tail model
```

and every consumer of the recovered potential receives `r_reach`
with the curve and is required to draw the interior as unknown —
hatched, with no curve and no extrapolation. The architectural test
A8.6(4) asserts that no code path returns a `V(r)` value for
`r < r_reach` without the unknown marker.

**The energy sweep stacks reaches.** At higher `Ẽ` the head-on
turning point moves inward, so `r_reach` falls. With a sweep, each
energy is inverted separately and the recovered curves are overlaid;
where they overlap they must agree (a consistency check the panel
displays as a number), and the union of their ranges is what the
sweep measured. The interior of the *deepest* reach stays unknown.
This is G5's second half: energy is what buys depth, and no amount
of statistics at one energy substitutes for it.

---

## 8.7 Error propagation

Three sources, kept separate (P3):

- **Statistical.** Poisson on the counts, propagated through the
  partial sums (8.2) into `b(θ_j)`, and then by a resampling
  estimate through (8.4): the histogram is resampled `n_resample`
  times (fidelity, default 50) from its own Poisson expectation,
  each resample inverted, and the spread of the recovered curves
  drawn as a band. This is the honest way to carry counting error
  through a nonlinear integral transform, and at forty bins and
  fifty resamples it costs a second.

- **Tail model.** The difference between the recovered curves under
  the chosen tail model and under `"zero"`, drawn as a second,
  differently styled band. It is not statistical and is not
  combined with the band above.

- **Numerical.** The quadrature tolerance of (8.4), far below the
  other two and reported as a number rather than drawn.

The spike's numbers set expectations: at `2 × 10⁵` particles the
statistical band is about one percent over the reachable range.

---

## 8.8 The comparison

The recovered `V(r)` is overlaid on the potential that generated
the counts (the tool knows it; an experiment would not), with:

- the reach limit and the unknown interior (8.6);
- the statistical and tail bands (8.7);
- the mirror-sign recovery as a dashed curve (8.3);
- the relative error at each recovered radius as a numeric readout.

And the loop closes: the recovered potential can be fed back into
the *forward* chain (a `custom` potential from a tabulated `V(r)`,
A6.1) to produce a predicted histogram, whose pulls against the
actual counts are the final consistency check. That the forward and
inverse tools share their modules (P4) is what makes this a few
lines rather than a feature.

---

## 8.9 The result record

Per energy:

```
  cross_section    from Step 1: estimate, error, mask, flags
  impact_table     (θ_edge, b, δb) from (8.2), strictly monotone
  assume_sign      ±1
  tail_model       name and fitted parameters
  b_low, b_high
  recovered        (w, r, V) arrays over w ∈ [b_low, w_max]
  reach            r_reach
  tail_fraction    [len(w)]
  stat_band        (V_lo, V_hi) from resampling
  tail_band        (V_lo, V_hi) versus the zero tail
  mirror           the (r, V) under −assume_sign
  quad_error       largest quadrature error estimate
  refused          None, or the reason (non-monotone, rainbow, …)
```

---

## 8.10 Invariants and tests

- (8.1) on the exact Rutherford cross section reproduces (2.9) to
  `1e-12`; (8.2) on a histogram of exact bin-integrated expected
  counts reproduces `b` at every edge to the same.
- (8.4)–(8.5) on the exact Rutherford `Θ(b)` recover `V = s / r` to
  `1e-12`, both signs.
- Inverting with `−assume_sign` recovers `−V` exactly (bitwise on
  the `Θ` table, to precision on `V`).
- On a fixed-seed histogram of `2 × 10⁵` Coulomb particles with the
  Coulomb tail, the recovered `V` is within `3 %` of `1 / r` at
  every recovered radius, and within the statistical band at the
  stated confidence for all but a Poisson-expected fraction of
  points (A8.4: fixed seed, seed-independent property).
- With `tail_model = "zero"`, the error grows with `r` and scales
  as `1 / b_max` across a doubling sequence.
- No `V` value is returned for `r < r_reach` without the unknown
  marker (A8.6(4)).
- A non-monotone `Θ` table is refused with a message; the refusal
  is tested with a synthetic rainbow.
- The closed loop of 8.8 on exact data gives pull RMS at the Poisson
  level.

---

## 8.11 Alternatives considered

**Invert the orbits rather than the deflection function.** There is
nothing to invert: the detector never saw an orbit. This is why A2
puts the orbits outside the inverse chain.

**Fit a parametric potential to the histogram.** Simpler and often
what an experiment does. Rejected as the *primary* mechanism
because it presupposes the functional form, which is the thing the
inversion is supposed to discover; kept as a Section 12 refinement
(the "guess the potential" mode from the original discussion),
where a student proposes `V(r)`, the forward chain runs, and the
pulls are shown.

**Differentiate the cross section to get `db/dθ`.** Rejected:
(8.1) integrates, which smooths noise; differentiating a histogram
amplifies it. The Firsov route needs `Θ(b)`, not `dΘ/db`.

**Gauss–Chebyshev quadrature on (8.4).** Exact for the `1 /
sqrt(b² − w²)` weight, but the `cosh` substitution makes the
integrand smooth enough that adaptive `quad` is simpler and
potential-agnostic. Same reasoning as Section 5.10.

**Analytic error propagation through (8.4).** Possible, since the
transform is linear in `Θ`; rejected for the first version because
the nonlinearity enters at (8.5) and through the interpolation, and
resampling handles all of it honestly at negligible cost.

**Adaptive (equal-count) bins for the inversion.** Attractive for
equalizing the error in (8.2) per edge; deferred, as in Section
7.10.

---

## 8.12 References

- Firsov, O. B., "Determination of the forces acting between atoms
  using the differential effective cross section of elastic
  scattering," *Zh. Eksp. Teor. Fiz.* **24**, 279 (1953).
- Landau and Lifshitz, *Mechanics*, 3rd ed., Section 18, Problem 7
  (the inversion of the deflection function).
- Newton, R. G., *Scattering Theory of Waves and Particles*, 2nd
  ed., Section 5.4 (the classical inverse problem).
- Keller, J. B., Kay, I., and Shmoys, J., "Determination of the
  potential from scattering data," *Phys. Rev.* **102**, 557 (1956),
  for the conditions of uniqueness.
