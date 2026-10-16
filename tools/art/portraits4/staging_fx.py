"""The pictures of the dialogue staging (docs/design/dialogue-staging.md, G5R3-13, G5R3-19) for the v4 portraits.

    python3 -I tools/art/portraits4/staging_fx.py                 # -> assets/portraits/pixel/staging/
    python3 -I tools/art/portraits4/staging_fx.py --sheet FILE    #    also a review sheet (every face, x2)
    python3 -I tools/godot/sync_assets.py --portraits-only        # then copy them into godot/art/portraits

Two kinds of pieces, packed into atlases (whole native pixels, RGBA, no dithering added):

  marks.png    the generic manga marks (漫符) from staging_marks.txt (anger, sweat, surprise lines, question, sparkle,
               sigh, note, dots), hung on a per-character anchor at run time; and the card's dot screen (tone, 网点),
               three 128 x 128 frames shared by every face.
  <char>.png   the pieces that have to fit one face (its eyes are measured in config.SELECTION), for every expression
               in portraits.json:
                 gloom  (縦线)  a band over the upper face, hairline to the upper eyelids, a step darker (indigo, its
                                edges dithered), with vertical lines 2-3 px apart, ragged, longest in the middle; a line
                                pixel is dark indigo over light pixels and light lavender over dark ones, so it reads
                                on black, red and silver hair; 4 frames (the lines grow down, the tone deepens)
                 blush  (红晕线) deep-pink 2-px strokes, three on the near cheek and two on the far one; 3 frames
                 focus  (集中线) lines from the card's edges toward the face, stopping outside an oval round it (the
                                face stays clear); 3 frames (short, full, another set: the flicker of manga lines)
staging.json lists every frame: marks as [x, y, w, h] in marks.png (drawn with their top-left on the anchor), per-face
pieces as [x, y, w, h, ox, oy] in <char>.png with (ox, oy) the frame's top-left in the portrait's own pixels; an
empty frame is [0, 0, 0, 0, 0, 0]. Deterministic: the same inputs give the same bytes.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build as B  # noqa: E402
import config as C  # noqa: E402

ROOT = B.ROOT
ART = os.path.join(ROOT, 'assets', 'portraits', 'pixel')
OUT = os.path.join(ART, 'staging')
MARKS_SRC = os.path.join(HERE, 'staging_marks.txt')
CARD_BG = (78, 70, 86, 255)          # DialogueBox.CARD_BG

TONE = np.array([26, 20, 48])         # the gloom's dark tone (indigo)
LINE_ON_DARK = np.array([176, 168, 230], np.float32)
LINE_ON_LIGHT = np.array([44, 34, 84], np.float32)
BLUSH = np.array([201, 64, 90])       # deeper than the blush drawn into v4
BLUSH_HI = np.array([233, 118, 131])
FOCUS = np.array([240, 234, 246])
DOT = np.array([43, 36, 51])


# ------------------------------------------------------------------------------------------------ marks

def parse_marks(path):
    legend, frames, cur = {}, {}, None
    for raw in open(path, encoding='utf-8'):
        t = raw.strip()
        if not t or t.startswith('#'):
            continue
        m = re.match(r'^(\S) \$([0-9a-fA-F]{6})', t)
        if m and cur is None:
            legend[m.group(1)] = tuple(int(m.group(2)[i:i + 2], 16) for i in (0, 2, 4))
            continue
        if t.startswith('= '):
            name, fr = t[2:].split()
            cur = frames.setdefault(name, {}).setdefault(int(fr), [])
            continue
        cur.append(t.split()[0])
    out = {}
    for name, fr in frames.items():
        out[name] = []
        for i in sorted(fr):
            rows = fr[i]
            a = np.zeros((len(rows), max(len(r) for r in rows), 4), np.uint8)
            for y, r in enumerate(rows):
                for x, k in enumerate(r):
                    if k != '.':
                        a[y, x, :3] = legend[k]
                        a[y, x, 3] = 255
            out[name].append(a)
    return out


def tone_frames():
    """The card's background as a dark dot screen, denser at the top: sparse, medium, full."""
    frames = []
    for k in range(3):
        a = np.zeros((128, 128, 4), np.uint8)
        for y in range(128):
            density = (1.0 - y / 160.0) * (k + 1) / 3.0
            for x in range(128):
                cy = y % 4
                shift = (y // 4) % 2 * 2
                on = ((x + shift) % 4 < 2) and cy < 2
                if (on and density > 0.66) or (on and density > 0.33 and (x + shift) % 4 == 0 and cy == 0) or \
                        (density > 0.15 and (x + shift) % 4 == 0 and cy == 0 and (y // 4 + x // 4) % 2 == 0):
                    a[y, x, :3], a[y, x, 3] = DOT, 255
        frames.append(a)
    return frames


# ------------------------------------------------------------------------------------------------ per face

def eyes(char, expr):
    _, el, er, *_ = C.SELECTION[char][expr]
    return np.array(B.to_native(char, expr, el)), np.array(B.to_native(char, expr, er))


def gloom(char, expr):
    """縦线, drawn on the portrait itself (it is static, so the overlay knows what lies under every pixel)."""
    por = np.asarray(Image.open(os.path.join(ART, char, expr + '.png')).convert('RGBA')).astype(np.float32)
    e1, e2 = eyes(char, expr)
    d = float(np.linalg.norm(e2 - e1))
    mid = (e1 + e2) / 2
    slope = (e2[1] - e1[1]) / (e2[0] - e1[0])
    xl, xr = int(round(mid[0] - 0.82 * d)), int(round(mid[0] + 0.78 * d))

    def lid(x):                                                  # about the upper eyelids, following the tilt
        return e1[1] + slope * (x - e1[0]) - 0.12 * d

    opaque = por[..., 3] > 0
    lum = por[..., :3] @ np.array([0.299, 0.587, 0.114], np.float32)
    rng = random.Random(sum(map(ord, char + expr)))
    top = {x: lid(x) - 0.92 * d - rng.uniform(0, 4) for x in range(xl, xr + 1)}
    cols, x = [], xl + rng.choice([0, 1])
    while x <= xr:
        cols.append(x)
        x += rng.choice([2, 3, 3])
    tail = {x: rng.uniform(0.0, 0.22) for x in cols}
    frames = []
    for k in range(4):
        grow = (k + 1) / 4.0
        out = np.zeros((128, 128, 4), np.uint8)
        for x in range(max(0, xl), min(127, xr) + 1):
            u = (x - mid[0]) / (0.8 * d)
            side = max(0.0, 1.0 - abs(u) ** 3)
            t0, t1 = top[x], lid(x)
            for y in range(max(0, int(t0)), min(127, int(t1)) + 1):
                if not opaque[y, x]:
                    continue
                f = (y - t0) / max(1.0, t1 - t0)
                strength = (0.55 - 0.35 * f) * side * grow
                if (f > 0.75 or side < 0.45) and (x + y) % 2:    # soft edges as a dither, not a gradient
                    continue
                if strength < 0.04:
                    continue
                out[y, x, :3] = np.clip(por[y, x, :3] * (1 - strength) + TONE * strength, 0, 255).astype(np.uint8)
                out[y, x, 3] = 255
        for x in cols:
            if not (0 <= x < 128):
                continue
            u = (x - mid[0]) / (0.8 * d)
            t0, t1 = top[x] + 1, lid(x)
            reach = max(0.0, 1.0 - 0.5 * u * u - tail[x])
            end = t0 + (t1 - t0) * reach * grow
            for y in range(max(0, int(t0)), min(127, int(end)) + 1):
                if not opaque[y, x]:
                    continue
                base = out[y, x, :3].astype(np.float32) if out[y, x, 3] else por[y, x, :3]
                c = LINE_ON_DARK if lum[y, x] < 70 else LINE_ON_LIGHT
                if y >= int(end) - 1:                            # the ragged tip, half a step weaker
                    c = (c + base) / 2
                out[y, x, :3] = c.astype(np.uint8)
                out[y, x, 3] = 255
        frames.append(out)
    return frames, (0, 0)


def blush(char, expr):
    e1, e2 = eyes(char, expr)
    d = float(np.linalg.norm(e2 - e1))
    near = e1 + np.array([-0.30 * d, 0.40 * d])
    far = e2 + np.array([-0.05 * d, 0.36 * d])
    W, H = int(d * 1.6) + 8, int(d * 0.8) + 8
    org = np.floor(np.minimum(near, far) - 2).astype(int)
    strokes = [(near, 0), (near, 1), (near, 2), (far, 0), (far, 1)]
    order = [[0, 3], [0, 1, 3, 4], [0, 1, 2, 3, 4]]
    frames = []
    for k in range(3):
        a = np.zeros((H, W, 4), np.uint8)
        for si in order[k]:
            base, i = strokes[si]
            n = 5 if base is near else 4             # the far cheek is narrower
            sx = int(base[0] - org[0]) + i * 4
            sy = int(base[1] - org[1])
            for t in range(n):                       # a 2-px stroke from upper right to lower left
                for dx, col in ((0, BLUSH), (1, BLUSH_HI if t == 0 else BLUSH)):
                    x, y = sx + (n - 1 - t) + dx, sy + t
                    if 0 <= x < W and 0 <= y < H:
                        a[y, x, :3] = col
                        a[y, x, 3] = 255
        frames.append(a)
    return frames, (int(org[0]), int(org[1]))


def line_px(x0, y0, x1, y1):
    x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        yield x0, y0
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def focus(char, expr):
    e1, e2 = eyes(char, expr)
    d = float(np.linalg.norm(e2 - e1))
    c = (e1 + e2) / 2 + np.array([0.0, 0.30 * d])
    rx, ry = 1.25 * d, 1.45 * d                      # the clear oval round the face
    frames = []
    for n, seed, reach in ((30, 5, 0.45), (30, 5, 1.0), (30, 11, 1.0)):
        rng = random.Random(seed)
        a = np.zeros((128, 128, 4), np.uint8)
        for i in range(n):
            ang = 2 * math.pi * (i + rng.uniform(-0.35, 0.35)) / n
            dx, dy = math.cos(ang), math.sin(ang)
            ts = [t for t in ((127.5 - c[0]) / dx if dx > 1e-6 else None, (-0.5 - c[0]) / dx if dx < -1e-6 else None,
                              (127.5 - c[1]) / dy if dy > 1e-6 else None, (-0.5 - c[1]) / dy if dy < -1e-6 else None)
                  if t is not None]
            t_edge = min(ts)
            t_oval = 1.0 / math.sqrt((dx / rx) ** 2 + (dy / ry) ** 2) * (1.0 + rng.uniform(0.05, 0.45))
            if t_oval >= t_edge:
                continue
            t_end = t_edge - (t_edge - t_oval) * reach
            for x, y in line_px(c[0] + dx * t_edge, c[1] + dy * t_edge, c[0] + dx * t_end, c[1] + dy * t_end):
                if 0 <= x < 128 and 0 <= y < 128:
                    a[y, x, :3] = FOCUS
                    a[y, x, 3] = 190
        frames.append(a)
    return frames, (0, 0)


# ------------------------------------------------------------------------------------------------ packing

class Shelf:
    """Packs frames left to right in rows (a frame keeps its own size; 1 px of gap so nothing bleeds)."""

    def __init__(self, width):
        self.width, self.x, self.y, self.row, self.items = width, 0, 0, 0, []

    def add(self, a):
        h, w = a.shape[:2]
        if self.x + w > self.width:
            self.x, self.y, self.row = 0, self.y + self.row + 1, 0
        self.items.append((self.x, self.y, a))
        r = (self.x, self.y, w, h)
        self.x += w + 1
        self.row = max(self.row, h)
        return r

    def image(self):
        hh = self.y + self.row
        img = np.zeros((max(1, hh), self.width, 4), np.uint8)
        for x, y, a in self.items:
            img[y:y + a.shape[0], x:x + a.shape[1]] = a
        return Image.fromarray(img, 'RGBA')


def crop(a):
    ys, xs = np.nonzero(a[..., 3])
    if len(xs) == 0:
        return None, (0, 0)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    return a[y0:y1, x0:x1], (int(x0), int(y0))


def build(sheet=None):
    os.makedirs(OUT, exist_ok=True)
    meta = {'version': 1, 'marks': {}, 'tone': [], 'faces': {}}
    shelf = Shelf(512)
    for name, frs in parse_marks(MARKS_SRC).items():
        meta['marks'][name] = [list(shelf.add(a)) for a in frs]
    meta['tone'] = [list(shelf.add(a)) for a in tone_frames()]
    shelf.image().save(os.path.join(OUT, 'marks.png'), optimize=True)
    portraits = json.load(open(os.path.join(ART, 'portraits.json'), encoding='utf-8'))
    review = []
    for char, info in portraits['characters'].items():
        shelf = Shelf(1024)
        faces = meta['faces'].setdefault(char, {})
        for expr in info['expressions']:
            entry = {}
            for kind, fn in (('gloom', gloom), ('blush', blush), ('focus', focus)):
                frames, (px, py) = fn(char, expr)
                rects = []
                for a in frames:
                    c, (ox, oy) = crop(a)
                    if c is None:
                        rects.append([0, 0, 0, 0, 0, 0])
                    else:
                        rects.append(list(shelf.add(c)) + [px + ox, py + oy])
                entry[kind] = rects
                if sheet:
                    review.append((char, expr, kind, frames[-1], (px, py)))
            faces[expr] = entry
        shelf.image().save(os.path.join(OUT, char + '.png'), optimize=True)
    with open(os.path.join(OUT, 'staging.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, separators=(',', ':'))
        f.write('\n')
    n = sum(len(v) for v in meta['faces'].values())
    print('staging: %d marks, %d faces -> %s' % (len(meta['marks']), n, os.path.relpath(OUT, ROOT)))
    if sheet:
        write_sheet(sheet, review)


def write_sheet(path, review):
    """Every face with its last gloom, blush and focus frame over the portrait, x2, on the card colour."""
    Z, cols = 2, 9
    tiles = []
    by_face = {}
    for char, expr, kind, a, off in review:
        by_face.setdefault((char, expr), []).append((kind, a, off))
    for (char, expr), parts in by_face.items():
        por = Image.open(os.path.join(ART, char, expr + '.png')).convert('RGBA')
        row = Image.new('RGBA', (3 * 130, 140), (24, 22, 28, 255))
        for i, (kind, a, off) in enumerate(parts):
            t = Image.new('RGBA', (128, 128), CARD_BG)
            t.alpha_composite(por)
            t.alpha_composite(Image.fromarray(a, 'RGBA'), (int(off[0]), int(off[1])))
            row.paste(t, (i * 130, 0))
        d = ImageDraw.Draw(row)
        d.text((2, 129), '%s %s' % (char, expr), fill=(255, 230, 150, 255))
        tiles.append(row)
    w, h = tiles[0].size
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new('RGBA', (cols * (w + 4), rows * (h + 4)), (16, 14, 20, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * (w + 4), (i // cols) * (h + 4)))
    sheet = sheet.resize((sheet.width * Z // 2, sheet.height * Z // 2), Image.NEAREST)
    sheet.save(path)
    print('review sheet ->', path)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--sheet', help='also write a review sheet (every face) to this PNG')
    build(ap.parse_args().sheet)
