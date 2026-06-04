#!/usr/bin/env python3
"""Chase: one or more comets running around the border, each with a fading tail.

Comets are positioned in perimeter-fraction space (0..1 clockwise from the
bottom-left corner), so they smoothly trace the rectangle. Each comet has a bright
head and an exponential tail trailing behind it. Use --direction ccw to reverse,
--start-phase to move the origin.

Examples:
    ./.venv/bin/python chase.py
    ./.venv/bin/python chase.py --count 3 --speed 0.25 --tail 0.08
    ./.venv/bin/python chase.py --count 2 --colors 'teal,magenta' --direction ccw
"""
import argparse

import numpy as np

import mirror_leds as m

# ---- defaults --------------------------------------------------------------
COUNT = 1           # number of comets
SPEED = 0.15        # loops around the rectangle per second
TAIL = 0.12         # tail length as a fraction of the loop
BACKGROUND = "black"
COLORS = m.DEFAULT_PALETTE


def main():
    ap = argparse.ArgumentParser(description="Comets chasing around the LED rectangle")
    ap.add_argument("--count", type=int, default=COUNT, help="number of comets")
    ap.add_argument("--speed", type=float, default=SPEED, help="loops per second")
    ap.add_argument("--tail", type=float, default=TAIL, help="tail length (fraction of loop)")
    ap.add_argument("--background", type=str, default=BACKGROUND, help="background color")
    ap.add_argument("--colors", type=str, default=COLORS, help="palette spread across comets")
    m.add_common_args(ap)
    args = ap.parse_args()

    geom = m.geometry_from_args(args)
    rt = m.runtime_from_args(args, geom)
    palette = m.Palette.parse(args.colors)
    bg = np.array(m.parse_color(args.background), dtype=float)
    ts = geom.ts
    count = max(1, args.count)

    # each comet starts evenly spaced, colored across the palette (bright end for one)
    starts = np.array([j / count for j in range(count)])
    cpos = np.array([1.0] if count == 1 else np.linspace(0.0, 1.0, count))
    comet_colors = palette.map(cpos)                        # (count, 3)
    tail = max(1e-4, args.tail)

    def render(t, dt, frame):
        rgb = np.tile(bg, (geom.num_leds, 1))
        for j in range(count):
            head = (starts[j] + args.speed * t) % 1.0
            d = (head - ts) % 1.0                           # distance behind the head, along travel
            inten = np.exp(-d / tail)
            rgb += inten[:, None] * comet_colors[j]
        return rgb

    rt.run(render)


if __name__ == "__main__":
    main()
