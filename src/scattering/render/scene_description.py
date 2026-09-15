"""The scene description: a renderer-agnostic list of what to draw
(pseudocode 11.2, 11.4; design 11.2, 11.7).

Every drawable is a named physical quantity with a geometry, a role, a label,
and the design section that defines it (VISION P7); nothing decorative goes in.
Static drawables -- traces, rings, cones, spheres -- are built once per energy
and view and cached by the session; only `build_frame` runs per tick, and it is
array slicing and glyph placement, never physics.

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from scattering.core.natural_units import (angular_momentum,
                                           asymptotic_speed, kinetic_energy)
from scattering.core.units import format_natural
from scattering.analysis.conservation_monitor import residual_maxima
from scattering.geometry import (Points, Polyline, annulus_ring, beam_axis,
    bin_bands, cone_band, detector_sphere, entry_plane, orbit_plane,
    probe_depth, tracked_markers, unmeasured_caps)


@dataclass(frozen=True)
class Drawable:
    quantity: str
    section: str
    geometry: object
    role: object                 # a role name, or per-point roles
    label: Optional[str]
    panel: str
    static: bool


@dataclass(frozen=True)
class Telemetry:
    scene_time: float
    frame_index: int
    n_samples: int
    energy_index: int
    energy_label: str
    tracked_index: int
    tracked_impact: float
    tracked_azimuth_deg: float
    tracked_r: float
    tracked_phi_deg: float
    tracked_speed: float
    tracked_kinetic: float
    tracked_potential: float
    tracked_total_energy: float
    tracked_angular_momentum: float
    tracked_deflection_deg: float
    tracked_turning_point: float
    exterior_deflection_max: float
    energy_drift_max: float
    angmom_drift_max: float
    provider: str
    mirror_diff: float
    ratio_of_scene_to_wall_time: float = 0.0

    def lines(self):
        """The overlay text, one entry per line."""
        return [
            f't = {self.scene_time:.3f}   frame {self.frame_index} / '
            f'{self.n_samples - 1}   scene/wall = '
            f'{self.ratio_of_scene_to_wall_time:.2f}',
            f'energy [{self.energy_index}] = {self.energy_label}',
            f'tracked {self.tracked_index}: b = {self.tracked_impact:.3g}, '
            f'azimuth {self.tracked_azimuth_deg:.0f} deg',
            f'  r = {self.tracked_r:.3f}   phi = {self.tracked_phi_deg:.1f} '
            f'deg   |v| = {self.tracked_speed:.3f}',
            f'  E = {self.tracked_total_energy:.6f}  (T = '
            f'{self.tracked_kinetic:.4f}, V = {self.tracked_potential:.4f})',
            f'  L = {self.tracked_angular_momentum:.4f}   Theta = '
            f'{self.tracked_deflection_deg:+.2f} deg   r_min = '
            f'{self.tracked_turning_point:.3f}',
            f'orbits: {self.provider};  drift E {self.energy_drift_max:.1e}'
            f'  L {self.angmom_drift_max:.1e};  exterior deflection '
            f'{self.exterior_deflection_max:.1e} rad',
            f'mirror cross-section difference {self.mirror_diff:.1e}',
        ]


@dataclass(frozen=True)
class Scene:
    static: list
    dynamic: list
    telemetry: Telemetry


def role_for_particle(store, particle_index):
    ring = store.annulus_index[particle_index]
    return f'annulus_{ring % 8}' if ring >= 0 else 'disc'


def build_static(store, resolved, energy_index, tracked, glyph_radius,
                 detector=None):
    """The drawables that do not change between frames at one energy
    and one tracked particle (pseudocode 11.4), plus the detector's
    bin bands when a DetectorResult is given (pseudocode 7.7)."""
    k = energy_index
    spec = resolved.spec
    r_max = resolved.settings.r_max
    r_detect = resolved.detector_radius
    sign_label = resolved.potential.describe()
    table, xsec, mirror, maps = store.tables(k)
    out = [
        Drawable('beam axis', '4.3', beam_axis(r_detect), 'axis', 'z',
                 'scene', True),
        Drawable('entry plane', '4.6', entry_plane(r_max, 1.2 * max(
            spec.beam.largest_impact(), 0.1 * r_max)), 'plane', 't = 0',
            'scene', True),
        Drawable('detector sphere', '7.2', detector_sphere(r_detect),
                 'detector', f'R_detect = {r_detect:.3g}', 'scene', True),
    ]
    for cap in unmeasured_caps(store.theta_min[k], store.theta_head[k],
                               r_detect):
        out.append(Drawable('unmeasured', '7.3', cap, 'unmeasured',
                            'unmeasured', 'scene', True))
    if detector is not None:
        for band in bin_bands(detector.layout, r_detect):
            out.append(Drawable('detector bin', '7.4', band, 'detector',
                                None, 'scene', True))
    for j, (ring, ring_map) in enumerate(zip(spec.beam.annuli, maps)):
        role = f'annulus_{j % 8}'
        out.append(Drawable('annulus', '5.7', annulus_ring(ring, r_max),
                            role, f'b_{j} = {ring.impact:.3g}', 'scene',
                            True))
        side = ' (far side)' if resolved.potential.value(1.0) < 0 else ''
        out.append(Drawable('cone', '5.7', cone_band(ring_map, r_detect),
                            role, f'theta_{j}{side}', 'scene', True))
    geometry, label = probe_depth(resolved.potential, store.energies[k],
        spec.beam.smallest_impact(), 2 * glyph_radius)
    out.append(Drawable('probe depth', '2.3', geometry, 'probe', label,
                        'scene', True))
    for i in range(store.n_particles):
        times, positions, velocities, polar, phase = store.particle(k, i)
        trace = store.trace(k, i)
        if len(trace):
            out.append(Drawable('trace', '4.10', Polyline(trace),
                                role_for_particle(store, i), None, 'scene',
                                True))
        for leg in (-1, +1):
            points = positions[phase == leg]
            if len(points) >= 2:
                out.append(Drawable('free flight', '4.6', Polyline(points),
                                    'free_flight', None, 'scene', True))
    out.append(Drawable('orbit plane', '4.3',
                        orbit_plane(store.azimuth[tracked], 0.6 * r_max),
                        'orbit_plane', f'orbital plane of {tracked}',
                        'scene', True))
    out.append(Drawable('potential', '2', None, 'text', sign_label,
                        'scene', True))
    return out


def build_frame(store, resolved, energy_index, frame_index, tracked,
                glyph_radius, scales):
    """The per-frame drawables and the telemetry (pseudocode 11.4)."""
    k, n, i = energy_index, frame_index, tracked
    r_max = resolved.settings.r_max
    positions = store.frame(k, n)
    roles = [role_for_particle(store, j) for j in range(store.n_particles)]
    out = [Drawable('particles', '6.3', Points(positions, glyph_radius),
                    roles, None, 'scene', False)]
    for geometry, role, label in tracked_markers(store, k, i, n, r_max,
        resolved.detector_radius, glyph_radius, 0.1 * r_max):
        out.append(Drawable('tracked marker', '11.2', geometry, role, label,
                            'scene', False))
    out.append(Drawable('tracked particle', '12.6',
                        Points(positions[i][None, :], 1.6 * glyph_radius),
                        'tracked', f'particle {i}', 'scene', False))
    return out, telemetry_for(store, resolved, k, n, i, scales)


def telemetry_for(store, resolved, k, n, i, scales):
    energy = float(store.energies[k])
    velocity = store.frame_velocity(k, n)[i]
    speed = float(np.linalg.norm(velocity))
    radius, phi = store.frame_polar(k, n)[i]
    potential_value = float(resolved.potential.value(radius))
    kinetic = float(kinetic_energy(speed))
    position = store.frame(k, n)[i]
    angmom = float(np.linalg.norm(np.cross(position, velocity)))
    energy_max, angmom_max, exterior_max = residual_maxima(store, k)
    return Telemetry(
        scene_time=float(store.time_of(k, n)), frame_index=n,
        n_samples=store.n_samples, energy_index=k,
        energy_label=f'{energy:.4g} = '
                     f'{format_natural(energy, "energy", scales)}',
        tracked_index=i, tracked_impact=float(store.impact_parameter[i]),
        tracked_azimuth_deg=float(np.degrees(store.azimuth[i])),
        tracked_r=float(radius), tracked_phi_deg=float(np.degrees(phi)),
        tracked_speed=speed, tracked_kinetic=kinetic,
        tracked_potential=potential_value,
        tracked_total_energy=kinetic + potential_value,
        tracked_angular_momentum=angmom,
        tracked_deflection_deg=float(np.degrees(store.deflection[k, i])),
        tracked_turning_point=float(store.turning_point[k, i]),
        exterior_deflection_max=exterior_max,
        energy_drift_max=energy_max,
        angmom_drift_max=angmom_max,
        provider=store.provider[k], mirror_diff=float(store.mirror_diff[k]))
