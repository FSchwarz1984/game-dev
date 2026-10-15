"""v4 pixel dialogue portraits (docs/knowledge/13-pixel-portraits.md section 10).

    python3 -I tools/art/portraits4/build.py crops --packs DIR      # 1. cut the source crops (needs the 12 packs)
    python3 -I tools/art/portraits4/build.py build                  # 2. crops + edits -> assets/portraits/pixel
    python3 -I tools/art/portraits4/build.py build --auto DIR       #    also write the un-edited auto results to DIR
    python3 -I tools/art/portraits4/build.py check                  #    verify the PNGs against a fresh build

Dependencies: numpy, Pillow, opencv-python-headless, scipy (the same as v1's tools/art/pixel_portraits.py).

Inputs: the owner's packs (12 zips of 1024x1536 RGBA PNGs, A = Tsuzumi/Kasasagi, B = Shione, C = Saji, extracted as
DIR/Character_<L>_<nn-nn>/<L>_<nn>.png) are read once by `crops`, which keeps the source pixels around every window
in assets/portraits/src4/<char>/<source>.webp (lossy colour, lossless alpha) with their origin in crops.json; `build`
reads only those, so the portraits are reproducible from the repository.

Method:
 1. Window. Each expression has its own illustration (config.SELECTION, both eyes measured in source px). The eye
    midpoint lands at FRAME's position and every expression of a character has the same scale (REF_EYE_DIST ->
    FRAME eye distance), so changing expression never moves or resizes the head. Sampled at SUB x the native size,
    premultiplied, with a Gaussian prefilter.
 2. Flatten. L0 gradient minimisation (config.L0_LAMBDA; a quarter of it on the face) turns the soft painting into
    clean regions before pixelising.
 3. Pixelise. Contrast-aware downscale (oe.py, a port of PixelOE): dark strokes (lashes, mouth, outlines) survive
    as 1-px lines instead of averaging into the skin.
 4. Palette. Per character, PALETTE_K colours measured by k-means (Lab) over all her expressions (face pixels
    count three times), plus the colours named in the edit legends. Nearest colour in Lab, no dithering.
 5. Clean. Colour islands of <= CLEAN_MAX px merge into their most similar neighbour, except inside the eyes,
    mouth and the edit masks.
 6. Edits. tools/art/portraits4/edits/<char>/<expr>.txt: hand-placed pixels (legend keys -> colours) laid over
    the result: tears, brows, mouths, blush, highlights. '.' leaves a pixel as it is, '_' makes it transparent.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import config as C  # noqa: E402
import oe  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SRC4 = os.path.join(ROOT, 'assets', 'portraits', 'src4')
OUT = os.path.join(ROOT, 'assets', 'portraits', 'pixel')
EDITS = os.path.join(HERE, 'edits')


# ------------------------------------------------------------------------------------------------ geometry

def scale_of(char):
    """Source px per native px."""
    return C.REF_EYE_DIST[char] / C.FRAME[char][0]


def window(char, expr):
    """(x0, y0, side) of the native window in source px."""
    _, el, er, _, _, *opt = C.SELECTION[char][expr]
    opt = opt[0] if opt else {}
    s = scale_of(char)
    _, ex, ey = C.FRAME[char]
    mid = (np.asarray(el, float) + np.asarray(er, float)) / 2
    dx, dy = opt.get('shift', (0, 0))
    return mid[0] - (ex * C.SIZE - dx) * s, mid[1] - (ey * C.SIZE - dy) * s, C.SIZE * s


def to_native(char, expr, p):
    x0, y0, _ = window(char, expr)
    s = scale_of(char)
    return (p[0] - x0) / s, (p[1] - y0) / s


# ------------------------------------------------------------------------------------------------ crops

def pack_path(packs, name):
    letter, n = name[0], int(name[2:])
    rng = ['01-09', '10-18', '19-27', '28-36'][(n - 1) // 9]
    return os.path.join(packs, f'Character_{letter}_{rng}', f'{name}.png')


def cmd_crops(args):
    boxes = {}
    for char, exprs in C.SELECTION.items():
        for expr, row in exprs.items():
            x0, y0, side = window(char, expr)
            b = (int(np.floor(x0)) - C.CROP_MARGIN, int(np.floor(y0)) - C.CROP_MARGIN,
                 int(np.ceil(x0 + side)) + C.CROP_MARGIN, int(np.ceil(y0 + side)) + C.CROP_MARGIN)
            key = (char, row[0])
            o = boxes.get(key, b)
            boxes[key] = (min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3]))
    manifest = {}
    for (char, name), (bx0, by0, bx1, by1) in sorted(boxes.items()):
        im = Image.open(pack_path(args.packs, name)).convert('RGBA')
        crop = Image.new('RGBA', (bx1 - bx0, by1 - by0), (0, 0, 0, 0))
        crop.paste(im.crop((max(bx0, 0), max(by0, 0), min(bx1, im.width), min(by1, im.height))),
                   (max(0, -bx0), max(0, -by0)))
        os.makedirs(os.path.join(SRC4, char), exist_ok=True)
        crop.save(os.path.join(SRC4, char, f'{name}.webp'), 'WEBP', quality=95, alpha_quality=100, method=6)
        manifest[f'{char}/{name}'] = [bx0, by0]
        print('crop', char, name, crop.size)
    with open(os.path.join(SRC4, 'crops.json'), 'w') as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
        fh.write('\n')


# ------------------------------------------------------------------------------------------------ pixelising

def l0_smooth(img, lam, kappa=2.0, beta_max=1e5):
    """L0 gradient minimisation (Xu, Lu, Xu, Jia 2011), as in v1."""
    s = img.astype(np.float64).copy()
    h, w = s.shape[:2]

    def otf(psf):
        pad = np.zeros((h, w))
        pad[:psf.shape[0], :psf.shape[1]] = psf
        for ax, n in enumerate(psf.shape):
            pad = np.roll(pad, -(n // 2), axis=ax)
        return np.fft.fft2(pad)

    d2 = np.abs(otf(np.array([[1, -1]], float))) ** 2 + np.abs(otf(np.array([[1], [-1]], float))) ** 2
    n1 = np.fft.fft2(s, axes=(0, 1))
    beta = 2 * lam
    while beta < beta_max:
        gh = np.roll(s, -1, axis=1) - s
        gv = np.roll(s, -1, axis=0) - s
        t = (gh ** 2 + gv ** 2).sum(-1) < lam / beta
        gh[t] = 0
        gv[t] = 0
        n2 = (np.roll(gh, 1, axis=1) - gh) + (np.roll(gv, 1, axis=0) - gv)
        s = np.real(np.fft.ifft2((n1 + beta * np.fft.fft2(n2, axes=(0, 1))) / (1 + beta * d2)[..., None], axes=(0, 1)))
        beta *= kappa
    return np.clip(s, 0, 1).astype(np.float32)


def fill_transparent(c, a):
    m = a < 0.5
    if not m.any() or m.all():
        return c
    _, (iy, ix) = ndi.distance_transform_edt(m, return_indices=True)
    return c[iy, ix]


def lab(rgb):
    """float RGB 0..1 -> float Lab (L 0..100)."""
    return cv2.cvtColor(np.ascontiguousarray(rgb, np.float32).reshape(-1, 1, 3), cv2.COLOR_RGB2Lab).reshape(rgb.shape)


def hexrgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


_CROPS = None


def load_work(char, expr):
    """The window at SUB x native: (rgb 0..1, alpha 0..1)."""
    global _CROPS
    if _CROPS is None:
        with open(os.path.join(SRC4, 'crops.json')) as fh:
            _CROPS = json.load(fh)
    name = C.SELECTION[char][expr][0]
    ox, oy = _CROPS[f'{char}/{name}']
    rgba = np.asarray(Image.open(os.path.join(SRC4, char, f'{name}.webp')).convert('RGBA')).astype(np.float32) / 255
    a = np.clip((rgba[..., 3] - 0.03) / 0.93, 0, 1)            # the packs top out at alpha 253
    pm = np.dstack([rgba[..., :3] * a[..., None], a])
    x0, y0, _ = window(char, expr)
    sk = scale_of(char) / C.SUB
    sig = max(0.0, 0.5 * sk - 0.25)
    if sig > 0.2:
        pm = cv2.GaussianBlur(pm, (0, 0), sig)
    m = np.array([[sk, 0, x0 - ox], [0, sk, y0 - oy]], np.float32)
    n = C.SIZE * C.SUB
    w = cv2.warpAffine(pm, m, (n, n), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_CONSTANT,
                       borderValue=0)
    aa = np.clip(w[..., 3], 0, 1)
    c = np.where(aa[..., None] > 1e-3, w[..., :3] / np.maximum(aa[..., None], 1e-3), 0)
    return np.clip(c, 0, 1), aa


def face_mask(char, expr, n, grow=1.0):
    """Ellipse around the eyes, nose and mouth at resolution n x n (n = SIZE * k)."""
    _, el, er, mc, _, *_ = C.SELECTION[char][expr]
    k = n / C.SIZE
    e1 = np.array(to_native(char, expr, el)) * k
    e2 = np.array(to_native(char, expr, er)) * k
    m = np.array(to_native(char, expr, mc)) * k
    d = np.linalg.norm(e2 - e1)
    centre = (e1 + e2 + m) / 3
    ax = (e2 - e1) / d
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    u = ((xx - centre[0]) * ax[0] + (yy - centre[1]) * ax[1]) / (0.95 * d * grow)
    v = ((xx - centre[0]) * -ax[1] + (yy - centre[1]) * ax[0]) / (0.85 * d * grow)
    return u * u + v * v <= 1


def feature_mask(char, expr, n):
    """Eyes and mouth (where small islands are kept), at resolution n x n."""
    _, el, er, mc, state, *_ = C.SELECTION[char][expr]
    k = n / C.SIZE
    e1 = np.array(to_native(char, expr, el)) * k
    e2 = np.array(to_native(char, expr, er)) * k
    d = np.linalg.norm(e2 - e1)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    msk = np.zeros((n, n), bool)
    for c in (e1, e2):
        msk |= ((xx - c[0]) / (0.36 * d)) ** 2 + ((yy - c[1]) / (0.30 * d)) ** 2 <= 1
    if state != 'hidden':
        m = np.array(to_native(char, expr, mc)) * k
        msk |= ((xx - m[0]) / (0.26 * d)) ** 2 + ((yy - m[1]) / (0.16 * d)) ** 2 <= 1
    return msk


def pixelise(char, expr):
    """-> (native float RGB, native opaque mask, the work image before flattening)."""
    c, a = load_work(char, expr)
    n = C.SIZE * C.SUB
    cf = fill_transparent(c, a)
    card = np.array(C.CARD, np.float32) / 255
    comp = cf * a[..., None] + card * (1 - a[..., None])
    comp0 = comp
    if C.L0_LAMBDA > 0:
        strong = l0_smooth(comp, C.L0_LAMBDA)
        light = l0_smooth(comp, C.L0_LAMBDA / 4)
        f = cv2.GaussianBlur(face_mask(char, expr, n).astype(np.float32), (0, 0), 2 * C.SUB)[..., None]
        comp = strong * (1 - f) + light * f
    bgr = cv2.cvtColor((comp * 255).round().astype(np.uint8), cv2.COLOR_RGB2BGR)
    sm = oe.pixelize(bgr, C.SUB, C.OE_THICKNESS)
    rgb = cv2.cvtColor(sm, cv2.COLOR_BGR2RGB).astype(np.float32) / 255
    an = a.reshape(C.SIZE, C.SUB, C.SIZE, C.SUB).mean((1, 3))
    return rgb, an >= 0.5, comp0.astype(np.float32)


CACHE = os.environ.get('PORTRAITS4_CACHE')   # optional directory: pixelised results keyed by crop + settings


def cached_pixelise(char, expr):
    if not CACHE:
        return pixelise(char, expr)
    import hashlib
    name = C.SELECTION[char][expr][0]
    h = hashlib.sha1()
    h.update(open(os.path.join(SRC4, char, f'{name}.webp'), 'rb').read())
    h.update(repr((C.SIZE, C.SUB, C.CARD, C.REF_EYE_DIST[char], C.FRAME[char], C.SELECTION[char][expr],
                   C.L0_LAMBDA, C.OE_THICKNESS, open(os.path.join(HERE, 'oe.py'), 'rb').read())).encode())
    path = os.path.join(CACHE, f'{char}_{expr}_{h.hexdigest()[:16]}.npz')
    if os.path.exists(path):
        z = np.load(path)
        if 'work' in z:
            return z['rgb'], z['msk'], z['work']
    rgb, msk, work = pixelise(char, expr)
    os.makedirs(CACHE, exist_ok=True)
    np.savez_compressed(path, rgb=rgb, msk=msk, work=work.astype(np.float16))
    return rgb, msk, work


# ------------------------------------------------------------------------------------------------ palette

def measure_palette(char, results):
    """k-means (Lab) over all of a character's expressions; face pixels count three times."""
    px = []
    for expr, (rgb, msk, _) in results.items():
        L = lab(rgb)
        px.append(L[msk])
        fm = face_mask(char, expr, C.SIZE) & msk
        px += [L[fm]] * 2
    px = np.concatenate(px).astype(np.float32)
    cv2.setRNGSeed(7)
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.02)
    _, _, cent = cv2.kmeans(px, C.PALETTE_K, None, crit, 6, cv2.KMEANS_PP_CENTERS)
    rgb = np.clip(cv2.cvtColor(cent.reshape(-1, 1, 3), cv2.COLOR_Lab2RGB).reshape(-1, 3), 0, 1)
    rgb = (rgb * 255).round() / 255                     # exact 8-bit colours
    order = np.argsort(lab(rgb)[:, 0])                  # dark -> light, so the palette reads in order
    return rgb[order]


