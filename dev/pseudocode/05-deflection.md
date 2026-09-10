# Pseudocode 5. The Deflection Function and the Cross Section

> **Parent:** [`../PSEUDOCODE.md`](../PSEUDOCODE.md) — index.
> **Specifies:** design section 5,
> [`../design/05-deflection-and-cross-section.md`](
> ../design/05-deflection-and-cross-section.md).
> **Governs:** `src/scattering/deflection/deflection_function.py`,
> `src/scattering/deflection/cross_section.py`,
> `src/scattering/deflection/solid_angle.py`, and the root-of-`g`
> routine in `src/scattering/orbits/turning_point.py`.
> **Status:** draft; the quadrature is verified by
> `dev/spikes/coulomb_closed_forms.py`.

---

## 5.1 Records

```
record DeflectionTable:              # per energy (D5.4)
    energy
    impact          array (M,)       b~ grid, ascending
    deflection      array (M,)       Theta, signed
    d_deflection    array (M,)       dTheta/db~
    turning_point   array (M,)       r~_min
    monotone        bool
    source          "closed_form" | "quadrature"
    check           float            largest |closed form - quadrature|
                                     on a subset, or NaN

record CrossSectionTable:            # per energy (D5.5)
    energy
    theta           array (M,)       ascending
    dsdo            array (M,)       dsigma/dOmega, units ell_0^2
    flags           array (M,) of {ok, extrapolated, rainbow}
    theta_min, theta_head            the measured range (D7.3)

record AnnulusMap:                   # per annulus per energy (D5.7)
    impact, width
    area            Delta A
    theta_1, theta_2
    solid_angle     Delta Omega
    ratio           Delta A / Delta Omega
    dsdo_mid        dsigma/dOmega at the annulus midpoint
```

---

## 5.2 The turning point from `g` (D5.2)

```
function g(potential, energy, impact, r):
    return 1 - impact^2 / r^2 - potential.value(r) / energy       (5.2)

function g_prime(potential, energy, impact, r):
    return 2 * impact^2 / r^3 - potential.derivative(r) / energy  (5.4)

function turning_point_from_g(potential, energy, impact) -> (r_min, orbiting):
    if impact == 0 and potential.admits_center():
        # Radial motion: the root of V(r) = E.
        r_min = brentq(lambda r: potential.value(r) - energy, tiny, big)
        return (r_min, False)
    high = 1e3 * max(1.0, impact)          # g(high) ~ 1
    low  = high
    repeat: low *= 0.5 until g(low) <= 0 or low < 1e-12
    if low < 1e-12: fail "no turning point: g > 0 everywhere"
    r_min = brentq(g, low, high, xtol = 1e-15, rtol = 1e-15)
    orbiting = |g_prime(r_min)| < 1e-10 * max(1, |energy|)
    return (r_min, orbiting)
```

Marching inward by halving finds the *largest* root first (D5.2).
`orbiting = True` means a double root; the caller records
`Theta = ±inf` and the table is flagged.

---

## 5.3 The deflection integral (D5.3)

```
function deflection_by_quadrature(potential, energy, impact)
        -> (Theta, r_min, err):
    if impact == 0:
        return (pi, turning_point_from_g(...).r_min, 0.0)
    (r_min, orbiting) = turning_point_from_g(potential, energy, impact)
    if orbiting:
        return (copysign(inf, -potential.derivative(r_min)), r_min, 0.0)
    gp0 = g_prime(potential, energy, impact, r_min)
    def integrand(rho):
        if rho == 0.0:
            return 1 / (sqrt(gp0) * r_min^2)          # the limit (D5.3)
        r = r_min + rho^2
        return rho / (r^2 * sqrt(g(potential, energy, impact, r)))
    (I, err) = scipy.integrate.quad(integrand, 0, inf,
                                    epsabs = 1e-12, epsrel = 1e-12,
                                    limit = 200)
    return (pi - 4 * impact * I, r_min, err)                    (5.3)
```

---

## 5.4 Per-particle deflection and the table (D5.4)

```
function deflection_of(potential, energy, impact):
    if potential.has_closed_form_deflection:
        return potential.closed_form_deflection(energy, impact)
    return deflection_by_quadrature(potential, energy, impact).Theta

function d_deflection_of(potential, energy, impact, delta = 1e-4):
    # Centered difference on the INTEGRAL (or closed form), not on
    # the table.
    hi = deflection_of(potential, energy, impact * (1 + delta))
    lo = deflection_of(potential, energy, impact * (1 - delta))
    return (hi - lo) / (2 * impact * delta)

function build_deflection_table(potential, energy, b_min, b_max,
                                n_points, admits_center) -> DeflectionTable:
    floor = b_min if b_min > 0 else 1e-3 * b_max
    grid = geomspace(floor, b_max, n_points)
    if admits_center and b_min == 0:
        grid = concatenate([[0.0], grid])
    Theta = [deflection_of(potential, energy, b) for b in grid]
    dTheta = [d_deflection_of(potential, energy, b) if b > 0 else NaN
              for b in grid]
    r_min = [turning_point_from_g(potential, energy, b).r_min for b in grid]
    monotone = all(diff(Theta * sign(Theta[-1])) <= 0)    # |Theta| decreasing
    check = NaN
    if potential.has_closed_form_deflection:
        subset = grid[::max(1, n_points // 20)]
        check = max(|closed_form(b) - deflection_by_quadrature(b).Theta|
                    for b in subset if b > 0)
    return DeflectionTable(energy, grid, Theta, dTheta, r_min, monotone,
                           "closed_form" if potential.has_closed_form_deflection
                           else "quadrature", check)

function particle_deflections(potential, energy, impacts) -> array:
    return array(deflection_of(potential, energy, b) for b in impacts)
```

