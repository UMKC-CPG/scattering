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

**`v0.8-detector` (2026-09-15): the forward chain is complete on
screen.** `scsim.py runs/rutherford_disc.toml` shows a uniform-flux
beam scattering onto a detector whose histogram carries real Poisson
errors, a pull readout against the exact cross section, hatched
unmeasured cones, and an error-budget panel that keeps numerical,
statistical, and assumption errors in separate columns. Attractive
and repulsive potentials give bit-identical histograms while their
orbits look nothing alike — VISION G8 on screen. The inversion
(pseudocode section 8) is next. See `dev/TODO.md`.

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

There are two ways, for two situations; they run the same code.

**On your own computer (Windows, macOS, or Linux).** You need Python
3.10 or later. Make an environment, install the tool into it, and
check that the computer can draw:

```bash
python -m venv physdemo
source physdemo/bin/activate        # Windows: physdemo\Scripts\activate
pip install https://github.com/UMKC-CPG/scattering/archive/refs/heads/main.zip
scsim --check
```

`pip` fetches the numerical and graphics libraries (about 1 GB) and
creates the `scsim` command. No `git`, compiler, or GPU is needed.
In later sessions only the `activate` line is repeated. To update
later, `pip install --upgrade` with the same URL picks up a new
release; between releases the version number does not change and
`pip` will do nothing, so use
`pip install --force-reinstall --no-deps <the same URL>`.

**On a shared computer (a teaching cluster).** The tool is one member
of the [`physdemo`](https://github.com/UMKC-CPG/physdemo) suite, which
one person installs for everybody: a single Python environment and a
directory of commands. Nothing is installed per user, which suits
small home directories and a read-only shared area. The instructor
follows the suite's README; a student only turns it on:

```bash
source /path/to/the/shared/physdemo/activate.sh
scsim --check
```

## Running

```bash
scsim rutherford          # run a packaged example by name
scsim --examples          # copy the example run files here, to edit
scsim rutherford.toml     # run your edited copy
scsim --write-rc          # copy the window/palette defaults here
scsim --help
```

Run from a directory you can write in: saved run files, screenshots,
and the `command` log go to the working directory. In a directory you
cannot write, the tool still runs and says what it could not save.

Every run appends its invocation to a `command` file in the working
directory, so the exact call that produced a result can be recovered
later.

## Testing

```bash
pytest tests/ -v
```

## License

GPL-3.0-or-later; see `LICENSE`. If you build on this tool — by hand
or with an AI assistant — carry the attribution and the citations in
the design sections forward.

## Citation

Not yet published. The physics follows Goldstein, Poole, and Safko,
*Classical Mechanics*, 3rd ed., chapter 3, and Landau and Lifshitz,
*Mechanics*, sections 15–20; each design section cites its sources.