def quantise(rgb, pal):
    L = lab(rgb)
    P = lab(pal)
    return ((L[..., None, :] - P[None, None]) ** 2).sum(-1).argmin(-1)


def merge_small(idx, msk, pal, protect, limit):
    P = lab(pal)
    for _ in range(2):
        for v in np.unique(idx[msk]):
            comp, n = ndi.label((idx == v) & msk)
            if not n:
                continue
            sizes = ndi.sum(np.ones_like(comp), comp, range(1, n + 1))
            for ci in np.nonzero(sizes <= limit)[0]:
                m = comp == ci + 1
                if (m & protect).any():
                    continue
                ring = ndi.binary_dilation(m, np.ones((3, 3), bool)) & ~m & msk
                if not ring.any():
                    continue
                vals, cnts = np.unique(idx[ring], return_counts=True)
                d = ((P[vals] - P[v]) ** 2).sum(-1)
                idx[m] = vals[np.argmin(d - 2.0 * cnts)]
    return idx


# ------------------------------------------------------------------------------------------------ face features

def eye_regions(char, expr):
    """Native-px boolean masks of the two eye ellipses."""
    _, el, er, *_ = C.SELECTION[char][expr]
    e1, e2 = np.array(to_native(char, expr, el)), np.array(to_native(char, expr, er))
    d = np.linalg.norm(e2 - e1)
    yy, xx = np.mgrid[0:C.SIZE, 0:C.SIZE].astype(np.float32) + 0.5
    rx, ry = C.EYE_REGION
    return [((xx - e[0]) / (rx * d)) ** 2 + ((yy - e[1]) / (ry * d)) ** 2 <= 1 for e in (e1, e2)]


