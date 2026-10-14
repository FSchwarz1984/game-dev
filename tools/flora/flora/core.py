"""Shared math for the vegetation generator: projection, colour ramps, noise, randomness.

Projection (knowledge/15 section 0): oblique 3/4 view, 1 m = 20 native px on all three axes.
World axes: X east, Y up, Z south. Screen: sx = ax + X*PPM, sy = ay + (Z - Y)*PPM.
Depth toward the camera: D = Y + Z (larger = nearer).
Camera space for normals (what the normal maps store): x right, y screen-up, z toward the viewer.
  e_x = (1, 0, 0), e_up = (0, 1, -1)/sqrt2, e_view = (0, 1, 1)/sqrt2  (world components)
The baked key light comes from the upper left of the screen (from the north-west, about 48 deg
high), the same direction as every other asset in the game.
"""
import math

import numpy as np

PPM = 20.0                     # native pixels per metre
SQ2 = math.sqrt(2.0)
# Round things (trunk cross-sections, ropes, leaf masses, clusters) are drawn the way pixel artists
# draw them in 3/4 view: their own north-south depth is compressed (a horizontal ring around a trunk
# reads as a shallow arc, not the deep U the strict 1:1 oblique projection gives). Positions of the
# parts (limb tips, mass centres, root paths) stay at true world scale.
KZ = 0.42

# Two lights, as in hand-drawn 3/4 pixel art (knowledge/15 section 0: light from the upper left):
#  - the SHADING light baked into the sprites comes from the upper left of the picture and a little
#    toward the viewer, so faces turned to the camera are mid-tone, tops and left sides are lit,
#    right sides are dark (about the run-time sun at noon, seen on the screen);
#  - the SUN of the run-time lighting contract shared with the terrain (tools/terrain, toward_xz):
#    a fixed azimuth, its elevation changing with the time of day. It casts the shadows (baked at
#    SUN_ELEV_REF; the shadow shader stretches and slides them continuously for other elevations)
#    and lights the normal maps in Godot (uniform sun_dir).
_LC = np.array([-0.55, 0.60, 0.58])                 # camera space: x right, y up, z toward viewer
LIGHT_C = _LC / np.linalg.norm(_LC)
LIGHT_W = np.array([LIGHT_C[0], (LIGHT_C[1] + LIGHT_C[2]) / SQ2, (LIGHT_C[2] - LIGHT_C[1]) / SQ2])
LIGHT_W = LIGHT_W / np.linalg.norm(LIGHT_W)         # the shading light in world space (crown self-shade)
SUN_TOWARD_XZ = (-0.92, 0.38)       # toward the sun on the ground (x east, z south): the terrain's
SUN_ELEV_REF = 40.0                 # the elevation the cast shadows are baked at (degrees)


def sun_vector(elev_deg, toward_xz=SUN_TOWARD_XZ):
    """Unit vector toward the sun (world x east, y up, z south)."""
    d = np.asarray(toward_xz, np.float64)
    d = d / np.linalg.norm(d)
    e = math.radians(elev_deg)
    return np.array([d[0] * math.cos(e), math.sin(e), d[1] * math.cos(e)])


SHADOW_LIGHT_W = sun_vector(SUN_ELEV_REF)
SHADOW_DIR = -np.asarray(SUN_TOWARD_XZ, np.float64) / np.linalg.norm(SUN_TOWARD_XZ)   # on the ground


def world_to_cam(n):
    """World-space normals (..., 3) -> camera-space normals (..., 3)."""
    n = np.asarray(n, dtype=np.float64)
    x = n[..., 0]
    up = (n[..., 1] - n[..., 2]) / SQ2
    vw = (n[..., 1] + n[..., 2]) / SQ2
    return np.stack([x, up, vw], axis=-1)


def normalize(v, axis=-1):
    v = np.asarray(v, dtype=np.float64)
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.maximum(n, 1e-9)


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- colour (port of src/env/core.js)
def hex_rgb(h):
    h = h.lstrip('#')
    return [int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)]


def rgb_to_hsl(r, g, b):
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    mx, mn = max(r, g, b), min(r, g, b)
    h = s = 0.0
    l = (mx + mn) / 2
    if mx != mn:
        d = mx - mn
        s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
        if mx == r:
            h = (g - b) / d + (6 if g < b else 0)
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h /= 6
    return h, s, l


def hsl_to_rgb(h, s, l):
    h = ((h % 1) + 1) % 1
    if s == 0:
        return [l * 255, l * 255, l * 255]
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q

    def f(t):
        t = ((t % 1) + 1) % 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 0.5:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p
    return [f(h + 1 / 3) * 255, f(h) * 255, f(h - 1 / 3) * 255]


def _ang_diff(a, b):
    d = (b - a) % (2 * math.pi)
    if d > math.pi:
        d -= 2 * math.pi
    if d < -math.pi:
        d += 2 * math.pi
    return d


