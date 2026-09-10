"""Named real-unit presets: physically meaningful (m, kappa, E_ref)
triples and the units a student should see results in.

Design section 1.5 ships two presets, one of each sign of the
Coulomb strength: `alpha_on_gold` (Rutherford's experiment) and
`interstellar_visitor` (a hyperbolic pass by the Sun). A run file
selects one by name and may override any single value (design
10.3). Every physical constant here is read from `scipy.constants`
at import time rather than typed in, because a hand-copied constant
is a transcription error waiting to be found (design 1.4). The one
exception is the solar gravitational parameter, which SciPy does not
carry; it is the IAU 2015 nominal value, cited where it is defined.

This module imports pint through `units.py` only, and holds no
physics: it is data.

Attribution: this module is part of the scattering teaching tool.
Derived code should cite it, and the sources named in design 1.8.
"""

from dataclasses import dataclass, field
from typing import Optional

from scipy import constants

from scattering.core.units import Quantity, quantity

# IAU 2015 Resolution B3, nominal solar mass parameter GM_sun in
# m^3 s^-2. Not available in scipy.constants, hence the one typed
# literal in this file; the resolution is the citation.
GM_SUN_M3_PER_S2 = 1.3271244e20


@dataclass(frozen=True)
class Preset:
    """A preset's data, per pseudocode 1.1.

    Exactly one of `kappa` and `kappa_per_mass` is set. When
    `kappa_per_mass` is set (gravity), the orbit is independent of
    the projectile mass, `mass` may be None, and the driver assigns
    a dummy unit mass that is never displayed. `reference_energy`
    may be None if `v_inf` is given, in which case the reference
    energy is the kinetic energy at that speed.
    """
    name: str
    kind: str
    sign: int
    kappa: Optional[Quantity] = None
    kappa_per_mass: Optional[Quantity] = None
    mass: Optional[Quantity] = None
    reference_energy: Optional[Quantity] = None
    v_inf: Optional[Quantity] = None
    display_units: dict = field(default_factory=dict)
    note: str = ''


def _alpha_on_gold():
    """Rutherford's experiment: alpha particles on a gold nucleus."""
    atomic_number_projectile = 2
    atomic_number_target = 79
    coulomb_constant = 1.0 / (4.0 * constants.pi * constants.epsilon_0)
    kappa_joule_metre = (atomic_number_projectile * atomic_number_target
                         * constants.e ** 2 * coulomb_constant)
    return Preset(
        name='alpha_on_gold', kind='coulomb', sign=+1,
        kappa=quantity(kappa_joule_metre, 'J * m'),
        mass=quantity(constants.physical_constants['alpha particle mass'][0],
                      'kg'),
        reference_energy=quantity(5.0, 'MeV'),
        display_units={'energy': 'MeV', 'length': 'fm', 'mass': 'MeV/c^2',
                       'speed': 'c', 'time': 's', 'energy*length': 'MeV*fm',
                       'area': 'fm^2', 'angular_momentum': 'MeV*fm/c'},
        note='non-relativistic: v_inf / c is reported on screen')


def _interstellar_visitor():
    """A small body passing the Sun on a hyperbolic orbit, with an
    excess speed of the order of Oumuamua's."""
    return Preset(
        name='interstellar_visitor', kind='coulomb', sign=-1,
        kappa_per_mass=quantity(-GM_SUN_M3_PER_S2, 'm^3 / s^2'),
        mass=None,
        v_inf=quantity(26.0, 'km / s'),
        display_units={'energy': 'J', 'length': 'au', 'mass': 'kg',
                       'speed': 'km / s', 'time': 'day',
                       'energy*length': 'J * au', 'area': 'au^2',
                       'angular_momentum': 'J * s'},
        note='orbit independent of projectile mass (equivalence '
             'principle); the mass is a dummy and is never shown')


PRESETS = {
    'alpha_on_gold': _alpha_on_gold(),
    'interstellar_visitor': _interstellar_visitor(),
}
