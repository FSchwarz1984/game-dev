"""Leaf tile atlases and the foliage material for the renderer's toon_foliage shader."""
from __future__ import annotations

import math

import numpy as np

from . import leaves as LV


def build_tiles(specs, width=128):
    """specs: dict set_name -> list of (fn, kwargs) where fn is a tile painter (leaves.clumps,
    leaves.spray or any function returning (h, w, 4) uint8). Returns (atlas, rects, sets) with
    sets[name] = list of (tile index, w, h)."""
    tiles = []
    sets = {}
    for name, lst in specs.items():
        sets[name] = []
        for fn, kw in lst:
            t = LV.trim(fn(**kw))
            sets[name].append((len(tiles), t.shape[1], t.shape[0]))
            tiles.append(t)
    atlas, rects = LV.pack_tiles(tiles, width=width)
    return atlas, rects, sets


def srgb_to_lab(c):
    """sRGB 0..1 (..., 3) -> CIELAB (D65)."""
    c = np.asarray(c, np.float64)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def lch(c):
    lab = srgb_to_lab(c)
    C = np.hypot(lab[..., 1], lab[..., 2])
    h = (np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) + 360) % 360
    return np.stack([lab[..., 0], C, h], axis=-1)


def foliage_params(wind_px=1.0, porosity=0.5, hi_band=1.0, cutaway=True):
    return {'foliage_mode': 1, 'wind_px': wind_px, 'porosity': porosity, 'hi_band': hi_band, 'cutaway': cutaway}
