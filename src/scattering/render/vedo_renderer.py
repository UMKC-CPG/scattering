"""Realize a scene description as pixels with vedo / VTK (pseudocode
11.6, design 11.1). This is the ONLY module that imports vedo or VTK
(ARCHITECTURE 6.5); a different backend would be a new module here and nothing
above it would change.

Offscreen rendering: VTK fixes its window class when it is imported,
and a window without a valid OpenGL context accepts Render() and
draws nothing -- the rigid-body spike's trap. `render/offscreen.py`
holds the portable rule for choosing the class (EGL on Linux when
offscreen drawing is asked for; nothing on macOS or Windows); tests
read the framebuffer back and skip if it is empty.

Attribution: this module is part of the scattering teaching tool.
"""

from scattering.render.offscreen import (no_display_available,
                                         prepare_offscreen)

# The import-time fallback of pseudocode 11.6: on Linux with no display
# named at all, no window could open, so draw offscreen. Callers that
# WANT offscreen drawing call prepare_offscreen() themselves before
# importing this module, which also covers a DISPLAY that is set but
# dead.
if no_display_available():
    prepare_offscreen()

import numpy as np                                # noqa: E402
import vedo                                       # noqa: E402

from scattering.geometry import (Arc, Arrow, Plane, Points, Polyline,   # noqa
                                 Ring, Segment, Sphere, SphereBand, Text)
from scattering.render.palettes import BACKGROUNDS, PALETTES   # noqa: E402
from scattering.render.panels import build_panel, render_panel  # noqa

_LINE_STYLE_PATTERNS = {'solid': None, 'dashed': 0x00FF, 'dotted': 0x1111,
                        'dash_dot': 0x1C47}


def _layout(n_panels):
    """The scene takes 70 % of the width; panels stack on the right."""
    shape = [dict(bottomleft=(0.0, 0.0), topright=(0.7, 1.0))]
    if n_panels:
        height = 1.0 / n_panels
        for index in range(n_panels):
            shape.append(dict(bottomleft=(0.7, 1.0 - (index + 1) * height),
                              topright=(1.0, 1.0 - index * height)))
    return shape


