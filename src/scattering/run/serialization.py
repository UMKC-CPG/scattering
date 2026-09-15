"""Loading, validating, defaulting, overriding, and writing back run
files (pseudocode 10.4-10.6, 10.8; design 10).

The pipeline from a path to a ResolvedRun is

    load_run_file -> apply_overrides -> apply_defaults -> validate
                  -> run_spec_from_raw -> resolve

and every step reads the one schema table. Overrides from the command line are
applied BEFORE defaults and validation, so that an override is checked exactly
like a value in the file. Unknown keys are errors, not warnings: a misspelled
key that silently fell back to a default is precisely the failure the run file
exists to prevent (design 10.6).

Attribution: this module is part of the scattering teaching tool.
"""

import difflib
import warnings
from dataclasses import asdict
from pathlib import Path

import numpy as np

try:
    import tomllib
except ImportError:                       # Python 3.10
    import tomli as tomllib
import tomli_w

from scattering.core.units import (ReferenceScales, is_bare, quantity,
                                   to_natural)
from scattering.run.rc import RcSettings, load_rc
from scattering.run.run_spec import (ResolvedRun, RunFileError,
                                     resolve, run_spec_from_raw)
from scattering.run.schema import FROM_RC, KNOWN_SCHEMA, SCHEMA

# A throwaway set of SI scales for dimension checks at validation: to_natural
# raises on a mismatch whatever the scales are, and the real conversion waits
# for resolve (pseudocode 10.5).
_SI_SCALES = ReferenceScales(mass=quantity(1.0, 'kg'),
    energy=quantity(1.0, 'J'), length=quantity(1.0, 'm'),
    speed=quantity(1.0, 'm/s'), time=quantity(1.0, 's'),
    angular_momentum=quantity(1.0, 'kg*m^2/s'), display_units={})


def load_run_file(path):
    """Read TOML and settle the schema version (pseudocode 10.4)."""
    raw = tomllib.loads(Path(path).read_text())
    if 'schema' not in raw:
        warnings.warn(f'{path}: no schema key; assuming {KNOWN_SCHEMA}')
        raw['schema'] = KNOWN_SCHEMA
    if raw['schema'] > KNOWN_SCHEMA:
        raise RunFileError('schema', None,
                           f'run file schema {raw["schema"]} is newer than '
                           f'this tool understands ({KNOWN_SCHEMA})')
    return raw


def parse_value(text, key_spec):
    """Parse a `--set` value with TOML syntax, so that strings and
    lists are written the same way as in the file."""
    try:
        return tomllib.loads(f'v = {text}')['v']
    except tomllib.TOMLDecodeError as problem:
        raise RunFileError('', None, f'cannot parse {text!r} as a TOML '
                           f'value: {problem}') from None


def apply_overrides(raw, overrides):
    """Apply `table.key=value` strings (pseudocode 10.6)."""
    for text in overrides:
        if '=' not in text or '.' not in text.split('=', 1)[0]:
            raise RunFileError('', None, f'--set expects TABLE.KEY=VALUE, '
                               f'got {text!r}')
        path, value_text = text.split('=', 1)
        table, key = path.split('.', 1)
        if table not in SCHEMA or key not in SCHEMA[table]:
            raise RunFileError(table, key, 'unknown key in --set', '10.6')
        raw.setdefault(table, {})[key] = parse_value(value_text,
                                                     SCHEMA[table][key])
    return raw


def apply_defaults(raw, rc):
    """Fill every absent key that has a default (pseudocode 10.6)."""
    rc_values = {
        ('beam', 'annuli', 'n_azimuth'): rc.default_n_azimuth,
        ('view', 'palette'): rc.default_palette,
        ('view', 'camera'): dict(rc.default_camera),
        ('view', 'panels'): list(rc.default_panels),
    }
    for table, keys in SCHEMA.items():
        raw.setdefault(table, {})
        for key, spec in keys.items():
            if key in raw[table] or spec.default is None:
                continue
            raw[table][key] = rc_values[(table, key)] \
                if spec.default == FROM_RC else spec.default
    raw['inversion'].setdefault('enabled', raw['beam'].get('layout')
                                == 'disc')
    for ring in raw['beam'].get('annuli', []):
        ring.setdefault('n_azimuth', rc_values[('beam', 'annuli',
                                                'n_azimuth')])
    return raw


