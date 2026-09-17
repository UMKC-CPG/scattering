# Pseudocode 10. The Run File

> **Parent:** [`../PSEUDOCODE.md`](../PSEUDOCODE.md) — index.
> **Specifies:** design section 10,
> [`../design/10-run-file.md`](../design/10-run-file.md).
> **Governs:** `src/scattering/run/run_spec.py`,
> `src/scattering/run/serialization.py`,
> `src/scattering/run/schema.py`, `src/scattering/run/rc.py`,
> `src/scattering/defaults/scsimrc.py`; and the resolution step that
> `src/scattering/run/driver.py` hands over (10.2).
> **Status:** draft.

---

## 10.1 What exists, and what this section adds

`run/run_spec.py` already holds `PotentialSpec`, `FidelitySpec`,
`RunSpec`, and `RcSettings` (pseudocode 6.3), and the driver
consumes a `RunSpec` whose beam quantities arrive *as loaded* and
converts them itself (`resolve_beam_units`, pseudocode 6.4). This
section adds the TOML path around those records and moves the
conversion into a resolution step, as pseudocode 6.3 said it would.

New records:

```
record DetectorSpec:                # [detector], D10.5
    radius        float, multiple of r_max     default 2.0
    mode          "asymptotic" | "position"    default "asymptotic"
    layout        "log_theta" | "uniform_theta" | "equal_solid_angle"
                                               default "log_theta"
    n_bins        int                          default 40
    n_phi         int                          default 1

record InversionSpec:               # [inversion]
    enabled       bool          default: layout == "disc"
    assume_sign   +1 | -1       default +1
    tail_model    "coulomb" | "power" | "zero"   default "coulomb"
    n_resample    int           default 50

record ViewSpec:                    # [view], presentation zone
    palette           "light" | "dark" | "colorblind"   default rc
    camera            {azimuth_deg, elevation_deg, distance} default rc
    tracked_particle  int       default 0
    panels            list of panel names       default rc

record MetaSpec:                    # [meta], written on resolve
    resolved_by   str;  source  str | None;  git_commit  str | None

record RunSpec:                     # extended
    schema        int = 1
    potential     PotentialSpec
    beam          BeamSpec           quantities AS LOADED
    detector      DetectorSpec
    inversion     InversionSpec
    fidelity      FidelitySpec      r_max AS LOADED
    view          ViewSpec
    meta          MetaSpec | None
    # `detector_radius` of pseudocode 6.3 becomes detector.radius.

record ResolvedRun:                 # frozen; what the driver consumes
    spec          RunSpec           every key present, every quantity
                                    converted to natural units
    potential     the Potential object (P2)
    scales        ReferenceScales (P1)
    settings      OrbitSettings (P4.1), entry_plane_z = r_max
    detector_radius   float         in natural units
    estimate_bytes    int           the budget (P6.2)
```

---

## 10.2 Seam inventory: the driver hands over resolution

The driver's first six lines (pseudocode 6.4) become the body of
`resolve` below, and the driver takes a `ResolvedRun`. For every
quantity the driver consumes after this change:

- `potential`: was `make_potential(spec.potential)` in the driver;
  becomes `resolved.potential`.
- `scales`: was `build_scales(...)` in the driver; becomes
  `resolved.scales`.
- natural-unit `BeamSpec`: was `resolve_beam_units(...)` in the
  driver; becomes `resolved.spec.beam`.
- `r_max`: was `to_natural(spec.fidelity.r_max)` in the driver;
  becomes `resolved.settings.r_max`.
- `OrbitSettings`: was built in the driver; becomes
  `resolved.settings`.
- `r_detect`: was `spec.detector_radius * r_max`; becomes
  `resolved.detector_radius`.
- the budget: was `check_budget(spec, rc)` in the driver; checked in
  `resolve`, with the value in `resolved.estimate_bytes`.

`resolve_beam_units` moves to `run_spec.py` unchanged. The driver's
`build_results_store(resolved, progress)` starts at
`generate_beam(resolved.spec.beam, resolved.potential)`. The store's
`run_spec` provenance field holds `resolved.spec`. Every existing
test that builds a `RunSpec` in code calls `resolve(spec)` first;
the records they build are unchanged except that `detector_radius`
becomes `detector=DetectorSpec(radius=...)`.

---

## 10.3 The schema as data

`run/schema.py` holds one table that validation, defaults, the
`--set` parser, and write-back all read, so that the four cannot
disagree (D10.5):

