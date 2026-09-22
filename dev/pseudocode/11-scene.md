# Pseudocode 11. Geometry, the Scene Description, Palettes, and the Renderer

> **Parent:** [`../PSEUDOCODE.md`](../PSEUDOCODE.md) — index.
> **Specifies:** design section 11,
> [`../design/11-scene-and-geometry.md`](../design/11-scene-and-geometry.md).
> **Governs:** `src/scattering/geometry/` (`annulus.py`, `cone.py`,
> `orbit_plane.py`, `probe_depth.py`, `markers.py`),
> `src/scattering/render/` (`scene_description.py`, `palettes.py`,
> `panels.py`, `vedo_renderer.py`).
> **Status:** draft. The Tier-1 default particle count waits on the
> rendering-budget spike (ARCHITECTURE 9.3); everything else here
> does not.

---

## 11.1 Seam inventory: what the scene reads

The scene is built from a frozen `ResultsStore` through its read
interface (P6.1) and from the `ResolvedRun` (P10.1). Nothing here
computes physics or touches an array the store did not expose:

| Consumed | From | Produced by |
| --- | --- | --- |
| `frame`, `frame_velocity`, `frame_polar` `(k, n)` | store | P6.5 |
| `particle(k, i)` — the tracked particle's history | store | P6.5 |
| `trace(k, i)` | store | P6.4 |
| `tables(k)` — deflection, cross section, mirror, annulus map | store | P5 |
| `impact_parameter`, `azimuth`, `annulus_index` | store | P3 |
| `deflection[k]`, `turning_point[k]`, `out_direction[k]` | store | P5.8, P4 |
| `theta_min[k]`, `theta_head[k]`, `energies` | store | P5.5 |
| `drift(k)` | store | P4, P6.4 |
| `time_grid[k]`, `entry_index`, `exit_index` | store | P6.5 |
| `resolved.spec.beam.annuli` — the declared rings | resolved run | P10 |
| `resolved.settings.r_max`, `resolved.detector_radius` | resolved run | P10.7 |
| `resolved.spec.view` — palette, camera, tracked, panels | resolved run | P10 |
| `resolved.potential.admits_center()`, `describe()` | resolved run | P2 |
| `resolved.scales` — for display units | resolved run | P1 |
| `state.hidden_rings`, `graticule_lines` — what to draw | session | P12.2 |
| `rc.glyph_radius_fraction` — of `R̃_max` | rc | P10.6 |

The detector histogram (D11.2) and the recovered-potential panel
need P7 and P8; in this section they are placeholders that draw the
exact cross-section curve and nothing, respectively, and the panel
list in `ViewSpec` accepts their names now.

---

## 11.2 Records

```
record Drawable:
    quantity   str          the physical quantity, for the legend
    section    str          design section that defines it, e.g. "5.7"
    geometry   Geometry     one of the kinds below, in scene coords
    role       str          a palette key (11.5)
    label      str | None   text anchored to the geometry
    panel      str          "scene" or a 2D panel name
    static     bool         unchanged between frames; cached

Geometry kinds (plain data, numpy arrays):
    Points     positions (n, 3), radius (display units)
    Polyline   points (n, 3), closed bool
    Ring       center (3,), normal (3,), inner, outer   (a flat annulus)
    SphereBand center, radius, theta_1, theta_2, azimuth_range
    Sphere     center, radius
    Plane      center, normal, half_extent
    Arrow      start (3,), direction (3,), display_length
    Arc        center, radius, start_dir, end_dir, plane_normal
    Segment    start (3,), end (3,)
    Text       anchor (3,), text

record Scene:
    static     list of Drawable     per (energy index, view)
    dynamic    list of Drawable     per frame
    telemetry  Telemetry            the numbers for the overlay

record Telemetry:
    scene_time, frame_index, n_samples, energy_index, energy_label
    tracked:  index, impact, azimuth, r, phi, speed, kinetic, potential,
              total_energy, angular_momentum, deflection_deg, turning_point
    exterior_deflection_max, energy_drift_max, angmom_drift_max
    provider, mirror_diff
    ratio_of_scene_to_wall_time   filled by the session (P12)
```

---

## 11.3 Geometry (`geometry/`)

All functions return `Geometry` values in scene coordinates and
draw nothing (design 11.1).

