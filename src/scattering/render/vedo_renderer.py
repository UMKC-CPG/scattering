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

_LINE_STYLE_PATTERNS = {'solid': None, 'dashed': 0x00FF, 'dotted': 0x1111,
                        'dash_dot': 0x1C47}

# Where the three text blocks sit (design 11.2, 11.11, 12.15), as
# normalized window coordinates; the sliders take the bottom strip and
# the right margin (design 12.4, 12.5).
_TELEMETRY_POSITION = 'top-right'
_RING_LEGEND_ORIGIN = (0.01, 0.98)          # first line; then downwards
_RING_LEGEND_STEP = 0.028
_KEY_LEGEND_POSITION = 'bottom-left'


class VedoRenderer:
    """See the module docstring and pseudocode 11.6. One 3D viewport;
    the 2D panels are matplotlib windows (render/panel_windows.py)."""

    def __init__(self, palette_name, size=(1280, 960), offscreen=False):
        self.palette_name = palette_name
        self.offscreen = bool(offscreen)
        self.plotter = vedo.Plotter(size=tuple(size), offscreen=offscreen,
                                    axes=0, bg=BACKGROUNDS[palette_name])
        self.static_actors = {}
        self.static_key = None
        self.frame_actors = []
        self.text_actors = []
        self.legend_visible = True
        self.legend_lines = []
        self.graticule_lines = 12
        # Design 12.14: the camera is applied only when this changes.
        self.camera_applied = None
        self.camera_set_count = 0
        # Design 12.4-12.5: the two slider widgets, built on the first
        # on-screen show; their callbacks hand commands to this sink.
        self.sliders = None
        self.command_sink = None
        self._shown = False

    @property
    def palette(self):
        return PALETTES[self.palette_name]

    def set_palette(self, palette_name):
        self.palette_name = palette_name
        self.plotter.background(BACKGROUNDS[palette_name])
        self._invalidate_static()

    def set_graticule(self, n_lines):
        """Rebuild the detector sphere with `n_lines` lines of latitude
        (design 11.12) at the next frame."""
        if n_lines != self.graticule_lines:
            self.graticule_lines = int(n_lines)
            self._invalidate_static()

    def _invalidate_static(self):
        """Make the next render rebuild the static actors. The OLD
        actors stay listed here until render() removes them from the
        view: clearing the list first (as this once did) left every old
        copy on screen, so each rebuild stacked another translucent
        orbit plane, cap, and graticule on top of the last."""
        self.static_key = None

    def render(self, scene, camera, static_key, resolved=None, state=None,
               ring_lines=()):
        """Draw one frame. Static actors are rebuilt only when
        `static_key` changes (pseudocode 11.6)."""
        view = self.plotter.at(0)
        if static_key != self.static_key:
            for actors in self.static_actors.values():
                view.remove(*actors)
            self.static_actors = {static_key: [
                actor for drawable in scene.static
                for actor in self._actors_for(drawable)]}
            view.add(*self.static_actors[static_key])
            self.static_key = static_key
        if self.frame_actors:
            view.remove(*self.frame_actors)
        self.frame_actors = [actor for drawable in scene.dynamic
                             for actor in self._actors_for(drawable)]
        view.add(*self.frame_actors)
        self._draw_text(scene.telemetry.lines(), ring_lines)
        if camera != self.camera_applied:
            self._set_camera(view, camera, resolved)
        if not self._shown:
            self.plotter.show(interactive=False, resetcam=False)
            self._shown = True
        if state is not None and not self.offscreen:
            if self.sliders is None:
                self._build_sliders(state)
            self._sync_sliders(state)
        self.plotter.render()

    def screenshot(self, path=None, as_array=False):
        return self.plotter.screenshot(path, asarray=as_array)

    def close(self):
        self.plotter.close()

    def set_legend(self, lines):
        """The key legend's text (design 12.15), drawn each frame while
        `legend_visible`."""
        self.legend_lines = list(lines)

    # --- The camera (design 12.14) ----------------------------------

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
        self.camera_applied = dict(camera)
        self.camera_set_count += 1
        self._r_detect = r_detect

    def read_camera(self):
        """The live camera as the run file's three numbers, so that a
        view found with the mouse can be saved (design 12.14)."""
        cam = self.plotter.at(0).camera
        r_detect = getattr(self, '_r_detect', 1.0)
        offset = np.array(cam.GetPosition()) - np.array(cam.GetFocalPoint())
        distance = float(np.linalg.norm(offset))
        if distance == 0.0:
            return dict(self.camera_applied or {})
        return {'azimuth_deg': float(np.degrees(np.arctan2(offset[1],
                                                           offset[0]))),
                'elevation_deg': float(np.degrees(np.arcsin(
                    np.clip(offset[2] / distance, -1.0, 1.0)))),
                'distance': distance / r_detect}

    # --- Text (design 11.2, 11.11, 12.15) ---------------------------

    def _draw_text(self, telemetry_lines, ring_lines):
        view = self.plotter.at(0)
        if self.text_actors:
            view.remove(*self.text_actors)
        colour = self.palette['text'].color
        actors = [vedo.Text2D('\n'.join(telemetry_lines),
                              pos=_TELEMETRY_POSITION, s=0.6, font='Calco',
                              c=colour)]
        # One actor per ring line, so that each is in its ring's hue.
        x0, y0 = _RING_LEGEND_ORIGIN
        for j, line in enumerate(ring_lines):
            hue = self.palette[f'annulus_{j % 8}'].color
            actors.append(vedo.Text2D(line, pos=(x0, y0 - j
                                                 * _RING_LEGEND_STEP),
                                      s=0.6, font='Calco', c=hue))
        if self.legend_visible and self.legend_lines:
            actors.append(vedo.Text2D('\n'.join(self.legend_lines),
                                      pos=_KEY_LEGEND_POSITION, s=0.5,
                                      font='Calco', c=colour))
        view.add(*actors)
        self.text_actors = actors

    # --- Sliders (design 12.4, 12.5) --------------------------------

    def _build_sliders(self, state):
        n_samples = getattr(state, 'n_samples', None)
        n_energies = getattr(state, 'n_energies', None)
        if n_samples is None or n_energies is None or \
                self.command_sink is None:
            self.sliders = {}
            return
        colour = self.palette['text'].color

        def on_time(widget, event):
            value = widget.GetRepresentation().GetValue()
            self.command_sink(('seek', int(round(value))))

        def on_energy(widget, event):
            value = widget.GetRepresentation().GetValue()
            self.command_sink(('set_energy', int(round(value))))

        self.sliders = {
            'time': self.plotter.add_slider(on_time, 0, n_samples - 1,
                value=state.frame_index, pos=5, title='frame', c=colour,
                title_size=0.7),
        }
        if n_energies > 1:
            self.sliders['energy'] = self.plotter.add_slider(on_energy, 0,
                n_energies - 1, value=state.energy_index, pos=15,
                title='energy', c=colour, title_size=0.7)

    def _sync_sliders(self, state):
        """Move the knobs to the state without firing the callbacks."""
        if not self.sliders:
            return
        self.sliders['time'].GetRepresentation().SetValue(state.frame_index)
        if 'energy' in self.sliders:
            self.sliders['energy'].GetRepresentation().SetValue(
                state.energy_index)

    # --- Actors -----------------------------------------------------

    def _actors_for(self, drawable):
        geometry = drawable.geometry
        if geometry is None:
            return []
        if isinstance(drawable.role, list):
            # Per-point roles: color each glyph by its own role. The spheres are
            # merged into one mesh, so colors are given per sphere at
            # construction rather than per vertex afterwards.
            if len(geometry.positions) == 0:
                return []
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
        elif isinstance(geometry, Sphere) and drawable.role == 'detector':
            # The detector sphere is a graticule, not a surface (design
            # 11.12): n lines of latitude (constant scattering angle)
            # and 2n of longitude.
            for points in _graticule(geometry, self.graticule_lines):
                actors.append(vedo.Line(points, lw=1).c(color).alpha(
                    max(encoding.opacity, 0.5)))
        elif isinstance(geometry, Sphere):
            # Any other sphere (the probe-depth sphere of design 11.4)
            # is a translucent surface.
            actor = vedo.Sphere(pos=geometry.center, r=geometry.radius,
                                res=24).c(color).alpha(encoding.opacity)
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
        if drawable.label and actors:
            # Every labeled quantity carries its label on screen (design
            # 11.2, pseudocode 11.6): rings and spheres at their rim, the
            # tracked particle's markers beside the mark itself.
            anchor, size = _label_placement(geometry)
            if anchor is not None:
                actors.append(vedo.Text3D(drawable.label, pos=anchor,
                                          s=size).c(color))
        return actors


