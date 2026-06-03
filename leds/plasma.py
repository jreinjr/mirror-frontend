#!/usr/bin/env python3
"""Plasma: classic multi-sine plasma over the rectangle's 2D coordinates.

Several sine waves over the aspect-correct (x, y) positions (including a radial
term about the center) are summed and mapped through the palette, giving a smooth
flowing field. Different vibe than the cloud: more rhythmic and colorful.

Examples:
    ./.venv/bin/python plasma.py
    ./.venv/bin/python plasma.py --scale 0.9 --speed 3 --colors sunset
    ./.venv/bin/python plasma.py --colors 'magenta,cyan,yellow'
"""
import argparse

import numpy as np

import mirror_leds as m

# ---- defaults --------------------------------------------------------------
SCALE = 0.6         # spatial frequency of the sine waves
SPEED = 2.0         # animation speed
COLORS = m.DEFAULT_PALETTE


def main():
    ap = argparse.ArgumentParser(description="Multi-sine plasma over the LED rectangle")
    ap.add_argument("--scale", type=float, default=SCALE, help="spatial frequency")
    ap.add_argument("--speed", type=float, default=SPEED, help="animation speed")
    ap.add_argument("--colors", type=str, default=COLORS, help="palette (name or comma list)")
    m.add_common_args(ap)
    args = ap.parse_args()

    geom = m.geometry_from_args(args)
    rt = m.runtime_from_args(args, geom)
    palette = m.Palette.parse(args.colors)
    xs, ys = geom.xs, geom.ys
    w, h = geom.aspect
    cx, cy = w / 2.0, h / 2.0
    radial = np.hypot(xs - cx, ys - cy)
    s = args.scale

    def render(t, dt, frame):
        sp = args.speed
        v = (np.sin(xs * s + t * sp)
             + np.sin(ys * s * 1.3 + t * sp * 0.9)
             + np.sin((xs + ys) * s * 0.7 + t * sp * 1.1)
             + np.sin(radial * s + t * sp * 1.3))
        n = (v + 4.0) / 8.0                 # 4 sines in [-4,4] -> [0,1]
        return palette.map(n)

    rt.run(render)


if __name__ == "__main__":
    main()