```
function annulus_ring(annulus: AnnulusSpec, r_max) -> Ring:
    # In the entry plane z = -r_max (D4.6), normal +z.
    return Ring(center=(0, 0, -r_max), normal=(0, 0, 1),
                inner=annulus.impact, outer=annulus.impact + annulus.width)

function cone_band(annulus_map: AnnulusMap, sign, r_detect) -> SphereBand:
    # On the detector sphere between the two asymptotic angles
    # (D5.7). For an attractive potential the cone is on the far
    # side of the axis (D4.8): the band is the same in theta, and
    # the label says "far side"; azimuth_range is full for a ring.
    return SphereBand(center=0, radius=r_detect,
                      theta_1=min(map.theta_1, map.theta_2),
                      theta_2=max(map.theta_1, map.theta_2),
                      azimuth_range=(0, 2 pi))

function detector_sphere(r_detect) -> Sphere
function unmeasured_caps(theta_min, theta_head, r_detect)
        -> (SphereBand(0..theta_min), SphereBand(theta_head..pi))   # D7.3
function beam_axis(r_detect) -> Segment((0,0,-r_detect), (0,0,+r_detect))
function entry_plane(r_max, half_extent) -> Plane((0,0,-r_max), +z, half_extent)

function probe_depth(potential, energy, beam_smallest_impact)
        -> Sphere | Points:
    # D11.4. The head-on turning point when the center is admitted,
    # else a marker at the turning point of the smallest b thrown.
    if potential.admits_center():
        (r_min, _) = turning_point_from_g(potential, energy, 0.0)   # P5.2
        return Sphere(0, r_min)          label "no orbit enters"
    (r_min, _) = turning_point_from_g(potential, energy, beam_smallest_impact)
    return Points([...on the tracked orbit's pericenter...], radius)
           label "smallest impact parameter thrown"

function orbit_plane(azimuth, half_extent) -> Plane:
    # Contains z and e_rho(azimuth): normal = (-sin phi, cos phi, 0).
    return Plane(center=0, normal=(-sin azimuth, cos azimuth, 0), half_extent)

function tracked_markers(store, k, i, n, r_max) -> list of Geometry:
    (x, y, z) = store.frame(k, n)[i];  v = store.frame_velocity(k, n)[i]
    (r, phi)  = store.frame_polar(k, n)[i]
    azimuth   = store.azimuth[i]
    pericenter_dir = the in-plane pericenter direction embedded at azimuth
                     (recovered from polar: the direction at phi = 0)
    return [
      Segment(0, (x, y, z))                       role "radius"   label "r"
      Segment(0, 0.25 r_max * pericenter_dir)     role "polar"
                                          label "pericenter direction"
                                          # dotted: the reference line
                                          #   phi is measured from (D11.6)
      Arc(0, 0.3 r_max*?, pericenter_dir, (x,y,z)/r, plane normal)
                                                  role "polar"    label "phi"
      Arrow((x,y,z), v/|v|, display_length)       role "velocity"
                                                  label "v (direction only)"
      Points([turning point on the trace], 0.8 * glyph)
                                                  role "turning"  label "r_min"
      Segment(entry asymptote), Segment(exit asymptote)
                                                  role "asymptote"
      Arc(between the two asymptote directions)
                                            role "deflection" label "Theta"
    ]
```

The asymptote segments are the inbound and outbound free-flight
lines: from the entry sample backwards to the plane, and from the
exit sample along `out_direction[k, i]` to the detector sphere.
`phase` picks those samples (P6.5).

---

## 11.4 The scene description (`render/scene_description.py`)

