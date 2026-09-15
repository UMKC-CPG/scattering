"""The 2D panels (pseudocode 11.4, 7.7, 9.4; design 11.2).

Each `panel_*` function returns plain data from the store; `render_panel` turns
that data into an RGB image with matplotlib, which the vedo renderer places in a
sub-window. The cross-section panel draws the exact curve and, given a
DetectorResult, the measured bars spanning their bins with Poisson errors,
arrows for empty bins, and hatching over the unmeasured cones. The error-budget
panel shows three text columns -- numerical, statistical, assumption -- and the
tracked particle's residual curves; no expression in it combines fields of two
columns (design 9.9, tested). The recovered-potential panel arrives with
pseudocode section 8.

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import dataclass, field

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt          # noqa: E402  (after use('Agg'))
import numpy as np                       # noqa: E402

from scattering.core.natural_units import angular_momentum   # noqa: E402

_LINE_STYLES = {'solid': '-', 'dashed': '--', 'dotted': ':',
                'dash_dot': '-.'}


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
    bars: list = field(default_factory=list)     # (x0, x1, y, dy, role)
    arrows: list = field(default_factory=list)   # (x, y, role): empty bins
    hatched: list = field(default_factory=list)  # (x0, x1): unmeasured
    text_columns: list = field(default_factory=list)  # lists of lines
    symlog: bool = False


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


def panel_cross_section(store, k, detector=None):
    """The exact curve, and with a DetectorResult the measured bars,
    arrows for empty bins, and hatching over the unmeasured cones
    (pseudocode 7.7)."""
    _, xsec, _, _ = store.tables(k)
    ok = xsec.flags == 'ok'
    curves = [(xsec.theta[ok], xsec.dsdo[ok], 'exact_curve', 'exact')]
    text = [f'measured: {xsec.theta_min:.3f} .. {xsec.theta_head:.3f}']
    if detector is None:
        return PanelData('cross_section', 'Differential cross section',
            'theta (rad)', 'dsigma/dOmega (l0^2)', curves, ylog=True, text=text)
    layout = detector.layout
    bars, arrows = [], []
    for i in range(layout.n_bins):
        low, high = layout.edges[i], layout.edges[i + 1]
        if not detector.has_flux:
            continue
        if detector.empty[i]:
            arrows.append((0.5 * (low + high),
                           1.0 / (detector.flux * layout.solid_angle[i]),
                           'measured'))
        else:
            bars.append((low, high, detector.estimate[i],
                         detector.error[i], 'measured'))
    hatched = [(1e-3, layout.theta_min), (layout.theta_head, np.pi)]
    text = [f'N = {detector.n_thrown}; mode {layout.mode}, {layout.name}, '
            f'{layout.n_bins} bins']
    if detector.has_flux:
        text.append(f'pull rms {detector.pull_rms:.2f} (1.0 = Poisson)')
        empties = int(detector.empty.sum())
        share = detector.counts.max() / max(detector.n_counted, 1)
        # Design 7.4: the labeled bad example.
        if empties > layout.n_bins // 4 or share > 0.5:
            text.append(f'{empties} of {layout.n_bins} bins empty, '
                        f'{share:.0%} of counts in one bin: a poor '
                        f'layout for this cross section')
    else:
        text.append('uniform-flux beam required for an estimate; '
                    'counts only')
    if detector.n_outside:
        text.append(f'{detector.n_outside} outside the measured range '
                    f'(a bug)')
    return PanelData('cross_section', 'Differential cross section',
        'theta (rad)', 'dsigma/dOmega (l0^2)', curves, ylog=True, text=text,
        bars=bars, arrows=arrows, hatched=hatched)


def panel_effective_potential(store, resolved, k, tracked):
    energy = float(store.energies[k])
    b = float(store.impact_parameter[tracked])
    r_min = float(store.turning_point[k, tracked])
    radii = np.geomspace(max(0.3 * r_min, 1e-3), resolved.settings.r_max,
                         400)
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
                     f'{m.solid_angle:9.4f} {m.ratio:10.4f} '
                     f'{m.dsdo_mid:9.4f}')
    return PanelData('annulus_to_cone', 'Annulus to cone (design 5.7)', '',
                     '', text=lines)


def panel_error_budget(budget):
    """Three text columns and the tracked residual curves (pseudocode
    9.4). Each column is formatted from its own record only."""
    numeric = budget.numerical
    numerical = ['NUMERICAL',
                 f'orbits: {numeric.orbit_provider}'
                 + (' (closed form)' if numeric.closed_form else
                    f' {numeric.integrator} rtol {numeric.rtol:.0e}'),
                 f'energy drift   {numeric.energy_drift_max:.1e}',
                 f'L drift        {numeric.angmom_drift_max:.1e}',
                 f'exterior defl. {numeric.exterior_deflection_max:.1e} '
                 f'rad',
                 f'quadrature     {numeric.provider_check:.1e}']
    stat = budget.statistical
    statistical = ['STATISTICAL',
                   f'N = {stat.n_particles}, {stat.n_bins} bins']
    if stat.has_flux:
        statistical.append(f'pull rms {stat.pull_rms:.2f} '
                           f'(1.0 = Poisson)')
    else:
        statistical.append('no flux (annuli beam)')
    if np.isfinite(stat.stat_band_at_reach):
        statistical.append(f'band at reach {stat.stat_band_at_reach:.1e}')
    if budget.assumption is not None:
        assume = budget.assumption
        assumption = ['ASSUMPTION', f'tail model {assume.tail_model}',
                      f'tail share at far r '
                      f'{assume.tail_fraction_at_far:.0%}',
                      f'sign assumed {assume.assume_sign:+d}']
    else:
        assumption = ['ASSUMPTION', '(inversion not run)']
    series = budget.tracked
    curves = [(series.time, series.energy_residual, 'exact_curve',
               'energy residual'),
              (series.time, series.angmom_residual, 'mirror',
               'L residual')]
    return PanelData('error_budget', 'Error budget (design 9)', 't (natural)',
        'residual', curves=curves,
        text_columns=[numerical, statistical, assumption], symlog=True)


def panel_placeholder(name, title):
    return PanelData(name, title, '', '', text=['(after pseudocode 8)'])


def build_panel(name, store, resolved, k, tracked, show_mirror,
                detector=None, budget=None):
    if name == 'deflection':
        return panel_deflection(store, k, tracked, show_mirror)
    if name == 'cross_section':
        return panel_cross_section(store, k, detector)
    if name == 'effective_potential':
        return panel_effective_potential(store, resolved, k, tracked)
    if name == 'annulus_to_cone':
        return panel_annulus_to_cone(store, k)
    if name == 'error_budget':
        if budget is None:
            return panel_placeholder(name, 'error budget')
        return panel_error_budget(budget)
    if name == 'telemetry':
        return None                          # drawn as overlay text
    if name in ('recovered_potential', 'histogram'):
        return panel_placeholder(name, name.replace('_', ' '))
    raise ValueError(f'unknown panel {name!r}')


def render_panel(data, palette, background, size=(400, 300)):
    """An RGB uint8 array of the panel, via matplotlib Agg.

    A panel with text columns (the error budget) puts the columns in
    the upper part of the figure and its curves below; every other
    panel is one axes with its notes in a corner.
    """
    dpi = 100
    fig = plt.figure(figsize=(size[0] / dpi, size[1] / dpi), dpi=dpi)
    fig.patch.set_facecolor(background)
    foreground = palette['exact_curve'].color
    if data.text_columns:
        ax = fig.add_axes([0.14, 0.14, 0.82, 0.40])
        width = 0.97 / len(data.text_columns)
        for index, lines in enumerate(data.text_columns):
            fig.text(0.03 + index * width, 0.96, '\n'.join(lines),
                     fontsize=5.5, family='monospace', color=foreground,
                     va='top')
    else:
        ax = fig.add_axes([0.17, 0.16, 0.79, 0.74])
    ax.set_facecolor(background)
    for x, y, role, label in data.curves:
        enc = palette[role]
        ax.plot(x, y, color=enc.color, lw=enc.weight,
                ls=_LINE_STYLES[enc.line_style], label=label)
    for x, y, role, label in data.markers:
        ax.plot([x], [y], 'o', color=palette[role].color, label=label)
    for y, role, label in data.hlines:
        ax.axhline(y, color=palette[role].color, lw=1, ls='--', label=label)
    for x0, x1, y, dy, role in data.bars:
        color = palette[role].color
        ax.hlines(y, x0, x1, color=color, lw=2)
        # On a log axis a one-count bin's lower error reaches zero;
        # clip it at a tenth of the estimate so it stays drawable
        # without dragging the axis to the floor.
        ax.vlines(0.5 * (x0 + x1), max(y - dy, 0.1 * y), y + dy,
                  color=color, lw=1)
    for x, y, role in data.arrows:
        ax.annotate('', xy=(x, y * 0.3), xytext=(x, y),
                    arrowprops=dict(arrowstyle='->',
                                    color=palette[role].color))
    for x0, x1 in data.hatched:
        ax.axvspan(x0, x1, hatch='//', alpha=0.12, color=foreground, lw=0)
    if data.xlog:
        ax.set_xscale('log')
    if data.ylog:
        ax.set_yscale('log')
    if data.symlog:
        ax.set_yscale('symlog', linthresh=1e-14)
    ax.set_title(data.title, color=foreground, fontsize=9,
                 y=1.02 if not data.text_columns else 1.0)
    ax.set_xlabel(data.xlabel, color=foreground, fontsize=8)
    ax.set_ylabel(data.ylabel, color=foreground, fontsize=8)
    ax.tick_params(colors=foreground, labelsize=7)
    for spine in ax.spines.values():
        spine.set_color(foreground)
    if data.curves or data.markers:
        ax.legend(fontsize=7, loc='best')
    if data.text:
        ax.text(0.02, 0.02, '\n'.join(data.text), transform=ax.transAxes,
                fontsize=6, family='monospace', color=foreground,
                va='bottom')
        if not (data.curves or data.markers):
            ax.set_axis_off()
    fig.canvas.draw()
    image = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy()
    plt.close(fig)
    return image
