# Design 7. The Detector

> **Parent:** [`../DESIGN.md`](../DESIGN.md) — design index.
> **Status:** draft; the binning and expectation rules are fixed by
> `dev/spikes/firsov_inversion.py`.
> **Serves:** G6 (honest detector), G8 (sign ambiguity), P3
> (statistical error kept distinct), P15 (unknown shown as unknown);
> ARCHITECTURE A4.6 (`detector/`), A6.4 (the detector boundary),
> A8.4 (statistical tests).
> **Depends on:** Sections 3, 5, 6.
> **Implemented by:** pseudocode section 7.

---

## 7.1 Purpose and scope

The detector turns the ensemble into what an experiment actually
yields: counts in angular bins, with the statistical error those
counts carry. It is the last stage of the forward chain and the
first of the inverse one (A2), and its output record is what
Section 8 receives unchanged.

It consumes, per energy, only the per-particle asymptotic
directions `n̂_out` of Section 5.8, the beam's flux `F` and
`theta_min` of Section 3, and its own bin layout. It does not see
the potential, the orbits, or the impact parameters (A6.4). That
restriction is not a convenience; it is the lesson of G8 enforced
by an import test.

---

## 7.2 Geometry

A sphere of radius `R̃_detect ≥ R̃_max` (fidelity; default `2 R̃_max`)
is where particles are *drawn* landing (Section 4.6, outbound free
flight). What is *counted* is the direction, not the landing point:

**`mode = "asymptotic"` (default).** Each particle is binned by the
polar angle `θ = arccos(n̂_out · ẑ)` of its asymptotic direction.
This is the scattering angle as the cross section defines it, and
it is exact.

**`mode = "position"`.** Each particle is binned by the polar angle
of the point where its outbound free-flight line meets the sphere.
The outgoing asymptote is offset from the center by the impact
parameter (the orbit is symmetric), so this angle differs from the
asymptotic one by about `b̃ / R̃_detect`. This is what a real detector
at finite distance measures, and the mode exists so a student can
switch to it and watch the histogram shift at small angles, then
move the sphere outward and watch it converge. The difference is
reported per bin (P14).

The detector bins in `θ` only. Azimuthal symmetry justifies it, and
the layout record carries `n_phi = 1` explicitly so that FD4 is a
change of value, not of interface.

---

## 7.3 The measured range and the unmeasured cones

A beam of finite `b̃_max` produces no scattering below `θ_min =
|Θ(b̃_max)|`, and a beam with `b̃_min > 0` (attractive potentials,
Section 3.4) produces none above `θ_head = |Θ(b̃_min)|`. Both limits
come from the beam and the deflection table, per energy, and the
detector's bins cover exactly `[θ_min, θ_head]`.

Angles outside that interval are **unmeasured, not zero.** The
result record carries a mask, the histogram draws those regions
hatched with no bar, and Section 8 receives them as absent data.
Writing zero there would assert a cross section of zero where the
experiment made no measurement — precisely the misrepresentation
P15 exists to prevent, and one the inversion would faithfully turn
into a wrong potential.

For Coulomb the forward cone is also where the total cross section
diverges (Section 2.5); a student raising `b̃_max` sees `θ_min`
shrink and the forward bins fill with counts that grow as `θ⁻⁴`.
That the hatched region never quite closes is the divergence made
visible.

---

## 7.4 Bin layouts

Three are offered; the layout is a run-file setting with a default
chosen by the spike's finding.

**`log_theta` (default).** Edges uniform in `log θ` between `θ_min`
and `θ_head`, `n_bins` of them (default 40). Over a cross section
that spans three decades this keeps every bin populated; the spike
found zero empty bins at `2 × 10⁵` particles.

**`uniform_theta`.** Edges uniform in `θ`. Simple to read, and the
large-angle bins go empty first as `N` falls; offered because a
student should see that happen.

**`equal_solid_angle`.** Edges uniform in `cos θ`. Every bin has the
same `ΔΩ`, which sounds fair and is the worst choice here: for a
`θ⁻⁴` law nearly every count lands in the first bin and the rest
are empty. Offered *as a labeled bad example*, with a warning in
the panel when more than a quarter of the bins are empty. The spike
tried it first and this is what it found.

Every layout records its edges `θ_0 < θ_1 < … < θ_n` and the solid
angle of each bin,

```
  ΔΩ_i = 2π | cos θ_i − cos θ_{i+1} |                         (7.1)
```

---

## 7.5 Counts, the estimate, and its error

With `N_i` the count in bin `i` and `F` the beam flux (3.3):

```
  estimate     σ̂_i = N_i / (F ΔΩ_i)                            (7.2)
  error        δσ̂_i = sqrt(N_i) / (F ΔΩ_i)                     (7.3)
```

`σ̂_i` estimates the **bin average** of `dσ/dΩ` over `ΔΩ_i`, not its
value at any point. The histogram therefore draws each estimate as
a horizontal bar spanning its bin with a vertical error bar, and
overlays the exact curve of Section 5.5; it never plots a point at
a bin center, because for a steep cross section the center value
and the bin average can differ by orders of magnitude.

An empty bin has `σ̂_i = 0` and no meaningful (7.3); it is drawn as
an arrow at the one-count level and flagged `empty` in the record.
A proper upper limit is deferred (7.10).

