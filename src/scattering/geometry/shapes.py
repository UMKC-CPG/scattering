"""The geometry kinds a drawable may carry (pseudocode 11.2): plain
records of numpy arrays in scene coordinates, with no notion of color or of any
graphics library. The renderer turns each kind into an actor; nothing else needs
to know how.

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Points:
    positions: np.ndarray      # (n, 3)
    radius: float              # display radius, a labeled convention


@dataclass(frozen=True)
class Polyline:
    points: np.ndarray         # (n, 3)
    closed: bool = False


@dataclass(frozen=True)
class Ring:
    """A flat annulus."""
    center: np.ndarray
    normal: np.ndarray
    inner: float
    outer: float


@dataclass(frozen=True)
class SphereBand:
    """The band of a sphere between two polar angles (from +z)."""
    center: np.ndarray
    radius: float
    theta_1: float
    theta_2: float
    azimuth_range: tuple = (0.0, 2.0 * np.pi)


@dataclass(frozen=True)
class Sphere:
    center: np.ndarray
    radius: float


@dataclass(frozen=True)
class Plane:
    center: np.ndarray
    normal: np.ndarray
    half_extent: float


@dataclass(frozen=True)
class Arrow:
    start: np.ndarray
    direction: np.ndarray      # unit
    display_length: float      # a labeled convention (design 11.6)


@dataclass(frozen=True)
class Arc:
    """An arc of a circle from `start_dir` toward `end_dir` in the
    plane with the given normal."""
    center: np.ndarray
    radius: float
    start_dir: np.ndarray
    end_dir: np.ndarray
    plane_normal: np.ndarray


@dataclass(frozen=True)
class Segment:
    start: np.ndarray
    end: np.ndarray


@dataclass(frozen=True)
class Text:
    anchor: np.ndarray
    text: str
