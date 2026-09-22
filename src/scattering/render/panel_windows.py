"""The 2D panels as ordinary matplotlib windows (pseudocode 11.6,
design 11.10): one figure window per panel, redrawn only when the
data behind it changes, kept responsive by pumping matplotlib's event
queue once per session tick.

This module imports matplotlib and nothing of vedo or VTK. It is also
the ONE place a matplotlib backend is chosen, and it chooses before
pyplot is imported, which is the only time a choice takes effect:
offscreen runs use Agg (no window); on-screen runs try the Tk backend,
which ships with a python.org or conda Python on Linux, macOS, and
Windows, and fall back to Agg with one line on standard error if it
is missing, so that the scene still runs without its graphs.

Attribution: this module is part of the scattering teaching tool.
"""

import sys

import matplotlib

from scattering.render.panels import draw_panel_into, render_panel


def _choose_backend(offscreen):
    """Pick the backend; True if figure windows can be opened."""
    if offscreen:
        matplotlib.use('Agg')
        return False
    try:
        matplotlib.use('TkAgg')
        import tkinter                              # noqa: F401
        return True
    except Exception as problem:                    # noqa: BLE001
        print(f'panels: no Tk backend for matplotlib ({problem}); the '
              'graphs are drawn offscreen only', file=sys.stderr)
        matplotlib.use('Agg')
        return False


class PanelWindows:
    """One figure per panel name; see the module docstring."""

    def __init__(self, panel_names, palette, background, offscreen=False):
        self.names = [name for name in panel_names if name != 'telemetry']
        self.palette = palette
        self.background = background
        self.interactive = _choose_backend(offscreen) if self.names \
            else False
        self.figures = {}
        self.keys = {}
        self.draw_count = 0            # for the tests: redraws so far

    def set_palette(self, palette, background):
        self.palette, self.background = palette, background
        self.keys.clear()              # every figure is stale now

    def _figure(self, name):
        """The figure for a panel, opened (or reopened) on demand."""
        import matplotlib.pyplot as plt
        figure = self.figures.get(name)
        if figure is not None and (not self.interactive
                                   or plt.fignum_exists(figure.number)):
            return figure
        # First use, or the student closed the window: a closed graph
        # must not end the session, so it is simply reopened.
        figure = plt.figure(f'scattering: {name.replace("_", " ")}',
                            figsize=(5.0, 3.75))
        self.figures[name] = figure
        return figure

    def update(self, name, data, key):
        """Redraw panel `name` from `data` if `key` differs from the key
        it was last drawn with; otherwise do nothing (design 11.10)."""
        if data is None or key == self.keys.get(name):
            return
        figure = self._figure(name)
        draw_panel_into(figure, data, self.palette, self.background)
        figure.canvas.draw_idle()
        if self.interactive:
            figure.show()
        self.keys[name] = key
        self.draw_count += 1

    def pump(self):
        """Keep the figure windows responsive between redraws (session
        loop step 4, design 12.3)."""
        if not self.interactive:
            return
        for figure in self.figures.values():
            try:
                figure.canvas.flush_events()
            except Exception:                       # noqa: BLE001
                pass                                # a window being closed

    def image(self, name, data, size=(400, 300)):
        """The panel as an RGB array, offscreen, whatever the backend:
        the tests' and the batch tier's path."""
        return render_panel(data, self.palette, self.background, size)

    def close(self):
        import matplotlib.pyplot as plt
        for figure in self.figures.values():
            plt.close(figure)
        self.figures.clear()
        self.keys.clear()
