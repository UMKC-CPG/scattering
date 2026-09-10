# Design 11. Scene Description, Geometry, and Palettes

> **Parent:** [`../DESIGN.md`](../DESIGN.md) — design index.
> **Status:** draft. The rendering budget spike (`dev/TODO.md`,
> ARCHITECTURE A9.3) sets the Tier-1 default particle count and is
> not yet run.
> **Serves:** G1 (annulus to cone), G3 (every quantity labeled), G5
> (probe depth), P7 (transparency), P8 (palettes), P11 (physics
> decoupled from presentation), P14 (distortions labeled);
> ARCHITECTURE A4.9 (`geometry/`), A4.12 (`render/`), A6.5 (the
> renderer boundary).
> **Depends on:** Sections 4, 5, 6, 7, 8, 9.
> **Implemented by:** pseudocode section 11.

---

## 11.1 Purpose and scope

This is where the quantities the earlier sections computed become
something on a screen, and the design follows the rigid-body tool's
three-hand split exactly: `geometry/` computes *what* the
constructions are, in scene coordinates, and draws nothing;
`render/scene_description.py` lists them as renderer-agnostic
drawables; `render/vedo_renderer.py` alone turns drawables into
pixels and is the only module that names vedo or VTK (A6.5). This
section specifies the first two hands and the palette that sits
between the second and third. It does not specify the interaction
(Section 12).

---

## 11.2 Every drawable is a named quantity

Nothing is drawn that does not stand for a quantity a student can
trace to an equation (P7). A drawable is a *quantity* with a
geometry, a role, a label, and the section that defines it; the
label travels with it. The inventory:

### The 3D scene

| Drawable | Quantity | Section |
| --- | --- | --- |
| Particle glyphs | positions at the current frame | 6.3 |
| Traces | the orbit paths, adaptive polylines | 4.10 |
| Free-flight legs | the straight approach and exit, `phase ≠ 0` | 4.6 |
| Beam axis | `ẑ` | 4.3 |
| Entry plane | `z̃ = −Z̃₀`, the `t̃ = 0` pulse | 4.6 |
| Annulus rings | `[b̃, b̃ + db̃]` per declared annulus | 3.3, 5.7 |
| Cones | `[θ₁, θ₂]` per annulus, on the detector sphere | 5.7 |
| Detector sphere | `R̃_detect`, with bin bands | 7.2, 7.4 |
| Unmeasured caps | the forward and backward cones of 7.3 | 7.3 |
| Probe-depth sphere | `r̃_min(b̃ = 0)` at the current energy | 2.3, G5 |
| Scattering center | the origin | — |
| Orbit plane | the tracked particle's plane, translucent | 4.3 |
| `r` and `φ` markers | radius line and angle arc, tracked particle | 4.5 |
| Velocity arrow | `ṽ` of the tracked particle | 6.3 |
| Turning-point marker | `r̃_min` on the tracked orbit | 2.3 |
| Asymptote lines | incoming and outgoing, tracked particle | 2.4 |
| Deflection arc | `Θ` between the asymptotes | 2.4 |

### The 2D panels

| Panel | Content | Section |
| --- | --- | --- |
| Deflection function | `Θ(b̃)`, both signs; tracked particle |
| | marked | 5.4, 5.6 |
| Cross section | histogram bars with errors, exact curve, |
| | unmeasured hatching | 7.5 |
| Effective potential | `Ṽ + L̃² / 2r̃²`, tracked particle, with |
| | `Ẽ` and `r̃_min` | 2.3 |
| Recovered potential | `V(r)` from the inversion, bands, reach, mirror | 8.8 |
| Annulus-to-cone | `ΔA`, `ΔΩ`, their ratio, `dσ/dΩ` at the midpoint | 5.7 |
| Error budget | the record of 9.8, three columns | 9.8 |
| Telemetry | `t̃`, frame, energy, tracked `(r̃, φ, ṽ, Ẽ, L̃)` | 6, 9 |

The negative rule holds: a drawable with no quantity behind it does
not go in. No decorative geometry, no unlabeled helper lines.

---

## 11.3 The annulus and the cone (G1)

The tool's central image, specified as geometry:

**The annulus** is a flat ring in the entry plane `z̃ = −Z̃₀`,
inner radius `b̃`, outer `b̃ + db̃`, centered on the axis. It is
filled, translucent, and labeled with its `b̃` and its area `ΔA`.
Its particles start on it (they sit at exactly `b̃`; the ring's
width is `db̃`, drawn).

**The cone** is the band on the detector sphere between polar
angles `θ₁ = θ(b̃ + db̃)` and `θ₂ = θ(b̃)` (5.6), same hue as its
annulus, labeled with `ΔΩ`. For an attractive potential it is on
the far side of the axis (4.8), and the label says so.

**The ratio** `ΔA / ΔΩ` is shown beside `dσ/dΩ` at the annulus
midpoint, in the annulus-to-cone panel, updated as `db̃` is edited.
A student who narrows `db̃` watches the ring thin, the cone narrow,
and the two numbers converge.

The link between a ring and its cone is carried three ways (11.5):
shared hue, a shared index label (`b₁`, `θ₁`), and — when the
scrubber is at a frame where the ring's particles are in flight —
the particles themselves, which are the ring in motion.

---

## 11.4 The probe-depth sphere (G5)

