# Design 6. The Results Store

> **Parent:** [`../DESIGN.md`](../DESIGN.md) — design index.
> **Status:** draft.
> **Serves:** G4 (exact scrubbing), G5 (energy axis), G9
> (reproducible), G10 (two tiers), P5 (precompute, then view);
> ARCHITECTURE A3 (execution model), A4.10 (`run/results_store.py`),
> A6.3 (the results-store boundary), A8.6(3) (determinism).
> **Depends on:** Sections 3, 4, 5.
> **Implemented by:** pseudocode section 6.

---

## 6.1 Purpose and scope

The results store is the precomputed run: every sample of every
particle at every energy, plus everything the stages of Section 5
attached, plus the beam and the run specification that produced it.
It is written once by the driver and then read — by the scrubber,
the geometry, the detector, the inversion, and the sinks. This
section fixes its layout, its memory budget, what is and is not
materialized, and the read interface behind which those choices
hide (A6.3).

It does not fix the HDF5 file layout (Section 13), though the names
here are chosen so that Section 13 can mirror them one to one.

---

## 6.2 The scene-time grid

Every stored sample is at a *scene time* on one clock per energy
(Section 4.6). At energy index `k`:

```
  time_grid[k, n]   n = 0 … n_samples − 1
                    uniform from 0 to t̃_end[k]
```

`t̃_end[k]` is the time at which the slowest particle at that energy
reaches the detector radius `R̃_detect` (Section 7); every particle
is therefore in the scene for the whole grid — inbound free flight,
the integrated orbit, outbound free flight (Section 4.6) — and the
frame at any `n` is a complete picture of the beam. The grid differs
between energies because the speeds differ, so the energy scrubber
(Section 12) moves between energies at equal *fractions* of the
run, `n / n_samples`, not at equal `t̃`.

`n_samples` is a fidelity setting (Section 10). Its default for the
interactive tier, 400, makes a frame step about a quarter of a
percent of the run; the batch tier may set it to 0 (6.5).

---

## 6.3 Layout

All arrays are `float64` unless stated, `C`-ordered, with the energy
index first so that a single energy is a contiguous slab, and the
particle index second so that a single frame — one time, all
particles — is a strided read the renderer can take in one call.
`K = n_energies`, `N = n_particles`, `S = n_samples`.

### The trajectory block

```
  position   [K, N, S, 3]    scene coordinates (4.3)
  velocity   [K, N, S, 3]    scene velocities
  polar      [K, N, S, 2]    (r̃, φ) in the orbital plane (4.5)
  phase      [K, N, S] int8  −1 inbound free flight,
                              0 integrated orbit,
                             +1 outbound free flight
```

`polar` is redundant with `position` and is stored anyway: G3 puts
`r̃` and `φ` on screen every frame, `φ` needs the pericenter
direction to compute, and computing it per frame in the render loop
would move physics into presentation (P11). `phase` lets the scene
draw the free-flight legs differently from the integrated orbit
(P14: the free flight *is* an approximation, labeled).

### The per-particle block

Quantities that do not vary along the orbit, from Sections 3–5:

```
  impact_parameter  [N]         b̃, the same at every energy
  azimuth           [N]         ϕ
  annulus_index     [N] int     ring id, or −1
  turning_point     [K, N]      r̃_min, from the orbit provider
  turning_point_q   [K, N]      r̃_min, from the root of g (5.2)
  deflection        [K, N]      Θ, signed, from Section 5
  out_direction     [K, N, 3]   n̂_out of (4.4)
  time_offset       [K, N]      τ of (4.6)
  entry_index       [K, N] int  first n with phase == 0
  exit_index        [K, N] int  first n with phase == +1
  energy_drift      [K, N]      max |Ẽ_sample − Ẽ| / Ẽ (P2)
  angmom_drift      [K, N]      max |L̃_sample − L̃| / L̃
  finite_radius     [K, N]      angle between exit velocity and
                                out_direction (4.4, 4.7)
```

### The per-energy block

