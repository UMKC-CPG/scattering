# Route B (pip install) end-to-end check

**Date:** 2026-09-17. **Specified by:** pseudocode 12.10,
"Verification", last item; ARCHITECTURE 8.6(5), 9.1.

The structural tests (`tests/unit/test_installed_copy.py`) cannot
prove that an installed copy works; only installing one can. This is
the record of doing so, and the recipe for doing it again.

## Recipe

In an empty directory OUTSIDE the repository, with an empty `HOME` and
a bare `PATH` so that nothing of the developer's environment leaks in:

```bash
python -m venv laptop && source laptop/bin/activate
pip install --no-cache-dir /path/to/scattering   # or the archive URL
mkdir work && cd work
scsim --check
scsim --examples
scsim rutherford.toml --offscreen --frames 2 --screenshot first.png
scsim rutherford_disc --set beam.n_particles=500 --offscreen --frames 2
scsim --write-rc
```

## Result (Linux x86_64, Python 3.10.19)

- `pip` resolved and installed every dependency by itself in 39 s
  (warm network): numpy 2.2.6, scipy 1.15.3, matplotlib 3.10.9, vedo
  2026.6.1, **vtk 9.7.0**, pint 0.24.4, tomli 2.4.1, tomli_w 1.2.0.
  The environment is 897 MB.
- vtk 9.7.0 is NEWER than the physdemo suite's pin (9.6.2). The tool
  works with it. This is the behaviour ARCHITECTURE 9.1 describes:
  Route B meets new releases first.
- The package was imported from `site-packages`, not from the
  repository, and the examples and rc file were found there.
- `scsim --check`: PASS (built 3 x 120 in 0.7 s; 2 frames in 1.6 s).
- `--examples` wrote both run files; the run from the copied file
  wrote a non-blank `first.png`; the bare-name run used the packaged
  file; `--write-rc` wrote `scsimrc.py`; `command` recorded the runs
  and none of the utility invocations.

## Not yet done

macOS and Windows (`dev/TODO.md`, ARCHITECTURE). Nothing above
depends on a shell, but nobody has watched it run there.

## Found on the way

`rutherford_disc` as shipped (20 000 particles) takes more than ten
minutes to start with `--offscreen --frames 2`, in the suite
environment as well as here, so it is a property of the example and
not of the route. It is far too heavy to be a student's second
command; see the TODO entry on the Tier-1 default particle count.