---

## 7.6 The expected counts and the pull

The expectation is the bin-integrated cross section, using the
table of Section 5.5 interpolated in `log(dσ/dΩ)`:

```
  E_i = F ∫_{bin i} (dσ/dΩ) dΩ = 2π F ∫_{θ_i}^{θ_{i+1}} (dσ/dΩ) sin θ dθ
                                                                (7.4)
  pull_i = (N_i − E_i) / sqrt(E_i)                              (7.5)
```

The integral is by `quad` on each bin, cheap at forty bins. The
pull is what P3 puts on screen: its RMS over the bins is 1.0 when
the counts scatter exactly as Poisson statistics predict, which the
spike confirms (`0.94`, `1.04`, `1.05` at three values of `N`). A
pull RMS well above one means the physics and the statistics
disagree — a wrong flux, a wrong bin edge, or a bug — and a student
sees that as a number distinct from any conservation drift.

**The comparison is against (7.4), never against `dσ/dΩ(θ_center)
ΔΩ_i`.** The spike's first attempt made that substitution and
reported a pull RMS of 27; the counts were right and the comparison
was wrong. Where the cross section is steep the two expectations
differ by orders of magnitude in a wide bin.

---

## 7.7 What the detector cannot see

Recorded here because Section 8 inherits every one of these as an
ambiguity of the inversion:

- **The sign of the potential.** `θ = |Θ|`, and (2.7) makes
  attractive and repulsive Coulomb give identical `θ` for every
  particle. The histograms are not merely statistically alike; for
  the same seed they are **bit-identical**, and that is a regression
  test (7.9).

- **The side of the axis.** An attractive orbit exits at azimuth
  `ϕ + π` (4.8). A detector with azimuthal bins would still see a
  uniform distribution, because it does not know which incoming
  particle produced which count and the beam is uniform in `ϕ`.
  The scene shows the far-side cone; the histogram cannot.

- **Angles outside `[θ_min, θ_head]`.** Section 7.3.

- **Anything inside the reach.** No orbit at energy `Ẽ` went inside
  the head-on turning point; the counts contain no information
  about the potential there. This is the boundary Section 8's
  `reachability` reports.

---

## 7.8 The result record

Per energy index `k`:

```
  layout          name, n_bins, mode, n_phi
  edges           [n_bins + 1]
  solid_angle     [n_bins]                   (7.1)
  counts          [n_bins] int
  estimate        [n_bins]                   (7.2)
  error           [n_bins]                   (7.3)
  expected        [n_bins]                   (7.4)
  pull            [n_bins]                   (7.5)
  empty           [n_bins] bool
  measured        (θ_min, θ_head)
  flux            F
  n_thrown        N
  n_counted       sum of counts (== N for every first-version
                  potential; a miss is a bug)
  pull_rms        scalar
  position_shift  [n_bins]  mean |θ_position − θ_asymptotic| per
                            bin, for the mode toggle of 7.2
```

Section 8 receives exactly this. It does not receive `n̂_out`, `b̃`,
or anything per particle; the inversion works from the histogram,
as an experiment would.

---

## 7.9 Invariants and tests

- `sum(counts) + (particles outside the measured range) = N`; for
  the first version's potentials the second term is zero.
- `sum(solid_angle) = 2π (cos θ_min − cos θ_head)`.
- For a Coulomb beam with `layout = "log_theta"` and `N ≥ 10⁵`, no
  bin is empty (fixed seed; property expected for any seed).
- Pull RMS is within `3 sqrt(2 / n_bins)` of 1.0 at a fixed seed,
  with a comment naming the seed-independent property (A8.4).
- Attractive and repulsive Coulomb at the same seed give
  bit-identical `counts`.
- `position` mode agrees with `asymptotic` mode to within
  `b̃_max / R̃_detect` per particle, and converges as `R̃_detect`
  doubles.
- No module under `detector/` imports from `potentials/`, `orbits/`,
  or `beam/` beyond the beam record's `flux` and `theta_min` fields
  (A8.6(1)).

---

## 7.10 Alternatives considered

**Bin by landing position by default.** Rejected: it makes the
finite-distance error the default and the exact angle the option.
Kept as `mode = "position"` for the lesson it teaches.

**Compare counts to the center value times `ΔΩ`.** Rejected; 7.6.

**Equal-solid-angle bins by default.** Rejected; 7.4.

**Write zero into unmeasured bins.** Rejected; 7.3.

**A physical beam stop as a separate unmeasured cone.** A real
apparatus has a hole at `θ = 0` for the undeflected beam. The
unmeasured cone from `b̃_max` already plays that role in the first
version, so a separate `theta_stop` setting is deferred; the layout
record's `measured` field is where it would enter.

**Feldman–Cousins or Bayesian upper limits for empty bins.**
Deferred; the one-count arrow of 7.5 is honest and the machinery is
not yet warranted.

**Bin the cross section by particle count (adaptive bins).** Gives
equal statistical error per bin, which is attractive for the
inversion. Rejected for the first version because bin edges that
depend on the data are harder for a student to reason about and
make the expectation (7.4) data-dependent; recorded as a Section 8
refinement.
