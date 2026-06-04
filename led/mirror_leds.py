"""Shared toolkit for the magic-mirror LED animations.

The strip (~120 LEDs) is wound around the border of a monitor in a *portrait 16:9*
rectangle, starting at the BOTTOM-LEFT corner and running CLOCKWISE:

        TOP  (9 units)
      +-----------+
      |           |
 LEFT |           | RIGHT      LED 0 is at the bottom-left corner.
 (16) |           | (16)       Increasing index walks clockwise:
      |           |              up LEFT -> across TOP -> down RIGHT -> across BOTTOM.
      +-----------+
      ^  BOTTOM (9 units)
      LED 0

Everything an effect needs is here: geometry (each LED's 2D position + perimeter
fraction), a color/palette utility, a numpy Perlin/fBm noise generator, and a
fixed-FPS runtime loop that handles brightness, gamma, clamping and clean shutdown.

Only `make_strip()` touches the hardware, so geometry/palette/noise can be imported
and tested on a machine without the Pi / spidev.
"""

from __future__ import annotations

import argparse
import math
import signal
import time
from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# Defaults (every script can override these via CLI flags / constants)
# ---------------------------------------------------------------------------
NUM_LEDS = 120          # logical LEDs animated around the rectangle
LED_COUNT = 121         # value passed to the driver (matches working white.py; extra pixel -> black)
SPI_BUS = 0
SPI_DEVICE = 0
ASPECT = (9, 16)        # (width, height) in aspect units -> portrait 16:9
MASTER_BRIGHTNESS = 0.3  # hardware global cap. Keep <=0.3 unless PSU is 4A+
GAMMA = 2.4             # perceptual correction, applied once in the runtime loop
FPS = 60

DEFAULT_PALETTE = "ocean"  # ethereal teal -> blue -> soft white


# ===========================================================================
# Geometry
# ===========================================================================
def _largest_remainder(total: int, weights) -> list[int]:
    """Apportion `total` units across buckets proportional to `weights`, with the
    rounding error distributed so the result sums to exactly `total`."""
    weights = np.asarray(weights, dtype=float)
    exact = weights / weights.sum() * total
    floor = np.floor(exact).astype(int)
    remainder = total - int(floor.sum())
    # hand the leftover units to the buckets with the largest fractional parts
    order = np.argsort(-(exact - floor))
    for i in range(remainder):
        floor[order[i]] += 1
    return floor.tolist()


@dataclass(frozen=True)
class Geometry:
    num_leds: int
    aspect: tuple
    edge_counts: tuple          # (left, top, right, bottom)
    xs: np.ndarray              # aspect-correct x in [0, W]   <- USE for 2D noise (round blobs)
    ys: np.ndarray              # aspect-correct y in [0, H]
    nx: np.ndarray              # normalized x in [0, 1] (convenience only)
    ny: np.ndarray              # normalized y in [0, 1]
    ts: np.ndarray              # perimeter fraction [0, 1), cw from bottom-left
    edge_id: np.ndarray         # 0=left 1=top 2=right 3=bottom


def build_geometry(num_leds: int = NUM_LEDS, aspect: tuple = ASPECT,
                   edge_counts=None, start_phase: float = 0.0,
                   direction: str = "cw") -> Geometry:
    """Place `num_leds` LEDs around the rectangle border and return their coords.

    edge_counts: optional (left, top, right, bottom) override; must sum to num_leds.
                 If None, derived proportionally from edge lengths.
    start_phase: fraction added to every perimeter position (rotate LED-0 origin).
    direction:   "cw" (default, matches the physical winding) or "ccw" (reverse ts).
    """
    w, h = aspect
    # perimeter segments in walk order, clockwise from bottom-left
    seg_len = [h, w, h, w]              # left, top, right, bottom
    perim = sum(seg_len)

    if edge_counts is None:
        edge_counts = _largest_remainder(num_leds, seg_len)
    else:
        edge_counts = list(edge_counts)
        if sum(edge_counts) != num_leds:
            raise ValueError(f"edge_counts {edge_counts} sum to {sum(edge_counts)}, "
                             f"expected num_leds={num_leds}")

    # perimeter distance s for each LED: evenly spaced within its own edge, half-step inset
    seg_start = [0.0]
    for L in seg_len[:-1]:
        seg_start.append(seg_start[-1] + L)

    s = np.empty(num_leds)
    edge_id = np.empty(num_leds, dtype=int)
    idx = 0
    for e in range(4):
        n = edge_counts[e]
        for k in range(n):
            s[idx] = seg_start[e] + (k + 0.5) * seg_len[e] / n
            edge_id[idx] = e
            idx += 1

    xs = np.empty(num_leds)
    ys = np.empty(num_leds)
    for i in range(num_leds):
        si = s[i]
        if si < h:                      # LEFT edge, going up
            xs[i], ys[i] = 0.0, si
        elif si < h + w:                # TOP edge, going right
            xs[i], ys[i] = si - h, h
        elif si < 2 * h + w:            # RIGHT edge, going down
            xs[i], ys[i] = w, h - (si - h - w)
        else:                           # BOTTOM edge, going left
            xs[i], ys[i] = w - (si - 2 * h - w), 0.0

    ts = (s / perim + start_phase) % 1.0
    if direction == "ccw":
        ts = (1.0 - ts) % 1.0
    elif direction != "cw":
        raise ValueError("direction must be 'cw' or 'ccw'")

    nx = xs / w
    ny = ys / h
    return Geometry(num_leds, aspect, tuple(edge_counts), xs, ys, nx, ny, ts, edge_id)


