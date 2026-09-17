# Design 10. The Run File

> **Parent:** [`../DESIGN.md`](../DESIGN.md) — design index.
> **Status:** draft. `runs/rutherford.toml` and
> `runs/rutherford_disc.toml` are the reference examples.
> **Serves:** G9 (reproducible from a file), G10 (two tiers, one
> file); ARCHITECTURE A4.10 (`run/run_spec.py`,
> `run/serialization.py`, `run/fidelity.py`), A7 (configuration).
> **Depends on:** Sections 1, 3, 4, 5, 7, 8.
> **Implemented by:** pseudocode section 10.

---

## 10.1 Purpose and scope

Everything the tool computes flows from one file. This section
fixes its format (TOML), its tables and keys, how quantities carry
units, how presets and defaults resolve, what is validated at load,
and the rule that decides what belongs in it. It does not repeat
the meaning of each setting — every key points at the section that
owns it.

---

## 10.2 Plain data, two zones, one rule

A run specification is plain data with no behavior. It crosses the
tier boundary unchanged, and it embeds in the results store and in
the HDF5 output verbatim.

Its tables divide into two zones:

- **Physics** — `[potential]`, `[beam]`, `[detector]`,
  `[inversion]`, `[fidelity]`. These determine the results store,
  the counts, and the recovered potential, and the bit-for-bit
  guarantee of Section 6.7 attaches to them.
- **Presentation** — `[view]`. These fix what is shown of a run
  already determined. A regression test perturbs every `[view]`
  key and asserts the store is unchanged.

And the rule (A7): any value that can affect a computed result lives
in the physics zone, and the **resolved** value is what is recorded
— never a reference to a default another machine might fill
differently. The rc file may supply defaults and the command line
may override, but once the driver has resolved the specification it
writes every key back with its actual value. The file a student
saves is complete.

---

## 10.3 Quantities and units

A physical quantity is written one of two ways:

```toml
energies = ["5 MeV", "8 MeV"]     # dimensioned: converted at the boundary
b_max    = 12.0                   # bare: natural units of Section 1
```

A dimensioned string is parsed by `core/units.py` (Section 1.4) and
divided by the run's reference scale for its dimension. A bare
number is taken as already in natural units. Mixing the two in one
list is an error. Which keys accept which dimension is fixed in the
schema table (10.5); a string with the wrong dimension fails at
load, naming the key and both dimensions.

The reference scales themselves come from the preset or from
explicit keys:

```toml
[potential]
preset = "alpha_on_gold"          # supplies m, kappa, E_ref, display units
# or, without a preset:
kind   = "coulomb"
kappa  = "227.6 MeV fm"
mass   = "3727 MeV/c^2"
reference_energy = "5 MeV"
reference_length = "45.5 fm"      # optional; default per Section 1.3
```

A preset key beside an explicit key is allowed and the explicit key
wins — that is how a student changes `Z₂` without editing a preset.
The resolved file records every value.

---

## 10.4 Format and versioning

TOML, because it is readable, has typed values and nested tables,
is in the standard library from Python 3.11 (`tomllib`, with the
`tomli` backport on 3.10), and is what the rigid-body tool and
`sabsim` already use in this group. Writing uses `tomli-w`.

The first key of every file is `schema = 1`. The loader refuses a
file with a newer schema than it knows and upgrades an older one
by a documented rule per version, writing the upgraded file back
only on request. A file without `schema` is treated as version 1
with a warning.

---

## 10.5 The schema

Keys, their dimension (`—` for none, `nat` for natural-unit bare
number allowed), default, and owning section. A default of `req`
means required.

### `[potential]`

| Key | Type | Default | Section |
| --- | --- | --- | --- |
| `kind` | `"coulomb"`; later `"yukawa"`, `"hard_sphere"`, |
| | `"well"` | `req` | 2, FD3 |
| `preset` | name, or absent | absent | 1.5 |
| `sign` | `+1` or `−1` | from preset | 2 |
| `kappa`, `mass` | energy·length, mass | from preset | 1.5 |
| `reference_energy` | energy | first of `energies` | 1.2 |
| `reference_length` | length | per potential | 1.3 |

