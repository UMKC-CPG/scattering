#!/usr/bin/env python3

"""scsim -- the interactive scattering tool (Tier 1).

Loads a run file, builds the results store (every orbit at every energy,
precomputed; ARCHITECTURE section 3), and opens the vedo window with the time
scrubber and the energy slider. Pseudocode section 12.7 governs this script.

Settings arrive from three places, each overriding the one before:
the resource-control file scsimrc.py (machine-local, never physics), the run
file (self-contained physics), and --set overrides on the command line. Every
invocation is appended to a `command` file in the working directory so the exact
call can be recovered later.

    scsim.py runs/rutherford.toml
    scsim.py runs/rutherford.toml --set fidelity.n_samples=200
    scsim.py runs/rutherford.toml --offscreen --frames 5 \\
             --screenshot out.png
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# The library lives in src/scattering next to this scripts/ directory;
# an installed package (pip install -e .) makes this a no-op.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scattering.run import build_results_store, load_and_resolve, load_rc


def record_command():
    """Append this invocation to `command` in the working directory,
    as a dated block naming the full argument vector. Called from the `__main__`
    block, not from main(), so that the test suite calling
    main(argv) never writes stray files. `--help` is not logged."""
    if any(argument in ('-h', '--help') for argument in sys.argv):
        return
    with open('command', 'a') as command_log:
        timestamp = datetime.now().strftime('%b. %d, %Y: %H:%M:%S')
        command_log.write(f'Date: {timestamp}\n')
        command_log.write('Cmnd:')
        for argument in sys.argv:
            command_log.write(f' {argument}')
        command_log.write('\n\n')


def parse_command_line(command_line_args=None):
    parser = argparse.ArgumentParser(
        prog='scsim',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
        epilog='Defaults are given in ./scsimrc.py or '
               '$SCATTERING_RC/scsimrc.py.')
    parser.add_argument('runfile', help='TOML run file (design section 10)')
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
    args = parser.parse_args(command_line_args)
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
    rc = load_rc()
    overrides = list(args.overrides)
    if args.palette:
        overrides.append(f'view.palette="{args.palette}"')
    if args.tracked is not None:
        overrides.append(f'view.tracked_particle={args.tracked}')
    resolved = load_and_resolve(args.runfile, overrides, rc)
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
        offscreen=args.offscreen, panels=resolved.spec.view.panels)
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


if __name__ == '__main__':
    record_command()
    sys.exit(main())
