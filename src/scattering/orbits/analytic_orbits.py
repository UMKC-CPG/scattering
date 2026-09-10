"""The analytic orbit provider, re-exported for the module map of
ARCHITECTURE section 4.4. The implementation lives beside the
numerical provider in `orbit_provider.py` because the two share the
entry-plane and pericenter helpers; the closed forms themselves are
the potential's (potentials/coulomb.py)."""

from scattering.orbits.orbit_provider import AnalyticProvider

__all__ = ['AnalyticProvider']
