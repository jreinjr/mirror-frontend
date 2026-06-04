# Magic Mirror LED animations

Animations for the ~120-LED WS2812 strip wound **clockwise around a portrait 16:9
rectangle**, starting at the **bottom-left corner** (up the left edge → across the
top → down the right edge → across the bottom).

All effects share [mirror_leds.py](mirror_leds.py), which knows the geometry (each
LED's 2D position and its fraction around the loop), a color/palette system, a
numpy Perlin/fBm noise generator, and a fixed-FPS runtime that handles brightness,
gamma, and a clean shutdown (LEDs are always cleared on exit).

## Running

Use the project venv (don't need to activate it):

```bash
./.venv/bin/python cloud.py
./.venv/bin/python cloud.py --scale 0.5 --evolve 0.25 --colors '#ff0066,#3300ff'
```

Press **Ctrl-C** to stop — the strip is cleared automatically. Or pass
`--duration 30` to run a scene for 30 seconds and then exit.

> **PSU safety:** master brightness defaults to **0.3**. Keep it ≤0.3 unless your
> power supply is 4A+ (`--brightness 0.5`, etc.).

## The effects

| Script | What it does | Key flags |
| --- | --- | --- |
| `cloud.py` | **Flagship.** 2D fractal-noise cloud drifting over the frame; noise drives color + brightness. | `--scale --evolve --pan-speed --pan-angle --octaves --contrast --min-bri --max-bri --colors` |
| `chase.py` | Comets with fading tails running around the border. | `--count --speed --tail --background --colors` |
| `twinkle.py` | Random sparkles fading in/out from the palette. | `--rate --fade-in --fade-out --max-concurrent --bg-glow --colors` |
| `pulse.py` | Sine "breathe" of the whole frame, or a travelling brightness wave. | `--period --min-bri --max-bri --wave --wave-count --colors` |
| `rainbow.py` | Hue gradient wrapped around the loop, rotating. | `--speed --cycles --sat --val` |
| `plasma.py` | Multi-sine plasma over the rectangle's 2D coordinates. | `--scale --speed --colors` |
| `fire.py` | Flames rising from the bottom edge around the frame. | `--cooling --sparking --rise-bias --colors` |

Run `./.venv/bin/python <script>.py --help` for the full list.

## Common flags (every script)

`--fps` · `--brightness` (master 0..1) · `--gamma` · `--duration` (sec, 0=forever) ·
`--colors` · `--num-leds` · `--led-count` · `--edge-counts` · `--direction` ·
`--start-phase` · `--seed`

## Colors & palettes

`--colors` accepts:

- **Named palettes:** `cool` (default, ethereal), `ocean`, `ember`, `fire`,
  `aurora`, `sunset`, `ice`, `white`, `rainbow`.
- **A comma list of colors:** `--colors '#ff0066,#3300ff'` or `--colors 'teal,white'`.
  Each is a hex (`#ff0066`, `#f06`, `ff0066`) or a name (`red`, `teal`, `skyblue`…).

How the noise/value (0..1) maps to a palette:

- **1 color** → black → that color (dark to bright).
- **2 colors** → first at the dark end, second at the bright end.
- **3+ colors** → an evenly-spaced gradient across them.

## Geometry tuning

The LED-per-edge split defaults to the 16:9 proportions (≈ `[38,22,38,22]` for 120
LEDs). If you measure your real strip, override it:

```bash
./.venv/bin/python cloud.py --edge-counts 39,22,38,21   # left,top,right,bottom (must sum to --num-leds)
```

Other orientation knobs:

- `--direction ccw` — reverse chase/rainbow/wave direction.
- `--start-phase 0.25` — rotate where LED 0 sits around the loop (fraction 0..1).

To check orientation, run `./.venv/bin/python chase.py --count 1 --speed 0.1` — the
single comet should start at the bottom-left and travel **up the left edge first**.

## If LEDs get stuck on

A crash (or `kill -9`) can leave pixels lit. Clear them with:

```bash
./.venv/bin/python -c "from mirror_leds import make_strip; s=make_strip(); s.clear(); s.show()"
```