```
SCHEMA = {
  "potential": {
    "kind":  Key(type=str, choices=["coulomb"], required=True),
    "preset": Key(type=str, choices=PRESETS.keys(), default=None),
    "sign":  Key(type=int, choices=[+1, -1], default=None),
    "kappa": Key(quantity="energy*length", default=None),
    "mass":  Key(quantity="mass", default=None),
    "reference_energy": Key(quantity="energy", default=None),
    "reference_length": Key(quantity="length", default=None),
  },
  "beam": {
    "energies": Key(quantity="energy", list=True, required=True),
    "energy_distribution": Key(type=str, choices=["delta"],
                               default="delta"),
    "layout": Key(type=str, choices=["annuli", "disc"], required=True),
    "annuli": Key(table_list={"b": Key(quantity="length"),
                              "db": Key(quantity="length"),
                              "n_azimuth": Key(type=int,
                                               default="rc")},
                  required_if=("layout", "annuli")),
    "n_particles": Key(type=int, required_if=("layout", "disc")),
    "b_min": Key(quantity="length", default=0.0),
    "b_max": Key(quantity="length", required_if=("layout", "disc")),
    "stratify": Key(type=bool, default=False),
    "seed": Key(type=int, required_if=("layout", "disc")),
  },
  "detector":  { ... per D10.5 ... },
  "inversion": { ... },
  "fidelity":  { ... "r_max": Key(quantity="length", required=True),
                     "step": Key(type=float,
                                 required_if=("integrator", "verlet")),
                 ... },
  "view":      { ... presentation zone ... },
  "meta":      { ... ignored on load ... },
}
PRESENTATION_TABLES = {"view"}
```

A `Key` records its type or physical dimension, its default (a
value, `None`, or the sentinel `"rc"` meaning "from the rc file"),
its allowed choices, and whether it is required unconditionally or
only when another key has a given value. `quantity=` keys accept a
bare number (natural units), a string, or a pint quantity (D10.3).

---

## 10.4 Loading

```
function load_run_file(path) -> dict:
    text = read(path)
    raw = tomllib.loads(text)              # tomli on 3.10
    if "schema" not in raw:
        warn "no schema key; assuming 1"
        raw["schema"] = 1
    if raw["schema"] > KNOWN_SCHEMA:
        fail f"run file schema {raw['schema']} is newer than this
              tool understands ({KNOWN_SCHEMA})"
    if raw["schema"] < KNOWN_SCHEMA:
        raw = upgrade(raw)                 # one function per version step;
                                           #   none exist yet
    return raw
```

---

## 10.5 Validation (D10.6)

Every failure raises `RunFileError(table, key, message, section)`,
whose string names all four, e.g. `[beam].seed: required when
layout = "disc" (design 3.5)`. Nothing is coerced.

```
function validate(raw) -> None:
    for table in raw:
        if table not in SCHEMA and table != "schema":
            fail (table, None, "unknown table", "10.6")
        for key in raw[table]:
            if key not in SCHEMA[table]:
                fail (table, key, f"unknown key; did you mean "
                                  f"{closest(key, SCHEMA[table])}?", "10.6")
    for table, keys in SCHEMA.items():
        for key, spec in keys.items():
            present = key in raw.get(table, {})
            if spec.required and not present: fail (table, key, "required")
            if spec.required_if and not present:
                (other, value) = spec.required_if
                if raw[table].get(other) == value:
                    fail (table, key, f'required when {other} = "{value}"')
            if present:
                check_type_or_dimension(raw[table][key], spec)
                if spec.choices and raw[table][key] not in spec.choices:
                    fail (table, key, f"one of {spec.choices}")

    # Cross-key rules.
    energies = raw["beam"]["energies"] as list
    if not energies or len(set(energies)) < len(energies):
        fail ("beam", "energies", "non-empty, no duplicates", "3.2")
    if raw["beam"]["layout"] == "disc":
        if not (0 <= raw["beam"]["b_min"] < raw["beam"]["b_max"]):
            fail ("beam", "b_min", "0 <= b_min < b_max", "3.3")
    else:
        for ring in raw["beam"]["annuli"]:
            if ring["b"] < 0 or ring["db"] <= 0 or ring["n_azimuth"] < 1:
                fail ("beam", "annuli", "b >= 0, db > 0, n_azimuth >= 1")
    if raw["detector"].get("radius", 2.0) < 1.0:
        fail ("detector", "radius", ">= 1, in units of r_max", "7.2")
    if raw["detector"].get("n_bins", 40) < 2:
        fail ("detector", "n_bins", ">= 2", "7.4")
```

