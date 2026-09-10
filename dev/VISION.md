# Vision

> **Document hierarchy:** **VISION** → ARCHITECTURE → DESIGN →
> PSEUDOCODE → Code. This is the top of the chain; it cites nothing
> above it, and every level below must be consistent with it.

---

## 1. Purpose

This project is an interactive, real-time teaching tool that builds
physical intuition for **classical scattering** in a graduate
theoretical-mechanics course. A student configures a beam of test
particles and a central potential, then watches the ensemble scatter
in a 3D scene alongside the quantities that describe it: the energy
fixed by the asymptotic speed, the impact parameter and its annulus,
the polar coordinates of each orbit, the scattering angle, the
differential cross section, and the solid angle into which a given
ring of impact parameters is thrown.

The subject has one central image, and the tool exists to deliver
it. An incoming annulus of area `2π b db` is mapped by the potential
onto an outgoing cone-shell of solid angle `2π sin θ dθ`, and the
ratio of the two is the differential cross section. Rendered as a
colored ring of particles landing on a colored cone, the definition
`dσ/dΩ = (b / sin θ) |db/dθ|` stops being an algebraic identity and
becomes something a student has seen happen.

The tool then runs the same subject backwards. Scattering theory is
a chain — potential, to orbits, to deflection function, to cross
section, to counts on a detector — and *inverse scattering* is that
chain read from right to left. The tool exposes the chain as a chain,
so that a student who has watched a potential produce a distribution
of counts can take a distribution of counts and, with the same tool,
recover the potential that made it, and see plainly where and why
the recovery is incomplete.

It is the companion of the rigid-body rotation tool in this group
and shares its tooling, its environment, and its conventions.

---

## 2. Goals

1. **Show the annulus-to-cone mapping.** Render the incoming annulus
   at impact parameter `b`, the outgoing cone at scattering angle
   `θ`, and the differential area and solid angle that connect them,
   so that the differential cross section is seen as a geometric
   ratio before it is written as a formula.

2. **Integrate real orbits in a real potential.** Each particle's
   motion follows from the equations of motion in the chosen central
   potential, beginning with `V = κ / r` of either sign. The
   Rutherford and gravitational cases are the same physics with
   opposite signs of `κ`, and the tool treats them as such.

3. **Expose every quantity on the chain.** Energy from `v_∞`, impact
   parameter, the polar coordinates `(r, φ)` of the orbit, the
   distance of closest approach, the scattering angle, the
   deflection function `θ(b)`, and the differential cross section
   are each displayed, labeled, and tied to the geometry that
   produces them.

4. **Scrub time in both directions.** Play, pause, step, reverse,
   and jump anywhere in the run. Because every trajectory is finite
   and precomputed, reversal is exact, not approximated.

5. **Sweep energy as a first-class axis.** The beam energy may be a
   single value or an ordered list; a list yields a family of runs
   through the identical pipeline, scrubbed by a second slider. A
   student watches orbits tighten and the turning point march inward
   as energy rises, and sees that at energy `E` the potential is
   probed only outside the head-on turning point.

6. **Simulate a detector honestly.** Scattered particles are counted
   in angular bins on a detector sphere, so the measured cross
   section carries real counting statistics. Finite sample size
   becomes a visible source of error, distinct from numerical error.

7. **Invert from counts back to the potential.** From binned counts,
   recover the cross section, from it the deflection function, and
   from that the potential over the radial range the data can reach.
   Overlay the recovered `V(r)` on the one that generated the data,
   with the unreachable interior marked as unknown rather than
   filled in.

8. **Make the ambiguities visible.** The Coulomb cross section is
   independent of the sign of `κ`: attractive and repulsive
   potentials give identical detector counts while their orbits look
   nothing alike. The tool shows this directly, so a student learns
   from the simplest case that a cross section does not determine a
   potential.

9. **Reproduce any run from a file.** A run is specified completely
   by a TOML input file — beam, potential, detector, fidelity, and
   view — so that a result can be regenerated exactly and a
   classroom demonstration can be replayed.

