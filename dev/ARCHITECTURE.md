# Architecture

> **Document hierarchy:** VISION → **ARCHITECTURE** → DESIGN →
> PSEUDOCODE → Code. For goals and principles, see `VISION.md`.
> Principles are cited as `P<n>`, goals as `G<n>`, future directions
> as `FD<n>`.

---

## 1. Repository Layout

```
scattering/
  dev/
    README.md         What lives in dev/, and what is not the chain
    VISION.md         Goals and principles
    ARCHITECTURE.md   This document
    DESIGN.md         Index of design sections
    design/           One file per design section
    PSEUDOCODE.md     Index of pseudocode sections
    pseudocode/       One file per pseudocode section
    TODO.md           Task list by level
    notes/            Dated working notes (not binding)
    figures/          Diagrams and their editable sources
  runs                Symbolic link to src/scattering/examples/
  src/
    scattering/       The importable library (Section 3), including
      cli/            the entry points' bodies (Section 4.13),
      defaults/       the shipped rc file (Section 7), and
      examples/       the example run files (TOML)
    scripts/          Thin executable fronts for cli/ (Section 4.13)
  tests/
    unit/             One module under test per file
    integration/      Several modules together, or an entry point
    regression/       Frozen reference outputs
  .claude/            Slash commands and reflow helpers
  .scattering/        Machine-local rc overrides (never tracked)
  CLAUDE.md           AI assistant guidance
  README.md           User-facing description
  pyproject.toml      Packaging
```

Simulation output (HDF5, video, frames) is regenerable from a run
file and is excluded from version control; the run file that produced
it is what is tracked (Section 9.4).

**Everything the tool needs at run time lives under
`src/scattering/`,** because that directory is all that an installed
copy contains (Section 9.1): the code, the shipped rc defaults, and
the example run files. `runs` at the top level is kept as a symbolic
link so that `runs/rutherford.toml` remains the short path it has
always been in a clone; it is a convenience of a checkout and nothing
may depend on it. (On a Windows checkout without symbolic-link
support it appears as a small text file. Windows users are served by
the installed route and `scsim --examples`, not by a clone.)

---

## 2. The Chain of Stages

VISION P4 says the forward and inverse tools are the same modules
read in opposite directions. This section is that principle made
structural; everything else in the document hangs off it.

```
   FORWARD  ─────────────────────────────────────────────────────►

  potential      orbits       deflection      cross        detector
    V(r)   ──►  r(t), φ(t) ──►   θ(b)    ──►  section  ──►  counts
                                              dσ/dΩ        N(θ_i)

   ◄─────────────────────────────────────────────────────  INVERSE
   V(r) for      (not          θ(b) by       dσ/dΩ by     N(θ_i)
   r > r_min     needed)       integrating   dividing     with
   by Abel                     dσ/dΩ         by ΔΩ_i      counting
   inversion                                              error
```

Each arrow is a module with a narrow interface, and each node is a
plain data object that both neighbors understand. The inverse
direction does not pass through the orbits: it goes from counts to
cross section to deflection function to potential by quadrature,
which is why the deflection function is a first-class object rather
than a by-product of the orbit solver.

**The consequence for module design.** A stage may not reach past
its neighbors. The detector consumes final velocities and knows
nothing about the potential; the inversion consumes a cross section
and knows nothing about the detector's geometry beyond the bin
edges it is handed. This is what lets a student swap the *measured*
cross section for the *exact* one at the same input and see the
counting noise vanish (VISION P3), and swap the recovered potential
back into the forward chain and see whether it reproduces the counts
(G7).

---

## 3. Execution Model: Precompute, Then View

VISION P5 states that the run is precomputed and the display is a
view. This is the second structural idea, and it is what makes the
scrubber (G4) and the energy axis (G5) cheap.

Every test particle is a one-body problem in a fixed potential (VISION
Non-Goal 2). Its trajectory is finite: it enters the scene at a
radius `R_max` where the potential is negligible, and it leaves at
the same radius. So the whole ensemble, at every energy in the sweep,
is integrated *before* anything is drawn, and stored as one array:

```
  trajectory[energy_index, particle_index, sample_index, component]
```

