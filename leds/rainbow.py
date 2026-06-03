#!/usr/bin/env python3
"""Rainbow: a hue gradient wrapped around the perimeter, rotating over time.

--cycles sets how many full hue wraps fit around the rectangle; --speed sets how
fast the whole pattern rotates (loops per second). --direction ccw reverses it.

Examples:
    ./.venv/bin/python rainbow.py
    ./.venv/bin/python rainbow.py --cycles 2 --speed 0.2
    ./.venv/bin/python rainbow.py --sat 0.7 --val 0.9 --direction ccw
"""
import argparse

import numpy as np

import mirror_leds as m

# ---- defaults --------------------------------------------------------------
SPEED = 0.1         # rotations around the loop per second
CYCLES = 1.0        # full hue wraps around the rectangle
SAT = 1.0           # saturation 0..1
VAL = 1.0           # value/brightness 0..1


def main():
    ap = argparse.ArgumentParser(description="Rotating rainbow around the LED rectangle")
    ap.add_argument("--speed", type=float, default=SPEED, help="rotations per second")
    ap.add_argument("--cycles", type=float, default=CYCLES, help="hue wraps around the loop")
    ap.add_argument("--sat", type=float, default=SAT, help="saturation 0..1")
    ap.add_argument("--val", type=float, default=VAL, help="value/brightness 0..1")
    m.add_common_args(ap)
    args = ap.parse_args()

    geom = m.geometry_from_args(args)
    rt = m.runtime_from_args(args, geom)
    ts = geom.ts

    def render(t, dt, frame):
        h = (args.cycles * ts + args.speed * t) % 1.0
        return m.hsv_to_rgb(h, args.sat, args.val)

    rt.run(render)


if __name__ == "__main__":
    main()