```
function build_static(store, resolved, k, view) -> list of Drawable:
    annuli = resolved.spec.beam.annuli;  maps = store.tables(k).annulus_map
    r_max, r_det = resolved.settings.r_max, resolved.detector_radius
    out = []
    out += [Drawable("beam axis", "4.3", beam_axis(r_det), "axis", "z",
                     "scene", True)]
    out += [Drawable("entry plane", "4.6", entry_plane(r_max, ...), "plane",
                     "t = 0", "scene", True)]
    out += [Drawable("detector sphere", "7.2", detector_sphere(r_det),
                     "detector", f"R_detect = {r_det:.3g}", "scene", True)]
    for (theta_lo, theta_hi) in unmeasured_caps(store.theta_min[k],
                                                store.theta_head[k], r_det):
        out += [Drawable("unmeasured", "7.3", ..., "unmeasured", "unmeasured",
                         "scene", True)]
    for (j, (ring, map)) in enumerate(zip(annuli, maps)):
        out += [Drawable("annulus", "5.7", annulus_ring(ring, r_max),
                         f"annulus_{j}", f"b_{j} = {ring.impact:.3g}",
                         "scene", True)]
        out += [Drawable("cone", "5.7", cone_band(map, sign, r_det),
                         f"annulus_{j}", f"theta_{j}", "scene", True)]
    out += [Drawable("probe depth", "2.3", probe_depth(...), "probe",
                     "no orbit enters", "scene", True)]
    for i in 0 .. N-1:
        out += [Drawable("trace", "4.10", Polyline(store.trace(k, i)),
                         role_for_particle(store, i), None, "scene", True)]
        # Free-flight legs drawn dashed: the samples with phase != 0,
        # as two Polylines with role "free_flight".
    out += [Drawable("orbit plane", "4.3", orbit_plane(azimuth of tracked),
                     "orbit_plane", None, "scene", True)]
    return out

function glyph_radius(resolved, rc) -> float:
    # D11.6: a FRACTION of R_max, never an absolute length.
    return rc.glyph_radius_fraction * resolved.settings.r_max

function shown_particles(store, hidden_rings, tracked) -> index array:
    # D11.11: a hidden ring hides its particles, except the tracked one.
    # For a disc beam the "ring" of particle i is its band (band_index).
    ring_of = store.annulus_index if store.beam.layout == "annuli"
              else band_index(store)
    return [i for i in 0..N-1 if ring_of[i] not in hidden_rings
                                  or i == tracked]

function band_index(store) -> int array:
    # D11.11: a disc's particles fall into 8 equal-count bands of b.
    order = argsort(store.impact_parameter)
    band = empty(N); band[order] = floor(8 * arange(N) / N)
    return band

function build_frame(store, resolved, k, n, tracked, hidden_rings, rc)
        -> (list of Drawable, Telemetry):
    positions = store.frame(k, n)
    shown = shown_particles(store, hidden_rings, tracked)
    glyph = glyph_radius(resolved, rc)
    out = [Drawable("particles", "6.3",
                    Points(positions[shown], glyph),
                    roles per shown particle (role_for_particle), None,
                    "scene", False)]
    out += tracked_markers(store, k, tracked, n, r_max) as Drawables
    out += [Drawable("tracked", "12.6",
                     Points([positions[tracked]], 1.6 * glyph),
                     "tracked", f"particle {tracked}", "scene", False)]
    return out, telemetry_for(store, resolved, k, n, tracked)

function role_for_particle(store, i) -> str:
    # One hue per ring (annuli) or per band of b (disc), D11.11.
    j = store.annulus_index[i] if store.beam.layout == "annuli"
        else band_index(store)[i]
    return f"annulus_{j mod 8}"
```

**Hidden rings in `build_static`.** The static drawables of a
hidden ring — its annulus ring, its cone, its traces and free-flight
legs — are omitted the same way: `build_static` takes
`hidden_rings` and skips a drawable whose ring (or band) is hidden,
except the tracked particle's trace. `hidden_rings` is therefore part
of the static cache key (P12.6). The detector sphere, its bands, the
caps, the probe sphere, and the entry plane never depend on it.

**The ring legend** (D11.11) is built beside the scene, not drawn in
it:

```
function ring_legend_lines(store, resolved, k, hidden_rings) -> list:
    table, xsec, mirror, maps = store.tables(k)
    rings = resolved.spec.beam.annuli if layout == "annuli"
            else the 8 bands' [b_lo, b_hi] from band_index
    for j, (ring, ring_map) in enumerate(zip(rings, maps)):
        lo, hi = degrees(ring_map.theta_1), degrees(ring_map.theta_2)
        n = count of particles with ring j
        mark = "   hidden" if j in hidden_rings else ""
        lines += [f"ring {j}  b = {ring.impact:.3g}   theta {lo:.1f} - "
                  f"{hi:.1f} deg   {n} particles{mark}"]
    return lines           # the renderer colours line j in hue j
```