```
  energies          [K]         Ẽ_k, in run-file order
  time_grid         [K, S]
  theta_min         [K]         Section 3.3
  deflection_table  [K]  record (b̃, Θ, dΘ/db̃, r̃_min)      (5.4)
  xsec_table        [K]  record (θ, dσ/dΩ, flags)          (5.5)
  mirror_table      [K]  record, or absent                 (5.6)
  annulus_map       [K]  record per annulus                (5.7)
  provider          [K]  str   "analytic" or "numerical"
  provider_check    [K]         largest closed-form vs
                                quadrature discrepancy (5.4)
```

The tables are ragged (their lengths are fidelity settings, not
`N` or `S`) and are held as small records rather than padded arrays.

### The trace block

Traces (4.10) are one polyline per particle per energy, of varying
length, dense where the path curves:

```
  trace_points   [K, N]  → array [n_i, 3]
```

held as a list of arrays, since padding to the longest would waste
the memory that adaptive sampling saved. Their total point count is
reported in the budget (6.4).

### Provenance

```
  run_spec          the frozen, fully resolved run specification
                    (every default filled in; A7)
  beam              the beam record of Section 3.6
  created           ISO timestamp
  versions          scattering, numpy, scipy, python
  git_commit        of the source tree, and whether it was dirty
```

The resolved `run_spec` is what G9 promises: the store carries
enough to regenerate itself exactly, and the batch tier writes it
into the HDF5 file verbatim (Section 13).

---

## 6.4 The memory budget

The trajectory block dominates. In bytes,

```
  trajectory ≈ K · N · S · (3 + 3 + 2) · 8  +  K · N · S · 1
             ≈ 65 · K · N · S                                   (6.1)
```

with the per-particle block at `≈ 150 · K · N` and traces at
`24 · (total trace points)`. Defaults for the interactive tier,
`K = 5`, `N = 500`, `S = 400`, give about 65 MB for trajectories
and a few MB for the rest — comfortable. The batch tier's
`N = 10⁶` at `S = 400` would be 130 GB and is refused; the batch
tier sets `S = 0` (6.5).

**The budget is computed before the run, from the run file alone,
and shown.** The driver evaluates (6.1) plus the trace cap from the
fidelity settings, prints it, and refuses to proceed if it exceeds
`max_store_bytes` from the rc file (default 4 GB), naming the
setting to change. A student who asks for `N = 10⁵` interactively
learns what that costs before waiting for it, not after.

---

## 6.5 What is materialized, and when

**The first version materializes everything in 6.3 unconditionally
when `S > 0`.** A6.3 permits an on-demand implementation that
regenerates samples from orbit parameters; it is not built now, for
three reasons: the renderer takes a full frame as one array anyway,
so on-demand generation would rebuild that array every frame; the
budget of 6.4 is comfortable for the interactive tier; and a
materialized store is the simplest thing to make deterministic
(6.7) and to write to HDF5. The read interface (6.6) is what makes
the choice reversible.

**`n_samples = 0` is the batch mode.** With `S = 0` the trajectory
block is empty, and the store holds the per-particle, per-energy,
and provenance blocks only. Everything the detector (Section 7) and
the inversion (Section 8) need is in those blocks — `deflection`
and `out_direction` above all — so a batch run of `10⁶` particles
needs no trajectory at all. Traces are likewise skipped at `S = 0`
unless `trace_points > 0` is set explicitly, which lets a batch run
keep a few hundred paths for a figure.

**The integrated orbit is stored on the same grid as the free
flight.** An alternative is to store integrated samples densely and
free flight not at all, reconstructing the straight legs on demand.
Rejected: it makes the frame at time `n` a computation instead of a
read, and the saving is small because the free-flight legs are
short compared with the orbit at any sensible `R̃_max`.

---

## 6.6 The read interface (A6.3)

Every consumer speaks to the store through these calls and no
attribute access:

