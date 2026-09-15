#!/usr/bin/env python3

"""Resource-control defaults for XYZ.py.

TEMPLATE: rename alongside its script, to <name>rc.py.

This file holds the hard defaults for every setting XYZ.py understands. It is
looked up first in the working directory and then in $PROJECT_RC, so a user can
copy it next to their data and edit it without touching the installed version.

It is a plain Python module rather than a data file on purpose: a default can be
computed, and the comments explaining each setting sit right beside the value
they explain.

This file has no `main()` and is never run as an entry point, so it does not log
to `command` the way XYZ.py does.
"""


def parameters_and_defaults():
    """Return the dictionary of default parameter values.

    Every key here must be consumed by ScriptSettings in the paired script. A
    key added here and not read there is dead; a key read there and missing here
    is a KeyError at startup, which is the intended, loud failure.
    """

    param_dict = {
        # A pair of strings, consumed as a_list.
        'some': 'Foo',
        'thing': 'Bar',

        # A triple of reals, consumed as b_list. Units: <state them>.
        'first_extent': 1.0,
        'second_extent': 2.0,
        'third_extent': 3.0,

        # A single real, consumed as c_value.
        'final_thing': 1.1,

        # A switch. T (F) = the property is (is not) requested.
        'verbose': False,
    }

    return param_dict


if __name__ == '__main__':
    # Running this file directly prints the defaults, which is a convenient way
    # to check what the script will start from.
    print(parameters_and_defaults())
