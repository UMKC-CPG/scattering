#!/usr/bin/env python3

"""Resource-control defaults for scsim (pseudocode 10.9).

This file holds the MACHINE-LOCAL settings of the interactive tool:
things that depend on the computer, the display, or personal taste, and that
never affect a computed result. Physics defaults are not here; they live in the
run-file schema (src/scattering/run/schema.py) so that a run file is
self-contained (ARCHITECTURE section 7).

It is looked up first in the current working directory, then in
$SCATTERING_RC, then here, inside the package (design 10.7). A user who
wants a bigger window or a dark palette by default runs
`scsim --write-rc`, which copies this file into the working directory,
and edits the copy; nobody needs to know where the package is.

This file has no main() and is never run as an entry point, so it does not log
to `command` the way scsim does.
"""


def parameters_and_defaults():
    """Return the dictionary of rc settings. Every key here maps to a
    field of scattering.run.rc.RcSettings; a misspelled key fails at
    startup rather than silently doing nothing."""

    param_dict = {
        # The results store is refused above this size; design 6.4.
        'max_store_bytes': 4_000_000_000,

        # Particles per ring for the shorthand annulus list; design 3.3.
        'default_n_azimuth': 24,

        # r_max must exceed the beam's largest impact parameter by this factor;
        # design 10.6.
        'r_max_safety_factor': 3.0,

        # Presentation defaults; design 11. A run file's [view] table overrides
        # these.
        'default_palette': 'light',
        'default_camera': {'azimuth_deg': 35.0, 'elevation_deg': 20.0,
                           'distance': 4.0},
        'default_panels': ['deflection', 'cross_section',
                           'effective_potential', 'error_budget',
                           'telemetry'],
        'window_size': [1280, 960],

        # Particle glyph radius in natural units, a labeled display convention;
        # design 11.6.
        'glyph_radius': 0.02,

        # Where saved run files and screenshots go.
        'output_dir': '.',
    }

    return param_dict


if __name__ == '__main__':
    # Running this file directly prints the defaults, which is a convenient way
    # to check what scsim will start from.
    print(parameters_and_defaults())