def ramp(base, n=5, lo=0.42, hi=0.38, hue_shift=0.055, sat_shift=0.1):
    """Hue-shifted ramp, dark -> light (shadows drift toward violet-blue, lights toward warm
    yellow). Same maths as ramp() in src/env/core.js, so the colours match the game palette."""
    c = hex_rgb(base) if isinstance(base, str) else list(base)
    h, s, l = rgb_to_hsl(*c)
    out = []
    for i in range(n):
        t = 0.5 if n == 1 else i / (n - 1)
        k = t - 0.5
        target = 0.68 if k < 0 else 0.13
        dh = _ang_diff(h * 2 * math.pi, target * 2 * math.pi) / (2 * math.pi)
        hh = h + dh * abs(k) * 2 * hue_shift * 4
        ll = min(1.0, max(0.0, l + (k * 2 * lo * l if k < 0 else k * 2 * hi * (1 - l))))
        sat = min(1.0, max(0.0, s + (abs(k) * sat_shift if k < 0 else -abs(k) * sat_shift * 0.8)))
        out.append([int(round(v)) for v in hsl_to_rgb(hh, sat, ll)])
    return np.array(out, dtype=np.uint8)


def mix(a, b, t):
    return (np.asarray(a, dtype=np.float64) * (1 - t) + np.asarray(b, dtype=np.float64) * t)


def lum(c):
    c = np.asarray(c, dtype=np.float64)
    return (c[..., 0] * 0.299 + c[..., 1] * 0.587 + c[..., 2] * 0.114) / 255.0


# ---------------------------------------------------------------- noise
def _hash_u32(*ints):
    """Integer hash on numpy int arrays -> uint32 (deterministic, platform independent)."""
    h = np.zeros(np.broadcast(*ints).shape, dtype=np.uint64)
    mults = (374761393, 668265263, 982451653, 2246822519, 3266489917)
    for k, v in enumerate(ints):
        h = h + (np.asarray(v).astype(np.int64).astype(np.uint64) * np.uint64(mults[k % 5]))
    h = h & np.uint64(0xFFFFFFFF)
    h = ((h ^ (h >> np.uint64(13))) * np.uint64(1274126177)) & np.uint64(0xFFFFFFFF)
    h = h ^ (h >> np.uint64(16))
    return h.astype(np.uint32)


def hash01(*ints):
    return _hash_u32(*ints).astype(np.float64) / 4294967296.0


def vnoise2(x, y, seed=0):
    """Smooth value noise in [0, 1) on float arrays."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    xi = np.floor(x).astype(np.int64)
    yi = np.floor(y).astype(np.int64)
    xf = x - xi
    yf = y - yi
    u = xf * xf * (3 - 2 * xf)
    v = yf * yf * (3 - 2 * yf)
    s = np.int64(seed)
    a = hash01(xi, yi, s)
    b = hash01(xi + 1, yi, s)
    c = hash01(xi, yi + 1, s)
    d = hash01(xi + 1, yi + 1, s)
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v


def vnoise3(x, y, z, seed=0):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    z = np.asarray(z, dtype=np.float64)
    xi, yi, zi = (np.floor(q).astype(np.int64) for q in (x, y, z))
    xf, yf, zf = x - xi, y - yi, z - zi
    u, v, w = (q * q * (3 - 2 * q) for q in (xf, yf, zf))
    s = np.int64(seed)
    out = 0.0
    for dz in (0, 1):
        for dy in (0, 1):
            for dx in (0, 1):
                h = hash01(xi + dx, yi + dy, zi + dz, s)
                wx = u if dx else 1 - u
                wy = v if dy else 1 - v
                wz = w if dz else 1 - w
                out = out + h * wx * wy * wz
    return out


def fbm2(x, y, octaves=3, seed=0, lac=2.03, gain=0.5):
    t = 0.0
    a = 0.5
    f = 1.0
    n = 0.0
    for i in range(octaves):
        t = t + a * vnoise2(np.asarray(x) * f, np.asarray(y) * f, seed + i * 17)
        n += a
        a *= gain
        f *= lac
    return t / n


class Rng:
    """Deterministic RNG with the helpers the painters use."""

    def __init__(self, seed):
        self.g = np.random.default_rng(int(seed) & 0xFFFFFFFF)

    def __call__(self):
        return float(self.g.random())

    def range(self, lo, hi):
        return lo + (hi - lo) * float(self.g.random())

    def int(self, lo, hi):
        return int(self.g.integers(lo, hi + 1))

    def pick(self, seq):
        return seq[int(self.g.integers(0, len(seq)))]

    def chance(self, p):
        return float(self.g.random()) < p

    def sign(self):
        return -1 if self.g.random() < 0.5 else 1

    def gauss(self, sd=1.0):
        return float(self.g.normal(0.0, sd))

    def unit3(self):
        v = self.g.normal(size=3)
        return v / max(np.linalg.norm(v), 1e-9)


def poisson_disc_sphere(n_target, rng, min_dot=None):
    """Roughly even points on the unit sphere (Fibonacci lattice with jitter)."""
    k = np.arange(n_target) + 0.5
    phi = np.arccos(1 - 2 * k / n_target)
    theta = math.pi * (1 + 5 ** 0.5) * k
    pts = np.stack([np.cos(theta) * np.sin(phi), np.cos(phi), np.sin(theta) * np.sin(phi)], axis=-1)
    pts += rng.g.normal(scale=0.55 / math.sqrt(n_target), size=pts.shape)
    return normalize(pts)
