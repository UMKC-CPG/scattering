# Pseudocode 7. The Detector

> **Parent:** [`../PSEUDOCODE.md`](../PSEUDOCODE.md) — index.
> **Specifies:** design section 7,
> [`../design/07-detector.md`](../design/07-detector.md).
> **Governs:** `src/scattering/detector/detector_spec.py`,
> `src/scattering/detector/binning.py`,
> `src/scattering/detector/counting_statistics.py`; and the grafts
> named in 7.1 onto `render/panels.py`, `render/scene_description.py`,
> `geometry/cone.py`, `ui/interactive_session.py`, `ui/controls.py`.
> **Status:** draft. Binning and expectation rules verified by
> `dev/spikes/firsov_inversion.py`.

---

## 7.1 Seam inventory

The detector is a pure function of the frozen store and a layout;
it is NOT computed by the driver and NOT stored in the results
store, because its mode and layout are viewing controls (design
12.7): the session recomputes it from the stored asymptotic
directions when either changes, and caches it. What it consumes:

| Consumed | From | Produced by |
| --- | --- | --- |
| `store.final_directions(k)` — `out_direction[k]` | store | P5.8 |
| `store.impact_parameter` — for the position-mode offset | store | P3 |
| `store.beam.flux` — `F`, or NaN for an annuli beam | store | P3.2 |
| `store.theta_min[k]`, `store.theta_head[k]` | store | P5.5 |
| `store.tables(k)[1]` — the `CrossSectionTable`; `dsdo_at` | store, P5.5 | P5 |
| `store.position[k, i, exit_index[k, i]]` — a point on the |
| outbound free-flight line (position mode); absent when |
| `n_samples = 0` | store | P6.5 |
| `store.mirror_diff[k]` — for the sign-independence readout | store | P5.6 |
| `resolved.spec.detector` — `DetectorSpec` | resolved run | P10 |
| `resolved.detector_radius` — `R̃_detect` | resolved run | P10.7 |

What it produces, `DetectorResult` (7.2), is consumed by:

- `render/panels.py`: `panel_cross_section` gains the measured bars,
  errors, pulls, and hatched unmeasured regions; `build_panel` takes
  a `detector` argument (7.7). The `histogram` placeholder is
  replaced by this panel.
- `geometry/cone.py` and `render/scene_description.py`: a new
  `bin_bands(edges, r_detect)` draws the bin edges as thin bands on
  the detector sphere, one static drawable with role `detector`.
- `ui/interactive_session.py`: the static cache key becomes
  `(k, palette, tracked, detector_layout, detector_mode)`, and the
  session holds a `detector_cache` keyed the same way; `build_panel`
  receives the cached result. `ui/controls.py`: the existing
  `detector_mode` command flips the mode; a new `detector_layout`
  command (key `b`) cycles the three layouts.
- P8 (inversion) receives the record unchanged.
- P13 (batch) writes it to HDF5.

Import rule (ARCHITECTURE 6.4, tested): nothing under `detector/`
imports from `potentials/`, `orbits/`, or `beam/`. It reaches the
beam only through the store's `flux` and `theta_*` fields, and the
cross section only through `deflection.cross_section.dsdo_at`.

---

## 7.2 Records

```
record DetectorLayout:               # from DetectorSpec + the beam
    name            "log_theta" | "uniform_theta" | "equal_solid_angle"
    mode            "asymptotic" | "position"
    n_bins, n_phi   ints (n_phi = 1 in v1)
    edges           array (n_bins + 1,)  ascending theta, radians
    solid_angle     array (n_bins,)      2 pi |cos e_i - cos e_{i+1}|  (7.1)
    theta_min, theta_head                the measured range
    radius          R~_detect

record DetectorResult:               # design 7.8, per energy index
    layout          DetectorLayout
    energy_index    int
    counts          array (n_bins,) int
    estimate        array (n_bins,)      sigma_hat_i             (7.2)
    error           array (n_bins,)      delta sigma_hat_i       (7.3)
    expected        array (n_bins,)      E_i                     (7.4)
    pull            array (n_bins,)      (N_i - E_i) / sqrt(E_i) (7.5)
    empty           array (n_bins,) bool
    flux            float                F, or NaN
    n_thrown        int
    n_counted       int                  sum(counts)
    n_outside       int                  particles outside the range
    pull_rms        float                NaN when flux is NaN
    position_shift  array (n_bins,)      mean |theta_pos - theta_asym|
                                         per bin; NaN if unavailable
    mirror_diff     float                from the store
    has_flux        bool                 False for an annuli beam
```

---

## 7.3 The layout (`detector_spec.py`)

