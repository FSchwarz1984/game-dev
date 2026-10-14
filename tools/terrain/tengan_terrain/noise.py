"""Deterministic, vectorised noise and hashing (numpy only).

Everything here is a pure function of integer/float coordinate arrays and a
seed, so a bake is bit-for-bit reproducible. Coordinates are world pixels
(1 m = 20 px) unless a caller scales them.
"""
import numpy as np

_M1 = np.uint32(0x8DA6B343)
_M2 = np.uint32(0xD8163841)
_M3 = np.uint32(0xCB1AB31F)
_K1 = np.uint32(0x7FEB352D)
_K2 = np.uint32(0x846CA68B)


def _u32(a):
    return np.asarray(a).astype(np.int64).astype(np.uint32)


def hash2(ix, iy, seed=0):
    """32-bit integer hash of two integer arrays (wraps on purpose)."""
    with np.errstate(over='ignore'):
        h = _u32(ix) * _M1 ^ _u32(iy) * _M2 ^ np.uint32((seed * 0x9E3779B1 + 0x632BE5AB) & 0xFFFFFFFF) * _M3
        h ^= h >> np.uint32(16)
        h *= _K1
        h ^= h >> np.uint32(15)
        h *= _K2
        h ^= h >> np.uint32(16)
    return h


def hash01(ix, iy, seed=0):
    """Uniform [0, 1) float from two integer arrays."""
    return (hash2(ix, iy, seed) >> np.uint32(8)).astype(np.float32) * np.float32(1.0 / 16777216.0)


def _fade(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def vnoise(x, y, seed=0):
    """Value noise in [0, 1), quintic interpolation (smooth, no grid creases)."""
    x = np.asarray(x, np.float32)
    y = np.asarray(y, np.float32)
    ix = np.floor(x)
    iy = np.floor(y)
    fx = _fade(x - ix)
    fy = _fade(y - iy)
    ix = ix.astype(np.int64)
    iy = iy.astype(np.int64)
    a = hash01(ix, iy, seed)
    b = hash01(ix + 1, iy, seed)
    c = hash01(ix, iy + 1, seed)
    d = hash01(ix + 1, iy + 1, seed)
    ab = a + (b - a) * fx
    cd = c + (d - c) * fx
    return ab + (cd - ab) * fy


def fbm(x, y, seed=0, octaves=4, lacunarity=2.03, gain=0.5):
    """Fractal sum of value noise, normalised to roughly [0, 1)."""
    x = np.asarray(x, np.float32)
    y = np.asarray(y, np.float32)
    total = np.zeros(np.broadcast(x, y).shape, np.float32)
    amp, norm, f = 1.0, 0.0, 1.0
    for o in range(octaves):
        # rotate each octave a little so the lattice directions never line up
        ang = 0.6 * o
        ca, sa = np.cos(ang), np.sin(ang)
        xr = (x * ca - y * sa) * f + 17.3 * o
        yr = (x * sa + y * ca) * f - 9.1 * o
        total += amp * vnoise(xr, yr, seed + 101 * o)
        norm += amp
        amp *= gain
        f *= lacunarity
    return total / norm


def ridge(x, y, seed=0, octaves=3):
    """Ridged noise in [0, 1]: thin bright crests, for cracks and creases."""
    n = fbm(x, y, seed, octaves)
    return 1.0 - np.abs(n * 2.0 - 1.0)


def warp(x, y, scale, amount, seed=0, octaves=3):
    """Domain warp: returns displaced coordinates (organic, non-grid shapes)."""
    wx = fbm(x / scale, y / scale, seed + 7, octaves) - 0.5
    wy = fbm(x / scale + 31.7, y / scale - 12.9, seed + 13, octaves) - 0.5
    return x + wx * 2 * amount, y + wy * 2 * amount


BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16.0


def bayer(x, y):
    """Screen-/world-locked 4x4 ordered-dither threshold in (0, 1)."""
    return BAYER4[np.asarray(y, np.int64) & 3, np.asarray(x, np.int64) & 3]


def grid(h, w, x0=0, y0=0):
    """Pixel-centre coordinate arrays (float32) for an h x w raster."""
    ys, xs = np.mgrid[0:h, 0:w]
    return (xs + x0).astype(np.float32), (ys + y0).astype(np.float32)
