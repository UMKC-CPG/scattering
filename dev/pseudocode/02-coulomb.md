# Pseudocode 2. The Potential Interface and the Coulomb Potential

> **Parent:** [`../PSEUDOCODE.md`](../PSEUDOCODE.md) — index.
> **Specifies:** design section 2,
> [`../design/02-coulomb-closed-forms.md`](
> ../design/02-coulomb-closed-forms.md),
> and the potential boundary of ARCHITECTURE A6.1.
> **Governs:** `src/scattering/potentials/potential_interface.py`,
> `src/scattering/potentials/coulomb.py`.
> **Status:** draft. Every closed form below is verified by
> `dev/spikes/coulomb_closed_forms.py`.

---

## 2.1 The potential interface (A6.1)

All quantities in natural units (P1). `energy` is `Ẽ`, `impact` is
`b̃`, `radius` is `r̃`.

```
protocol Potential:
    # Required.
    value(radius) -> float                  # V~(r~)
    derivative(radius) -> float             # dV~/dr~
    admits_center() -> bool                 # is b~ = 0 an orbit?
    default_reference_length(kappa, E_ref) -> pint length   (D1.3)
    describe() -> str                       # for labels

    # Optional capabilities. A consumer tests `has_closed_form_*`
    # and never the potential's type (P12).
    has_closed_form_deflection -> bool
    closed_form_deflection(energy, impact) -> float         # signed Theta
    has_closed_form_orbit -> bool
    closed_form_orbit(energy, impact) -> AnalyticOrbit      # P4.4
    asymptotic_state(energy, impact, radius) -> (x_p, y_p, v_x, v_y)
                                                            # D4.4
    has_mirror -> bool
    mirror() -> Potential                   # the sign-flipped potential
```

`value` and `derivative` accept scalars and arrays alike (the
deflection quadrature calls them scalar-wise; the conservation
monitor calls them on whole sample arrays).

---

## 2.2 The Coulomb potential

```
class CoulombPotential(Potential):
    sign: +1 or -1                          # s

    value(r):        return sign / r
    derivative(r):   return -sign / r^2
    admits_center(): return sign == +1                       (D2.3)
    default_reference_length(kappa, E_ref): return |kappa| / E_ref
    describe():      return "repulsive Coulomb" if sign > 0
                            else "attractive Coulomb"
    has_closed_form_deflection = True
    has_closed_form_orbit      = True
    has_mirror                 = True
    mirror():        return CoulombPotential(-sign)
```

### Closed forms (D2.2–D2.5)

```
function eccentricity(energy, impact) -> float:
    return sqrt(1 + (2 * energy * impact)^2)                  (2.2)

function turning_point(sign, energy, impact) -> float:
    e = eccentricity(energy, impact)
    return (e + sign) / (2 * energy)                          (2.3)
    # NOT 2 E b^2 / (e - s): that form is 0/0 at b = 0.

function closed_form_deflection(energy, impact) -> float:
    if impact == 0:
        if sign < 0: fail "attractive Coulomb has no b = 0 orbit"
        return pi
    return 2 * atan(sign / (2 * energy * impact))             (2.8)

function impact_of_angle(energy, theta) -> float:           # theta in (0, pi]
    return cot(theta / 2) / (2 * energy)                      (2.9)

function closed_form_cross_section(energy, theta) -> float:
    return 1 / (16 * energy^2 * sin(theta / 2)^4)             (2.11)

function asymptote_angle(sign, energy, impact) -> float:    # phi_inf
    return acos(sign / eccentricity(energy, impact))          (2.5)
```

---

## 2.3 The analytic orbit (D2.6)

```
record AnalyticOrbit:
    sign, energy, impact
    eccentricity      e
    semi_major        a = 1 / (2 energy)
    turning_point     r_min
    asymptote_angle   phi_inf
    deflection        Theta
    coeff             k = sqrt((e - sign) / (e + sign))     # for phi(H)
```

Note `k` collapses D2.6's two cases: `s = -1` gives
`sqrt((e+1)/(e-1))`, `s = +1` gives `sqrt((e-1)/(e+1))`.

