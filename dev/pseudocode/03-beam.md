# Pseudocode 3. The Beam

> **Parent:** [`../PSEUDOCODE.md`](../PSEUDOCODE.md) — index.
> **Specifies:** design section 3,
> [`../design/03-beam.md`](../design/03-beam.md).
> **Governs:** `src/scattering/beam/beam_spec.py`,
> `src/scattering/beam/impact_sampler.py`,
> `src/scattering/beam/energy_sampler.py`.
> **Status:** draft.

---

## 3.1 Records

```
record AnnulusSpec:
    impact        b~
    width         db~
    n_azimuth     int >= 1

record BeamSpec:                    # the resolved [beam] table, natural units
    energies      array (K,)        E~_k in run-file order
    distribution  "delta"           # the FD2 hook; only value in v1
    layout        "annuli" | "disc"
    annuli        list of AnnulusSpec, or empty
    n_particles   int               # disc only
    b_min, b_max  floats            # disc only
    stratify      bool              # disc only
    seed          int or None       # disc only; required there

record Beam:                        # D3.6, immutable
    energies          array (K,)
    impact_parameter  array (N,)
    azimuth           array (N,)
    annulus_index     array (N,) int   ring id, or -1
    annulus_width     array (n_annuli,)
    flux              float            F, or NaN for annuli
    theta_min         array (K,)       set later by P5; NaN here
    theta_head        array (K,)       likewise
    layout, seed, stratify
```

---

## 3.2 Generating a beam

```
function generate_beam(spec: BeamSpec, potential) -> Beam:
    if spec.layout == "annuli":
        (b, phi, ring, widths) = layout_annuli(spec.annuli)
        flux = NaN
    else:
        rng = numpy.random.default_rng(spec.seed)      # seed required
        (b, phi) = sample_disc(spec.n_particles, spec.b_min,
                               spec.b_max, spec.stratify, rng)
        ring   = full(spec.n_particles, -1)
        widths = empty array
        flux   = spec.n_particles / (pi * (spec.b_max^2 - spec.b_min^2))
                                                                  (3.3)
    check_admissible(b, potential)                                (3.4)
    return Beam(spec.energies, b, phi, ring, widths, flux,
                theta_min = NaN * ones(K), theta_head = NaN * ones(K),
                spec.layout, spec.seed, spec.stratify)   # frozen
```

Validation of the spec itself (`seed` present for `disc`,
`b_min < b_max`, non-empty annuli, …) happens at run-file load
(P10), not here; this function may assume a valid spec and asserts
it in debug mode.

---

## 3.3 The annulus layout

```
function layout_annuli(annuli) -> (b, phi, ring, widths):
    b, phi, ring = [], [], []
    for (i, ring_spec) in enumerate(annuli):
        for j in 0 .. ring_spec.n_azimuth - 1:
            b.append(ring_spec.impact)                # exactly b~
            phi.append(2 * pi * j / ring_spec.n_azimuth)
            ring.append(i)
    widths = [ring_spec.width for ring_spec in annuli]
    return (array(b), array(phi), array(ring), array(widths))
```

Particles of one ring are contiguous in index, ring order as
declared, azimuth increasing within a ring. `db~` is not sampled;
it is carried for drawing and for the annulus-to-cone map (P5).

---

## 3.4 The uniform-flux disc

```
function sample_disc(n, b_min, b_max, stratify, rng) -> (b, phi):
    # ONLY rng.random() is used (D3.5): reproducibility rests on
    # the PCG64 raw stream, not on NumPy's distribution methods.
    u = rng.random(n)
    w = rng.random(n)
    if stratify:
        # One particle per equal stratum of b^2, uniformly placed
        # within it; the strata are in index order.
        u = (arange(n) + u) / n
    b   = sqrt(b_min^2 + u * (b_max^2 - b_min^2))               (3.1)
    phi = 2 * pi * w                                             (3.2)
    return (b, phi)
```

The two draws are made in this order — all `u`, then all `w` — and
the order is part of the contract: a regression test stores the
first ten `(b, phi)` for `seed = 20260910` and any change to the
draw order or count breaks it deliberately.

---

## 3.5 The forbidden center

```
function check_admissible(b, potential):
    if not potential.admits_center() and any(b == 0):
        fail "impact parameter 0 is not an orbit for
              {potential.describe()}: raise b_min or the annulus b"
```

The check asks the potential (P2.1), never the sign (D3.4).

---

## 3.6 The energy sampler (FD2 hook)

```
function particle_energy(spec: BeamSpec, energy_index, particle_index):
    if spec.distribution == "delta":
        return spec.energies[energy_index]
    fail "unsupported energy distribution"
```

Trivial in v1 and called anyway from the driver (P6), so that a
continuous distribution later is a new branch here and nothing
else. The results store keys on `energy_index`, which survives the
generalization (D3.2).

---

## 3.7 Verification

`tests/unit/test_beam.py`:

- `layout_annuli` on two rings of 24 gives 48 particles, `b` exact,
  azimuths `2πj/24`, ring ids `[0]*24 + [1]*24`.
- `sample_disc` with `seed = 20260910`, `n = 10`, `b_min = 0`,
  `b_max = 8`: the stored reference `(b, phi)` (regression).
- Every `b` in `[b_min, b_max]`, every `phi` in `[0, 2π)`.
- **Flux test (A8.4).** `n = 200000`, `b_max = 8`: counts in five
  concentric annuli of equal area agree with `n / 5` to within
  `4 sqrt(n/5)` (fixed seed; the property is seed-independent and
  the comment says so).
- `stratify = True`: every stratum `[k/n, (k+1)/n)` of `u` has
  exactly one particle.
- `check_admissible` raises for attractive Coulomb with a `b = 0`
  ring, passes for repulsive, and the message names the potential.
- `particle_energy` returns `energies[k]` for every `(k, i)`.
