# Pseudocode 6. The Results Store and the Driver

> **Parent:** [`../PSEUDOCODE.md`](../PSEUDOCODE.md) — index.
> **Specifies:** design section 6,
> [`../design/06-results-store.md`](../design/06-results-store.md),
> and the driver of ARCHITECTURE A4.10.
> **Governs:** `src/scattering/run/results_store.py`,
> `src/scattering/run/driver.py`.
> **Status:** draft.

---

## 6.1 The store

```
class ResultsStore:                  # frozen after build (D6.7)
    # Trajectory block (D6.3); absent when n_samples == 0.
    position    [K, N, S, 3]  float64
    velocity    [K, N, S, 3]
    polar       [K, N, S, 2]          (r~, phi)
    phase       [K, N, S]     int8    -1 inbound, 0 orbit, +1 outbound
    time_grid   [K, S]

    # Per-particle block.
    impact_parameter [N];  azimuth [N];  annulus_index [N] int
    turning_point    [K, N];  turning_point_q [K, N]
    deflection       [K, N];  out_direction   [K, N, 3]
    time_offset      [K, N];  entry_index [K, N] int;  exit_index [K, N] int
    energy_drift     [K, N];  angmom_drift [K, N];  finite_radius [K, N]

    # Per-energy block.
    energies         [K]
    theta_min, theta_head  [K]
    deflection_table [K]  DeflectionTable
    xsec_table       [K]  CrossSectionTable
    mirror_table     [K]  DeflectionTable or None
    mirror_diff      [K]
    annulus_map      [K]  list of AnnulusMap
    provider         [K]  str;   provider_check [K]

    # Traces: list [K] of list [N] of arrays (n_i, 3), or empty.
    trace_points

    # Provenance.
    run_spec, beam, created, versions, git_commit

    # Read interface (D6.6). Every array returned is a read-only view.
    frame(k, n)            -> position[k, :, n, :]
    frame_polar(k, n)      -> polar[k, :, n, :]
    frame_velocity(k, n)   -> velocity[k, :, n, :]
    particle(k, i)         -> (time_grid[k], position[k, i], velocity[k, i],
                               polar[k, i], phase[k, i])
    final_directions(k)    -> out_direction[k]
    deflection_of(k)       -> (impact_parameter, deflection[k])
    tables(k)              -> (deflection_table[k], xsec_table[k],
                               mirror_table[k], annulus_map[k])
    trace(k, i)            -> trace_points[k][i]
    drift(k)               -> (energy_drift[k], angmom_drift[k],
                               finite_radius[k])
    time_of(k, n)          -> time_grid[k, n]
    n_energies, n_particles, n_samples
    size_bytes()
    provenance()

    freeze():
        for every array: array.flags.writeable = False
        self._frozen = True
    __setattr__ after freeze: raise AttributeError
```

---

## 6.2 The memory budget (D6.4)

```
function estimate_bytes(K, N, S, n_annuli, trace_points_max) -> int:
    trajectory  = K * N * S * (3 + 3 + 2) * 8 + K * N * S * 1
    per_particle = K * N * (8 * 8 + 3 * 8 + 2 * 8)
    traces      = K * N * trace_points_max * 3 * 8      # upper bound
    tables      = K * 4 * n_deflection_points * 8 + small
    return trajectory + per_particle + traces + tables

function check_budget(spec, rc) -> int:
    estimate = estimate_bytes(...)
    print(f"results store: about {estimate / 1e6:.0f} MB")
    if estimate > rc.max_store_bytes:
        fail f"estimated {estimate / 1e9:.1f} GB exceeds max_store_bytes
               = {rc.max_store_bytes / 1e9:.1f} GB; lower n_samples,
               n_particles, or the energy count, or raise the cap"
    return estimate
```

---

## 6.3 The run specification the driver consumes

P10 owns the run file: its schema, loading, validation, defaults,
and write-back. Until P10 exists the driver still needs a typed
record to consume, so its *shape* is fixed here and P10 will
populate it. This is a seam inventory (`CLAUDE.md`): every field
below names who produces it.

