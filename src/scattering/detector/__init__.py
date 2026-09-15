"""The detector: counts in angular bins, with the statistical error
those counts carry.

Governed by pseudocode section 7 and design section 7. The detector is a pure
function of the frozen results store and a layout; it is recomputed as a viewing
control (design 12.7), never stored. It consumes only the stored asymptotic
directions, the beam's flux and measured range, and the cross-section table --
it cannot see the potential or the orbits, and an import test enforces that
(ARCHITECTURE 6.4). That restriction is the lesson of VISION G8 in
code: a detector cannot tell attraction from repulsion.
"""

from scattering.detector.detector_spec import DetectorLayout, build_layout
from scattering.detector.binning import (asymptotic_angles, bin_particles,
                                         position_angles)
from scattering.detector.counting_statistics import (DetectorResult,
    build_detector_result, estimate_and_error, expected_counts, pulls)

__all__ = ['DetectorLayout', 'build_layout', 'asymptotic_angles',
           'bin_particles', 'position_angles', 'DetectorResult',
           'build_detector_result', 'estimate_and_error',
           'expected_counts', 'pulls']
