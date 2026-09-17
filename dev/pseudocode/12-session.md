# Pseudocode 12. The Scrubber, the Interactive Session, and `scsim.py`

> **Parent:** [`../PSEUDOCODE.md`](../PSEUDOCODE.md) — index.
> **Specifies:** design section 12,
> [`../design/12-scrubber-and-session.md`](
> ../design/12-scrubber-and-session.md).
> **Governs:** `src/scattering/ui/session_state.py`,
> `src/scattering/ui/controls.py`, `src/scattering/ui/vedo_controls.py`,
> `src/scattering/ui/interactive_session.py`, `src/scripts/scsim.py`.
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
    show_mirror    bool

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
BINDINGS = {
  "space": ("play_pause",   "toggle playing"),
  "r":     ("reverse",      "flip direction"),
  ".":     ("step_forward", "one frame, then pause"),
  ",":     ("step_back",    "one frame back, then pause"),
  "plus":  ("faster",       "rate x2, up to 16"),
  "minus": ("slower",       "rate / 2, down to 1"),
  "e":     ("jump_entry",   "tracked particle's entry"),
  "p":     ("jump_pericenter", "tracked particle's pericenter"),
  "x":     ("jump_exit",    "tracked particle's exit"),
  "Home":  ("jump_start", ""),  "End": ("jump_end", ""),
  "l":     ("loop",         "toggle loop at the end"),
  "bracketleft":  ("energy_down", ""),  "bracketright": ("energy_up", ""),
  "Tab":   ("track_next",   "next tracked particle"),
  "m":     ("mirror",       "toggle the mirror deflection curve"),
  "d":     ("detector_mode","asymptotic / position"),
  "c":     ("palette",      "cycle light / dark / colorblind"),
  "s":     ("save",         "write the resolved run file"),
  "h":     ("help",         "show this legend"),
  "q":     ("quit",         ""),
}

function apply(command, session) -> Session:
    state, store = session.state, session.store
    S = store.n_samples
    match command:
      "play_pause":   state = replace(state, playing=not state.playing)
      "reverse":      state = replace(state, direction=-state.direction)
      "step_forward": state = step(state, S, +1)
      "step_back":    state = step(state, S, -1)
      "faster":       state = set_rate(state, 2)
      "slower":       state = set_rate(state, 0.5)
      "jump_entry":   state = jump(state, S, store.entry_index[k, tracked])
      "jump_pericenter":
          k, i = state.energy_index, state.tracked
          state = jump(state, S, argmin(store.polar[k, i, :, 0]))
      "jump_exit":    state = jump(state, S, store.exit_index[k, tracked])
      "jump_start":   state = jump(state, S, 0)
      "jump_end":     state = jump(state, S, S - 1)
      "loop":         state = replace(state, loop=not state.loop)
      "energy_down" | "energy_up":
          k = clamp(state.energy_index -/+ 1, 0, store.n_energies - 1)
          state = set_energy(state, k, S)
      "track_next":   state = cycle_tracked(state, store, +1)
      "mirror":       state = replace(state, show_mirror=not ...)
      "detector_mode": state = replace(state, detector_mode=other)
      "palette":      state = replace(state, palette=next in cycle)
                      session.renderer.set_palette(state.palette)
      "save":         write_back(session.resolved with view = state,
                                 rc.output_dir / "<stem>.resolved.toml")
      "help":         session.renderer.show_legend(BINDINGS)
      "quit":         session.running = False
    return replace(session, state=state)

function control_legend_lines() -> list of str:
    return [f"{key:>8}  {help}" for key, (_, help) in BINDINGS.items()]
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
    _on_key_press(event): key = event.keypress; if key in BINDINGS:
        self.queue.append(BINDINGS[key][0])
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
        energy_index=0, frame_index=0, rate=1, playing=False,
        direction=+1, loop=False,
        tracked=resolved.spec.view.tracked_particle,
        palette=resolved.spec.view.palette,
        camera=resolved.spec.view.camera,
        panels=resolved.spec.view.panels,
        detector_mode="asymptotic", show_mirror=False)
    session = Session(resolved, store, state, renderer, controls, {}, ...)
    session.running = True
    wall_start = now();  scene_advanced = 0.0
    while session.running and not controls.window_closed():
        # 1. Advance (D12.3 step 1).
        previous = state.frame_index
        state = advance(state, store.n_samples)
        scene_advanced += |store.time_of(k, state.frame_index)
                           - store.time_of(k, previous)|
        # 2. Build the scene: static from the cache, dynamic now.
        view_key = (state.palette, state.show_mirror, state.tracked)
        if (state.energy_index, view_key) not in session.static_cache:
            session.static_cache[...] = build_static(store, resolved,
                                                     state.energy_index, state)
        dynamic, telemetry = build_frame(store, resolved,
                                         state.energy_index,
                                         state.frame_index, state.tracked)
        telemetry.ratio_of_scene_to_wall_time = scene_advanced
                                                / max(1e-9, now() - wall_start)
        scene = Scene(static=session.static_cache[...], dynamic=dynamic,
                      telemetry=telemetry)
        # 3. Draw once.
        renderer.render(scene, state.camera, state.energy_index, view_key)
        # 4. Pump and apply controls.
        controls.pump()
        for command in controls.read():
            session = apply(command, session)
        state = session.state
    return state
```

No physics runs in the loop (D12.3): step 2 is slicing and glyph
placement. The static cache is keyed by everything a static
drawable depends on; changing the tracked particle rebuilds the
orbit-plane drawable, which is why `tracked` is in the key.

---

## 12.7 The entry point (`src/scripts/scsim.py`)

Follows the template's `XYZ.py` / `XYZrc.py` idiom exactly
(`CLAUDE.md`, "Command Logging"): `record_command()` at module
level, called from `__main__`; `main(argv=None)` for the tests.

```
function main(argv=None) -> int:
    args = parse(argv):
        runfile                positional
        --set TABLE.KEY=VALUE  repeatable
        --offscreen            no window; render to memory
        --frames N             run N ticks then exit (implies scripted
                               controls; with --offscreen for tests)
        --screenshot PATH      after the last frame
        --script "tick:command,..."   scripted controls
        --palette, --tracked   overrides of [view] (viewing only)
    if args.offscreen and not (args.frames or args.script):
        usage error: "--offscreen needs --frames N or --script ..."
        # Interactive controls on a window nobody can see would run
        # forever with no way to stop them; refuse before any work.
    rc = load_rc()                                      # P10.6
    resolved = load_and_resolve(args.runfile, args.set, rc)   # P10.8
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

if __name__ == "__main__":
    record_command()
    sys.exit(main())
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
`tests/integration/test_session.py`, `tests/integration/test_scsim.py`:

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

---

## 12.9 Deferred (D12.8, D12.10)

Interactive run controls with a rebuild (edit `b_max` in the window,
confirm the budget, swap the store) and the guess-the-potential mode
are not in this section. Both are additions to `apply` that call
`resolve` and `build_results_store` and swap `session.store`; the
loop and the state record need no change for them, which is why
the store is a field of `Session` and not a global.
