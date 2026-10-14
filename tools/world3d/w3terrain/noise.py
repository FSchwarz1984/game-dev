"""Seeded, vectorised value noise and fbm on numpy grids (deterministic)."""
from __future__ import annotations

import numpy as np


def _hash2(ix, iz, seed):
    h = (ix.astype(np.int64) * 374761393 + iz.astype(np.int64) * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF).astype(np.float64) / float(0xFFFFFF)


def value(x, z, seed=0):
    """Value noise in [0, 1] with smooth (quintic) interpolation; x, z arrays in lattice units."""
    x = np.asarray(x, np.float64)
    z = np.asarray(z, np.float64)
    ix = np.floor(x)
    iz = np.floor(z)
    fx = x - ix
    fz = z - iz
    ux = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
    uz = fz * fz * fz * (fz * (fz * 6 - 15) + 10)
    ix = ix.astype(np.int64)
    iz = iz.astype(np.int64)
    a = _hash2(ix, iz, seed)
    b = _hash2(ix + 1, iz, seed)
    c = _hash2(ix, iz + 1, seed)
    d = _hash2(ix + 1, iz + 1, seed)
    return (a + (b - a) * ux) + ((c + (d - c) * ux) - (a + (b - a) * ux)) * uz


def fbm(x, z, octaves=4, seed=0, lacunarity=2.03, gain=0.5):
    """Fractal sum of value noise, normalised to about [0, 1]."""
    tot = 0.0
    amp = 1.0
    norm = 0.0
    fx, fz = np.asarray(x, np.float64), np.asarray(z, np.float64)
    for o in range(octaves):
        tot = tot + value(fx, fz, seed + o * 101) * amp
        norm += amp
        amp *= gain
        fx = fx * lacunarity + 17.3
        fz = fz * lacunarity - 9.1
    return tot / norm


def ridged(x, z, octaves=4, seed=0):
    """Ridged fbm in [0, 1]: sharp crests (1) between soft hollows."""
    tot = 0.0
    amp = 1.0
    norm = 0.0
    fx, fz = np.asarray(x, np.float64), np.asarray(z, np.float64)
    for o in range(octaves):
        n = 1.0 - np.abs(value(fx, fz, seed + o * 57) * 2.0 - 1.0)
        tot = tot + n * n * amp
        norm += amp
        amp *= 0.5
        fx = fx * 2.07 + 5.1
        fz = fz * 2.07 - 3.3
    return tot / norm


def warp(x, z, scale, amount, seed=0):
    """Domain warp: returns displaced coordinates (organic, non-grid shapes)."""
    dx = (fbm(x / scale, z / scale, 3, seed) - 0.5) * 2.0 * amount
    dz = (fbm(x / scale + 31.7, z / scale - 12.9, 3, seed + 7) - 0.5) * 2.0 * amount
    return x + dx, z + dz
