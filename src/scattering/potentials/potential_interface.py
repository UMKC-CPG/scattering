"""The contract every central potential satisfies (pseudocode 2.1,
ARCHITECTURE 6.1).

A potential is a function of the radius alone, in the natural units
of design section 1. The REQUIRED part of the contract is small: the
value V(r), the derivative dV/dr, whether a head-on orbit (b = 0)
exists, the default reference length, and a description for labels.

The OPTIONAL part is a set of capabilities -- a closed-form
deflection function, a closed-form orbit, an exact starting state
at finite radius, a sign-flipped mirror -- each announced by a
boolean attribute. A consumer that finds a capability present may
use it; one that finds it absent falls back to the general
numerical route. No consumer may ask which potential it holds: the
Coulomb potential and a later Yukawa potential are told apart only
by what they can do (VISION P12).

Attribution: this module is part of the scattering teaching tool.
Derived code should cite it.
"""


class Potential:
    """Base class for central potentials.

    Subclasses override the required methods and set the capability
    flags they support; the defaults here declare no capabilities
    and raise if a capability is called anyway, which is a
    programming error rather than a user error.
    """

    # Capability flags (ARCHITECTURE 6.1). Consumers test these.
    has_closed_form_deflection = False
    has_closed_form_orbit = False
    has_mirror = False

    # --- Required ------------------------------------------------

    def value(self, radius):
        """V(r) in natural units. Accepts scalars and arrays."""
        raise NotImplementedError

    def derivative(self, radius):
        """dV/dr in natural units. Accepts scalars and arrays."""
        raise NotImplementedError

    def admits_center(self):
        """Whether an impact parameter of exactly zero is an orbit.
        Repulsive Coulomb: yes (the particle turns straight back).
        Attractive Coulomb: no (it falls to the center). The beam
        asks this before throwing a b = 0 particle (design 3.4)."""
        raise NotImplementedError

    def default_reference_length(self, kappa, reference_energy):
        """The natural length scale for this potential, as a pint
        quantity, used when the run file does not set one (design
        1.3). `kappa` and `reference_energy` are pint quantities;
        this is the one place a potential touches real units, and
        it does so only to divide two of them."""
        raise NotImplementedError

    def tail_exponent(self):
        """The power n in V ~ r^(-n) at large r. Used to decide
        whether a straight-line start at finite radius is acceptable
        (design 4.4) and to shape the inversion's tail model (design
        8.5). Coulomb is 1; anything faster is safe to truncate."""
        raise NotImplementedError

    def describe(self):
        """A short label for the screen, e.g. 'repulsive Coulomb'."""
        raise NotImplementedError

    # --- Optional capabilities -----------------------------------

    def closed_form_deflection(self, energy, impact):
        """Signed deflection angle Theta(b) at energy E, if a closed
        form exists. Guarded by `has_closed_form_deflection`."""
        raise NotImplementedError('no closed-form deflection')

    def closed_form_orbit(self, energy, impact):
        """An analytic orbit object (pseudocode 2.3), if one exists.
        Guarded by `has_closed_form_orbit`."""
        raise NotImplementedError('no closed-form orbit')

    def asymptotic_state(self, energy, impact, radius):
        """The exact in-plane state (x_p, y_p, v_x, v_y), in the beam
        frame of design 4.3, of the true orbit at the given radius on
        the inbound leg. Guarded by `has_closed_form_orbit`."""
        raise NotImplementedError('no closed-form orbit')

    def mirror(self):
        """The potential with its sign flipped, for the sign-
        independence check of design 5.6. Guarded by `has_mirror`."""
        raise NotImplementedError('no mirror')
