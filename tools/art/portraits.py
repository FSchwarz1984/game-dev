"""Dialogue portraits: background-removed cut-outs of the three reference illustrations.

    python3 tools/art/portraits.py [--debug DIR]

Input:  assets/reference/illustrations/{tsuzumi,saji,shione}.png (1024x1536, paper background)
Output: assets/portraits/<name>_full.webp   the whole figure on the original 1024x1536 canvas
        assets/portraits/<name>_bust.webp   512x640 bust; the eye midpoint sits at (256, 280) in
                                            every bust, at the illustration's own scale (the three
                                            faces are drawn at the same size), so all three line up.
Only the neutral expression exists; nothing is repainted.

Method (deterministic, numpy only):
1. Paper colour = median of a border band. The paper and the soft drop shadow are low-saturation
   and light; the ink outline around every figure is dark.
2. Flood fill from the image border through "paper-like" pixels; anything the fill cannot reach
   is figure (the white clothing is enclosed by ink lines, so it is never reached).
3. Edge matting: along the boundary, a pixel is a mix of ink/figure and paper. Its alpha comes from
   how far it is from the paper colour relative to the darkest nearby figure colour, and its colour
   is un-mixed ((c - (1 - a) * paper) / a), so no light halo is left on any background.
4. Small specks of paper trapped inside the silhouette (between hair strands) that are not
   enclosed by ink are removed by a second fill from those pockets when they are clearly paper.
"""

from __future__ import annotations

import argparse
import os
from collections import deque

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
SRC = os.path.join(ROOT, 'assets', 'reference', 'illustrations')
OUT = os.path.join(ROOT, 'assets', 'portraits')

# Eye midpoints measured on the illustrations (pixels), used to frame the busts identically.
EYES = {'tsuzumi': (515, 252), 'saji': (526, 192), 'shione': (548, 175)}
# Paper visible through closed shapes (checked by eye on the debug masks): (x, y) seed points.
POCKETS = {
    'tsuzumi': [(660, 300), (183, 660), (313, 341), (208, 494), (226, 784), (163, 735), (714, 716), (231, 479)],
    'saji': [(408, 504), (599, 283), (337, 117)],
    'shione': [(118, 611)],
}
BUST = (512, 640)
BUST_EYE = (256, 280)


def flood(passable: np.ndarray, seeds: np.ndarray) -> np.ndarray:
    h, w = passable.shape
    out = np.zeros_like(passable)
    q = deque()
    for y, x in zip(*np.nonzero(seeds & passable)):
        out[y, x] = True
        q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and passable[ny, nx] and not out[ny, nx]:
                out[ny, nx] = True
                q.append((ny, nx))
    return out


def dilate(m: np.ndarray, r: int = 1) -> np.ndarray:
    out = m.copy()
    for _ in range(r):
        o = out.copy()
        o[1:] |= out[:-1]; o[:-1] |= out[1:]; o[:, 1:] |= out[:, :-1]; o[:, :-1] |= out[:, 1:]
        out = o
    return out


def local_std(lum: np.ndarray, r: int = 1) -> np.ndarray:
    """Standard deviation over a (2r+1)^2 window (edge-padded)."""
    p = np.pad(lum, r, mode='edge')
    h, w = lum.shape
    acc = np.zeros_like(lum)
    acc2 = np.zeros_like(lum)
    n = 0
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            v = p[r + dy:r + dy + h, r + dx:r + dx + w]
            acc += v
            acc2 += v * v
            n += 1
    m = acc / n
    return np.sqrt(np.maximum(acc2 / n - m * m, 0))


def components(mask: np.ndarray):
    """Connected components (4-neighbour) of a boolean mask: yields index arrays."""
    seen = np.zeros_like(mask)
    h, w = mask.shape
    for y0, x0 in zip(*np.nonzero(mask)):
        if seen[y0, x0]:
            continue
        pts = []
        q = deque([(y0, x0)])
        seen[y0, x0] = True
        while q:
            y, x = q.popleft()
            pts.append((y, x))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    q.append((ny, nx))
        yield pts


