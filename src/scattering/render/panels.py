"""The 2D panels (pseudocode 11.4, design 11.2): the deflection
function, the cross section, the effective potential of the tracked particle,
and the annulus-to-cone numbers. Each `panel_*` function returns plain data from
the store; `render_panel` turns that data into an RGB image with matplotlib,
which the vedo renderer places in a sub-window. The detector histogram and the
recovered potential arrive with pseudocode sections 7 and 8; their panels are
placeholders here.

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import dataclass, field

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt          # noqa: E402  (after use('Agg'))
import numpy as np                       # noqa: E402

from scattering.core.natural_units import angular_momentum   # noqa: E402


@dataclass(frozen=True)
class PanelData:
    name: str
    title: str
    xlabel: str
    ylabel: str
    curves: list = field(default_factory=list)   # (x, y, role, label)
    markers: list = field(default_factory=list)  # (x, y, role, label)
    hlines: list = field(default_factory=list)   # (y, role, label)
    xlog: bool = False
    ylog: bool = False
    text: list = field(default_factory=list)     # lines of text


def panel_deflection(store, k, tracked, show_mirror):
    table, _, mirror, _ = store.tables(k)
    curves = [(table.impact, np.degrees(table.deflection), 'exact_curve',
               'Theta(b)')]
    if show_mirror and mirror is not None:
        curves.append((mirror.impact, np.degrees(mirror.deflection),
                       'mirror', 'mirror potential'))
    b = store.impact_parameter[tracked]
    markers = [(b, np.degrees(store.deflection[k, tracked]), 'tracked',
                'tracked')]
    return PanelData('deflection', 'Deflection function', 'b (natural)',
                     'Theta (deg)', curves, markers, xlog=True)


def panel_cross_section(store, k):
    _, xsec, _, _ = store.tables(k)
    ok = xsec.flags == 'ok'
    return PanelData('cross_section', 'Differential cross section',
        'theta (rad)', 'dsigma/dOmega (l0^2)',
        [(xsec.theta[ok], xsec.dsdo[ok], 'exact_curve', 'exact')], ylog=True,
        text=[f'measured: {xsec.theta_min:.3f} .. ' f'{xsec.theta_head:.3f}'])


def panel_effective_potential(store, resolved, k, tracked):
    energy = float(store.energies[k])
    b = float(store.impact_parameter[tracked])
    r_min = float(store.turning_point[k, tracked])
    radii = np.geomspace(max(0.3 * r_min, 1e-3), resolved.settings.r_max, 400)
    ang_mom = angular_momentum(energy, b)
    effective = (resolved.potential.value(radii)
                 + ang_mom ** 2 / (2 * radii ** 2))
    keep = np.abs(effective) < 5 * energy + 5
    return PanelData('effective_potential', 'Effective potential',
        'r (natural)', 'V_eff',
        [(radii[keep], effective[keep], 'exact_curve', 'V + L^2/2r^2')],
        markers=[(r_min, energy, 'turning', 'r_min')],
        hlines=[(energy, 'tracked', 'E')], xlog=True)


def panel_annulus_to_cone(store, k):
    _, _, _, maps = store.tables(k)
    lines = ['ring   b      db     dA       dOmega    dA/dOmega  dsdo(mid)']
    for j, m in enumerate(maps):
        lines.append(f'{j:>3}  {m.impact:6.3f} {m.width:6.3f} {m.area:8.4f} '
                     f'{m.solid_angle:9.4f} {m.ratio:10.4f} {m.dsdo_mid:9.4f}')
    return PanelData('annulus_to_cone', 'Annulus to cone (design 5.7)', '',
                     '', text=lines)


def panel_placeholder(name, title):
    return PanelData(name, title, '', '', text=['(after pseudocode 7/8)'])


def build_panel(name, store, resolved, k, tracked, show_mirror):
    if name == 'deflection':
        return panel_deflection(store, k, tracked, show_mirror)
    if name == 'cross_section':
        return panel_cross_section(store, k)
    if name == 'effective_potential':
        return panel_effective_potential(store, resolved, k, tracked)
    if name == 'annulus_to_cone':
        return panel_annulus_to_cone(store, k)
    if name == 'telemetry':
        return None                          # drawn as overlay text
    if name in ('recovered_potential', 'error_budget', 'histogram'):
        return panel_placeholder(name, name.replace('_', ' '))
    raise ValueError(f'unknown panel {name!r}')


def render_panel(data, palette, background, size=(400, 300)):
    """An RGB uint8 array of the panel, via matplotlib Agg."""
    dpi = 100
    fig, ax = plt.subplots(figsize=(size[0] / dpi, size[1] / dpi), dpi=dpi)
    fig.patch.set_facecolor(background)
    ax.set_facecolor(background)
    foreground = palette['exact_curve'].color
    for x, y, role, label in data.curves:
        enc = palette[role]
        ax.plot(x, y, color=enc.color, lw=enc.weight,
                ls={'solid': '-', 'dashed': '--', 'dotted': ':',
                    'dash_dot': '-.'}[enc.line_style], label=label)
    for x, y, role, label in data.markers:
        ax.plot([x], [y], 'o', color=palette[role].color, label=label)
    for y, role, label in data.hlines:
        ax.axhline(y, color=palette[role].color, lw=1, ls='--', label=label)
    if data.xlog:
        ax.set_xscale('log')
    if data.ylog:
        ax.set_yscale('log')
    ax.set_title(data.title, color=foreground, fontsize=9)
    ax.set_xlabel(data.xlabel, color=foreground, fontsize=8)
    ax.set_ylabel(data.ylabel, color=foreground, fontsize=8)
    ax.tick_params(colors=foreground, labelsize=7)
    for spine in ax.spines.values():
        spine.set_color(foreground)
    if data.curves or data.markers:
        ax.legend(fontsize=7, loc='best')
    if data.text:
        ax.text(0.02, 0.02, '\n'.join(data.text), transform=ax.transAxes,
            fontsize=6, family='monospace', color=foreground, va='bottom')
        if not (data.curves or data.markers):
            ax.set_axis_off()
    fig.tight_layout()
    fig.canvas.draw()
    image = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
    plt.close(fig)
    return image