The interactive tier then never integrates during display. Play,
pause, reverse, step, and jump are all changes to `sample_index`;
the energy slider is a change to `energy_index`. Reverse is exact
because it reads the same stored samples backwards (G4). Two runs of
one file are identical bit for bit regardless of how they were
scrubbed, because scrubbing touches nothing that computes
(Section 8.6 tests this).

**Retention is bounded by the run file, not by the clock.** The
number of samples per orbit, the number of particles, and the number
of energies are fidelity settings (Section 7), and the array size
they imply is reported before the run begins. Whether an orbit is
stored as samples or, for a closed-form potential, as parameters
from which samples are generated on demand, is a DESIGN decision
that the results-store interface (Section 5.3) hides from every
consumer.

**The two tiers share this model.** The interactive tier holds the
array in memory and hands it to a renderer; the batch tier writes
the same array to HDF5 and stops. The array is the bridge.

```
  TIER 1: INTERACTIVE                  TIER 2: BATCH
  -------------------                  -------------
  Modest N, sampled orbits             Large N for statistics
  Desktop node, vedo window            Scheduled job, no display
  Purpose: see the geometry,           Purpose: counts good enough
  find interesting settings            for a convincing inversion

            \                              /
             v                            v
          +----------------------------------+
          |   run file  ->  results store    |
          |   (identical physics, identical  |
          |    array layout)                 |
          +----------------------------------+
```

Per the programmer's direction, Tier 2 is designed now and built
later. The results-store and sink interfaces exist from the start so
the batch tier drops in without disturbing the interactive one (G10).

---

## 4. Module Map

The package is `src/scattering/`. Subpackages are named for the
stage of the chain they implement (Section 2), plus the supporting
groups that every stage shares. Each module has one responsibility.

### 4.1 `core/` — Foundations

| Module | Single responsibility |
| --- | --- |
| `units.py` | The units boundary: presets and SI at the edge (P13) |
| `natural_units.py` | The dimensionless scaling used inside the core |
| `frames.py` | Center-of-mass frame now; lab-frame transform later (FD1) |

`natural_units.py` fixes the scaling — lengths in units of a
reference impact parameter, energies in units of the beam energy —
so that a Coulomb run at any `κ / E` is the same computation. It is
the reason the Rutherford and gravitational presets can share every
line of physics. `frames.py` is a seam that in the first version is
the identity; it exists so that FD1 is an addition, not a rewrite.

### 4.2 `potentials/` — What scatters

| Module | Single responsibility |
| --- | --- |
| `potential_interface.py` | The contract every potential satisfies |
| `coulomb.py` | `V = κ / r`, either sign, with closed forms |
| `yukawa.py` | Screened Coulomb (FD3, later) |
| `hard_sphere.py` | Hard sphere (FD3, later) |
| `well.py` | A potential with a well (FD3, later) |

The interface requires `V(r)` and `dV/dr`, and *optionally* offers a
closed-form deflection function and closed-form orbit. A consumer
that finds the optional forms present may use them; one that finds
them absent falls back to the numerical route. No consumer may branch
on *which* potential it holds (P12). The contract is Section 5.1.

### 4.3 `beam/` — What is thrown

| Module | Single responsibility |
| --- | --- |
| `beam_spec.py` | Energies, impact-parameter layout, azimuths, N |
| `impact_sampler.py` | Discrete annuli or uniform-flux disc (G1, G6) |
| `energy_sampler.py` | Delta or discrete list now; distribution later |

The beam is a plain description of initial conditions and nothing
more. `energy_sampler.py` is the hook for FD2: its interface returns
one energy per particle from a distribution, and the first version
implements only the delta function and the discrete list of G5. Two
impact-parameter layouts are offered because they teach different
things: named annuli make the ring-to-cone mapping visible (G1),
while a uniform-flux disc is what a cross section is actually defined
against and is what the detector needs (G6).

### 4.4 `orbits/` — How each particle moves

