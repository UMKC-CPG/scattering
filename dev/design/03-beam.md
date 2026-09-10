# Design 3. The Beam: Energies, Impact Parameters, and the Seed

> **Parent:** [`../DESIGN.md`](../DESIGN.md) — design index.
> **Status:** draft.
> **Serves:** G1 (annulus), G5 (energy sweep), G6 (honest detector),
> G9 (reproducible from a file); VISION Non-Goal 4 and FD2 (energy
> spread, hooked but unhooked); ARCHITECTURE A4.3 (`beam/`), A7
> (the seed in the run file).
> **Implemented by:** pseudocode section 3.

---

## 3.1 Purpose and scope

The beam is the complete set of initial conditions for a run: which
energies, which impact parameters, which azimuths, how many
particles. It is plain data. This section designs how that data is
specified and how it is generated from a specification, including
the random sampling that the uniform-flux layout needs and the seed
that makes it reproducible.

It does not design where a particle *starts* in the scene (`R_max`
and the entry plane are Section 4), nor the run-file syntax beyond
the keys named here (Section 10).

---

## 3.2 Energies

The `energies` key is a list of one or more dimensioned values, or a
single value; a single value is a list of length one. Each becomes
`Ẽ_k = E_k / E_ref` (Section 1.2). The list is the energy axis of
the results store (Section 6) and of the energy scrubber (Section
12), in the order given. Duplicates are an error; the list need not
be sorted, since a teacher may want a deliberate order, but the
scrubber presents it sorted and says so.

**Every particle is run at every energy.** The beam's impact
parameters and azimuths are generated once and reused across the
sweep, so the same particle — same `b̃`, same azimuth, same array
index — appears at each energy. This is what lets a student follow
*one* particle's orbit tighten as the energy slider moves (G5). It
also means the sweep costs a factor of `n_energies` in storage, and
nothing in sampling.

### The distribution hook (FD2)

`energy_sampler.py` exposes one interface: given the beam
specification and a particle index, return that particle's `Ẽ`. The
first version implements exactly two distributions:

| `energy_distribution` | Meaning |
| --- | --- |
| `"delta"` (default) | Every particle has the listed energy |
| `"list"` | Synonym; a list of energies is a sweep of deltas |

A continuous distribution (`"gaussian"` with a width, say) is a new
case in this one module, changing the sampler and nothing else. It
would break the "same particle at every energy" property above,
since a per-particle energy is no longer a sweep index; that is why
the hook exists but is unhooked, and why the results-store layout
(Section 6) keys on an *energy index* rather than an energy value —
the index survives the generalization.

---

## 3.3 Impact-parameter layouts

Two layouts are offered because they teach different things (A4.3).
The `layout` key selects one.

### `layout = "annuli"` — the teaching picture (G1)

A list of rings, each with an impact parameter, a width, and a
particle count around it:

```toml
[beam]
layout = "annuli"
annuli = [
  { b = "1.0", db = "0.1", n_azimuth = 24 },
  { b = "2.0", db = "0.1", n_azimuth = 24 },
]
```

For a ring with `n_azimuth` particles, azimuths are `ϕ_j = 2π j /
n_azimuth`, `j = 0 … n_azimuth − 1`, all at exactly `b̃`; `db̃` is not
sampled, it is *drawn*: it is the width of the annulus rendered in
the scene and the `db` of the solid-angle map (Section 5). Every
particle on a ring has the same orbit rotated about the beam axis,
so the ring stays a ring as it scatters and lands on one cone. That
is the whole point of this layout.

`b` values are in units of `ℓ₀` when given as bare numbers, or
dimensioned strings converted at the boundary (Section 1.4). A list
of `b` values without azimuth counts (`b = [0.5, 1.0, 2.0]`) is
accepted as shorthand with a default `n_azimuth` from the rc file.

### `layout = "disc"` — what a cross section is defined against (G6)

Particles fill a disc, or an annular disc, with **uniform flux**:
the number of particles per unit area of the transverse plane is
constant. This is the definition of a beam that the cross section
presupposes, and it is what makes binned counts an estimate of
`dσ/dΩ` (Section 7).

```toml
[beam]
layout = "disc"
n_particles = 2000
b_min = "0.0"
b_max = "8.0"
seed = 20260910
```

Uniform flux over an annular disc means the probability density in
`b̃` is proportional to `b̃` on `[b̃_min, b̃_max]`, and the azimuth is
uniform on `[0, 2π)`. Both are sampled by inverse transform from
uniform deviates `u, w ∈ [0, 1)`:

```
  b̃ = sqrt(b̃_min² + u (b̃_max² − b̃_min²))                      (3.1)
  ϕ = 2π w                                                   (3.2)
```

The flux the detector needs is the number per unit area,

```
  F = n_particles / (π (b̃_max² − b̃_min²))       [per ℓ₀²]    (3.3)
```

and it is stored with the beam, since every cross-section estimate
divides by it.

**`b̃_max` is a physical statement, not a convenience.** No particle
with `b̃ > b̃_max` is thrown, so no count lands below `θ_min =
2 arctan(1 / (2 Ẽ b̃_max))` for Coulomb, and generally below the
deflection at `b̃_max`. Those detector bins are *unmeasured*, and the
beam records `θ_min` at each energy so the detector can mark them
(Section 7). A student raising `b̃_max` watches `θ_min` fall and the
forward bins fill — and watches the particle count needed to keep
the *large*-angle statistics fixed climb as `b̃_max²`, because a
uniform-flux disc spends almost all its particles at large `b̃`
where nothing interesting happens. That trade-off is the reason the
batch tier exists.