```
function build_layout(spec: DetectorSpec, theta_min, theta_head,
                      r_detect) -> DetectorLayout:
    if spec.n_phi != 1: fail "azimuthal bins are FD4; n_phi must be 1"
    lo, hi = theta_min, theta_head
    if not (0 < lo < hi <= pi): fail "measured range is empty"
    match spec.layout:
      "log_theta":         edges = geomspace(lo, hi, n_bins + 1)
      "uniform_theta":     edges = linspace(lo, hi, n_bins + 1)
      "equal_solid_angle": edges = arccos(linspace(cos lo, cos hi,
                                                   n_bins + 1))
    solid_angle = 2 pi |cos(edges[:-1]) - cos(edges[1:])|          (7.1)
    return DetectorLayout(spec.layout, spec.mode, n_bins, 1, edges,
                          solid_angle, lo, hi, r_detect)
```

The edges cover exactly `[theta_min, theta_head]` (design 7.3);
angles outside are unmeasured and are never given a bin.

---

## 7.4 Binning (`binning.py`)

```
function asymptotic_angles(directions) -> array (N,):
    return arccos(clip(directions[:, 2], -1, 1))     # from +z

function position_angles(store, k, layout) -> array (N,) | None:
    # Design 7.2, mode "position": the polar angle of the point
    # where the outbound free-flight line meets the detector sphere.
    # A point on that line is the first outbound sample; the line's
    # direction is the asymptotic one. Unavailable in batch mode.
    if store.n_samples == 0: return None
    angles = empty(N)
    for i in 0 .. N-1:
        n = store.exit_index[k, i]
        if n >= store.n_samples: n = store.n_samples - 1
        point = store.position[k, i, n];  d = store.out_direction[k, i]
        along = point . d
        travel = -along + sqrt(along^2 + layout.radius^2 - point . point)
        landing = point + d * travel
        angles[i] = arccos(clip(landing[2] / layout.radius, -1, 1))
    return angles

function bin_particles(angles, layout) -> (counts, n_outside):
    inside = (angles >= layout.edges[0]) & (angles <= layout.edges[-1])
    counts = histogram(angles[inside], bins=layout.edges)
    return (counts, N - inside.sum())
```

A particle exactly at `theta_head` (the head-on particle at `pi`)
must be counted; `histogram` includes the right edge of the last
bin, which is why the check above is `<=` on both sides.

---

## 7.5 Counting statistics (`counting_statistics.py`)

```
function estimate_and_error(counts, layout, flux) -> (estimate, error, empty):
    # (7.2), (7.3). With no flux (annuli), NaN throughout; the
    # counts are still meaningful, the estimate is not.
    if isnan(flux): return (NaN..., NaN..., counts == 0)
    estimate = counts / (flux * layout.solid_angle)
    error    = sqrt(counts) / (flux * layout.solid_angle)
    return (estimate, error, counts == 0)

function expected_counts(xsec: CrossSectionTable, layout, flux) -> array:
    # (7.4): the BIN-INTEGRATED expectation, never dsdo at the center
    # times the solid angle (design 7.6; the spike's first trap).
    expected = empty(n_bins)
    for i in 0 .. n_bins-1:
        (a, b) = layout.edges[i], layout.edges[i+1]
        integral = quad(lambda t: dsdo_at(xsec, t) * sin(t), a, b,
                        epsabs=1e-12, epsrel=1e-10)
        expected[i] = 2 pi flux integral
    return expected

function pulls(counts, expected) -> (pull, pull_rms):
    # (7.5). Bins with expected == 0 contribute no pull.
    valid = expected > 0
    pull = where(valid, (counts - expected) / sqrt(where(valid, expected, 1)),
                 NaN)
    return (pull, sqrt(nanmean(pull^2)))
```

---

## 7.6 The whole detector

```
function build_detector_result(store, resolved, k, spec=None) -> DetectorResult:
    spec   = spec or resolved.spec.detector
    layout = build_layout(spec, store.theta_min[k], store.theta_head[k],
                          resolved.detector_radius)
    directions = store.final_directions(k)
    angles_asym = asymptotic_angles(directions)
    angles_pos  = position_angles(store, k, layout)
    angles = angles_pos if (spec.mode == "position" and angles_pos is not None)
             else angles_asym
    (counts, n_outside) = bin_particles(angles, layout)
    flux = store.beam.flux
    (estimate, error, empty) = estimate_and_error(counts, layout, flux)
    xsec = store.tables(k)[1]
    if isnan(flux):
        expected = pull = full(n_bins, NaN);  pull_rms = NaN
    else:
        expected = expected_counts(xsec, layout, flux)
        (pull, pull_rms) = pulls(counts, expected)
    shift = per-bin mean of |angles_pos - angles_asym| over the
            particles in each bin (by asymptotic angle), or NaN
    return DetectorResult(layout, k, counts, estimate, error, expected,
                          pull, empty, flux, N, counts.sum(), n_outside,
                          pull_rms, shift, store.mirror_diff[k],
                          has_flux = not isnan(flux))
```

