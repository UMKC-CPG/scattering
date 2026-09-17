"""The shipped resource-control (rc) defaults.

`scsimrc.py` here is the documented set of machine-local defaults and
the last place `scattering.run.rc.load_rc` looks (design 10.7). It is
inside the package, rather than beside the entry-point script, because
an installed copy of the tool has no script directory: the package is
the one location that exists however the tool was obtained. A user who
wants to change a default copies the file to their working directory
with `scsim --write-rc` and edits the copy.

Attribution: this module is part of the scattering teaching tool.
"""
