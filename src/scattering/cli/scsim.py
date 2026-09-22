"""scsim -- the interactive scattering tool (Tier 1).

Loads a run file, builds the results store (every orbit at every energy,
precomputed; ARCHITECTURE section 3), and opens the vedo window with the time
scrubber and the energy slider. Pseudocode sections 12.7 and 12.10 govern it.

Settings arrive from three places, each overriding the one before:
the resource-control file scsimrc.py (machine-local, never physics), the run
file (self-contained physics), and --set overrides on the command line. Every
invocation is appended to a `command` file in the working directory so the exact
call can be recovered later.

    scsim --check                  can this computer run and draw it?
    scsim rutherford               a packaged example, by bare name
    scsim --examples               copy the example run files here
    scsim rutherford.toml          your own (edited) copy
    scsim rutherford.toml --set fidelity.n_samples=200
    scsim rutherford.toml --offscreen --frames 5 --screenshot out.png
    scsim --write-rc               copy the rc defaults here, to edit
"""

# WHERE THIS CODE LIVES, AND WHY. This module is the body of the `scsim`
# command. It is inside the package, not in src/scripts/, because the
# command is reached in two ways that must run the same code
# (ARCHITECTURE 4.13, 9.1): the executable src/scripts/scsim.py, which
# the physdemo suite links and a clone runs directly; and the console
# script that `pip install` creates from pyproject.toml, which calls
# console_main() below. The docstring above is the --help text.
#
# The helpers it calls (the packaged examples, the rc copy, the command
# log, the self-check driver) are `cli/support.py`, INHERITED from the
# physdemo skeleton (dev/PSEUDOCODE.md row 0; pseudocode 12.10). That
# module holds no command name and no dependency list, so this one
# supplies them: COMMAND_NAME, CHECKED_DISTRIBUTIONS, and run_offscreen.

import argparse
import sys
import time

from scattering.cli.support import (copy_examples, copy_rc_file,
                                    locate_run_file, record_command,
                                    self_check)
from scattering.run import (RunFileError, build_results_store,
                            load_and_resolve, load_rc)
from scattering.run.rc import RC_FILENAME

COMMAND_NAME = 'scsim'

# The packages `scsim --check` reports on: the ones this tool imports,
# by the names `pip` knows them by. pyproject.toml declares the same
# set (minus the Python 3.10 TOML backport), and a test keeps the two
# in agreement. It lives here and not in support.py because it differs
# per tool and the inherited module must not.
CHECKED_DISTRIBUTIONS = ('numpy', 'scipy', 'matplotlib', 'vedo', 'vtk',
                        'pint', 'tomli_w')


def run_offscreen(run_file_path, frames):
    """Build a deliberately small run from `run_file_path` THROUGH THE
    ORDINARY CODE PATH (loading, resolving, building), draw `frames`
    frames offscreen, and return the last frame as an array. This is
    what `--check` runs; `support.self_check` calls prepare_offscreen()
    before it, so the renderer may be imported here."""
    started = time.perf_counter()
    rc = load_rc()
    resolved = load_and_resolve(
        run_file_path,
        ['fidelity.n_samples=40', 'fidelity.n_deflection_points=60'], rc)
    store = build_results_store(resolved)
    print(f'built       {store.n_energies} energies x '
          f'{store.n_particles} particles in '
          f'{time.perf_counter() - started:.1f} s')
    from scattering.render.vedo_renderer import VedoRenderer
    from scattering.ui import ScriptedControls, run_session
    renderer = VedoRenderer(resolved.spec.view.palette, (640, 480),
                            offscreen=True)
    run_session(resolved, store, ScriptedControls([], frames), renderer,
                rc)
    image = renderer.screenshot(as_array=True)
    renderer.close()
    return image


