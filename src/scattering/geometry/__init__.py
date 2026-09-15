"""Derived display geometry: what the constructions are, in scene
coordinates, computed from the results store and drawing nothing.

Governed by pseudocode section 11.3 and design section 11. Keeping this apart
from `render/` is what lets the batch tier write the rings, cones, and spheres
to HDF5 without a renderer present.
"""

from scattering.geometry.shapes import (Arc, Arrow, Plane, Points, Polyline,
    Ring, Segment, Sphere, SphereBand, Text)
from scattering.geometry.annulus import annulus_ring
from scattering.geometry.cone import (beam_axis, bin_bands, cone_band,
                                      detector_sphere, entry_plane,
                                      unmeasured_caps)
from scattering.geometry.orbit_plane import orbit_plane
from scattering.geometry.probe_depth import probe_depth
from scattering.geometry.markers import tracked_markers

__all__ = ['Arc', 'Arrow', 'Plane', 'Points', 'Polyline', 'Ring',
           'Segment', 'Sphere', 'SphereBand', 'Text', 'annulus_ring',
           'beam_axis', 'bin_bands',
           'cone_band', 'detector_sphere', 'entry_plane',
           'unmeasured_caps', 'orbit_plane', 'probe_depth',
           'tracked_markers']
