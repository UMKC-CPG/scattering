"""The planar equations of motion in a central potential (pseudocode
4.5, design 4.3).

Central-force motion is planar, so each particle is integrated in its own
orbital plane as a two-degree-of-freedom problem. The coordinates are Cartesian
in that plane -- x_p transverse to the beam, y_p along it -- rather than polar,
because dphi/dt = L / r^2 is stiff at the small-b attractive pericenter and the
radial equation has a coordinate singularity at r = 0; Cartesian coordinates
have neither (design 4.11). The polar coordinates the display shows are derived
from the state afterwards.

With unit mass (design 1.2) the acceleration is -dV/dr times the
unit radial vector:

##   d x_p / dt = v_x      d v_x / dt = -(dV/dr) x_p / r
##   d y_p / dt = v_y      d v_y / dt = -(dV/dr) y_p / r         (4.1)

Attribution: this module is part of the scattering teaching tool.
"""

import numpy as np


def equations_of_motion(potential):
    """Return the right-hand side f(t, state) of eq. (4.1) for the
    given potential, in the form scipy.integrate.solve_ivp expects.
    The state is (x_p, y_p, v_x, v_y)."""

    def right_hand_side(_time, state):
        x_position, y_position, x_velocity, y_velocity = state
        radius = np.hypot(x_position, y_position)
        # Radial acceleration divided by r, so that multiplying by each
        # coordinate gives that coordinate's acceleration.
        radial_over_r = -potential.derivative(radius) / radius
        return [x_velocity, y_velocity,
                radial_over_r * x_position, radial_over_r * y_position]

    return right_hand_side