```
record PotentialSpec:               # from [potential]; produced by P10
    kind              "coulomb"
    sign              +1 | -1 | None (None = from preset)
    preset            name | None
    kappa, mass       pint quantity | None
    reference_energy  pint quantity | None
    reference_length  pint quantity | None

record RunSpec:
    potential   PotentialSpec
    beam        BeamSpec (P3.1) whose energies, annulus b and db,
                b_min and b_max are AS LOADED: pint quantities,
                dimensioned strings, or bare natural-unit numbers.
                The driver converts them (6.4) once; nothing below
                the driver sees a pint object.
    fidelity    the OrbitSettings fields of P4.1 (except
                entry_plane_z, derived here) plus n_samples,
                n_deflection_points, trace_points_max, orbit_provider
    detector_radius   multiple of r_max (D7.2), default 2.0

record RcSettings:                  # machine-local; produced by P10
    max_store_bytes   int, default 4e9
```

In v0.5 a `RunSpec` is constructed directly in code and tests; P10
adds the TOML path. When P10 arrives the unit conversion of 6.4
moves into `run_spec.py`'s resolution step (D10.8) and the driver
receives natural-unit values; that move is a P10 change and is
recorded there.

---

## 6.4 The driver: the forward chain in order (A2, A4.10)

```
function build_results_store(spec: RunSpec, rc, progress = None)
        -> ResultsStore:
    potential = make_potential(spec.potential)          # P2; Coulomb in v1
    scales    = build_scales(spec.potential, potential,
                             spec.beam.energies[0])     # P1.3
    beam_spec = resolve_beam_units(spec.beam, scales)   # P1.4 to_natural
                #   energies -> "energy"; b, db, b_min, b_max -> "length"
    check_budget(spec, rc)
    beam      = generate_beam(beam_spec, potential)     # P3.2
    settings  = OrbitSettings from spec.fidelity, with
                entry_plane_z = r_max                       (D4.6)
    provider  = choose_provider(potential, settings)    # P4.1
    K = len(beam.energies)
    N = len(beam.impact_parameter)
    S = spec.fidelity.n_samples
    store     = ResultsStore.allocate(K, N, S)
    store.impact_parameter, store.azimuth, store.annulus_index = beam fields

    for k in 0 .. K-1:
        energy = beam.energies[k]

        # --- deflection stage first: it is cheap, and it fixes the
        #     measured range and the out-directions the orbits' free
        #     flight will follow (D4.6).
        # The table spans the DECLARED extents for a disc (D7.3: the
        # measured range is what the beam could produce) and the
        # thrown values for annuli.
        (b_lo, b_hi) = (beam_spec.b_min, beam_spec.b_max) if disc
                       else (min(beam.impact_parameter),
                             max(beam.impact_parameter))
        table = build_deflection_table(potential, energy, b_lo, b_hi,
                    n_points = spec.fidelity.n_deflection_points,
                    admits_center = potential.admits_center())    # P5.4
        xsec  = build_cross_section_table(table)                   # P5.5
        (mirror, mdiff) = mirror_check(potential, energy, table)   # P5.6
        outputs = particle_outputs(potential, energy, beam)        # P5.8
        store.deflection[k]     = outputs.deflection
        store.out_direction[k]  = outputs.out_direction
        store.turning_point_q[k] = outputs.turning_point_q
        store.theta_min[k]  = xsec.theta_min
        store.theta_head[k] = xsec.theta_head
        store.deflection_table[k], store.xsec_table[k] = table, xsec
        store.mirror_table[k], store.mirror_diff[k] = mirror, mdiff
        store.annulus_map[k] = [annulus_map(potential, energy, a, xsec)
                                for a in spec.beam.annuli]
        store.provider[k], store.provider_check[k] = provider.name, table.check

        # --- orbits.
        orbits = []
        for i in 0 .. N-1:
            E_i = particle_energy(spec.beam, k, i)                 # P3.6
            orbits.append(provider.provide(potential, E_i,
                                           beam.impact_parameter[i], settings))
            progress(k, i) if progress
        store.turning_point[k] = [o.turning_point for o in orbits]
        store.time_offset[k]   = [o.time_offset for o in orbits]
        store.energy_drift[k] = [o.drift.energy for o in orbits]
        store.angmom_drift[k] = [o.drift.angmom for o in orbits]
        store.finite_radius[k] = [angle_between(
                                      embed(o.exit_state.v, beam.azimuth[i]),
                                      store.out_direction[k, i])
                                  for (i, o) in enumerate(orbits)]      # D4.7

        # --- the scene-time grid and the samples (D6.2).
        if S > 0:
            t_end = max over i of (time of reaching R_detect along the
                    outbound free flight) - orbits[i].time_offset
            store.time_grid[k] = linspace(0, t_end, S)
            for i in 0 .. N-1:
                fill_samples(store, k, i, orbits[i], beam.azimuth[i],
                             settings, spec.detector.radius * settings.r_max)
            if spec.fidelity.trace_points_max > 0:
                store.trace_points[k] = [embed_trace(o.trace(), beam.azimuth[i])
                                         for (i, o) in enumerate(orbits)]

    store.run_spec, store.beam = spec, beam (with theta_min/head filled)
    store.created, store.versions, store.git_commit = provenance()
    store.freeze()
    return store
```

