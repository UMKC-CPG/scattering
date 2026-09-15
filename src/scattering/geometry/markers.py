"""The tracked particle's markers (pseudocode 11.3, design 11.2): the
radius line and polar-angle arc that put (r, phi) on screen (VISION G3), the
velocity direction, the turning point, the two asymptotes, and the deflection
arc between them.

The asymptote segments are the free-flight legs the store holds:
from the entry sample back to the entry plane, and from the exit sample along
the asymptotic direction to the detector sphere. The pericenter direction, from
which phi is measured, is recovered from
the stored polar angle: at the sample where phi is nearest zero the
position points along it.

Attribution: this module is part of the scattering teaching tool.
"""

import numpy as np

from scattering.geometry.shapes import Arc, Arrow, Points, Segment


def _unit(vector):
    norm = np.linalg.norm(vector)
    return vector / norm if norm > 0 else vector


def tracked_markers(store, energy_index, particle_index, sample_index,
                    r_max, r_detect, glyph_radius, arrow_length):
    """Return a list of (geometry, role, label) for the tracked
    particle at one frame."""
    k, i, n = energy_index, particle_index, sample_index
    times, positions, velocities, polar, phase = store.particle(k, i)
    position = positions[n]
    velocity = velocities[n]
    radius = float(polar[n, 0])
    pericenter_sample = int(np.argmin(np.abs(polar[:, 1])))
    pericenter_direction = _unit(positions[pericenter_sample])
    plane_normal = _unit(np.cross(pericenter_direction,
                                  np.array([0.0, 0.0, 1.0])))
    if np.linalg.norm(plane_normal) == 0.0:          # head-on: radial
        plane_normal = np.array([0.0, 1.0, 0.0])

    markers = [
        (Segment(np.zeros(3), position), 'radius', 'r'),
        (Arc(np.zeros(3), 0.25 * r_max, pericenter_direction,
             _unit(position), plane_normal), 'polar', 'phi'),
        (Arrow(position, _unit(velocity), arrow_length), 'velocity',
         'v (direction only)'),
        (Points(positions[pericenter_sample][None, :], 1.4 * glyph_radius),
         'turning', 'r_min'),
    ]

    inbound = np.nonzero(phase == -1)[0]
    on_orbit = np.nonzero(phase == 0)[0]
    outbound = np.nonzero(phase == 1)[0]
    if on_orbit.size:
        entry = positions[on_orbit[0]]
        direction_in = np.array([0.0, 0.0, 1.0])
        plane_point = entry - direction_in * (entry[2] + r_max)
        markers.append((Segment(plane_point, entry), 'asymptote',
                        'incoming asymptote'))
        exit_point = positions[on_orbit[-1]]
        out_direction = store.out_direction[k, i]
        along = exit_point @ out_direction
        travel = -along + np.sqrt(along ** 2 + r_detect ** 2
                                  - exit_point @ exit_point)
        markers.append((Segment(exit_point, exit_point
                                + out_direction * travel),
                        'asymptote', 'outgoing asymptote'))
        markers.append((Arc(np.zeros(3), 0.35 * r_max, direction_in,
                            out_direction,
                            _unit(np.cross(direction_in, out_direction))
                            if abs(out_direction[2]) < 1 - 1e-12
                            else plane_normal),
                        'deflection', 'Theta'))
    return markers