Dimension checks on `quantity=` keys are made here with a throwaway
`ReferenceScales` built from SI units — `to_natural` with any
scales raises on a dimension mismatch, and the actual conversion
waits for `resolve`. A bare number passes.

Two rules need the potential and the scales and are checked in
`resolve` (10.7): the beam admits `b = 0` only if the potential
does (D3.4), and `r_max` exceeds the beam's largest impact
parameter by the rc safety factor (D10.6).

---

## 10.6 Defaults, the rc file, and overrides

```
function load_rc() -> RcSettings:
    # D10.7: ./scsimrc.py first, then $SCATTERING_RC/scsimrc.py, then
    # the package's own copy. The last is located from rc.py's own
    # resolved position (<package>/defaults/), NOT from the entry
    # script: an installed copy has no script directory (A9.1), and
    # the package is the one place that exists on both routes.
    for directory in [cwd, $SCATTERING_RC, PACKAGE_DEFAULTS_DIR]:
        if exists(directory / "scsimrc.py"):
            import parameters_and_defaults from it
            return RcSettings(**parameters_and_defaults())
    fail "scsimrc.py not found"      # unreachable unless the package
                                     #   itself is damaged

PACKAGE_DEFAULTS_DIR = dirname(resolved(rc.py)) / ".." / "defaults"

record RcSettings:                  # extends pseudocode 6.3
    max_store_bytes        int      4e9
    default_n_azimuth      int      24        (annulus shorthand, D3.3)
    r_max_safety_factor    float    3.0       (D10.6)
    default_palette        str      "light"
    default_camera         dict     {azimuth_deg: 35, elevation_deg: 20,
                                     distance: 4.0}
    default_panels         list     ["deflection", "cross_section",
                                     "effective_potential",
                                     "error_budget", "telemetry"]
    window_size            (int, int)  (1280, 960)
    glyph_radius           float    0.02      (D11.6, natural units)
    output_dir             str      "."

# The camera distance (3.0 -> 4.0, which stops the default view
# clipping the R_max sphere) and the error_budget panel (P9.4) were
# settled during v0.6 and v0.8; this record now agrees with them.

function apply_defaults(raw, rc) -> raw:
    for table, keys in SCHEMA.items():
        raw.setdefault(table, {})
        for key, spec in keys.items():
            if key not in raw[table] and spec.default is not None:
                raw[table][key] = rc_value(spec, rc) if spec.default == "rc"
                                  else spec.default
    # Conditional defaults.
    raw["inversion"].setdefault("enabled", raw["beam"]["layout"] == "disc")
    for ring in raw["beam"].get("annuli", []):
        ring.setdefault("n_azimuth", rc.default_n_azimuth)
    return raw

function apply_overrides(raw, overrides) -> raw:
    # overrides: list of "table.key=value" strings from --set.
    for text in overrides:
        (path, value_text) = text.split("=", 1)
        (table, key) = path.split(".", 1)
        if table not in SCHEMA or key not in SCHEMA[table]:
            fail f"--set {path}: unknown key"
        raw.setdefault(table, {})[key] = parse_value(value_text,
                                                     SCHEMA[table][key])
    return raw

function parse_value(text, key_spec):
    # TOML syntax for the value, so that lists and strings are
    # written the same way as in the file: --set beam.energies='["3
    # MeV","5 MeV"]', --set fidelity.n_samples=200.
    return tomllib.loads(f"v = {text}")["v"]
```

Overrides are applied *before* defaults and validation, so an
override is validated like any file value.

---

## 10.7 Resolution