| Module | Single responsibility |
| --- | --- |
| `orbit_provider.py` | The contract: initial conditions → orbit |
| `equations_of_motion.py` | Planar central-force equations, `(r, φ)` |
| `integrators.py` | Time-stepping schemes, selectable per run |
| `analytic_orbits.py` | Closed-form orbit where the potential has one |
| `turning_point.py` | Distance of closest approach from `E`, `b`, `V` |
| `embedding.py` | Orbital plane → 3D scene coordinates |

Each particle is integrated **in its own orbital plane**, as a
two-degree-of-freedom problem in `(r, φ)`. Central-force motion is
planar, so this is exact, cheaper, and more accurate than a 3D
integration; and it puts the polar coordinates that G3 must display
directly in the state vector. `embedding.py` then places each plane
in the scene by the azimuth of the particle's impact point around the
beam axis. The three-dimensionality of the picture is a property of
the ensemble, not of any one orbit.

`orbit_provider.py` is the seam that lets the exact Coulomb orbit and
a numerical orbit be interchanged (P12, Section 5.2).

### 4.5 `deflection/` — From orbits to angles

| Module | Single responsibility |
| --- | --- |
| `deflection_function.py` | `θ(b)` at each energy, from orbits or closed form |
| `cross_section.py` | `dσ/dΩ` from `θ(b)` by `(b / sin θ) |db/dθ|` |
| `solid_angle.py` | `dΩ` for a `db`, and the annulus-to-cone map (G1) |

The scattering angle is measured from the **asymptotic outgoing
velocity**, not from the position at which the particle crosses
`R_max`. The difference is a finite-radius correction that vanishes
as `R_max → ∞` and is measurable at any finite value; DESIGN states
the correction and the test suite checks it. This module group is
the forward chain's middle and the inverse chain's middle alike, and
it is why `θ(b)` is stored as an object of its own rather than
recomputed from orbits on demand.

### 4.6 `detector/` — What is measured

| Module | Single responsibility |
| --- | --- |
| `detector_spec.py` | Sphere radius, bin edges in `θ`, `φ` later (FD4) |
| `binning.py` | Assign each final velocity to a bin |
| `counting_statistics.py` | Counts, Poisson error, `dσ/dΩ` estimate (P3) |

The detector consumes only final velocity directions and the bin
geometry. It does not know the potential, and it must not: the whole
point of G6 and G8 is that a detector cannot see what the orbits saw.
The bin layout is a data object that the inverse chain receives
unchanged, so the estimate and the inversion agree on what was
measured.

### 4.7 `inversion/` — The chain run backwards

| Module | Single responsibility |
| --- | --- |
| `counts_to_cross_section.py` | Divide by solid angle and flux, with error |
| `cross_section_to_deflection.py` | Recover `θ(b)` by integrating `dσ/dΩ` |
| `deflection_to_potential.py` | Abel-type inversion to `V(r)`, `r > r_min` |
| `reachability.py` | The turning-point boundary; what is unknown (P15) |

`reachability.py` is small and important. It computes, for the
energies actually run, the radius inside which no orbit went, and
every consumer of the recovered potential receives that radius
alongside the curve and is required to draw or report the interior
as unknown. The inversion formulas themselves are a DESIGN matter and
are to be verified against the literature by a spike before they are
written into DESIGN; the architecture only fixes what goes in and
what comes out.

### 4.8 `analysis/` — Is it right?

| Module | Single responsibility |
| --- | --- |
| `conservation_monitor.py` | Drift in `E` and `L` along every orbit (P2) |
| `analytic_solutions.py` | Closed forms for overlay and validation (G11) |
| `error_budget.py` | Numerical vs statistical error, kept separate (P3) |

These are runtime components, not test helpers: the monitor's output
is on screen, and the analytic cross section is drawn beside the
measured one. `error_budget.py` exists so that the two kinds of error
have one owner and are never combined by a caller that did not know
they were different.

### 4.9 `geometry/` — Derived display geometry

| Module | Single responsibility |
| --- | --- |
| `annulus.py` | The incoming ring at `b`, width `db` (G1) |
| `cone.py` | The outgoing cone at `θ`, width `dθ` (G1) |
| `orbit_plane.py` | The plane, `r` and `φ` markers for one orbit (G3) |
| `probe_depth.py` | The turning-point sphere at each energy (G5) |

