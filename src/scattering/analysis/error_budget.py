"""The error budget: three columns, never summed (pseudocode 9.3,
design 9.2, 9.8).

Numerical error comes from a finite step, radius, or tolerance and is cured by
tightening them; statistical error comes from a finite particle count and is
cured by more particles; an assumption is a model chosen where the data are
silent and is cured by a different assumption or more data. A student who sees
one combined figure learns nothing about which remedy applies, so the three are
kept in separate records and displayed in separate columns. No function in this
module or in the panel that draws it may combine a field of one column with a
field of another; tests/unit/test_error_budget.py walks the syntax tree to
check.

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import dataclass
from typing import Optional

import numpy as np

from scattering.analysis.conservation_monitor import (residual_maxima,
                                                      residual_series)


@dataclass(frozen=True)
class NumericalColumn:
    energy_drift_max: float
    angmom_drift_max: float
    exterior_deflection_max: float
    provider_check: float
    quad_error: float
    orbit_provider: str
    integrator: str
    rtol: float
    atol: float
    r_max: float
    closed_form: bool


@dataclass(frozen=True)
class StatisticalColumn:
    pull_rms: float
    n_particles: int
    n_bins: int
    stat_band_at_reach: float
    stat_band_at_far: float
    has_flux: bool


@dataclass(frozen=True)
class AssumptionColumn:
    tail_model: str
    tail_fraction_at_far: float
    assume_sign: int


@dataclass(frozen=True)
class TrackedSeries:
    particle_index: int
    time: np.ndarray
    energy_residual: np.ndarray
    angmom_residual: np.ndarray


@dataclass(frozen=True)
class ErrorBudget:
    energy_index: int
    numerical: NumericalColumn
    statistical: StatisticalColumn
    assumption: Optional[AssumptionColumn]
    tracked: TrackedSeries


def build_error_budget(store, resolved, energy_index, tracked,
                       detector=None, inversion=None):
    """Collect the budget for one energy (pseudocode 9.3). `detector`
    is a DetectorResult or None; `inversion` an InversionResult or
    None until pseudocode section 8 exists."""
    k = energy_index
    energy_max, angmom_max, exterior_max = residual_maxima(store, k)
    settings = resolved.settings
    numerical = NumericalColumn(
        energy_drift_max=energy_max, angmom_drift_max=angmom_max,
        exterior_deflection_max=exterior_max,
        provider_check=float(store.provider_check[k]),
        quad_error=(float(inversion.quad_error) if inversion is not None
                    else np.nan),
        orbit_provider=store.provider[k], integrator=settings.integrator,
        rtol=settings.rtol, atol=settings.atol, r_max=settings.r_max,
        closed_form=store.provider[k] == 'analytic')
    has_flux = bool(detector is not None and detector.has_flux)
    statistical = StatisticalColumn(
        pull_rms=float(detector.pull_rms) if has_flux else np.nan,
        n_particles=store.n_particles,
        n_bins=detector.layout.n_bins if detector is not None else 0,
        stat_band_at_reach=(float(inversion.stat_band_at_reach)
                            if inversion is not None else np.nan),
        stat_band_at_far=(float(inversion.stat_band_at_far)
                          if inversion is not None else np.nan),
        has_flux=has_flux)
    assumption = None
    if inversion is not None:
        assumption = AssumptionColumn(inversion.tail_model,
            float(inversion.tail_fraction_at_far), int(inversion.assume_sign))
    times, energy_residual, angmom_residual = residual_series(
        store, resolved, k, tracked)
    return ErrorBudget(k, numerical, statistical, assumption,
        TrackedSeries(tracked, times, energy_residual, angmom_residual))
