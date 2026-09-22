"""Palettes: the mapping from a drawable's ROLE to its visual
ENCODING (pseudocode 11.5, design 11.5).

A drawable names only its role; a palette resolves the role to a color, line
style, weight, opacity, and glyph; the renderer draws the encoding. Three
palettes ship -- light, dark, and colorblind -- and switching between them
touches neither the scene description nor the physics (VISION P8).

The rule inherited from the rigid-body tool: no distinction that carries meaning
may rest on color alone where a label or a line style can also carry it. The
REDUNDANCY table below records every such distinction and the non-color channel
that carries it, and a test checks each palette against it.

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Encoding:
    color: tuple
    line_style: str = 'solid'
    weight: float = 1.0
    opacity: float = 1.0
    glyph: str = 'sphere'


# Eight categorical hues for the annuli. The colorblind set is the Okabe-Ito
# palette, safe for the common deficiencies.
_LIGHT_HUES = [(0.12, 0.47, 0.71), (1.00, 0.50, 0.05), (0.17, 0.63, 0.17),
               (0.84, 0.15, 0.16), (0.58, 0.40, 0.74), (0.55, 0.34, 0.29),
               (0.89, 0.47, 0.76), (0.50, 0.50, 0.50)]
_DARK_HUES = [(0.40, 0.70, 0.95), (1.00, 0.65, 0.30), (0.45, 0.85, 0.45),
              (0.95, 0.40, 0.40), (0.75, 0.60, 0.95), (0.80, 0.60, 0.50),
              (0.98, 0.65, 0.88), (0.75, 0.75, 0.75)]
_OKABE_ITO = [(0.00, 0.45, 0.70), (0.90, 0.60, 0.00), (0.00, 0.62, 0.45),
              (0.80, 0.40, 0.00), (0.80, 0.60, 0.70), (0.34, 0.71, 0.91),
              (0.94, 0.89, 0.26), (0.00, 0.00, 0.00)]

N_ANNULUS_ROLES = 8

ROLES = (['axis', 'plane', 'detector', 'unmeasured', 'probe', 'disc',
          'free_flight', 'orbit_plane', 'radius', 'polar', 'velocity',
          'turning', 'asymptote', 'deflection', 'tracked', 'trace',
          'reference',
          'exact_curve', 'measured', 'stat_band', 'tail_band', 'recovered',
          'mirror', 'true_potential', 'text']
         + [f'annulus_{j}' for j in range(N_ANNULUS_ROLES)])

# (pair of roles, the non-color channel that tells them apart)
REDUNDANCY = [
    (('annulus_0', 'annulus_1'), 'label'),
    (('free_flight', 'trace'), 'line_style'),
    (('measured', 'unmeasured'), 'line_style'),
    (('stat_band', 'tail_band'), 'line_style'),
    (('recovered', 'true_potential'), 'line_style'),
    (('tracked', 'disc'), 'weight'),
    (('exact_curve', 'mirror'), 'line_style'),
    (('radius', 'reference'), 'line_style'),
]


def _palette(hues, foreground, background_dim, accent):
    table = {
        'axis': Encoding(foreground, 'dash_dot', 1.0, 0.6, 'none'),
        'plane': Encoding(foreground, 'solid', 1.0, 0.08, 'none'),
        'detector': Encoding(foreground, 'solid', 1.0, 0.12, 'none'),
        'unmeasured': Encoding(background_dim, 'dashed', 1.0, 0.35, 'none'),
        'probe': Encoding(accent, 'solid', 1.0, 0.25, 'none'),
        'disc': Encoding(hues[0], 'solid', 1.0, 1.0, 'sphere'),
        'trace': Encoding(foreground, 'solid', 1.0, 0.7, 'none'),
        'free_flight': Encoding(foreground, 'dashed', 1.0, 0.5, 'none'),
        'orbit_plane': Encoding(accent, 'solid', 1.0, 0.10, 'none'),
        'radius': Encoding(accent, 'solid', 2.0, 1.0, 'none'),
        'polar': Encoding(accent, 'solid', 2.0, 1.0, 'none'),
        'reference': Encoding(accent, 'dotted', 1.5, 0.9, 'none'),
        'velocity': Encoding(accent, 'solid', 2.0, 1.0, 'none'),
        'turning': Encoding(accent, 'solid', 1.0, 1.0, 'cube'),
        'asymptote': Encoding(foreground, 'dotted', 1.5, 0.8, 'none'),
        'deflection': Encoding(accent, 'solid', 2.0, 1.0, 'none'),
        'tracked': Encoding(accent, 'solid', 2.0, 1.0, 'sphere'),
        'exact_curve': Encoding(foreground, 'solid', 2.0, 1.0, 'none'),
        'measured': Encoding(hues[0], 'solid', 1.0, 0.8, 'none'),
        'stat_band': Encoding(hues[0], 'solid', 1.0, 0.3, 'none'),
        'tail_band': Encoding(hues[1], 'dotted', 1.0, 0.3, 'none'),
        'recovered': Encoding(hues[0], 'solid', 2.0, 1.0, 'none'),
        'mirror': Encoding(hues[3], 'dashed', 1.5, 1.0, 'none'),
        'true_potential': Encoding(foreground, 'dotted', 2.0, 1.0, 'none'),
        'text': Encoding(foreground, 'solid', 1.0, 1.0, 'none'),
    }
    for j in range(N_ANNULUS_ROLES):
        table[f'annulus_{j}'] = Encoding(hues[j], 'solid', 1.0, 1.0,
                                         'sphere')
    return table


PALETTES = {
    'light': _palette(_LIGHT_HUES, (0.15, 0.15, 0.15), (0.6, 0.6, 0.6),
                      (0.85, 0.10, 0.10)),
    'dark': _palette(_DARK_HUES, (0.90, 0.90, 0.90), (0.5, 0.5, 0.5),
                     (1.00, 0.35, 0.35)),
    'colorblind': _palette(_OKABE_ITO, (0.10, 0.10, 0.10), (0.6, 0.6, 0.6),
                           (0.80, 0.40, 0.00)),
}

BACKGROUNDS = {'light': (1.0, 1.0, 1.0), 'dark': (0.08, 0.08, 0.10),
               'colorblind': (1.0, 1.0, 1.0)}


def resolve_encoding(palette_name, role):
    """Every role exists in every palette; a KeyError here is a bug,
    not a user error."""
    return PALETTES[palette_name][role]


def check_redundancy(palette_name):
    """Violations of the redundancy rule for one palette: pairs whose
    named non-color channel does not actually differ."""
    palette = PALETTES[palette_name]
    violations = []
    for (first, second), channel in REDUNDANCY:
        if channel == 'label':
            continue                       # carried by the drawable
        if getattr(palette[first], channel) == getattr(palette[second],
                                                       channel):
            violations.append((first, second, channel))
    return violations
