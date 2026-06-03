#!/usr/bin/env python3
"""Twinkle: random sparkles that fade in and out over a faint background.

Sparks spawn at a configurable rate, each on a random LED with a random color
drawn from the palette, fading in then out over the given durations. Timing is
elapsed-time based, so it looks the same at any FPS.

Examples:
    ./.venv/bin/python twinkle.py
    ./.venv/bin/python twinkle.py --rate 16 --fade-in 0.1 --fade-out 0.5
    ./.venv/bin/python twinkle.py --colors 'white' --bg-glow 0.04
"""
import argparse
import random

import numpy as np

import mirror_leds as m

# ---- defaults --------------------------------------------------------------
RATE = 8.0          # sparks spawned per second
FADE_IN = 0.3       # seconds to brighten
FADE_OUT = 0.8      # seconds to dim
MAX_CONCURRENT = 40  # cap on simultaneously live sparks
BG_GLOW = 0.0       # faint background brightness (0..1) of palette midpoint
COLORS = m.DEFAULT_PALETTE


def main():
    ap = argparse.ArgumentParser(description="Random twinkle sparkles around the rectangle")
    ap.add_argument("--rate", type=float, default=RATE, help="sparks per second")
    ap.add_argument("--fade-in", type=float, default=FADE_IN, help="fade-in seconds")
    ap.add_argument("--fade-out", type=float, default=FADE_OUT, help="fade-out seconds")
    ap.add_argument("--max-concurrent", type=int, default=MAX_CONCURRENT, help="live spark cap")
    ap.add_argument("--bg-glow", type=float, default=BG_GLOW, help="faint background brightness 0..1")
    ap.add_argument("--colors", type=str, default=COLORS, help="palette to draw spark colors from")
    m.add_common_args(ap)
    args = ap.parse_args()

    geom = m.geometry_from_args(args)
    rt = m.runtime_from_args(args, geom)
    palette = m.Palette.parse(args.colors)
    rng = random.Random(args.seed)
    n_leds = geom.num_leds
    base = palette.map(np.full(n_leds, 0.5)) * args.bg_glow   # faint background glow
    life = args.fade_in + args.fade_out
    sparks = []  # each: dict(led, color(3,), t0)

    def render(t, dt, frame):
        # spawn: expected rate*dt new sparks this frame
        expected = args.rate * dt
        n_new = int(expected) + (1 if rng.random() < (expected - int(expected)) else 0)
        for _ in range(n_new):
            if len(sparks) >= args.max_concurrent:
                break
            color = palette.map(np.array([rng.random()]))[0] * rng.uniform(0.6, 1.0)
            sparks.append({"led": rng.randrange(n_leds), "color": color, "t0": t})

        rgb = base.copy()
        alive = []
        for s in sparks:
            age = t - s["t0"]
            if age >= life:
                continue
            if age < args.fade_in:
                env = age / args.fade_in if args.fade_in > 0 else 1.0
            else:
                env = 1.0 - (age - args.fade_in) / args.fade_out if args.fade_out > 0 else 0.0
            rgb[s["led"]] += s["color"] * env
            alive.append(s)
        sparks[:] = alive
        return rgb

    rt.run(render)


if __name__ == "__main__":
    main()