def parse_command_line(command_line_args=None):
    parser = argparse.ArgumentParser(
        prog=COMMAND_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
        epilog='Defaults are given in ./scsimrc.py or '
               '$SCATTERING_RC/scsimrc.py; --write-rc makes the first.')
    parser.add_argument('runfile', nargs='?', default=None,
        help='TOML run file (design section 10), or the bare name of a '
             'packaged example')
    parser.add_argument('--set', dest='overrides', action='append', default=[],
        metavar='TABLE.KEY=VALUE', help='override one run-file key; repeatable')
    parser.add_argument('--offscreen', action='store_true',
                        help='render without a window')
    parser.add_argument('--frames', type=int, default=0,
        help='draw N frames with scripted controls, then ' 'exit')
    parser.add_argument('--script', default='',
                        help='scripted controls, "tick:command,..."')
    parser.add_argument('--screenshot', default=None,
                        help='write an image after the last frame')
    parser.add_argument('--palette', default=None,
                        help='override [view].palette')
    parser.add_argument('--tracked', type=int, default=None,
                        help='override [view].tracked_particle')
    parser.add_argument('--examples', nargs='?', const='.', default=None,
        metavar='DIR', help='copy the packaged example run files into DIR '
                            '(default: here) and exit; never overwrites')
    parser.add_argument('--write-rc', action='store_true',
        help='copy the shipped scsimrc.py here, to edit, and exit')
    parser.add_argument('--check', action='store_true',
        help='check that this computer can run and draw the tool, and exit')
    args = parser.parse_args(command_line_args)
    # Exactly one thing to do (pseudocode 12.7): a run, or one utility.
    requested = [args.runfile is not None, args.examples is not None,
                 args.write_rc, args.check]
    if sum(requested) != 1:
        parser.error('give a run file, or exactly one of --examples, '
                     '--write-rc, --check')
    if args.offscreen and not (args.frames or args.script):
        # Interactive controls on a window nobody can see would run
        # forever with no way to stop them; refuse before any work.
        parser.error('--offscreen needs --frames N or --script "..." '
                     'so that the run knows when to stop')
    return args


def console_progress(total):
    """A one-line progress bar for the store build."""
    state = {'done': 0}

    def report(energy_index, particle_index):
        state['done'] += 1
        if state['done'] % max(1, total // 20) == 0 or \
                state['done'] == total:
            print(f'\r  orbits {state["done"]}/{total}', end='',
                  file=sys.stderr, flush=True)
            if state['done'] == total:
                print(file=sys.stderr)
    return report


def main(command_line_args=None):
    """Run the tool. Accepting an argument list lets the test suite
    drive this without touching sys.argv."""
    args = parse_command_line(command_line_args)
    if args.examples is not None:
        return copy_examples(args.examples, COMMAND_NAME)
    if args.write_rc:
        return copy_rc_file(RC_FILENAME, '.', COMMAND_NAME)
    if args.check:
        return self_check(run_offscreen, COMMAND_NAME,
                          CHECKED_DISTRIBUTIONS)

    overrides = list(args.overrides)
    if args.palette:
        overrides.append(f'view.palette="{args.palette}"')
    if args.tracked is not None:
        overrides.append(f'view.tracked_particle={args.tracked}')
    # A run file that is missing or wrong is the commonest mistake a
    # student makes; it earns a message and status 2, not a traceback.
    try:
        runfile = locate_run_file(args.runfile, COMMAND_NAME)
        rc = load_rc()
        resolved = load_and_resolve(runfile, overrides, rc)
    except (RunFileError, FileNotFoundError) as problem:
        print(f'{COMMAND_NAME}: {problem}', file=sys.stderr)
        return 2
    print(f'results store: about {resolved.estimate_bytes / 1e6:.0f} MB',
          file=sys.stderr)
    total = (len(resolved.spec.beam.energies)
             * resolved.spec.beam.n_particles_total())
    store = build_results_store(resolved, progress=console_progress(total))

    # Imported here so that `--help` and a run-file error never pay for VTK's
    # import, which is slow on a shared filesystem.
    from scattering.render.offscreen import prepare_offscreen
    if args.offscreen:
        # Before the renderer (and so VTK) is imported; this also
        # covers a DISPLAY that is set but dead (pseudocode 11.6).
        prepare_offscreen()
    from scattering.render.vedo_renderer import VedoRenderer
    from scattering.ui import ScriptedControls, VedoControls, run_session
    from scattering.ui.vedo_controls import parse_script

    renderer = VedoRenderer(resolved.spec.view.palette, rc.window_size,
                            offscreen=args.offscreen)
    if args.frames or args.script:
        script = parse_script(args.script)
        max_frames = args.frames or (max(t for t, _ in script) + 2)
        controls = ScriptedControls(script, max_frames)
    else:
        controls = VedoControls(renderer.plotter)
    run_session(resolved, store, controls, renderer, rc)
    if args.screenshot:
        renderer.screenshot(args.screenshot)
    renderer.close()
    return 0


def console_main():
    """The front that `pip install` creates (pyproject.toml,
    [project.scripts]). It is the real entry point on that route, so it
    is where the invocation is logged; main() itself never logs."""
    record_command()
    sys.exit(main())
