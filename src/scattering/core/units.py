"""The units boundary: the only module that imports pint.

Design section 1.4 and ARCHITECTURE section 6.6 fix the rule: real
units enter the library exactly once, when a run specification is
converted to natural units, and leave exactly once, when a value is
formatted for display. Below `run/`, no module imports pint, accepts
a pint object, or returns one -- an architectural test enforces it.

Three operations live here (pseudocode 1.3-1.4):

  build_scales   resolve the reference scales (m, E_ref, ell_0) from
                 a [potential] table and a preset;
  to_natural     divide a dimensioned quantity by its reference scale
                 and return a bare float;
  from_natural   multiply a bare float back up and express it in the
                 preset's display unit.

Why pint (inherited from the rigid-body tool, ARCHITECTURE 6.6): its
per-operation cost lands only at this boundary, its error messages
are the clearest a student will see, and it parses strings such as
"5 MeV" so that a run file can carry readable quantities.

Attribution: this module is part of the scattering teaching tool.
Derived code should cite it.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pint

# One registry for the whole program. `c` is the speed of light, so
# that "MeV/c^2" parses as a mass and "0.05 c" as a speed.
UNIT_REGISTRY = pint.UnitRegistry()
UNIT_REGISTRY.define('c = speed_of_light')
Quantity = UNIT_REGISTRY.Quantity


def quantity(magnitude, unit):
    """Build a pint quantity; the one constructor the rest of the
    package is meant to call, so that only this module names the
    registry."""
    return Quantity(magnitude, unit)


def parse_quantity(value):
    """Turn a string such as "5 MeV" or "26 km/s", or an existing
    pint quantity, into a pint quantity. A bare number is refused
    here: whether a bare number means "natural units" is the
    caller's decision (`to_natural`), not this function's."""
    if isinstance(value, Quantity):
        return value
    if isinstance(value, str):
        return UNIT_REGISTRY.parse_expression(value)
    raise TypeError(f'expected a quantity or a unit string, got '
                    f'{type(value).__name__}: {value!r}')


def is_bare(value):
    """True for a plain number, which the run file treats as already
    in natural units (design 10.3)."""
    return isinstance(value, (int, float, np.integer, np.floating)) \
        and not isinstance(value, bool)


@dataclass(frozen=True)
class ReferenceScales:
    """The three reference scales and what follows from them
    (pseudocode 1.1). All are pint quantities in SI.

    The speed scale is sqrt(E_ref / m) -- NOT sqrt(2 E_ref / m) --
    so that the natural-unit mechanics has unit mass with kinetic
    energy v^2 / 2 (design 1.2). `display_units` maps a dimension
    name to the unit string the preset wants results shown in.
    """
    mass: Quantity
    energy: Quantity
    length: Quantity
    speed: Quantity
    time: Quantity
    angular_momentum: Quantity
    display_units: dict

    def scale_for(self, dimension):
        """The reference quantity that divides a given dimension.
        The dimension names are the ones the run-file schema uses
        (design 10.5)."""
        table = {
            'energy': self.energy,
            'length': self.length,
            'mass': self.mass,
            'speed': self.speed,
            'time': self.time,
            'angular_momentum': self.angular_momentum,
            'energy*length': self.energy * self.length,
            'area': self.length ** 2,
        }
        try:
            return table[dimension]
        except KeyError:
            raise KeyError(f'unknown dimension {dimension!r}; one of '
                           f'{sorted(table)}') from None


def build_scales(potential_table, potential, first_energy):
    """Resolve the reference scales per pseudocode 1.3.

    `potential_table` is a PotentialSpec (pseudocode 6.3): a preset
    name and optional explicit kappa, mass, reference_energy, and
    reference_length, each a pint quantity or None. Explicit values
    override the preset. `potential` supplies the default reference
    length (design 1.3); `first_energy` is the first beam energy, the
    fallback for E_ref (design 1.2).
    """
    # Imported here rather than at module top so that presets.py can
    # import `quantity` from this module without a cycle.
    from scattering.core.presets import PRESETS

    preset = None
    if potential_table.preset is not None:
        try:
            preset = PRESETS[potential_table.preset]
        except KeyError:
            raise ValueError(f'unknown preset {potential_table.preset!r}; '
                             f'one of {sorted(PRESETS)}') from None

    def from_preset(attribute):
        return getattr(preset, attribute) if preset is not None else None

    kappa = potential_table.kappa or from_preset('kappa')
    mass = potential_table.mass or from_preset('mass')
    kappa_per_mass = from_preset('kappa_per_mass') if kappa is None \
        else None

    if kappa is None and kappa_per_mass is None:
        raise ValueError('no Coulomb strength: give [potential].kappa or '
                         'a preset')
    if kappa is None:
        # Gravity: kappa is proportional to the projectile mass, so
        # the orbit does not depend on it and a dummy mass serves.
        mass = mass or quantity(1.0, 'kg')
        kappa = kappa_per_mass * mass
    if mass is None:
        raise ValueError('no projectile mass: give [potential].mass or '
                         'a preset')

    reference_energy = (potential_table.reference_energy
                        or from_preset('reference_energy'))
    if reference_energy is None and from_preset('v_inf') is not None:
        reference_energy = 0.5 * mass * from_preset('v_inf') ** 2
    if reference_energy is None:
        reference_energy = parse_quantity(first_energy)

    for name, value in (('mass', mass), ('reference energy',
                                         reference_energy)):
        if not value.magnitude > 0:
            raise ValueError(f'{name} must be positive, got {value}')
    if not abs(kappa.magnitude) > 0:
        raise ValueError(f'kappa must be nonzero, got {kappa}')

    reference_length = potential_table.reference_length
    if reference_length is None:
        reference_length = potential.default_reference_length(
            kappa, reference_energy)

    mass = mass.to_base_units()
    reference_energy = reference_energy.to_base_units()
    reference_length = reference_length.to_base_units()
    speed = (reference_energy / mass) ** 0.5
    time = reference_length / speed
    display_units = dict(from_preset('display_units') or {})
    return ReferenceScales(mass, reference_energy, reference_length,
                           speed.to_base_units(), time.to_base_units(),
                           (mass * speed * reference_length).to_base_units(),
                           display_units)


def to_natural(value, dimension, scales):
    """Convert one quantity to natural units (pseudocode 1.4).

    A bare number is returned as is: the run file's convention is that
    a number with no unit is already in natural units (design 10.3).
    A string or pint quantity is parsed, checked against the named
    dimension, and divided by that dimension's reference scale.
    """
    if is_bare(value):
        return float(value)
    parsed = parse_quantity(value)
    expected = scales.scale_for(dimension)
    if parsed.dimensionality != expected.dimensionality:
        raise ValueError(f'{dimension} expected, got a quantity of '
                         f'dimension {parsed.dimensionality} ({value})')
    return float((parsed / expected).to_base_units().magnitude)


def to_natural_list(values, dimension, scales):
    """Convert a list, refusing a mix of bare and dimensioned entries
    (design 10.3): a list that is half natural and half SI is almost
    certainly a mistake, and silently converting it would hide it."""
    kinds = {is_bare(value) for value in values}
    if len(kinds) > 1:
        raise ValueError(f'mixed bare and dimensioned values in '
                         f'{list(values)}')
    return np.array([to_natural(value, dimension, scales)
                     for value in values], dtype=float)


def from_natural(value, dimension, scales):
    """Multiply a natural-unit value back to a pint quantity in the
    preset's display unit for that dimension, or SI if the preset
    names none (the label then says so, design 1.6)."""
    result = value * scales.scale_for(dimension)
    unit = scales.display_units.get(dimension)
    if unit is None:
        return result.to_base_units()
    return result.to(unit)


def format_natural(value, dimension, scales, digits=4):
    """A display string such as "45.5 fm" for a natural-unit value."""
    result = from_natural(value, dimension, scales)
    return f'{result.magnitude:.{digits}g} {result.units:~}'