A translucent sphere of radius `r̃_min(b̃ = 0) = 1 / Ẽ` for a
repulsive Coulomb potential at the current energy, labeled *"no
orbit enters"*. As the energy slider moves it shrinks or grows,
and the tracked particle's turning-point marker always sits on or
outside it. This is the geometric statement of the reach limit that
Section 8.6 later draws on the recovered-potential panel; seeing it
in the scene first is what makes the hatched interior of the
inversion plot mean something.

For an attractive potential there is no such sphere (`r̃_min → 0`),
and the drawable is replaced by a marker at `r̃_min(b̃_min)` with
the label *"smallest impact parameter thrown"*.

---

## 11.5 Palettes and the redundancy rule

A palette maps *roles* to *encodings* — hue, line style, weight,
opacity, glyph. Drawables name roles; the palette resolves them;
the renderer draws. Three ship: `light`, `dark`, `colorblind`. The
rule inherited from the rigid-body tool and P8:

> No distinction that carries meaning may rest on color alone where
> a label or line style can also carry it.

The distinctions this scene carries, and their redundant channels:

| Distinction | Hue | Second channel | Third |
| --- | --- | --- | --- |
| Annulus `i` vs `j` | hue `i` | index label `bᵢ` | ring order |
| Ring and its cone | same hue | same index label | particles |
| Integrated vs free flight | same | solid vs dashed | `phase` label |
| Repulsive vs attractive | — | near vs far side of axis | label |
| Measured vs unmeasured bins | fill vs hatch | bars vs none | label |
| Statistical vs tail band | hue | fill vs stipple | legend |
| Recovered vs true `V(r)` | hue | solid vs dotted | legend |
| Tracked particle | accent hue | larger glyph | label |

The `colorblind` palette uses a seven-hue set safe for the common
deficiencies and relies on the second channels for the rest. It is
a test, not a policy, that every row above has a non-color channel.

---

## 11.6 Labeled distortions (P14)

Three things are drawn away from their physical size, each labeled
in the scene:

- **Particle glyphs** have a display radius; particles are points.
  The legend states the glyph size in natural units.
- **The detector sphere** is at `R̃_detect`, which is a real setting,
  but is drawn at reduced opacity so the orbits behind it are
  visible; the label gives its radius.
- **The velocity arrow** of the tracked particle is drawn at a
  fixed display length as a direction, with its magnitude on the
  telemetry panel, exactly as the rigid-body tool draws `ω` and
  `L`. Its label says *"direction only"*.

Nothing else is scaled. The traces, the rings, the cones, the
probe-depth sphere, and the asymptotes are at true scene scale.

---

## 11.7 The scene description as data

`scene_description.py` produces, per frame, a plain list of
drawables:

```
  Drawable
    quantity     name, and the design section
    geometry     points, lines, a mesh, or text — in scene coords
    role         a palette key
    label        text, and where to anchor it
    panel        "scene" or a 2D panel name
    static       True if unchanged between frames (traces, rings,
                 spheres); the renderer caches these
```

Static drawables are built once per results store and per energy
index; only the particle glyphs, the tracked-particle markers, and
the telemetry change per frame. This split is what keeps the frame
loop cheap (Section 12) and is the thing the rendering-budget
spike must measure: how many static traces and how many moving
glyphs a software-rendered node sustains at an interactive rate.

The batch tier builds no scene description. `geometry/` writes the
rings, cones, and probe-depth spheres to HDF5 as geometry (Section
13), and ParaView draws them.

---

## 11.8 Invariants and tests

- Every drawable has a non-empty `quantity`, `label`, and `role`;
  the scene builder refuses one without.
- Every role in every drawable exists in every palette.
- Every row of the redundancy table has a non-color channel in the
  `colorblind` palette (a structural test over the palette data).
- The cone drawn for an annulus spans exactly `[θ(b̃ + db̃), θ(b̃)]`
  from the deflection table; a particle from that annulus lands
  inside it (the free-flight line meets the sphere within the band)
  for `mode = "asymptotic"` up to the `b̃ / R̃_detect` offset of 7.2.
- The probe-depth sphere radius equals `1 / Ẽ` at each energy index.
- The scene builder imports nothing from `render/vedo_renderer.py`
  and `geometry/` imports nothing from `render/` (A8.6(1)).
- An offscreen render of the reference run at a fixed frame is
  captured and its pixel content verified non-empty, as the
  rigid-body tool's spike learned to do: a VTK window with no
  OpenGL context accepts `Render()` and draws nothing.

---

## 11.9 Alternatives considered

**Draw the cone at the exit point `R̃_max` rather than on the
detector sphere.** Rejected: the cone is a detector concept, and
drawing it where the particles land is what makes the annulus-to-
cone map a picture of the measurement.

**Color particles by scattering angle continuously.** Attractive,
but it breaks the ring-cone link: a ring is one hue because it is
one `b̃`. Offered as an alternative role mapping in a later palette,
not in the first version.

**Two 3D panels (body/space) as the rigid-body tool has.** There is
one frame in the first version (A6.7), so one 3D panel. When recoil
arrives (FD1), a lab-frame panel is the natural addition and the
scene description's `panel` field already admits it.

**Draw every particle's orbit plane.** Rejected: `N` translucent
planes are visual noise and hide the rings; one plane, for the
tracked particle, is the lesson.
