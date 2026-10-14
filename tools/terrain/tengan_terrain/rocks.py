"""Photoscan height maps -> pixel-art stone/plate atlases.

A CC0 photoscan's displacement map is used only as a *shape source*: it is
resampled to the project scale, segmented into individual plates/stones
(watershed), and every plate is then drawn flat with a top-left bevel and
dark gaps by our own ramps. No photo pixels reach the game.

Atlas arrays (all periodic, shape (h, w)):
  plate  int32  plate id (0 = gap/crevice)
  base   float  plate base value 0..1 (protrusion + facing)
  rim    int8   +2 top edge (lit lip), +1 left edge, -1 bottom/right edge, 0 inside, -2 gap
  nx,ny  float  per-pixel normal tilt in face coordinates (x right, y up)
  ledge  bool   top surface of a plate (where moss and grass can sit)
"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.segmentation import watershed, find_boundaries
from skimage.feature import peak_local_max


def load_height(path):
    a = np.asarray(Image.open(path)).astype(np.float64)
    if a.ndim == 3:
        a = a[..., 0]
    lo, hi = np.percentile(a, 0.5), np.percentile(a, 99.5)
    return np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)


def resample_wrap(a, out_h, out_w):
    """Periodic area-ish resample (Gaussian prefilter + cubic, wrapping)."""
    zy, zx = out_h / a.shape[0], out_w / a.shape[1]
    sig = (max(0.0, 0.5 / zy - 0.5), max(0.0, 0.5 / zx - 0.5))
    if sig[0] > 0 or sig[1] > 0:
        a = ndi.gaussian_filter(a, sigma=sig, mode='wrap')
    return ndi.zoom(a, (zy, zx), order=3, mode='grid-wrap')


def build_atlas(disp_path, tile_m, ppm=20, aspect=(1.0, 1.0), min_dist=3, smooth=1.0, gap_pct=8,
                strata=0.0, strata_px=11.0, crack=0.5, seed=0):
    """tile_m: how many metres of wall one tile of the scan should cover (larger
    than the scan's real size gives bigger, more readable plates).
    aspect=(sx, sy) stretches the scan (sx > sy gives wide, layered plates).
    strata: adds horizontal bedding (a sawtooth in height every strata_px px)
    so the segmentation produces layered plates with lit ledges.
    crack: 0..1, how much of the plate boundaries become dark cracks (the
    concave ones first); the rest stay as plate rims (lit top, dark under)."""
    h0 = load_height(disp_path)
    W1 = int(round(tile_m * ppm * aspect[0]))
    H1 = int(round(tile_m * ppm * aspect[1]))
    W2, H2 = W1 * 2, H1 * 2                       # segment at 2x for clean outlines
    h2 = resample_wrap(h0, H2, W2)
    if strata > 0:
        rng = np.random.default_rng(seed + 5)
        yy, xx = np.mgrid[0:H2, 0:W2].astype(np.float64)
        # bedding planes wobble and pinch along x; periodic in both axes
        wob = np.zeros_like(xx)
        for k in (1, 2, 3):
            ph = rng.uniform(0, 2 * np.pi)
            wob += np.sin(2 * np.pi * k * xx / W2 + ph) * (2.4 / k)
        per = strata_px * 2
        n_per = max(1, int(round(H2 / per)))
        per = H2 / n_per
        ph = (yy + wob * 2) / per
        saw = ph - np.floor(ph)                    # 0 at a bedding plane, rising downward
        h2 = h2 + strata * (saw - 0.5)
    hs = ndi.gaussian_filter(h2, smooth, mode='wrap')
    big = np.tile(hs, (3, 3))
    pk = peak_local_max(big, min_distance=min_dist * 2, threshold_rel=0.02, exclude_border=False)
    # periodic marker ids: copies of a peak in the 3x3 tiling share one id
    key = (pk[:, 0] % H2) * W2 + (pk[:, 1] % W2)
    uk, inv = np.unique(key, return_inverse=True)
    markers = np.zeros(big.shape, np.int32)
    markers[tuple(pk.T)] = inv + 1
    lab = watershed(-big, markers, mask=big > np.percentile(big, gap_pct))
    lab = lab[H2:2 * H2, W2:2 * W2]
    # boundary pixels between plates at 2x; concave ones (valleys) are cracks
    bnd = find_boundaries(np.tile(lab, (3, 3)), mode='inner', connectivity=1)[H2:2 * H2, W2:2 * W2]
    lap = ndi.laplace(ndi.gaussian_filter(h2, 1.0, mode='wrap'), mode='wrap')
    thr = np.percentile(lap[bnd], 100 * (1 - crack)) if bnd.any() else 0
    crackm = bnd & (lap >= thr)
    lab1 = lab[::2, ::2].copy()
    gap1 = (crackm[::2, ::2] & (crackm[1::2, 1::2] | crackm[::2, 1::2] | crackm[1::2, ::2])) | (lab1 == 0)
    h1 = hs[::2, ::2]
    lab1[gap1] = 0
    ids = np.unique(lab1[lab1 > 0])
    remap = np.zeros(lab1.max() + 1, np.int32)
    remap[ids] = np.arange(1, len(ids) + 1)
    plate = remap[lab1]
    n = int(plate.max())
    idx = np.arange(1, n + 1)
    mh = np.asarray(ndi.mean(h1, plate, idx)) if n else np.zeros(0)
    gy, gx = np.gradient(ndi.gaussian_filter(h1, 1.0, mode='wrap'))
    mgx = np.asarray(ndi.mean(gx, plate, idx)) if n else np.zeros(0)
    mgy = np.asarray(ndi.mean(gy, plate, idx)) if n else np.zeros(0)
    rng = np.random.default_rng(seed)
    jit = rng.uniform(-1, 1, n + 1)
    # facet lighting from the upper left: a surface tilted up (h rising downward) or
    # toward the left (h rising rightward) catches the light
    hz = (mh - mh.mean()) / (mh.std() + 1e-9) if n else mh
    sc = max(np.abs(mgy).max(), np.abs(mgx).max(), 1e-9) if n else 1
    face_up = np.clip(mgy / sc * 2.5, -1, 1) if n else mgy
    face_left = np.clip(mgx / sc * 2.5, -1, 1) if n else mgx
    base_p = np.clip(0.5 + 0.10 * hz + 0.26 * face_up + 0.12 * face_left, 0.04, 0.96)
    base = np.zeros(plate.shape, np.float32)
    ins = plate > 0
    base[ins] = base_p[plate[ins] - 1] + 0.05 * jit[plate[ins]]
    up = np.roll(plate, 1, 0)
    dn = np.roll(plate, -1, 0)
    lf = np.roll(plate, 1, 1)
    rt = np.roll(plate, -1, 1)
    rim = np.zeros(plate.shape, np.int8)
    rim[ins & (lf != plate)] = 1
    rim[ins & ((dn != plate) | (rt != plate))] = -1
    rim[ins & (up != plate)] = 2
    rim[~ins] = -2
    ledge = ins & (up != plate)
    nx = np.zeros(plate.shape, np.float32)
    ny = np.zeros(plate.shape, np.float32)
    if n:
        nx[ins] = -0.4 * face_left[plate[ins] - 1]
        ny[ins] = 0.4 * face_up[plate[ins] - 1]
    ny[rim == 2] += 0.55
    nx[rim == 1] -= 0.35
    ny[(rim == -1) & (dn != plate)] -= 0.5
    nx[(rim == -1) & (rt != plate)] += 0.3
    return {'plate': plate.astype(np.int32), 'base': base, 'rim': rim, 'nx': nx, 'ny': ny,
            'ledge': ledge, 'h': h1.astype(np.float32), 'n': int(n)}


def save_atlas(atlas, path):
    np.savez_compressed(path, **atlas)


def load_atlas(path):
    d = np.load(path)
    return {k: d[k] for k in d.files}