def _graticule(sphere, n_latitude, n_points=90):
    """The polylines of a sphere's graticule (design 11.12): latitude
    circles at polar angles k * pi / n_latitude, k = 1 .. n_latitude-1,
    and 2 * n_latitude meridian semicircles."""
    c, r = sphere.center, sphere.radius
    lines = []
    azimuths = np.linspace(0.0, 2.0 * np.pi, n_points)
    for k in range(1, n_latitude):
        theta = k * np.pi / n_latitude
        lines.append(c + r * np.stack([np.sin(theta) * np.cos(azimuths),
                                       np.sin(theta) * np.sin(azimuths),
                                       np.full_like(azimuths,
                                                    np.cos(theta))], axis=1))
    polar = np.linspace(0.0, np.pi, n_points // 2)
    for m in range(2 * n_latitude):
        phi = m * np.pi / n_latitude
        lines.append(c + r * np.stack([np.sin(polar) * np.cos(phi),
                                       np.sin(polar) * np.sin(phi),
                                       np.cos(polar)], axis=1))
    return lines


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


def _label_placement(geometry):
    """Where a drawable's label sits and how big it is, per geometry:
    (anchor, text size) or (None, None) for a geometry with no natural
    place for text."""
    if isinstance(geometry, Ring):
        return (geometry.center + np.array([geometry.outer, 0.0, 0.0]),
                0.025 * geometry.outer)
    if isinstance(geometry, Sphere):
        return (geometry.center + np.array([0.0, 0.0, geometry.radius]),
                0.025 * geometry.radius)
    if isinstance(geometry, Arc):
        # Just outside the arc's midpoint.
        points = _arc_points(geometry, count=3)
        outward = points[1] - geometry.center
        return (geometry.center + 1.15 * outward, 0.12 * geometry.radius)
    if isinstance(geometry, Segment):
        length = float(np.linalg.norm(geometry.end - geometry.start))
        return (0.5 * (geometry.start + geometry.end), 0.03 * length)
    if isinstance(geometry, Arrow):
        tip = geometry.start + geometry.direction * geometry.display_length
        return (tip, 0.12 * geometry.display_length)
    if isinstance(geometry, Points) and len(geometry.positions) == 1:
        return (geometry.positions[0] + 1.5 * geometry.radius,
                0.8 * geometry.radius)
    return (None, None)
