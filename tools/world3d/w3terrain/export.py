"""Writes a terrain region for Godot (godot/world3d/terrain/<name>/) and previews (tools/world3d/out/).

Files (all PNGs imported with Godot's lossless "image" importer, read as Image at runtime):
  height.png   RGB8, R*256+G = u16 of (h - h_min) / h_range, 0.5 m cells (vertex grid)
  walk.png     L8, 255 walkable (slope <= 35 deg, not deep water), 0.5 m cells
  water.png    RGBA8, R*256+G = u16 water surface (0 = none), B = kind*64 (1 pool, 2 stream,
               3 paddy), A = flow angle (atan2(z, x) mapped to 0..255), 0.5 m cells
  m0..m3.png   RGBA8 material maps on the 0.25 m splat grid (see materials.py)
  terrain.json grid, encodings, markers (with heights), placements, road, paths, steps, pads,
               stream, spring, kiln, zones
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

IMPORT_IMAGE = '[remap]\n\nimporter="image"\ntype="Image"\n'


def _png(path: Path, arr, mode):
    Image.fromarray(arr, mode).save(path, optimize=True)
    imp = Path(str(path) + ".import")
    if not imp.exists():
        imp.write_text(IMPORT_IMAGE)


def _u8(a):
    return np.clip(np.round(np.asarray(a) * 255.0), 0, 255).astype(np.uint8)


def write(L, out: Path, tmp: Path, D):
    h = D["h"]
    h_min = float(np.floor(h.min())) - 2.0
    h_range = 128.0
    q = np.clip(np.round((h - h_min) / h_range * 65535.0), 0, 65535).astype(np.uint32)
    rgb = np.stack([(q >> 8).astype(np.uint8), (q & 255).astype(np.uint8), np.zeros_like(q, np.uint8)], -1)
    _png(out / "height.png", rgb, "RGB")
    _png(out / "walk.png", (D["walk"].astype(np.uint8) * 255), "L")
    wq = np.where(D["water_k"] > 0, np.clip(np.round((D["water_h"] - h_min) / h_range * 65535.0), 1, 65535), 0).astype(np.uint32)
    ang = (np.arctan2(D["flow"][..., 1], D["flow"][..., 0]) / (2 * np.pi)) % 1.0
    water = np.stack([(wq >> 8).astype(np.uint8), (wq & 255).astype(np.uint8), (D["water_k"].astype(np.uint8) * 64), _u8(ang)], -1)
    _png(out / "water.png", water, "RGBA")
    for k in ("m0", "m1", "m2", "m3"):
        _png(out / f"{k}.png", _u8(D["mats"][k]), "RGBA")

    x0, z0, cell = D["x0"], D["z0"], D["cell"]

    def hat(x, z):
        i = int(round((x - x0) / cell))
        j = int(round((z - z0) / cell))
        i = min(max(i, 0), D["nx"] - 1)
        j = min(max(j, 0), D["nz"] - 1)
        return round(float(h[j, i]), 3)

    markers = {k: {"x": v[0], "z": v[1], "y": hat(v[0], v[1])} for k, v in L["markers"].items()}
    RP, rprof = D["road"]
    info = {
        "format": "tengan-world3d-terrain/1",
        "name": L["name"],
        "note": L.get("note", ""),
        "origin": [x0, z0],
        "cell": cell,
        "size": [D["nx"], D["nz"]],
        "height": {"file": "height.png", "min": h_min, "range": h_range, "encoding": "R*256+G = u16"},
        "walk": "walk.png",
        "water": {"file": "water.png", "kinds": {"1": "pool", "2": "stream", "3": "paddy"}},
        "splat": {"cell": D["cs"], "size": [int(D["Hs"].shape[1]), int(D["Hs"].shape[0])], "files": ["m0.png", "m1.png", "m2.png", "m3.png"],
                  "channels": {"m0": ["grass", "dirt", "gravel", "rock"], "m1": ["moss", "litter", "bank", "paddy"],
                               "m2": ["ao", "puddle", "wear", "flowers"], "m3": ["litter_kind", "dryness", "tufts", "slope/90"]}},
        "markers": markers,
        "placements": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in p.items()} for p in D["placements"]],
        "road": {"points": [[round(float(a), 3), round(float(b), 3)] for a, b in RP[::4]], "heights": [round(float(v), 3) for v in rprof[::4]], "width": L["road"]["width"]},
        "paths": [{"id": P["id"], "width": P["width"], "points": [[round(float(a), 3), round(float(b), 3)] for a, b in pts]} for P, pts, d in D["paths"]],
        "steps": D["steps"],
        "pads": L["pads"],
        "stream": {"points": [[round(float(a), 3), round(float(b), 3)] for a, b in D["stream"][0]], "floor": [round(float(v), 3) for v in D["stream"][1]], "width": L["stream"]["width"]},
        "spring": {**L["spring"], "surface": round(float(D["pool_surf"]), 3)},
        "kiln": L["kiln"],
        "terraces": L["terraces"],
        "zones": L["zones"],
    }
    (out / "terrain.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))

    # ---- previews for checking (not shipped)
    gz, gx = np.gradient(h, cell)
    nrm = np.stack([-gx, np.ones_like(h), -gz], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    sun = np.array([-0.5, 0.75, -0.45])
    sun /= np.linalg.norm(sun)
    shade = np.clip(nrm @ sun, 0, 1)
    hs = (shade * 200 + 30).astype(np.uint8)
    Image.fromarray(hs, "L").save(tmp / "hillshade.png")
    cols = np.array([[96, 112, 62], [140, 118, 84], [150, 146, 136], [110, 112, 118], [58, 84, 46], [120, 92, 52], [128, 100, 70], [90, 140, 120]], np.float64)
    W = D["mats"]["W"]
    from .materials import ORDER
    img = sum(W[k][..., None] * cols[i] for i, k in enumerate(ORDER))
    from scipy import ndimage as ndi
    hsu = ndi.map_coordinates(shade, [(np.arange(img.shape[0])[:, None] * D["cs"]) / cell + 0 * np.arange(img.shape[1])[None, :], (np.arange(img.shape[1])[None, :] * D["cs"]) / cell + 0 * np.arange(img.shape[0])[:, None]], order=1)
    img = img * (0.45 + 0.75 * hsu[..., None])
    wk = ndi.map_coordinates(D["water_k"].astype(float), [(np.arange(img.shape[0])[:, None] * D["cs"]) / cell + 0 * np.arange(img.shape[1])[None, :], (np.arange(img.shape[1])[None, :] * D["cs"]) / cell + 0 * np.arange(img.shape[0])[:, None]], order=0)
    img = np.where(wk[..., None] > 0, np.array([70, 110, 140]), img)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB").save(tmp / "materials.png")
    return {"size": [D["nx"], D["nz"]], "h_min": h_min, "h_max": float(h.max()), "placements": len(D["placements"])}
