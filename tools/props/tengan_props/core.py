"""Shared constants and maths for the props generator (docs/knowledge/19-props.md).

Projection (knowledge/15 section 0): oblique 3/4 view, 1 m = 20 native px on every axis.
  World: metres, x east, y up, z south.  Screen: sx = ax + 20 x,  sy = ay + 20 (z - y).
  Depth toward the camera: D = y + z (larger = nearer). The view ray through a pixel is the line
  (x, y, z) + t (0, 1, 1): every point on it lands on the same pixel.

Light (knowledge/15 section 0, the lead's decision of 2026-10-14):
  - SURFACE light is a fixed screen-space direction: from the upper left, a little toward the viewer
    (LIGHT_C, the same vector as tools/flora core.LIGHT_C; in Godot the DirectionalLight2D with
    rotation -42.5 deg and height 0.42). Normal maps are in camera space (x right, y screen-up,
    z toward the viewer) and follow the convention: level tops face the viewer tilted UP by TILT_DEG,
    south faces face the viewer tilted DOWN by TILT_DEG, east sides face right (darkest), west sides
    face left (lit).
  - CAST SHADOWS come from a sun in the north-west (SUN_TOWARD_XZ, same as tools/flora): they fall to
    the lower right, their length set by the sun's elevation at run time (horizon maps, shadow.py).
"""
import math

import numpy as np

PPM = 20.0
SQ2 = math.sqrt(2.0)
KZ = 0.42           # round things: their own north-south depth is drawn compressed (as tools/flora)
TILT_DEG = 20.0     # normal-map tilt of level tops (up) and south faces (down), knowledge/15 section 0

_LC = np.array([-0.55, 0.60, 0.58])
LIGHT_C = _LC / np.linalg.norm(_LC)          # camera space: x right, y up, z toward the viewer
SUN_TOWARD_XZ = (-0.92, -0.38)               # toward the shadow sun on the ground (x east, z south)
SHADOW_DIR = -np.asarray(SUN_TOWARD_XZ) / np.linalg.norm(SUN_TOWARD_XZ)   # shadows fall this way
SHADOW_MIN_ELEV = 12.0                       # below this the cast shadows stop growing (degrees)
VIEW_W = np.array([0.0, 1.0, 1.0]) / SQ2     # toward the viewer, world


def normalize(v, axis=-1):
    v = np.asarray(v, dtype=np.float64)
    n = np.linalg.norm(v, axis=axis, keepdims=True)
    return v / np.maximum(n, 1e-12)


def world_to_cam_strict(n):
    """World normals -> camera space by the strict oblique map (tops 45 deg up, south 45 deg down)."""
    n = np.asarray(n, dtype=np.float64)
    up = (n[..., 1] - n[..., 2]) / SQ2
    vw = (n[..., 1] + n[..., 2]) / SQ2
    return np.stack([n[..., 0], up, vw], axis=-1)


_TILT_K = math.tan(math.radians(TILT_DEG))


def world_to_cam(n):
    """World normals -> camera-space normals in the project's convention (knowledge/15 section 0):
    the strict map's vertical angle is compressed so that a level top tilts up by TILT_DEG and a
    south face tilts down by TILT_DEG; east/west sides stay sideways."""
    c = world_to_cam_strict(n)
    up = c[..., 1] * _TILT_K
    out = np.stack([c[..., 0], up, c[..., 2]], axis=-1)
    return normalize(out)