```
function resolve(spec: RunSpec, rc: RcSettings) -> ResolvedRun:
    # spec may come from a file (10.8) or be built in code (tests).
    potential = make_potential(spec.potential)                    # P2
    scales    = build_scales(spec.potential, potential,
                             spec.beam.energies[0])               # P1.3
    beam_spec = resolve_beam_units(spec.beam, scales)             # P6.4
    r_max     = to_natural(spec.fidelity.r_max, "length", scales)

    # The two rules that need the potential and the scales (10.5).
    if not potential.admits_center() and beam_spec.smallest_impact() == 0:
        fail ("beam", "b_min" or "annuli", f"b = 0 is not an orbit for
              {potential.describe()}", "3.4")
    if r_max < rc.r_max_safety_factor * beam_spec.largest_impact():
        fail ("fidelity", "r_max", f"must be at least
              {rc.r_max_safety_factor} x the largest impact parameter
              ({beam_spec.largest_impact():.3g})", "10.6")

    settings = OrbitSettings(r_max=r_max, integrator=..., rtol=..., atol=...,
                             step=..., asymptote_tolerance=...,
                             trace_angle=radians(spec.fidelity.trace_angle_deg),
                             trace_points_max=..., orbit_provider=...,
                             entry_plane_z=r_max)                 # D4.6
    estimate = estimate_bytes(len(beam_spec.energies),
                              beam_spec.n_particles_total(),
                              spec.fidelity.n_samples,
                              spec.fidelity.trace_points_max,
                              spec.fidelity.n_deflection_points)  # P6.2
    if estimate > rc.max_store_bytes: fail as check_budget does (P6.2)

    resolved_spec = replace(spec, beam=beam_spec,
                            fidelity=replace(spec.fidelity, r_max=r_max),
                            meta=MetaSpec(resolved_by=tool_version_and_time(),
                                          source=spec.meta.source if any,
                                          git_commit=git_commit()))
    return ResolvedRun(resolved_spec, potential, scales, settings,
                       spec.detector.radius * r_max, estimate)   # frozen
```

`BeamSpec.n_particles_total()` is a small addition to P3.1: the sum
of `n_azimuth` over the annuli, or `n_particles`.

---

## 10.8 From file to `ResolvedRun`, and back

```
function run_spec_from_raw(raw) -> RunSpec:
    # Straight mapping of validated, defaulted tables onto the
    # records; annuli become AnnulusSpec(b, db, n_azimuth); quantity
    # strings stay strings (resolve converts them).

function load_and_resolve(path, overrides=(), rc=None) -> ResolvedRun:
    rc  = rc or load_rc()
    raw = load_run_file(path)
    raw = apply_overrides(raw, overrides)
    raw = apply_defaults(raw, rc)
    validate(raw)
    spec = run_spec_from_raw(raw)
    spec = replace(spec, meta=MetaSpec(source=path, ...))
    return resolve(spec, rc)

function write_back(resolved: ResolvedRun, path) -> None:
    # serialization.py. Every schema key present, in SCHEMA order,
    # natural-unit numbers written as bare numbers, with a comment
    # header naming the source file and the tool version, and the
    # [meta] table filled. Written with tomli_w.
    text = "# Resolved by scattering <version> on <time> from <source>\n"
    text += tomli_w.dumps(ordered_tables(resolved.spec))
    write(path, text)

function round_trip_equal(resolved, path) -> bool:
    # load_and_resolve(path) after write_back(resolved, path) yields
    # a ResolvedRun whose spec equals resolved.spec field by field
    # (floats to 1e-12) and whose potential and scales agree.
```

Round-tripping through natural units is exact because a resolved
file carries bare numbers, which `to_natural` passes through
unchanged; the reference scales are re-derived from the same
preset and explicit keys.

---

## 10.9 The rc file itself

`src/scattering/defaults/scsimrc.py` (moved from `src/scripts/` with
Route B; D10.7) follows `XYZrc.py`: a
`parameters_and_defaults()` returning a dict with the keys of
`RcSettings` (10.6), each commented with its meaning and the design
section that owns it. It holds no physics defaults; those are in
`SCHEMA`. `scbatchrc.py` (P13) adds cluster settings and inherits
the rest.

---

## 10.10 Verification

`tests/unit/test_run_file.py`:

- `runs/rutherford.toml` and `runs/rutherford_disc.toml` load,
  validate, resolve, write back to a temporary file, and reload to
  an equal `ResolvedRun`.
- Every rule in 10.5 has a test that violates it in a copy of the
  example and asserts the error names the table and key: unknown
  key (with the "did you mean" hint), missing `seed` for `disc`,
  duplicate energies, `b_min >= b_max`, `radius < 1`, a
  dimensioned string of the wrong dimension, a mixed list, `verlet`
  without `step`, an unknown `schema`.
- Perturbing every `[view]` key leaves `build_results_store` output
  bit-identical (D10.2).
- `--set fidelity.n_samples=10` and `--set beam.energies='["1
  MeV"]'` override and validate; `--set nosuch.key=1` fails.
- `load_rc` finds `./scsimrc.py` before `$SCATTERING_RC`.
- The resolved `alpha_on_gold` file has `b = 1.0` for an annulus
  written as `"45.5 fm"`, to the precision of the constants.
- The existing driver and provider tests pass unchanged through
  `resolve` (10.2).
