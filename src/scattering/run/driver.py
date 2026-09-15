"""The driver: the forward chain, in order, from a run specification
to a frozen results store (pseudocode 6.4-6.5, ARCHITECTURE 2 and 4.10).

This is the one module that knows the sequence of stages:

- potential, scales, beam;
- per energy: deflection tables, per-particle outputs, orbits,
  samples, traces;
- freeze.

The deflection stage runs BEFORE the orbits at each energy, because it is cheap
and because it fixes the asymptotic out-direction each orbit's outbound free
flight must follow (design 4.6-4.7). Nothing here computes physics; it calls the
stages and lays the results out.

Attribution: this module is part of the scattering teaching tool.
"""

import datetime
import sys

import numpy as np

from scattering.beam import generate_beam, particle_energy
from scattering.core.natural_units import asymptotic_speed
from scattering.deflection import (annulus_map, build_cross_section_table,
    build_deflection_table, mirror_check, particle_outputs)
from scattering.orbits import choose_provider, embed
from scattering.run.results_store import ResultsStore
from scattering.run.run_spec import git_commit


def build_results_store(resolved, progress=None):
    """Run the forward chain from a ResolvedRun (pseudocode 10.1) and
    return a frozen ResultsStore.

    Resolution -- the potential, the reference scales, the unit conversion, the
    orbit settings, and the memory budget -- happened in `run_spec.resolve`
    (pseudocode 10.7); this function starts at the beam. `progress(energy_index,
    particle_index)` is called after each orbit, for a progress bar. The order
    of stages is the whole content of this function; see the module docstring.
    """
    spec = resolved.spec
    potential = resolved.potential
    beam_spec = spec.beam
    settings = resolved.settings
    beam = generate_beam(beam_spec, potential)
    provider = choose_provider(potential, settings)
    r_detect = resolved.detector_radius

    n_energies, n_particles = beam.n_energies, beam.n_particles
    n_samples = spec.fidelity.n_samples
    store = ResultsStore.allocate(n_energies, n_particles, n_samples)
    store.impact_parameter[:] = beam.impact_parameter
    store.azimuth[:] = beam.azimuth
    store.annulus_index[:] = beam.annulus_index
    store.energies[:] = beam.energies

    theta_min = np.empty(n_energies)
    theta_head = np.empty(n_energies)
    for k in range(n_energies):
        energy = beam.energies[k]
        # --- Deflection stage (pseudocode 5), first. The table spans
        #   the DECLARED beam extents, not the sampled ones: the
        #   measured range of design 7.3 is what the beam could
        #   produce, so that a bin the finite sample happened to miss
        #   shows as empty rather than as unmeasured.
        if beam_spec.layout == 'disc':
            b_low, b_high = float(beam_spec.b_min), float(beam_spec.b_max)
        else:
            b_low = float(beam.impact_parameter.min())
            b_high = float(beam.impact_parameter.max())
        table = build_deflection_table(potential, energy, b_low, b_high,
            spec.fidelity.n_deflection_points, potential.admits_center())
        xsec = build_cross_section_table(table)
        mirror, mirror_diff = mirror_check(potential, energy, table,
            spec.fidelity.n_deflection_points, potential.admits_center())
        outputs = particle_outputs(potential, energy, beam)
        store.deflection[k] = outputs['deflection']
        store.out_direction[k] = outputs['out_direction']
        store.turning_point_q[k] = outputs['turning_point_q']
        theta_min[k], theta_head[k] = xsec.theta_min, xsec.theta_head
        store.theta_min[k], store.theta_head[k] = theta_min[k], theta_head[k]
        store.deflection_table[k] = table
        store.xsec_table[k] = xsec
        store.mirror_table[k] = mirror
        store.mirror_diff[k] = mirror_diff
        store.annulus_map[k] = [annulus_map(potential, energy, ring, xsec)
                                for ring in beam_spec.annuli]
        store.provider[k] = provider.name
        store.provider_check[k] = table.check

        # --- Orbits (pseudocode 4).
        orbits = []
        for i in range(n_particles):
            particle_e = particle_energy(beam_spec, k, i)
            orbits.append(provider.provide(potential, particle_e,
                                           beam.impact_parameter[i],
                                           settings))
            if progress is not None:
                progress(k, i)
        for i, orbit in enumerate(orbits):
            store.turning_point[k, i] = orbit.turning_point
            store.time_offset[k, i] = orbit.time_offset
            store.energy_drift[k, i] = orbit.energy_drift
            store.angmom_drift[k, i] = orbit.angmom_drift
            exit_velocity = embed(orbit.exit_state[2], orbit.exit_state[3],
                                  beam.azimuth[i])
            store.finite_radius[k, i] = _angle_between(
                exit_velocity, store.out_direction[k, i])

        # --- Samples on the scene-time grid (pseudocode 6.5).
        if n_samples > 0:
            t_end = max(_detector_arrival(orbit, store.deflection[k, i],
                                          r_detect) - orbit.time_offset
                        for i, orbit in enumerate(orbits))
            store.time_grid[k] = np.linspace(0.0, t_end, n_samples)
            for i, orbit in enumerate(orbits):
                fill_samples(store, k, i, orbit, store.deflection[k, i],
                             beam.azimuth[i])
            if spec.fidelity.trace_points_max > 0:
                store.trace_points[k] = [
                    _embed_trace(orbit.trace(), beam.azimuth[i])
                    for i, orbit in enumerate(orbits)]

    store.run_spec = spec
    store.beam = beam.with_angles(theta_min, theta_head)
    store.created = datetime.datetime.now().isoformat(timespec='seconds')
    store.versions = _versions()
    store.git_commit = git_commit()
    store.freeze()
    return store


