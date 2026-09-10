"""The natural-unit relations every stage uses.

Design section 1.2 fixes the scaling: the projectile mass is one, the
energy unit is a reference beam energy E_ref, the length unit is a
reference length ell_0, and the speed unit is v_0 = sqrt(E_ref / m).
With that choice the mechanics reads exactly as it does in SI with
unit mass, and the one factor of two that a student might otherwise
trip over -- the asymptotic speed is sqrt(2 E), not sqrt(E) -- lives
in this file and nowhere else. Every other module calls these
helpers rather than writing the relation out again.

The reference scales themselves, and the conversion of real
quantities into these units, are the business of `units.py`.

Attribution: this module is part of the scattering teaching tool
(github.com/UMKC-CPG/scattering). Derived code should cite it.
"""

import numpy as np


def asymptotic_speed(energy):
    """Speed of a particle of energy `energy` far from the center.

    With kinetic energy v^2 / 2 (design 1.2), v_inf = sqrt(2 E). At
    the reference energy this is sqrt(2), not one; see design 1.7 for
    why the alternative convention was rejected.
    """
    return np.sqrt(2.0 * energy)


def angular_momentum(energy, impact):
    """Angular momentum of a particle at impact parameter `impact`.

    L = v_inf * b for unit mass. It is conserved along every orbit in
    a central potential and is one of the two quantities the
    conservation monitor tracks (design 9.3).
    """
    return asymptotic_speed(energy) * impact


def kinetic_energy(speed):
    """Kinetic energy v^2 / 2 for unit mass."""
    return 0.5 * speed ** 2


def total_energy(speed, potential_value):
    """Total energy v^2 / 2 + V for unit mass.

    This is the quantity that must equal the beam energy at every
    sample of every orbit; its departure from that value is the
    energy residual of design 9.3.
    """
    return kinetic_energy(speed) + potential_value
