#!/usr/bin/env python3
"""Cloud: 2D fractal noise drifting over the rectangle, driving color + brightness.

A 3D Perlin/fBm field is sampled at each LED's (x, y) position. The third noise
axis is time, so the cloud morphs in place ("evolution"); panning the sample
window makes the cloud drift across the frame. The noise value n in [0,1] picks a
color from the palette AND sets brightness = lerp(min_bri, max_bri, n).

Examples:
    ./.venv/bin/python cloud.py
    ./.venv/bin/python cloud.py --scale 0.5 --evolve 0.25 --colors '#ff0066,#3300ff'
    ./.venv/bin/python cloud.py --pan-speed 0.12 --pan-angle 90 --octaves 5 --contrast 3
"""
import argparse

import numpy as np

import mirror_leds as m

# ---- defaults (override with the flags below) -----------------------------
SCALE = 0.05        # noise frequency -> blob size (smaller = bigger, softer blobs)
EVOLVE = 0.1       # how fast the cloud morphs in place (noise z-rate)
PAN_SPEED = 0.03    # how fast the cloud drifts across the frame
PAN_ANGLE = 90.0    # drift direction in degrees (0=+x right, 90=+y up)
OCTAVES = 4         # fBm octaves -> texture detail
CONTRAST = 2.5      # spreads the noise toward dark/bright extremes
MIN_BRI = 0.4      # brightness where noise is darkest
MAX_BRI = 0.8       # brightness where noise is brightest
COLORS = m.DEFAULT_PALETTE


def main():
    ap = argparse.ArgumentParser(description="2D noise cloud over the LED rectangle")
    ap.add_argument("--scale", type=float, default=SCALE, help="noise size (smaller=bigger blobs)")
    ap.add_argument("--evolve", type=float, default=EVOLVE, help="morph-in-place speed")
    ap.add_argument("--pan-speed", type=float, default=PAN_SPEED, help="drift speed across frame")
    ap.add_argument("--pan-angle", type=float, default=PAN_ANGLE, help="drift direction (degrees)")
    ap.add_argument("--octaves", type=int, default=OCTAVES, help="fBm octaves (texture detail)")
    ap.add_argument("--contrast", type=float, default=CONTRAST, help="dark/bright spread")
    ap.add_argument("--min-bri", type=float, default=MIN_BRI, help="brightness at darkest noise")
    ap.add_argument("--max-bri", type=float, default=MAX_BRI, help="brightness at brightest noise")
    ap.add_argument("--colors", type=str, default=COLORS, help="palette (name or comma list)")
    m.add_common_args(ap)
    args = ap.parse_args()

    geom = m.geometry_from_args(args)
    rt = m.runtime_from_args(args, geom)
    palette = m.Palette.parse(args.colors)
    noise = m.PerlinNoise3D(seed=args.seed)

    px, py = m.angle_to_unit(args.pan_angle)
    xs, ys = geom.xs, geom.ys

    def render(t, dt, frame):
        raw = m.fbm3(noise,
                     xs * args.scale + px * args.pan_speed * t,
                     ys * args.scale + py * args.pan_speed * t,
                     t * args.evolve,
                     octaves=args.octaves)
        n = np.clip(0.5 + raw * args.contrast, 0.0, 1.0)   # -> [0,1]
        color = palette.map(n)                              # (N,3)
        bri = m.lerp(args.min_bri, args.max_bri, n)         # (N,)
        return color * bri[:, None]

    rt.run(render)


if __name__ == "__main__":
    main()
