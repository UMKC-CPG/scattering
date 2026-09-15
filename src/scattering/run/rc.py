"""The resource-control (rc) settings and where they come from
(pseudocode 10.6, 10.9; ARCHITECTURE 7).

The rc file holds what is MACHINE-DEPENDENT and rarely changed:
the store-size cap, window size, default palette and camera, the glyph radius,
output directory. It never holds physics defaults; those live in the schema
table (`schema.py`), so that a run file is self-contained and reproduces the
same physics on any machine.

The lookup follows the template's XYZrc.py idiom: a `scsimrc.py` in the current
directory first (so a user can drop a modified copy beside their data), then the
directory named by $SCATTERING_RC, then the copy shipped beside the entry-point
script, so that a fresh checkout runs with no setup.

Attribution: this module is part of the scattering teaching tool.
"""

import importlib.util
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RcSettings:
    """Every rc key, with the design 6.4 / 10.6 defaults. The defaults
    here are the fallback of last resort; the shipped scsimrc.py is
    the documented source."""
    max_store_bytes: int = 4_000_000_000
    default_n_azimuth: int = 24
    r_max_safety_factor: float = 3.0
    default_palette: str = 'light'
    default_camera: dict = field(default_factory=lambda: {
        'azimuth_deg': 35.0, 'elevation_deg': 20.0, 'distance': 4.0})
    default_panels: tuple = ('deflection', 'cross_section',
                             'effective_potential', 'telemetry')
    window_size: tuple = (1280, 960)
    glyph_radius: float = 0.02
    output_dir: str = '.'


RC_FILENAME = 'scsimrc.py'


def rc_search_path():
    """The directories searched, in order (pseudocode 10.6)."""
    candidates = [Path.cwd()]
    environment_dir = os.environ.get('SCATTERING_RC')
    if environment_dir:
        candidates.append(Path(environment_dir))
    candidates.append(Path(__file__).resolve().parents[2] / 'scripts')
    return candidates


def load_rc(search_path=None):
    """Find scsimrc.py and build RcSettings from its
    parameters_and_defaults(). Raises if no copy is found."""
    for directory in (search_path or rc_search_path()):
        candidate = Path(directory) / RC_FILENAME
        if candidate.is_file():
            spec = importlib.util.spec_from_file_location('scsimrc',
                                                          candidate)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            values = dict(module.parameters_and_defaults())
            if 'default_panels' in values:
                values['default_panels'] = tuple(values['default_panels'])
            if 'window_size' in values:
                values['window_size'] = tuple(values['window_size'])
            return RcSettings(**values)
    raise FileNotFoundError(f'{RC_FILENAME} not found in any of: '
                            f'{[str(p) for p in rc_search_path()]}')
