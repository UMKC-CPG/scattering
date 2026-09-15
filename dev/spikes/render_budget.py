#!/usr/bin/env python3

"""Measure the offscreen frame rate of the scattering scene against
the particle count (ARCHITECTURE section 9.3, design section 11).

This is a spike (see dev/spikes/README.md). The question: how many particles,
each with an adaptive trace and a moving glyph, does a software-rendered node
sustain at an interactive rate through the real render path (scene description
-> VedoRenderer)? The answer sets the Tier-1 default `n_particles`.

The rigid-body tool's spike learned that a VTK window without a GL context
accepts Render() and draws nothing at a gratifying frame rate, so every
measurement here reads the framebuffer back and reports `pixels_verified`. A
result with pixels_verified False means nothing.

Run, with DISPLAY unset so the EGL window class is chosen:

    unset DISPLAY
    python3 dev/spikes/render_budget.py --counts 50 200 500 1000
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))

from scattering.beam.beam_spec import BeamSpec            # noqa: E402
from scattering.run import (DetectorSpec, FidelitySpec,
    # noqa: E402 PotentialSpec, RcSettings, RunSpec, build_results_store,
    resolve)
from scattering.render.scene_description import (Scene,
    # noqa: E402 build_frame, build_static)


def measure(n_particles, frames, size, panels):
    from scattering.render.vedo_renderer import VedoRenderer
    spec = RunSpec(
        potential=PotentialSpec(preset='alpha_on_gold'),
        beam=BeamSpec(energies=['5 MeV'], layout='disc',
                      n_particles=n_particles, b_min=0.0, b_max=8.0,
                      seed=1),
        fidelity=FidelitySpec(r_max=40.0, n_samples=120,
                              n_deflection_points=100),
        detector=DetectorSpec(radius=2.0))
    rc = RcSettings()
    resolved = resolve(spec, rc)
    build_start = time.time()
    store = build_results_store(resolved)
    build_seconds = time.time() - build_start
    renderer = VedoRenderer('light', size, offscreen=True, panels=panels)
    static = build_static(store, resolved, 0, 0, rc.glyph_radius)
    dynamic, telemetry = build_frame(store, resolved, 0, 0, 0,
                                     rc.glyph_radius, resolved.scales)
    key = (0, 'light', 0)
    renderer.render(Scene(static, dynamic, telemetry),
        resolved.spec.view.camera, key, store=store, resolved=resolved)
    first = renderer.screenshot(as_array=True)
    start = time.time()
    for frame in range(1, frames + 1):
        n = frame % store.n_samples
        dynamic, telemetry = build_frame(store, resolved, 0, n, 0,
                                         rc.glyph_radius, resolved.scales)
        renderer.render(Scene(static, dynamic, telemetry),
            resolved.spec.view.camera, key, store=store, resolved=resolved)
    elapsed = time.time() - start
    last = renderer.screenshot(as_array=True)
    renderer.close()
    verified = bool(first.min() != first.max()
                    and not np.array_equal(first, last))
    return dict(n_particles=n_particles, build_seconds=build_seconds,
        fps=frames / elapsed, ms_per_frame=1000 * elapsed / frames,
        pixels_verified=verified,
        trace_points=sum(len(t) for t in store.trace_points[0]))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--counts', type=int, nargs='+',
                        default=[50, 200, 500])
    parser.add_argument('--frames', type=int, default=30)
    parser.add_argument('--size', type=int, nargs=2, default=[1280, 960])
    parser.add_argument('--no-panels', action='store_true')
    args = parser.parse_args()
    panels = () if args.no_panels else ('deflection', 'cross_section',
                                        'effective_potential', 'telemetry')
    print(f'window {args.size[0]}x{args.size[1]}, {args.frames} frames, '
          f'panels {"off" if args.no_panels else "on"}')
    for count in args.counts:
        result = measure(count, args.frames, tuple(args.size), panels)
        print(f"  N={result['n_particles']:5d}  "
              f"build {result['build_seconds']:5.1f}s  "
              f"{result['fps']:6.1f} fps ({result['ms_per_frame']:6.1f} ms)"
              f"  trace points {result['trace_points']:6d}"
              f"  pixels_verified={result['pixels_verified']}")


if __name__ == '__main__':
    main()