class VedoRenderer:
    """See the module docstring and pseudocode 11.6."""

    def __init__(self, palette_name, size=(1280, 960), offscreen=False,
                 panels=()):
        self.palette_name = palette_name
        self.panels = [p for p in panels if p != 'telemetry']
        self.plotter = vedo.Plotter(shape=_layout(len(self.panels)),
            size=tuple(size), offscreen=offscreen, sharecam=False, axes=0,
            bg=BACKGROUNDS[palette_name])
        self.static_actors = {}
        self.static_key = None
        self.frame_actors = []
        self.panel_actors = []
        self.panel_key = None
        self.overlay = None
        self.legend = None
        self._shown = False

    @property
    def palette(self):
        return PALETTES[self.palette_name]

    def set_palette(self, palette_name):
        self.palette_name = palette_name
        self.plotter.background(BACKGROUNDS[palette_name])
        self.static_actors.clear()
        self.static_key = None
        self.panel_key = None

    def render(self, scene, camera, static_key, store=None, resolved=None,
               tracked=0, show_mirror=False, detector=None, budget=None):
        """Draw one frame. Static actors are rebuilt only when
        `static_key` changes; panels likewise (pseudocode 11.6)."""
        scene_view = self.plotter.at(0)
        if static_key != self.static_key:
            for actors in self.static_actors.values():
                scene_view.remove(*actors)
            self.static_actors = {static_key: [
                actor for drawable in scene.static
                for actor in self._actors_for(drawable)]}
            scene_view.add(*self.static_actors[static_key])
            self.static_key = static_key
            if self.legend is not None:
                scene_view.remove(self.legend)
            self.legend = vedo.Text2D(self._legend_text(scene.static),
                pos='bottom-left', s=0.55, c=self.palette['text'].color)
            scene_view.add(self.legend)
        if self.frame_actors:
            scene_view.remove(*self.frame_actors)
        self.frame_actors = [actor for drawable in scene.dynamic
                             for actor in self._actors_for(drawable)]
        scene_view.add(*self.frame_actors)
        if self.overlay is not None:
            scene_view.remove(self.overlay)
        self.overlay = vedo.Text2D('\n'.join(scene.telemetry.lines()),
            pos='top-left', s=0.6, font='Calco', c=self.palette['text'].color)
        scene_view.add(self.overlay)
        self._set_camera(scene_view, camera, resolved)
        if store is not None and self.panels:
            key = (static_key, tracked, show_mirror)
            if key != self.panel_key:
                self._draw_panels(store, resolved, static_key[0], tracked,
                                  show_mirror, detector, budget)
                self.panel_key = key
        if not self._shown:
            self.plotter.show(interactive=False, resetcam=False)
            self._shown = True
        self.plotter.render()

    def screenshot(self, path=None, as_array=False):
        return self.plotter.screenshot(path, asarray=as_array)

    def close(self):
        self.plotter.close()

    def show_legend(self, lines):
        """The key-binding legend, as an overlay for a few frames."""
        text = vedo.Text2D('\n'.join(lines), pos='top-right', s=0.6,
                           c=self.palette['text'].color)
        self.plotter.at(0).add(text)
        return text

    # --- Internals ------------------------------------------------

    def _set_camera(self, view, camera, resolved):
        r_detect = resolved.detector_radius if resolved else 1.0
        azimuth = np.radians(camera['azimuth_deg'])
        elevation = np.radians(camera['elevation_deg'])
        distance = camera['distance'] * r_detect
        position = distance * np.array([np.cos(elevation) * np.cos(azimuth),
                                        np.cos(elevation) * np.sin(azimuth),
                                        np.sin(elevation)])
        cam = view.camera
        cam.SetPosition(*position)
        cam.SetFocalPoint(0.0, 0.0, 0.0)
        cam.SetViewUp(0.0, 0.0, 1.0)
        view.renderer.ResetCameraClippingRange()

    def _draw_panels(self, store, resolved, k, tracked, show_mirror,
                     detector=None, budget=None):
        for actor in self.panel_actors:
            self.plotter.remove(actor)
        self.panel_actors = []
        background = BACKGROUNDS[self.palette_name]
        for index, name in enumerate(self.panels, start=1):
            data = build_panel(name, store, resolved, k, tracked,
                               show_mirror, detector, budget)
            if data is None:
                continue
            image = render_panel(data, self.palette, background)
            actor = vedo.Image(image)
            self.plotter.at(index).add(actor)
            self.plotter.at(index).reset_camera()
            self.panel_actors.append(actor)

    def _legend_text(self, static):
        seen = []
        for drawable in static:
            entry = f'{drawable.quantity} (design {drawable.section})'
            if entry not in seen:
                seen.append(entry)
        return 'drawables:\n' + '\n'.join(seen[:14])

    def _actors_for(self, drawable):
        geometry = drawable.geometry
        if geometry is None:
            return []
        if isinstance(drawable.role, list):
            # Per-point roles: color each glyph by its own role. The spheres are
            # merged into one mesh, so colors are given per sphere at
            # construction rather than per vertex afterwards.
            colors = [self.palette[r].color for r in drawable.role]
            actor = vedo.Spheres(geometry.positions, r=geometry.radius,
                                 res=8, c=colors)
            return [actor]
        encoding = self.palette[drawable.role]
        color = encoding.color
        actors = []
        if isinstance(geometry, Points):
            actor = vedo.Spheres(geometry.positions, r=geometry.radius,
                                 res=8).c(color).alpha(encoding.opacity)
            actors.append(actor)
        elif isinstance(geometry, Polyline):
            if len(geometry.points) >= 2:
                actor = vedo.Line(geometry.points, closed=geometry.closed,
                                  lw=encoding.weight).c(color)
                actor.alpha(encoding.opacity)
                _apply_line_style(actor, encoding.line_style)
                actors.append(actor)
        elif isinstance(geometry, Segment):
            actor = vedo.Line([geometry.start, geometry.end],
                              lw=encoding.weight).c(color)
            _apply_line_style(actor, encoding.line_style)
            actors.append(actor.alpha(encoding.opacity))
        elif isinstance(geometry, Ring):
            actor = vedo.Disc(pos=geometry.center, r1=geometry.inner,
                              r2=geometry.outer, res=(1, 72)).c(color)
            actors.append(actor.alpha(max(encoding.opacity * 0.5, 0.25)))
        elif isinstance(geometry, SphereBand):
            actors.append(_sphere_band_mesh(geometry).c(color).alpha(
                max(encoding.opacity * 0.6, 0.3)))
        elif isinstance(geometry, Sphere):
            actor = vedo.Sphere(pos=geometry.center, r=geometry.radius,
                                res=36).c(color).alpha(encoding.opacity)
            actor.wireframe(False)
            actors.append(actor)
        elif isinstance(geometry, Plane):
            side = 2.0 * geometry.half_extent
            actor = vedo.Plane(pos=geometry.center, normal=geometry.normal,
                               s=(side, side)).c(color)
            actors.append(actor.alpha(encoding.opacity))
        elif isinstance(geometry, Arrow):
            end = geometry.start + geometry.direction * geometry.display_length
            actor = vedo.Arrow(geometry.start, end,
                               s=0.02 * geometry.display_length).c(color)
            actors.append(actor)
        elif isinstance(geometry, Arc):
            actor = vedo.Line(_arc_points(geometry), lw=encoding.weight)
            actors.append(actor.c(color))
        elif isinstance(geometry, Text):
            actors.append(vedo.Text3D(geometry.text, pos=geometry.anchor,
                                      s=0.03).c(color))
        if drawable.label and drawable.static and actors and \
                isinstance(geometry, (Ring, Sphere)):
            anchor = _label_anchor(geometry)
            actors.append(vedo.Text3D(drawable.label, pos=anchor,
                                      s=0.025 * _extent(geometry)).c(color))
        return actors


