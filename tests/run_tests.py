#!/usr/bin/env python3

"""Run the test suite via pytest.

A convenience wrapper so the suite can be run without remembering pytest's
arguments. Any extra arguments are passed straight through, so
`./tests/run_tests.py -k orientation -x` works as expected.
"""

import os
import sys

import pytest

if __name__ == '__main__':
    sys.exit(pytest.main(
        [os.path.dirname(os.path.abspath(__file__)), '-v']
        + sys.argv[1:]))