Every particle gets a direct evaluation (D5.4); no interpolation.

---

## 5.5 The cross section (D5.5)

```
function build_cross_section_table(table: DeflectionTable) -> CrossSectionTable:
    if not table.monotone:
        fail "non-monotone deflection function (rainbow or well):
              not supported in this version"
    theta = |table.deflection|
    flags = ["ok"] * M
    dsdo  = empty(M)
    for i in 0 .. M-1:
        b, dTh = table.impact[i], table.d_deflection[i]
        if b == 0:                                   # head-on node
            dsdo[i] = NaN; flags[i] = "extrapolated"; continue
        if dTh == 0:
            dsdo[i] = inf; flags[i] = "rainbow"; continue
        dsdo[i] = (b / sin(theta[i])) / |dTh|                    (5.5)
    if any(flags == "extrapolated"):
        # Head-on limit from the two nearest finite nodes, in log.
        j = the two smallest positive-b indices
        dsdo[head] = exp(extrapolate_linear(log(dsdo[j]), theta[j], pi))
    # Sort ascending in theta (the table is descending for repulsive).
    order = argsort(theta)
    return CrossSectionTable(table.energy, theta[order], dsdo[order],
                             flags[order],
                             theta_min  = min(theta),
                             theta_head = max(theta))

function dsdo_at(xsec: CrossSectionTable, theta_query) -> float:
    # Interpolate in log(dsdo) against theta, ok nodes only.
    return exp(interp(theta_query, xsec.theta[ok], log(xsec.dsdo[ok])))
```

`theta_min` and `theta_head` are written back into the beam record
(P3.1) by the driver (P6), since the beam owns "what was thrown"
and these are its consequences.

---

## 5.6 Sign independence (D5.6)

```
function mirror_check(potential, energy, table) -> (mirror_table, max_rel_diff):
    if not potential.has_mirror: return (None, NaN)
    mirror = build_deflection_table(potential.mirror(), energy, ...)
                                                          # same grid
    xs   = build_cross_section_table(table)
    xs_m = build_cross_section_table(mirror)
    diff = max(|xs.dsdo - xs_m.dsdo| / xs.dsdo over ok nodes)
    return (mirror, diff)
```

---

## 5.7 The annulus-to-cone map (D5.7)

```
function annulus_map(potential, energy, annulus: AnnulusSpec, xsec)
        -> AnnulusMap:
    b, db = annulus.impact, annulus.width
    area = pi * ((b + db)^2 - b^2)
    theta_1 = |deflection_of(potential, energy, b + db)|
    theta_2 = |deflection_of(potential, energy, b)|
    solid_angle = 2 * pi * |cos(theta_1) - cos(theta_2)|           (5.6)
    mid = |deflection_of(potential, energy, b + db / 2)|
    return AnnulusMap(b, db, area, theta_1, theta_2, solid_angle,
                      area / solid_angle, dsdo_at(xsec, mid))
```

---

## 5.8 Per-particle outputs (D5.8)

```
function particle_outputs(potential, energy, beam) -> record:
    Theta  = particle_deflections(potential, energy, beam.impact_parameter)
    theta  = |Theta|
    n_out  = out_direction(Theta, beam.azimuth)                 # P4.8
    r_min  = [turning_point_from_g(potential, energy, b).r_min
              for b in beam.impact_parameter]
    return (deflection = Theta, scattering_angle = theta,
            out_direction = n_out, turning_point_q = r_min)
```

---

## 5.9 Verification

`tests/unit/test_deflection.py`:

- `deflection_by_quadrature` vs `closed_form_deflection` on Coulomb,
  both signs, `E ∈ {0.3, 1, 3}`, `b ∈ {0.05 … 50}`: `≤ 1e-10`
  (spike: `2e-12`).
- `turning_point_from_g` vs (2.3): `≤ 1e-12` relative.
- `orbiting` is `False` for every Coulomb case; a synthetic
  potential with a barrier (`V = 1/r − 2/r² + …`, test-only) yields
  `True` at the critical `b`.
- `build_cross_section_table` on Coulomb reproduces (2.11) to
  `1e-8` at `ok` nodes and to `1e-4` at the extrapolated head-on
  node.
- The table is refused (raises) for a synthetic non-monotone
  `Theta`.
- `mirror_check` on Coulomb returns `max_rel_diff ≤ 1e-14`.
- `annulus_map`: `ratio → dsdo_mid` as `db → 0`, second order
  (halving `db` quarters the difference, ± 10 %).
- `particle_outputs`: `theta_min` of the beam equals
  `|deflection_of(b_max)|`; `n_out` is unit and has `z = cos(Theta)`.