def _check_value(table, key, value, spec):
    """Type or dimension check for one key (pseudocode 10.5)."""
    if spec.quantity is not None:
        values = value if isinstance(value, list) else [value]
        if spec.list and not isinstance(value, list):
            raise RunFileError(table, key, 'expected a list', spec.section)
        kinds = {is_bare(v) for v in values}
        if len(kinds) > 1:
            raise RunFileError(table, key, 'mixed bare and dimensioned '
                               'values', '10.3')
        for item in values:
            if isinstance(item, bool):
                raise RunFileError(table, key, 'expected a quantity',
                                   spec.section)
            try:
                to_natural(item, spec.quantity, _SI_SCALES)
            except (ValueError, TypeError) as problem:
                raise RunFileError(table, key, str(problem),
                                   spec.section) from None
        return
    if spec.table_list is not None:
        if not isinstance(value, list):
            raise RunFileError(table, key, 'expected a list of tables',
                               spec.section)
        for ring in value:
            for sub_key in ring:
                if sub_key not in spec.table_list:
                    raise RunFileError(table, f'{key}.{sub_key}',
                                       'unknown key', '10.6')
            for sub_key, sub_spec in spec.table_list.items():
                if sub_spec.required and sub_key not in ring:
                    raise RunFileError(table, f'{key}.{sub_key}',
                                       'required', spec.section)
                if sub_key in ring:
                    _check_value(table, f'{key}.{sub_key}', ring[sub_key],
                                 sub_spec)
        return
    expected = spec.type
    if spec.list:
        if not isinstance(value, list) or not all(
                isinstance(v, expected) for v in value):
            raise RunFileError(table, key, f'expected a list of '
                               f'{expected.__name__}', spec.section)
        return
    if expected is float:
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif expected is int:
        ok = isinstance(value, int) and not isinstance(value, bool)
    else:
        ok = isinstance(value, expected)
    if not ok:
        raise RunFileError(table, key, f'expected {expected.__name__}, got '
                           f'{type(value).__name__} {value!r}', spec.section)
    if spec.choices is not None and value not in spec.choices:
        raise RunFileError(table, key, f'one of {list(spec.choices)}, got '
                           f'{value!r}', spec.section)


def validate(raw):
    """Every rule of design 10.6 that needs no potential or scales;
    nothing is coerced (pseudocode 10.5)."""
    for table in raw:
        if table == 'schema':
            continue
        if table not in SCHEMA:
            raise RunFileError(table, None, 'unknown table', '10.6')
        for key in raw[table]:
            if key not in SCHEMA[table]:
                hint = difflib.get_close_matches(key, SCHEMA[table], n=1)
                message = 'unknown key' + (f'; did you mean {hint[0]!r}?'
                                           if hint else '')
                raise RunFileError(table, key, message, '10.6')
    for table, keys in SCHEMA.items():
        present_table = raw.get(table, {})
        for key, spec in keys.items():
            present = key in present_table
            if spec.required and not present:
                raise RunFileError(table, key, 'required', spec.section)
            if spec.required_if and not present:
                other, value = spec.required_if
                if present_table.get(other) == value:
                    raise RunFileError(table, key, f'required when {other} '
                                       f'= {value!r}', spec.section)
            if present:
                _check_value(table, key, present_table[key], spec)

    beam = raw['beam']
    energies = beam['energies']
    if not isinstance(energies, list):
        energies = [energies]
    if not energies or len({str(e) for e in energies}) < len(energies):
        raise RunFileError('beam', 'energies', 'non-empty, no duplicates',
                           '3.2')
    if beam['layout'] == 'disc':
        b_min, b_max = beam.get('b_min', 0.0), beam['b_max']
        if is_bare(b_min) and is_bare(b_max) and not 0 <= b_min < b_max:
            raise RunFileError('beam', 'b_min', '0 <= b_min < b_max', '3.3')
        if beam['n_particles'] < 1:
            raise RunFileError('beam', 'n_particles', '>= 1', '3.3')
    else:
        if not beam.get('annuli'):
            raise RunFileError('beam', 'annuli', 'at least one ring', '3.3')
        for ring in beam['annuli']:
            if (is_bare(ring['b']) and ring['b'] < 0) or \
                    (is_bare(ring['db']) and ring['db'] <= 0) or \
                    ring['n_azimuth'] < 1:
                raise RunFileError('beam', 'annuli',
                                   'b >= 0, db > 0, n_azimuth >= 1', '3.3')
    if raw['detector']['radius'] < 1.0:
        raise RunFileError('detector', 'radius', '>= 1, in units of r_max',
                           '7.2')
    if raw['detector']['n_bins'] < 2:
        raise RunFileError('detector', 'n_bins', '>= 2', '7.4')


