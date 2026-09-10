"""The run specification records the driver consumes (pseudocode
6.3).

Pseudocode section 10 owns the run FILE: its schema, loading,
validation, defaults, and write-back. These records fix only the
shape the driver needs, so that v0.5 can build a run in code and
tests, and so that section 10 has a target to populate. The seam
is recorded in pseudocode 6.3: the quantities in `BeamSpec` may
arrive as loaded (pint quantities, dimensioned strings, or bare
natural-unit numbers) and the driver converts them once; when
section 10 arrives, that conversion moves into its resolution step.

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import dataclass
from typing import Optional

from scattering.beam.beam_spec import BeamSpec


@dataclass(frozen=True)
class PotentialSpec:
    """The [potential] table. `sign` of None means 'from the preset'.
    The quantity fields are pint quantities or None; a bare number
    is not meaningful for them (they set the scales)."""
    kind: str = 'coulomb'
    sign: Optional[int] = None
    preset: Optional[str] = None
    kappa: object = None
    mass: object = None
    reference_energy: object = None
    reference_length: object = None


@dataclass(frozen=True)
class FidelitySpec:
    """The [fidelity] table (design 10.5), natural units where
    dimensioned. `r_max` may arrive as loaded, like the beam's
    lengths."""
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
    """Everything the driver needs (pseudocode 6.3)."""
    potential: PotentialSpec
    beam: BeamSpec
    fidelity: FidelitySpec
    detector_radius: float = 2.0


@dataclass(frozen=True)
class RcSettings:
    """Machine-local settings (pseudocode 6.3). The default store cap
    is the design 6.4 value."""
    max_store_bytes: int = 4_000_000_000