10. **Run at two fidelities from one file.** An interactive tier for
    exploration and a batch tier for large ensembles share the same
    physics and the same input file. The batch tier is designed now
    and built later; its abstractions are in place from the start.

11. **Validate against closed forms.** The Coulomb orbit, the
    Rutherford deflection function and cross section, and the
    hard-sphere case have exact solutions. They are the standard of
    correctness for the integrator, the detector, and the inversion,
    and they form the regression suite.

---

## 3. Non-Goals

1. **Quantum scattering.** Partial waves, phase shifts, and the Born
   approximation are a different subject with a different tool. The
   classical treatment here is complete in itself and is the natural
   preparation for the quantum one, but nothing quantum is simulated.

2. **Particle-particle interaction within the beam.** Each test
   particle moves independently in the fixed potential. The beam is
   an ensemble of one-body problems, and its independence is what
   makes the whole run precomputable (Principle 4). Many-body
   scattering belongs to a molecular-dynamics code.

3. **Target recoil, in the first version.** The scattering center is
   infinitely massive and the frame is the center-of-mass frame. The
   reduced mass and a frame-transformation boundary are designed in
   from the start so that recoil and the lab-frame angle can be added
   later without disturbing the physics (Future Direction 1).

4. **Energy spread within a beam, in the first version.** A beam is
   monoenergetic, or a discrete list of monoenergetic shells (Goal
   5). A continuous energy distribution would smear the deflection
   function and complicate the single-energy inversion, so it is
   deferred; the beam specification leaves the hook in place (Future
   Direction 2).

5. **Fitted or empirical potentials.** The potentials offered are
   simple closed forms chosen for what they teach. This is not a
   tool for modelling a specific physical system.

---

## 4. Design Principles

1. **Physical fidelity.** The motion is produced by solving the true
   equations of motion in the stated potential, never by scripted or
   faked animation. Where a closed-form orbit exists it may be used
   directly, but it must be the exact solution.

2. **Numerical error is disclosed, never disguised.** Energy and
   angular momentum are conserved along every orbit, and the tool
   measures and reports their departure so that a viewer can always
   tell whether an effect on screen is physics or numerics. Where a
   closed-form orbit is available, the numerical orbit is compared
   against it and the discrepancy shown.

3. **Statistical error is disclosed, and kept distinct.** A cross
   section measured from finite counts carries counting error that
   is not numerical error. The two are reported separately and are
   never combined into one figure, because they have different
   causes and different remedies: more particles for one, a smaller
   step for the other.

4. **The forward chain and the inverse chain are the same modules.**
   Potential, orbits, deflection function, cross section, and
   detector counts are stages with clean interfaces. The inverse
   tool is a second traversal of those stages in the opposite
   direction, not a separate subsystem. A change to a stage serves
   both directions or it is wrong.

5. **The run is precomputed; the display is a view.** Trajectories
   are finite and independent, so the whole ensemble is integrated
   before display and the time scrubber is an index into stored
   results. Time controls change what is shown, never what is
   computed, and a run is identical regardless of how it was
   scrubbed.

6. **Real-time interactivity.** Rotating, zooming, panning, and
   scrubbing produce an immediate, smooth response. Changing beam or
   potential parameters recomputes the run quickly enough to feel
   like manipulation rather than resubmission.

7. **Pedagogical transparency.** Nothing physical is hidden. Every
   vector, ring, cone, and trace is labeled with the quantity it
   represents, and the mathematics is exposed rather than buried.

8. **Configurable visual encoding.** The mapping from quantity to
   color and line style is a selectable palette. Light, dark, and
   color-blind-safe palettes are provided at minimum, and no
   distinction that carries meaning may rest on color alone.

9. **Student-readable source.** The code itself is a teaching
   artifact: richly documented, with self-explanatory names, so a
   student can read it cold and follow the physics (see
   `CLAUDE.md`).

10. **Start simple, stay extensible.** The first target is Coulomb
    scattering with the annulus-to-cone picture and a working
    detector. Further potentials, recoil, and energy spread are
    anticipated and the design must admit them without a rewrite.

