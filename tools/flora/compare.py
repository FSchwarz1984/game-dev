#!/usr/bin/env python3
"""Contact sheets: the new plants next to the rejected JS ones and the CC0 reference conifers,
all at the same native pixel density, scaled by the same integer factor, on one neutral ground.

  python3 tools/flora/compare.py --js <dir of JS sprite PNGs> --pistachio <iso_pines.png>
         [--ansimuz <trees_and_bushes png>] [--shot-js <JS game screenshot>] [--shot-new <bench x3 shot>]
         --out <dir>
JS sprites: dump them with a small node script (src/env/flora1.js PREVIEW(), camphor.js PREVIEW()).
The new plants are taken from godot/art/flora (run build.py first).
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'godot', 'art', 'flora')
BG = (74, 88, 62)
INK = (232, 226, 205)


def plant_rgba(name, shadow=False):
    """Composite of one exported plant (ground, trunk, crown), cropped, RGBA."""
    with open(os.path.join(ROOT, 'catalog.json')) as fh:
        cat = json.load(fh)
    c = cat[name]
    d = os.path.join(ROOT, 'plants', c['species'], name)
    L = c['layers']
    order = (['shadow'] if shadow else []) + ['ground', 'trunk', 'crown']
    boxes = [(L[k]['offset'], L[k]['size']) for k in order if k in L]
    x0 = min(o[0] for o, s in boxes)
    y0 = min(o[1] for o, s in boxes)
    x1 = max(o[0] + s[0] for o, s in boxes)
    y1 = max(o[1] + s[1] for o, s in boxes)
    out = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
    for k in order:
        if k not in L:
            continue
        im = np.asarray(Image.open(os.path.join(d, L[k]['albedo'])).convert('RGBA'))
        ox, oy = L[k]['offset'][0] - x0, L[k]['offset'][1] - y0
        if k == 'shadow':
            a = im[..., 3:4].astype(float) / 255 * 0.6
            sub = out[oy:oy + im.shape[0], ox:ox + im.shape[1]]
            sub[..., :3] = (sub[..., :3] * (1 - a) + np.array([30, 36, 48]) * a).astype(np.uint8)
            sub[..., 3] = np.maximum(sub[..., 3], (a[..., 0] * 255).astype(np.uint8))
            continue
        m = im[..., 3] > 0
        out[oy:oy + im.shape[0], ox:ox + im.shape[1]][m] = im[m]
    return out


def crop_alpha(im, margin=2):
    ys, xs = np.nonzero(im[..., 3] > 0)
    return im[max(0, ys.min() - margin):ys.max() + margin + 1, max(0, xs.min() - margin):xs.max() + margin + 1]


def components(path, min_px=400):
    """Split a sprite sheet into its separate sprites (by alpha), left to right, top to bottom."""
    im = np.asarray(Image.open(path).convert('RGBA'))
    lab, n = ndi.label(ndi.binary_dilation(im[..., 3] > 0, iterations=3))
    out = []
    for i, sl in enumerate(ndi.find_objects(lab)):
        if sl is None:
            continue
        sub = im[sl].copy()
        sub[lab[sl] != i + 1] = 0
        if (sub[..., 3] > 0).sum() >= min_px:
            out.append((sl[0].start, sl[1].start, sub))
    out.sort(key=lambda t: (t[0] // 200, t[1]))
    return [t[2] for t in out]


def row(images, pad=8, bottom=True):
    H = max(i.shape[0] for i in images) + 2 * pad
    W = sum(i.shape[1] for i in images) + pad * (len(images) + 1)
    out = np.zeros((H, W, 4), np.uint8)
    x = pad
    for i in images:
        y = H - pad - i.shape[0] if bottom else pad
        sub = out[y:y + i.shape[0], x:x + i.shape[1]]
        m = i[..., 3] > 0
        sub[m] = i[m]
        x += i.shape[1] + pad
    return out


def panel(title, rows, scale, out_path, labels):
    """rows: list of RGBA arrays (native px). Each row gets a label; everything is scaled by `scale`."""
    font = ImageFont.load_default()
    W = max(r.shape[1] for r in rows) * scale + 40
    H = sum(r.shape[0] * scale + 24 for r in rows) + 36
    img = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(img)
    dr.text((12, 10), title, fill=INK, font=font)
    y = 32
    for r, lab in zip(rows, labels):
        dr.text((12, y), lab, fill=INK, font=font)
        y += 16
        rgba = Image.fromarray(r, 'RGBA').resize((r.shape[1] * scale, r.shape[0] * scale), Image.NEAREST)
        img.paste(rgba, (20, y), rgba)
        y += r.shape[0] * scale + 8
    img.save(out_path)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--js', required=True)
    ap.add_argument('--pistachio', required=True)
    ap.add_argument('--ansimuz', default=None)
    ap.add_argument('--shot-js', default=None)
    ap.add_argument('--shot-new', default=None)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    js = lambda n: crop_alpha(np.asarray(Image.open(os.path.join(a.js, n + '.png')).convert('RGBA')))
    new = lambda n: crop_alpha(plant_rgba(n))
    pist = components(a.pistachio)
    # 1. conifers
    panel('Conifers, native px x3. Top: new (albedo only, no dynamic light). Middle: rejected JS. Bottom: CC0 pistachio (OpenGameArt, scored 3/5)',
          [row([new('cedar_1'), new('cedar_4'), new('cedar_2'), new('red_pine_1'), new('red_pine_3')]),
           row([js('cedar'), js('cedarB'), js('cedarThin'), js('pine'), js('pineLean')]),
           row(pist[:4])], 3, os.path.join(a.out, 'compare_conifers_x3.png'),
          ['NEW: sugi cedar x3, red pine x2', 'REJECTED JS: cedar x3, pine x2', 'CC0 pistachio pines'])
    # 2. broadleaf
    rows = [row([new('beech_1'), new('persimmon_1'), new('maple_green_1'), new('maple_turn_1'), new('maple_red_1')]),
            row([js('maple'), js('mapleR'), js('mapleS'), js('lobe')])]
    labs = ['NEW: beech, persimmon, maple green / turning / red', 'REJECTED JS: maple, red maple, small maple, camphor crown lobe']
    if a.ansimuz:
        rows.append(row(components(a.ansimuz, 2000)[:3]))
        labs.append('CC0 ansimuz Trees & Bushes (preview x2 as published)')
    panel('Broadleaf trees, native px x3', rows, 3, os.path.join(a.out, 'compare_broadleaf_x3.png'), labs)
    # 3. the camphor
    jt = js('trunk')
    lobes = [js('lobeW1'), js('lobeE1')]
    panel('The great camphor, native px x2. Top: new (one organism). Bottom: rejected JS parts (trunk sprite and two of its 14 crown lobes)',
          [row([new('camphor_a'), new('camphor_b')]), row([jt] + lobes)], 2,
          os.path.join(a.out, 'compare_camphor_x2.png'), ['NEW: camphor_a, camphor_b', 'REJECTED JS: trunk + crown lobes (placed separately in the world)'])
    # 4. small plants
    smalls = ['hydrangea_1', 'azalea_1', 'shrub_1', 'susuki_1', 'fern_1', 'higanbana_1', 'tsuyukusa_1', 'ominaeshi_1', 'bamboo_1']
    js_small = ['hydr', 'shrubA', 'shrubC', 'susuki', 'fern', 'higan', 'dayfl', 'omina', 'bamboo']
    panel('Shrubs, herbs, bamboo, native px x3', [row([new(n) for n in smalls]), row([js(n) for n in js_small])], 3,
          os.path.join(a.out, 'compare_small_x3.png'), ['NEW', 'REJECTED JS'])
    # 5. in context (both at x3: the JS shot is 1280x720 at x3, the bench shot is 1440x810 at x3)
    if a.shot_js and a.shot_new:
        A = Image.open(a.shot_js).convert('RGB')
        B = Image.open(a.shot_new).convert('RGB')
        h = min(A.height, B.height)
        A = A.crop((0, 0, A.width, h))
        B = B.crop((0, 0, min(B.width, 1280), h))
        out = Image.new('RGB', (A.width + B.width + 20, h + 30), BG)
        dr = ImageDraw.Draw(out)
        font = ImageFont.load_default()
        dr.text((10, 8), 'REJECTED JS segment 1 (x3)', fill=INK, font=font)
        dr.text((A.width + 30, 8), 'NEW in Godot (x3, same density)', fill=INK, font=font)
        out.paste(A, (0, 30))
        out.paste(B, (A.width + 20, 30))
        out.save(os.path.join(a.out, 'compare_context_x3.png'))
    print('sheets in', a.out)


if __name__ == '__main__':
    main()
