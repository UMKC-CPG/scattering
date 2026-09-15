"""Verifies pseudocode section 11.3 and 11.4 (P11.8), the parts that
need no renderer."""

import numpy as np
import pytest

from scattering.geometry import (Ring, Sphere, SphereBand, cone_band,
                                 orbit_plane, probe_depth, annulus_ring)
from scattering.beam.beam_spec import AnnulusSpec
from scattering.potentials import CoulombPotential
from scattering.render.palettes import ROLES
from scattering.render.scene_description import build_frame, build_static
from scattering.run import (DetectorSpec, FidelitySpec, PotentialSpec,
                            RunSpec, build_results_store, resolve)
from scattering.beam.beam_spec import BeamSpec


@pytest.fixture(scope='module')
def run():
    spec = RunSpec(
        potential=PotentialSpec(preset='alpha_on_gold'),
        beam=BeamSpec(energies=['3 MeV', '5 MeV'], layout='annuli',
                      annuli=(AnnulusSpec(0.0, 0.05, 1),
                              AnnulusSpec(1.0, 0.05, 6),
                              AnnulusSpec(3.0, 0.05, 6))),
        fidelity=FidelitySpec(r_max=40.0, n_samples=40,
                              n_deflection_points=80),
        detector=DetectorSpec(radius=2.0))
    resolved = resolve(spec)
    return resolved, build_results_store(resolved)


def test_annulus_ring():
    ring = annulus_ring(AnnulusSpec(1.0, 0.1, 4), 40.0)
    assert isinstance(ring, Ring)
    assert ring.center[2] == -40.0 and ring.inner == 1.0 and ring.outer == 1.1


def test_cone_band_matches_table_and_particles(run):
    resolved, store = run
    k = 0
    _, _, _, maps = store.tables(k)
    for j, ring_map in enumerate(maps):
        band = cone_band(ring_map, resolved.detector_radius)
        assert isinstance(band, SphereBand)
        members = np.nonzero(store.annulus_index == j)[0]
        last = store.frame(k, store.n_samples - 1)[members]
        theta = np.arccos(last[:, 2] / np.linalg.norm(last, axis=1))
        # The landing POSITION differs from the asymptotic direction by asin(b /
        # R_detect) (design 7.2); allow that and a margin.
        slack = 1.5 * np.arcsin(store.impact_parameter[members].max()
                                / resolved.detector_radius) + 1e-9
        assert np.all(theta >= band.theta_1 - slack)
        assert np.all(theta <= band.theta_2 + slack)


def test_probe_depth_is_one_over_energy(run):
    resolved, store = run
    for k, energy in enumerate(store.energies):
        geometry, label = probe_depth(resolved.potential, energy, 0.0)
        assert isinstance(geometry, Sphere)
        assert geometry.radius == pytest.approx(1.0 / energy, rel=1e-9)
        assert label == 'no orbit enters'
    geometry, label = probe_depth(CoulombPotential(-1), 1.0, 0.3)
    assert not isinstance(geometry, Sphere)


def test_orbit_plane_contains_the_orbit(run):
    resolved, store = run
    i = 4
    plane = orbit_plane(store.azimuth[i], 10.0)
    _, positions, _, _, _ = store.particle(0, i)
    assert np.max(np.abs(positions @ plane.normal)) < 1e-10


def test_drawables_are_named_quantities(run):
    resolved, store = run
    static = build_static(store, resolved, 1, 2, 0.02)
    dynamic, telemetry = build_frame(store, resolved, 1, 20, 2, 0.02,
                                     resolved.scales)
    for drawable in static + dynamic:
        assert drawable.quantity and drawable.section
        roles = drawable.role if isinstance(drawable.role, list) \
            else [drawable.role]
        assert all(role in ROLES for role in roles)
        assert drawable.panel == 'scene'
    assert any(d.quantity == 'probe depth' for d in static)
    assert sum(d.quantity == 'cone' for d in static) == 3
    assert len(telemetry.lines()) == 8
    assert telemetry.tracked_index == 2
    assert telemetry.tracked_total_energy == pytest.approx(
        store.energies[1], rel=1e-6)
