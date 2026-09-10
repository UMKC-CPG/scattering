"""Central potentials: the interface every potential satisfies and
the potentials themselves.

Governed by pseudocode section 2 and design section 2 (Coulomb), with the
interface fixed by ARCHITECTURE section 6.1: a potential must supply its value
and derivative, and MAY supply closed forms for the deflection function and the
orbit. Consumers test for those capabilities and never branch on a potential's
type (VISION P12).
"""

from scattering.potentials.potential_interface import Potential
from scattering.potentials.coulomb import CoulombPotential


def make_potential(potential_spec):
    """Build the potential named by a PotentialSpec (pseudocode 6.3).
    The first version knows only Coulomb; a later kind is a new
    branch here and a new module beside `coulomb.py`."""
    if potential_spec.kind == 'coulomb':
        sign = potential_spec.sign
        if sign is None:
            from scattering.core.presets import PRESETS
            if potential_spec.preset is None:
                raise ValueError('[potential].sign is required when no '
                                 'preset is given')
            sign = PRESETS[potential_spec.preset].sign
        return CoulombPotential(sign)
    raise ValueError(f'unknown potential kind {potential_spec.kind!r}; '
                     f'the first version supports "coulomb"')


__all__ = ['Potential', 'CoulombPotential', 'make_potential']
