"""Key bindings as data, and the dispatcher (pseudocode 12.4, design
12.4). The legend on screen and the dispatcher read the same table, so they
cannot disagree. Every command here is a viewing control; run controls (editing
the physics) are made by editing the run file or with --set and restarting
(design 12.8, deferred to 12.9).

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import replace

import numpy as np

from scattering.ui.session_state import (advance, cycle_tracked, jump,
                                         set_energy, set_rate, step)

PALETTE_CYCLE = ('light', 'dark', 'colorblind')

BINDINGS = {
    'space': ('play_pause', 'toggle playing'),
    'r': ('reverse', 'flip direction'),
    'period': ('step_forward', 'one frame, then pause'),
    'comma': ('step_back', 'one frame back, then pause'),
    'plus': ('faster', 'rate x2, up to 16'),
    'minus': ('slower', 'rate / 2, down to 1'),
    'e': ('jump_entry', "tracked particle's entry"),
    'p': ('jump_pericenter', "tracked particle's pericenter"),
    'x': ('jump_exit', "tracked particle's exit"),
    'Home': ('jump_start', 'first frame'),
    'End': ('jump_end', 'last frame'),
    'l': ('loop', 'toggle loop at the end'),
    'bracketleft': ('energy_down', 'previous energy'),
    'bracketright': ('energy_up', 'next energy'),
    'Tab': ('track_next', 'next tracked particle'),
    'm': ('mirror', 'toggle the mirror deflection curve'),
    'd': ('detector_mode', 'asymptotic / position'),
    'c': ('palette', 'cycle light / dark / colorblind'),
    's': ('save', 'write the resolved run file'),
    'h': ('help', 'show this legend'),
    'q': ('quit', 'quit'),
}

COMMANDS = {command for command, _ in BINDINGS.values()}


def control_legend_lines():
    return [f'{key:>12}  {help_text}' for key, (_, help_text)
            in BINDINGS.items()]


def apply(command, session):
    """Dispatch one command (pseudocode 12.4). Returns the session."""
    state, store = session.state, session.store
    n_samples = store.n_samples
    k, tracked = state.energy_index, state.tracked
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
    elif command == 'loop':
        state = replace(state, loop=not state.loop)
    elif command in ('energy_down', 'energy_up'):
        delta = -1 if command == 'energy_down' else +1
        new_index = min(max(k + delta, 0), store.n_energies - 1)
        state = set_energy(state, new_index, n_samples)
    elif command == 'track_next':
        state = cycle_tracked(state, store, +1)
    elif command == 'mirror':
        state = replace(state, show_mirror=not state.show_mirror)
    elif command == 'detector_mode':
        state = replace(state, detector_mode='position'
                        if state.detector_mode == 'asymptotic'
                        else 'asymptotic')
    elif command == 'palette':
        index = PALETTE_CYCLE.index(state.palette)
        state = replace(state, palette=PALETTE_CYCLE[(index + 1)
                                                     % len(PALETTE_CYCLE)])
        session.renderer.set_palette(state.palette)
    elif command == 'save':
        session.save()
    elif command == 'help':
        session.renderer.show_legend(control_legend_lines())
    elif command == 'quit':
        session.running = False
    else:
        raise ValueError(f'unknown command {command!r}')
    session.state = state
    return session
