"""Key bindings as data, and the dispatcher (pseudocode 12.4, design
12.4, 12.15). The legend on screen and the dispatcher read the same
table, so they cannot disagree. Every command here is a viewing
control; run controls (editing the physics) are made by editing the
run file or with --set and restarting (design 12.8, deferred to 12.9).

EVERY KEY IS A CTRL CHORD (design 12.15), for the reason the
rigid-body tool found first: a bare letter typed into a VTK window is
taken by VTK's own bindings (`s` surface, `w` wireframe, `r` reset the
camera, `e` close), so a student could not tell the tool's keys from
VTK's. Keys arrive from vedo already prefixed ("Ctrl+s", "Ctrl+minus",
"Ctrl+bracketleft") and are matched CASE-SENSITIVELY, because Shift
changes the key symbol: "Ctrl+S" is Ctrl+Shift+s, which is how step
back is told from step. Aliases (help text None) map several symbols
to one command so that a chord feels natural whatever a keyboard's
shift state names the key. Where the rigid-body tool has a key for the
same purpose, the same key is used.

Two commands carry a value and are not in the table: ("seek", n) from
the time slider and ("set_energy", k) from the energy slider (design
12.4, 12.5); the dispatcher accepts them beside the key commands.

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import replace

import numpy as np

from scattering.ui.session_state import (cycle_tracked, jump,
    set_energy, set_graticule, set_rate, step, toggle_all_rings,
    toggle_ring)

PALETTE_CYCLE = ('light', 'dark', 'colorblind')
LAYOUT_CYCLE = ('log_theta', 'uniform_theta', 'equal_solid_angle')

BINDINGS = {
    'Ctrl+space': ('play_pause', 'play / pause'),
    'Ctrl+s': ('step_forward', 'one frame, then pause'),
    'Ctrl+S': ('step_back', 'one frame back, then pause (Shift)'),
    'Ctrl+plus': ('faster', 'rate x2, up to 16'),
    'Ctrl+equal': ('faster', None),
    'Ctrl+minus': ('slower', 'rate / 2, down to 1'),
    'Ctrl+underscore': ('slower', None),
    'Ctrl+n': ('normal', 'rate 1'),
    'Ctrl+0': ('normal', None),
    'Ctrl+r': ('reverse', 'flip direction'),
    'Ctrl+e': ('jump_entry', "tracked particle's entry"),
    'Ctrl+p': ('jump_pericenter', "tracked particle's pericenter"),
    'Ctrl+x': ('jump_exit', "tracked particle's exit"),
    'Ctrl+Home': ('jump_start', 'first frame'),
    'Ctrl+End': ('jump_end', 'last frame'),
    'Ctrl+l': ('loop', 'toggle loop at the end'),
    'Ctrl+comma': ('energy_down', 'previous energy'),
    'Ctrl+period': ('energy_up', 'next energy'),
    'Ctrl+Tab': ('track_next', 'next tracked particle'),
    'Ctrl+1': ('ring_1', 'toggle ring 1 .. 9 (Ctrl+1 .. Ctrl+9)'),
    'Ctrl+2': ('ring_2', None), 'Ctrl+3': ('ring_3', None),
    'Ctrl+4': ('ring_4', None), 'Ctrl+5': ('ring_5', None),
    'Ctrl+6': ('ring_6', None), 'Ctrl+7': ('ring_7', None),
    'Ctrl+8': ('ring_8', None), 'Ctrl+9': ('ring_9', None),
    'Ctrl+a': ('rings_all', 'toggle all rings'),
    'Ctrl+bracketleft': ('graticule_fewer', 'fewer latitude lines'),
    'Ctrl+bracketright': ('graticule_more', 'more latitude lines'),
    'Ctrl+m': ('mirror', 'toggle the mirror deflection curve'),
    'Ctrl+d': ('detector_mode', 'asymptotic / position'),
    'Ctrl+b': ('detector_layout', 'cycle the bin layout'),
    'Ctrl+c': ('palette', 'cycle light / dark / colorblind'),
    'Ctrl+w': ('save', 'write the resolved run file'),
    'Ctrl+h': ('legend', 'hide / show this legend'),
    'Ctrl+q': ('quit', 'quit'),
    # VTK closes its window on a bare q or Escape of its own accord;
    # honouring them keeps the session in step with the real window.
    'q': ('quit', None),
    'Escape': ('quit', None),
}

COMMANDS = {command for command, _ in BINDINGS.values()}
VALUED_COMMANDS = ('seek', 'set_energy')

# Ctrl+w rather than Ctrl+s for save: Ctrl+s is single-step in the
# rigid-body tool, and a tool that steps where its sibling saves would
# teach the wrong reflex (design 12.15).

_LEGEND_KEY_NAMES = {'space': 'space', 'plus': '+', 'minus': '-',
                     'comma': ',', 'period': '.', 'bracketleft': '[',
                     'bracketright': ']', 'Tab': 'Tab', 'Home': 'Home',
                     'End': 'End'}


def _legend_key(key):
    """'Ctrl+bracketleft' -> 'Ctrl+['; 'Ctrl+S' -> 'Ctrl+Shift+s'."""
    prefix, _, symbol = key.rpartition('+')
    if len(symbol) == 1 and symbol.isupper():
        return f'{prefix}+Shift+{symbol.lower()}'
    return f'{prefix}+{_LEGEND_KEY_NAMES.get(symbol, symbol)}'


def control_legend_lines():
    """One line per command with a help text; aliases are not listed.
    Drawn permanently in the 3D window (design 12.15)."""
    return [f'{_legend_key(key):>14}  {help_text}'
            for key, (_, help_text) in BINDINGS.items()
            if help_text is not None]


def n_rings_of(store, resolved):
    """How many rings Ctrl+1 .. Ctrl+9 can address: the declared annuli,
    or the eight bands of a disc beam (design 11.11)."""
    if store.beam.layout == 'annuli':
        return len(resolved.spec.beam.annuli)
    return 8


def apply(command, session):
    """Dispatch one command (pseudocode 12.4). Returns the session. A
    command is a name from BINDINGS or a (name, value) pair from a
    slider."""
    state, store = session.state, session.store
    n_samples = store.n_samples
    k, tracked = state.energy_index, state.tracked
    value = None
    if isinstance(command, tuple):
        command, value = command
    if command == 'play_pause':
        state = replace(state, playing=not state.playing)
    elif command == 'reverse':
        state = replace(state, direction=-state.direction)
    elif command == 'step_forward':
        state = step(state, n_samples, +1)
    elif command == 'step_back':
        state = step(state, n_samples, -1)
    elif command == 'faster':
        state = set_rate(state, 2.0)
    elif command == 'slower':
        state = set_rate(state, 0.5)
    elif command == 'normal':
        state = replace(state, rate=1)
    elif command == 'jump_entry':
        state = jump(state, n_samples, store.entry_index[k, tracked])
    elif command == 'jump_pericenter':
        state = jump(state, n_samples,
                     int(np.argmin(store.polar[k, tracked, :, 0])))
    elif command == 'jump_exit':
        state = jump(state, n_samples, store.exit_index[k, tracked])
    elif command == 'jump_start':
        state = jump(state, n_samples, 0)
    elif command == 'jump_end':
        state = jump(state, n_samples, n_samples - 1)
    elif command == 'seek':
        # The time slider: any frame, and pause there (design 12.4).
        state = replace(jump(state, n_samples, int(value)), playing=False)
    elif command == 'loop':
        state = replace(state, loop=not state.loop)
    elif command in ('energy_down', 'energy_up'):
        delta = -1 if command == 'energy_down' else +1
        new_index = min(max(k + delta, 0), store.n_energies - 1)
        state = set_energy(state, new_index, n_samples)
    elif command == 'set_energy':
        new_index = min(max(int(value), 0), store.n_energies - 1)
        state = set_energy(state, new_index, n_samples)
    elif command == 'track_next':
        state = cycle_tracked(state, store, +1)
    elif command.startswith('ring_'):
        state = toggle_ring(state, int(command[5:]) - 1,
                            n_rings_of(store, session.resolved))
    elif command == 'rings_all':
        state = toggle_all_rings(state, n_rings_of(store, session.resolved))
    elif command in ('graticule_fewer', 'graticule_more'):
        state = set_graticule(state, -2 if command == 'graticule_fewer'
                              else +2)
        session.renderer.set_graticule(state.graticule_lines)
    elif command == 'mirror':
        state = replace(state, show_mirror=not state.show_mirror)
    elif command == 'detector_mode':
        state = replace(state, detector_mode='position'
                        if state.detector_mode == 'asymptotic'
                        else 'asymptotic')
    elif command == 'detector_layout':
        index = LAYOUT_CYCLE.index(state.detector_layout)
        state = replace(state, detector_layout=LAYOUT_CYCLE[
            (index + 1) % len(LAYOUT_CYCLE)])
    elif command == 'palette':
        index = PALETTE_CYCLE.index(state.palette)
        state = replace(state, palette=PALETTE_CYCLE[(index + 1)
                                                     % len(PALETTE_CYCLE)])
        session.renderer.set_palette(state.palette)
    elif command == 'save':
        # The view a student found by dragging is the one to keep
        # (design 12.14): read the live camera back before writing.
        state = replace(state, camera=session.renderer.read_camera())
        session.state = state
        session.save()
    elif command == 'legend':
        state = replace(state, legend_visible=not state.legend_visible)
        session.renderer.legend_visible = state.legend_visible
    elif command == 'quit':
        session.running = False
    else:
        raise ValueError(f'unknown command {command!r}')
    session.state = state
    return session
