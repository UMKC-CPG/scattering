# Pseudocode — Index

> **Document hierarchy:** VISION → ARCHITECTURE → DESIGN →
> **PSEUDOCODE** → Code. For the rationale behind these algorithms
> see the corresponding section under `design/`.

---

**This file is an index, not the pseudocode.** Each numbered section
lives in its own file under `dev/pseudocode/`. Read this table to
find the section you need, then read only that file.

**This is the gate.** No file under `src/` is edited until the
governing section here exists and already describes the change. See
"Chain Discipline" in `../CLAUDE.md`. When beginning a coded task,
name the section from this table that governs it.

## Sections

Each entry: number, file, what it governs under `src/scattering/`,
the design section it implements, status.

1. [`pseudocode/01-natural-units.md`](pseudocode/01-natural-units.md)
   — governs `core/natural_units.py`, `core/units.py`,
   `core/presets.py`. Design 1. *implemented*
2. [`pseudocode/02-coulomb.md`](pseudocode/02-coulomb.md) — governs
   `potentials/potential_interface.py`, `potentials/coulomb.py`.
   Design 2. *implemented*
3. [`pseudocode/03-beam.md`](pseudocode/03-beam.md) — governs
   `beam/beam_spec.py`, `beam/impact_sampler.py`,
   `beam/energy_sampler.py`. Design 3. *implemented*
4. [`pseudocode/04-orbits.md`](pseudocode/04-orbits.md) — governs
   `orbits/orbit_provider.py`, `orbits/equations_of_motion.py`,
   `orbits/integrators.py`, `orbits/analytic_orbits.py`,
   `orbits/turning_point.py`, `orbits/embedding.py`. Design 4.
   *implemented*
5. [`pseudocode/05-deflection.md`](pseudocode/05-deflection.md) —
   governs `deflection/deflection_function.py`,
   `deflection/cross_section.py`, `deflection/solid_angle.py`.
   Design 5. *implemented*
6. [`pseudocode/06-results-store.md`](pseudocode/06-results-store.md)
   — governs `run/results_store.py`, `run/driver.py`. Design 6.
   *implemented*
7. [`pseudocode/07-detector.md`](pseudocode/07-detector.md) — governs
   `detector/` and the panel, geometry and session grafts it names.
   Design 7. *draft*
8. `pseudocode/08-inversion.md` — `inversion/`. Design 8. *planned*
9. [`pseudocode/09-error-budget.md`](pseudocode/09-error-budget.md)
   — governs `analysis/` and the error-budget panel. Design 9.
   *draft*
10. [`pseudocode/10-run-file.md`](pseudocode/10-run-file.md) —
    governs `run/run_spec.py`, `run/serialization.py`,
    `run/schema.py`, `run/rc.py`, `scripts/scsimrc.py`, and the
    resolution the driver hands over. Design 10. *implemented*
11. [`pseudocode/11-scene.md`](pseudocode/11-scene.md) — governs
    `geometry/` and `render/`. Design 11. *implemented*
12. [`pseudocode/12-session.md`](pseudocode/12-session.md) —
    governs `ui/` and `scripts/scsim.py`. Design 12. *implemented*
13. `pseudocode/13-batch.md` — `sinks/`, `scripts/scbatch.py`.
    Design 13. *planned*

Status is one of: planned, draft, reviewed, implemented, superseded.

## Conventions

**Section numbers track DESIGN where they can.** Pseudocode section N
implements design section N by default. Where one design section
needs several algorithms, use N.1, N.2 rather than breaking the
correspondence, and say so in the Design column.

**Use the names the code will use.** The variable names here should
be the ones that appear in `src/`, following the naming rules in
`../CLAUDE.md`. Pseudocode that renames everything cannot be checked
against the implementation by eye, which is the whole point of it.

**Language-agnostic, but concrete.** No language syntax, but no
hand-waving either: loop bounds, index origins, allocation, and error
paths are all specified. "Compute the overlap" is not pseudocode.

**Never edit upward to match code.** A disagreement between this
document and the source means the source is wrong, unless the source
has first been verified against DESIGN. See `../CLAUDE.md`.
