"""Ground heights from the renderer's terrain (read only), so a one-off hero asset can fit its roots
to the ground it is placed on (the great camphor stands at the 'camphor' marker of the saddle).
Falls back to flat ground when the terrain is not there. Rebuild the asset after the terrain
changes (python3 tools/world3d_assets/build.py --only camphor).
"""
from __future__ import annotations

import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SADDLE = os.path.join(REPO, 'godot', 'world3d', 'terrain', 'saddle')


def ground_fn(marker='camphor', terrain_dir=SADDLE):
    """g(x, z) -> ground height relative to the asset origin (object space, metres), and a note."""
    meta_p = os.path.join(terrain_dir, 'terrain.json')
    if not os.path.exists(meta_p):
        return (lambda x, z: np.zeros(np.broadcast(np.asarray(x), np.asarray(z)).shape)), 'flat (no terrain found)'
    from PIL import Image
    meta = json.load(open(meta_p))
    hm = meta['height']
    im = np.array(Image.open(os.path.join(terrain_dir, hm['file']))).astype(np.float64)
    H = (im[..., 0] * 256 + im[..., 1]) / 65535.0 * hm['range'] + hm['min']
    ox, oz = meta['origin']
    c = meta['cell']
    mk = meta['markers'][marker]
    x0, z0 = float(mk['x']), float(mk['z'])

    def raw(x, z):
        i = (np.asarray(x, np.float64) - ox) / c
        j = (np.asarray(z, np.float64) - oz) / c
        i0 = np.clip(np.floor(i).astype(int), 0, H.shape[1] - 2)
        j0 = np.clip(np.floor(j).astype(int), 0, H.shape[0] - 2)
        fi = np.clip(i - i0, 0, 1)
        fj = np.clip(j - j0, 0, 1)
        return (H[j0, i0] * (1 - fi) * (1 - fj) + H[j0, i0 + 1] * fi * (1 - fj)
                + H[j0 + 1, i0] * (1 - fi) * fj + H[j0 + 1, i0 + 1] * fi * fj)
    y0 = float(raw(x0, z0))

    def g(x, z):
        return raw(x0 + np.asarray(x, np.float64), z0 + np.asarray(z, np.float64)) - y0
    return g, f"saddle terrain at marker '{marker}' ({x0:.1f}, {z0:.1f}), origin height {y0:.3f}"
