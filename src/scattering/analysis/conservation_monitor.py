"""Residuals of the conserved quantities along a stored orbit
(pseudocode 9.2, design 9.3).

Energy and angular momentum are conserved along every orbit in a central
potential. Their departure from the beam values, measured from the STORED
samples so that what the panel shows is what the scrubber shows, is the
integrator's error made visible (VISION P2). A scattering pass reports the
maximum rather than a rate: the error is concentrated at pericenter, and a rate
averaged over the long quiet approach would understate it (design 9.3).

Attribution: this module is part of the scattering teaching tool.
"""

import numpy as np

from scattering.core.natural_units import angular_momentum, total_energy


def residual_series(store, resolved, energy_index, particle_index):
    """(time, energy_residual, angmom_residual) on the integrated
    phase of one particle, eq. (9.1). The angular-momentum residual is relative,
    except for the head-on orbit whose L is zero, where
    it is absolute."""
    k, i = energy_index, particle_index
    times, positions, velocities, polar, phase = store.particle(k, i)
    keep = phase == 0
    radius = polar[keep, 0]
    speed = np.linalg.norm(velocities[keep], axis=1)
    energy = float(store.energies[k])
    total = total_energy(speed, resolved.potential.value(radius))
    energy_residual = (total - energy) / energy
    angmom = np.linalg.norm(np.cross(positions[keep], velocities[keep]),
                            axis=1)
    expected = angular_momentum(energy, float(store.impact_parameter[i]))
    if expected > 0.0:
        angmom_residual = (angmom - expected) / expected
    else:
        angmom_residual = angmom
    return times[keep], energy_residual, angmom_residual


def residual_maxima(store, energy_index):
    """The per-energy maxima the telemetry and the budget show."""
    energy_drift, angmom_drift, exterior = store.drift(energy_index)
    return (float(energy_drift.max()), float(angmom_drift.max()),
            float(exterior.max()))
