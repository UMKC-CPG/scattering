"""scattering — the importable library.

A teaching tool for classical scattering in a central potential and
for the inversion of scattering data back to the potential. The
subpackages are named for the stages of the forward chain they
implement (potentials, beam, orbits, deflection, detector,
inversion) plus the supporting groups (core, analysis, geometry,
run, sinks, render, ui); see dev/ARCHITECTURE.md section 4.

The convention that has worked on earlier projects is that this
package holds subpackages named for a *concern* rather than a layer.
For a simulation that has meant, for example, `core/` for shared
types and units, `geometry/`, `dynamics/`, `analysis/`, `render/`,
and a `spec/` or `scenario/` package for the input deck.

Command-line entry points stay thin and live in `src/scripts/`; they
parse arguments and call in here. No physics lives in a script.

The module map that governs this layout is `dev/ARCHITECTURE.md`
section 2. Adding a subpackage means adding its row there.
"""

__version__ = '0.1.0'