# ===========================================================================
# Color / palette
# ===========================================================================
def clamp8(arr) -> np.ndarray:
    """(...,3) float -> uint8-safe ints in 0..255. Guards the library's uint8 cast:
    NaN/inf -> 0, then clip and round. Returns an int array; build Color(int(r),...)."""
    arr = np.nan_to_num(np.asarray(arr, dtype=float), nan=0.0, posinf=255.0, neginf=0.0)
    return np.clip(np.rint(arr), 0, 255).astype(int)


def hsv_to_rgb(h, s, v) -> np.ndarray:
    """Vectorized HSV->RGB. h,s,v in [0,1] (h wraps). Returns (...,3) float in 0..255."""
    h = np.asarray(h, dtype=float) % 1.0
    s = np.clip(np.asarray(s, dtype=float), 0, 1)
    v = np.clip(np.asarray(v, dtype=float), 0, 1)
    i = np.floor(h * 6.0)
    f = h * 6.0 - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    i = i.astype(int) % 6
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1) * 255.0


def hex_to_rgb(spec: str):
    s = spec.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"bad hex color: {spec!r}")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


NAMED_COLORS = {
    "black": (0, 0, 0), "white": (255, 255, 255), "warmwhite": (255, 190, 120),
    "red": (255, 0, 0), "orange": (255, 90, 0), "amber": (255, 150, 30),
    "yellow": (255, 220, 0), "green": (0, 255, 0), "teal": (0, 200, 180),
    "cyan": (0, 255, 255), "blue": (0, 60, 255), "skyblue": (60, 160, 255),
    "indigo": (40, 0, 200), "purple": (150, 0, 255), "magenta": (255, 0, 200),
    "pink": (255, 80, 160),
}

# named multi-stop palettes (low noise/black end -> high noise/white end)
NAMED_PALETTES = {
    "cool": ["#9EA8B5", "teal", "skyblue", "#dff2ff"],     # ethereal default
    "ocean": ["#001020", "#003a66", "teal", "cyan"],
    "ember": ["black", "#330000", "red", "orange", "#ffd060"],
    "fire": ["black", "red", "orange", "yellow", "white"],
    "aurora": ["#001a10", "#00aa66", "teal", "#a0ffe0"],
    "sunset": ["#1a0030", "purple", "magenta", "orange", "#ffd060"],
    "ice": ["#00121f", "#0050a0", "skyblue", "white"],
    "white": ["warmwhite"],
    "rainbow": ["red", "yellow", "green", "cyan", "blue", "magenta", "red"],
}


def parse_color(spec):
    """Accept '#ff0066' / 'f06' / 'red' / (r,g,b). Returns an (r,g,b) int tuple."""
    if isinstance(spec, (tuple, list)):
        return tuple(int(c) for c in spec)
    key = str(spec).strip().lower()
    if key in NAMED_COLORS:
        return NAMED_COLORS[key]
    return hex_to_rgb(key)


class Palette:
    """Maps t in [0,1] to an RGB color via piecewise-linear interpolation of stops.

    1 stop  C       -> ramps black -> C   (noise 0 = dark, noise 1 = C)
    2 stops A,B      -> A at 0, B at 1
    3+ stops         -> evenly spaced multi-stop gradient
    """

    def __init__(self, stops):
        stops = [parse_color(s) for s in stops]
        if len(stops) == 1:
            stops = [(0, 0, 0), stops[0]]
        self.stops = np.array(stops, dtype=float)            # (k, 3)
        self.positions = np.linspace(0.0, 1.0, len(self.stops))

    @classmethod
    def parse(cls, spec) -> "Palette":
        """'cool' (named) or '#ff0066,#3300ff' / 'red,blue,white' (comma list)."""
        if isinstance(spec, Palette):
            return spec
        if isinstance(spec, (list, tuple)):
            return cls(list(spec))
        key = str(spec).strip().lower()
        if key in NAMED_PALETTES:
            return cls(NAMED_PALETTES[key])
        return cls([p for p in str(spec).split(",") if p.strip()])

    def map(self, t) -> np.ndarray:
        """t: array in [0,1] -> (N,3) float 0..255."""
        t = np.clip(np.asarray(t, dtype=float), 0.0, 1.0)
        r = np.interp(t, self.positions, self.stops[:, 0])
        g = np.interp(t, self.positions, self.stops[:, 1])
        b = np.interp(t, self.positions, self.stops[:, 2])
        return np.stack([r, g, b], axis=-1)


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