def fill_samples(store, energy_index, particle_index, orbit, deflection,
                 azimuth):
    """One particle's samples on the scene-time grid (pseudocode 6.5):
    inbound free flight before entry, the integrated orbit between
    entry and exit, outbound free flight along the ASYMPTOTIC
    direction after exit (design 4.6-4.7)."""
    k, i = energy_index, particle_index
    orbit_times = store.time_grid[k] + orbit.time_offset
    speed = asymptotic_speed(orbit.energy)
    inbound = orbit_times < orbit.entry_time
    outbound = orbit_times > orbit.exit_time
    on_orbit = ~(inbound | outbound)
    count = len(orbit_times)
    x_plane = np.empty(count)
    y_plane = np.empty(count)
    vx_plane = np.empty(count)
    vy_plane = np.empty(count)

    entry = orbit.state_at([orbit.entry_time])[0]
    elapsed = orbit_times[inbound] - orbit.entry_time
    x_plane[inbound] = entry[0]
    y_plane[inbound] = entry[1] + speed * elapsed
    vx_plane[inbound] = 0.0
    vy_plane[inbound] = speed

    if on_orbit.any():
        states = orbit.state_at(orbit_times[on_orbit])
        x_plane[on_orbit], y_plane[on_orbit] = states[:, 0], states[:, 1]
        vx_plane[on_orbit], vy_plane[on_orbit] = states[:, 2], states[:, 3]

    exit_state = orbit.exit_state
    direction = np.array([np.sin(deflection), np.cos(deflection)])
    elapsed = orbit_times[outbound] - orbit.exit_time
    x_plane[outbound] = exit_state[0] + direction[0] * speed * elapsed
    y_plane[outbound] = exit_state[1] + direction[1] * speed * elapsed
    vx_plane[outbound] = direction[0] * speed
    vy_plane[outbound] = direction[1] * speed

    store.position[k, i] = embed(x_plane, y_plane, azimuth)
    store.velocity[k, i] = embed(vx_plane, vy_plane, azimuth)
    store.polar[k, i, :, 0] = np.hypot(x_plane, y_plane)
    store.polar[k, i, :, 1] = _signed_angle_from(orbit.pericenter_direction,
                                                 x_plane, y_plane)
    phase = np.zeros(count, dtype=np.int8)
    phase[inbound] = -1
    phase[outbound] = +1
    store.phase[k, i] = phase
    store.entry_index[k, i] = int(np.argmax(~inbound)) if on_orbit.any() \
        else count
    store.exit_index[k, i] = int(np.argmax(outbound)) if outbound.any() \
        else count


def _detector_arrival(orbit, deflection, r_detect):
    """Orbit time at which the outbound free flight reaches the
    detector sphere: the positive root of |exit + d v t| = R."""
    exit_x, exit_y = orbit.exit_state[0], orbit.exit_state[1]
    speed = asymptotic_speed(orbit.energy)
    direction = np.array([np.sin(deflection), np.cos(deflection)])
    along = exit_x * direction[0] + exit_y * direction[1]
    radial_sq = exit_x ** 2 + exit_y ** 2
    travel = (-along + np.sqrt(along ** 2 + r_detect ** 2 - radial_sq))
    return orbit.exit_time + travel / speed


def _signed_angle_from(reference, x_values, y_values):
    """The polar angle phi of (x, y) measured from the pericenter
    direction, signed counterclockwise (design 4.5)."""
    cross = reference[0] * y_values - reference[1] * x_values
    dot = reference[0] * x_values + reference[1] * y_values
    return np.arctan2(cross, dot)


def _angle_between(first, second):
    cosine = np.dot(first, second) / (np.linalg.norm(first)
                                      * np.linalg.norm(second))
    return float(np.arccos(np.clip(cosine, -1.0, 1.0)))


def _embed_trace(trace_plane, azimuth):
    return embed(trace_plane[:, 0], trace_plane[:, 1], azimuth)


def _versions():
    import numpy
    import scipy
    return {'python': sys.version.split()[0], 'numpy': numpy.__version__,
            'scipy': scipy.__version__}