### `[beam]`

| Key | Type | Default | Section |
| --- | --- | --- | --- |
| `energies` | energy or list | `req` | 3.2 |
| `energy_distribution` | `"delta"` | `"delta"` | 3.2, FD2 |
| `layout` | `"annuli"` or `"disc"` | `req` | 3.3 |
| `annuli` | list of `{b, db, n_azimuth}`; `b`, `db` |
| | length/nat | `req` if annuli | 3.3 |
| `n_particles` | int | `req` if disc | 3.3 |
| `b_min`, `b_max` | length/nat | `0`, `req` | 3.3, 3.4 |
| `stratify` | bool | `false` | 3.3 |
| `seed` | int | `req` if disc | 3.5 |

### `[detector]`

| Key | Type | Default | Section |
| --- | --- | --- | --- |
| `radius` | multiple of `r_max` | `2.0` | 7.2 |
| `mode` | `"asymptotic"` or `"position"` | `"asymptotic"` | 7.2 |
| `layout` | `"log_theta"`, `"uniform_theta"`, |
| | `"equal_solid_angle"` | `"log_theta"` | 7.4 |
| `n_bins` | int | `40` | 7.4 |
| `n_phi` | int | `1` | 7.2, FD4 |

### `[inversion]`

| Key | Type | Default | Section |
| --- | --- | --- | --- |
| `enabled` | bool | `true` if disc | 8 |
| `assume_sign` | `+1` or `−1` | `+1` | 8.3 |
| `tail_model` | `"coulomb"`, `"power"`, `"zero"` | `"coulomb"` | 8.5 |
| `n_resample` | int | `50` | 8.7 |

### `[fidelity]`

| Key | Type | Default | Section |
| --- | --- | --- | --- |
| `orbit_provider` | `"auto"`, `"analytic"`, `"numerical"` | `"auto"` | 4.2 |
| `integrator` | `"dop853"`, `"rk45"`, `"verlet"` | `"dop853"` | 4.9 |
| `rtol`, `atol` | float | `1e-10`, `1e-12` | 4.9 |
| `step` | nat time | `req` if verlet | 4.9 |
| `r_max` | length/nat | `req` | 4.4 |
| `asymptote_tolerance` | float | `1e-6` | 4.4 |
| `n_samples` | int, `0` = batch | `400` | 6.2, 6.5 |
| `trace_angle_deg` | float | `2.0` | 4.10 |
| `trace_points_max` | int | `2000` | 4.10 |
| `n_deflection_points` | int | `400` | 5.4 |

### `[view]` (presentation zone)

| Key | Type | Default | Section |
| --- | --- | --- | --- |
| `palette` | `"light"`, `"dark"`, `"colorblind"` | rc | 11 |
| `camera` | `{azimuth_deg, elevation_deg, distance}` | rc | 11 |
| `tracked_particle` | int | `0` | 12 |
| `panels` | list of panel names | rc | 11 |

### `[meta]` (written by the driver on resolve; ignored on load)

| Key | Meaning |
| --- | --- |
| `resolved_by` | tool version and timestamp |
| `source` | the file this was resolved from, if any |
| `git_commit` | of the source tree |

---

## 10.6 Validation at load

Every rule below fails at load with a message naming the key, the
value, and the section that explains the rule. None is coerced.

- `schema` known (10.4).
- Every key in the schema table; an unknown key is an error, not a
  warning, because a misspelled `n_particle` that silently fell
  back to a default is exactly the failure G9 exists to prevent.
- Dimensions match (10.3).
- `energies` non-empty, all positive, no duplicates (3.2).
- `layout = "disc"` has `seed`, `n_particles ≥ 1`, `b_min < b_max`;
  `layout = "annuli"` has a non-empty list with `b ≥ 0`, `db > 0`,
  `n_azimuth ≥ 1` (3.3).
