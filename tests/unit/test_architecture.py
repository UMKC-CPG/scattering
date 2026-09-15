"""The architectural tests of ARCHITECTURE section 8.6 that can be
checked by reading the source: the import rule (5) and the units boundary (6.6).
The determinism guarantee (3) and the reachability
guarantee (4) are tested where the code they govern lives."""

import ast
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / 'src' / 'scattering'

# Groups that produce physics may not import from presentation or from the sinks
# (ARCHITECTURE 5 and 6.5).
STAGE_GROUPS = ('core', 'potentials', 'beam', 'orbits', 'deflection',
                'detector', 'inversion', 'analysis', 'geometry')
PRESENTATION = ('scattering.render', 'scattering.ui', 'scattering.sinks')

# The detector may not see the potential or the orbits (ARCHITECTURE 6.4): it
# consumes final directions and a bin layout only.
DETECTOR_FORBIDDEN = ('scattering.potentials', 'scattering.orbits',
                      'scattering.beam')


def _imports_of(path):
    tree = ast.parse(path.read_text())
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def _modules_under(group):
    directory = PACKAGE_ROOT / group
    if not directory.is_dir():
        return []
    return sorted(directory.rglob('*.py'))


def test_only_units_module_imports_pint():
    offenders = []
    for path in PACKAGE_ROOT.rglob('*.py'):
        if path.name == 'units.py' and path.parent.name == 'core':
            continue
        if any(name == 'pint' or name.startswith('pint.')
               for name in _imports_of(path)):
            offenders.append(str(path.relative_to(PACKAGE_ROOT)))
    assert offenders == [], f'pint imported outside core/units.py: ' \
                            f'{offenders}'


@pytest.mark.parametrize('group', STAGE_GROUPS)
def test_stage_groups_do_not_import_presentation(group):
    for path in _modules_under(group):
        for name in _imports_of(path):
            assert not name.startswith(PRESENTATION), \
                f'{path.relative_to(PACKAGE_ROOT)} imports {name}'


def test_detector_cannot_see_the_potential():
    for path in _modules_under('detector'):
        for name in _imports_of(path):
            assert not name.startswith(DETECTOR_FORBIDDEN), \
                f'{path.relative_to(PACKAGE_ROOT)} imports {name}'
