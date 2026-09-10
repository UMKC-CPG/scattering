# Task List

> **Document hierarchy:** this is a work queue, not a level of the
> chain. Tasks are organized by the level they affect, and each item
> cites the document section it touches.

---

## How to write an entry

```
- [ ] (D3.2) One-line statement of what must be true when done.
      Any constraint or gotcha the doer needs. Blocked by: (P1.4).
```

The leading tag is the citation: `V4` for VISION section 4, `A2` for
ARCHITECTURE 2, `D3.2` for design section 3.2, `P1.4` for pseudocode
1.4, and a path for code. An entry with no citation is an entry
nobody can check against anything.

**Keep entries short on purpose.** When a task's plan grows detailed
enough to implement from — naming the functions, the files, and the
call sequence — that specificity belongs in a `pseudocode/` section,
not here. A detailed TODO entry looks like a specification and is
not one: `/refine` never checks it against DESIGN, and once its box
is ticked nobody reads it again. Move the detail up and leave the
entry pointing at the section. This is the single most common way
this chain has been broken in practice.

Completed items move to ARCHIVE with a `- [x]`, keeping their
numbering so older cross-references still resolve.

---

## VISION

(none)

---

## ARCHITECTURE

- [ ] (A9.3) Rendering-budget spike: frame rate vs particle count
      and trace length for a many-thin-traces scene, on an
      interactive node with software rendering. Sets the Tier-1
      default `n_particles`. Blocked by: nothing; do before D11.

---

## DESIGN

- [ ] (D1.5) Decide whether `interstellar_visitor` should name a
      real object's `v_∞` or keep the round 26 km/s.
- [ ] (D12.10) "Guess the potential" mode: a student proposes
      `V(r)`, the forward chain runs it as a custom potential, and
      pulls against the counts are shown. After `v1.0-classroom`.
- [ ] (D11) Set the Tier-1 default `n_particles` from the
      rendering-budget spike (A9.3) once it has run.

---

## PSEUDOCODE

- [ ] (P7–P13) Pseudocode for design sections 7–13. P1–P6 exist;
      the chain gate in `CLAUDE.md` forbids a `src/` edit until the
      governing section does, so `v0.5-orbits` can be coded now and
      the detector onward cannot.

---

## CODE

- [ ] (src/scripts/) Rename the template `XYZ.py` / `XYZrc.py` to
      `scsim.py` / `scsimrc.py` once P-sections exist; delete the
      template `tests/unit/test_example.py` when a real test lands.
- [ ] (src/scattering/) Package skeleton per A4: subpackage
      directories and `__init__.py` docstrings. No physics until
      the governing pseudocode exists.

---

## Campaigns

(none)

---

## ARCHIVE

- [x] (V) VISION.md written and ratified. Tagged `v0.1-vision`.
- [x] (A) ARCHITECTURE.md written. Tagged `v0.2-architecture`.
- [x] (D1–D3) Natural units, Coulomb closed forms, beam.
- [x] (spike) `coulomb_closed_forms.py`: closed forms verified to
      `3e-13`; found and fixed the `v₀` convention error in D1;
      measured the finite-`R_max` residual at `0.2353 / R`;
      verified the D5 deflection quadrature to `2e-12`.
- [x] (D4–D6) Orbit integration, deflection and cross section,
      results store.
- [x] (spike) `firsov_inversion.py`: Firsov form verified to
      `2e-14` both signs; tail truncation costs up to 30 %;
      binned-count pipeline recovers `V(r)` to 1 % at `2e5`
      particles with pull RMS 1.0; found the bin-center and
      equal-solid-angle traps now written into D7.
- [x] (D7) Detector.
- [x] (D8) Inversion, with the tail model, sign assumption,
      reach limit, and resampled error bands.
- [x] (D9–D13) Error budget, run file, scene and palettes,
      scrubber and session, batch and HDF5. Design complete for
      the first version.
- [x] (P1–P6) Pseudocode for units, Coulomb, beam, orbits,
      deflection, results store and driver. The pericenter-to-beam
      rotation (P2 eq. 2.13) was checked numerically in both signs.