This group computes *what* the constructions are, in scene
coordinates, and draws nothing. Keeping it out of `render/` lets the
batch tier write the annulus and cone to HDF5 without a renderer.

### 4.10 `run/` — The reproducible unit of work

| Module | Single responsibility |
| --- | --- |
| `run_spec.py` | Complete description of a run, as data (G9) |
| `serialization.py` | Save and restore a run file exactly |
| `fidelity.py` | The fidelity knob set shared by both tiers |
| `results_store.py` | The precomputed array and its access interface |
| `driver.py` | Run the forward chain end to end from a spec |

A run spec holds the potential, the beam, the detector, the
integrator and fidelity settings, and the viewpoint. It is plain data
with no behavior, which is what allows it to cross the tier boundary.
`driver.py` is the one place that knows the order of the forward
stages; `results_store.py` is the Section 5.3 boundary.

### 4.11 `sinks/` — What consumes a results store

| Module | Single responsibility |
| --- | --- |
| `sink_interface.py` | Abstract consumer of a completed results store |
| `live_sink.py` | Hands the store to the interactive session |
| `hdf5_sink.py` | Writes HDF5 with the run spec embedded (Tier 2, later) |
| `video_sink.py` | Encodes a scrub sequence to video (later) |

### 4.12 `render/` and `ui/` — Presentation

| Module | Single responsibility |
| --- | --- |
| `render/scene_description.py` | Renderer-agnostic list of drawables |
| `render/palettes.py` | Light, dark, color-blind-safe encodings (P8) |
| `render/vedo_renderer.py` | Realizes a scene with vedo / VTK |
| `ui/scrubber.py` | Time and energy sliders, play/pause/reverse (G4, G5) |
| `ui/controls.py` | Widgets for beam, potential, and view |
| `ui/interactive_session.py` | The interactive loop |

### 4.13 `cli/` and `scripts/` — Entry points

An entry point is reached in two ways (Section 9.1), and both must
run the same code. So the body of each command is a module in the
library, and what differs is only the few lines that start it.

| Module | Purpose |
| --- | --- |
| `cli/scsim.py` | Body of the interactive tool (Tier 1): argument |
| | parsing, `main(argv)`, `record_command()`, `console_main()` |
| `cli/examples.py` | Finds and copies the packaged example run |
| | files and the shipped rc file |
| `cli/scbatch.py` | Body of the batch tool (Tier 2, later) |

| Front | How it is reached |
| --- | --- |
| `scripts/scsim.py` | Executable script; the `physdemo` suite links |
| | it, and a clone runs it directly. Puts `src/` on the path from |
| | its resolved location, then calls `cli.scsim`. |
| console script `scsim` | Declared in `pyproject.toml`; created by |
| | `pip install`. Calls `cli.scsim.console_main`. |

Both fronts log the invocation to `command` and then call
`main()`; `main(argv)` itself never logs, so the test suite can call
it freely (`CLAUDE.md`, "Command Logging"). Neither the fronts nor
`cli/` hold any physics. `cli/` sits at the top of the dependency
graph, where `scripts/` was, and nothing imports it.

The shipped rc file moves with the code it configures: it is
`defaults/scsimrc.py` inside the package (Section 7), not a file
beside the script, because an installed copy has no `scripts/`
directory to look in.

---

## 5. Dependency Graph

Dependencies point downward only. No module may import from a group
listed above it, and this is tested (Section 8.6).

```
  scripts/  (fronts only; import cli/ and nothing else)
  cli/
    +-- ui/
    |     +-- render/
    |     +-- sinks/
    +-- sinks/
    +-- run/          (driver, results_store, run_spec, fidelity)
          +-- inversion/
          +-- detector/
          +-- deflection/
          +-- analysis/
          +-- geometry/
          +-- orbits/
          +-- beam/
          +-- potentials/
          +-- core/
```

Within the stage groups, the forward chain's order is also the import
order: `deflection/` may import `orbits/`, never the reverse;
`detector/` imports neither, since it sees only final velocities;
`inversion/` imports `deflection/` (for the solid-angle map and the
cross-section definition) and `detector/` (for the bin layout), and
nothing else. `analysis/` and `geometry/` import the stage groups
and are imported only by `run/` and above.

