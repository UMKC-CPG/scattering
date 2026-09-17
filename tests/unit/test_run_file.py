"""Verifies pseudocode section 10 (P10.10): loading, validation,
defaults, overrides, resolution, and write-back of run files."""

import copy
from pathlib import Path

import numpy as np
import pytest

from scattering.run import (RcSettings, RunFileError, build_results_store,
    load_and_resolve, load_run_file, resolve, write_back)
from scattering.run.rc import load_rc
from scattering.run.serialization import (apply_defaults, apply_overrides,
                                          validate)
from scattering.run.run_spec import run_spec_from_raw

REPO = Path(__file__).resolve().parents[2]
EXAMPLES = [REPO / 'runs' / 'rutherford.toml',
            REPO / 'runs' / 'rutherford_disc.toml']
RC = RcSettings()


def prepared(path, overrides=()):
    raw = load_run_file(path)
    raw = apply_overrides(raw, list(overrides))
    return apply_defaults(raw, RC)


@pytest.mark.parametrize('path', EXAMPLES, ids=lambda p: p.stem)
def test_examples_round_trip(path, tmp_path):
    resolved = load_and_resolve(path, rc=RC)
    out = tmp_path / 'resolved.toml'
    write_back(resolved, out)
    again = load_and_resolve(out, rc=RC)
    first, second = resolved.spec, again.spec
    assert np.allclose(first.beam.energies, second.beam.energies)
    assert first.beam.layout == second.beam.layout
    for ring_a, ring_b in zip(first.beam.annuli, second.beam.annuli):
        assert ring_a.impact == pytest.approx(ring_b.impact, rel=1e-12)
        assert ring_a.n_azimuth == ring_b.n_azimuth
    assert first.fidelity.r_max == pytest.approx(second.fidelity.r_max)
    assert first.detector == second.detector
    assert first.inversion == second.inversion
    assert resolved.settings.r_max == pytest.approx(again.settings.r_max)
    assert resolved.scales.length.magnitude == \
        pytest.approx(again.scales.length.magnitude)


def test_unit_conversion_of_an_annulus():
    """An annulus written as "45.5 fm" under alpha_on_gold is b = 1.0
    to the precision of the constants (design 1.5)."""
    raw = prepared(EXAMPLES[0], ['beam.annuli=[{b="45.5 fm", db="1 fm", '
                                 'n_azimuth=4}]'])
    validate(raw)
    resolved = resolve(run_spec_from_raw(raw), RC)
    assert resolved.spec.beam.annuli[0].impact == pytest.approx(1.0,
                                                                 rel=0.002)


def _expect_error(raw, table, key):
    with pytest.raises(RunFileError) as caught:
        validate(raw)
    message = str(caught.value)
    assert f'[{table}]' in message
    if key:
        assert key in message
    return message


def test_unknown_key_with_hint():
    raw = prepared(EXAMPLES[1])
    raw['beam']['n_particle'] = 5
    message = _expect_error(raw, 'beam', 'n_particle')
    assert 'n_particles' in message


def test_unknown_table():
    raw = prepared(EXAMPLES[0])
    raw['bean'] = {}
    _expect_error(raw, 'bean', None)


def test_disc_without_seed():
    raw = prepared(EXAMPLES[1])
    del raw['beam']['seed']
    _expect_error(raw, 'beam', 'seed')


def test_duplicate_energies():
    raw = prepared(EXAMPLES[0])
    raw['beam']['energies'] = ['3 MeV', '3 MeV']
    _expect_error(raw, 'beam', 'energies')


def test_b_min_not_below_b_max():
    raw = prepared(EXAMPLES[1])
    raw['beam']['b_min'] = 12.0
    _expect_error(raw, 'beam', 'b_min')


def test_detector_radius_below_one():
    raw = prepared(EXAMPLES[0])
    raw['detector']['radius'] = 0.5
    _expect_error(raw, 'detector', 'radius')


def test_wrong_dimension():
    raw = prepared(EXAMPLES[0])
    raw['fidelity']['r_max'] = '5 MeV'
    _expect_error(raw, 'fidelity', 'r_max')


def test_mixed_list():
    raw = prepared(EXAMPLES[0])
    raw['beam']['energies'] = ['3 MeV', 5.0]
    _expect_error(raw, 'beam', 'energies')


def test_verlet_needs_step():
    raw = prepared(EXAMPLES[0])
    raw['fidelity']['integrator'] = 'verlet'
    _expect_error(raw, 'fidelity', 'step')


def test_bad_choice():
    raw = prepared(EXAMPLES[0])
    raw['detector']['layout'] = 'log_phi'
    _expect_error(raw, 'detector', 'layout')


def test_newer_schema_refused(tmp_path):
    text = EXAMPLES[0].read_text().replace('schema = 1', 'schema = 99', 1)
    assert 'schema = 99' in text
    path = tmp_path / 'future.toml'
    path.write_text(text)
    with pytest.raises(RunFileError):
        load_run_file(path)


def test_attractive_with_center_refused():
    raw = prepared(EXAMPLES[0], ['potential.sign=-1',
                                 'beam.annuli=[{b=0.0, db=0.05, n_azimuth=1}]'])
    validate(raw)
    with pytest.raises(RunFileError) as caught:
        resolve(run_spec_from_raw(raw), RC)
    assert 'attractive' in str(caught.value)


def test_r_max_safety_factor():
    raw = prepared(EXAMPLES[0], ['fidelity.r_max=5.0'])
    validate(raw)
    with pytest.raises(RunFileError) as caught:
        resolve(run_spec_from_raw(raw), RC)
    assert 'r_max' in str(caught.value)


def test_overrides():
    resolved = load_and_resolve(EXAMPLES[0],
        ['fidelity.n_samples=10', 'beam.energies=["1 MeV"]'], RC)
    assert resolved.spec.fidelity.n_samples == 10
    assert len(resolved.spec.beam.energies) == 1
    with pytest.raises(RunFileError):
        load_and_resolve(EXAMPLES[0], ['nosuch.key=1'], RC)
    with pytest.raises(RunFileError):
        load_and_resolve(EXAMPLES[0], ['fidelity.n_samples'], RC)


def test_view_zone_does_not_change_the_store():
    """Design 10.2: perturb every [view] key and the store is
    bit-identical."""
    base = load_and_resolve(EXAMPLES[0], ['fidelity.n_samples=20'], RC)
    varied = load_and_resolve(
        EXAMPLES[0], ['fidelity.n_samples=20', 'view.palette="dark"',
                      'view.tracked_particle=7',
                      'view.camera={azimuth_deg=0, elevation_deg=90, '
                      'distance=1.5}', 'view.panels=["telemetry"]'], RC)
    first = build_results_store(base)
    second = build_results_store(varied)
    assert np.array_equal(first.position, second.position)
    assert np.array_equal(first.deflection, second.deflection)


def test_load_rc_prefers_cwd(tmp_path, monkeypatch):
    local = tmp_path / 'scsimrc.py'
    local.write_text('def parameters_and_defaults():\n'
                     '    return {"max_store_bytes": 123}\n')
    monkeypatch.chdir(tmp_path)
    assert load_rc().max_store_bytes == 123
    assert load_rc([REPO / 'src' / 'scattering' / 'defaults']).max_store_bytes == \
        4_000_000_000


def test_shipped_rc_loads():
    rc = load_rc([REPO / 'src' / 'scattering' / 'defaults'])
    assert rc.default_palette == 'light'
    assert rc.window_size == (1280, 960)
