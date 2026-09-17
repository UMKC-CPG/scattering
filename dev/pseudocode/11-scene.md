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
      Arc(0, 0.3 r_max*?, pericenter_dir, (x,y,z)/r, plane normal)
                                                  role "polar"    label "phi"
      Arrow((x,y,z), v/|v|, display_length)       role "velocity"
                                                  label "v (direction only)"
      Points([turning point on the trace])        role "turning"  label "r_min"
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

function build_frame(store, resolved, k, n, tracked)
        -> (list of Drawable, Telemetry):
    positions = store.frame(k, n)
    out = [Drawable("particles", "6.3",
                    Points(positions, rc.glyph_radius),
                    roles per particle (role_for_particle), None, "scene",
                    False)]
    out += tracked_markers(store, k, tracked, n, r_max) as Drawables
    out += [Drawable("tracked", "12.6",
                     Points([positions[tracked]], 1.6 * glyph),
                     "tracked", f"particle {tracked}", "scene", False)]
    return out, telemetry_for(store, resolved, k, n, tracked)

function role_for_particle(store, i) -> str:
    j = store.annulus_index[i]
    return f"annulus_{j}" if j >= 0 else "disc"
```

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
    __init__(palette_name, size, offscreen, panels):
        self.plotter = vedo.Plotter(N=1 + len(panels) layout, size=size,
                                    offscreen=offscreen, axes=0)
        self.palette = PALETTES[palette_name]
        self.static_actors = {}          # (k, view_key) -> list of actors
        self.frame_actors  = []

    render(scene: Scene, camera, k, view_key):
        if (k, view_key) not in self.static_actors:
            self.static_actors[(k, view_key)] = [
                actor_for(d, self.palette) for d in scene.static]
            self.plotter.at(0).remove(all previous static).add(these)
        self.plotter.at(0).remove(self.frame_actors)
        self.frame_actors = [actor_for(d, self.palette) for d in scene.dynamic]
        self.plotter.at(0).add(self.frame_actors)
        for (index, panel) in enumerate(panels, start=1):
            self.plotter.at(index).show(panel_image(panel data))
        self.plotter.at(0).camera from `camera` (azimuth, elevation, distance
                                                 relative to r_detect)
        self.plotter.render()

    screenshot(path=None, as_array=False) -> plotter.screenshot(...)
    close()

function actor_for(drawable, palette) -> vedo actor:
    encoding = resolve_encoding(palette, drawable.role)
    match drawable.geometry:
        Points     -> vedo.Points or Spheres(radius)
        Polyline   -> vedo.Line, with line style via VTK stipple as the
                      rigid-body renderer does
        Ring       -> vedo.Disc(r1=inner, r2=outer) positioned and oriented
        SphereBand -> vedo.Sphere sliced by theta: a parametric mesh of
                      the band, or a Sphere with a clipping by two cones
        Sphere     -> vedo.Sphere, alpha from encoding
        Plane      -> vedo.Plane
        Arrow      -> vedo.Arrow at display_length
        Arc        -> vedo.Arc
        Segment    -> vedo.Line
        Text       -> vedo.Text3D or 2D caption
    if drawable.label: attach a caption / flag
    apply color, opacity, weight
```

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
