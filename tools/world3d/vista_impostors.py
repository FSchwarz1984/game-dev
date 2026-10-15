#!/usr/bin/env python3
"""Pack the impostor bake (godot/render3d/dev/impostor_bake.gd) into the vista's atlases.

    python3 tools/world3d/vista_impostors.py <bake dir> [<bake dir> ...] <out dir> [--ppm=14.14,10,...]
        [--hero=name:ppm/ppm/...,...]

Every baked frame (20 px per metre, texel for pixel) is reduced to a chain of levels of detail in
steps of the square root of two (14.1, 10, 7.1, 5 ... px per metre), so the vista can draw every
tree texel for pixel at the level nearest its size on screen (at most 19 % off its true size).
The reduction keeps the pixel art: each target pixel takes 4 x 4 samples of the source; it is
covered when at least half of them are, and takes the colour of the covered sample nearest their
mean (an existing tone, not a blend); normals are averaged, AO averaged, the class by majority.
Hero frames (the great camphor, the hut, the shrine: seen big, from one place) are reduced to the
one scale they are seen at.

Writes <out>/impostors_a.png (RGB albedo sRGB, A: 0 empty, 128 wood, 255 foliage),
<out>/impostors_n.png (RGB normal * 0.5 + 0.5 in the bake camera's frame, A ambient occlusion) and
<out>/impostors.json (pages, frames: asset, angle, ppm, rect, pivot).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PAGE = 2048
LEVELS = [20.0 / math.sqrt(2.0) ** k for k in range(1, 10)]     # 14.1 .. 0.88 px per metre
IMPORT_IMAGE = '[remap]\n\nimporter="image"\ntype="Image"\n'


def load_frame(bake: Path, base: str):
    a = np.asarray(Image.open(bake / f"{base}_a.png").convert("RGBA")).astype(np.float64)
    n = np.asarray(Image.open(bake / f"{base}_n.png").convert("RGB")).astype(np.float64) / 255.0
    o = np.asarray(Image.open(bake / f"{base}_o.png").convert("RGB")).astype(np.float64) / 255.0
    cov = a[..., 3] > 127
    col = a[..., :3]
    nrm = n * 2.0 - 1.0
    ao = o[..., 0]
    cls = o[..., 1] > 0.5
    return cov, col, nrm, ao, cls


def reduce(cov, col, nrm, ao, cls, pivot, f):
    """The frame at scale f (< 1), its pivot on a whole pixel. Returns arrays and the new pivot."""
    h, w = cov.shape
    ys, xs = np.nonzero(cov)
    if len(xs) == 0:
        return None
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    px, py = pivot
    tpx = int(round(px * f))
    tpy = int(round(py * f))
    # target pixel range covering the source bounds (target x maps to source px + (x - tpx) / f)
    tx0 = int(math.floor((x0 - px) * f + tpx)) - 1
    tx1 = int(math.ceil((x1 - px) * f + tpx)) + 1
    ty0 = int(math.floor((y0 - py) * f + tpy)) - 1
    ty1 = int(math.ceil((y1 - py) * f + tpy)) + 1
    W, H = tx1 - tx0, ty1 - ty0
    S = 4
    sub = (np.arange(S) + 0.5) / S
    tx = np.arange(tx0, tx1)
    ty = np.arange(ty0, ty1)
    sx = px + ((tx[:, None] + sub[None, :]) - tpx) / f            # (W, S)
    sy = py + ((ty[:, None] + sub[None, :]) - tpy) / f            # (H, S)
    ix = np.clip(np.floor(sx).astype(int), 0, w - 1).reshape(-1)
    iy = np.clip(np.floor(sy).astype(int), 0, h - 1).reshape(-1)
    inb_x = ((sx >= 0) & (sx < w)).reshape(-1)
    inb_y = ((sy >= 0) & (sy < h)).reshape(-1)
    YY, XX = np.meshgrid(iy, ix, indexing="ij")                    # (H*S, W*S)
    inb = np.outer(inb_y, inb_x)
    c = cov[YY, XX] & inb
    def blocks(arr):
        sh = arr.shape[2:] if arr.ndim > 2 else ()
        return arr.reshape((H, S, W, S) + sh).swapaxes(1, 2).reshape((H, W, S * S) + sh)
    cb = blocks(c)
    colb = blocks(col[YY, XX])
    nrmb = blocks(nrm[YY, XX])
    aob = blocks(ao[YY, XX])
    clsb = blocks(cls[YY, XX])
    k = cb.sum(axis=2)
    covered = k >= (S * S) * 0.5
    kk = np.maximum(k, 1)[..., None]
    mean = (colb * cb[..., None]).sum(axis=2) / kk
    d = ((colb - mean[:, :, None, :]) ** 2).sum(axis=3)
    d = np.where(cb, d, np.inf)
    pick = np.argmin(d, axis=2)
    out_col = np.take_along_axis(colb, pick[:, :, None, None], axis=2)[:, :, 0, :]
    nm = (nrmb * cb[..., None]).sum(axis=2)
    nm /= np.maximum(np.linalg.norm(nm, axis=2, keepdims=True), 1e-6)
    out_ao = (aob * cb).sum(axis=2) / np.maximum(k, 1)
    out_cls = (clsb & cb).sum(axis=2) * 2 > k
    return covered, out_col, nm, out_ao, out_cls, (tpx - tx0, tpy - ty0)


def crop(covered, col, nm, ao, cls, pivot):
    ys, xs = np.nonzero(covered)
    if len(xs) == 0:
        return None
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    sl = (slice(y0, y1), slice(x0, x1))
    return covered[sl], col[sl], nm[sl], ao[sl], cls[sl], (pivot[0] - x0, pivot[1] - y0)


class Packer:
    """Shelves on pages of PAGE x PAGE, tallest first."""

    def __init__(self):
        self.pages = []

    def place(self, w, h):
        for pi, pg in enumerate(self.pages):
            for sh in pg["shelves"]:
                if h <= sh["h"] and sh["x"] + w + 1 <= PAGE:
                    x = sh["x"]
                    sh["x"] += w + 1
                    return pi, x, sh["y"]
            if pg["y"] + h + 1 <= PAGE:
                sh = {"y": pg["y"], "h": h, "x": w + 1}
                pg["shelves"].append(sh)
                pg["y"] += h + 1
                return pi, 0, sh["y"]
        self.pages.append({"shelves": [], "y": 0})
        return self.place(w, h)


def main():
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    bakes = [Path(p) for p in pos[:-1]]
    out = Path(pos[-1])
    opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    levels = [float(v) for v in opts["ppm"].split(",")] if "ppm" in opts else LEVELS
    hero = {}
    for h in opts.get("hero", "").split(","):
        if h:
            nm, p = h.split(":")
            hero[nm] = [float(v) for v in p.split("/")]
    items = []
    for bake in bakes:
        meta = json.loads((bake / "frames.json").read_text())
        for fr in meta["frames"]:
            cov, col, nrm, ao, cls = load_frame(bake, fr["file"])
            for ppm in hero.get(fr["asset"], levels):
                f = ppm / meta["ppm"]
                if abs(f - 1.0) < 1e-6:
                    r = (cov, col, nrm, ao, cls, (int(round(fr["pivot"][0])), int(round(fr["pivot"][1]))))
                else:
                    r = reduce(cov, col, nrm, ao, cls, fr["pivot"], f)
                if r is None:
                    continue
                r = crop(*r)
                if r is None:
                    continue
                items.append((fr, ppm, r))
    items.sort(key=lambda t: -t[2][0].shape[0])
    pk = Packer()
    placed = []
    for fr, ppm, r in items:
        h, w = r[0].shape
        pi, x, y = pk.place(w, h)
        placed.append((fr, ppm, r, pi, x, y))
    n_pages = len(pk.pages)
    A = np.zeros((n_pages, PAGE, PAGE, 4), np.uint8)
    N = np.zeros((n_pages, PAGE, PAGE, 4), np.uint8)
    frames = []
    for fr, ppm, (cv, col, nm, ao, cls, piv), pi, x, y in placed:
        h, w = cv.shape
        a = np.zeros((h, w, 4), np.uint8)
        a[..., :3] = np.clip(np.round(col), 0, 255).astype(np.uint8)
        a[..., 3] = np.where(cv, np.where(cls, 255, 128), 0).astype(np.uint8)
        nn = np.zeros((h, w, 4), np.uint8)
        nn[..., :3] = np.clip(np.round((nm * 0.5 + 0.5) * 255.0), 0, 255).astype(np.uint8)
        nn[..., 3] = np.clip(np.round(ao * 255.0), 0, 255).astype(np.uint8)
        A[pi, y:y + h, x:x + w] = a
        N[pi, y:y + h, x:x + w] = nn
        frames.append({"asset": fr["asset"], "index": fr["index"], "angle": fr["angle"], "elev": fr["elev"],
                       "ppm": round(ppm, 4), "page": pi, "rect": [x, y, w, h], "pivot": [int(piv[0]), int(piv[1])]})
    out.mkdir(parents=True, exist_ok=True)
    # a single page is the common case; several pages are stacked vertically in one image
    Image.fromarray(A.reshape(n_pages * PAGE, PAGE, 4), "RGBA").save(out / "impostors_a.png", optimize=True)
    Image.fromarray(N.reshape(n_pages * PAGE, PAGE, 4), "RGBA").save(out / "impostors_n.png", optimize=True)
    for nm in ("impostors_a.png", "impostors_n.png"):
        imp = out / (nm + ".import")
        if not imp.exists():
            imp.write_text(IMPORT_IMAGE)
    used = sum(pg["y"] for pg in pk.pages)
    (out / "impostors.json").write_text(json.dumps({"format": "tengan-impostors/1", "page": PAGE, "pages": n_pages,
                                                    "frames": frames}, separators=(",", ":")))
    print("frames %d, pages %d, shelf height used %d" % (len(frames), n_pages, used))


if __name__ == "__main__":
    main()
