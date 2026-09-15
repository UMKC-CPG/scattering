"""The run specification records and their resolution (pseudocode
10.1, 10.7; design 10).

`RunSpec` is the run file as loaded: every table a record, every physical
quantity AS WRITTEN -- a bare natural-unit number, a dimensioned string such as
"5 MeV", or a pint quantity. `resolve` turns it into a `ResolvedRun`: the
potential built, the reference scales fixed, every quantity converted to natural
units once, the orbit settings assembled, and the memory budget checked. The
driver consumes only a `ResolvedRun`, so nothing below this module ever sees a
pint object (ARCHITECTURE 6.6).

A `RunSpec` may come from a TOML file (`serialization.py`) or be built directly
in code, which is what the tests do.

Attribution: this module is part of the scattering teaching tool.
"""

import datetime
import subprocess
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

import numpy as np

from scattering.beam.beam_spec import AnnulusSpec, BeamSpec
from scattering.core.units import (build_scales, to_natural,
                                   to_natural_list)
from scattering.orbits.orbit_provider import OrbitSettings
from scattering.potentials import make_potential
from scattering.run.rc import RcSettings
from scattering.run.results_store import estimate_bytes

TOOL_VERSION = '0.6'


class RunFileError(ValueError):
    """A run-file problem, naming the table, the key, and the design
    section that explains the rule (pseudocode 10.5)."""

    def __init__(self, table, key, message, section=''):
        where = f'[{table}]' + (f'.{key}' if key else '')
        suffix = f' (design {section})' if section else ''
        super().__init__(f'{where}: {message}{suffix}')
        self.table, self.key, self.section = table, key, section


@dataclass(frozen=True)
class PotentialSpec:
    """The [potential] table. `sign` of None means 'from the preset'.
    Quantity fields are pint quantities or None."""
    kind: str = 'coulomb'
    sign: Optional[int] = None
    preset: Optional[str] = None
    kappa: object = None
    mass: object = None
    reference_energy: object = None
    reference_length: object = None


@dataclass(frozen=True)
class DetectorSpec:
    """The [detector] table (design 7)."""
    radius: float = 2.0
    mode: str = 'asymptotic'
    layout: str = 'log_theta'
    n_bins: int = 40
    n_phi: int = 1


@dataclass(frozen=True)
class InversionSpec:
    """The [inversion] table (design 8)."""
    enabled: bool = False
    assume_sign: int = 1
    tail_model: str = 'coulomb'
    n_resample: int = 50


@dataclass(frozen=True)
class ViewSpec:
    """The [view] table: the presentation zone (design 10.2)."""
    palette: str = 'light'
    camera: dict = field(default_factory=lambda: {
        'azimuth_deg': 35.0, 'elevation_deg': 20.0, 'distance': 4.0})
    tracked_particle: int = 0
    panels: tuple = ('deflection', 'cross_section', 'effective_potential',
                     'error_budget', 'telemetry')


@dataclass(frozen=True)
class MetaSpec:
    """The [meta] table, written by resolve and ignored on load."""
    resolved_by: Optional[str] = None
    source: Optional[str] = None
    git_commit: Optional[str] = None


@dataclass(frozen=True)
class FidelitySpec:
    """The [fidelity] table (design 10.5). `r_max` may arrive as
    loaded, like the beam's lengths."""
    r_max: object
    orbit_provider: str = 'auto'
    integrator: str = 'dop853'
    rtol: float = 1e-10
    atol: float = 1e-12
    step: Optional[float] = None
    asymptote_tolerance: float = 1e-6
    n_samples: int = 400
    trace_angle_deg: float = 2.0
    trace_points_max: int = 2000
    n_deflection_points: int = 400


@dataclass(frozen=True)
class RunSpec:
    """The whole run file, as loaded (pseudocode 10.1)."""
    potential: PotentialSpec
    beam: BeamSpec
    fidelity: FidelitySpec
    detector: DetectorSpec = field(default_factory=DetectorSpec)
    inversion: InversionSpec = field(default_factory=InversionSpec)
    view: ViewSpec = field(default_factory=ViewSpec)
    meta: Optional[MetaSpec] = None
    schema: int = 1


@dataclass(frozen=True)
class ResolvedRun:
    """What the driver consumes (pseudocode 10.1): the spec with every
    quantity in natural units, plus the objects derived from it."""
    spec: RunSpec
    potential: object
    scales: object
    settings: OrbitSettings
    detector_radius: float
    estimate_bytes: int


def resolve_beam_units(beam_spec, scales):
    """Convert every dimensioned quantity of a BeamSpec to natural
    units, once (pseudocode 6.4, 10.7). Bare numbers pass through."""
    energies = to_natural_list(list(beam_spec.energies), 'energy', scales)
    annuli = tuple(AnnulusSpec(to_natural(ring.impact, 'length', scales),
                               to_natural(ring.width, 'length', scales),
                               int(ring.n_azimuth))
                   for ring in beam_spec.annuli)
    return BeamSpec(energies, beam_spec.layout, annuli, beam_spec.n_particles,
        to_natural(beam_spec.b_min, 'length', scales),
        to_natural(beam_spec.b_max, 'length', scales), beam_spec.stratify,
        beam_spec.seed, beam_spec.distribution)