def cam_to_rgb(nc):
    """Camera-space normals -> Godot 2D normal-map RGB (R screen right, G screen up, B toward viewer)."""
    return np.clip(np.round((np.asarray(nc) * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------------------------------------------------------- hashing and noise
def _hash_u32(*ints):
    h = np.zeros(np.broadcast(*ints).shape, dtype=np.uint64)
    mults = (374761393, 668265263, 982451653, 2246822519, 3266489917)
    for k, v in enumerate(ints):
        h = h + (np.asarray(v).astype(np.int64).astype(np.uint64) * np.uint64(mults[k % 5]))
    h = h & np.uint64(0xFFFFFFFF)
    h = ((h ^ (h >> np.uint64(13))) * np.uint64(1274126177)) & np.uint64(0xFFFFFFFF)
    h = h ^ (h >> np.uint64(16))
    return h.astype(np.uint32)


def hash01(*ints):
    """Deterministic hash of integer arrays -> [0, 1)."""
    return _hash_u32(*ints).astype(np.float64) / 4294967296.0


def vnoise2(x, y, seed=0):
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
                out = out + h * (u if dx else 1 - u) * (v if dy else 1 - v) * (w if dz else 1 - w)
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


def fbm3(x, y, z, octaves=3, seed=0, lac=2.03, gain=0.5):
    t = 0.0
    a = 0.5
    f = 1.0
    n = 0.0
    for i in range(octaves):
        t = t + a * vnoise3(np.asarray(x) * f, np.asarray(y) * f, np.asarray(z) * f, seed + i * 17)
        n += a
        a *= gain
        f *= lac
    return t / n


def worley2(x, y, seed=0, jitter=0.9):
    """Cellular noise: (F1, F2, cell id) on float arrays (cells of size 1)."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    xi = np.floor(x).astype(np.int64)
    yi = np.floor(y).astype(np.int64)
    f1 = np.full(x.shape, 9.0)
    f2 = np.full(x.shape, 9.0)
    cid = np.zeros(x.shape, np.int64)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            cx = xi + dx
            cy = yi + dy
            px = cx + 0.5 + (hash01(cx, cy, seed) - 0.5) * jitter
            py = cy + 0.5 + (hash01(cx, cy, seed + 7) - 0.5) * jitter
            d = np.hypot(x - px, y - py)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            cid = np.where(closer, cx * 73856093 ^ cy * 19349663, cid)
            f1 = np.where(closer, d, f1)
    return f1, f2, cid


class Rng:
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


# ---------------------------------------------------------------- colour
def srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, dtype=np.float64), 0.0, None)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def hex_rgb(h):
    h = h.lstrip('#')
    return np.array([int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)], np.float64)


def _rgb_to_lab(rgb255):
    from skimage.color import rgb2lab
    a = np.asarray(rgb255, np.float64).reshape(1, -1, 3) / 255.0
    return rgb2lab(a).reshape(-1, 3)


def _lab_to_rgb(lab):
    from skimage.color import lab2rgb
    a = np.asarray(lab, np.float64).reshape(1, -1, 3)
    return np.clip(lab2rgb(a).reshape(-1, 3) * 255.0, 0, 255)


def ramp(base, n=7, dark=0.42, light=0.30, hue_dark=None, hue_light=80.0, shift=0.22, chroma_ends=0.55):
    """A hue-shifted colour ramp, dark -> light, built in CIELAB/LCh around a base colour (sRGB hex
    or 0..255 triple) placed in the middle. Darks drift toward violet (warm bases: toward red-violet,
    so a brown never passes through green on its way into shadow; cool bases: toward blue), lights
    toward warm ochre (hue_light); chroma peaks at the base and falls at both ends (low saturation,
    P-2). dark/light: how far L* drops / rises at the ends, as a fraction of L* / (100 - L*)."""
    c = hex_rgb(base) if isinstance(base, str) else np.asarray(base, np.float64)
    L, A, B = _rgb_to_lab(c)[0]
    C = math.hypot(A, B)
    h = math.degrees(math.atan2(B, A)) % 360.0
    if hue_dark is None:
        hue_dark = 330.0 if 10.0 < h < 105.0 else 250.0
    out = []
    for i in range(n):
        t = i / (n - 1) - 0.5           # -0.5 .. 0.5
        if t < 0:
            k = -t * 2
            Li = L - L * dark * k
            target = hue_dark
        else:
            k = t * 2
            Li = L + (100 - L) * light * k
            target = hue_light
        d = ((target - h + 180.0) % 360.0) - 180.0
        hi = h + d * shift * k
        Ci = C * (1.0 - (1.0 - chroma_ends) * k)
        out.append([Li, Ci * math.cos(math.radians(hi)), Ci * math.sin(math.radians(hi))])
    return np.round(_lab_to_rgb(np.array(out))).astype(np.float64)


def lum(rgb):
    rgb = np.asarray(rgb, dtype=np.float64)
    return (rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114) / 255.0
