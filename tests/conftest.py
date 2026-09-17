"""Shared pytest fixtures and import-path setup.

Putting `src/` on sys.path here means the test suite runs against the working
tree with no install step, which is what you want while developing. An installed
copy is still tested by CI or by running pytest from outside the repository.
"""

import os
import sys

import pytest

# Resolve <repo>/src relative to this file so the suite works no matter which
# directory pytest was invoked from.
_source_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'src'))

if _source_root not in sys.path:
    sys.path.insert(0, _source_root)

# The suite always draws offscreen. Choose VTK's window class now,
# before any test imports the renderer, so that a DISPLAY that is set
# but dead cannot hang a render test (pseudocode 11.6).
from scattering.render.offscreen import prepare_offscreen  # noqa: E402

prepare_offscreen()


@pytest.fixture
def source_root():
    """Absolute path to the `src/` directory.

    Useful for tests that need to locate a script or a data file rather than
    import a module.
    """

    return _source_root


@pytest.fixture
def run_directory(tmp_path, monkeypatch):
    """Run a test inside a fresh temporary working directory.

    Entry-point scripts write into the current directory (the `command` log,
    output files), so a test that exercises one must not run in the repository
    root. Depend on this fixture and the directory is created, switched to, and
    cleaned up automatically.
    """

    monkeypatch.chdir(tmp_path)
    return tmp_path
