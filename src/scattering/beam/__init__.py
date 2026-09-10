"""The beam: the complete set of initial conditions for a run.

Governed by pseudocode section 3 and design section 3. A beam is plain data --
energies, impact parameters, azimuths, and how they were laid out -- and nothing
downstream knows anything else about where the particles came from.
"""

from scattering.beam.beam_spec import AnnulusSpec, Beam, BeamSpec
from scattering.beam.impact_sampler import (
    check_admissible, generate_beam, layout_annuli, sample_disc)
from scattering.beam.energy_sampler import particle_energy

__all__ = ['AnnulusSpec', 'Beam', 'BeamSpec', 'check_admissible',
           'generate_beam', 'layout_annuli', 'sample_disc',
           'particle_energy']
