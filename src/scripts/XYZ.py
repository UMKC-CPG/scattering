#!/usr/bin/env python3

"""XYZ -- <one-line statement of what this script does>.

TEMPLATE: copy this file to src/scripts/<name>.py and its companion
to src/scripts/<name>rc.py, then replace every XYZ and every angle- bracketed
placeholder. Delete this paragraph when you do.

The pattern here is the group's standard command-line entry point.
Settings arrive from three places, each overriding the one before it:

  1. Hard defaults in the companion <name>rc.py resource-control file
  2. A local ./<name>rc.py in the working directory, if one exists
  3. Command-line arguments

A script is a thin front door: it resolves settings, calls into the library
under src/<package>/, and writes results. Physics and algorithms belong in the
library, where the design chain governs them and the test suite can reach them.
"""

import argparse as ap
import copy
import os
import sys
from datetime import datetime


def record_command():
    """Append this invocation to a `command` file in the working
    directory, as a dated block naming the full argument vector.

    This exists so that a result found months later can be traced back to the
    exact call that produced it. It is called from the `if __name__ ==
    '__main__':` block rather than from main(), for
    a specific reason: only the real entry point sees the real
    sys.argv, and keeping the call out of main() stops the test suite from
    littering `command` files every time it invokes main(argv) directly.

    A `--help` invocation is not logged; see below.
    """

    # Asking for the usage message is not a run, and logging it would leave a
    # `command` file in any directory where someone merely checked the options.
    if any(argument in ('-h', '--help') for argument in sys.argv):
        return

    with open('command', 'a') as command_log:
        timestamp = datetime.now().strftime('%b. %d, %Y: %H:%M:%S')
        command_log.write(f'Date: {timestamp}\n')
        command_log.write('Cmnd:')
        for argument in sys.argv:
            command_log.write(f' {argument}')
        command_log.write('\n\n')


class ScriptSettings():
    """Holds every user-controllable setting for this script.

    The instance variables are the settings themselves. Their values are pulled
    from the resource-control file and then reconciled with whatever the user
    gave on the command line.
    """

    def __init__(self, command_line_args=None):
        """Resolve settings from the rc file and the command line.

        The rc file is looked for first in the current working directory, so a
        user can drop a modified copy beside their data, and then in the
        directory named by the $PROJECT_RC environment variable, which holds the
        installed defaults.

        Passing command_line_args (a list of strings) is what lets the test
        suite drive this class without touching sys.argv.
        """

        self.assign_rc_defaults(self.load_rc_defaults())

        # Parse the command line, then let it override the defaults.
        self.reconcile(self.parse_command_line(command_line_args))

    def load_rc_defaults(self):
        """Import the resource-control file and return its parameter
        dictionary, preferring a local copy over the installed one.
        """

        # A copy in the working directory wins, so that a user can override the
        # installed defaults for one set of runs.
        search_path = [os.getcwd()]

        rc_directory = os.getenv('PROJECT_RC')
        if rc_directory:
            search_path.append(rc_directory)

        for candidate in search_path:
            if os.path.isfile(os.path.join(candidate, 'XYZrc.py')):
                sys.path.insert(1, candidate)
                from XYZrc import parameters_and_defaults
                return parameters_and_defaults()

        sys.exit('Error: XYZrc.py was not found in the current '
                 'directory or in $PROJECT_RC. See the installation '
                 'instructions.')

    def assign_rc_defaults(self, default_rc):
        """Copy the rc dictionary into named instance variables.

        Naming them individually here, rather than keeping the raw dictionary,
        is deliberate: it puts every setting the script understands in one
        readable list, and a typo becomes a KeyError at startup instead of a
        silent None much later.
        """

        # First group of default settings.
        self.a_list = [default_rc['some'], default_rc['thing']]

        # Second group of default settings.
        self.b_list = [default_rc['first_extent'],
                       default_rc['second_extent'],
                       default_rc['third_extent']]

        # Third group of default settings.
        self.c_value = default_rc['final_thing']
        self.verbose = default_rc['verbose']

    def parse_command_line(self, command_line_args=None):
        """Build the argument parser and parse the command line."""

        program_name = '<Program Name>'

        description_text = """
<Meta data: version, date of last edit, relevant URL, requirements.>
<Description: purpose, capabilities, and limitations.>
"""

        epilog_text = """
Please contact <name> (<email>) regarding questions.
Defaults are given in ./XYZrc.py or $PROJECT_RC/XYZrc.py.
"""

        parser = ap.ArgumentParser(prog=program_name,
            formatter_class=ap.RawDescriptionHelpFormatter,
            description=description_text, epilog=epilog_text)

        self.add_parser_arguments(parser)

        # Passing None here makes argparse read sys.argv, which is what happens
        # in normal use; the test suite passes a list.
        return parser.parse_args(command_line_args)

    def add_parser_arguments(self, parser):
        """Declare every command-line option.

        Each default is the value already resolved from the rc file, so the help
        text shows the user what they will actually get rather than a hard-coded
        constant.
        """

        parser.add_argument('-x', '--xyz-x', nargs=2, dest='a_list', type=str,
            default=self.a_list,
            help=f'Argument a_list. Default: {self.a_list}')

        parser.add_argument('-y', '--xyz-y', nargs=3, dest='b_list', type=float,
            default=self.b_list,
            help=f'Argument b_list. Default: {self.b_list}')

        parser.add_argument('-c', '--xyz-c', dest='c_value', type=float,
            default=self.c_value,
            help=f'Argument c_value. Default: {self.c_value}')

        # A switch whose rc default may be either state needs both halves
        # declared, so that a user can turn it back off when the rc file has
        # turned it on. `dest` ties them together.
        parser.add_argument('-v', '--verbose', dest='verbose',
            action='store_true', default=self.verbose,
            help=f'Report progress. Default: {self.verbose}')
        parser.add_argument('-q', '--quiet', dest='verbose',
            action='store_false', help='Suppress progress reporting.')

        parser.add_argument(
            'filename', help='Name of the file to operate on.')

    def reconcile(self, args):
        """Overwrite the rc defaults with the parsed arguments.

        The lists are deep-copied so that later mutation of a setting cannot
        reach back into the parsed namespace or into the rc dictionary and
        change it underneath another reader.
        """

        self.a_list = copy.deepcopy(args.a_list)
        self.b_list = copy.deepcopy(args.b_list)
        self.c_value = args.c_value
        self.verbose = args.verbose
        self.filename = args.filename


def main(command_line_args=None):
    """Run the script.

    Accepting command_line_args lets the test suite call main() directly with a
    synthetic argument list instead of manipulating sys.argv, which is fragile
    and leaks state between tests.
    """

    # Resolve settings from the rc file and the command line.
    settings = ScriptSettings(command_line_args)

    # Start executing the main activities of the program. Call into the library
    # under src/<package>/; do not implement the algorithm here.

    # Finalize the program activities and quit.

    return 0


if __name__ == '__main__':
    # Everything above this point was a definition or an import. Only now does
    # the program actually start running. Keeping it this way lets another
    # Python program import this script and call its functions internally.

    # Log the invocation from here, at the real entry point, so the logged argv
    # is the true one and so importers and tests never write stray `command`
    # files. See record_command() above.
    record_command()

    sys.exit(main())
