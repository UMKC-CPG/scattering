"""The per-particle energy (pseudocode 3.6): the hook for a future
continuous energy spread (VISION FD2, design 3.2).

In the first version every particle at energy index k has exactly the k-th
listed energy, so this is trivial -- and it is called anyway from the driver, so
that a distribution later is a new branch here and nothing else. The results
store keys on the energy INDEX, which survives the generalization.

Attribution: this module is part of the scattering teaching tool.
"""


def particle_energy(spec, energy_index, particle_index):
    """The energy of one particle in the sweep. `particle_index` is
    unused by the delta distribution and is part of the signature so
    that a per-particle distribution slots in unchanged."""
    if spec.distribution == 'delta':
        return float(spec.energies[energy_index])
    raise ValueError(f'unsupported energy distribution '
                     f'{spec.distribution!r}; the first version '
                     f'supports "delta"')
