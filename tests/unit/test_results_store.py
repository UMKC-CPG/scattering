"""Verifies pseudocode section 6 (P6.6), the store half. Design
section 6. The driver's build is exercised in
tests/integration/test_driver.py."""

import numpy as np
import pytest

from scattering.run.results_store import (FrozenError, ResultsStore,
                                          estimate_bytes)


def test_estimate_matches_design_budget():
    """Design 6.4: K = 5, N = 500, S = 400 is about 65 MB for the
    trajectory block; traces add a bounded amount."""
    trajectory_only = estimate_bytes(5, 500, 400, 0, 0)
    assert 60e6 < trajectory_only < 70e6


def test_frozen_store_refuses_writes():
    store = ResultsStore.allocate(1, 2, 3)
    store.position[:] = 0.0
    store.freeze()
    with pytest.raises(ValueError):
        store.position[0, 0, 0, 0] = 1.0
    with pytest.raises(FrozenError):
        store.energies = np.zeros(1)
    assert store.frozen


def test_batch_mode_has_no_trajectory():
    store = ResultsStore.allocate(2, 10, 0)
    assert store.position is None and store.time_grid is None
    assert store.out_direction.shape == (2, 10, 3)
