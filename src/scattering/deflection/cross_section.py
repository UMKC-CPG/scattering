"""The differential cross section from the deflection table
(pseudocode 5.5, design 5.5).

For a uniform-flux beam the particles in the annulus [b, b + db]
scatter into the cone [theta(b + db), theta(b)], and the ratio of
the annulus area to the cone's solid angle is

##   dsigma/dOmega(theta) = (b / sin theta) |db / dtheta|         (5.5)

Three nodes need care and are flagged: the head-on node (b = 0 and
sin theta = 0 together; the limit is finite and is extrapolated in
log(dsdo) against (pi - theta)^2 from the two nearest nodes), a node
where dTheta/db = 0 (a
rainbow; the cross section diverges), and a non-monotone table (a
well; several b scatter to one theta and (5.5) is a sum over
branches), which the first version refuses rather than mishandles.

Attribution: this module is part of the scattering teaching tool.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CrossSectionTable:
    """dsigma/dOmega tabulated against theta, ascending, at one
    energy, in units of the reference length squared."""
    energy: float
    theta: np.ndarray
    dsdo: np.ndarray
    flags: np.ndarray
    theta_min: float
    theta_head: float


def build_cross_section_table(table):
    """Eq. (5.5) on every node of a DeflectionTable."""
    if not table.monotone:
        raise ValueError('non-monotone deflection function (a rainbow or '
                         'a well): not supported in this version')
    theta = np.abs(table.deflection)
    count = len(theta)
    flags = np.array(['ok'] * count, dtype=object)
    dsdo = np.empty(count)
    for index in range(count):
        impact = table.impact[index]
        slope = table.d_deflection[index]
        if impact == 0.0:
            dsdo[index] = np.nan
            flags[index] = 'extrapolated'
        elif slope == 0.0:
            dsdo[index] = np.inf
            flags[index] = 'rainbow'
        else:
            dsdo[index] = (impact / np.sin(theta[index])) / abs(slope)
    head = np.nonzero(flags == 'extrapolated')[0]
    if head.size:
        # The two smallest positive-b nodes, extrapolated linearly in
        # log(dsdo) against (pi - theta)^2 to the head-on angle. Near
        # back-scattering the cross section is even in (pi - theta),
        # so log(dsdo) is quadratic in it and linear in its square;
        # extrapolating in theta itself would be first order and, at
        # the default grid, a thousand times less accurate.
        finite = np.nonzero((table.impact > 0.0) & (flags == 'ok'))[0][:2]
        if finite.size == 2:
            log_values = np.log(dsdo[finite])
            squared = (np.pi - theta[finite]) ** 2
            slope = (log_values[1] - log_values[0]) / (squared[1] - squared[0])
            target = (np.pi - theta[head]) ** 2
            dsdo[head] = np.exp(log_values[0] + slope * (target - squared[0]))
    order = np.argsort(theta)
    return CrossSectionTable(table.energy, theta[order], dsdo[order],
                             flags[order], float(theta.min()),
                             float(theta.max()))


def dsdo_at(xsec, theta_query):
    """Interpolate the table in log(dsdo) against theta, using the
    ok nodes only. The cross section spans decades and is smooth in
    the log where it is not in the value."""
    ok = xsec.flags == 'ok'
    return np.exp(np.interp(theta_query, xsec.theta[ok],
                            np.log(xsec.dsdo[ok])))