For a disc beam the `maps` are computed for the bands' edges from
the deflection table (P5.7's `annulus_to_cone` on `[b_lo, b_hi]`),
which is the same function the annulus case uses.

Static drawables are built once per `(k, view)` and cached by the
session; only `build_frame` runs per tick (design 11.7).

### 2D panels (`render/panels.py`)

Each panel is a function of the store and the frame returning a
`PanelData` record the renderer draws with matplotlib into an image
placed in the window, or with vedo's 2D plotting; the choice is the
renderer's (11.6). The data records:

```
panel_deflection(store, k, tracked)   -> curves Theta(b) (both signs if
                                         mirror table), marker at tracked b
panel_cross_section(store, k)         -> the exact curve; the measured
                                         bars arrive with P7
panel_effective_potential(store, k, tracked)
    -> V_eff(r) = V(r) + L^2 / (2 r^2) with L = sqrt(2E) b_tracked,
       the line E, the marker r_min; from potential.value and P1.5
panel_annulus_to_cone(store, k)       -> the AnnulusMap fields per ring
panel_telemetry(telemetry, scales)    -> formatted lines via
                                         format_natural (P1.4)
panel_recovered_potential             -> empty until P8
panel_error_budget                    -> the drift maxima now; the
                                         full record with P9
```

---

## 11.5 Palettes (`render/palettes.py`)

```
record Encoding:
    color        (r, g, b) in [0, 1]
    line_style   "solid" | "dashed" | "dotted" | "dash_dot"
    weight       float
    opacity      float
    glyph        "sphere" | "cube" | "none"

ROLES = ["axis", "plane", "detector", "unmeasured", "probe",
         "annulus_0" .. "annulus_7", "disc", "free_flight", "orbit_plane",
         "radius", "polar", "velocity", "turning", "asymptote",
         "deflection", "tracked", "exact_curve", "measured", "stat_band",
         "tail_band", "recovered", "mirror", "true_potential"]

PALETTES = {"light": {...}, "dark": {...}, "colorblind": {...}}
    # Each maps every role to an Encoding. annulus_j hues are a
    # categorical set of eight; "colorblind" uses an Okabe-Ito set.

REDUNDANCY = [                      # design 11.5's table, as data
    (("annulus_0", "annulus_1"), "label"),
    (("free_flight", "annulus_0"), "line_style"),
    (("measured", "unmeasured"), "line_style"),
    (("stat_band", "tail_band"), "line_style"),
    (("recovered", "true_potential"), "line_style"),
    (("tracked", "disc"), "glyph_or_weight"),
]

function resolve_encoding(palette_name, role) -> Encoding:
    return PALETTES[palette_name][role]      # KeyError = a bug: every
                                             #   role in every palette

function check_redundancy(palette) -> list of violations:
    for ((a, b), channel) in REDUNDANCY:
        if palette[a].channel == palette[b].channel: violation
```

---

## 11.6 The renderer (`render/vedo_renderer.py`)

The only module that imports vedo or VTK (A6.5). Mirrors the
rigid-body tool's renderer.

```
class VedoRenderer:
    __init__(palette_name, size, offscreen):
        # ONE 3D viewport: the panels are not in this window (D11.10).
        self.plotter = vedo.Plotter(size=size, offscreen=offscreen, axes=0)
        self.palette = PALETTES[palette_name]
        self.static_actors = {}          # (k, view_key) -> list of actors
        self.frame_actors  = []
        self.camera_applied = None       # the last camera dict applied
        self.sliders = None              # built on the first on-screen show
        self.legend_visible = True

    render(scene: Scene, camera, k, view_key, state, ring_lines):
        if (k, view_key) not in self.static_actors:
            self.static_actors[(k, view_key)] = [
                actor_for(d, self.palette) for d in scene.static]
            self.plotter.at(0).remove(all previous static).add(these)
        self.plotter.remove(self.frame_actors)
        self.frame_actors = [actor_for(d, self.palette) for d in scene.dynamic]
        self.plotter.add(self.frame_actors)
        self.draw_text(scene.telemetry.lines(), "top-right")
        self.draw_text(ring_lines, "top-left", colour line j by hue j)
        if self.legend_visible: self.draw_text(KEY_LEGEND, "bottom-left")
        # D12.14: the camera is applied ONLY when it changed.
        if camera != self.camera_applied:
            set the camera from (azimuth, elevation, distance * r_detect)
            self.camera_applied = dict(camera)
        if on screen and self.sliders is None: self.build_sliders(state)
        self.sync_sliders(state)         # follow the frame while playing
        self.plotter.render()

    read_camera() -> {azimuth_deg, elevation_deg, distance}:
        # D12.14: for Save. Inverse of the setting above: position
        # relative to the focal point, distance in units of r_detect.

    build_sliders(state):
        # D12.4, D12.5: two vedo slider widgets in this window.
        time:   plotter.add_slider(on_time, 0, n_samples - 1, value=frame,
                    pos=along the bottom, title="frame")
        energy: plotter.add_slider(on_energy, 0, n_energies - 1,
                    value=k, pos=right edge, vertical, title="energy")
        # The callbacks do not touch the state; they queue a command
        # with a value for the controls source (P12.5): ("seek", frame)
        # and ("set_energy", k). The loop applies them like keys.

    sync_sliders(state):
        # Move a slider's knob to the state without firing its callback.

    set_graticule(n): rebuild the detector sphere's lines, D11.12.
    screenshot(path=None, as_array=False) -> plotter.screenshot(...)
    close(): also close the panel windows (below)

function actor_for(drawable, palette) -> vedo actor:
    encoding = resolve_encoding(palette, drawable.role)
    match drawable.geometry:
        Points     -> vedo.Points or Spheres(radius)
        Polyline   -> vedo.Line, with line style via VTK stipple as the
                      rigid-body renderer does
        Ring       -> vedo.Disc(r1=inner, r2=outer) positioned and oriented
        SphereBand -> vedo.Sphere sliced by theta: a parametric mesh of
                      the band, or a Sphere with a clipping by two cones
        Sphere     -> a GRATICULE (D11.12): n latitude circles and 2n
                      longitude semicircles as vedo.Line, thin, in the
                      sphere's hue; n from state.graticule_lines
        Plane      -> vedo.Plane
        Arrow      -> vedo.Arrow at display_length
        Arc        -> vedo.Arc
        Segment    -> vedo.Line
        Text       -> vedo.Text3D or 2D caption
    if drawable.label: attach a caption / flag
    apply color, opacity, weight
```

**The panel windows (`render/panel_windows.py`, D11.10).** A second
small module beside the renderer; it imports matplotlib and nothing
of vedo.

```
class PanelWindows:
    __init__(panel_names, palette, background, offscreen):
        self.figures = {}            # name -> matplotlib Figure
        self.keys = {}               # name -> the key last drawn
        self.interactive = not offscreen and a GUI backend is available
        # Backend choice happens HERE, before pyplot is imported:
        #   offscreen -> "Agg"; else try "TkAgg", fall back to "Agg"
        #   with one line on stderr (D11.10).

    update(name, data: PanelData, key):
        if key == self.keys.get(name): return         # nothing changed
        figure = self.figures.get(name) or new figure titled name
        if self.interactive and figure's window was closed: reopen it
        draw_panel_into(figure, data, palette, background)   # panels.py
        figure.canvas.draw_idle()
        self.keys[name] = key

    pump():
        # D12.3 step 4: keep the figure windows responsive.
        if self.interactive: figure.canvas.flush_events() for each

    image(name) -> RGB array:    # the offscreen path; unchanged tests
    close(): close every figure
```

`panels.py` keeps `build_panel` and gains `draw_panel_into(figure,
...)`; `render_panel` (array out) becomes a wrapper that draws into an
Agg figure and reads it back, so that the pixel tests are unchanged.

**Offscreen and the pixel check.** A VTK window without a valid
OpenGL context accepts `Render()` and draws nothing (the rigid-body
spike's trap), so the render test reads the screenshot back as an
array and asserts it is not uniform.

**Choosing VTK's window class (`render/offscreen.py`).** VTK picks
its window class when it is first imported, from the environment
variable `VTK_DEFAULT_OPENGL_WINDOW`. The rule, which is the
`physdemo` suite's rule and is portable by construction:

```
function prepare_offscreen() -> bool:
    # Call BEFORE anything imports vtk or vedo. Linux only: on
    # macOS and Windows the default window class draws offscreen
    # with no help, and EGL does not exist there.
    if not sys.platform.startswith("linux"): return False
    if "vtkmodules" in sys.modules or "vtk" in sys.modules:
        warn "VTK is already imported; the window class is fixed"
        return False
    os.environ.setdefault("VTK_DEFAULT_OPENGL_WINDOW",
                          "vtkEGLRenderWindow")
    return True
```

- **Offscreen requested ⇒ EGL, whatever `DISPLAY` says.** A
  `DISPLAY` that is set but dead (a stale SSH forwarding) is common
  on clusters, and VTK's X window class hangs on it. So the decision
  keys on what was ASKED FOR, not on `DISPLAY`: `scsim --offscreen`,
  the test suite (`tests/conftest.py`), and the spikes call
  `prepare_offscreen()` before importing the renderer.
- **On screen ⇒ leave VTK alone.** The default X (or Cocoa, or
  Win32) window class is the right one when a window is wanted.
- **Import-time fallback in `vedo_renderer.py`:** on Linux with
  neither `DISPLAY` nor `WAYLAND_DISPLAY` set, no window can open at
  all, so the renderer calls `prepare_offscreen()` itself. An
  explicit `VTK_DEFAULT_OPENGL_WINDOW` in the environment always
  wins (`setdefault`).

The earlier rule — EGL whenever `DISPLAY` is unset, on any platform —
was wrong twice: macOS never sets `DISPLAY`, and a stale `DISPLAY`
defeated it on the cluster.

---

## 11.7 Labeled distortions (D11.6)

- Particle glyph radius `rc.glyph_radius` in natural units, stated
  in the legend as `glyphs: r = 0.02 (display)`.
- The velocity arrow's `display_length` is `0.1 r_max`; label
  `v (direction only)`; magnitude in the telemetry.
- The detector sphere at opacity 0.15; label gives its radius.

---

## 11.8 Verification

`tests/unit/test_geometry.py`, `tests/unit/test_palettes.py`,
`tests/integration/test_render.py`:

- Every drawable from `build_static` and `build_frame` on the
  rutherford store has non-empty `quantity`, `section`, `label` or
  `None` by design, `role` in `ROLES`, `panel` known.
- Every role exists in every palette; `check_redundancy` returns no
  violations for any of the three.
- `cone_band` for annulus `j` spans exactly
  `[|Theta(b + db)|, |Theta(b)|]` from the table, and the particles
  of ring `j` at their last frame lie within it in polar angle
  (asymptotic mode) to the `b / R_detect` offset of D7.2.
- `probe_depth` radius equals `1 / E_k` at each energy index of a
  repulsive Coulomb store.
- `orbit_plane(azimuth)` contains `store.frame(k, n)[i]` for every
  `n` of a tracked particle at that azimuth (dot with the normal is
  `< 1e-10`).
- `geometry/` and `scene_description.py` import nothing from
  `vedo_renderer.py`; `vedo` is imported only there (A8.6(1)).
- Offscreen render of the rutherford store at frame `n_samples / 2`
  produces a non-uniform screenshot array; a second render at
  another frame differs from it; rendering leaves the store
  bit-identical.
- `glyph_radius` equals `rc.glyph_radius_fraction * r_max` (D11.6);
  with the shipped rc it is at least 1/200 of the window's `4 r_max`.
- `shown_particles` with every ring hidden is `[tracked]`; with none
  hidden it is every index; for a disc beam `band_index` gives eight
  bands whose counts differ by at most one.
- `ring_legend_lines` gives one line per ring, whose angles equal the
  cone band's for that ring at that energy, and says `hidden` exactly
  for the hidden ones.
- A `Sphere` drawable becomes `n + 2n` line actors for
  `graticule_lines = n`; `n` is clamped to `[4, 36]`.
- `PanelWindows` offscreen: `image(name)` equals `render_panel` on
  the same data; `update` with an unchanged key draws nothing (a
  counter); with a changed key draws once.
- The renderer applies the camera once for a scripted session with
  no camera change (a counter), and `read_camera()` after applying a
  camera returns it to 1e-9.