For the first version's potentials every particle lands in the
measured range, so `n_outside == 0`; a nonzero value is a bug and
the panel says so in red.

---

## 7.7 Display (grafts on P11)

```
function panel_cross_section(store, k, detector: DetectorResult | None):
    curve = the exact dsdo(theta) at ok nodes, role "exact_curve"   (as now)
    if detector is None: return PanelData(curve only)
    L = detector.layout
    bars = [(L.edges[i], L.edges[i+1], detector.estimate[i],
             detector.error[i]) for i if not detector.empty[i]]
                                        # horizontal bars spanning the bin
    arrows = [bin i at the one-count level for i if detector.empty[i]]
    hatched = [(0, L.theta_min), (L.theta_head, pi)]
    text = [f"N = {detector.n_thrown}, pull rms {detector.pull_rms:.2f} "
            f"(1.0 = Poisson)", f"mode {L.mode}, {L.name}, {L.n_bins} bins",
            "uniform-flux beam required for an estimate" if not has_flux,
            f"{detector.n_outside} outside the measured range" if > 0]
    return PanelData("cross_section", ..., curves=[curve], bars=bars,
                     arrows=arrows, hatched=hatched, ylog=True, text=text)
    # PanelData gains `bars`, `arrows`, `hatched` fields; render_panel
    # draws bars with ax.hlines + vertical error bars, arrows with
    # ax.annotate, hatched spans with ax.axvspan(hatch="//", alpha=.15).

function bin_bands(layout, r_detect) -> list of SphereBand:
    # geometry/cone.py: a thin band at every edge, width 0.25 deg,
    # role "detector"; drawn at low opacity so the cones stay legible.
```

---

## 7.8 The session (grafts on P12)

```
BINDINGS["b"] = ("detector_layout", "cycle log_theta / uniform / equal")
SessionState gains: detector_layout  str   default "log_theta"

in run_session:
    static_key = (k, palette, tracked, detector_layout, detector_mode)
    if static_key not in session.detector_cache:
        spec = replace(resolved.spec.detector, mode=state.detector_mode,
                       layout=state.detector_layout)
        session.detector_cache[static_key] = build_detector_result(
            store, resolved, k, spec)
    ... build_static(...) adds the bin bands from the cached result
    renderer.render(..., detector=session.detector_cache[static_key])
```

Both commands are viewing controls: the store is untouched, the
detector is recomputed from stored directions in milliseconds.

---

## 7.9 Verification

`tests/unit/test_detector.py`, `tests/integration/test_detector.py`:

- `build_layout` for each layout: `edges[0] == theta_min`,
  `edges[-1] == theta_head`, `sum(solid_angle) == 2 pi (cos theta_min
  - cos theta_head)` to `1e-12`; `equal_solid_angle` gives equal
  entries to `1e-12`.
- Coulomb disc beam, `N = 20000`, `b_max = 12`, fixed seed,
  `log_theta`, 40 bins: `n_outside == 0`, `n_counted == N`, no empty
  bin, `pull_rms` within `3 sqrt(2 / 40)` of 1.0 — a fixed-seed test
  of a seed-independent property (A8.4, spike: 0.94–1.05).
- The same beam with `equal_solid_angle`: more than a quarter of the
  bins empty (design 7.4's labeled bad example), and the panel text
  says so.
- **Sign independence, bitwise (design 7.9).** The same disc seed
  under `sign = +1` and `sign = -1` (with `b_min > 0` for the
  attractive case, both runs sharing it) gives `array_equal(counts)`
  in asymptotic mode.
- `expected` from (7.4) on the exact table, compared with the count
  a beam of `10^6` uniform-flux particles WOULD give: the sum of
  `expected` equals `N` to 0.1 % (the table integrates to the beam).
- **Position mode.** For the annuli example: every particle's
  position angle exceeds its asymptotic angle by `asin(b / R_detect)`
  to `1e-9`; `position_shift` halves when `R_detect` doubles.
- Batch store (`n_samples = 0`): position mode falls back to
  asymptotic and `position_shift` is NaN.
- Annuli beam: `has_flux` is False, `estimate` and `pull` are NaN,
  `counts` per ring equal `n_azimuth`, and the panel carries the
  "uniform-flux beam required" line.
- Import test: no module under `detector/` imports `potentials`,
  `orbits`, or `beam` (extends `test_architecture.py`).
- The scripted-session determinism test (P12.8) now includes the
  `detector_layout` and `detector_mode` commands.
