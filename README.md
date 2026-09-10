# Scattering

An interactive teaching tool for **classical scattering** — Rutherford
and gravitational — built for a graduate theoretical-mechanics course.
A student throws a beam of particles at a central potential and
watches, in a 3D scene they can rotate and scrub through time, how
the impact parameter becomes the scattering angle, how an annulus of
impact parameters becomes a cone of solid angle, and how that ratio
is the differential cross section. The tool then runs the same chain
backwards, from simulated detector counts to a recovered potential,
so that inverse scattering is seen as the forward problem read in
reverse.

## Status

**`v0.5-orbits` (2026-09-10): the forward chain from a run
specification to a frozen results store runs and is tested** —
natural units and presets, the Coulomb closed forms, the beam, both
orbit providers, the deflection function and cross section, and the
store with its driver, 136 tests. No display yet, and no run-file
loader: a run is built in code from the records of
`src/scattering/run/run_spec.py` until pseudocode section 10 lands.
See `dev/TODO.md` for what is next.

## What It Will Do

- Show the **annulus-to-cone mapping** that defines the differential
  cross section, as a ring of particles landing on a cone.
- Integrate real orbits in `V = κ/r` of either sign, displaying the
  energy, impact parameter, polar coordinates, turning point, and
  scattering angle of each.
- **Scrub time in both directions** and **sweep energy** on a second
  slider, watching orbits tighten and the probe depth move inward.
- Count scattered particles on a **detector** with honest Poisson
  statistics, kept distinct from numerical error.
- **Invert** the counts to a cross section, a deflection function,
  and a recovered potential, marking the unreachable interior as
  unknown — and show why the Coulomb cross section cannot tell
  attraction from repulsion.
- Reproduce any run exactly from a TOML **run file**, including the
  sampler's seed.

## Documents

Development follows a five-level chain, each level citing the one
above it. All design documents live in `dev/`:

| Document | Question it answers |
| --- | --- |
| `dev/VISION.md` | Why does this project exist? |
| `dev/ARCHITECTURE.md` | How is it organized? |
| `dev/DESIGN.md` | How do the algorithms work? |
| `dev/PSEUDOCODE.md` | What are the steps, precisely? |
| `src/` | The implementation. |

`DESIGN.md` and `PSEUDOCODE.md` are indexes; their sections live in
`dev/design/` and `dev/pseudocode/`. `dev/TODO.md` tracks tasks by
level, and `dev/README.md` explains everything else in `dev/`.

When a change is made at any level, check upward (does this
invalidate a parent claim?) and downward (does this require child
updates?) before committing.

## Layout

```
dev/          Design document chain and development material
src/
  scattering/   The importable library
  scripts/      Command-line entry points
tests/        Test suite (pytest)
```

## Installing

```bash
# If the numerical environment is built and pinned separately,
# install without letting pip re-resolve it:
pip install -e . --no-deps
```

## Running

```bash
source $CPG_VENV_RIGID
python3 src/scripts/scsim.py runs/rutherford.toml   # planned
```

Every runnable script appends its invocation to a `command` file in
the working directory, so the exact call that produced a result can
be recovered later.

## Testing

```bash
pytest tests/ -v
```

## Citation

Not yet published. The physics follows Goldstein, Poole, and Safko,
*Classical Mechanics*, 3rd ed., chapter 3, and Landau and Lifshitz,
*Mechanics*, sections 15–20; each design section cites its sources.