def _apply_line_style(actor, line_style):
    pattern = _LINE_STYLE_PATTERNS.get(line_style)
    if pattern is not None:
        actor.properties.SetLineStipplePattern(pattern)
        actor.properties.SetLineStippleRepeatFactor(1)


def _sphere_band_mesh(band, n_theta=24, n_phi=72):
    thetas = np.linspace(band.theta_1, band.theta_2, n_theta)
    phis = np.linspace(band.azimuth_range[0], band.azimuth_range[1], n_phi)
    theta_grid, phi_grid = np.meshgrid(thetas, phis, indexing='ij')
    vertices = np.stack([np.sin(theta_grid) * np.cos(phi_grid),
                         np.sin(theta_grid) * np.sin(phi_grid),
                         np.cos(theta_grid)], axis=-1).reshape(-1, 3)
    vertices = band.center + band.radius * vertices
    faces = []
    for a in range(n_theta - 1):
        for b in range(n_phi - 1):
            index = a * n_phi + b
            faces.append([index, index + 1, index + n_phi + 1,
                          index + n_phi])
    return vedo.Mesh([vertices, faces])


def _arc_points(arc, count=48):
    start = arc.start_dir / np.linalg.norm(arc.start_dir)
    end = arc.end_dir / np.linalg.norm(arc.end_dir)
    normal = arc.plane_normal / max(np.linalg.norm(arc.plane_normal), 1e-12)
    angle = np.arccos(np.clip(start @ end, -1.0, 1.0))
    if np.cross(start, end) @ normal < 0:
        angle = -angle
    perpendicular = np.cross(normal, start)
    fractions = np.linspace(0.0, 1.0, count)
    points = [arc.center + arc.radius * (np.cos(f * angle) * start
                                         + np.sin(f * angle) * perpendicular)
              for f in fractions]
    return np.array(points)


def _label_anchor(geometry):
    if isinstance(geometry, Ring):
        return geometry.center + np.array([geometry.outer, 0.0, 0.0])
    return geometry.center + np.array([0.0, 0.0, geometry.radius])


def _extent(geometry):
    return geometry.outer if isinstance(geometry, Ring) else geometry.radius
