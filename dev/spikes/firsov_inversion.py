#!/usr/bin/env python3

"""Verify the inverse-scattering chain of dev/design/08 numerically.

This is a spike (see dev/spikes/README.md). The question: is the
Firsov inversion of the classical deflection integral, as it will be
written into design section 8, correct as derived here -- and how
does it degrade under the two things a real detector imposes, a
finite maximum impact parameter and finite counts?

The chain tested, in the natural units of design section 1 (unit
mass, V = s / r for Coulomb, E the beam energy):

  counts N_i  ->  dsigma/dOmega  ->  b(theta)  ->  Theta(b)  ->  V(r)

Stage formulas (all derived in design section 8 from the deflection
integral of section 5):

  b(theta)^2 = 2 * int_theta^pi  (dsigma/dOmega)(t) sin t dt         (B)

  w(r) = r sqrt(1 - V(r) / E),   the Firsov variable

  ln( r / w ) = (1/pi) int_w^inf  Theta(b) db / sqrt(b^2 - w^2)
              = (1/pi) int_0^inf  Theta(w cosh t) dt                (F)

  V(r) = E ( 1 - w^2 / r^2 )     at  r = r(w)                        (V)

Run:  python3 dev/spikes/firsov_inversion.py
"""

import warnings

import numpy as np
from scipy.integrate import IntegrationWarning, quad
from scipy.interpolate import PchipInterpolator, interp1d

# The largest t at which cosh(t) is finite in double precision; the
#   deflection at such b is zero to precision, so this truncation costs
#   nothing and silences an overflow warning.
_T_CAP = 700.0


def rutherford_deflection(sign, energy):
    """Signed Theta(b) for V = sign / r, design eq. (2.8)."""
    return lambda impact: 2.0 * np.arctan(sign / (2.0 * energy * impact))


def rutherford_cross_section(energy):
    """dsigma/dOmega(theta) for Coulomb, design eq. (2.11)."""
    return lambda theta: 1.0 / (16.0 * energy ** 2
                                * np.sin(theta / 2.0) ** 4)


def firsov_radius(deflection, firsov_w, upper_impact=np.inf,
                  break_impact=None):
    """r(w) by (F). deflection(b) may be given only up to
    upper_impact; beyond it Theta is taken as zero (truncation). If
    the model has a kink at break_impact (measured data joined to a
    tail model), the integral is split there so quad sees smooth
    pieces."""

    def t_of(impact):
        return np.arccosh(impact / firsov_w) if impact > firsov_w else 0.0

    t_max = _T_CAP if np.isinf(upper_impact) else t_of(upper_impact)
    knots = [0.0, t_max]
    if break_impact is not None and 0.0 < t_of(break_impact) < t_max:
        knots.insert(1, t_of(break_impact))
    integral = 0.0
    for lower, upper in zip(knots[:-1], knots[1:]):
        piece, _ = quad(lambda t: deflection(firsov_w * np.cosh(t)),
                        lower, upper, epsabs=1e-13, epsrel=1e-13,
                        limit=400)
        integral += piece
    return firsov_w * np.exp(integral / np.pi)


def invert_to_potential(deflection, energy, w_values, upper_impact=np.inf,
                        break_impact=None):
    """Return (r, V) arrays from Theta(b) via (F) and (V)."""
    radii = np.array([firsov_radius(deflection, w, upper_impact,
                                    break_impact)
                      for w in w_values])
    return radii, energy * (1.0 - w_values ** 2 / radii ** 2)


def impact_from_cross_section(cross_section, theta, theta_head_on=np.pi):
    """b(theta) by (B), integrating the cross section from theta up to
    the head-on angle (pi for a repulsive potential)."""
    integral, _ = quad(lambda t: cross_section(t) * np.sin(t), theta,
                       theta_head_on, epsabs=1e-13, epsrel=1e-13,
                       limit=400)
    return np.sqrt(2.0 * integral)


