# Pseudocode 12. The Scrubber, the Interactive Session, and `scsim.py`

> **Parent:** [`../PSEUDOCODE.md`](../PSEUDOCODE.md) — index.
> **Specifies:** design section 12,
> [`../design/12-scrubber-and-session.md`](
> ../design/12-scrubber-and-session.md).
> **Governs:** `src/scattering/ui/session_state.py`,
> `src/scattering/ui/controls.py`, `src/scattering/ui/vedo_controls.py`,
> `src/scattering/ui/interactive_session.py`,
> `src/scattering/cli/scsim.py`, `src/scattering/cli/examples.py`,
> `src/scripts/scsim.py`, and the `[project]` tables of
> `pyproject.toml`.
> **Status:** draft.

---

## 12.1 Seam inventory

The session consumes a `ResolvedRun` (P10.1), the `ResultsStore` the
driver built from it (P6.1), the scene builders and renderer (P11),
and, for run controls, `resolve` (P10.7) and `build_results_store`
(P6.4). It produces nothing the physics reads. Specifically:

| Consumed | From |
| --- | --- |
| `store.n_energies`, `n_particles`, `n_samples`, `energies` | P6.1 |
| `store.time_grid[k]` — for the telemetry's `t` | P6.5 |
| `store.entry_index`, `exit_index` — jump targets | P6.5 |
| `polar[k, i, :, 0]` — its `argmin` is the pericenter frame | P6.5 |
| `build_static`, `build_frame`, `VedoRenderer` | P11.4, P11.6 |
| `resolved.spec.view` — initial palette, camera, tracked, panels | P10.1 |
| `resolve(spec, rc)`, `build_results_store(resolved)` | P10.7, P6.4 |
| `write_back(resolved, path)` | P10.8 |
| `rc.window_size`, `rc.output_dir` | P10.6 |
| `rc.glyph_radius_fraction` — handed to `build_frame` | P10.6 |
| `renderer.read_camera()`, `renderer.legend_visible` | P11.6 |
| `renderer.set_graticule(n)` | P11.6 |
| `PanelWindows.update / pump / close` | P11.6 |
| `ring_legend_lines(store, resolved, k, hidden_rings)` | P11.4 |
| slider commands `("seek", n)`, `("set_energy", k)` | P12.5 |

The rigid-body tool's `ui/interactive_session.py` and
`ui/vedo_controls.py` are the model: a controls source with
`read()`, `pump()`, `window_closed()`, a `VedoControls` bound to
`plotter.add_callback("KeyPress", ...)` that pumps
`plotter.interactor.ProcessEvents()`, and a `ScriptedControls` for
headless tests. The names below match theirs.

---

## 12.2 Records

```
record SessionState:                # all VIEWING state (D12.2)
    energy_index   int
    frame_index    int
    rate           int      frames per tick, 1..16
    playing        bool
    direction      +1 | -1
    loop           bool
    tracked        int      particle index
    palette        str
    camera         {azimuth_deg, elevation_deg, distance}
    panels         list of str
    detector_mode  str      "asymptotic" | "position"   (P7; viewing)
    detector_layout str
    show_mirror    bool
    hidden_rings   frozenset of int     D11.11; empty = all shown
    graticule_lines int                 D11.12; 12, in [4, 36]
    legend_visible bool                 D12.15

record Session:                     # what the loop owns
    resolved       ResolvedRun
    store          ResultsStore
    state          SessionState
    renderer       VedoRenderer
    controls       a controls source
    static_cache   {(k, view_key): list of Drawable}
    wall_start     float;  scene_advanced  float   (for the ratio)
```

---

## 12.3 State transitions (`ui/session_state.py`)

Pure functions on `SessionState`; every one is a viewing control
and touches neither the store nor the resolved run.