def snap_eyes(char, expr, img, work=None):
    """Inside the eyes, every colour snaps to the character's canonical eye colours (Lab nearest). With the work
    image, the illustration's catchlights come back: white blobs inside the iris (the downscale tends to drop them,
    and an eye without its glint looks dead)."""
    cols = np.array([hexrgb(h) for h in C.EYE_CANON[char]])
    P = lab(cols)
    reg = eye_regions(char, expr)
    m = (reg[0] | reg[1]) & (img[..., 3] > 0)
    L = lab(img[..., :3].astype(np.float32) / 255)
    k = ((L[m][:, None, :] - P[None]) ** 2).sum(-1).argmin(-1)
    img[m, :3] = (cols[k] * 255).round().astype(np.uint8)
    if work is None:
        return
    n = C.SIZE * C.SUB
    W = lab(work)
    wk = ((W[..., None, :] - P[None, None]) ** 2).sum(-1).argmin(-1)
    for r in reg:
        rw = cv2.resize(r.astype(np.uint8), (n, n), interpolation=cv2.INTER_NEAREST).astype(bool)
        iris = rw & np.isin(wk, (2, 3, 4))
        if iris.sum() < 40:
            continue
        hull = np.zeros((n, n), np.uint8)
        cv2.fillConvexPoly(hull, cv2.convexHull(np.argwhere(iris)[:, ::-1].astype(np.int32)), 1)
        hull = hull.astype(bool)
        white = hull & (W[..., 0] > 88) & (np.hypot(W[..., 1], W[..., 2]) < 12)
        dark = np.isin(wk, (0, 1, 2, 3, 4))                 # lash and iris classes
        comp, nc = ndi.label(white)
        for ci in range(1, nc + 1):
            cm = comp == ci
            if not 5 <= cm.sum() <= 160:                     # a glint, not a patch of sclera or skin
                continue
            ring = ndi.binary_dilation(cm, np.ones((3, 3), bool), iterations=2) & ~cm
            if dark[ring].mean() < 0.5:                      # a catchlight sits inside the dark iris
                continue
            cover = cm.reshape(C.SIZE, C.SUB, C.SIZE, C.SUB).mean((1, 3))
            pick = cover >= 0.30
            if not pick.any():
                yy, xx = np.argwhere(cm).mean(0) / C.SUB
                pick = np.zeros_like(pick)
                pick[int(yy), int(xx)] = True
            img[pick & (img[..., 3] > 0), :3] = 255


