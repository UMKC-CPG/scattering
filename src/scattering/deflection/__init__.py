"""From orbits to angles: the deflection function, the cross
section, and the annulus-to-cone map.

Governed by pseudocode section 5 and design section 5. This is the middle of the
chain in both directions (ARCHITECTURE 2): the deflection function is computed
FROM THE POTENTIAL BY QUADRATURE, not read off the integrated orbits, because
that integral is what the inversion later inverts.
"""

from scattering.deflection.deflection_function import (DeflectionTable,
    build_deflection_table, d_deflection_of, deflection_by_quadrature,
    deflection_of, mirror_check, particle_deflections, particle_outputs)
from scattering.deflection.cross_section import (
    CrossSectionTable, build_cross_section_table, dsdo_at)
from scattering.deflection.solid_angle import AnnulusMap, annulus_map

__all__ = ['DeflectionTable', 'build_deflection_table',
           'd_deflection_of', 'deflection_by_quadrature',
           'deflection_of', 'mirror_check', 'particle_deflections',
           'particle_outputs', 'CrossSectionTable',
           'build_cross_section_table', 'dsdo_at', 'AnnulusMap',
           'annulus_map']