```
function advance(state, n_samples) -> state:
    if not state.playing: return state
    next = state.frame_index + state.direction * state.rate
    if 0 <= next < n_samples: return replace(state, frame_index=next)
    if state.loop:
        return replace(state, frame_index=next mod n_samples)
    # Stop at the end that was hit.
    return replace(state, frame_index=clamp(next, 0, n_samples - 1),
                   playing=False)

function step(state, n_samples, delta) -> state:
    return replace(state, playing=False,
                   frame_index=clamp(state.frame_index + delta, 0, n_samples-1))

function jump(state, n_samples, target) -> state:
    return replace(state, frame_index=clamp(target, 0, n_samples-1))

function set_energy(state, new_index, n_samples) -> state:
    # Preserve the FRACTION of the run (D12.5, D6.2).
    fraction = state.frame_index / max(1, n_samples - 1)
    return replace(state, energy_index=new_index,
                   frame_index=round(fraction * (n_samples - 1)))

function set_rate(state, factor) -> state:
    return replace(state, rate=clamp(state.rate * factor, 1, 16))

function toggle_ring(state, j, n_rings) -> state:
    # D11.11. j outside [0, n_rings) is ignored.
    if not 0 <= j < n_rings: return state
    hidden = state.hidden_rings ^ {j}           # symmetric difference
    return replace(state, hidden_rings=hidden)

function toggle_all_rings(state, n_rings) -> state:
    if state.hidden_rings: return replace(state, hidden_rings=frozenset())
    return replace(state, hidden_rings=frozenset(range(n_rings)))

function set_graticule(state, delta) -> state:
    return replace(state, graticule_lines=clamp(state.graticule_lines
                                                + delta, 4, 36))

function cycle_tracked(state, store, delta) -> state:
    # D12.6: annuli layouts cycle ring-major (particles are contiguous
    # by ring, P3.3, so index order IS ring-major); disc layouts cycle
    # in order of b.
    if store.beam.layout == "disc":
        order = argsort(store.impact_parameter)
        position = index of state.tracked in order
        return replace(state, tracked=order[(position + delta) mod N])
    return replace(state, tracked=(state.tracked + delta) mod N)
```

---

## 12.4 Key bindings (`ui/controls.py`)

The table of D12.4 as data, so that the legend and the dispatcher
read one source:

```
# D12.15: every key is a Ctrl chord. Keys arrive from vedo already
# prefixed ("Ctrl+s", "Ctrl+minus", "Ctrl+bracketleft"); they are
# matched case-SENSITIVELY, because Shift changes the key symbol
# ("Ctrl+S" is Ctrl+Shift+s) and that is how step-back is told from
# step. Aliases map several symbols to one command so that a chord
# feels natural whatever a keyboard's shift state names the key.
BINDINGS = {
  "Ctrl+space":   ("play_pause",   "play / pause"),
  "Ctrl+s":       ("step_forward", "one frame, then pause"),
  "Ctrl+S":       ("step_back",    "one frame back, then pause"),
  "Ctrl+plus":    ("faster",       "rate x2, up to 16"),
  "Ctrl+equal":   ("faster",       None),                  # alias
  "Ctrl+minus":   ("slower",       "rate / 2, down to 1"),
  "Ctrl+underscore": ("slower",    None),                  # alias
  "Ctrl+n":       ("normal",       "rate 1"),
  "Ctrl+0":       ("normal",       None),                  # alias
  "Ctrl+r":       ("reverse",      "flip direction"),
  "Ctrl+e":       ("jump_entry",   "tracked particle's entry"),
  "Ctrl+p":       ("jump_pericenter", "tracked particle's pericenter"),
  "Ctrl+x":       ("jump_exit",    "tracked particle's exit"),
  "Ctrl+Home":    ("jump_start",   "first frame"),
  "Ctrl+End":     ("jump_end",     "last frame"),
  "Ctrl+l":       ("loop",         "toggle loop at the end"),
  "Ctrl+comma":   ("energy_down",  "previous energy"),
  "Ctrl+period":  ("energy_up",    "next energy"),
  "Ctrl+Tab":     ("track_next",   "next tracked particle"),
  "Ctrl+1" .. "Ctrl+9": ("ring_1" .. "ring_9", "toggle ring i"),
  "Ctrl+a":       ("rings_all",    "toggle all rings"),
  "Ctrl+bracketleft":  ("graticule_fewer", "fewer latitude lines"),
  "Ctrl+bracketright": ("graticule_more",  "more latitude lines"),
  "Ctrl+m":       ("mirror",       "toggle the mirror deflection curve"),
  "Ctrl+d":       ("detector_mode","asymptotic / position"),
  "Ctrl+b":       ("detector_layout", "cycle the bin layout"),
  "Ctrl+c":       ("palette",      "cycle light / dark / colorblind"),
  "Ctrl+w":       ("save",         "write the resolved run file"),
  "Ctrl+h":       ("legend",       "hide / show this legend"),
  "Ctrl+q":       ("quit",         "quit"),
  "q": ("quit", None), "Escape": ("quit", None),   # VTK closes on these
}
# Slider commands carry a value and are not in BINDINGS:
#   ("seek", n)        -> jump to frame n, then pause     (time slider)
#   ("set_energy", k)  -> set_energy(state, k, S)         (energy slider)

function apply(command, session) -> Session:
    state, store = session.state, session.store
    S = store.n_samples
    n_rings = len(resolved.spec.beam.annuli) if annuli else 8
    match command:
      "play_pause":   state = replace(state, playing=not state.playing)
      "reverse":      state = replace(state, direction=-state.direction)
      "step_forward": state = step(state, S, +1)
      "step_back":    state = step(state, S, -1)
      "faster":       state = set_rate(state, 2)
      "slower":       state = set_rate(state, 0.5)
      "normal":       state = replace(state, rate=1)
      "jump_entry":   state = jump(state, S, store.entry_index[k, tracked])
      "jump_pericenter":
          k, i = state.energy_index, state.tracked
          state = jump(state, S, argmin(store.polar[k, i, :, 0]))
      "jump_exit":    state = jump(state, S, store.exit_index[k, tracked])
      "jump_start":   state = jump(state, S, 0)
      "jump_end":     state = jump(state, S, S - 1)
      ("seek", n):    state = step-like: replace(jump(state, S, n),
                                                 playing=False)
      "loop":         state = replace(state, loop=not state.loop)
      "energy_down" | "energy_up":
          k = clamp(state.energy_index -/+ 1, 0, store.n_energies - 1)
          state = set_energy(state, k, S)
      ("set_energy", k): state = set_energy(state, clamp(k), S)
      "track_next":   state = cycle_tracked(state, store, +1)
      "ring_i":       state = toggle_ring(state, i - 1, n_rings)
      "rings_all":    state = toggle_all_rings(state, n_rings)
      "graticule_fewer" | "graticule_more":
          state = set_graticule(state, -2 / +2)
          session.renderer.set_graticule(state.graticule_lines)
      "mirror":       state = replace(state, show_mirror=not ...)
      "detector_mode": state = replace(state, detector_mode=other)
      "detector_layout": state = replace(state, detector_layout=next)
      "palette":      state = replace(state, palette=next in cycle)
                      session.renderer.set_palette(state.palette)
      "save":         state = replace(state,
                                      camera=session.renderer.read_camera())
                      write_back(session.resolved with view = state,
                                 rc.output_dir / "<stem>.resolved.toml")
      "legend":       state = replace(state, legend_visible=not ...)
                      session.renderer.legend_visible = state.legend_visible
      "quit":         session.running = False
    return replace(session, state=state)

function control_legend_lines() -> list of str:
    # One line per DISTINCT command with a help text; aliases (help
    # None) are not listed. Drawn permanently, D12.15.
    return [f"{key:>18}  {help}" for key, (_, help) in BINDINGS.items()
            if help is not None]
```

**`save` must not end the session.** The tool is routinely run from
a directory the user cannot write — a shared, read-only installation
on a teaching cluster, with the student standing among the example
run files. If `write_back` raises an OS error, the session prints one
line naming the directory and the remedy (run from a writable
directory, or set `output_dir` in a local `scsimrc.py`) and carries
on; the orbits on screen are worth more than the file.

Every command above is a viewing control (D12.2, D12.7). Run
controls — editing the beam, potential, or fidelity — are not bound
to keys in the first version: they are made by editing the run file
and restarting, or through `--set`; the interactive edit-and-rebuild
path of D12.8 is a refinement noted in 12.9.

---

## 12.5 The controls sources (`ui/vedo_controls.py`)