---

## 6. Key Boundaries

Seven seams exist specifically to protect a VISION principle. Each
is an interface that must remain stable.

### 6.1 The potential boundary (P12, FD3)

`potential_interface.py` requires `V(r)` and `dV/dr` and permits
optional closed-form orbit and deflection function. `coulomb.py`
supplies all of them; a later potential may supply only the required
pair. Consumers query for the optional forms by capability, never by
potential type. This is what lets Yukawa, hard sphere, and a well
arrive as new files with no change downstream.

### 6.2 The orbit boundary (P12, G11)

`orbit_provider.py` defines one operation: given a potential, an
energy, and an impact parameter, return the orbit as `(r, φ)` against
a parameter, together with the turning point and the asymptotic
outgoing direction. `analytic_orbits.py` implements it in closed form
for Coulomb; `integrators.py` implements it numerically for any
potential. Every consumer sees only the returned orbit. The test that
certifies this boundary is the numerical provider reproducing the
analytic one on Coulomb to a stated tolerance (Section 8.2).

### 6.3 The results-store boundary (P5, G4, G5)

`results_store.py` hides how the precomputed run is held. It offers:
the sample at `(energy_index, particle_index, sample_index)`; the
final state of every particle at an energy; the deflection function
and cross section at an energy; and the store's size. Whether the
samples are materialized or generated from orbit parameters is
invisible above this line. The scrubber and every sink speak only to
this interface.

### 6.4 The detector boundary (G6, G8)

`detector/` receives final velocity directions and a bin layout. It
receives nothing else. A test asserts that no module under
`detector/` imports from `potentials/` or `orbits/`. This is the
architectural form of the lesson in G8: the detector cannot see the
sign of `κ`, so the code that models it must not be able to either.

### 6.5 The sink and renderer boundaries (P11, G10)

The driver does not know what happens to a completed results store;
it hands it to a `sink_interface`. Only `vedo_renderer.py` imports
vedo or VTK; a different backend is a new module in `render/` and
nothing else changes. Nothing under the stage groups, `analysis/`,
or `geometry/` imports from `render/`, `ui/`, or `sinks/`.

### 6.6 The units boundary (P13)

The core works in the natural units of `natural_units.py`. Real units
enter at exactly one place, `core/units.py`, which is the only module
permitted to import **pint**, and they enter through *named presets*
in the run file — `preset = "alpha_on_gold"`, `preset =
"comet_past_sun"` — or through explicit dimensioned values that the
boundary converts. Display formats a natural-unit value back into the
preset's real units, with the scale factor stated (P14). Below
`run/`, no module imports pint, accepts a pint object, or returns
one; a test enforces this.

The library and the reasons for it are inherited from the rigid-body
tool: pint's overhead lands only at the boundary, its error messages
are the clearest available to a student, and it parses unit strings
so that a run file can say `energy = "5 MeV"` rather than a bare
number with a comment.

### 6.7 The frame boundary (FD1)

`core/frames.py` exposes a transform from the center-of-mass frame
to the laboratory frame that, in the first version, is the identity
and carries a reduced mass equal to the projectile mass. Every angle
the detector reports and every energy the beam declares passes
through it. When recoil is added, the transform acquires the target
mass and nothing else moves.

---

## 7. Configuration

Two mechanisms hold different kinds of thing, and the division is a
rule.

**The rc file** (`scsimrc.py`) holds what is *machine-dependent and
rarely changed*: filesystem paths, output directories, default window
size, preferred palette, cluster and queue settings, and defaults for
anything below. It is looked for in the working directory, then in
`$SCATTERING_RC`, and last in the package itself
(`scattering/defaults/scsimrc.py`), which is the documented set of
defaults and is always present, in a clone and in an installed copy
alike. `scsim --write-rc` copies that file into the working directory
for a user who wants to change it; nobody should need to know where
the package is installed.

**The run file** (TOML) holds the *physics*: the potential and its
parameters or preset, the beam, the detector, the integrator and
fidelity settings actually used, and the viewpoint.

