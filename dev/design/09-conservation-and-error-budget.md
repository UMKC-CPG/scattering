# Design 9. Conservation Monitoring and the Error Budget

> **Parent:** [`../DESIGN.md`](../DESIGN.md) — design index.
> **Status:** draft.
> **Serves:** P2 (numerical error disclosed), P3 (statistical error
> distinct), P14 (distortions labeled); ARCHITECTURE A4.8
> (`analysis/`), A8.4 (tolerance policy).
> **Depends on:** Sections 4, 5, 7, 8.
> **Implemented by:** pseudocode section 9.

---

## 9.1 Purpose and scope

Every number the tool shows is wrong by some amount, and the tool's
obligation is to say by how much and *why*. This section collects
every source of error the earlier sections produce, fixes how each
is measured, and fixes the one rule that governs their display:
errors of different kinds are shown side by side and never added.

It does not set tolerances for tests (each section does, per A8.4)
and does not design the panel's appearance (Section 11). It fixes
what the panel's numbers are.

---

## 9.2 Three kinds of error

| Kind | Cause | Remedy | Sections |
| --- | --- | --- | --- |
| Numerical | Finite step, radius, tolerance | Smaller step, larger |
| | | `R_max`, tighter tolerance | 4, 5 |
| Statistical | Finite particle count | More particles | 3, 7, 8 |
| Assumption | A model where data are absent | Another assumption, |
| | | or more data | 8 |

They have different causes and different remedies, and a single
combined figure would hide which remedy applies. A student who sees
"±3 %" learns nothing; one who sees "numerical `1e-9`, statistical
`2 %`, tail assumption `1 %`" knows to throw more particles, not to
tighten the integrator. That is P3, and it extends naturally to the
third kind, which Section 8 introduced.

---

## 9.3 Numerical: the conservation monitor

For every orbit at every energy, from the stored samples (Section
6.3) on the integrated phase only (`phase == 0`):

```
  energy_residual(n)  = ( ½ ṽ² + Ṽ(r̃) − Ẽ ) / Ẽ
  angmom_residual(n)  = ( x_p ṽ_y − y_p ṽ_x − sqrt(2 Ẽ) b̃ ) / (sqrt(2 Ẽ) b̃)
                                                                (9.1)
```

Stored per particle as the maximum absolute value along the orbit
(`energy_drift`, `angmom_drift` in Section 6.3) and, for the one
tracked particle the scene follows (Section 12), as the full series
for plotting against time. The `b̃ = 0` orbit has `L̃ = 0` and its
angular-momentum residual is reported absolutely, not relatively.

The panel shows, per energy, the maximum over particles of each,
and for the tracked particle its own. For the analytic provider
both are at floating-point precision, and the panel says
*"closed-form orbit"* so that a student does not mistake `1e-16`
for a very good integrator. For `dop853` at default tolerance they
are of order `1e-10`; for `verlet` at a coarse step they are
visible, which is that integrator's purpose (Section 4.9).

**Why a scattering pass reports a maximum, not a rate.** The
rigid-body tool reports drift per unit simulated time because its
runs are open-ended. A scattering orbit is finite and its error is
dominated by the pericenter passage, so a rate would average a
sharp event over a long quiet approach and understate it. The
maximum is the honest number; the series for the tracked particle
shows *where* it happens.

---

## 9.4 Numerical: the finite-radius residual

Section 4.4 established that an orbit started at finite `R̃_max` on
the straight asymptote is deflected wrongly by `O(1 / R̃_max)`, and
Section 4.7 that the exit direction is not the scattering angle.
The residual between them,

```
  finite_radius(k, i) = angle( exit velocity, n̂_out )           (9.2)
```

is stored per particle (Section 6.3) and its maximum per energy is
on the panel. With the exact start it is at integrator tolerance;
with the corrected start it is the `1 / R̃_max` curve of the spike.
It is *not* a conservation residual — energy and angular momentum
are conserved perfectly along a wrongly started orbit — and it is
listed separately for that reason.