def check_exact_deflection():
    """(F) + (V) on the exact Rutherford Theta(b), both signs."""
    worst = 0.0
    w_values = np.geomspace(0.05, 50.0, 25)
    for sign in (+1, -1):
        for energy in (0.5, 1.0, 2.0):
            radii, potential = invert_to_potential(
                rutherford_deflection(sign, energy), energy, w_values)
            worst = max(worst, np.max(np.abs(potential - sign / radii)
                                      / np.abs(sign / radii)))
    return worst


def check_exact_cross_section():
    """(B) on the exact Rutherford cross section reproduces (2.9),
    then (F) + (V) recover V = +1 / r (the sign is an ASSUMPTION at
    this stage: a cross section carries no sign)."""
    energy = 1.0
    xsec = rutherford_cross_section(energy)
    thetas = np.linspace(0.2, 3.0, 40)
    impacts = np.array([impact_from_cross_section(xsec, t) for t in thetas])
    exact = 1.0 / np.tan(thetas / 2.0) / (2.0 * energy)
    worst_b = np.max(np.abs(impacts - exact) / exact)

    # Theta(b) from the recovered b(theta): interpolate theta(b) on a
    #   log-b grid, assuming the repulsive sign.
    theta_of_b = interp1d(np.log(impacts[::-1]), thetas[::-1],
                          kind='cubic', fill_value='extrapolate')

    def deflection(impact):
        # Outside the tabulated range fall back to the Coulomb tail
        #   shape, which is what design section 8 will do explicitly.
        if impact > impacts[0]:
            return 2.0 * np.arctan(1.0 / (2.0 * energy * impact))
        if impact < impacts[-1]:
            return np.pi
        return float(theta_of_b(np.log(impact)))

    w_values = np.geomspace(0.6, 5.0, 12)
    radii, potential = invert_to_potential(deflection, energy, w_values,
                                           break_impact=impacts[0])
    worst_v = np.max(np.abs(potential - 1.0 / radii) * radii)
    return worst_b, worst_v


def check_truncation(energy=1.0):
    """Error in V(r) from knowing Theta(b) only for b <= b_max, with
    Theta taken as ZERO beyond. Design section 8 will instead
    extrapolate the tail; this measures the cost of not doing so."""
    deflection = rutherford_deflection(+1, energy)
    rows = []
    for b_max in (4.0, 8.0, 16.0, 32.0):
        w_values = np.array([0.5, 1.0, 2.0])
        radii, potential = invert_to_potential(deflection, energy, w_values,
                                               upper_impact=b_max)
        rel = np.abs(potential - 1.0 / radii) * radii
        rows.append((b_max, radii, rel))
    return rows


