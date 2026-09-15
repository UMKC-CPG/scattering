"""Presentation: the renderer-agnostic scene description, the
palettes, the 2D panels, and the one module that draws (vedo).

Governed by pseudocode section 11 and design section 11. Nothing under the stage
groups imports from here (ARCHITECTURE 6.5), and only `vedo_renderer.py` imports
vedo or VTK.
"""

from scattering.render.scene_description import (Drawable, Scene, Telemetry,
    build_frame, build_static)
from scattering.render.palettes import (BACKGROUNDS, PALETTES, ROLES,
                                        check_redundancy, resolve_encoding)

__all__ = ['Drawable', 'Scene', 'Telemetry', 'build_frame', 'build_static',
           'BACKGROUNDS', 'PALETTES', 'ROLES', 'check_redundancy',
           'resolve_encoding']
