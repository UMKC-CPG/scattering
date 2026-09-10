"""Example unit test -- delete once real tests exist.

TEMPLATE: this file exists to show the two conventions the suite
relies on, both of which are load-bearing.

FIRST, a test names the chain section it verifies. The pseudocode
section's "Verification" subsection states the oracle and the
tolerance; the test implements exactly that. Writing the oracle down
first is what makes a test a check rather than a transcript of
whatever the code happened to produce on the day it was written.

SECOND, a numerical tolerance is justified where it is written. An
unexplained tolerance is one that will be quietly loosened the first
time it fails, which is the moment it stops being a test.
"""

import pytest


def test_placeholder_addition():
    """Verifies: pseudocode section 1.2 (`P1.2`).

    Oracle: the closed-form result, which is exact for integers, so
    the comparison is exact rather than approximate.
    """

    assert 1 + 1 == 2


def test_placeholder_tolerance():
    """Verifies: pseudocode section 1.3 (`P1.3`).

    Oracle: an analytic value. The tolerance is set at 1e-12 rather
    than machine epsilon because the algorithm accumulates over a
    few hundred terms, so a handful of ulps of rounding is expected
    and anything larger indicates a real defect.
    """

    computed_value = sum(0.1 for _ in range(10))

    assert computed_value == pytest.approx(1.0, abs=1e-12)