```
  frame(k, n)              → position[k, :, n, :]      one frame
  frame_polar(k, n)        → polar[k, :, n, :]
  particle(k, i)           → the full sample history of one particle
  final_directions(k)      → out_direction[k]           for the detector
  deflection_of(k)         → (impact_parameter, deflection[k])
  tables(k)                → the per-energy records
  trace(k, i)              → trace_points[k][i]
  drift(k)                 → (energy_drift[k], angmom_drift[k],
                              finite_radius[k])
  time_of(k, n)            → time_grid[k, n]
  n_energies, n_particles, n_samples
  size_bytes()
  provenance()
```

Returned arrays are read-only views (`writeable = False`); a
consumer that needs to modify one copies it. This is what makes 6.7
enforceable rather than hoped for.

An on-demand implementation later would provide the same calls
with `frame` computed rather than sliced, and nothing above the
interface would know.

---

## 6.7 Immutability and determinism

The store is built by the driver and **frozen** on completion: every
array is marked read-only and the object exposes no setter. From
that moment the scrubber, the renderer, and every analysis stage
read and never write. This is P5 in code, and it is what makes
A8.6(3) a mechanical test:

> Build the store twice from one run file: every array is equal
> bit for bit. Build it once and scrub it in any sequence of
> `frame` calls: every array is unchanged.

Determinism across builds rests on: the seed and the raw-uniform
sampling of Section 3.5; the integrator's adaptive step sequence
being a pure function of its inputs and tolerances (true of
`solve_ivp`); and the quadrature of Section 5 likewise. None of
these consults the clock, thread scheduling, or the machine. The
test runs on every commit.

Determinism across *machines* is a weaker claim — floating-point
reductions in NumPy can differ between BLAS builds — and the design
promises it only to the tolerance of the regression suite, not bit
for bit. The provenance block records the versions so that a
discrepancy can be attributed.

---

## 6.8 Precision

`float64` throughout. The conservation drift of P2 is measured from
the stored samples, and a `float32` store would put the storage
rounding (about `1e-7` relative) above the integrator drift it is
meant to display. A `float32` *export* for a bulky batch file is a
Section 13 option applied at write time; it never touches the
in-memory store.

---

## 6.9 Invariants and tests

- `phase` is nondecreasing along `n` for every particle, and takes
  each of its three values at least once when `S > 0`.
- `position[k, i, n]` for `phase == ±1` lies on the straight
  asymptote to floating-point precision (free flight is exact).
- `|position[k, i, entry_index]| = R̃_max` and likewise at
  `exit_index`, to the integrator's event tolerance.
- `polar[k, i, n, 0]` equals `|position[k, i, n]|` at every sample.
- `turning_point` and `turning_point_q` agree to the integrator
  tolerance; `finite_radius` is at that tolerance for an analytic
  start and scales as `1 / R̃_max` for a corrected start (4.12).
- Every array is read-only after freezing; writing raises.
- `size_bytes()` agrees with the pre-run estimate of 6.4 to within
  the trace cap.
- Two builds from one run file are bit-identical; a build is
  unchanged by any sequence of reads (A8.6(3)).

---

## 6.10 Alternatives considered

**Generate samples on demand from orbit parameters.** Permitted by
A6.3 and rejected for the first version; see 6.5.

**Store one shared time grid across energies.** Rejected: at higher
energy the run is shorter, and a shared grid would either waste
samples on the fast run or under-sample the slow one. Equal
fractions of the run (6.2) is the right notion of "the same moment"
across a sweep.

**Store only positions and derive velocities by differencing.**
Rejected: the telemetry shows speed and kinetic energy, and a
difference quotient on a 400-sample grid is not the velocity — at
an attractive pericenter it is not even close.

**`float32` storage.** Rejected; see 6.8.

**Pad traces to a fixed length.** Rejected; see 6.3, trace block.

**A database or memory-mapped file rather than in-memory arrays.**
Rejected for the interactive tier as needless; the batch tier's
HDF5 output (Section 13) is the persistent form, and reading it back
into this same store structure is the batch-to-interactive path.
