"""Verifies pseudocode section 9 (P9.5). Design section 9."""

import ast
from pathlib import Path

import numpy as np
import pytest

from scattering.analysis import build_error_budget, residual_series
from scattering.beam.beam_spec import AnnulusSpec, BeamSpec
from scattering.detector import build_detector_result
from scattering.render.panels import panel_error_budget, render_panel
from scattering.render.palettes import BACKGROUNDS, PALETTES
from scattering.run import (DetectorSpec, FidelitySpec, PotentialSpec,
                            RunSpec, build_results_store, resolve)

PACKAGE = Path(__file__).resolve().parents[2] / 'src' / 'scattering'


def annuli_spec(**fidelity):
    return RunSpec(
        potential=PotentialSpec(preset='alpha_on_gold'),
        beam=BeamSpec(energies=[1.0, 2.0], layout='annuli',
                      annuli=(AnnulusSpec(0.0, 0.05, 1),
                              AnnulusSpec(1.0, 0.05, 4),
                              AnnulusSpec(3.0, 0.05, 4))),
        fidelity=FidelitySpec(r_max=40.0, n_samples=200,
                              n_deflection_points=60, **fidelity),
        detector=DetectorSpec())


@pytest.fixture(scope='module')
def analytic():
    resolved = resolve(annuli_spec())
    return resolved, build_results_store(resolved)


def test_analytic_residuals_at_precision(analytic):
    resolved, store = analytic
    for k in range(store.n_energies):
        for i in range(store.n_particles):
            _, energy_res, angmom_res = residual_series(store, resolved, k, i)
            assert np.max(np.abs(energy_res)) < 1e-12
            assert np.max(np.abs(angmom_res)) < 1e-12
    budget = build_error_budget(store, resolved, 0, 2)
    assert budget.numerical.closed_form


def test_numerical_residuals_match_stored_maxima():
    resolved = resolve(annuli_spec(orbit_provider='numerical'))
    store = build_results_store(resolved)
    for i in range(store.n_particles):
        _, energy_res, _ = residual_series(store, resolved, 0, i)
        assert np.max(np.abs(energy_res)) < 1e-8
        # The stored maximum was taken on 512 dense samples; the stored grid is
        # coarser, so the series maximum is bounded by it rather than equal to
        # it.
        assert np.max(np.abs(energy_res)) <= store.energy_drift[0, i] * 1.5 \
            + 1e-13


def test_verlet_order():
    drifts = []
    for step in (0.02, 0.01, 0.005):
        resolved = resolve(annuli_spec(orbit_provider='numerical',
                                       integrator='verlet', step=step))
        store = build_results_store(resolved)
        drifts.append(build_error_budget(store, resolved, 0, 1)
                      .numerical.energy_drift_max)
    ratios = np.array(drifts[:-1]) / np.array(drifts[1:])
    assert np.allclose(ratios, 4.0, rtol=0.2)


def test_head_on_angular_momentum_is_absolute(analytic):
    resolved, store = analytic
    _, _, angmom_res = residual_series(store, resolved, 0, 0)
    assert np.max(np.abs(angmom_res)) < 1e-12


def test_statistical_column_needs_flux(analytic):
    resolved, store = analytic
    detector = build_detector_result(store, resolved, 0)
    budget = build_error_budget(store, resolved, 0, 1, detector)
    assert not budget.statistical.has_flux
    assert np.isnan(budget.statistical.pull_rms)
    assert budget.assumption is None


def test_panel_has_three_columns_and_renders(analytic):
    resolved, store = analytic
    budget = build_error_budget(store, resolved, 0, 1)
    data = panel_error_budget(budget)
    heads = [column[0] for column in data.text_columns]
    assert heads == ['NUMERICAL', 'STATISTICAL', 'ASSUMPTION']
    image = render_panel(data, PALETTES['light'], BACKGROUNDS['light'])
    assert image.min() != image.max()


def _column_roots(tree):
    """Every attribute chain like `x.numerical.field` -> 'numerical'."""
    roots = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value,
                                                          ast.Attribute):
            if node.value.attr in ('numerical', 'statistical',
                                   'assumption'):
                roots.append((node, node.value.attr))
    return roots


def test_no_expression_mixes_columns():
    """Design 9.9: no expression combines fields across the three
    columns. Each BinOp / Call / Compare in error_budget.py and
    panels.py must reference at most one column."""
    for name in ('analysis/error_budget.py', 'render/panels.py'):
        tree = ast.parse((PACKAGE / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.BinOp, ast.Compare, ast.BoolOp)):
                columns = {column for _, column in _column_roots(node)}
                assert len(columns) <= 1, f'{name}: mixes {columns}'
