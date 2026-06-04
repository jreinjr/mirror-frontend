#!/usr/bin/env python3
"""Fire: flames that rise from the bottom edge up around the frame.

Heat is hottest along the bottom edge (and the lower parts of the side edges) and
fades toward the top, so the fire visually "rises" around the rectangle. A small
cellular-automaton (cool / diffuse / random spark) gives the flicker. Heat is
mapped through a black -> red -> orange -> yellow -> white palette.

The strip is a closed loop (index 0 and the last LED are both near the bottom-left
corner), so heat diffuses across that seam correctly.

Examples:
    ./.venv/bin/python fire.py
    ./.venv/bin/python fire.py --cooling 2.2 --sparking 10 --rise-bias 2
    ./.venv/bin/python fire.py --colors ice          # blue "cold fire"
"""
import argparse

import numpy as np

import mirror_leds as m

# ---- defaults --------------------------------------------------------------
COOLING = 1.5       # how fast cells cool (units/sec); higher = shorter flames
SPARKING = 8.0      # spark attempts per LED per second near the base
RISE_BIAS = 1.5     # >1 keeps flames lower; <1 lets heat climb higher
COLORS = "fire"     # black -> red -> orange -> yellow -> white


def main():
    ap = argparse.ArgumentParser(description="Rising fire around the LED rectangle")
    ap.add_argument("--cooling", type=float, default=COOLING, help="cooling rate (units/sec)")
    ap.add_argument("--sparking", type=float, default=SPARKING, help="spark rate near the base")
    ap.add_argument("--rise-bias", type=float, default=RISE_BIAS, help=">1 lower flames, <1 higher")
    ap.add_argument("--colors", type=str, default=COLORS, help="heat palette (e.g. fire, ember, ice)")
    m.add_common_args(ap)
    args = ap.parse_args()

    geom = m.geometry_from_args(args)
    rt = m.runtime_from_args(args, geom)
    palette = m.Palette.parse(args.colors)
    rng = np.random.default_rng(args.seed)
    n_leds = geom.num_leds
    w, h = geom.aspect

    # vertical rise profile: 1 at the bottom (y=0), fading to 0 at the top
    rise = np.clip(1.0 - geom.ys / h, 0.0, 1.0) ** args.rise_bias
    heat = np.zeros(n_leds)

    def render(t, dt, frame):
        nonlocal heat
        # 1. cool every cell by a random amount
        heat = np.clip(heat - rng.uniform(0, args.cooling, n_leds) * dt, 0.0, None)
        # 2. diffuse along the (looped) strip so flames are smooth, not pixelated
        heat = 0.64 * heat + 0.18 * np.roll(heat, 1) + 0.18 * np.roll(heat, -1)
        # 3. random sparks near the base (weighted by how low/hot the LED sits)
        spark = (rng.random(n_leds) < args.sparking * dt) * rng.uniform(0.6, 1.0, n_leds)
        heat = np.maximum(heat, rise * spark)
        # 4. steady embers at the very bottom so the fire never fully dies
        heat = np.maximum(heat, rise * 0.15)
        return palette.map(np.clip(heat, 0.0, 1.0))

    rt.run(render)


if __name__ == "__main__":
    main()