11. **Physics decoupled from presentation.** The physics, detector,
    and inversion are independent of the rendering and interface
    layer, so the display medium can be changed without touching
    them, and the batch tier can run them with no display at all.

12. **The computation method never dictates the simulation.** An
    orbit may come from a closed-form solution or from a numerical
    integrator; a deflection function may come from an analytic
    formula or from the orbits themselves. Every consumer sees only
    the result. No consumer may branch on, or be restricted by, the
    technique that produced it.

13. **A dimensionless core, with real units at the boundary.**
    Scattering in a power-law potential scales: every Coulomb result
    depends on `κ / E` alone, and the Rutherford and gravitational
    cases sit thirty orders of magnitude apart in every dimensional
    quantity while being the same computation. The core therefore
    works in natural units of the problem, and real units enter only
    through named presets at the input boundary — an alpha particle
    on gold, a comet past the Sun — which carry SI dimensions and
    are reported in them. A student sees physical scale where it
    means something and is not asked to carry meaningless exponents
    where it does not.

14. **Deliberate distortions are labeled.** Exaggerating a deflection
    or compressing a timescale to make an effect visible is
    legitimate. Doing so silently is not. Whenever a displayed
    quantity is scaled away from its computed value, the factor is
    stated on screen.

15. **What the data cannot reach is shown as unknown.** At energy
    `E` no orbit penetrates inside the head-on turning point, so the
    inverted potential is defined only outside it. The tool marks
    that boundary and leaves the interior blank rather than
    extrapolating. An inversion that silently fills in what it
    could not measure teaches exactly the wrong lesson.

---

## 5. Audience and Use

The audience is graduate students in a theoretical-mechanics course
at the level of Goldstein: the deflection function, the Rutherford
formula, and the Firsov-type inversion are all fair game, and rainbow
and glory scattering are within reach once a potential with a well is
added.

The tool runs on the teaching cluster, not on student laptops. It
uses the shared Python virtual environment already built for the
rigid-body tool, which contains every dependency this project needs;
a student activates that environment and runs the tool. The batch
tier, when built, runs as a scheduled cluster job from the same
input file and writes HDF5 for post-processing.

---

## 6. Future Directions

These are explicitly not goals for the first versions, and the early
versions must not be compromised to accommodate them. They are
recorded so that present-day decisions leave the door open.

1. **Target recoil and the laboratory frame.** A finite target mass
   introduces the reduced mass and the distinction between the
   center-of-mass scattering angle and the angle a laboratory
   detector measures. Showing both frames side by side is the direct
   analogue of the body-frame versus space-frame display in the
   rigid-body tool, and the same kind of conceptual error is at
   stake. The frame boundary exists in the architecture from the
   start; only the transform is deferred.

2. **Energy spread within a beam.** A continuous distribution of
   beam energy, sampled per particle, smears the deflection function
   and turns the clean single-energy inversion into a deconvolution.
   That is a lesson in why real data is harder than textbook data.
   The beam specification is a distribution over energy that the
   first version restricts to a delta function or a discrete list;
   lifting that restriction changes the sampler and nothing
   downstream.

3. **Further potentials.** Three are already chosen for what each
   one teaches. A screened Coulomb (Yukawa) potential makes the
   total cross section finite and shows why the pure Coulomb one is
   not. A hard sphere is the trivial inversion and the cleanest test
   of the detector and inversion pipeline. A potential with a well
   (Lennard-Jones or a square well) produces rainbow, glory, and
   orbiting, where `db/dθ` vanishes or `b(θ)` becomes multivalued,
   the cross section diverges, and the inversion becomes ambiguous —
   the natural second semester of the inverse-scattering material.

4. **Azimuthal structure.** The first detector bins only in `θ`,
   which azimuthal symmetry justifies. A non-central potential, or a
   polarized beam, would need `φ` bins; the detector interface
   should not assume symmetry even though the first implementation
   exploits it.

5. **Compiled kernels for very large ensembles.** The batch tier may
   eventually want more particles than a NumPy loop serves. The
   integrator sits behind an interface so that a compiled kernel can
   replace it without touching the beam, detector, or inversion.
