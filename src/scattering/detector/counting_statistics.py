"""Counts, the cross-section estimate, its Poisson error, the
bin-integrated expectation, and the pulls (pseudocode 7.5-7.6, design 7.5-7.6).

The estimate in bin i is N_i / (F dOmega_i): the BIN AVERAGE of the cross
section, not its value at any point. The expectation it is compared with is the
cross section integrated over the bin -- never its value at the bin center times
the solid angle, which for a theta^-4 law is off by orders of magnitude in a
wide bin (the first trap dev/spikes/firsov_inversion.py found). The pull (N_i -
E_i) / sqrt(E_i) has an RMS of 1.0 when the counts scatter exactly as Poisson
statistics predict; that number is what VISION P3 puts on screen, separately
from any conservation drift.

Attribution: this module is part of the scattering teaching tool.
"""

import warnings
from dataclasses import dataclass

import numpy as np
from scipy.integrate import IntegrationWarning, quad

from scattering.deflection.cross_section import dsdo_at
from scattering.detector.binning import (asymptotic_angles, bin_particles,
                                         position_angles)
from scattering.detector.detector_spec import DetectorLayout, build_layout


@dataclass(frozen=True)
class DetectorResult:
    """Design 7.8. What the inversion receives, and all it receives."""
    layout: DetectorLayout
    energy_index: int
    counts: np.ndarray
    estimate: np.ndarray
    error: np.ndarray
    expected: np.ndarray
    pull: np.ndarray
    empty: np.ndarray
    flux: float
    n_thrown: int
    n_counted: int
    n_outside: int
    pull_rms: float
    position_shift: np.ndarray
    mirror_diff: float
    has_flux: bool


def estimate_and_error(counts, layout, flux):
    """Eqs. (7.2) and (7.3). With no flux (an annuli beam) the
    estimate is undefined and NaN; the counts still mean something."""
    empty = counts == 0
    if not np.isfinite(flux):
        nans = np.full(len(counts), np.nan)
        return nans, nans.copy(), empty
    denominator = flux * layout.solid_angle
    return counts / denominator, np.sqrt(counts) / denominator, empty


def expected_counts(xsec, layout, flux):
    """Eq. (7.4): flux times the cross section integrated over each
    bin's solid angle."""
    expected = np.empty(layout.n_bins)
    # The table is piecewise in log(dsdo), so quad reports roundoff at its
    # knots; the achieved accuracy (the expectations sum to N to 1e-4) is far
    # beyond what a comparison with counts needs.
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', IntegrationWarning)
        for index in range(layout.n_bins):
            low, high = layout.edges[index], layout.edges[index + 1]
            integral, _ = quad(lambda t: dsdo_at(xsec, t) * np.sin(t), low,
                high, epsabs=1e-12, epsrel=1e-10, limit=100)
            expected[index] = 2.0 * np.pi * flux * integral
    return expected


def pulls(counts, expected):
    """Eq. (7.5) and its RMS; bins with no expectation contribute
    nothing."""
    valid = expected > 0.0
    safe = np.where(valid, expected, 1.0)
    pull = np.where(valid, (counts - expected) / np.sqrt(safe), np.nan)
    rms = float(np.sqrt(np.nanmean(pull ** 2))) if valid.any() else np.nan
    return pull, rms


def build_detector_result(store, resolved, energy_index, spec=None):
    """The whole detector for one energy (pseudocode 7.6)."""
    k = energy_index
    spec = spec or resolved.spec.detector
    layout = build_layout(spec, store.theta_min[k], store.theta_head[k],
                          resolved.detector_radius)
    directions = store.final_directions(k)
    angles_asymptotic = asymptotic_angles(directions)
    angles_position = position_angles(store, k, layout)
    use_position = spec.mode == 'position' and angles_position is not None
    angles = angles_position if use_position else angles_asymptotic
    counts, n_outside = bin_particles(angles, layout)
    flux = float(store.beam.flux)
    estimate, error, empty = estimate_and_error(counts, layout, flux)
    has_flux = bool(np.isfinite(flux))
    if has_flux:
        expected = expected_counts(store.tables(k)[1], layout, flux)
        pull, pull_rms = pulls(counts, expected)
    else:
        expected = np.full(layout.n_bins, np.nan)
        pull = np.full(layout.n_bins, np.nan)
        pull_rms = np.nan
    shift = np.full(layout.n_bins, np.nan)
    if angles_position is not None:
        difference = np.abs(angles_position - angles_asymptotic)
        which = np.clip(
            np.searchsorted(layout.edges, angles_asymptotic, side='right') - 1,
            0, layout.n_bins - 1)
        for index in range(layout.n_bins):
            members = which == index
            if members.any():
                shift[index] = difference[members].mean()
    return DetectorResult(layout, k, counts, estimate, error, expected, pull,
        empty, flux, store.n_particles, int(counts.sum()), n_outside, pull_rms,
        shift, float(store.mirror_diff[k]), has_flux)