```
  rc file defaults  <  run file  <  command-line arguments
```

> **Any value that can affect the computed trajectories, the counts,
> or the inversion must live in the run file, never only in the rc
> file.** The rc file may supply its default, but the run file
> records the resolved value that was used.

A run file must be self-contained: handing it to another user on
another machine reproduces the same array, the same counts, and the
same recovered potential (G9). This includes the random seed used by
the uniform-flux impact sampler, which is a required key of the run
file's `[beam]` table (`seed = <integer>`) whenever the sampler is
stochastic; a run that depends on chance records the chance.

**Fidelity** is one table in the run file and one object in
`run/fidelity.py`, shared by both tiers: particle count, samples per
orbit, the energy list, integrator and step, `R_max`, and detector
bin count. Tier 1 and Tier 2 differ only in the values.

---

## 8. Testing Strategy

### 8.1 Layers

| Directory | Scope |
| --- | --- |
| `tests/unit/` | Pure functions: potentials, turning points, |
| | deflection formulas, binning, unit round-trips |
| `tests/integration/` | Stages together: beam → orbits → deflection; |
| | counts → inversion; a whole run from a file |
| `tests/regression/` | Whole runs against stored reference output |

### 8.2 Oracles

VISION G11 makes closed-form cases the standard of correctness. The
oracles are:

- The Coulomb orbit, a conic section with known eccentricity.
- The Rutherford deflection function `tan(θ/2) = κ / (2 E b)` and
  cross section `(κ / 4E)² / sin⁴(θ/2)`, at every energy in a sweep.
- The head-on turning point `r_min = κ / E` for repulsive Coulomb.
- Sign independence: attractive and repulsive Coulomb give identical
  cross sections and identical detector counts for the same seed.
- The hard-sphere cross section, isotropic and equal to `a² / 4`,
  when that potential arrives.
- The inversion of an *exact* Rutherford cross section returning
  `κ / r` for `r > r_min`, to a stated tolerance.

The numerical orbit provider's first duty is to reproduce the
analytic one on Coulomb; that certifies the Section 6.2 boundary.

### 8.3 Invariants

Asserted wherever the quantity is produced:

- Energy and angular momentum are conserved along every orbit to the
  tolerance the integrator implies.
- Every orbit's turning point satisfies `V(r_min) ≤ E`.
- `θ(b)` is monotonic in `b` for a monotonic repulsive potential.
- Binned counts sum to the number of particles that reached the
  detector; none are lost.
- The recovered potential is reported only for `r > r_min`; a
  consumer asking for a smaller radius receives "unknown", not a
  number.

### 8.4 Tolerance policy

Every numerical tolerance is **derived and justified**, not tuned,
with the reasoning in a comment beside it. Statistical tests are held
to a different standard, and the two must not be confused:

| Kind | Standard |
| --- | --- |
| Numerical | Derived from integrator order and step, or from |
| | floating-point precision; a fixed bound |
| Statistical | A chi-square or equivalent against the Poisson |
| | expectation, at a stated confidence; a *fixed seed* so |
| | the test is deterministic, and a comment naming the |
| | seed-independent property being checked |

A statistical test that passes only for one seed is not a test; a
statistical test that is loosened until it passes is a rubber stamp.
The seed is fixed for reproducibility, and the *design* of the test
is what must hold for any seed.

### 8.5 Reference-output governance

A file in `tests/regression/reference_outputs/` is a claim about
correct behavior, and may be created only from a case checked
against an oracle or verified by hand. Regenerating one requires the
commit message to say what changed and why the new values are more
correct. References are stored as compact, diff-reviewable text, not
HDF5: a reviewer must see which numbers moved, and anything large
enough to need HDF5 is a batch result, not a fixture.

### 8.6 Architectural tests

Mechanically checkable, so tested rather than left to discipline:

1. **The import rule of Section 5.** Nothing under the stage groups,
   `analysis/`, or `geometry/` imports from `render/`, `ui/`, or
   `sinks/`; `detector/` imports nothing from `potentials/` or
   `orbits/`.
