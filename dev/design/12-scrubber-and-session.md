# Design 12. The Scrubber and the Interactive Session

> **Parent:** [`../DESIGN.md`](../DESIGN.md) — design index.
> **Status:** draft.
> **Serves:** G4 (scrub both directions), G5 (energy axis), G6, G7,
> P5 (precompute, then view), P6 (interactivity), P14;
> ARCHITECTURE A3 (execution model), A4.12 (`ui/`), A6.3, A8.6(3)
> (determinism).
> **Depends on:** Sections 6, 10, 11.
> **Implemented by:** pseudocode section 12.

---

## 12.1 Purpose and scope

The session is what a student drives. This section designs the
loop that draws frames, the controls that move through a
precomputed run, the controls that change the run and therefore
rebuild it, and the single rule that separates the two. It does
not design the drawables (Section 11) or the run file (Section 10).

---

## 12.2 Two kinds of control, one rule

Every control is one of two kinds, and the kind decides what it is
allowed to touch:

**Viewing controls** read the results store and change what is
shown. Time and energy scrubbing, camera, palette, panel layout,
tracked-particle choice, `db̃` for the annulus display, the
detector's display mode. They touch nothing in the physics zone of
the run file and nothing in the store (which is frozen, Section
6.7). Any sequence of them leaves every computed array bit-identical
— A8.6(3), tested.

**Run controls** edit the physics zone — energies, `b̃_max`,
`n_particles`, the sign, the tail model, the integrator — and
therefore produce a *new* resolved run specification, a new results
store, and a new set of static drawables. They are never applied
live to the existing store. The rule:

> A run control makes a new run. A viewing control never does.

The run specification is the source of truth (Section 10.8). When
a run control is used the session resolves the new specification,
shows the memory budget (Section 6.4), rebuilds the store with a
progress readout, and swaps it in. The old store is discarded.
`Save` writes the current resolved specification to a run file, so
that what a student sees can always be handed to someone else.

---

## 12.3 The loop

Single-threaded, and the session owns it, as the rigid-body tool's
does — not a timer callback hung off VTK's interactor. Per tick:

```
  1. advance the frame index by the play state (12.4)
  2. build the per-frame drawables for (energy_index, frame_index)
     from the store (Section 11.7); static drawables are cached
  3. hand the scene to the renderer; it draws once
  4. pump the 3D window's event queue and matplotlib's (11.10);
     apply any control changes
```

**No physics runs in the loop.** Step 2 is array slicing (Section
6.6, `frame`) and glyph placement. This is the payoff of P5: the
rigid-body loop's hardest constraint — fixed substeps per frame so
that the trajectory cannot depend on machine load — is not needed
here, because nothing in the loop computes a trajectory. The frame
rate can float freely, and the displayed ratio of scene time to
wall time is reported rather than corrected.

Why own the loop anyway: uniformity with the rigid-body tool, the
video sink (Section 13) needs deterministic frame stepping without
a window, and a future recoil panel or a second energy view should
not require re-plumbing the interactor. The renderer boundary
(A6.5) keeps the vedo specifics in one module.

---

## 12.4 Time controls

All are changes to `frame_index` in `[0, n_samples − 1]`:

| Control | Effect | Key |
| --- | --- | --- |
| Play / pause | advance by `+rate` per tick, or `0` | `Ctrl+space` |
| Reverse | advance by `−rate` | `Ctrl+r` |
| Step | `±1`, then pause | `Ctrl+s` / `Ctrl+Shift+s` |
| Speed | `rate` in frames per tick, `1` to `16` | `Ctrl++` / `Ctrl+−` |
| Normal speed | `rate = 1` | `Ctrl+n` |
| Jump | entry / pericenter / exit of tracked | `Ctrl+e` `Ctrl+p` `Ctrl+x` |
| Home / end | `0` / `n_samples − 1` | `Ctrl+Home` / `Ctrl+End` |
| Slider | any frame, drag | the **time slider** |
| Loop | wrap at the end, or stop | `Ctrl+l` |

Every key is a `Ctrl` chord, for the reason the rigid-body tool
chose them (12.15): a bare letter typed into a VTK window is taken
by VTK's own bindings (`s` for surface, `w` for wireframe, `r` to
reset the camera), and a student cannot tell the tool's keys from
VTK's. The chords are listed on the 3D window permanently.

**The session starts playing.** A student who opens the tool sees
the beam in flight; the first version started paused and showed a
still picture until `space` was found.