**Stratified option.** For the same reason, `disc` accepts
`stratify = true`, which divides `[b̃_min², b̃_max²]` into
`n_particles` equal strata and places one particle at a uniformly
random point within each. This keeps the flux exactly uniform on
average while cutting the variance of the count in any bin; it is a
standard variance-reduction device and is labeled as such on screen,
since a stratified beam is not what a real accelerator produces.
The default is `false`.

---

## 3.4 The forbidden center

For an attractive potential, `b̃ = 0` is fall-to-center (Section
2.3). The beam refuses it:

- `annuli`: a ring at `b = 0` with `s = −1` is a load-time error
  naming the reason.
- `disc`: `b̃_min` must be strictly positive when `s = −1`; the
  default `b̃_min` for an attractive potential is not zero but a
  small value from the rc file, and the run file records the
  resolved value (A7).

For the repulsive case `b̃ = 0` is allowed and is the head-on orbit,
`θ = π`.

This is a property of the *potential*, so the check asks the
potential whether `b̃ = 0` is admissible (A6.1) rather than testing
`s` directly. A hard sphere admits it; a Lennard-Jones well does not.

---

## 3.5 The seed

The `disc` layout is stochastic and G9 demands reproducibility, so
the seed is a **required** key of `[beam]` whenever `layout =
"disc"`, and is recorded in the run file — never only in the rc
file (A7). A `disc` run file without a seed is a load-time error; it
is not silently seeded from the clock. For `annuli` the key is
ignored with a warning, since nothing is sampled.

### What reproducibility rests on

The generator is `numpy.random.default_rng(seed)`, whose bit
generator (PCG64) produces a raw stream that NumPy holds stable
across versions. NumPy does *not* promise that its higher-level
distribution methods (`rng.normal`, `rng.choice`, …) give the same
values across versions. So the sampler uses **only `rng.random()`**
— raw uniform doubles — and applies the inverse transforms (3.1) and
(3.2) in this project's own code. Reproducibility then rests on the
PCG64 stream alone.

### Belt and braces

The sampled `(b̃, ϕ)` of every particle are written into the results
store and into the batch tier's HDF5 output (Section 13), not merely
the seed that generated them. If a future NumPy did change the
stream, a stored result would still be exactly readable, and a
regression test would catch the change rather than a student. A
regression test does exactly this: it samples from a fixed seed and
compares against stored values.

---

## 3.6 The beam as data

The generated beam is an immutable record, one per run, holding:

```
  energies          array (n_energies,)        Ẽ_k, in list order
  impact_parameter  array (n_particles,)       b̃_i
  azimuth           array (n_particles,)       ϕ_i
  annulus_index     array (n_particles,) int   ring id, or −1 for disc
  annulus_width     array (n_annuli,)          db̃ per ring, or empty
  flux              float                      F of (3.3), or NaN
  theta_min         array (n_energies,)        unmeasured-below angle
  layout, seed, stratify                       as specified
```

Every stage downstream receives this record and nothing else about
where the particles came from. The orbit provider (Section 4)
consumes `(Ẽ_k, b̃_i)`; the embedding consumes `ϕ_i`; the geometry
consumes `annulus_index` and `annulus_width` to draw rings and
cones; the detector consumes `flux` and `theta_min`.

---

## 3.7 Invariants and failure modes

- `n_particles ≥ 1`; `n_azimuth ≥ 1` on every ring.
- `0 ≤ b̃_min < b̃_max`; strict positivity of `b̃_min` when the
  potential forbids the center.
- Every sampled `b̃_i` lies in `[b̃_min, b̃_max]`; every `ϕ_i` in
  `[0, 2π)`.
- For `disc`, the empirical flux — particles per unit area in a few
  concentric annuli — matches (3.3) within Poisson error; a
  statistical test at a fixed seed, designed to hold for any seed
  (A8.4).
- `theta_min` is monotone decreasing in `b̃_max` and increasing in
  `Ẽ`, for Coulomb.
- A run file with `layout = "disc"` and no `seed` fails at load.

---

## 3.8 Alternatives considered

**Sample `b̃` uniformly rather than with density `∝ b̃`.** Rejected;
it is the most common beginner's error in this subject and produces
a beam whose flux falls as `1 / b̃`, so binned counts would not
estimate the cross section. The tool could offer it as a deliberate
wrong example under a label, but not as a layout.

**Seed from the clock when absent.** Rejected under G9 and A7. A
convenience that silently makes a run unrepeatable is exactly the
kind of thing a student would not notice until it mattered.

**Generate a fresh beam per energy.** Rejected; see Section 3.2. The
same particle at every energy is the point of the sweep.

**Store only the seed, not the samples.** Rejected; see Section 3.5.
The seed is the *source* of reproducibility and the samples are the
*proof* of it.

---

## 3.9 References

- Goldstein, Poole, and Safko, *Classical Mechanics*, 3rd ed.,
  Section 3.10, for the definition of the cross section in terms of
  incident flux.
- NumPy Enhancement Proposal 19, "Random Number Generator Policy,"
  for what is and is not stream-stable across versions.
