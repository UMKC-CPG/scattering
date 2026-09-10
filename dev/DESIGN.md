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
   natural units, scaling, and the real-unit presets. *draft*
2. [`design/02-coulomb-closed-forms.md`](design/02-coulomb-closed-forms.md)
   — Coulomb orbit, deflection function, cross section. *draft*
3. [`design/03-beam.md`](design/03-beam.md) — beam energies, impact
   parameter sampling, the seed. *draft*
4. [`design/04-orbit-integration.md`](design/04-orbit-integration.md)
   — planar equations of motion, integrator, `R_max`, the ensemble
   clock, embedding into the scene. *draft*
5. [`design/05-deflection-and-cross-section.md`](
   design/05-deflection-and-cross-section.md) — `θ(b)` by
   quadrature, `dσ/dΩ`, solid angle, the annulus-to-cone map. *draft*
6. [`design/06-results-store.md`](design/06-results-store.md) —
   array layout, memory budget, materialization, the read interface.
   *draft*
7. `design/07-detector.md` — detector sphere, bins, counting
   statistics, the unmeasured forward cone. *planned*
8. `design/08-inversion.md` — counts → `dσ/dΩ` → `θ(b)` → `V(r)`;
   reachability and the unknown interior. *planned*
9. `design/09-conservation-and-error-budget.md` — drift monitor;
   numerical versus statistical error. *planned*
10. `design/10-run-file.md` — the TOML schema and precedence.
    *planned*
11. `design/11-scene-and-geometry.md` — annulus, cone, orbit plane,
    probe-depth sphere, palettes. *planned*
12. `design/12-scrubber-and-session.md` — time and energy scrubbing,
    the interactive loop. *planned*
13. `design/13-batch-and-hdf5.md` — Tier 2 output layout. *planned*

Status is one of: planned, draft, reviewed, implemented, superseded.
A superseded section keeps its number and file; its header names the
replacement. Numbers are never reused.

Section 8 depends on a spike (`dev/spikes/`) verifying the inversion
formulas against the literature before they are written into DESIGN.
Section 2's closed forms are already verified by
`dev/spikes/coulomb_closed_forms.py`.

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