2. **The units boundary of Section 6.6.** No module outside
   `core/units.py` imports pint.
3. **The determinism guarantee of Section 3.** The same run file
   produces an identical results store on two runs, and scrubbing
   the store in any sequence leaves it unchanged.
4. **The reachability guarantee of Section 4.7.** No code path
   returns a recovered `V(r)` inside `r_min` without the "unknown"
   marker.
5. **The installed-copy guarantee of Section 9.1.** Everything a run
   needs is inside the package: the rc file loads with the search
   restricted to the package, every example run file is found
   through the package and resolves, the console script named in
   `pyproject.toml` imports, and every third-party module the
   package imports is a declared dependency. `runs/` and the
   packaged examples are the same files.

---

## 9. Build System

### 9.1 Language, environment, and the two ways in

Python 3.10 or later, NumPy-based numerical core. The tool can reach
a user in two ways. They exist because the two intended places
(`VISION.md` section 5) want opposite things, and they run the same
code (Section 4.13).

**Route A: the `physdemo` suite, for a shared computer.** The tool
is one member of the suite (`github.com/UMKC-CPG/physdemo`): a set of
course demonstration tools that share one Python environment and one
`bin/` directory of commands. One person installs the suite; everyone
else only sources its `activate.sh`. Nothing is installed per user,
which is what a teaching cluster with small home quotas and a
read-only shared directory requires. The suite provides one virtual
environment built from a pinned `requirements.txt`, a command per
entry point named without `.py`, and an `activate.sh` that puts both
on the `PATH`. Nothing in it is specific to one computer; notes about
a particular site live in the suite's `site/` directory and nowhere
in this repository. The tool is *linked*, never copied and never
pip-installed into the suite, so a clone stays live.

The rules this tool obeys so that the suite can link it:

1. Every entry point under `src/scripts/` begins with
   `#!/usr/bin/env python3` and is executable, so it runs by name
   with whatever `python3` the activated environment provides.
2. An entry point finds the library from its own **resolved**
   location (`Path(__file__).resolve()`), never from the working
   directory and never from the unresolved path, which would name
   the suite's link to the script rather than the file.
3. The shipped defaults are inside the package (Section 7), so a
   linked command needs no configuration step.

**Route B: `pip install`, for a personal computer.** A laptop has one
user, no shared directory, and quite possibly no `bash` (Windows), so
the suite's shell scripts are the wrong tool. There the tool installs
like any Python package, with its dependencies, into an environment
the user makes:

```
python -m venv physdemo
source physdemo/bin/activate        (Windows: physdemo\Scripts\activate)
pip install https://github.com/UMKC-CPG/scattering/archive/refs/heads/main.zip
scsim --examples                    (copies the example run files here)
scsim rutherford.toml
```

The archive URL needs no `git` on the laptop; `pip install
git+https://github.com/UMKC-CPG/scattering` is equivalent where `git`
exists, and a release is the same URL with `refs/tags/<tag>`. `pip`
creates the `scsim` command from the console script declared in
`pyproject.toml`, on every operating system, so nothing here depends
on a shell.

This is why everything the tool needs at run time is inside the
package (Section 1), and why `pyproject.toml` **declares the
dependencies**: on this route nobody else will supply them.

**Who owns the versions.** The suite's `requirements.in` is the
single statement of what the course tools need; `pyproject.toml`
repeats the subset this tool imports, with lower bounds no tighter
than the suite's, and the suite's `requirements.txt` pins what was
tested. A dependency this tool needs and the suite lacks is added to
the suite first. Route B installs the newest versions that satisfy
the bounds, which is the right behaviour on a laptop and means a
breaking release of a dependency shows up there first; the pinned
set is the known-good fallback (`pip install -r` the suite's
`requirements.txt`, then this tool with `--no-deps`).

