"""The shipped resource-control (rc) defaults.

The `<command>rc.py` files here are the documented sets of
machine-local defaults and the last place
`scattering.cli.support.load_rc_defaults` looks. They are inside the
package, rather than beside the entry-point scripts, because an
installed copy of the tool has no script directory: the package is
the one location that exists however the tool was obtained (physdemo
contract C7). A user who wants to change a default copies the file to
their working directory with the command's `--write-rc` and edits the
copy.

Attribution: this module is part of the Scattering teaching tool.
"""