```
protocol ControlsSource:
    read() -> list of command names issued since the last read
    pump() -> None            process window events
    window_closed() -> bool

class VedoControls(ControlsSource):
    __init__(plotter):
        plotter.add_callback("KeyPress", self._on_key_press)
        self.queue = []
    _on_key_press(event):
        key = event.keypress            # arrives as "Ctrl+s" etc.
        if key in BINDINGS: self.queue.append(BINDINGS[key][0])
        elif key starts with "Ctrl+" or "Alt+":
            # A chord the table does not know: say so, with the name
            # as it arrived, on standard error. Key names differ between
            # X servers, remote desktops, and keyboard layouts, and this
            # line is how a mismatch is found ("Ctrl+bracketleft" is
            # what vedo documents for Ctrl+[; a display that sends
            # something else shows it here).
            print(f"scsim: key {key!r} is not bound (Ctrl+h: legend)")
        # Unchorded keys other than q / Escape are VTK's own and are
        # ignored here (D12.15).
    push(command):                      # from the renderer's sliders
        self.queue.append(command)      # ("seek", n) / ("set_energy", k)
    read(): q, self.queue = self.queue, []; return q
    pump():
        interactor = plotter.interactor
        if interactor is not None: interactor.ProcessEvents()
        # offscreen or context-less windows have no interactor
    window_closed(): return plotter closed or interactor terminated

class ScriptedControls(ControlsSource):
    # Headless tests and --frames: a fixed list of (tick, command)
    # and a frame cap.
    __init__(script: list of (tick, command), max_frames)
    read(): commands whose tick == self.tick; self.tick += 1
    pump(): nothing
    window_closed(): return self.tick >= max_frames
```

---

## 12.6 The loop (`ui/interactive_session.py`)

```
function run_session(resolved, store, controls, renderer, rc,
                     initial_state=None) -> SessionState:
    state = initial_state or SessionState(
        energy_index=0, frame_index=0, rate=1, playing=True,   # D12.4
        direction=+1, loop=False,
        tracked=resolved.spec.view.tracked_particle,
        palette=resolved.spec.view.palette,
        camera=resolved.spec.view.camera,
        panels=resolved.spec.view.panels,
        detector_mode="asymptotic", show_mirror=False,
        hidden_rings=frozenset(), graticule_lines=12,
        legend_visible=True)
    session = Session(resolved, store, state, renderer, controls, {}, ...)
    panels = PanelWindows(state.panels, palette, background,
                          offscreen=renderer.offscreen)          # P11.6
    session.running = True
    wall_start = now();  scene_advanced = 0.0
    while session.running and not controls.window_closed():
        # 1. Advance (D12.3 step 1).
        previous = state.frame_index
        state = advance(state, store.n_samples)
        scene_advanced += |store.time_of(k, state.frame_index)
                           - store.time_of(k, previous)|
        # 2. Build the scene: static from the cache, dynamic now.
        view_key = (state.palette, state.show_mirror, state.tracked,
                    state.hidden_rings, state.detector_layout,
                    state.detector_mode)
        if (state.energy_index, view_key) not in session.static_cache:
            session.static_cache[...] = build_static(store, resolved,
                                                     state.energy_index, state)
        dynamic, telemetry = build_frame(store, resolved,
                                         state.energy_index,
                                         state.frame_index, state.tracked,
                                         state.hidden_rings, rc)
        ring_lines = ring_legend_lines(store, resolved, state.energy_index,
                                       state.hidden_rings)
        telemetry.ratio_of_scene_to_wall_time = scene_advanced
                                                / max(1e-9, now() - wall_start)
        scene = Scene(static=session.static_cache[...], dynamic=dynamic,
                      telemetry=telemetry)
        # 3. Draw once; the panels only when their key changed.
        renderer.render(scene, state.camera, state.energy_index, view_key,
                        state, ring_lines)
        for name in state.panels:
            panel_key = (state.energy_index, state.tracked,
                         state.show_mirror, state.detector_layout,
                         state.detector_mode, state.palette)
            panels.update(name, build_panel(name, ...), panel_key)
        # 4. Pump both event queues and apply controls.
        controls.pump(); panels.pump()
        for command in controls.read():
            session = apply(command, session)
        state = session.state
    panels.close()
    return state
```

