"""Verifies pseudocode section 1 (P1.6): scales, presets, the units
boundary. Design section 1."""

import numpy as np
import pytest

from scattering.core.presets import PRESETS
from scattering.core.units import (build_scales, format_natural,
                                   from_natural, quantity, to_natural,
                                   to_natural_list)
from scattering.core import natural_units
from scattering.potentials import CoulombPotential
from scattering.run.run_spec import PotentialSpec


@pytest.fixture
def alpha_scales():
    return build_scales(PotentialSpec(preset='alpha_on_gold'),
                        CoulombPotential(+1), '5 MeV')


def test_alpha_preset_reproduces_design_values(alpha_scales):
    """Design 1.5 quotes kappa ~ 227.6 MeV fm, ell_0 ~ 45.5 fm, and
    v_inf / c ~ 0.052. The 1 % tolerance tests the preset's plumbing
    from scipy.constants, not the constants themselves."""
    kappa = PRESETS['alpha_on_gold'].kappa.to('MeV * fm').magnitude
    assert kappa == pytest.approx(227.6, rel=0.01)
    assert alpha_scales.length.to('fm').magnitude == \
        pytest.approx(45.5, rel=0.01)
    v_inf = (2.0 * alpha_scales.energy / alpha_scales.mass) ** 0.5
    assert v_inf.to('c').magnitude == pytest.approx(0.052, rel=0.02)


def test_interstellar_preset_reproduces_design_values():
    """Design 1.5: ell_0 ~ 2.6 AU and t_0 ~ 250 days for v_inf =
    26 km/s; the mass cancels and a dummy is assigned."""
    scales = build_scales(PotentialSpec(preset='interstellar_visitor'),
                          CoulombPotential(-1), '1 J')
    assert scales.length.to('au').magnitude == pytest.approx(2.6, rel=0.02)
    assert scales.time.to('day').magnitude == pytest.approx(250, rel=0.03)
    assert scales.mass.to('kg').magnitude == pytest.approx(1.0)


def test_speed_scale_is_sqrt_of_energy_over_mass(alpha_scales):
    """Design 1.2: v_0 = sqrt(E_ref / m), so that the natural-unit
    asymptotic speed is sqrt(2 E) -- the convention the Section 2
    closed forms assume, and the one a scratch check found wrong in
    the first draft (design 1.7)."""
    expected = (alpha_scales.energy / alpha_scales.mass) ** 0.5
    assert alpha_scales.speed.to_base_units().magnitude == \
        pytest.approx(expected.to_base_units().magnitude)
    assert natural_units.asymptotic_speed(1.0) == pytest.approx(np.sqrt(2))
    assert natural_units.angular_momentum(2.0, 3.0) == \
        pytest.approx(np.sqrt(4.0) * 3.0)


def test_to_natural_of_reference_length_is_one(alpha_scales):
    fm = alpha_scales.length.to('fm').magnitude
    assert to_natural(f'{fm} fm', 'length', alpha_scales) == \
        pytest.approx(1.0, rel=1e-12)
    assert to_natural(1.0, 'length', alpha_scales) == 1.0


def test_wrong_dimension_names_both(alpha_scales):
    with pytest.raises(ValueError) as caught:
        to_natural('5 MeV', 'length', alpha_scales)
    assert 'length' in str(caught.value)
    assert 'dimension' in str(caught.value)


def test_mixed_list_is_refused(alpha_scales):
    with pytest.raises(ValueError):
        to_natural_list(['1 fm', 2.0], 'length', alpha_scales)


@pytest.mark.parametrize('dimension', ['energy', 'length', 'mass',
                                       'speed', 'time',
                                       'angular_momentum',
                                       'energy*length', 'area'])
def test_round_trip(dimension, alpha_scales):
    """from_natural(to_natural(x)) is the identity to 1e-12."""
    value = 3.7
    back = from_natural(value, dimension, alpha_scales)
    assert to_natural(back, dimension, alpha_scales) == \
        pytest.approx(value, rel=1e-12)


def test_format_natural_uses_display_unit(alpha_scales):
    assert format_natural(1.0, 'length', alpha_scales).endswith('fm')


def test_unknown_preset_is_named():
    with pytest.raises(ValueError) as caught:
        build_scales(PotentialSpec(preset='no_such'), CoulombPotential(+1),
                     '1 MeV')
    assert 'no_such' in str(caught.value)


def test_explicit_kappa_overrides_preset():
    """Design 10.3: an explicit key beside a preset wins -- how a
    student changes Z_2 without editing the preset."""
    doubled = PRESETS['alpha_on_gold'].kappa * 2
    spec = PotentialSpec(preset='alpha_on_gold', kappa=doubled)
    scales = build_scales(spec, CoulombPotential(+1), '5 MeV')
    assert scales.length.to('fm').magnitude == pytest.approx(91.0, rel=0.01)
