"""Verifies pseudocode section 11.5: every role in every palette, and
the redundancy rule (design 11.5)."""

import pytest

from scattering.render.palettes import (PALETTES, ROLES, check_redundancy,
                                        resolve_encoding)


@pytest.mark.parametrize('name', sorted(PALETTES))
def test_every_role_in_every_palette(name):
    for role in ROLES:
        encoding = resolve_encoding(name, role)
        assert len(encoding.color) == 3
        assert all(0.0 <= c <= 1.0 for c in encoding.color)


@pytest.mark.parametrize('name', sorted(PALETTES))
def test_redundancy_rule(name):
    assert check_redundancy(name) == []
