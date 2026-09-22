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

- [ ] (A9.1) Route B has been run on Linux only. Have someone run
      the README's four lines on **macOS** and on **Windows** and
      send back what `scsim --check` prints; record the result in
      A9.1 "What has been tried". Windows is the unknown: VTK's
      wheel, the `Scripts\activate` line, and path handling.
- [ ] (A9.1) Cut a release tag once Route B is confirmed, and point
      the README's `pip install` URL at `refs/tags/<tag>` so that a
      class installs a fixed version rather than `main`. Every
      release bumps `version` in `pyproject.toml`: pip decides whether
      to update by comparing versions, not code, so an unchanged
      number means `pip install --upgrade` does nothing (physdemo
      README, "Updating a tool").
- [ ] (A9.3, examples) `rutherford_disc` as shipped (20 000
      particles) takes over ten minutes to reach its first frame. Find
      where the time goes (store build, or 20 000 glyphs and traces),
      then either make the scene cheap for a disc beam or ship the
      example at a size that starts in seconds. Until then a student's
      second command is a trap. Same measurement as the next entry.
- [ ] (A9.3) Re-run `dev/spikes/render_budget.py` on an interactive
      compute node (`srun --partition=interactive`); the first run
      was on a loaded 1-CPU management node and is indicative only.
      Then set the Tier-1 default `n_particles` from it.

---

## DESIGN

- [ ] (D1.5) Decide whether `interstellar_visitor` should name a
      real object's `v_∞` or keep the round 26 km/s.
- [ ] (D12.10) "Guess the potential" mode: a student proposes
      `V(r)`, the forward chain runs it as a custom potential, and
      pulls against the counts are shown. After `v1.0-classroom`.

---

## PSEUDOCODE

- [ ] (P8, P13) Pseudocode for the inversion and the batch tier.
      P1–P7 and P9–P12 exist, so `v0.8-detector` can be coded now
      and the inversion cannot.

---

## CODE

- [x] (src/scripts/) Deleted the template `XYZ.py` / `XYZrc.py`;
      `scsim.py` / `scsimrc.py` are the pattern for `scbatch.py`
      (P13), and the template itself keeps the originals.
- [ ] (D11/D12) Camera framing: the default camera clips the
      detector sphere at distance 3; raised to 4. A "fit to scene"
      key (`Ctrl+f`, a camera command under D12.14) and per-energy
      framing are refinements. Seen 2026-09-22 in screenshots: at
      distance 4 `R_detect` the whole sphere fits but the orbits,
      which live inside `R_max = R_detect / 2`, occupy the middle
      sixth of the window, and the 120 straight free-flight legs
      dominate the picture. A second default framing that fills the
      window with the `R_max` region, and a lighter encoding for the
      free-flight legs, are what to try first.
- [ ] (src/scattering/) Remaining groups per A4 — `detector/`,
      `inversion/`, `analysis/`, `geometry/`, `render/`, `ui/`,
      `sinks/` — each after its pseudocode section.

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
- [x] (P10–P12) Pseudocode for the run file (with the seam that
      moves unit resolution out of the driver), the scene and
      renderer, and the session and `scsim.py`.
- [x] (v0.8-detector) P7 and P9 implemented: the detector as a
      viewing control (key `d` mode, `b` layout) with bars, empty-bin
      arrows and hatched unmeasured cones on the cross-section panel;
      the error-budget panel with its three columns and the tracked
      residual curves; bin bands on the sphere. The bitwise
      sign-independence test passes.
- [x] (P7, P9) Pseudocode for the detector (a pure function of
      the store, recomputed as a viewing control) and the error
      budget (three columns, never summed, enforced by an AST test).
- [x] (v0.6-scene) P10–P12 implemented: run files load, validate,
      resolve and write back; `scsim.py runs/rutherford.toml` opens
      the scene with the scrubber, the energy slider, the annulus
      and cone, the probe-depth sphere, and three 2D panels. The
      renderer selects VTK's EGL window when DISPLAY is unset, which
      is what makes offscreen tests possible on the cluster.
- [x] (v0.5-orbits) `core/`, `potentials/`, `beam/`, `orbits/`,
      `deflection/`, `run/` implemented with 136 tests. Building the
      store corrected three design claims upward: the entry plane is
      the tangent plane `Z₀ = R_max` (D4.6); the exterior deflection
      is geometry, not error, and scales as `1/R_max²` (D4.4, D9.4);
      the head-on cross section extrapolates in `(π−θ)²` (D5.5).