---

## 9.5 Numerical: quadrature and provider checks

Two more numbers, small and reported rather than drawn:

- `provider_check(k)` — the largest discrepancy between the closed-
  form deflection and the quadrature (5.3) on a subset of `b̃`, when
  a closed form exists (Section 5.4). Near `1e-12` for Coulomb.
- `quad_error` — the largest error estimate `quad` returned across
  the deflection integrals and the inversion integral (8.4).

Their purpose is to show a student that the deflection function and
the inversion are exact to a precision far below anything else on
the panel, so that whatever scatter they see in the recovered
potential is not coming from here.

---

## 9.6 Statistical: counts and the inversion

From Section 7: the pull RMS (7.5) per energy, with the reminder
*"1.0 = Poisson"*, and the per-bin errors (7.3) drawn on the
histogram. From Section 8: the resampled band on the recovered
potential (8.7), drawn as a filled band, and its width at the reach
limit and at the largest recovered radius as two numbers.

These change with `N` and with nothing else. A student who doubles
`n_particles` watches them shrink by `sqrt(2)` while every number in
9.3–9.5 stays put, which is the demonstration P3 exists for.

---

## 9.7 Assumption: the tail and the sign

From Section 8: the tail-model band (the recovered potential under
the chosen tail versus under `"zero"`), drawn as a second band in a
distinct style, and the `tail_fraction` at the largest recovered
radius as a number — *"at r = 6.5, 40 % of the recovered value comes
from the tail model."* And the sign: a line of text, *"assuming a
repulsive potential; the mirror fits equally,"* with the mirror
curve dashed.

These are not errors in the usual sense; they are places where the
data are silent and the tool had to choose. They are listed in the
budget so that a student never mistakes the confidence of a curve
for the confidence of the data behind it (P14).

---

## 9.8 The error-budget record

Per energy, the panel's source of truth:

```
  numerical:
    energy_drift_max, angmom_drift_max      (9.1), over particles
    finite_radius_max                       (9.2)
    provider_check, quad_error              (9.5)
    orbit_provider                          "analytic" | "numerical"
    integrator, rtol, atol, r_max           the settings that govern
  statistical:
    pull_rms, n_particles, n_bins
    stat_band_at_reach, stat_band_at_far    (8.7)
  assumption:
    tail_model, tail_fraction_at_far        (8.5)
    assume_sign                             (8.3)
  tracked_particle:
    energy_residual[n], angmom_residual[n]  full series
```

`error_budget.py` (A4.8) builds this record and nothing else reads
the underlying arrays for display purposes; the renderer takes the
record.

---

## 9.9 Invariants and tests

- For the analytic provider, both residuals of (9.1) are below
  `1e-13` at every sample.
- For `dop853` at default tolerance, both are below `1e-8` for
  every first-version test case; the bound is derived from the
  tolerance and the pass length in a comment beside the test.
- For `verlet` at step `h`, the energy residual scales as `h²`
  across a halving sequence — the order of the method, tested as
  such rather than bounded.
- `finite_radius_max` is at integrator tolerance for the exact
  start and scales as `1 / R̃_max` for the corrected start (4.12).
- Doubling `n_particles` at fixed seed-independent design reduces
  the statistical band by `sqrt(2)` within `20 %` and leaves every
  numerical entry unchanged to the last digit.
- The record's three groups are never summed anywhere in the code;
  a grep-style test asserts no function combines a numerical and a
  statistical field.

---

## 9.10 Alternatives considered

**One combined error figure.** Rejected; 9.2.

**Drift per unit time, as the rigid-body tool does.** Rejected for
a finite pass; 9.3.

**Estimate the integrator's error from step-halving at run time.**
Honest but doubles the cost of every run; the conservation
residuals are a cheaper proxy that catches the same failures, and
the step-halving test lives in the suite instead.

**Fold the tail band into the statistical band.** Rejected; the
first shrinks with more data and the second does not, and a student
should see that.