- The potential admits every `b` the beam throws (3.4): `b = 0`
  refused for attractive Coulomb.
- `r_max` exceeds `b_max` (or the largest annulus `b + db`) by a
  factor the rc file sets (default 3), so `Z̃₀` of Section 4.6
  exists and the entry plane is well inside the sphere.
- `radius ≥ 1` for the detector (7.2).
- `n_bins ≥ 2`; `mode` and `layout` from their enumerations.
- `integrator = "verlet"` has `step`.
- The memory budget of Section 6.4, computed from these values, is
  under the rc cap — reported as a number with the cap and the
  setting to change.

---

## 10.7 Precedence and the command line

```
  rc file defaults  <  run file  <  command-line overrides
```

The rc file (`scsimrc.py`, per the template's `XYZrc.py` idiom)
holds machine-dependent things: `max_store_bytes`, default palette
and window size, the default `n_azimuth` for the shorthand annulus
list, the `r_max / b_max` safety factor, output directories, and
cluster settings for the batch tier. It never holds physics
defaults that the schema table above does not already state.

It is searched for in three places, first found wins: the working
directory, so that a user can keep a modified copy beside their
data; the directory named by `$SCATTERING_RC`, for a machine-wide
copy; and the package itself, `scattering/defaults/scsimrc.py`. The
last is the documented set of defaults, and it is inside the package
rather than beside the entry-point script because an installed copy
of the tool (ARCHITECTURE 9.1, Route B) has no script directory: the
one location that exists on both routes is the package. It follows
that the search cannot fail, and that a user never needs to know
where the package is installed: `scsim --write-rc` (Section 12.13)
puts a copy in the working directory to edit.

The command line accepts a run file path and a small set of
overrides of the form `--set beam.n_particles=50000`, applied after
loading and before resolving, so that a sweep over one parameter
from a shell loop does not need one file per value. Every override
lands in the resolved specification like any other value. The
entry-point scripts log the full command line to `command`
(`CLAUDE.md`), so the override is recoverable even without the
resolved file.

---

## 10.8 Resolving and writing back

`run_spec.py` loads, validates, applies the rc defaults and the
overrides, computes derived values (the reference scales, `Z̃₀`,
`θ_min` per energy), and produces a **frozen** specification — an
immutable record with every schema key present. `serialization.py`
writes it back as TOML with the `[meta]` table filled, in schema
order, with a comment header naming the source file and the tool
version. The written file round-trips: loading it produces an
equal frozen specification, and that is a test.

The frozen specification, not the TOML text, is what the driver
runs from and what the results store carries (Section 6.3,
provenance). The TOML text is also embedded in the HDF5 output
(Section 13) so that a result file is self-describing without the
tool.

---

## 10.9 Invariants and tests

- Every example under `runs/` loads, validates, resolves, writes
  back, and round-trips to an equal specification.
- Every rule in 10.6 has a test that violates it and checks the
  message names the key.
- Perturbing any `[view]` key leaves the results store bit-identical
  (10.2).
- A file with an unknown key is refused.
- A `disc` file without `seed` is refused; with `seed`, two loads
  produce identical beams (3.5).
- A dimensioned and a bare value for the same key resolve to the
  same natural-unit number when they should (a `"45.5 fm"` `b`
  under `alpha_on_gold` equals a bare `1.0` to the precision of the
  constants).

---

## 10.10 Alternatives considered

**YAML.** Rejected: no standard-library reader, implicit typing
surprises (`no` is a boolean), and the group already uses TOML.

**JSON.** Rejected: no comments, and a run file a student edits by
hand needs comments more than it needs anything else.

**Physics defaults in the rc file.** Rejected under A7; the schema
table is the single source of defaults, and the rc file never
decides physics.

**Warn on unknown keys.** Rejected; 10.6.

**Separate files for beam, detector, and potential.** Composable,
but the one-file rule is what makes "hand a student the file"
mean something; rejected.