def check_from_counts(energy=1.0, n_particles=200_000, b_max=12.0,
                      n_bins=40, seed=20260910):
    """The whole chain from a uniform-flux disc beam binned on a
    detector, with real Poisson scatter. Compare the recovered V(r)
    with 1 / r and report the scatter.

    Two lessons from the first attempt are built in here and belong
    in design section 7:
      * counts must be compared with the BIN-INTEGRATED expectation,
        not the cross section at the bin center -- for a theta^-4 law
        the two differ by orders of magnitude in a wide bin;
      * bins uniform in log(theta) keep every bin populated, whereas
        equal-solid-angle bins put nearly all counts in the first.
    """
    rng = np.random.default_rng(seed)
    b_min = 0.0
    # Design eq. (3.1): uniform flux.
    impacts = np.sqrt(b_min ** 2 + rng.random(n_particles)
                      * (b_max ** 2 - b_min ** 2))
    thetas = 2.0 * np.arctan(1.0 / (2.0 * energy * impacts))
    flux = n_particles / (np.pi * (b_max ** 2 - b_min ** 2))
    theta_min = 2.0 * np.arctan(1.0 / (2.0 * energy * b_max))

    # Bins uniform in log(theta) over the MEASURED range; the forward
    #   cone below theta_min is left out as unmeasured, not counted as
    #   zero.
    edges = np.geomspace(theta_min, np.pi, n_bins + 1)
    counts, _ = np.histogram(thetas, bins=edges)
    xsec = rutherford_cross_section(energy)
    expected = np.array([
        flux * 2.0 * np.pi * quad(lambda t: xsec(t) * np.sin(t), a, c)[0]
        for a, c in zip(edges[:-1], edges[1:])])
    pulls = (counts - expected) / np.sqrt(expected)

    # (B) on the binned data, exactly: b^2 at each edge is twice the
    #   cumulative (counts / flux) / (2 pi) from the large-angle end.
    per_bin = counts / flux / (2.0 * np.pi)
    b_sq_edges = np.concatenate([[0.0], np.cumsum(per_bin[::-1])])[::-1]
    b_edges = np.sqrt(2.0 * b_sq_edges)

    # Theta(b) from the edges: ascending b, monotone interpolation in
    #   log b, empty large-angle bins (repeated b) dropped. Repulsive
    #   sign ASSUMED -- the counts carry none.
    asc_b, asc_theta = b_edges[::-1], edges[::-1]
    keep = np.concatenate([[True], np.diff(asc_b) > 0.0])
    asc_b, asc_theta = asc_b[keep], asc_theta[keep]
    positive = asc_b > 0.0
    theta_of_log_b = PchipInterpolator(np.log(asc_b[positive]),
                                       asc_theta[positive])
    b_low, b_high = asc_b[positive].min(), asc_b.max()

    def deflection(impact):
        if impact >= b_high:
            # Coulomb tail assumed beyond the last measured b.
            return 2.0 * np.arctan(1.0 / (2.0 * energy * impact))
        if impact <= b_low:
            return np.pi
        return float(theta_of_log_b(np.log(impact)))

    w_values = np.geomspace(0.35, 6.0, 10)
    radii, potential = invert_to_potential(deflection, energy, w_values,
                                           break_impact=b_high)
    rel = (potential - 1.0 / radii) * radii
    return dict(theta_min=theta_min, n_bins=n_bins,
                empty_bins=int(np.sum(counts == 0)),
                pull_rms=np.sqrt(np.mean(pulls ** 2)),
                radii=radii, rel=rel, r_min_reach=1.0 / energy)


def main():
    # An interpolated Theta(b) has knots that quad reports as roundoff
    #   limits; the achieved accuracy is far beyond what the checks
    #   below need, so the warning is noise here.
    warnings.simplefilter('ignore', IntegrationWarning)
    print('(F)+(V) on exact Rutherford Theta(b), both signs, worst '
          f'rel err in V: {check_exact_deflection():.2e}')
    worst_b, worst_v = check_exact_cross_section()
    print(f'(B) on exact cross section: b(theta) worst rel err '
          f'{worst_b:.2e}; V(r) via interpolated Theta: {worst_v:.2e}')

    print('\nTruncating Theta(b) to zero beyond b_max (no tail model):')
    for b_max, radii, rel in check_truncation():
        cells = '  '.join(f'r={r:5.2f}: {e:.1e}' for r, e in zip(radii, rel))
        print(f'  b_max={b_max:4.0f}   {cells}')

    print('\nFrom binned counts, b_max=12, 40 log-theta bins, repulsive '
          'sign assumed:')
    for n_particles in (20_000, 200_000, 2_000_000):
        result = check_from_counts(n_particles=n_particles)
        rel = result['rel']
        print(f"  N={n_particles:8d}: pull rms {result['pull_rms']:.2f} "
              f"(1.0 = Poisson), empty bins {result['empty_bins']}, "
              f"V(r) rel err rms {np.sqrt(np.mean(rel ** 2)):.1e} "
              f"max {np.max(np.abs(rel)):.1e}")
    print(f"  reach limit r_min = {result['r_min_reach']:.2f}; recovered "
          f"radii from {result['radii'][0]:.2f} to {result['radii'][-1]:.2f}")
    print('  V(r) rel err by radius at N=2e6: '
          + ' '.join(f'{e:+.1e}' for e in rel))


if __name__ == '__main__':
    main()