| Dependency | Pinned in the suite | Purpose |
| --- | --- | --- |
| `numpy` | 2.2.6 | Arrays, the results store |
| `scipy` | 1.15.3 | Integrators, quadrature for inversion |
| `vedo` | 2026.6.1 | Interactive 3D rendering |
| `vtk` | 9.6.2 | Rendering engine beneath vedo |
| `pint` | 0.24.4 | Units at the boundary (Section 6.6) |
| `tomli-w` | 1.2.0 | Writing TOML run files |
| `matplotlib` | 3.10.9 | The cross-section and `V(r)` plots |
| `h5py` | 3.16.0 | HDF5 output; the `batch` extra (Tier 2) |
| `pytest` | 9.1.1 | Test suite; the `test` extra |

Reading TOML uses the `tomli` backport on the 3.10 floor and
`tomllib` on 3.11+. Deliberately not dependencies: `numba` and
`mpi4py` (FD5, deferred behind the orbit boundary), and any GUI
toolkit beyond what vedo provides.

No absolute path appears in the source, the tests, or the run files.

**What has been tried.** Route A on Linux with Python 3.10, including
from a read-only installation with an empty home directory. Route B
on Linux. Neither route has yet been run on macOS or Windows; the
first person to do so should run `scsim --check` (Section 9.2) and
report what it prints.

**History.** Through `v0.8-detector` the tool ran in the virtual
environment built for the rigid-body tool, then in the suite alone.
Route B was added when laptops became an intended place to run.

### 9.2 Running

```bash
# Route A.
sdemo          # alias for:  source <suite prefix>/activate.sh
               # (or, where Lmod is used:  module load cpg_physdemo)
# Route B.
source physdemo/bin/activate

# Then, identically on both routes:
scsim --check                  # can this computer run and draw it?
scsim --examples               # copy the example run files here
scsim rutherford.toml          # Tier 1: interactive exploration
scsim rutherford               # a packaged example, by bare name
scsim --write-rc               # copy the rc defaults here, to edit
scbatch rutherford.toml        # Tier 2: batch run (later)

# In a clone, from the repository root:
scsim runs/rutherford.toml
pytest tests/ -v
```

`scsim --check` is the one-line answer to "will it work here": it
reports the versions in use, builds a small run, draws it offscreen,
and verifies that the picture is not blank. On Route A the suite's
`physdemo-check` does the same for the environment as a whole and can
also time a real window.

**Offscreen drawing** (`scsim --offscreen --frames N`, `--check`, the
tests, the spikes) chooses VTK's window class by the rule of
pseudocode 11.6: EGL on Linux whenever offscreen drawing is asked
for, nothing on macOS or Windows.

### 9.3 Rendering budget

The rigid-body tool established, by measurement, that software
rendering on an interactive cluster node sustains an interactive
frame rate for a scene of its complexity, and that the renderer is
fill-rate bound rather than geometry bound. This project's scene is
different in kind — many thin orbit traces and many small particle
glyphs rather than a few large surfaces — so that result is a prior,
not a guarantee. A spike measuring frame rate against particle count
and trace length is the first task of the render work, and the
particle count that Tier 1 defaults to is set from its result.

### 9.4 Data interchange

The batch tier writes HDF5 with the full run file embedded as
metadata, so any result traces back to the run that produced it, and
an XDMF companion so ParaView can read the trajectories directly.
HDF5 output is excluded from version control as bulky derived data;
the run file is tracked instead.

---

## 10. Development Checkpoints

Each level of the chain gets a tagged baseline when first considered
complete, so later drift is measured against a fixed point:

```
v0.1-vision          VISION.md complete
v0.2-architecture    ARCHITECTURE.md complete
v0.3-design          Design sections for the first version complete
v0.4-pseudocode      Pseudocode sections for the first version
v0.5-orbits          Coulomb orbits computed and validated (G2, G11)
v0.6-scene           Orbits, annulus and cone rendered, scrubber (G1, G4)
v0.7-energy          Energy sweep as a scrubber axis (G5)
v0.8-detector        Counts with statistics; sign ambiguity shown (G6, G8)
v0.9-inversion       Counts → V(r) with the unknown interior (G7, P15)
v1.0-classroom       Usable in a graduate mechanics course
```

Work proceeds on short-lived topic branches merged into `main`. Tier
2 and the further potentials of FD3 are scheduled after
`v1.0-classroom`; their abstractions, not their implementations, are
what the earlier milestones depend on.