def cutout(rgb: np.ndarray, pockets=(), report=None):
    a = rgb.astype(np.float32)
    h, w, _ = a.shape
    band = np.concatenate([a[:12].reshape(-1, 3), a[-12:].reshape(-1, 3), a[:, :12].reshape(-1, 3), a[:, -12:].reshape(-1, 3)])
    paper = np.median(band, axis=0)
    lum = a @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    plum = float(paper @ np.array([0.2126, 0.7152, 0.0722], np.float32))
    sat = a.max(2) - a.min(2)
    dist = np.sqrt(((a - paper) ** 2).sum(2))
    warm = (a[..., 2] - a[..., 0]) - (paper[2] - paper[0])       # < 0: warmer than the paper
    std = local_std(lum, 1)
    # Paper is flat and slightly cool; white cloth is textured and warmer.
    paper_px = (dist < 12) & (sat < 15) & (std < 4.5) & (warm > -5)
    # The soft grey drop shadow under the feet: unsaturated, smooth, near the bottom.
    rows = np.arange(h)[:, None]
    shadow_px = (rows > int(h * 0.9)) & (sat < 27) & (lum > plum - 60) & (std < 12) & (warm > -17)
    passable = paper_px | shadow_px
    # close one-pixel gaps in ink lines: a passable pixel next to two opposite non-passable ones is a wall
    wall = ~passable
    gap = (wall[:-2, 1:-1] & wall[2:, 1:-1]) | (wall[1:-1, :-2] & wall[1:-1, 2:])
    passable2 = passable.copy()
    passable2[1:-1, 1:-1] &= ~gap
    seeds = np.zeros((h, w), bool)
    seeds[0, :] = seeds[-1, :] = seeds[:, 0] = seeds[:, -1] = True
    bg = flood(passable2, seeds)
    # enclosed pockets of real paper (between an arm and the head, inside a hair curl): filled
    # only from seed points listed per illustration (a generic rule also ate flat white cloth)
    pocket_seeds = np.zeros((h, w), bool)
    for x, y in pockets:
        pocket_seeds[y, x] = True
    bg |= flood(passable2, pocket_seeds)
    if report is not None:
        for pts in components(passable2 & ~bg):
            if len(pts) >= 150:
                ys, xs = zip(*pts)
                report.append((len(pts), int(np.mean(xs)), int(np.mean(ys)), round(float(dist[ys, xs].mean()), 1), round(float(std[ys, xs].mean()), 1)))
    # let the background reach the ink: grow by up to 2 px through any light, unsaturated pixel
    near = (lum > plum - 40) & (sat < 22)
    for _ in range(2):
        bg = bg | (dilate(bg, 1) & near)
    fg = ~bg
    # keep only the main figure (drop tiny specks)
    ys, xs = np.nonzero(fg)
    seed = np.zeros_like(fg)
    seed[int(np.median(ys)), int(np.median(xs))] = True
    main = flood(fg, seed)
    if main.sum() > 0.5 * fg.sum():
        fg = main
    # edge matting on a 2-px band each side of the boundary
    edge = dilate(fg, 2) & dilate(~fg, 2)
    est = np.clip(dist / 150.0, 0.0, 1.0)
    alpha = fg.astype(np.float32)
    alpha = np.where(edge, np.where(fg, np.maximum(est, 0.4), np.where(dist > 16, est, 0.0)), alpha)
    am = alpha[..., None]
    col = np.where(am > 0.02, (a - (1 - am) * paper) / np.maximum(am, 1e-3), 0)
    col = np.clip(col, 0, 255)
    out = np.dstack([col, alpha * 255]).round().astype(np.uint8)
    out[alpha < 0.02] = 0
    return out, bg


def save_webp(arr, path):
    Image.fromarray(arr, 'RGBA').save(path, 'WEBP', quality=92, method=6, alpha_quality=100, exact=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--debug', default=None)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    for name in ('tsuzumi', 'saji', 'shione'):
        rgb = np.asarray(Image.open(os.path.join(SRC, f'{name}.png')).convert('RGB'))
        report = [] if args.debug else None
        rgba, bg = cutout(rgb, POCKETS[name], report)
        if report:
            print('  unreached paper-like regions (size, x, y, dist, std):', sorted(report, reverse=True)[:12])
        save_webp(rgba, os.path.join(OUT, f'{name}_full.webp'))
        ex, ey = EYES[name]
        x0, y0 = ex - BUST_EYE[0], ey - BUST_EYE[1]
        bust = np.zeros((BUST[1], BUST[0], 4), np.uint8)
        sx0, sy0 = max(0, x0), max(0, y0)
        sx1, sy1 = min(rgba.shape[1], x0 + BUST[0]), min(rgba.shape[0], y0 + BUST[1])
        bust[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = rgba[sy0:sy1, sx0:sx1]
        save_webp(bust, os.path.join(OUT, f'{name}_bust.webp'))
        print(f'{name}: full {rgba.shape[1]}x{rgba.shape[0]}, bust {BUST[0]}x{BUST[1]} (window {x0},{y0})')
        if args.debug:
            os.makedirs(args.debug, exist_ok=True)
            dbg = rgb.copy()
            dbg[bg] = (dbg[bg] * 0.4 + np.array([255, 0, 255]) * 0.6).astype(np.uint8)
            Image.fromarray(dbg).save(os.path.join(args.debug, f'{name}_mask.png'))
            for bgc, tag in (((20, 24, 32), 'dark'), ((255, 255, 255), 'white'), ((90, 140, 80), 'green')):
                base = Image.new('RGBA', (rgba.shape[1], rgba.shape[0]), bgc + (255,))
                base.alpha_composite(Image.fromarray(rgba, 'RGBA'))
                base.convert('RGB').save(os.path.join(args.debug, f'{name}_on_{tag}.png'))


if __name__ == '__main__':
    main()