def load_and_resolve(path, overrides=(), rc=None):
    """Path to ResolvedRun (pseudocode 10.8)."""
    rc = rc or load_rc()
    raw = load_run_file(path)
    raw = apply_overrides(raw, list(overrides))
    raw = apply_defaults(raw, rc)
    validate(raw)
    spec = run_spec_from_raw(raw)
    from dataclasses import replace
    from scattering.run.run_spec import MetaSpec
    spec = replace(spec, meta=MetaSpec(source=str(path)))
    return resolve(spec, rc)


def _plain(value):
    """TOML-writable form of a resolved value."""
    if isinstance(value, np.ndarray):
        return [float(v) for v in value]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, tuple):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def resolved_to_tables(resolved):
    """The resolved spec as ordered TOML tables, every schema key
    present, natural-unit numbers bare (pseudocode 10.8)."""
    spec = resolved.spec
    tables = {'schema': KNOWN_SCHEMA}
    potential = {k: _plain(v) for k, v in asdict(spec.potential).items()
                 if v is not None and not hasattr(v, 'magnitude')}
    for name in ('kappa', 'mass', 'reference_energy', 'reference_length'):
        value = getattr(spec.potential, name)
        if value is not None:
            potential[name] = f'{value:~}'
    tables['potential'] = potential
    beam = spec.beam
    beam_table = {'energies': _plain(beam.energies),
                  'energy_distribution': beam.distribution,
                  'layout': beam.layout}
    if beam.layout == 'annuli':
        beam_table['annuli'] = [{'b': float(r.impact), 'db': float(r.width),
                                 'n_azimuth': int(r.n_azimuth)}
                                for r in beam.annuli]
    else:
        beam_table.update(n_particles=int(beam.n_particles),
            b_min=float(beam.b_min), b_max=float(beam.b_max),
            stratify=bool(beam.stratify), seed=int(beam.seed))
    tables['beam'] = beam_table
    tables['detector'] = _plain(asdict(spec.detector))
    tables['inversion'] = _plain(asdict(spec.inversion))
    fidelity = {k: _plain(v) for k, v in asdict(spec.fidelity).items()
                if v is not None}
    tables['fidelity'] = fidelity
    tables['view'] = _plain(asdict(spec.view))
    if spec.meta:
        tables['meta'] = {k: v for k, v in asdict(spec.meta).items()
                          if v is not None}
    return tables


def write_back(resolved, path):
    """Write the resolved specification as TOML with a comment header
    (pseudocode 10.8). A resolved file round-trips exactly, since its
    bare numbers pass through `to_natural` unchanged."""
    meta = resolved.spec.meta
    header = (f'# Resolved run file: {meta.resolved_by if meta else ""}\n'
              f'# Source: {meta.source if meta and meta.source else "-"}\n'
              f'# Every quantity below is in natural units '
              f'(design section 1).\n\n')
    Path(path).write_text(header + tomli_w.dumps(resolved_to_tables(
        resolved)))
