# Pseudocode 1. Natural Units, Scaling, and Presets

> **Parent:** [`../PSEUDOCODE.md`](../PSEUDOCODE.md) — index.
> **Specifies:** design section 1,
> [`../design/01-natural-units.md`](../design/01-natural-units.md).
> **Governs:** `src/scattering/core/natural_units.py`,
> `src/scattering/core/units.py`, `src/scattering/core/presets.py`.
> **Status:** draft.

---

## 1.1 Records

```
record ReferenceScales:
    mass              m          [kg]
    energy            E_ref      [J]
    length            ell_0      [m]
    speed             v_0 = sqrt(E_ref / m)              (D1.2)
    time              t_0 = ell_0 / v_0
    angular_momentum  L_0 = m * v_0 * ell_0
    display_units     map dimension -> unit string, from the preset

record Preset:
    name              str
    kind              potential kind, "coulomb" in v1
    sign              +1 or -1
    kappa             pint quantity [energy * length], or None
    kappa_per_mass    pint quantity [length^3 / time^2], or None
                      (gravity: kappa = kappa_per_mass * m; m cancels)
    mass              pint quantity [mass], or None
    reference_energy  pint quantity [energy]
    display_units     map dimension -> unit string
    note              text shown on screen (the v_inf / c ratio, the
                      equivalence-principle remark)
```

Exactly one of `kappa` and `kappa_per_mass` is set. When
`kappa_per_mass` is set and `mass` is `None`, the mass is a dummy
`1 kg` and the display never shows it (D1.5).

---

## 1.2 Presets

```
PRESETS = {
  "alpha_on_gold":
      Z1 = 2, Z2 = 79
      kappa   = Z1 * Z2 * e^2 / (4 pi eps_0)        # scipy.constants
      mass    = m_alpha                              # scipy.constants
      reference_energy = 5.0 MeV
      sign = +1
      display_units = {energy: "MeV", length: "fm",
                       mass: "MeV/c^2", speed: "c", time: "s"}
      note = "v_inf / c = {v_inf_over_c:.3f}; non-relativistic"

  "interstellar_visitor":
      kappa_per_mass = -G * M_sun                    # IAU GM_sun
      mass = None
      v_inf = 26 km/s
      reference_energy = 0.5 * (1 kg) * v_inf^2     # per unit mass
      sign = -1
      display_units = {energy: "J/kg" (per unit mass), length: "AU",
                       speed: "km/s", time: "day"}
      note = "orbit independent of projectile mass (equivalence
              principle)"
}
```

Every constant is read from `scipy.constants` at import; none is a
typed literal (D1.4). The test suite compares the computed `kappa`
and `ell_0` against the approximate values in D1.5 to 1 %.

---

## 1.3 Building the scales

```
function build_scales(potential_table, first_energy) -> ReferenceScales:
    # potential_table is the resolved [potential] table (D10.5);
    # first_energy is energies[0] as a pint quantity.

    if potential_table.preset is not None:
        preset = PRESETS[potential_table.preset]      # KeyError -> load
                                                      #   error naming it
    else:
        preset = empty Preset

    # Explicit keys override the preset (D10.3).
    kappa  = potential_table.kappa   or preset.kappa
    mass   = potential_table.mass    or preset.mass
    kpm    = preset.kappa_per_mass   if kappa is None else None
    E_ref  = potential_table.reference_energy or preset.reference_energy
             or first_energy

    if kappa is None and kpm is None:
        fail "no kappa: give [potential].kappa or a preset"
    if kappa is None:                     # gravity: mass cancels
        mass  = mass or (1 kg)
        kappa = kpm * mass
    if mass is None:
        fail "no mass: give [potential].mass or a preset"

    assert mass > 0, E_ref > 0, |kappa| > 0     # D1.6

    ell_0 = potential_table.reference_length
    if ell_0 is None:
        ell_0 = potential.default_reference_length(kappa, E_ref)
        #   Coulomb: |kappa| / E_ref                     (D1.3)

    v_0 = sqrt(E_ref / mass)
    return ReferenceScales(mass, E_ref, ell_0, v_0, ell_0 / v_0,
                           mass * v_0 * ell_0,
                           preset.display_units or SI defaults)
```

`E_ref` defaults to the *first* energy, not the smallest, so that a
teacher's deliberate ordering (D3.2) sets the scale.

---

## 1.4 The units boundary

`core/units.py` is the only module that imports pint (A6.6). It
holds one module-level `UnitRegistry`.

```
DIMENSION_SCALE = {           # which reference scale divides which
    "energy": scales.energy,  "length": scales.length,
    "mass": scales.mass,      "speed": scales.speed,
    "time": scales.time,      "angular_momentum": scales.angular_momentum,
    "energy*length": scales.energy * scales.length,     # kappa
    "area": scales.length^2 }                           # cross section

function to_natural(value, dimension, scales) -> float:
    # value: a pint quantity, a string like "5 MeV", or a bare number.
    if value is a bare number:
        return float(value)                 # already natural (D10.3)
    quantity = parse(value)                 # pint; a bad string raises
                                            #   with pint's own message
    expected = DIMENSION_SCALE[dimension]
    if quantity.dimensionality != expected.dimensionality:
        fail f"{dimension} expected, got {quantity.dimensionality}"
    return float((quantity / expected).to_base_units().magnitude)

function to_natural_list(values, dimension, scales) -> array:
    # All bare or all dimensioned; mixing is an error (D10.3).
    kinds = {is_bare(v) for v in values}
    if len(kinds) > 1: fail "mixed bare and dimensioned values"
    return array(to_natural(v, dimension, scales) for v in values)

function from_natural(value, dimension, scales) -> pint quantity:
    quantity = value * DIMENSION_SCALE[dimension]
    unit = scales.display_units.get(dimension)
    if unit is None:
        return quantity.to_base_units()     # SI fallback, label says so
    return quantity.to(unit)

function format_natural(value, dimension, scales, digits=4) -> str:
    q = from_natural(value, dimension, scales)
    return f"{q.magnitude:.{digits}g} {q.units:~}"   # e.g. "45.5 fm"
```

Nothing below `run/` calls any of these; the driver converts the
run file once on load, and the renderer converts for display. The
architectural test walks the import graph and asserts that only
`core/units.py` imports pint (A8.6(2)).

---

## 1.5 Natural-unit helpers

`core/natural_units.py` holds the small relations every stage uses,
so that the factor of two lives in one place (D1.2):

```
function asymptotic_speed(energy) -> float:        return sqrt(2 * energy)
function angular_momentum(energy, impact) -> float:
    return sqrt(2 * energy) * impact
function kinetic_energy(speed) -> float:           return 0.5 * speed^2
function energy_from_speed(speed, potential_value) -> float:
    return 0.5 * speed^2 + potential_value
```

---

## 1.6 Verification

- `build_scales` on each preset reproduces D1.5's `kappa`, `ell_0`,
  and `v_inf / c` (alpha) to 1 %: `tests/unit/test_natural_units.py`.
- `to_natural("45.5 fm", "length", alpha_scales)` is `1.0` to the
  precision of the constants; `to_natural(1.0, "length", …)` is
  exactly `1.0`.
- `to_natural("5 MeV", "length", …)` raises, and the message names
  both dimensions.
- `to_natural_list(["1 fm", 2.0], …)` raises.
- `from_natural(to_natural(x))` round-trips to `1e-12` for every
  dimension in `DIMENSION_SCALE`.
- The pint import test of A8.6(2): `tests/unit/test_architecture.py`.
