"""Controls sources (pseudocode 12.5): where commands come from.

`VedoControls` listens to the window's key presses and pumps its event queue;
`ScriptedControls` feeds a fixed list of (tick, command) pairs and stops after a
frame cap, for headless tests and for `scsim.py --frames`. Both expose read(),
pump(), window_closed(), the shape the rigid-body tool's session uses.

This module names vedo objects only through duck typing (a plotter with
add_callback and an interactor), so that it imports no graphics library itself.

Attribution: this module is part of the scattering teaching tool.
"""

import sys

from scattering.ui.controls import BINDINGS


class VedoControls:
    def __init__(self, plotter):
        self.plotter = plotter
        self.queue = []
        self._closed = False
        try:
            plotter.add_callback('KeyPress', self._on_key_press)
        except Exception:                      # offscreen: no interactor
            pass

    def _on_key_press(self, event):
        # Keys arrive already chorded ("Ctrl+s"); anything not in the
        # table is VTK's own and is left to it (design 12.15).
        key = getattr(event, 'keypress', None)
        if key in BINDINGS:
            self.queue.append(BINDINGS[key][0])
        elif key and key.startswith(('Ctrl+', 'Alt+')):
            # A chord the table does not know: say so, with the name as
            # it arrived. Key names differ between X servers, remote
            # desktops, and keyboard layouts ("Ctrl+bracketleft" is what
            # vedo documents for Ctrl+[), and this line is how a
            # mismatch is found (pseudocode 12.5).
            print(f'scsim: key {key!r} is not bound (Ctrl+h: legend)',
                  file=sys.stderr)

    def push(self, command):
        """A command with a value from a slider (pseudocode 12.5):
        ('seek', frame) or ('set_energy', k). Applied like a key."""
        self.queue.append(command)

    def read(self):
        commands, self.queue = self.queue, []
        return commands

    def pump(self):
        interactor = getattr(self.plotter, 'interactor', None)
        if interactor is not None:
            interactor.ProcessEvents()
            if interactor.GetDone():
                self._closed = True

    def window_closed(self):
        return self._closed


class ScriptedControls:
    def __init__(self, script=(), max_frames=1):
        self.script = list(script)
        self.max_frames = int(max_frames)
        self.tick = 0

    def read(self):
        commands = [command for tick, command in self.script
                    if tick == self.tick]
        self.tick += 1
        return commands

    def pump(self):
        pass

    def window_closed(self):
        return self.tick >= self.max_frames


def parse_script(text):
    """'2:play_pause,10:reverse' -> [(2, 'play_pause'), (10, 'reverse')]."""
    if not text:
        return []
    pairs = []
    for item in text.split(','):
        tick, command = item.split(':', 1)
        pairs.append((int(tick), command.strip()))
    return pairs
