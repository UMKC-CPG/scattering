# Pseudocode 9. The Conservation Monitor and the Error Budget

> **Parent:** [`../PSEUDOCODE.md`](../PSEUDOCODE.md) — index.
> **Specifies:** design section 9,
> [`../design/09-conservation-and-error-budget.md`](
> ../design/09-conservation-and-error-budget.md).
> **Governs:** `src/scattering/analysis/conservation_monitor.py`,
> `src/scattering/analysis/error_budget.py`; and the grafts named in
> 9.1 onto `render/panels.py` and `render/scene_description.py`.
> **Status:** draft.

---

## 9.1 Seam inventory

Everything the budget reports is already computed and stored; this
section collects it into one record with three columns that are
never summed (design 9.2), and recomputes one thing the store does
not hold: the residual SERIES along the tracked orbit (design 9.3).

| Consumed | From | Produced by |
| --- | --- | --- |
| `store.drift(k)` — energy, angular momentum, exterior | store | P4, P6.4 |
| `store.provider[k]`, `store.provider_check[k]` | store | P5.4, P6.4 |
| `store.particle(k, i)` — the tracked particle's samples | store | P6.5 |
| `store.energies[k]`, `store.impact_parameter[i]` | store | P3, P6 |
| `resolved.potential.value(r)` — for the residual series | resolved run | P2 |
| `resolved.settings` — integrator, rtol, atol, r_max | resolved run | P10.7 |
| `DetectorResult` — `pull_rms`, `n_thrown`, `n_bins`, `has_flux` |
| | P7.2 | P7.6 |
| `InversionResult` — bands, tail fraction, sign, `quad_error` |
| (None until P8 exists) | P8 | P8 |

Produced: `ErrorBudget` (9.3), consumed by `render/panels.py`
(`panel_error_budget`, replacing the placeholder) and by the
telemetry overlay (`scene_description.telemetry_for` takes the
numerical maxima from the budget rather than recomputing them).

`analysis/analytic_solutions.py` of ARCHITECTURE 4.8 is satisfied by
the potentials' closed forms (`CoulombPotential.closed_form_*`,
`rutherford_cross_section`) and the exact-curve overlay already
drawn from the tables; no separate module is created, and that
decision is recorded here so the module map's entry is not a
dangling reference.

Not a stage of the chain: `analysis/` imports `core/` and reads the
store; nothing imports `analysis/` except `render/`, `ui/`, and the
batch sink.

---

## 9.2 The conservation monitor (`conservation_monitor.py`)

```
function residual_series(store, resolved, k, i) -> (time, energy_res,
                                                    angmom_res):
    # Design 9.3, eq. (9.1), on the integrated phase only.
    (time, position, velocity, polar, phase) = store.particle(k, i)
    keep   = phase == 0
    radius = polar[keep, 0]
    speed  = |velocity[keep]|
    energy = store.energies[k]
    total  = 0.5 speed^2 + resolved.potential.value(radius)
    energy_res = (total - energy) / energy
    angmom = |position[keep] x velocity[keep]|          # scene-frame L
    expected = angular_momentum(energy, store.impact_parameter[i])   # P1.5
    angmom_res = (angmom - expected) / expected  if expected > 0
                 else angmom                                # b = 0: absolute
    return (time[keep], energy_res, angmom_res)

function residual_maxima(store, k) -> (energy_max, angmom_max, exterior_max):
    (e, l, x) = store.drift(k)
    return (max(e), max(l), max(x))
```

The series is computed from the STORED samples, not from the orbit
provider, so that what the panel shows is what the scrubber shows.
For the analytic provider both residuals are at floating-point
precision and the panel says "closed-form orbit" (9.3).

---

## 9.3 The budget record (`error_budget.py`)