```
function radius_of_anomaly(orbit, H) -> float:
    return orbit.a * (orbit.e * cosh(H) + orbit.sign)          (2.12)

function time_of_anomaly(orbit, H) -> float:
    return orbit.a^1.5 * (orbit.e * sinh(H) + orbit.sign * H)  (2.12)

function polar_of_anomaly(orbit, H) -> float:               # phi
    return 2 * atan(orbit.coeff * tanh(H / 2))                (2.12)

function anomaly_of_time(orbit, t) -> float:
    # Invert t(H) by Newton; t(H) is monotone and near-exponential.
    H = asinh(t / (orbit.a^1.5 * orbit.e))                     # start
    repeat up to 50 times:
        f  = time_of_anomaly(orbit, H) - t
        df = orbit.a^1.5 * (orbit.e * cosh(H) + orbit.sign)    # dt/dH > 0
        step = f / df
        H = H - step
        if |step| < 1e-14 * max(1, |H|): break
    else: fail "anomaly_of_time did not converge"   # cannot happen for
                                                     #   e >= 1; guard anyway
    return H

function anomaly_of_radius(orbit, radius, outbound) -> float:
    # cosh H = (r/a - s) / e ; sign of H by direction.
    c = (radius / orbit.a - orbit.sign) / orbit.e
    if c < 1: fail "radius inside the turning point"
    H = acosh(c)
    return H if outbound else -H

function state_at_anomaly(orbit, H) -> (x_p, y_p, v_x, v_y):
    # In-plane state in the PERICENTER frame: x along the pericenter
    # direction, y perpendicular, phi measured from x.
    r   = radius_of_anomaly(orbit, H)
    phi = polar_of_anomaly(orbit, H)
    dr_dH   = orbit.a * orbit.e * sinh(H)
    dt_dH   = orbit.a^1.5 * (orbit.e * cosh(H) + orbit.sign)
    dphi_dH = orbit.coeff / cosh(H/2)^2 / (1 + (orbit.coeff * tanh(H/2))^2)
    r_dot   = dr_dH / dt_dH
    phi_dot = dphi_dH / dt_dH
    x_p = r * cos(phi);            y_p = r * sin(phi)
    v_x = r_dot * cos(phi) - r * phi_dot * sin(phi)
    v_y = r_dot * sin(phi) + r * phi_dot * cos(phi)
    return (x_p, y_p, v_x, v_y)
```

### From the pericenter frame to the beam frame

The beam frame of D4.3 has the incoming asymptote along `+ŷ_p`
(the beam axis) at transverse offset `+b̃` on `x̂_p`; the particle
moves counterclockwise (`L̃ = x_p v_y − y_p v_x = b̃ ṽ_∞ > 0`). The
pericenter frame above has the pericenter on `+x̂` and, since
`dφ/dH > 0`, is also counterclockwise. So the two differ by a pure
rotation, with no reflection, for either sign.

At large `r` on the incoming asymptote `φ → −φ_∞`, the position is
along `(cos φ_∞, −sin φ_∞)` and the velocity points inward along
that ray: `u_in = (−cos φ_∞, sin φ_∞) = (cos(π − φ_∞), sin(π − φ_∞))`.
Rotating `u_in` onto `(0, 1)` needs the angle

```
  alpha = pi/2 − (pi − phi_inf) = phi_inf − pi/2                (2.13)
```

For `s = +1`, `φ_∞ < π/2` and the rotation is clockwise: the
pericenter lands in the fourth quadrant (`x_p > 0`, `y_p < 0`),
which is where a repelled particle approaching from `−y` is closest
to the center. For `s = −1`, `φ_∞ > π/2` and the pericenter lands
in the first quadrant, which is where an attracted particle that
has begun to wrap the center passes it. Both limits `b̃ → ∞` give
`α → 0` and the pericenter at `(b̃, 0)`, as they must.

```
function pericenter_to_beam_rotation(orbit) -> 2x2 matrix:
    alpha = orbit.phi_inf - pi / 2
    return [[cos alpha, -sin alpha],
            [sin alpha,  cos alpha]]

function asymptotic_state(energy, impact, radius) -> state in beam frame:
    orbit = closed_form_orbit(energy, impact)
    H = anomaly_of_radius(orbit, radius, outbound=False)
    R = pericenter_to_beam_rotation(orbit)
    (x, y, vx, vy) = state_at_anomaly(orbit, H)
    return (R @ (x, y), R @ (vx, vy))
```

The verification below pins the sign conventions numerically
rather than trusting this derivation: a wrong `α` puts the exit on
the wrong side of the axis, and D4.8 says which side is right.

---

## 2.4 Head-on and the forbidden center

```
if impact == 0:
    if sign < 0: fail at beam generation (P3.4), never here
    # e = 1, k = 0: polar_of_anomaly returns 0 for every H;
    # radius_of_anomaly = a (cosh H + 1), time_of_anomaly fine.
    # Nothing special-cased; the formulas degrade gracefully (D2.6).
```

---

## 2.5 Verification

`tests/unit/test_coulomb.py`, mirroring the spike:

- `turning_point` two forms agree away from `b = 0`; at `b = 0`,
  repulsive gives `1 / energy`.
- `closed_form_deflection(E, b; -1) == -closed_form_deflection(E, b; +1)`
  to `1e-15`.
- `closed_form_cross_section` equals `(b / sin θ) |db/dθ|` from
  `impact_of_angle` by finite difference, to `1e-8`.
- Along `H ∈ [-5, 5]`: `radius_of_anomaly(H)` equals (2.1) at
  `polar_of_anomaly(H)` to `1e-12`; energy and angular momentum
  from `state_at_anomaly` equal `E` and `sqrt(2E) b` to `1e-12`.
- `anomaly_of_time(time_of_anomaly(H)) == H` to `1e-12` over the
  same range.
- **Beam-frame check:** `asymptotic_state(E, b, R)` for large `R`
  has `x_p → +b`, `v_x → 0`, `v_y → +sqrt(2E)` to `O(1/R)`; and
  integrating (4.1) from that state to the exit (P4) gives a final
  velocity direction agreeing with `closed_form_deflection` to the
  integrator tolerance, with the exit `x_p` positive for `s = +1`
  and negative for `s = −1` (D4.8). This is the test that catches a
  wrong reflection in `pericenter_to_beam_rotation`.
- The turning-point product `r_min(+) r_min(−) = b²` (D2.4).
