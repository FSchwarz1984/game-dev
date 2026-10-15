"""Shared maths for the 3D asset generators: the view contract numbers, deterministic randomness,
value noise, hue-shifted colour ramps.

The view contract is docs/knowledge/21-3d-pixel-render.md (the renderer agent's): world axes X east,
Y up, Z south (toward the camera), metres; orthographic camera looking north and down at PITCH;
30 native px per metre on the camera plane (round 4: native 640x360; it was 20 at 480x270);
upright objects lean back by k = tan(PITCH / 2) per metre of height so that a vertical metre also
reads 30 px; textures at 30 texels per metre.
Every generator reads these numbers from here.
"""
from __future__ import annotations

import math

import numpy as np

# ---------------------------------------------------------------------------------------------
# the view contract (see the module docstring)
PPM = 30.0            # native px per metre on the camera plane (contract section 1; round 4)
PITCH = 55.0          # camera pitch below the horizon, degrees (contract: provisional, 50-60)
TEXEL_PER_M = 30.0    # texture density on surfaces (contract section 2.3; follows PPM)
PX = 1.0 / PPM        # one native pixel in metres (bars one pixel wide: lattices, slats)
LEAN_K = math.tan(math.radians(PITCH) / 2)   # upright objects: z -= k * height (shader does it)


def screen_px(p, origin=(0.0, 0.0, 0.0)):
    """Native screen px (x right, y up) of a point on an upright object, relative to its origin,
    as the renderer draws it (contract section 1)."""
    p = np.asarray(p, np.float64)
    o = np.asarray(origin, np.float64)
    d = p - o
    return np.stack([PPM * d[..., 0], PPM * (d[..., 1] - math.sin(math.radians(PITCH)) * d[..., 2])], axis=-1)


def cam_vectors(pitch=None):
    """(right, up, toward_camera) unit vectors of the fixed camera in world space."""
    p = math.radians(PITCH if pitch is None else pitch)
    right = np.array([1.0, 0.0, 0.0])
    up = np.array([0.0, math.cos(p), -math.sin(p)])
    back = np.array([0.0, math.sin(p), math.cos(p)])     # from the scene toward the camera
    return right, up, back


# ---------------------------------------------------------------------------------------------
# small vector helpers
def normalize(v, axis=-1):
    v = np.asarray(v, dtype=np.float64)
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.maximum(n, 1e-12)


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float64)


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], np.float64)


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float64)


def rot_axis(axis, a):
    """Rotation matrix about a unit axis (Rodrigues)."""
    axis = normalize(axis)
    x, y, z = axis
    c, s = math.cos(a), math.sin(a)
    C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]], np.float64)


# ---------------------------------------------------------------------------------------------
# randomness: everything is seeded; the same seed gives the same asset on every machine
def rng(seed):
    return np.random.default_rng(np.uint64(seed & 0xFFFFFFFFFFFF))


def _hash_u32(*ints):
    shape = np.broadcast(*[np.asarray(v) for v in ints]).shape
    h = np.zeros(shape, dtype=np.uint64)
    mults = (374761393, 668265263, 982451653, 2246822519, 3266489917)
    with np.errstate(over='ignore'):
        for k, v in enumerate(ints):
            h = h + (np.asarray(v).astype(np.int64).astype(np.uint64) * np.uint64(mults[k % 5]))
        h = h & np.uint64(0xFFFFFFFF)
        h = ((h ^ (h >> np.uint64(13))) * np.uint64(1274126177)) & np.uint64(0xFFFFFFFF)
        h = h ^ (h >> np.uint64(16))
    return np.asarray(h).astype(np.uint32)


def hash01(*ints):
    """Integer lattice hash in [0, 1)."""
    return _hash_u32(*ints).astype(np.float64) / 4294967296.0


def vnoise2(x, y, seed=0):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    xi = np.floor(x).astype(np.int64)
    yi = np.floor(y).astype(np.int64)
    xf, yf = x - xi, y - yi
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
    out = np.zeros(np.broadcast(x, y, z).shape)
    for dz in (0, 1):
        wz = w if dz else 1 - w
        for dy in (0, 1):
            wy = v if dy else 1 - v
            for dx in (0, 1):
                wx = u if dx else 1 - u
                out = out + hash01(xi + dx, yi + dy, zi + dz, s) * wx * wy * wz
    return out


def fbm2(x, y, octaves=4, seed=0, lac=2.03, gain=0.5):
    t = 0.0
    a = 1.0
    n = 0.0
    f = 1.0
    for o in range(octaves):
        t = t + a * vnoise2(np.asarray(x) * f, np.asarray(y) * f, seed + o * 17)
        n += a
        a *= gain
        f *= lac
    return t / n


def fbm3(x, y, z, octaves=4, seed=0, lac=2.03, gain=0.5):
    t = 0.0
    a = 1.0
    n = 0.0
    f = 1.0
    for o in range(octaves):
        t = t + a * vnoise3(np.asarray(x) * f, np.asarray(y) * f, np.asarray(z) * f, seed + o * 17)
        n += a
        a *= gain
        f *= lac
    return t / n


def ridge2(x, y, octaves=3, seed=0):
    t = 0.0
    a = 1.0
    n = 0.0
    f = 1.0
    for o in range(octaves):
        t = t + a * (1 - np.abs(vnoise2(np.asarray(x) * f, np.asarray(y) * f, seed + o * 31) * 2 - 1))
        n += a
        a *= 0.5
        f *= 2.1
    return t / n


# ---------------------------------------------------------------------------------------------
# colour: the hue-shifted ramp of the game palette (port of src/env/core.js ramp())
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
    """Hue-shifted ramp, dark -> light: shadows drift toward violet-blue, lights toward warm yellow.
    Same maths as ramp() in src/env/core.js and tools/flora, so colours match the game palette."""
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
    return np.asarray(a, dtype=np.float64) * (1 - t) + np.asarray(b, dtype=np.float64) * t


def lum(c):
    c = np.asarray(c, dtype=np.float64)
    return (c[..., 0] * 0.299 + c[..., 1] * 0.587 + c[..., 2] * 0.114) / 255.0


BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float64)


def bayer(x, y):
    """Ordered-dither threshold in (0, 1) at integer texel coordinates."""
    return (BAYER4[np.asarray(y) & 3, np.asarray(x) & 3] + 0.5) / 16.0