---

## 6.5 Filling one particle's samples

```
function fill_samples(store, k, i, orbit, azimuth, settings, r_detect):
    t_scene = store.time_grid[k]
    t_orbit = t_scene + orbit.time_offset
    v_inf   = asymptotic_speed(orbit.energy)
    n_out   = store.out_direction[k, i]        # 3D; its in-plane form
                                               #   is (sin Theta, cos Theta)
    for n in 0 .. S-1:
        t = t_orbit[n]
        if t < orbit.entry_time:
            # Inbound free flight along the incoming asymptote (D4.6).
            phase = -1
            entry = orbit.state_at([orbit.entry_time])[0]
            (x, y) = (entry.x, entry.y) + (0, v_inf) * (t - orbit.entry_time)
            (vx, vy) = (0, v_inf)
        elif t <= orbit.exit_time:
            phase = 0
            (x, y, vx, vy) = orbit.state_at([t])[0]
        else:
            # Outbound free flight along the ASYMPTOTIC direction from
            # the exit point (D4.6, D4.7).
            phase = +1
            ex = orbit.exit_state
            d  = (sin(Theta_i), cos(Theta_i)) * v_inf
            (x, y) = (ex.x, ex.y) + d * (t - orbit.exit_time)
            (vx, vy) = d
        store.position[k, i, n] = embed(x, y, azimuth)
        store.velocity[k, i, n] = embed(vx, vy, azimuth)
        r   = hypot(x, y)
        phi = signed angle from orbit.pericenter_dir to (x, y)     # D4.5
        store.polar[k, i, n] = (r, phi)
        store.phase[k, i, n] = phase
    store.entry_index[k, i] = first n with phase == 0
    store.exit_index[k, i]  = first n with phase == +1 (or S)
```

`orbit.state_at` is called on the whole in-orbit slice at once in
the implementation, not per sample; the loop above is written per
sample for clarity. Beyond `r_detect` the particle is simply drawn
where the free flight puts it; the grid ends when the slowest
particle reaches `r_detect`, so no particle is far past the sphere.

---

## 6.6 Verification

`tests/unit/test_results_store.py`,
`tests/integration/test_driver.py`:

- `estimate_bytes(5, 500, 400, 5, 2000)` is about `65 MB` for the
  trajectory block plus traces; `check_budget` refuses when the cap
  is set below it and the message names `max_store_bytes`.
- After `freeze()`, every array raises on write and every attribute
  assignment raises.
- `phase` is nondecreasing along `n` for every `(k, i)`; every
  particle takes `0` and `+1`, and every `b > 0` particle also
  `−1`, when `S ≥ 50`.
- On free-flight samples, `position` lies on the straight asymptote
  to `1e-12`.
- `polar[..., 0] == |position|` to `1e-12`; `polar[..., 1]` at
  `entry_index` is `−φ_∞` to `1e-6` for Coulomb.
- `r_max − v_inf Δt < |position[k, i, entry_index]| ≤ r_max`, and
  the first outbound sample is outside `r_max` by at most one step.
- `turning_point` vs `turning_point_q`: `≤ 1e-9` relative.
- `finite_radius` scales as `1 / r_max^2` across a doubling
  sequence and is the same for both providers to the integrator
  tolerance (P4.11).
- **Determinism (A8.6(3)).** `build_results_store(spec)` twice
  gives bit-identical arrays; a scripted sequence of `frame`,
  `particle`, `trace`, and `tables` calls leaves every array
  bit-identical.
- `runs/rutherford.toml` builds in under 10 s on a login node with
  `n_samples = 400` (a wall-clock guard, marked as such).
- The store from `runs/rutherford.toml` has `theta_min[k]` equal to
  `|closed_form_deflection(E_k, b_max + db)|` and `theta_head[k]`
  equal to `|closed_form_deflection(E_k, b_min)|`.
