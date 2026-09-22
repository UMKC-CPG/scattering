"""Verifies pseudocode 11.4's additions: the glyph radius as a fraction
of R_max, ring and band selection, the ring legend, and the panel
windows' offscreen path (design 11.6, 11.10, 11.11)."""

import numpy as np
import pytest

from scattering.beam.beam_spec import AnnulusSpec, BeamSpec
from scattering.render.palettes import BACKGROUNDS, PALETTES
from scattering.render.panel_windows import PanelWindows
from scattering.render.panels import build_panel, render_panel
from scattering.render.scene_description import (band_index, build_frame,
    build_static, glyph_radius, ring_bands, ring_legend_lines,
    shown_particles)
from scattering.run import (DetectorSpec, FidelitySpec, PotentialSpec,
    RcSettings, RunSpec, build_results_store, resolve)


def _run(layout):
    if layout == 'annuli':
        beam = BeamSpec(energies=['3 MeV', '5 MeV'], layout='annuli',
                        annuli=(AnnulusSpec(0.5, 0.05, 6),
                                AnnulusSpec(2.0, 0.05, 6),
                                AnnulusSpec(4.0, 0.05, 6)))
    else:
        beam = BeamSpec(energies=['5 MeV'], layout='disc', n_particles=50,
                        b_min=0.2, b_max=4.0, seed=7)
    spec = RunSpec(potential=PotentialSpec(preset='alpha_on_gold'),
                   beam=beam,
                   fidelity=FidelitySpec(r_max=40.0, n_samples=20,
                                         n_deflection_points=60),
                   detector=DetectorSpec(radius=2.0))
    resolved = resolve(spec)
    return resolved, build_results_store(resolved)


@pytest.fixture(scope='module')
def annuli():
    return _run('annuli')


@pytest.fixture(scope='module')
def disc():
    return _run('disc')


def test_glyph_radius_is_a_fraction_of_r_max(annuli):
    resolved, _ = annuli
    rc = RcSettings()
    glyph = glyph_radius(resolved, rc)
    assert glyph == rc.glyph_radius_fraction * resolved.settings.r_max
    assert glyph >= 4 * resolved.settings.r_max / 200      # visible


def test_shown_particles(annuli):
    resolved, store = annuli
    n = store.n_particles
    assert list(shown_particles(store, frozenset(), 4)) == list(range(n))
    only_tracked = shown_particles(store, frozenset(range(3)), 7)
    assert list(only_tracked) == [7]
    without_ring_1 = shown_particles(store, frozenset({1}), 0)
    assert set(without_ring_1) == {i for i in range(n)
                                   if store.annulus_index[i] != 1}


def test_disc_bands_are_equal_count(disc):
    resolved, store = disc
    bands = band_index(store)
    counts = np.bincount(bands, minlength=8)
    assert counts.max() - counts.min() <= 1
    # Bands are ordered by impact parameter and do not overlap.
    edges = ring_bands(store, resolved)
    assert len(edges) == 8
    for (low, width), (next_low, _) in zip(edges, edges[1:]):
        assert low + width <= next_low + 1e-12


def test_ring_legend_matches_the_cones(annuli):
    resolved, store = annuli
    lines = ring_legend_lines(store, resolved, 1, frozenset({2}))
    assert len(lines) == 3
    assert lines[2].endswith('hidden') and 'hidden' not in lines[0]
    maps = store.tables(1)[3]
    for line, ring_map in zip(lines, maps):
        low = np.degrees(min(ring_map.theta_1, ring_map.theta_2))
        assert f'{low:.1f}' in line
        assert '6 particles' in line


def test_hidden_ring_leaves_the_static_scene(annuli):
    resolved, store = annuli
    shown = build_static(store, resolved, 0, 0, 0.24)
    fewer = build_static(store, resolved, 0, 0, 0.24,
                         hidden_rings=frozenset({1}))
    rings = [d for d in shown if d.quantity == 'annulus']
    rings_fewer = [d for d in fewer if d.quantity == 'annulus']
    assert len(rings) == 3 and len(rings_fewer) == 2
    traces = [d for d in fewer if d.quantity == 'trace']
    assert len(traces) == 12                       # 18 minus ring 1's 6
    frame, _ = build_frame(store, resolved, 0, 5, 0, 0.24, resolved.scales,
                           hidden_rings=frozenset(range(3)))
    particles = [d for d in frame if d.quantity == 'particles'][0]
    assert len(particles.geometry.positions) == 1  # the tracked one


def test_panel_windows_offscreen_redraws_only_on_a_new_key(annuli):
    resolved, store = annuli
    palette, background = PALETTES['light'], BACKGROUNDS['light']
    windows = PanelWindows(['deflection', 'telemetry'], palette,
                           background, offscreen=True)
    assert not windows.interactive and windows.names == ['deflection']
    data = build_panel('deflection', store, resolved, 0, 0, False)
    windows.update('deflection', data, key=('a',))
    windows.update('deflection', data, key=('a',))
    assert windows.draw_count == 1
    windows.update('deflection', data, key=('b',))
    assert windows.draw_count == 2
    image = windows.image('deflection', data)
    assert np.array_equal(image, render_panel(data, palette, background))
    assert image.min() != image.max()
    windows.close()
