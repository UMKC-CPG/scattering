# Design — Index

> **Document hierarchy:** VISION → ARCHITECTURE → **DESIGN** →
> PSEUDOCODE → Code. For goals and principles see `VISION.md`; for
> the chain of stages, the module map, and the boundaries see
> `ARCHITECTURE.md`. Principles are cited as `P<n>`, goals as `G<n>`,
> architecture sections as `A<n>`.

---

**This file is an index, not the design.** Each numbered section
lives in its own file under `dev/design/`. Read this table to find
the section you need, then read only that file.

## Sections

Each entry: number, file, topic, status.

1. [`design/01-natural-units.md`](design/01-natural-units.md) —
   natural units, scaling, and the real-unit presets. *implemented*
2. [`design/02-coulomb-closed-forms.md`](design/02-coulomb-closed-forms.md)
   — Coulomb orbit, deflection function, cross section. *implemented*
3. [`design/03-beam.md`](design/03-beam.md) — beam energies, impact
   parameter sampling, the seed. *implemented*
4. [`design/04-orbit-integration.md`](design/04-orbit-integration.md)
   — planar equations of motion, integrator, `R_max`, the ensemble
   clock, embedding into the scene. *implemented*
5. [`design/05-deflection-and-cross-section.md`](
   design/05-deflection-and-cross-section.md) — `θ(b)` by
   quadrature, `dσ/dΩ`, solid angle, the annulus-to-cone map. *implemented*
6. [`design/06-results-store.md`](design/06-results-store.md) —
   array layout, memory budget, materialization, the read interface.
   *implemented*
7. [`design/07-detector.md`](design/07-detector.md) — detector
   sphere, bin layouts, counts and pulls, the unmeasured cones.
   *implemented*
8. [`design/08-inversion.md`](design/08-inversion.md) — counts →
   `dσ/dΩ` → `Θ(b)` → `V(r)`; the sign assumption, the tail model,
   reachability, error bands. *draft*
9. [`design/09-conservation-and-error-budget.md`](
   design/09-conservation-and-error-budget.md) — the three kinds of
   error, measured and never combined. *implemented*
10. [`design/10-run-file.md`](design/10-run-file.md) — the TOML
    schema, units, validation, precedence, write-back. *implemented*
11. [`design/11-scene-and-geometry.md`](design/11-scene-and-geometry.md)
    — drawables, the annulus and cone, probe-depth sphere, palettes
    and the redundancy rule. *implemented*
12. [`design/12-scrubber-and-session.md`](
    design/12-scrubber-and-session.md) — viewing vs run controls,
    the loop, time and energy scrubbing. *implemented*
13. [`design/13-batch-and-hdf5.md`](design/13-batch-and-hdf5.md) —
    the sink, HDF5 layout, XDMF, read-back, `scbatch.py`. *draft*

Status is one of: planned, draft, reviewed, implemented, superseded.
A superseded section keeps its number and file; its header names the
replacement. Numbers are never reused.

Section 2's closed forms are verified by
`dev/spikes/coulomb_closed_forms.py`; the inversion chain that
Section 8 will specify, and the binning rules Section 7 uses, are
verified by `dev/spikes/firsov_inversion.py`.

## Conventions

**Numbering is stable.** Sections are cited by number from
PSEUDOCODE, from TODO, and from source comments. Append rather than
renumber.

**One topic per file.** A section file passing roughly 1,500 lines is
describing more than one thing; split it and add the row.

**Cite upward.** A design choice forced by a VISION principle names
it; one forced by an architectural boundary names the section.

**Record what was rejected.** The alternative that was considered and
dropped, with the reason, is what stops it being proposed again.

## Notation

Fixed here and used in every section and in PSEUDOCODE.

| Symbol | Meaning |
| --- | --- |
| `m` | Projectile mass |
| `κ` | Coulomb strength in `V = κ / r`; `κ > 0` repulsive, |
| | `κ < 0` attractive |
| `s` | `sgn(κ)`, `±1` |
| `E` | Beam energy, `½ m v_∞²`; always `> 0` |
| `v_∞` | Asymptotic speed |
| `b` | Impact parameter, `≥ 0` |
| `L` | Angular momentum magnitude, `m v_∞ b` |
| `r, φ` | Polar coordinates in the orbital plane, `φ` measured |
| | from pericenter |
| `r_min` | Distance of closest approach (turning point) |
| `φ_∞` | Polar angle of an asymptote, measured from pericenter |
| `Θ` | Signed deflection angle, `π − 2 φ_∞`; `Θ < 0` means |
| | bent toward the center |
| `θ` | Scattering angle, the magnitude of `Θ`, in `[0, π]`; |
| | what a detector sees |
| `e` | Orbit eccentricity, `> 1` for every scattering orbit |
| `ℓ₀, E_ref, t₀` | Reference length, energy, time (Section 1) |
| `x̃` | Any quantity `x` in natural units (Section 1) |
| `Ω` | Solid angle; `dΩ = sin θ dθ dϕ` |
| `ϕ` | Azimuth about the beam axis (distinct from orbital `φ`) |
| `dσ/dΩ` | Differential cross section |
| `R_max` | Radius at which orbits begin and end |

The beam travels along `+ẑ`. Azimuth `ϕ` is measured about `ẑ`. The
polar angle `θ` of a scattered particle is measured from `+ẑ`, so an
undeflected particle has `θ = 0` and a back-scattered one `θ = π`.