The camera in `state.camera` is the run file's view until `save`
reads the live one back (P12.4); the renderer applies it only when
the dict changes (P11.6), so mouse rotation and zoom are never undone
(D12.14).

No physics runs in the loop (D12.3): step 2 is slicing and glyph
placement. The static cache is keyed by everything a static
drawable depends on; changing the tracked particle rebuilds the
orbit-plane drawable, which is why `tracked` is in the key.

---

## 12.7 The entry point (`cli/scsim.py`, and its two fronts)

Follows the template's `XYZ.py` / `XYZrc.py` idiom (`CLAUDE.md`,
"Command Logging"), with one change forced by ARCHITECTURE 4.13: the
body lives in the package, because the command is reached in two
ways and both must run the same code.

**Seam inventory for the move.** What `src/scripts/scsim.py` holds
today, and where each part goes:

| Today in `scripts/scsim.py` | Goes to | Why |
| --- | --- | --- |
| module docstring (the `--help` text) | `cli/scsim.py` | argparse |
| | | reads `__doc__` there |
| `record_command()` | `cli/scsim.py` | both fronts call it |
| `parse_command_line()`, `console_progress()`, `main()` | same | |
| `sys.path.insert(resolved src/)` | stays in the script | only a |
| | | clone or a link needs it; an installed copy is importable |
| `if __name__ == "__main__"` | stays, and gains a twin, | |
| | `console_main()` in `cli/scsim.py` | |
| `rc` lookup beside the script | gone; P10.6 looks in the package | |

Consumed unchanged: `load_rc`, `load_and_resolve`, `RunFileError`
(P10); `build_results_store` (P6.4); `prepare_offscreen` (P11.6);
`VedoRenderer` (P11); `ScriptedControls`, `VedoControls`,
`run_session`, `parse_script` (12.5, 12.6). Tests that import `scsim`
by putting `src/scripts` on the path keep working, because the script
re-exports `main` and `record_command`.

```
# ---- cli/scsim.py ----
UTILITY_FLAGS = ("-h", "--help", "--examples", "--write-rc", "--check")

function record_command():
    if any flag of UTILITY_FLAGS in sys.argv: return     # not runs (D12.13)
    try: append the dated argv block to ./command
    except OSError: one line on stderr; continue          # see below

function parse(argv):
        runfile                optional positional
        --set TABLE.KEY=VALUE  repeatable
        --offscreen            no window; render to memory
        --frames N             run N ticks then exit (implies scripted
                               controls; with --offscreen for tests)
        --screenshot PATH      after the last frame
        --script "tick:command,..."   scripted controls
        --palette, --tracked   overrides of [view] (viewing only)
        --examples [DIR]       copy the packaged examples   (12.10)
        --write-rc             copy the shipped rc file     (12.10)
        --check                self-check of this computer  (12.10)
    exactly one of {runfile, --examples, --write-rc, --check} must be
        given; otherwise usage error
    if args.offscreen and not (args.frames or args.script):
        usage error: "--offscreen needs --frames N or --script ..."
        # Interactive controls on a window nobody can see would run
        # forever with no way to stop them; refuse before any work.

function main(argv=None) -> int:
    args = parse(argv)
    if args.examples is given: return copy_examples(args.examples)   # 12.10
    if args.write_rc:          return copy_rc_file(cwd)              # 12.10
    if args.check:             return self_check()                   # 12.10
    try:
        runfile  = locate_run_file(args.runfile)                     # 12.10
        rc       = load_rc()                                         # P10.6
        resolved = load_and_resolve(runfile, overrides, rc)          # P10.8
    except RunFileError, FileNotFoundError as problem:
        print "scsim: <problem>" on stderr; return 2     # a message, not
                                                         #   a traceback
    print(f"results store: about {resolved.estimate_bytes/1e6:.0f} MB")
    store = build_results_store(resolved, progress=console_bar)   # P6.4
    if args.offscreen: prepare_offscreen()      # P11.6, before the
                                                #   renderer is imported
    renderer = VedoRenderer(resolved.spec.view.palette, rc.window_size,
                            offscreen=args.offscreen,
                            panels=resolved.spec.view.panels)
    if args.frames or args.script:
        controls = ScriptedControls(parse_script(args.script),
                                    max_frames=args.frames or len(script)+1)
    else:
        controls = VedoControls(renderer.plotter)
    state = run_session(resolved, store, controls, renderer, rc)
    if args.screenshot: renderer.screenshot(args.screenshot)
    renderer.close()
    return 0

function console_main():            # the pip route's front (A4.13)
    record_command()
    sys.exit(main())

# ---- src/scripts/scsim.py: the suite's and the clone's front ----
#!/usr/bin/env python3
sys.path.insert(0, resolved(__file__).parents[1])    # src/
from scattering.cli.scsim import main, record_command
if __name__ == "__main__":
    record_command()
    sys.exit(main())

# ---- pyproject.toml ----
[project.scripts]  scsim = "scattering.cli.scsim:console_main"
[project] dependencies = the modules this package imports, with lower
    bounds no tighter than the suite's requirements.in (A9.1); h5py
    under the "batch" extra, pytest under "test"
[tool.setuptools.package-data] scattering.examples = ["*.toml"]
```

