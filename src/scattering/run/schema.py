"""The run-file schema as one data table (pseudocode 10.3, design
10.5).

Validation, defaults, the `--set` parser, and write-back all read this table, so
that the four cannot disagree about what a key is called, what it accepts, or
what it defaults to. A `Key` records either a Python type or a physical
dimension (for quantities that may arrive as a bare natural-unit number, a
dimensioned string, or a pint quantity), its default -- a value, None, or the
sentinel "rc" meaning "from the rc file" -- its allowed choices, and whether it
is required unconditionally or only when another key has a given value.

Physics defaults live HERE and nowhere else (ARCHITECTURE 7); the rc file holds
only machine-local settings.

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import dataclass, field
from typing import Optional

KNOWN_SCHEMA = 1

# Tables in the presentation zone: perturbing them must leave every computed
# result bit-identical (design 10.2).
PRESENTATION_TABLES = {'view'}

# The sentinel for "the default comes from the rc file".
FROM_RC = 'rc'


@dataclass(frozen=True)
class Key:
    """One schema entry. Exactly one of `type` and `quantity` is
    set; `table_list` describes a list of inline tables (the annuli)
    by its own sub-schema."""
    type: Optional[type] = None
    quantity: Optional[str] = None
    list: bool = False
    table_list: Optional[dict] = None
    default: object = None
    required: bool = False
    required_if: Optional[tuple] = None
    choices: Optional[tuple] = None
    section: str = ''


SCHEMA = {
    'potential': {
        'kind': Key(type=str, choices=('coulomb',), required=True,
                    section='2'),
        'preset': Key(type=str, section='1.5'),
        'sign': Key(type=int, choices=(1, -1), section='2'),
        'kappa': Key(quantity='energy*length', section='1.5'),
        'mass': Key(quantity='mass', section='1.5'),
        'reference_energy': Key(quantity='energy', section='1.2'),
        'reference_length': Key(quantity='length', section='1.3'),
    },
    'beam': {
        'energies': Key(quantity='energy', list=True, required=True,
                        section='3.2'),
        'energy_distribution': Key(type=str, choices=('delta',),
                                   default='delta', section='3.2'),
        'layout': Key(type=str, choices=('annuli', 'disc'), required=True,
                      section='3.3'),
        'annuli': Key(table_list={
                          'b': Key(quantity='length', required=True),
                          'db': Key(quantity='length', required=True),
                          'n_azimuth': Key(type=int, default=FROM_RC)},
                      required_if=('layout', 'annuli'), section='3.3'),
        'n_particles': Key(type=int, required_if=('layout', 'disc'),
                           section='3.3'),
        'b_min': Key(quantity='length', default=0.0, section='3.3'),
        'b_max': Key(quantity='length', required_if=('layout', 'disc'),
                     section='3.3'),
        'stratify': Key(type=bool, default=False, section='3.3'),
        'seed': Key(type=int, required_if=('layout', 'disc'),
                    section='3.5'),
    },
    'detector': {
        'radius': Key(type=float, default=2.0, section='7.2'),
        'mode': Key(type=str, choices=('asymptotic', 'position'),
                    default='asymptotic', section='7.2'),
        'layout': Key(type=str, choices=('log_theta', 'uniform_theta',
                                         'equal_solid_angle'),
                      default='log_theta', section='7.4'),
        'n_bins': Key(type=int, default=40, section='7.4'),
        'n_phi': Key(type=int, default=1, section='7.2'),
    },
    'inversion': {
        'enabled': Key(type=bool, section='8'),      # default: disc
        'assume_sign': Key(type=int, choices=(1, -1), default=1,
                           section='8.3'),
        'tail_model': Key(type=str, choices=('coulomb', 'power', 'zero'),
                          default='coulomb', section='8.5'),
        'n_resample': Key(type=int, default=50, section='8.7'),
    },
    'fidelity': {
        'orbit_provider': Key(type=str,
            choices=('auto', 'analytic', 'numerical'), default='auto',
            section='4.2'),
        'integrator': Key(type=str, choices=('dop853', 'rk45', 'verlet'),
                          default='dop853', section='4.9'),
        'rtol': Key(type=float, default=1e-10, section='4.9'),
        'atol': Key(type=float, default=1e-12, section='4.9'),
        'step': Key(type=float, required_if=('integrator', 'verlet'),
                    section='4.9'),
        'r_max': Key(quantity='length', required=True, section='4.4'),
        'asymptote_tolerance': Key(type=float, default=1e-6,
                                   section='4.4'),
        'n_samples': Key(type=int, default=400, section='6.2'),
        'trace_angle_deg': Key(type=float, default=2.0, section='4.10'),
        'trace_points_max': Key(type=int, default=2000, section='4.10'),
        'n_deflection_points': Key(type=int, default=400, section='5.4'),
    },
    'view': {
        'palette': Key(type=str, choices=('light', 'dark', 'colorblind'),
                       default=FROM_RC, section='11'),
        'camera': Key(type=dict, default=FROM_RC, section='11'),
        'tracked_particle': Key(type=int, default=0, section='12'),
        'panels': Key(type=str, list=True, default=FROM_RC, section='11'),
    },
    'meta': {
        'resolved_by': Key(type=str),
        'source': Key(type=str),
        'git_commit': Key(type=str),
    },
}