def resolve(spec, rc=None):
    """Build the ResolvedRun (pseudocode 10.7).

    The two validation rules that need the potential and the scales
    are checked here: the beam may reach b = 0 only if the potential
    admits it (design 3.4), and r_max must exceed the beam's largest impact
    parameter by the rc safety factor (design 10.6). The memory budget is
    checked here too, so that a run is refused before anything is computed
    (design 6.4).
    """
    rc = rc or RcSettings()
    potential = make_potential(spec.potential)
    scales = build_scales(spec.potential, potential, spec.beam.energies[0])
    beam_spec = resolve_beam_units(spec.beam, scales)
    r_max = to_natural(spec.fidelity.r_max, 'length', scales)

    if not potential.admits_center() and beam_spec.smallest_impact() == 0:
        key = 'annuli' if beam_spec.layout == 'annuli' else 'b_min'
        raise RunFileError('beam', key, f'b = 0 is not an orbit for '
                           f'{potential.describe()}', '3.4')
    largest = beam_spec.largest_impact()
    if r_max < rc.r_max_safety_factor * largest:
        raise RunFileError('fidelity', 'r_max',
                           f'must be at least {rc.r_max_safety_factor} x '
                           f'the largest impact parameter ({largest:.3g}); '
                           f'got {r_max:.3g}', '10.6')

    fidelity = spec.fidelity
    settings = OrbitSettings(r_max=r_max, integrator=fidelity.integrator,
        rtol=fidelity.rtol, atol=fidelity.atol, step=fidelity.step,
        asymptote_tolerance=fidelity.asymptote_tolerance,
        trace_angle=np.radians(fidelity.trace_angle_deg),
        trace_points_max=fidelity.trace_points_max,
        orbit_provider=fidelity.orbit_provider, entry_plane_z=r_max)
    estimate = estimate_bytes(len(beam_spec.energies),
        beam_spec.n_particles_total(), fidelity.n_samples,
        fidelity.trace_points_max, fidelity.n_deflection_points)
    if estimate > rc.max_store_bytes:
        raise MemoryError(
            f'estimated results store of {estimate / 1e9:.2f} GB exceeds '
            f'max_store_bytes = {rc.max_store_bytes / 1e9:.2f} GB; lower '
            f'n_samples, n_particles, or the number of energies, or '
            f'raise the cap in the rc file')

    meta = MetaSpec(
        resolved_by=f'scattering {TOOL_VERSION} on '
                    f'{datetime.datetime.now().isoformat(timespec="seconds")}',
        source=spec.meta.source if spec.meta else None,
        git_commit=git_commit())
    resolved_spec = replace(spec, beam=beam_spec,
        fidelity=replace(fidelity, r_max=r_max), meta=meta)
    return ResolvedRun(resolved_spec, potential, scales, settings,
                       spec.detector.radius * r_max, int(estimate))


def run_spec_from_raw(raw):
    """Map validated, defaulted TOML tables onto the records
    (pseudocode 10.8). Quantity strings stay strings; `resolve`
    converts them."""
    potential = raw['potential']
    beam = raw['beam']
    annuli = tuple(AnnulusSpec(ring['b'], ring['db'], int(ring['n_azimuth']))
                   for ring in beam.get('annuli', []))
    energies = beam['energies']
    if not isinstance(energies, list):
        energies = [energies]
    beam_spec = BeamSpec(energies=energies, layout=beam['layout'],
        annuli=annuli, n_particles=int(beam.get('n_particles', 0)),
        b_min=beam.get('b_min', 0.0), b_max=beam.get('b_max', 0.0),
        stratify=bool(beam.get('stratify', False)), seed=beam.get('seed'),
        distribution=beam['energy_distribution'])
    view = raw['view']
    meta = raw.get('meta') or {}
    return RunSpec(
        potential=PotentialSpec(**potential),
        beam=beam_spec,
        fidelity=FidelitySpec(**raw['fidelity']),
        detector=DetectorSpec(**raw['detector']),
        inversion=InversionSpec(**raw['inversion']),
        view=ViewSpec(palette=view['palette'], camera=dict(view['camera']),
                      tracked_particle=int(view['tracked_particle']),
                      panels=tuple(view['panels'])),
        meta=MetaSpec(**meta) if meta else None,
        schema=int(raw.get('schema', 1)))


def git_commit():
    """The source tree's commit and whether it was dirty, or None if
    git is unavailable; provenance, not a dependency."""
    root = Path(__file__).resolve().parents[3]
    try:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root,
            capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(['git', 'status', '--porcelain'], cwd=root,
            capture_output=True, text=True, check=True).stdout.strip() != ''
        return commit + ('-dirty' if dirty else '')
    except (OSError, subprocess.CalledProcessError):
        return None