**The time slider** is a widget along the bottom of the 3D window
(vedo's slider, the only widget that can share the scene). Dragging
it sets `frame_index` and pauses; it follows the frame while
playing; its label shows `t̃` and the frame index.

Reverse is exact: it reads the same stored frames backwards (G4).
The telemetry shows `t̃` and the frame index, and the ratio of
scene time advanced per wall second.

**Rate is in frames, not in time.** Two energies have different
time grids (Section 6.2); a rate in frames means a playback at
`rate = 4` takes the same wall time for every energy, and the
displayed `t̃` per frame differs — which is the point.

---

## 12.5 The energy slider (G5)

`energy_index` in `[0, n_energies − 1]`, changed by the **energy
slider** (a second widget in the 3D window, at the right edge, with
`n_energies` stops) or by `Ctrl+,` / `Ctrl+.` (the brackets belong to
the graticule, 11.12). Because each particle exists at every energy (Section
3.2), the slider changes nothing about *which* particles are shown,
only their orbits. The frame index is preserved as a **fraction of
the run**, `frame / n_samples` (Section 6.2), so that the picture
stays at "the same moment" of the pass while the orbits tighten.

The static drawables that depend on energy — traces, cones, the
probe-depth sphere, the deflection and cross-section panels — are
rebuilt at the new index from the cache. The rings and the entry
plane do not depend on energy and are not rebuilt.

The energies are shown sorted on the slider with their natural-unit
and preset-unit values, and the index into the run file's order is
shown beside them, since a teacher may have ordered the list
deliberately (Section 3.2).

---

## 12.6 The tracked particle

One particle is *tracked*: its orbit plane, `r` and `φ` markers,
velocity arrow, turning point, asymptotes, and deflection arc are
drawn (Section 11.2), its residual series fills the error-budget
panel (Section 9.3), and its effective potential is plotted. It is
chosen by clicking a glyph or a trace, by index in `[view]`, or by
cycling with `Ctrl+Tab`. Choosing it is a viewing control.

For an annulus layout the natural choice is one particle per ring;
`Tab` cycles through rings first and azimuths second. For a disc
layout `Tab` cycles in order of `b̃`.

---

## 12.7 The detector and inversion panels

Both read the store's per-energy records (Sections 7.8, 8.9) and
redraw when the energy index changes. Their viewing controls:

- **Detector mode** (asymptotic / position) and **bin layout** are
  *viewing* controls, because the counts are recomputed from the
  stored `n̂_out` and free-flight lines without touching the
  physics — the detector consumes the store and writes nothing
  back. Switching them is instant.
- **Exact vs measured** on the inversion panel substitutes the
  exact cross section for the histogram (Section 8.2), a viewing
  control that reruns the inversion (about a second with
  resampling) and shows the noise vanish.
- **Sign toggle** and **tail model** rerun the inversion the same
  way; they are recorded in `[inversion]`, so a `Save` captures
  them, but they change no trajectory and no count, so they are
  viewing controls under the rule of 12.2.

The last point deserves its statement: the inversion is *downstream*
of the store, so every inversion setting is a viewing control. Only
the beam, the potential, and the fidelity are run controls.

---

## 12.8 Run controls, and the budget

Editing an energy, the beam layout, `b̃_max`, `n_particles`, the
potential's sign or preset, the integrator, `R̃_max`, or
`n_samples` opens the run-control path of 12.2. The session:

1. shows the new resolved values and the memory budget beside the
   old, and the estimated rebuild time from the last build's rate;
2. on confirmation, rebuilds with a progress bar (the driver
   reports per energy and per particle);
3. swaps the store, rebuilds static drawables, keeps the frame
   fraction and the tracked particle's index where they still
   exist.

`Esc` during a rebuild cancels it and keeps the old store. An edit
that fails validation (Section 10.6) shows the message beside the
field and leaves the run untouched.

---

## 12.9 Labeled scaling (P14)

One control scales a physical quantity for visibility: the particle
glyph size. Its factor is on the legend (Section 11.6). There is
deliberately no "exaggerate the deflection" control: the deflection
is the subject, and a student who wants to see a larger one lowers
the energy or the impact parameter, which is physics.

---

## 12.10 Later: the guess-the-potential mode

Recorded from Section 8.11 and the project's original discussion,
not built in the first version: a student proposes a `V(r)` — a
preset with edited parameters, or a hand-drawn curve on the
recovered-potential panel — the forward chain runs it as a
`custom` potential, and the predicted histogram's pulls against the
actual counts are shown. It is a run control on a second store
that lives beside the first, and it needs nothing the architecture
does not already have: a tabulated potential satisfying A6.1 and a
second results store. It is a Section 12 refinement because its
whole content is interaction.

---

## 12.11 Invariants and tests

- Any sequence of viewing controls leaves the store bit-identical
  (A8.6(3)); the test drives a scripted sequence of every control
  in 12.4–12.7 through the session with an offscreen renderer.
- `frame_index` stays in range under every control, including at
  the ends with loop off.
- Changing `energy_index` preserves the frame fraction to within
  one frame.
- A run control never mutates the current store; it produces a new
  object, and the old one is unchanged until dropped.
- A cancelled rebuild leaves the session on the old store with the
  old frame and tracked particle.
- `Save` after any sequence of controls writes a run file that
  reloads to the same resolved specification (Section 10.9).
- The loop draws at least one frame per tick with no physics call
  on the stack (an import-time check that `ui/` imports nothing
  from `orbits/` or `deflection/` directly; it reaches them only
  through `run/`).
- The renderer sets the camera only when the session's camera
  changes (12.14): after a scripted sequence with no camera command
  the renderer's camera-set count is one.
- `Save` after a camera change made through the renderer writes
  that camera to the run file (12.14).
- Every binding in the table is a `Ctrl` chord, and every command in
  the dispatcher has exactly one binding (12.15).
- Dragging either slider yields the same state as the equivalent
  key command (12.4, 12.5).

---

## 12.12 Alternatives considered

**Hang the loop on VTK's timer callback.** Simpler; rejected for
the reasons in 12.3.

**Apply beam edits live, re-integrating only the changed
particles.** Rejected: it makes the store mutable and the
determinism guarantee a matter of bookkeeping. The full rebuild is
seconds for a Tier-1 run, and the budget is shown first.

**Rate in scene time rather than frames.** Rejected; 12.4.

**Keep `t̃` rather than the frame fraction across an energy
change.** Rejected; 12.5 and Section 6.2.

**An "exaggerate deflection" slider.** Rejected; 12.9.

**Bare letters for keys.** Rejected 2026-09-22; 12.4 and 12.15.

**Panels as pictures inside the 3D window.** Rejected 2026-09-22;
11.10.

**Reapplying the run-file camera every frame.** It was never
chosen; it was a bug (12.14), recorded here so that "the camera
must match the run file" is not proposed as a reason to restore it.

---

## 12.14 The camera belongs to the mouse

The run file's `[view] camera` (azimuth, elevation, distance) is the
**starting** view, and the view a `Save` records. Between those two
moments the camera belongs to the mouse: VTK's own interaction —
drag to rotate, wheel to zoom, middle-drag to pan — is the right
tool and needs no help. So the renderer applies the session's camera
**only when it changes**: at the first frame, after a run-file edit,
and after any future camera command; on every other frame it leaves
the camera exactly where the student put it. The first version
reapplied the stored numbers on *every* frame, so that each drag or
zoom was undone a few milliseconds later; the scene appeared to
snap back, and could not be rotated at all.

`Save` reads the camera *back* from the renderer into the session
before writing, so that a view found by dragging is kept, and
reopening the saved run file shows it. A future `Ctrl+f` ("fit to
scene") is a camera command under the same rule (`dev/TODO.md`).

Distance is stored as a multiple of `R̃_detect`, as before, so that
the same run file frames the scene for any detector radius.

---

## 12.15 The key scheme

All keys are `Ctrl` chords, one scheme for every tool of the suite,
taken from the rigid-body tool (`rigid_body/dev/PSEUDOCODE.md` §15):

| Chord | Command | Section |
| --- | --- | --- |
| `Ctrl+space` | play / pause | 12.4 |
| `Ctrl+s`, `Ctrl+Shift+s` | step forward / back | 12.4 |
| `Ctrl+−`, `Ctrl++`, `Ctrl+n` (`Ctrl+0`) | slower, faster, normal | 12.4 |
| `Ctrl+r` | reverse | 12.4 |
| `Ctrl+e`, `Ctrl+p`, `Ctrl+x` | jump to entry, pericenter, exit | 12.4 |
| `Ctrl+Home`, `Ctrl+End` | first, last frame | 12.4 |
| `Ctrl+l` | loop | 12.4 |
| `Ctrl+,`, `Ctrl+.` | previous, next energy | 12.5 |
| `Ctrl+Tab` | next tracked particle | 12.6 |
| `Ctrl+1` … `Ctrl+9`, `Ctrl+a` | toggle ring `i`; toggle all | 11.11 |
| `Ctrl+[`, `Ctrl+]` | fewer, more graticule lines | 11.12 |
| `Ctrl+m` | mirror deflection curve | 5.6 |
| `Ctrl+d`, `Ctrl+b` | detector mode, bin layout | 12.7 |
| `Ctrl+c` | palette | 11.5 |
| `Ctrl+w` | write (save) the resolved run file | 12.2 |
| `Ctrl+h` | hide / show the legend | — |
| `Ctrl+q` | quit | — |

Where the rigid-body tool has a key for the same purpose, the same
key is used; `Ctrl+[` / `Ctrl+]` change a mesh's fineness there and
the graticule's here. The legend is drawn in the bottom-left corner
of the 3D window at all times, produced from the same table the
dispatcher reads, so that the keys shown can never drift from the
keys honoured; `Ctrl+h` hides it for a screenshot.

**Why `Ctrl+w` for save** and not `Ctrl+s`: `Ctrl+s` is single-step
in the rigid-body tool, and a tool that steps where its sibling
saves would teach the wrong reflex.

---

## 12.13 The command line beyond a run file

> **Serves:** VISION section 5 (a laptop and a read-only teaching
> cluster are both intended places to run); ARCHITECTURE 4.13, 9.1,
> 9.2. Added 2026-09-17 with Route B.

Until now the command line took a run file and nothing else, which
assumed the user had a clone: the example run files and the rc file
were things to be found in the repository. A student who installed
the tool with `pip`, or who is using a shared installation they did
not make, has no idea where those files are and should not need to.
Four small additions remove that assumption. None of them touches
the physics, and none is a viewing or a run control (12.2); they are
ways of *getting to* a run.

**Where the examples live.** In the package, `scattering/examples/`,
and they are located through the package (`importlib.resources`),
never through a path relative to a script or to the working
directory. That one rule makes a clone, a linked suite, and an
installed copy behave identically.

**`scsim --examples [DIR]`** copies every packaged example run file
into `DIR` (default: the working directory) and exits. It never
overwrites: a file already there is left alone and reported, because
a student's edited copy is worth more than a fresh one. If `DIR`
cannot be written the message says so and names the remedy. This is
how a student obtains a file to edit on either route.

**A packaged example by bare name.** `scsim rutherford` runs the
packaged `rutherford.toml` directly. The rule is narrow so that it
cannot surprise: it applies only when the argument names no existing
file, has no directory part, and matches a packaged example with or
without `.toml`; a file in the working directory always wins; and one
line on standard error says which file is being used. The resolved
run records that real path as its source (10.8), so the run is as
reproducible as any other. This is what makes the very first run a
single command.

**`scsim --write-rc`** copies the shipped `scsimrc.py` into the
working directory, again refusing to overwrite (Section 10.7).

**`scsim --check`** answers "will it work on this computer" without
the user knowing what to look for. It prints the Python version, the
platform, and the version of every declared dependency; builds a
deliberately small run from the packaged `rutherford` example
(timing it); draws two frames offscreen; and reads the picture back
to verify that it is not blank, since a window without a working
OpenGL context accepts draw calls and draws nothing (11). It ends
with one line, `RESULT: PASS` or `RESULT: FAIL -- <reason>`, and the
matching exit status, and it writes no file. The small run is made
with `--set`-style overrides of the packaged example, so the check
exercises the same loading, resolving, and building code as a real
run rather than a special path.

**What is and is not logged.** `--examples`, `--write-rc`, and
`--check` are not runs, and like `--help` they are not recorded in
`command`.

**Errors are messages.** A run file that does not exist, or that
fails validation (10.6), ends the command with the message and exit
status 2, not with a Python traceback. When the file does not exist
the message lists the packaged examples and mentions `--examples`,
because the likeliest cause is a student typing a name from the
notes in a directory that does not hold the file.

### Alternatives considered

**Keep the examples at the top of the repository.** Rejected: an
installed copy contains only the package, so they would not reach a
laptop at all. The top-level `runs` remains as a symbolic link for
the short path in a clone.

**Download the examples on demand.** Rejected: a teaching cluster's
nodes may have no network, and a run must not depend on one.

**Fall back to a packaged example for any missing path.** Rejected:
`scsim results/rutherford.toml` with a mistyped directory would
silently run something else. Hence the bare-name restriction.

**A separate `scsim-check` command.** Rejected for now: one command
to remember is the point. The suite's `physdemo-check` remains the
check of a whole shared environment, including a real window.

