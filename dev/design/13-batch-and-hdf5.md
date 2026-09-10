# Design 13. The Batch Tier and HDF5 Output

> **Parent:** [`../DESIGN.md`](../DESIGN.md) — design index.
> **Status:** draft; designed now, built after `v1.0-classroom`
> (ARCHITECTURE A10).
> **Serves:** G9 (reproducible), G10 (two tiers, one file);
> ARCHITECTURE A3 (execution model), A4.11 (`sinks/`), A4.13
> (`scbatch.py`), A9.4 (data interchange).
> **Depends on:** Sections 6, 7, 8, 10.
> **Implemented by:** pseudocode section 13.

---

## 13.1 Purpose and scope

The batch tier runs the same driver on the same run file with no
display and writes the results store to disk. Its reason to exist
is statistics: the inversion spike found that a convincing
classroom recovery of `V(r)` wants `10⁵` to `10⁶` particles, which
is a scheduled job, not an interactive wait. This section fixes the
HDF5 layout, what a batch run stores, how a stored run is read back
into the interactive tier, and the batch entry point. The sink
interface it uses is the one A4.11 names.

---

## 13.2 The sink interface

A sink consumes a *completed* results store (A6.5). One method:

```
  consume(store) → None
```

`live_sink.py` hands the store to the session (Section 12);
`hdf5_sink.py` writes it (13.3); `video_sink.py` (later) drives the
session's loop offscreen and encodes frames. Several may be
attached at once — an interactive session that also records. None
may write to the store (Section 6.7).

The driver does not stream partial results to a sink during the
build. The store is small enough to hold and complete before it is
consumed, the batch run is minutes not days, and a partial file
from an interrupted job is worse than none. This is a deliberate
difference from the rigid-body tool, whose open-ended runs need a
streaming sink; here the finite run makes a whole-store sink the
simpler and safer choice.

---

## 13.3 The HDF5 layout

One file per run, mirroring Section 6.3 group for group and name
for name, so that a reader of either document knows the other:

```
  /                       attrs: schema, created, versions,
                                 git_commit, tool
  /run_spec               the resolved TOML text, verbatim (str)
  /beam/                  Section 3.6: impact_parameter, azimuth,
                          annulus_index, annulus_width, flux,
                          theta_min, layout, seed, stratify
  /energies               [K]
  /trajectory/            present only when n_samples > 0
      time_grid           [K, S]
      position            [K, N, S, 3]   chunked (1, N, S, 3), gzip
      velocity            [K, N, S, 3]
      polar               [K, N, S, 2]
      phase               [K, N, S]  int8
  /particle/              turning_point, turning_point_q,
                          deflection, out_direction, time_offset,
                          entry_index, exit_index, energy_drift,
                          angmom_drift, finite_radius   — all [K, N…]
  /energy/<k>/            per energy index k
      deflection_table    b, Theta, dTheta_db, r_min
      xsec_table          theta, dsdo, flags
      mirror_table        (if present)
      annulus_map         per-annulus record
      provider, provider_check
  /trace/<k>/<i>          [n_i, 3], present when traces were kept
  /detector/<k>/          Section 7.8, every field
  /inversion/<k>/         Section 8.9, every field
  /error_budget/<k>/      Section 9.8
  /geometry/<k>/          rings, cones, probe-depth sphere as
                          polydata-ready arrays, for ParaView
```

Chunking is one energy slab per chunk on the trajectory arrays so
that reading one energy is one contiguous read, and gzip level 4
on everything larger than a kilobyte. `float64` throughout, with an
`--export-float32` option on `scbatch.py` that halves the
trajectory block *in the file only* (Section 6.8); the attribute
`/trajectory@precision` records which.

The resolved run specification is stored as text, not as
attributes, so that a file is self-describing to a reader with no
knowledge of the tool: `h5dump` on `/run_spec` prints the TOML that
made it.

---

## 13.4 XDMF companion

When `n_samples > 0` the sink also writes `<name>.xmf`, an XDMF
descriptor pointing into the HDF5 file, so that ParaView opens the
run as a time series: a polyvertex set per frame with `position`,
`velocity`, `polar`, and `phase` as point attributes, one temporal
collection per energy index, and the `/geometry/<k>/` rings, cones,
and spheres as static polydata. This is the group's established
path for large trajectory data and needs no code beyond the
descriptor.

---

## 13.5 Reading back

`results_store.from_hdf5(path)` reconstructs a frozen store from
the file, with every array read lazily per energy on first access
so that a `10⁶`-particle batch file opens instantly and the
interactive tier can scrub its detector and inversion panels
without loading a trajectory block it does not have. A store read
from file satisfies the same read interface (Section 6.6) as one
built in memory, and the session cannot tell them apart.

This is the batch-to-interactive path of G10: explore
interactively with `n_particles = 500`, save the run file, submit
it with `n_particles = 10⁶` and `n_samples = 0`, and open the
result in the same session to see the inversion with real
statistics. A run file's physics zone is identical between the two
except for the two fidelity values, and the session shows both
stores' error budgets side by side (Section 9) so that the change
in the statistical column, and the constancy of the numerical one,
is the last lesson of P3.

---

## 13.6 The batch entry point

```
  scbatch.py RUNFILE [--set key=value …] [--out DIR]
             [--export-float32] [--traces N]
```

Follows the template's `XYZ.py` idiom: `scbatchrc.py` defaults,
`--set` overrides as Section 10.7, the command logged to `command`.
It resolves the specification, prints the budget, builds the store
with a progress line per energy, and attaches an `hdf5_sink` (and
nothing else). Output goes to `DIR/<runfile-stem>.h5` and `.xmf`,
with the resolved run file written beside them as
`<stem>.resolved.toml`.

A Slurm submission template lives in `share/scbatch.sbatch`,
activating the shared environment (ARCHITECTURE A9.1) and calling
the script; `--traces N` keeps `N` traces at `n_samples = 0` for a
figure, sampled evenly in `b̃`.

---

## 13.7 Invariants and tests

- A store written and read back is equal, array by array, to the
  original, with `float64` export (round-trip test on a small run).
- With `--export-float32`, the trajectory arrays agree to `1e-6`
  relative and everything else is exact.
- `/run_spec` reloads to a specification equal to the one that
  produced the file (Section 10.9).
- A file with `n_samples = 0` has no `/trajectory` group and opens
  in the session with the detector and inversion panels live.
- The XDMF descriptor validates and names every dataset it refers
  to (a structural test; ParaView itself is not in the suite).
- `scbatch.py` on `runs/rutherford_disc.toml` produces a file whose
  `/detector/0/counts` equals the interactive tier's counts for the
  same file and seed, bit for bit.

---

## 13.8 Alternatives considered

**Stream partial results during the build.** Rejected; 13.2.

**NetCDF or Zarr.** Both fine; HDF5 is what the cluster, ParaView,
and the rigid-body tool already use, and `h5py` is in the shared
environment.

**Store the run specification as HDF5 attributes.** Rejected; text
is what a reader without the tool can use (13.3).

**Write the detector and inversion results only, not the
per-particle block.** Rejected: the per-particle `deflection` and
`out_direction` are what make a batch file re-binnable in the
session with a different detector layout without rerunning the
physics (Section 12.7).