def _blackhat(lum, r=3):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    return cv2.morphologyEx(lum, cv2.MORPH_CLOSE, k) - lum


def _is_skin(L):
    a, b = L[..., 1], L[..., 2]
    return (L[..., 0] > 72) & (a > 2) & (a < 32) & (b > 4) & (b < 40)


def render_mouth(char, expr, img, work):
    """A closed (or slightly open) mouth: one continuous 1-px stroke along the illustration's mouth line, like
    v1; the old pixels inside the mouth area go back to the surrounding skin. Returns the drawn mask."""
    _, el, er, mc, state, *_ = C.SELECTION[char][expr]
    drawn = np.zeros(img.shape[:2], bool)
    if state not in ('closed', 'small'):
        return drawn
    n = C.SIZE * C.SUB
    e1, e2 = np.array(to_native(char, expr, el)), np.array(to_native(char, expr, er))
    d = np.linalg.norm(e2 - e1)
    m = np.array(to_native(char, expr, mc))
    bh = _blackhat(lab(work)[..., 0])
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) + 0.5
    mw = m * C.SUB
    reg = ((xx - mw[0]) / (0.36 * d * C.SUB)) ** 2 + ((yy - mw[1]) / (0.20 * d * C.SUB)) ** 2 <= 1
    core = ((xx - mw[0]) / (0.26 * d * C.SUB)) ** 2 + ((yy - mw[1]) / (0.12 * d * C.SUB)) ** 2 <= 1
    st = (bh > C.MOUTH_BH) & reg
    comp, k = ndi.label(st, structure=np.ones((3, 3)))
    keep = np.zeros_like(st)
    for ci in range(1, k + 1):
        cm = comp == ci
        if (cm & core).any() and cm.sum() >= 6:
            keep |= cm
    if not keep.any():
        return drawn
    w = np.where(keep, bh, 0.0)
    colmass = w.reshape(n, C.SIZE, C.SUB).sum((0, 2))
    ys = np.arange(n, dtype=np.float32)[:, None]
    coly = (w * ys).reshape(n, C.SIZE, C.SUB).sum((0, 2)) / np.maximum(colmass, 1e-6)
    strong = colmass >= 0.30 * colmass.max()
    cols = np.nonzero(strong)[0]
    cols = np.arange(cols.min(), cols.max() + 1)
    while len(cols) > C.MOUTH_MAX_W:
        cols = cols[1:] if colmass[cols[0]] < colmass[cols[-1]] else cols[:-1]
    for c in cols:
        if not strong[c]:
            lft = [q for q in cols if q < c and strong[q]]
            rgt = [q for q in cols if q > c and strong[q]]
            coly[c] = (coly[lft[-1]] + coly[rgt[0]]) / 2 if lft and rgt else coly[(lft or rgt)[-1 if lft else 0]]
    if len(cols) == 1:
        c0 = cols[0]
        nb = [c for c in (c0 - 1, c0 + 1) if 0 <= c < C.SIZE]
        cols = np.sort(np.append(cols, max(nb, key=lambda c: colmass[c])))
        coly[cols] = coly[c0]
    # clear the old mouth pixels: inside the mouth area, anything not skin takes the skin around it
    L = lab(img[..., :3].astype(np.float32) / 255)
    skin = _is_skin(L) & (img[..., 3] > 0)
    yn, xn = np.mgrid[0:C.SIZE, 0:C.SIZE].astype(np.float32) + 0.5
    area = ((xn - m[0]) / (0.34 * d)) ** 2 + ((yn - m[1]) / (0.18 * d)) ** 2 <= 1
    for y, x in zip(*np.nonzero(area & ~skin & (img[..., 3] > 0))):
        win = skin[max(0, y - 2):y + 3, max(0, x - 2):x + 3]
        if win.any():
            cand = img[max(0, y - 2):y + 3, max(0, x - 2):x + 3][win][:, :3]
            img[y, x, :3] = np.median(cand, 0).round().astype(np.uint8)
    line, soft = (hexrgb(h) for h in C.MOUTH[char])
    peak = colmass[cols].max()
    for i, c in enumerate(cols):
        y = int(coly[c] // C.SUB)
        end = i in (0, len(cols) - 1) and len(cols) > 2
        if 0 <= y < C.SIZE and img[y, c, 3]:
            img[y, c, :3] = ((soft if end and colmass[c] < 0.55 * peak else line) * 255).round().astype(np.uint8)
            drawn[y, c] = True
    if state == 'small':
        cx = int(round(cols.mean()))
        y = int(coly[cx] // C.SUB) + 1
        if 0 <= y < C.SIZE and img[y, cx, 3]:
            img[y, cx, :3] = (hexrgb(C.MOUTH_PINK[char]) * 255).round().astype(np.uint8)
            drawn[y, cx] = True
    return drawn


def render_open_mouth(char, expr, img):
    """An open mouth: the illustration paints it soft pink with a dark rim on one side only, which reads as a
    blob at 128 px. Find the mouth blob (pinker or darker than the skin around it), give it a full lip line and a
    darker cavity in its upper part; the lower part keeps its colour (tongue). Returns the drawn mask."""
    _, el, er, mc, state, *_ = C.SELECTION[char][expr]
    drawn = np.zeros(img.shape[:2], bool)
    if state != 'open':
        return drawn
    e1, e2 = np.array(to_native(char, expr, el)), np.array(to_native(char, expr, er))
    d = np.linalg.norm(e2 - e1)
    m = np.array(to_native(char, expr, mc))
    yy, xx = np.mgrid[0:C.SIZE, 0:C.SIZE].astype(np.float32) + 0.5
    reg = ((xx - m[0]) / (0.50 * d)) ** 2 + ((yy - m[1]) / (0.40 * d)) ** 2 <= 1
    L = lab(img[..., :3].astype(np.float32) / 255)
    opaque = img[..., 3] > 0
    ring = reg & ~(((xx - m[0]) / (0.36 * d)) ** 2 + ((yy - m[1]) / (0.28 * d)) ** 2 <= 1) & opaque
    skin = ring & _is_skin(L)
    if skin.sum() < 6:
        return drawn
    sL, sa = np.median(L[skin][:, 0]), np.median(L[skin][:, 1])
    blob = reg & opaque & ((L[..., 0] < sL - 7) | (L[..., 1] > sa + 7))
    comp, k = ndi.label(blob)
    if not k:
        return drawn
    sizes = ndi.sum(blob, comp, range(1, k + 1))
    blob = comp == (int(np.argmax(sizes)) + 1)
    if blob.sum() < 6:
        return drawn
    blob = ndi.binary_fill_holes(blob)
    edge = blob & ~ndi.binary_erosion(blob, np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool))
    inner = blob & ~edge
    line = (hexrgb(C.MOUTH[char][0]) * 255).round().astype(np.uint8)
    cav = (hexrgb(C.MOUTH_CAVITY[char]) * 255).round().astype(np.uint8)
    img[edge, :3] = line
    if inner.any():
        ys = np.nonzero(inner)[0]
        top, h = ys.min(), ys.max() - ys.min() + 1
        upper = inner & (yy - 0.5 < top + max(1, round(0.45 * h)))
        img[upper, :3] = cav
    drawn |= blob
    return drawn


# ------------------------------------------------------------------------------------------------ edits

def read_legend(path):
    leg = {}
    if os.path.exists(path):
        for line in open(path, encoding='utf-8'):
            line = line.split('#', 1)[0] if not line.lstrip().startswith('#') else ''
            parts = line.split()
            if len(parts) >= 2 and parts[1].startswith('$'):
                leg[parts[0]] = '#' + parts[1][1:]
    return leg


def read_symbols():
    """edits/_symbols.txt: blocks introduced by `= NAME`, rows of keys."""
    syms, cur = {}, None
    path = os.path.join(EDITS, '_symbols.txt')
    if not os.path.exists(path):
        return syms
    for raw in open(path, encoding='utf-8'):
        s = raw.strip()
        if not s or s.startswith('#'):
            continue
        if s.startswith('= '):
            cur = syms.setdefault(s[2:].strip(), [])
            continue
        if cur is not None:
            cur.append(s.split()[0])
    return syms


def read_edits(char, expr):
    """-> list of patches and the legend (key -> '#rrggbb'). Legend lines: `key $rrggbb  comment`.
    Patches: `@ X Y` followed by rows of keys; `use NAME X Y` stamps a block of edits/_symbols.txt;
    `recolor X Y W H #from #to` swaps one exact colour for another inside a box."""
    legend = read_legend(os.path.join(EDITS, char, '_legend.txt'))
    path = os.path.join(EDITS, char, f'{expr}.txt')
    patches = []
    if not os.path.exists(path):
        return patches, legend
    syms = None
    cur = None
    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        parts = s.split()
        if len(parts) >= 2 and parts[1].startswith('$') and len(parts[0]) == 1:
            legend[parts[0]] = '#' + parts[1][1:]
            continue
        if s.startswith('@'):
            _, x, y = s.split()[:3]
            cur = (int(x), int(y), [])
            patches.append(cur)
            continue
        if parts[0] == 'recolor':                      # recolor X Y W H #from #to (exact colour match)
            x, y, w, h = (int(v) for v in parts[1:5])
            patches.append(('recolor', (x, y, w, h), parts[5], parts[6]))
            cur = None
            continue
        if parts[0] == 'use':
            syms = read_symbols() if syms is None else syms
            if parts[1] not in syms:
                raise KeyError(f'{path}: no symbol {parts[1]!r} in _symbols.txt')
            patches.append((int(parts[2]), int(parts[3]), list(syms[parts[1]])))
            cur = None
            continue
        if cur is None:
            raise ValueError(f'{path}: pixel row before any @ line')
        cur[2].append(s.split()[0])
    return patches, legend


def apply_edits(img, char, expr):
    """img: uint8 RGBA (SIZE, SIZE, 4), modified in place. Returns the edited mask."""
    patches, legend = read_edits(char, expr)
    mask = np.zeros(img.shape[:2], bool)
    for patch in patches:
        if patch[0] == 'recolor':
            (x, y, w, h), src, dst = patch[1], patch[2], patch[3]
            a = (hexrgb(src) * 255).round().astype(np.uint8)
            b = (hexrgb(dst) * 255).round().astype(np.uint8)
            reg = img[y:y + h, x:x + w]
            hit = np.all(reg[..., :3] == a, -1) & (reg[..., 3] > 0)
            reg[hit, :3] = b
            mask[y:y + h, x:x + w] |= hit
            continue
        x0, y0, rows = patch
        for dy, row in enumerate(rows):
            for dx, k in enumerate(row):
                x, y = x0 + dx, y0 + dy
                if k == '.' or not (0 <= x < C.SIZE and 0 <= y < C.SIZE):
                    continue
                if k == '_':
                    img[y, x] = 0
                else:
                    if k not in legend:
                        raise KeyError(f'{char}/{expr}: key {k!r} not in the legend')
                    img[y, x, :3] = (hexrgb(legend[k]) * 255).round().astype(np.uint8)
                    img[y, x, 3] = 255
                mask[y, x] = True
    return mask


# ------------------------------------------------------------------------------------------------ build

def build_all(only=None):
    """-> {char: {expr: (auto RGBA, final RGBA)}}, palettes."""
    out, palettes = {}, {}
    for char, exprs in C.SELECTION.items():
        if only and not any(o.split('/')[0] == char for o in only):
            continue
        results = {e: cached_pixelise(char, e) for e in exprs}
        pal = measure_palette(char, results)
        palettes[char] = pal
        out[char] = {}
        for expr, (rgb, msk, work) in results.items():
            if only and f'{char}/{expr}' not in only:
                continue
            idx = quantise(rgb, pal)
            protect = feature_mask(char, expr, C.SIZE)
            idx = merge_small(idx, msk, pal, protect, C.CLEAN_MAX)
            auto = np.zeros((C.SIZE, C.SIZE, 4), np.uint8)
            auto[..., :3] = (pal[idx] * 255).round().astype(np.uint8)
            auto[..., 3] = msk * 255
            snap_eyes(char, expr, auto, work.astype(np.float32))
            render_mouth(char, expr, auto, work.astype(np.float32))
            render_open_mouth(char, expr, auto)
            final = auto.copy()
            apply_edits(final, char, expr)
            out[char][expr] = (auto, final)
    return out, palettes


def cmd_build(args):
    out_dir = args.out
    res, _ = build_all(args.only)
    manifest = {'size': C.SIZE, 'version': 4,
                'source': 'tools/art/portraits4 (each expression converted from its own illustration in the owner\'s '
                          'packs, then hand-edited faces)', 'characters': {}}
    for char, exprs in res.items():
        os.makedirs(os.path.join(out_dir, char), exist_ok=True)
        for expr, (auto, final) in exprs.items():
            Image.fromarray(final, 'RGBA').save(os.path.join(out_dir, char, f'{expr}.png'), optimize=True)
            if args.auto:
                os.makedirs(args.auto, exist_ok=True)
                Image.fromarray(auto, 'RGBA').save(os.path.join(args.auto, f'{char}_{expr}.png'))
        if not args.only:
            mids = {}
            for e in C.SELECTION[char]:
                _, el, er, *_ = C.SELECTION[char][e]
                a, b = to_native(char, e, el), to_native(char, e, er)
                mids[e] = [round((a[0] + b[0]) / 2, 1), round((a[1] + b[1]) / 2, 1)]
            manifest['characters'][char] = {
                'name': C.NAMES[char], 'expressions': list(C.SELECTION[char]),
                'sources': {e: v[0] for e, v in C.SELECTION[char].items()}, 'eye_mid': mids,
                'edited': sorted(e for e in C.SELECTION[char] if os.path.exists(os.path.join(EDITS, char, f'{e}.txt')))}
        print('built', char, len(exprs))
    if not args.only:
        with open(os.path.join(out_dir, 'portraits.json'), 'w', encoding='utf-8') as fh:
            json.dump(manifest, fh, indent=1, ensure_ascii=False)
            fh.write('\n')


def cmd_check(args):
    OUTD = args.out
    res, _ = build_all()
    bad = 0
    for char, exprs in res.items():
        for expr, (_, final) in exprs.items():
            p = os.path.join(OUTD, char, f'{expr}.png')
            cur = np.asarray(Image.open(p).convert('RGBA')) if os.path.exists(p) else None
            a = final[..., 3]
            ok = cur is not None and np.array_equal(cur, final) and set(np.unique(a)) <= {0, 255}
            if not ok:
                bad += 1
                print('MISMATCH', char, expr)
    print('check:', 'OK' if not bad else f'{bad} differ')
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('crops')
    a.add_argument('--packs', required=True)
    b = sub.add_parser('build')
    b.add_argument('--only', nargs='*')
    b.add_argument('--auto', help='also write the un-edited results here')
    b.add_argument('--out', default=OUT, help='output directory (default assets/portraits/pixel)')
    c = sub.add_parser('check')
    c.add_argument('--out', default=OUT)
    args = ap.parse_args()
    return {'crops': cmd_crops, 'build': cmd_build, 'check': cmd_check}[args.cmd](args)


if __name__ == '__main__':
    sys.exit(main())