# ===========================================================================
# Perlin / fBm noise (numpy, vectorized over the LED sample points)
# ===========================================================================
_GRAD3 = np.array([
    (1, 1, 0), (-1, 1, 0), (1, -1, 0), (-1, -1, 0),
    (1, 0, 1), (-1, 0, 1), (1, 0, -1), (-1, 0, -1),
    (0, 1, 1), (0, -1, 1), (0, 1, -1), (0, -1, -1),
    (1, 1, 0), (-1, 1, 0), (0, -1, 1), (0, -1, -1),
], dtype=float)


class PerlinNoise3D:
    """Classic 3D Perlin gradient noise. sample() returns values in ~[-1, 1]."""

    def __init__(self, seed: int = 0):
        rng = np.random.default_rng(seed)
        p = rng.permutation(256)
        self.perm = np.concatenate([p, p]).astype(int)      # length 512, avoids wrap branch

    @staticmethod
    def _fade(t):
        return t * t * t * (t * (t * 6 - 15) + 10)          # quintic, C2 continuous

    def _grad(self, h, x, y, z):
        g = _GRAD3[h & 15]
        return g[..., 0] * x + g[..., 1] * y + g[..., 2] * z

    def sample(self, x, y, z) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        z = np.asarray(z, dtype=float)
        xi = np.floor(x).astype(int) & 255
        yi = np.floor(y).astype(int) & 255
        zi = np.floor(z).astype(int) & 255
        xf = x - np.floor(x)
        yf = y - np.floor(y)
        zf = z - np.floor(z)
        u, v, w = self._fade(xf), self._fade(yf), self._fade(zf)

        perm = self.perm
        a = perm[xi] + yi
        aa = perm[a] + zi
        ab = perm[a + 1] + zi
        b = perm[xi + 1] + yi
        ba = perm[b] + zi
        bb = perm[b + 1] + zi

        def lp(t, lo, hi):
            return lo + t * (hi - lo)

        x1 = lp(u, self._grad(perm[aa], xf, yf, zf),
                   self._grad(perm[ba], xf - 1, yf, zf))
        x2 = lp(u, self._grad(perm[ab], xf, yf - 1, zf),
                   self._grad(perm[bb], xf - 1, yf - 1, zf))
        y1 = lp(v, x1, x2)
        x3 = lp(u, self._grad(perm[aa + 1], xf, yf, zf - 1),
                   self._grad(perm[ba + 1], xf - 1, yf, zf - 1))
        x4 = lp(u, self._grad(perm[ab + 1], xf, yf - 1, zf - 1),
                   self._grad(perm[bb + 1], xf - 1, yf - 1, zf - 1))
        y2 = lp(v, x3, x4)
        return lp(w, y1, y2)


def fbm3(noise: PerlinNoise3D, x, y, z, octaves: int = 4,
         lacunarity: float = 2.0, gain: float = 0.5) -> np.ndarray:
    """Fractal Brownian motion: sum of `octaves` Perlin octaves, normalized to ~[-1, 1]."""
    total = np.zeros_like(np.asarray(x, dtype=float))
    freq, amp, norm = 1.0, 1.0, 0.0
    for _ in range(max(1, octaves)):
        total = total + amp * noise.sample(np.asarray(x) * freq,
                                            np.asarray(y) * freq,
                                            np.asarray(z) * freq)
        norm += amp
        freq *= lacunarity
        amp *= gain
    return total / norm


# ===========================================================================
# Hardware + runtime loop
# ===========================================================================
def make_strip(led_count: int = LED_COUNT, spi_bus: int = SPI_BUS,
               spi_device: int = SPI_DEVICE, master_brightness: float = MASTER_BRIGHTNESS):
    """Open the SPI WS2812 strip. This is the ONLY function that touches hardware."""
    from rpi5_ws2812.ws2812 import WS2812SpiDriver
    strip = WS2812SpiDriver(spi_bus=spi_bus, spi_device=spi_device, led_count=led_count).get_strip()
    strip.set_brightness(max(0.0, min(1.0, master_brightness)))
    return strip