```
record NumericalColumn:
    energy_drift_max, angmom_drift_max, exterior_deflection_max
    provider_check, quad_error            (quad_error from P8, else NaN)
    orbit_provider  str
    integrator, rtol, atol, r_max
    closed_form     bool                  provider == "analytic"

record StatisticalColumn:                 # NaN / None until a disc beam
    pull_rms, n_particles, n_bins
    stat_band_at_reach, stat_band_at_far  (from P8, else NaN)
    has_flux        bool

record AssumptionColumn:                  # None until P8
    tail_model, tail_fraction_at_far, assume_sign

record TrackedSeries:
    particle_index
    time, energy_residual, angmom_residual

record ErrorBudget:
    energy_index
    numerical      NumericalColumn
    statistical    StatisticalColumn
    assumption     AssumptionColumn | None
    tracked        TrackedSeries

function build_error_budget(store, resolved, k, tracked,
                            detector=None, inversion=None) -> ErrorBudget:
    (e_max, l_max, x_max) = residual_maxima(store, k)
    numerical = NumericalColumn(e_max, l_max, x_max, store.provider_check[k],
                                inversion.quad_error if inversion else NaN,
                                store.provider[k], resolved.settings.integrator,
                                resolved.settings.rtol, resolved.settings.atol,
                                resolved.settings.r_max,
                                store.provider[k] == "analytic")
    statistical = StatisticalColumn(
        detector.pull_rms if detector and detector.has_flux else NaN,
        store.n_particles, detector.layout.n_bins if detector else 0,
        inversion.stat_band_at_reach if inversion else NaN,
        inversion.stat_band_at_far if inversion else NaN,
        detector.has_flux if detector else False)
    assumption = AssumptionColumn(inversion.tail_model,
                                  inversion.tail_fraction_at_far,
                                  inversion.assume_sign) if inversion else None
    (t, e_res, l_res) = residual_series(store, resolved, k, tracked)
    return ErrorBudget(k, numerical, statistical, assumption,
                       TrackedSeries(tracked, t, e_res, l_res))
```

**The rule, enforced structurally (design 9.9):** no function in the
package adds, averages, or otherwise combines a field of one column
with a field of another. A test parses `error_budget.py` and
`panels.py` and asserts that no expression names fields from two
columns.

---

## 9.4 Display (grafts on P11)

```
function panel_error_budget(budget: ErrorBudget) -> PanelData:
    # Three columns of text (design 9.8), and the tracked series as
    # two curves against time on a symmetric log axis.
    numerical = ["NUMERICAL",
                 f"orbits: {b.numerical.orbit_provider}"
                 + (" (closed form)" if b.numerical.closed_form else
                    f" {integrator} rtol {rtol:.0e}"),
                 f"energy drift   {energy_drift_max:.1e}",
                 f"L drift        {angmom_drift_max:.1e}",
                 f"exterior defl. {exterior_deflection_max:.1e} rad",
                 f"quadrature     {provider_check:.1e}"]
    statistical = ["STATISTICAL",
                   f"N = {n_particles}, {n_bins} bins",
                   f"pull rms {pull_rms:.2f} (1.0 = Poisson)" if has_flux
                   else "no flux (annuli beam)",
                   f"band at reach {stat_band_at_reach:.1e}" if finite]
    assumption = ["ASSUMPTION", f"tail model {tail_model}",
                  f"tail share at far r {tail_fraction_at_far:.0%}",
                  f"sign assumed {assume_sign:+d}"] if b.assumption
                 else ["ASSUMPTION", "(inversion not run)"]
    curves = [(t, energy_residual, "exact_curve", "energy residual"),
              (t, angmom_residual, "mirror", "L residual")]
    return PanelData("error_budget", "Error budget (design 9)",
                     "t (natural)", "residual", curves=curves,
                     text_columns=[numerical, statistical, assumption],
                     symlog=True)
    # PanelData gains `text_columns` and `symlog`; render_panel lays
    # the three columns across the top and the curves below.

in scene_description.telemetry_for:
    the three numerical maxima come from residual_maxima(store, k);
    unchanged in value, one owner (9.1).
```

`error_budget` is added to the default panel list in the rc file,
replacing `effective_potential` when the window has room for four
panels; the run file's `[view].panels` decides.

---

## 9.5 Verification

`tests/unit/test_error_budget.py`:

- For the analytic provider, `residual_series` gives both residuals
  below `1e-13` at every sample of every particle in the rutherford
  store, and `closed_form` is True.
- With `orbit_provider = "numerical"`, `dop853`, default tolerance:
  both below `1e-8`; the maximum of the series equals
  `store.drift(k)` for that particle to `1e-12` (the series and the
  stored maximum agree on the same samples).
- With `verlet` at steps `h, h/2, h/4`: `energy_drift_max` scales as
  `h^2` (ratio 4 ± 20 %), the D9.9 order test.
- Head-on particle: the angular-momentum residual is absolute and
  below `1e-12`.
- The statistical column is NaN-filled for an annuli store and
  finite for a disc store with a detector result; the numerical
  column is identical between the two runs of the same orbits (to
  the last digit) when only `n_particles` changes — design 9.9's
  "doubling N leaves every numerical entry unchanged".
- The structural test: `error_budget.py` and `panels.py` contain no
  expression combining fields across columns (AST walk over
  attribute names `numerical.*`, `statistical.*`, `assumption.*`).
- `panel_error_budget` returns three text columns headed NUMERICAL,
  STATISTICAL, ASSUMPTION, and `render_panel` on it yields a non-
  uniform image.
