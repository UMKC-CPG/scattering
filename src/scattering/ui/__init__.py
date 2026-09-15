"""The interactive session: the state a student drives, the key
bindings, the controls sources, and the loop.

Governed by pseudocode section 12 and design section 12. Every control here is a
VIEWING control: it reads the frozen store and changes what is shown, never what
was computed. This package imports nothing from the physics stages directly (it
reaches the store through `run/`), and a structural test enforces that.
"""

from scattering.ui.session_state import (SessionState, advance, cycle_tracked,
    jump, set_energy, set_rate, step)
from scattering.ui.controls import BINDINGS, apply, control_legend_lines
from scattering.ui.vedo_controls import ScriptedControls, VedoControls
from scattering.ui.interactive_session import Session, run_session

__all__ = ['SessionState', 'advance', 'cycle_tracked', 'jump', 'set_energy',
           'set_rate', 'step', 'BINDINGS', 'apply', 'control_legend_lines',
           'ScriptedControls', 'VedoControls', 'Session', 'run_session']