**The command log must not end the run either.** `record_command()`
appends to `./command`. In a directory the user cannot write (the
read-only installation above) it prints one line to standard error —
"cannot write ./command here (…); continuing without the command
log" — and returns. A convenience log is never a reason to refuse to
run the physics.

`scsimrc.py` is P10.9.

---

## 12.8 Verification

`tests/unit/test_session_state.py`,
`tests/integration/test_session.py`; the entry point's own tests are
in 12.10:

- `advance` stops at either end with `loop` off and wraps with it
  on; `step` pauses; `jump` clamps; `set_rate` stays in `[1, 16]`.
- `set_energy` preserves the frame fraction to within one frame
  for every pair of energies of the rutherford store.
- `cycle_tracked` visits every particle exactly once per `N` calls,
  ring-major for annuli and by `b` for a disc.
- **Determinism (A8.6(3)).** A `ScriptedControls` sequence issuing
  every command in `BINDINGS` (except `quit` last), run through
  `run_session` with an offscreen renderer over 60 ticks, leaves
  every store array bit-identical to a snapshot taken before.
- `save` writes a file that `load_and_resolve` reads to a
  `ResolvedRun` equal to the session's (P10.10).
- `scsim.main(["runs/rutherford.toml", "--offscreen", "--frames",
  "5", "--screenshot", tmp])` returns 0, writes a non-uniform image,
  and writes no `command` file (the log is in `__main__` only).
- `scsim.main([..., "--set", "fidelity.n_samples=20"])` builds a
  store with 20 samples.
- The loop draws at least one frame per tick with no physics call
  on the stack: `ui/` imports nothing from `orbits/`, `deflection/`,
  or `potentials/` (A8.6(1) extended; a structural test).
- Every key in `BINDINGS` except `q` and `Escape` begins `Ctrl+`;
  every command the dispatcher accepts has at least one key, and
  every key's command is accepted (the two tables agree).
- `toggle_ring` on ring 2 twice restores the state; `toggle_all_rings`
  from all-shown hides every ring, and again shows every ring;
  `set_graticule` clamps to `[4, 36]`.
- A scripted session issuing `("seek", 7)` ends paused on frame 7;
  `("set_energy", 1)` gives the same state as `energy_up` from 0.
- A scripted session with no camera command calls the renderer's
  camera-setting code once (a counter on the offscreen renderer);
  `save` after the renderer's camera was moved writes that camera.
- `initial_state` is playing; the run file's `[view]` still sets the
  camera, palette, tracked particle, and panels.

---

## 12.9 Deferred (D12.8, D12.10)

Interactive run controls with a rebuild (edit `b_max` in the window,
confirm the budget, swap the store) and the guess-the-potential mode
are not in this section. Both are additions to `apply` that call
`resolve` and `build_results_store` and swap `session.store`; the
loop and the state record need no change for them, which is why
the store is a field of `Session` and not a global.

---

## 12.10 Examples, the rc copy, and the self-check (`cli/examples.py`)

Specifies D12.13. Everything here finds its files THROUGH THE PACKAGE
and never relative to a script or the working directory; that is the
whole of what makes a clone, a linked suite, and an installed copy
behave alike.

