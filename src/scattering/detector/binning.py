"""Assigning each particle to a bin (pseudocode 7.4, design 7.2).

Two ways to read a particle's angle. The asymptotic mode uses the direction of
its outgoing velocity at infinity -- the scattering angle as the cross section
defines it, exact. The position mode uses the polar angle of the point where the
outbound free-flight line meets the detector sphere, which is what a real
detector at finite distance measures; the outgoing asymptote is offset from the
center by the impact parameter, so the two differ by about asin(b / R_detect),
and a student can switch modes and watch the histogram shift at small angles,
then move the sphere out and watch it converge.

Attribution: this module is part of the scattering teaching tool.
"""

import numpy as np


def asymptotic_angles(directions):
    """Polar angle from +z of each unit direction."""
    return np.arccos(np.clip(np.asarray(directions)[:, 2], -1.0, 1.0))


def position_angles(store, energy_index, layout):
    """Landing-point angles on the sphere of `layout.radius`, from
    the first outbound sample and the asymptotic direction; None
    when the store holds no samples (batch mode)."""
    if store.n_samples == 0:
        return None
    k = energy_index
    count = store.n_particles
    angles = np.empty(count)
    directions = store.final_directions(k)
    for i in range(count):
        sample = min(int(store.exit_index[k, i]), store.n_samples - 1)
        point = store.position[k, i, sample]
        direction = directions[i]
        along = point @ direction
        travel = -along + np.sqrt(max(along ** 2 + layout.radius ** 2
                                      - point @ point, 0.0))
        landing = point + direction * travel
        angles[i] = np.arccos(np.clip(landing[2] / layout.radius, -1.0,
                                      1.0))
    return angles


def bin_particles(angles, layout):
    """Counts per bin and the number of particles outside the
    measured range. Both ends are inclusive so that the head-on
    particle at theta = pi is counted."""
    angles = np.asarray(angles)
    inside = (angles >= layout.edges[0]) & (angles <= layout.edges[-1])
    counts, _ = np.histogram(angles[inside], bins=layout.edges)
    return counts.astype(int), int(len(angles) - inside.sum())
