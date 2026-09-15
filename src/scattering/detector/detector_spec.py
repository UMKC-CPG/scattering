"""The detector layout: bin edges covering exactly the measured
range (pseudocode 7.3, design 7.3-7.4).

A beam of finite b_max produces no scattering below theta_min, and a beam that
excludes the center produces none above theta_head. The bins cover [theta_min,
theta_head] and nothing else, so an angle the experiment could not measure never
acquires a bin whose zero count would assert a cross section of zero (VISION
P15).

Three layouts: log_theta (the default; keeps every bin populated
over a cross section spanning decades), uniform_theta, and equal_solid_angle --
the last a labeled bad example, since for a theta^-4 law it puts nearly every
count in the first bin.

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import dataclass

import numpy as np

LAYOUTS = ('log_theta', 'uniform_theta', 'equal_solid_angle')
MODES = ('asymptotic', 'position')


@dataclass(frozen=True)
class DetectorLayout:
    name: str
    mode: str
    n_bins: int
    n_phi: int
    edges: np.ndarray
    solid_angle: np.ndarray
    theta_min: float
    theta_head: float
    radius: float


def build_layout(spec, theta_min, theta_head, r_detect):
    """Edges for the named layout over the measured range, and the
    solid angle of each bin, eq. (7.1)."""
    if spec.n_phi != 1:
        raise ValueError('azimuthal bins are a future direction (FD4); '
                         'n_phi must be 1')
    if spec.layout not in LAYOUTS:
        raise ValueError(f'unknown detector layout {spec.layout!r}')
    if spec.mode not in MODES:
        raise ValueError(f'unknown detector mode {spec.mode!r}')
    low, high = float(theta_min), float(theta_head)
    if not 0.0 < low < high <= np.pi + 1e-12:
        raise ValueError(f'the measured range [{low}, {high}] is empty')
    high = min(high, np.pi)
    count = int(spec.n_bins)
    if spec.layout == 'log_theta':
        edges = np.geomspace(low, high, count + 1)
    elif spec.layout == 'uniform_theta':
        edges = np.linspace(low, high, count + 1)
    else:
        edges = np.arccos(np.linspace(np.cos(low), np.cos(high),
                                      count + 1))
    solid_angle = 2.0 * np.pi * np.abs(np.cos(edges[:-1])
                                       - np.cos(edges[1:]))
    return DetectorLayout(spec.layout, spec.mode, count, 1, edges,
                          solid_angle, low, high, float(r_detect))
