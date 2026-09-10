"""The results store: the precomputed run, frozen (pseudocode 6.1-
6.2, design 6).

Every sample of every particle at every energy lives here, laid out
energy-first so that one energy is a contiguous slab and one frame
-- one time, all particles -- is a strided read the renderer takes
in a single call:

##   position   [K, N, S, 3]     K energies, N particles, S samples
##   velocity   [K, N, S, 3]
##   polar      [K, N, S, 2]     (r, phi) in the orbital plane
##   phase      [K, N, S]        -1 inbound free flight, 0 orbit,
##                               +1 outbound free flight

plus the per-particle, per-energy, and provenance blocks of design
6.3. With n_samples = 0 the trajectory block is absent: that is the
batch mode, in which a million particles need no trajectory because
the detector and the inversion consume only the per-particle block.

The store is FROZEN after the driver fills it: every array is
read-only and no attribute may be reassigned. That is VISION P5 in
code, and it is what makes the determinism test mechanical -- scrub
the store in any order and nothing changes (ARCHITECTURE 8.6(3)).

Attribution: this module is part of the scattering teaching tool.
"""

import numpy as np

# Bytes per (K, N, S) sample: position, velocity, polar as float64
# plus phase as int8 (design 6.4, eq. 6.1).
_BYTES_PER_SAMPLE = (3 + 3 + 2) * 8 + 1
# Bytes per (K, N) per-particle entry: eight floats, one 3-vector,
# two ints.
_BYTES_PER_PARTICLE = 8 * 8 + 3 * 8 + 2 * 8


def estimate_bytes(n_energies, n_particles, n_samples, trace_points_max,
                   n_deflection_points):
    """The memory budget of design 6.4, from the run file alone."""
    trajectory = n_energies * n_particles * n_samples * _BYTES_PER_SAMPLE
    per_particle = n_energies * n_particles * _BYTES_PER_PARTICLE
    traces = n_energies * n_particles * trace_points_max * 3 * 8
    tables = n_energies * 4 * n_deflection_points * 8
    return int(trajectory + per_particle + traces + tables)


class FrozenError(AttributeError):
    """Raised on any attempt to modify a frozen store."""


class ResultsStore:
    """See the module docstring. Built by `allocate`, filled by the
    driver, sealed by `freeze`, and read through the methods below;
    consumers do not touch attributes directly (design 6.6)."""

    def __init__(self):
        object.__setattr__(self, '_frozen', False)

    def __setattr__(self, name, value):
        if getattr(self, '_frozen', False):
            raise FrozenError(f'the results store is frozen; cannot set '
                              f'{name!r}')
        object.__setattr__(self, name, value)

    @classmethod
    def allocate(cls, n_energies, n_particles, n_samples):
        """Empty arrays of the right shapes. `n_samples = 0` allocates
        no trajectory block (batch mode, design 6.5)."""
        store = cls()
        K, N, S = n_energies, n_particles, n_samples
        store.n_energies, store.n_particles, store.n_samples = K, N, S
        if S > 0:
            store.position = np.empty((K, N, S, 3))
            store.velocity = np.empty((K, N, S, 3))
            store.polar = np.empty((K, N, S, 2))
            store.phase = np.empty((K, N, S), dtype=np.int8)
            store.time_grid = np.empty((K, S))
        else:
            store.position = store.velocity = store.polar = None
            store.phase = store.time_grid = None
        store.impact_parameter = np.empty(N)
        store.azimuth = np.empty(N)
        store.annulus_index = np.empty(N, dtype=int)
        for name in ('turning_point', 'turning_point_q', 'deflection',
                     'time_offset', 'energy_drift', 'angmom_drift',
                     'finite_radius'):
            setattr(store, name, np.empty((K, N)))
        store.out_direction = np.empty((K, N, 3))
        store.entry_index = np.empty((K, N), dtype=int)
        store.exit_index = np.empty((K, N), dtype=int)
        store.energies = np.empty(K)
        store.theta_min = np.empty(K)
        store.theta_head = np.empty(K)
        store.mirror_diff = np.full(K, np.nan)
        store.provider_check = np.full(K, np.nan)
        store.deflection_table = [None] * K
        store.xsec_table = [None] * K
        store.mirror_table = [None] * K
        store.annulus_map = [[] for _ in range(K)]
        store.provider = [''] * K
        store.trace_points = [[] for _ in range(K)]
        store.run_spec = store.beam = None
        store.created = store.versions = store.git_commit = None
        return store

    def freeze(self):
        """Seal the store (design 6.7)."""
        for name, value in list(vars(self).items()):
            if isinstance(value, np.ndarray):
                value.flags.writeable = False
        for energy_traces in self.trace_points:
            for trace in energy_traces:
                trace.flags.writeable = False
        object.__setattr__(self, '_frozen', True)

    @property
    def frozen(self):
        return self._frozen

    # --- The read interface (design 6.6) --------------------------

    def frame(self, energy_index, sample_index):
        return self.position[energy_index, :, sample_index, :]

    def frame_polar(self, energy_index, sample_index):
        return self.polar[energy_index, :, sample_index, :]

    def frame_velocity(self, energy_index, sample_index):
        return self.velocity[energy_index, :, sample_index, :]

    def particle(self, energy_index, particle_index):
        """(time_grid, position, velocity, polar, phase) for one
        particle at one energy."""
        k, i = energy_index, particle_index
        return (self.time_grid[k], self.position[k, i], self.velocity[k, i],
                self.polar[k, i], self.phase[k, i])

    def final_directions(self, energy_index):
        return self.out_direction[energy_index]

    def deflection_of(self, energy_index):
        return self.impact_parameter, self.deflection[energy_index]

    def tables(self, energy_index):
        k = energy_index
        return (self.deflection_table[k], self.xsec_table[k],
                self.mirror_table[k], self.annulus_map[k])

    def trace(self, energy_index, particle_index):
        return self.trace_points[energy_index][particle_index]

    def drift(self, energy_index):
        k = energy_index
        return (self.energy_drift[k], self.angmom_drift[k],
                self.finite_radius[k])

    def time_of(self, energy_index, sample_index):
        return self.time_grid[energy_index, sample_index]

    def size_bytes(self):
        total = 0
        for value in vars(self).values():
            if isinstance(value, np.ndarray):
                total += value.nbytes
        for energy_traces in self.trace_points:
            for trace in energy_traces:
                total += trace.nbytes
        return total

    def provenance(self):
        return {'run_spec': self.run_spec, 'beam': self.beam,
                'created': self.created, 'versions': self.versions,
                'git_commit': self.git_commit}
