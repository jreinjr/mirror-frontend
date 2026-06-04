#!/usr/bin/env python3
"""Pulse: a gentle sine "breathe" of the whole border, or a brightness wave that
travels around the perimeter.

By default the colors form a soft gradient around the frame (palette mapped to
perimeter position) and the whole thing breathes together. With --wave, the
brightness instead travels around the loop as a number of humps (--wave-count).

Examples:
    ./.venv/bin/python pulse.py --period 5
    ./.venv/bin/python pulse.py --wave --wave-count 3 --period 6
    ./.venv/bin/python pulse.py --colors 'teal' --min-bri 0.2
"""
import argparse

import numpy as np

import mirror_leds as m

# ---- defaults --------------------------------------------------------------
PERIOD = 4.0        # seconds per breath / wave cycle
MIN_BRI = 0.1
MAX_BRI = 1.0
WAVE = False        # False = uniform breathe, True = travelling brightness wave
WAVE_COUNT = 2      # number of brightness humps around the loop (wave mode)
COLORS = m.DEFAULT_PALETTE


def main():
    ap = argparse.ArgumentParser(description="Breathing pulse / travelling brightness wave")
    ap.add_argument("--period", type=float, default=PERIOD, help="seconds per cycle")
    ap.add_argument("--min-bri", type=float, default=MIN_BRI, help="brightness trough 0..1")
    ap.add_argument("--max-bri", type=float, default=MAX_BRI, help="brightness peak 0..1")
    ap.add_argument("--wave", action="store_true", default=WAVE, help="travelling wave instead of uniform")
    ap.add_argument("--wave-count", type=float, default=WAVE_COUNT, help="brightness humps around loop")
    ap.add_argument("--colors", type=str, default=COLORS, help="palette mapped around the perimeter")
    m.add_common_args(ap)
    args = ap.parse_args()

    geom = m.geometry_from_args(args)
    rt = m.runtime_from_args(args, geom)
    palette = m.Palette.parse(args.colors)
    base = palette.map(geom.ts)        # static gradient around the loop
    ts = geom.ts

    def render(t, dt, frame):
        if args.wave:
            phase = 2 * np.pi * (t / args.period - args.wave_count * ts)
        else:
            phase = 2 * np.pi * (t / args.period)
        bri = m.lerp(args.min_bri, args.max_bri, 0.5 - 0.5 * np.cos(phase))
        bri = np.broadcast_to(bri, (geom.num_leds,))
        return base * bri[:, None]

    rt.run(render)


if __name__ == "__main__":
    main()