```
function example_files() -> dict name -> path:
    # importlib.resources.files("scattering.examples"), every *.toml,
    # keyed by stem; sorted by name.

function locate_run_file(argument) -> path:
    if exists(argument): return argument              # a real file wins
    if argument has no directory part:
        stem = argument without a trailing ".toml"
        if stem in example_files():
            note on stderr: "using the packaged example <path>"
            return example_files()[stem]
    raise FileNotFoundError(
        "<argument>: no such run file. Packaged examples: <names>. "
        "Run one by name (scsim <name>), or copy them here with "
        "scsim --examples.")

function copy_without_overwriting(sources, directory) -> int:
    # Shared by the two copiers. Returns an exit status.
    try: create directory if missing
    for source in sources:
        target = directory / basename(source)
        if exists(target): print "kept   <target> (already here)"
        else:              copy; print "wrote  <target>"
    on OSError: print "cannot write in <directory> (<why>); choose a
        directory you can write, for example: scsim --examples
        ~/scattering-runs"; return 1
    return 0

function copy_examples(directory) -> int:
    return copy_without_overwriting(example_files().values(), directory)

function copy_rc_file(directory) -> int:
    return copy_without_overwriting([PACKAGE_DEFAULTS_DIR/"scsimrc.py"],
                                    directory)                 # P10.6

function self_check() -> int:                      # writes no file
    print python version, platform, and for each declared dependency
        its installed version or "MISSING"
    if any MISSING: print RESULT: FAIL -- <which>; return 1
    try:
        t0 = now
        rc = load_rc()
        resolved = load_and_resolve(example_files()["rutherford"],
            ["fidelity.n_samples=40", "fidelity.n_deflection_points=60"],
            rc)                                    # the real path, small
        store = build_results_store(resolved)
        print f"built {K} energies x {N} particles in {now - t0:.1f} s"
        prepare_offscreen()                        # P11.6
        renderer = VedoRenderer(palette, (640, 480), offscreen=True,
                                panels=())
        run_session(resolved, store, ScriptedControls([], 2), renderer, rc)
        image = renderer.screenshot(as_array=True); renderer.close()
    except Exception as problem:
        print RESULT: FAIL -- <type>: <problem>; return 1
    if image is uniform:
        print RESULT: FAIL -- the picture is blank: no working OpenGL
            context for offscreen drawing on this computer; return 1
    print RESULT: PASS; return 0
```

`self_check` catches every exception on purpose: its one job is to
turn whatever goes wrong on an unfamiliar computer into a line a
student can send to the instructor.

### Verification

`tests/integration/test_scsim_cli.py`,
`tests/unit/test_installed_copy.py`:

- `example_files()` is non-empty, every entry resolves with
  `load_and_resolve`, and its set of names equals the `*.toml` names
  in `runs/` (the link and the package are the same files).
- `locate_run_file`: an existing path is returned unchanged; a bare
  packaged name with and without `.toml` returns the packaged path; a
  local file of the same name wins; a name with a directory part, or
  an unknown name, raises with the examples listed.
- `copy_examples` into an empty directory writes every example;
  a second call writes nothing and reports each as kept; an edited
  copy is left unchanged; a read-only directory returns 1 with the
  remedy and no traceback.
- `copy_rc_file` writes a file that `load_rc([that directory])`
  loads, equal to the package defaults.
- `main(["no_such.toml"])` returns 2 and prints the examples;
  `main([])` and `main(["x.toml", "--examples"])` are usage errors.
- `record_command` writes nothing when a utility flag is present.
- `main(["--check"])` returns 0, prints `RESULT: PASS`, and leaves
  the working directory empty (skips where no GL context exists).
- **The installed-copy guarantee (A8.6(5)).** `load_rc` succeeds with
  the search restricted to the package; the object named by
  `[project.scripts] scsim` imports and is callable; every top-level
  third-party module imported anywhere under `src/scattering/` is
  covered by `[project] dependencies` or an extra; and
  `src/scripts/scsim.py` imports nothing but the standard library and
  `scattering.cli`.
- Manual, recorded in `dev/notes/`: build a wheel, install it in a
  fresh virtual environment outside the repository, and run
  `scsim --check`, `scsim --examples`, and `scsim rutherford` there.

