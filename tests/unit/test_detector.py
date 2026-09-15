"""Verifies pseudocode section 7 (P7.9). Design section 7."""

import numpy as np
import pytest

from scattering.beam.beam_spec import AnnulusSpec, BeamSpec
from scattering.detector import (build_detector_result, build_layout,
                                 expected_counts)
from scattering.run import (DetectorSpec, FidelitySpec, PotentialSpec,
                            RunSpec, build_results_store, resolve)


def disc_spec(sign=+1, n_particles=20000, b_min=0.0, seed=20260910,
              n_samples=0, **detector):
    return RunSpec(
        potential=PotentialSpec(preset='alpha_on_gold', sign=sign),
        beam=BeamSpec(energies=[1.0], layout='disc',
                      n_particles=n_particles, b_min=b_min, b_max=12.0,
                      seed=seed),
        fidelity=FidelitySpec(r_max=40.0, n_samples=n_samples,
                              n_deflection_points=200,
                              trace_points_max=0),
        detector=DetectorSpec(**detector))


@pytest.fixture(scope='module')
def disc():
    resolved = resolve(disc_spec())
    return resolved, build_results_store(resolved)


@pytest.fixture(scope='module')
def annuli():
    spec = RunSpec(
        potential=PotentialSpec(preset='alpha_on_gold'),
        beam=BeamSpec(energies=[1.0], layout='annuli',
                      annuli=(AnnulusSpec(0.5, 0.05, 8),
                              AnnulusSpec(2.0, 0.05, 8),
                              AnnulusSpec(6.0, 0.05, 8))),
        fidelity=FidelitySpec(r_max=40.0, n_samples=40,
                              n_deflection_points=80),
        detector=DetectorSpec(radius=2.0))
    resolved = resolve(spec)
    return resolved, build_results_store(resolved)


@pytest.mark.parametrize('layout', ['log_theta', 'uniform_theta',
                                    'equal_solid_angle'])
def test_layout_covers_the_measured_range(layout):
    spec = DetectorSpec(layout=layout, n_bins=25)
    built = build_layout(spec, 0.1, 2.9, 80.0)
    assert built.edges[0] == pytest.approx(0.1)
    assert built.edges[-1] == pytest.approx(2.9)
    assert built.solid_angle.sum() == pytest.approx(
        2 * np.pi * (np.cos(0.1) - np.cos(2.9)), rel=1e-12)
    if layout == 'equal_solid_angle':
        assert np.allclose(built.solid_angle, built.solid_angle[0])


def test_n_phi_refused():
    with pytest.raises(ValueError):
        build_layout(DetectorSpec(n_phi=4), 0.1, 3.0, 80.0)


def test_disc_counts_are_poisson(disc):
    """A8.4: fixed seed, seed-independent property. Spike: 0.94-1.05."""
    resolved, store = disc
    result = build_detector_result(store, resolved, 0)
    assert result.n_outside == 0
    assert result.n_counted == store.n_particles
    assert result.has_flux
    assert abs(result.pull_rms - 1.0) < 3 * np.sqrt(2 / 40)
    assert result.expected.sum() == pytest.approx(store.n_particles,
                                                  rel=2e-3)


def test_equal_solid_angle_is_the_labeled_bad_example(disc):
    resolved, store = disc
    result = build_detector_result(store, resolved, 0,
                                   DetectorSpec(layout='equal_solid_angle'))
    # Design 7.4: nearly every count lands in the first bin.
    assert result.counts.max() / result.n_counted > 0.5
    assert result.empty.sum() > 0
    from scattering.render.panels import panel_cross_section
    text = ' '.join(panel_cross_section(store, 0, result).text)
    assert 'poor layout' in text


def test_sign_independence_is_bitwise():
    """Design 7.9: attractive and repulsive Coulomb at one seed give
    identical counts, bit for bit."""
    plus = resolve(disc_spec(sign=+1, n_particles=4000, b_min=0.05))
    minus = resolve(disc_spec(sign=-1, n_particles=4000, b_min=0.05))
    result_plus = build_detector_result(build_results_store(plus), plus, 0)
    result_minus = build_detector_result(build_results_store(minus), minus,
                                         0)
    assert np.array_equal(result_plus.counts, result_minus.counts)
    assert result_plus.mirror_diff == 0.0


def test_position_mode_offset(annuli):
    """Every landing angle exceeds the asymptotic angle by
    asin(b / R_detect); the shift halves when R_detect doubles."""
    resolved, store = annuli
    from scattering.detector.binning import (asymptotic_angles,
                                             position_angles)
    layout = build_layout(DetectorSpec(mode='position'), store.theta_min[0],
        store.theta_head[0], resolved.detector_radius)
    asym = asymptotic_angles(store.final_directions(0))
    pos = position_angles(store, 0, layout)
    # The drawn line starts at the exit point on the R_max sphere,
    # not on the true asymptote, so the offset is asin(b / R_detect)
    # only to the exterior-deflection correction, about a percent.
    expected = np.arcsin(store.impact_parameter / resolved.detector_radius)
    assert np.allclose(np.abs(pos - asym), expected, rtol=0.02)
    near = build_detector_result(store, resolved, 0,
                                 DetectorSpec(mode='position', radius=2.0))
    far_layout = build_layout(DetectorSpec(mode='position'), store.theta_min[0],
        store.theta_head[0], 2 * resolved.detector_radius)
    far = position_angles(store, 0, far_layout)
    assert np.nanmean(np.abs(far - asym)) == pytest.approx(
        0.5 * np.nanmean(np.abs(pos - asym)), rel=0.02)
    assert np.isfinite(near.position_shift).any()


def test_batch_store_falls_back_to_asymptotic(disc):
    resolved, store = disc
    result = build_detector_result(store, resolved, 0,
                                   DetectorSpec(mode='position'))
    assert np.isnan(result.position_shift).all()
    assert result.n_counted == store.n_particles


def test_annuli_beam_has_counts_but_no_estimate(annuli):
    resolved, store = annuli
    result = build_detector_result(store, resolved, 0)
    assert not result.has_flux
    assert np.isnan(result.estimate).all() and np.isnan(result.pull_rms)
    assert result.counts.sum() == 24
    from scattering.render.panels import panel_cross_section
    text = ' '.join(panel_cross_section(store, 0, result).text)
    assert 'uniform-flux beam required' in text


def test_expected_integrates_the_table(disc):
    resolved, store = disc
    layout = build_layout(DetectorSpec(n_bins=12), store.theta_min[0],
                          store.theta_head[0], resolved.detector_radius)
    expected = expected_counts(store.tables(0)[1], layout, store.beam.flux)
    assert expected.sum() == pytest.approx(store.n_particles, rel=2e-3)