class Runtime:
    """Fixed-FPS render loop. The render callback returns an (N,3) perceptual float
    array (0..255); this loop applies gamma once, clamps, writes pixels and shows.
    Installs signal handlers + try/finally so LEDs are always cleared on exit."""

    def __init__(self, strip, geom: Geometry, *, fps: int = FPS, gamma: float = GAMMA,
                 num_leds: int = NUM_LEDS, led_count: int = LED_COUNT, duration: float = 0.0):
        from rpi5_ws2812.ws2812 import Color
        self._Color = Color
        self.strip = strip
        self.geom = geom
        self.fps = max(1, fps)
        self.gamma = gamma
        self.num_leds = num_leds
        self.led_count = led_count
        self.duration = duration  # seconds; 0 = run until interrupted
        if led_count < num_leds:
            raise ValueError(f"led_count ({led_count}) must be >= num_leds ({num_leds})")
        self._stop = False

    def _handle_signal(self, *_):
        self._stop = True

    def _write(self, rgb: np.ndarray):
        # rgb: (N,3) perceptual 0..255 -> gamma once -> clamp -> pixels
        out = (np.clip(rgb, 0, 255) / 255.0) ** self.gamma * 255.0
        out = clamp8(out)
        Color = self._Color
        set_pixel = self.strip.set_pixel_color
        for i in range(self.num_leds):
            set_pixel(i, Color(int(out[i, 0]), int(out[i, 1]), int(out[i, 2])))
        # any padding pixels beyond the animated set -> off
        for i in range(self.num_leds, self.led_count):
            set_pixel(i, Color(0, 0, 0))
        self.strip.show()

    def run(self, render):
        """render(t, dt, frame) -> (N,3) float in 0..255 (perceptual)."""
        prev = signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        frame_dt = 1.0 / self.fps
        t0 = time.monotonic()
        next_frame = t0
        last = t0
        frame = 0
        try:
            while not self._stop:
                now = time.monotonic()
                t = now - t0
                if self.duration and t >= self.duration:
                    break
                dt = now - last
                last = now
                try:
                    rgb = render(t, dt, frame)
                except Exception as exc:  # never die mid-frame with LEDs lit
                    print(f"[mirror_leds] render error: {exc!r}")
                    break
                self._write(np.asarray(rgb, dtype=float))
                frame += 1
                # monotonic-accumulator pacing (no drift; drop frames if behind)
                next_frame += frame_dt
                sleep = next_frame - time.monotonic()
                if sleep > 0:
                    time.sleep(sleep)
                else:
                    next_frame = time.monotonic()  # fell behind: reset schedule, don't burst
        finally:
            signal.signal(signal.SIGINT, prev[0])
            signal.signal(signal.SIGTERM, prev[1])
            self.strip.clear()
            self.strip.show()


# ===========================================================================
# CLI helpers shared by every effect script
# ===========================================================================
def add_common_args(parser: argparse.ArgumentParser):
    parser.add_argument("--fps", type=int, default=FPS, help="frames per second")
    parser.add_argument("--brightness", type=float, default=MASTER_BRIGHTNESS,
                        help="hardware master brightness 0..1 (keep <=0.3 unless PSU 4A+)")
    parser.add_argument("--gamma", type=float, default=GAMMA, help="perceptual gamma")
    parser.add_argument("--num-leds", type=int, default=NUM_LEDS, help="animated LED count")
    parser.add_argument("--led-count", type=int, default=LED_COUNT, help="driver LED count")
    parser.add_argument("--edge-counts", type=str, default=None,
                        help="override per-edge counts 'left,top,right,bottom' (must sum to num-leds)")
    parser.add_argument("--direction", choices=["cw", "ccw"], default="cw",
                        help="perimeter direction for chase/rainbow/wave effects")
    parser.add_argument("--start-phase", type=float, default=0.0,
                        help="rotate the LED-0 origin around the loop (fraction 0..1)")
    parser.add_argument("--seed", type=int, default=0, help="random seed (noise/twinkle)")
    parser.add_argument("--duration", type=float, default=0.0,
                        help="run for N seconds then clear & exit (0 = until Ctrl-C)")
    return parser


def geometry_from_args(args) -> Geometry:
    edge_counts = None
    if args.edge_counts:
        edge_counts = tuple(int(x) for x in args.edge_counts.split(","))
    return build_geometry(num_leds=args.num_leds, edge_counts=edge_counts,
                          start_phase=args.start_phase, direction=args.direction)


def runtime_from_args(args, geom: Geometry) -> Runtime:
    """Build the strip + runtime from common args. (Touches hardware.)"""
    strip = make_strip(led_count=args.led_count, master_brightness=args.brightness)
    return Runtime(strip, geom, fps=args.fps, gamma=args.gamma,
                   num_leds=args.num_leds, led_count=args.led_count,
                   duration=getattr(args, "duration", 0.0))


def angle_to_unit(deg: float):
    r = math.radians(deg)
    return math.cos(r), math.sin(r)
