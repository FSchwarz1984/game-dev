"""Previews for review (never shipped): labelled contact sheets at x4 and animated GIFs at x4."""

from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw

BG = (74, 98, 66)


def checker(w, h, s, a=(62, 66, 74), b=(70, 74, 83)):
    im = Image.new('RGB', (w, h), a)
    d = ImageDraw.Draw(im)
    for y in range(0, h, s):
        for x in range(0, w, s):
            if ((x // s) + (y // s)) % 2:
                d.rectangle([x, y, x + s - 1, y + s - 1], fill=b)
    return im


def sheet_previews(name, sheet, m, mod, work, res, out, k=4):
    os.makedirs(out, exist_ok=True)
    FW, FH = m.FRAME
    rows = [w for w in work if w[1] == sheet]
    # crop every cell to the union bounding box of the sheet to keep the contact sheet compact
    x0, y0, x1, y1 = FW, FH, 0, 0
    for w in rows:
        for a in res[w][1]:
            ys, xs = np.nonzero(a[..., 3])
            if len(xs):
                x0, y0 = min(x0, xs.min()), min(y0, ys.min())
                x1, y1 = max(x1, xs.max() + 1), max(y1, ys.max() + 1)
    x0, y0 = max(0, x0 - 1), max(0, y0 - 1)
    x1, y1 = min(FW, x1 + 1), min(FH, y1 + 1)
    cw, ch = (x1 - x0) * k, (y1 - y0) * k
    cols = max(len(res[w][1]) for w in rows)
    lw = 150
    img = Image.new('RGB', (lw + cols * (cw + 4) + 4, len(rows) * (ch + 4) + 4), (34, 37, 44))
    d = ImageDraw.Draw(img)
    for ri, w in enumerate(rows):
        y = 4 + ri * (ch + 4)
        d.text((6, y + 6), w[2], fill=(235, 235, 225))
        d.text((6, y + 22), w[3], fill=(165, 175, 195))
        d.text((6, y + 38), f"{mod.ANIMS[w[2]]['fps']} fps", fill=(120, 130, 140))
        for ci, a in enumerate(res[w][1]):
            cell = Image.fromarray(a[y0:y1, x0:x1], 'RGBA').resize((cw, ch), Image.NEAREST)
            bg = checker(cw, ch, k * 2)
            bg.paste(cell, (0, 0), cell)
            img.paste(bg, (lw + ci * (cw + 4), y))
    img.save(os.path.join(out, f'{name}_{sheet}_contact_x{k}.png'))
    # GIFs: every animation, all its views side by side
    anims = []
    for w in rows:
        if w[2] not in anims:
            anims.append(w[2])
    for an in anims:
        views = [w for w in rows if w[2] == an]
        n = max(len(res[w][1]) for w in views)
        fps = mod.ANIMS[an]['fps']
        frames = []
        for i in range(n):
            fr = Image.new('RGB', (len(views) * cw, ch), BG)
            for j, w in enumerate(views):
                a = res[w][1][i % len(res[w][1])]
                im = Image.fromarray(a[y0:y1, x0:x1], 'RGBA').resize((cw, ch), Image.NEAREST)
                fr.paste(im, (j * cw, 0), im)
            frames.append(fr)
        dur = int(round(1000 / fps))
        if not mod.ANIMS[an]['loop']:
            dur = [dur] * (n - 1) + [700]
        frames[0].save(os.path.join(out, f'{name}_{sheet}_{an}.gif'), save_all=True, append_images=frames[1:],
                       duration=dur, loop=0)
