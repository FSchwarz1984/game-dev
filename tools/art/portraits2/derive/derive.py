"""Derive a portrait base (v3) from the owner's illustration. Not needed to rebuild the portraits: build.py reads
only data/; this re-creates data/<char>/base.txt (e.g. if the owner redraws a character) and documents how it was
made. Method: docs/knowledge/13-pixel-portraits.md section 9.

    python3 -I tools/art/portraits2/derive/derive.py CHAR --packs PACKS --work WORK --pixelize-python VENV/bin/python
    python3 -I tools/art/portraits2/derive/derive.py CHAR ... --write      # also replace data/CHAR/base.txt

Steps (each writes into WORK/CHAR/):
 1. crop      the illustration (opened as an image only) is rotated so the eye line keeps the head tilt chosen for
              the portrait, scaled so the eyes sit a fixed distance apart, and cropped to the 96 frame (hi.png, x16)
 2. pixelize  PixelOE (contrast mode) brings it to 96 x 96 (oe.png). It needs PixelOE + torch, so it runs in the
              Python given by --pixelize-python; skipped when oe.png exists (--repixelize forces it)
 3. materials the cells are sorted into materials (hair, skin, costume parts) by colour rules and zones (chars.py),
              then corrected by hand: paint/CHAR/m_*.txt (traced edges, the horn, the ponytail, the collar, ...)
 4. tones     each material is locked to its palette ramp: skin from the illustration's luminance, the hair from
              the PixelOE luminance smoothed along the strand flow (bigger, cleaner clusters), the long strand lines
              of the illustration two steps darker / lighter, lone pixels and tiny clusters merged, outline on the
              silhouette
 5. finish    hand paint edits paint/CHAR/p_*.txt (hat ribs, bangs, ear, horn shading, cheeks, ...) -> base.txt
The face (eyes, brows, nose, mouth) is left out: the expressions are parts (data/CHAR/parts.txt).
Dependencies: numpy, opencv-python, scikit-image, scipy, Pillow; PixelOE 0.0.10 (Apache-2.0) for step 2.
"""

import argparse
import glob
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from chars import CHARS  # noqa: E402
from lib import (N4, N8, Canvas, cells, flow_smooth, lab, norm_blur, orientation, orphan_fix, paint,  # noqa: E402
                 prune_keys, read_grid, refclass, render, ridges, shade, thin_lines, write_grid)
from palettes import PALETTES  # noqa: E402

SIZE = 96
DATA = os.path.join(os.path.dirname(HERE), 'data')


def crop(packs, cfg):
    ident = cfg['ident']
    (lx, ly), (rx, ry) = cfg['eyes']
    eyed, tilt, ex, ey = cfg['frame']
    letter, n = ident[0], int(ident[2:])
    lo = (n - 1) // 9 * 9 + 1
    im = Image.open(os.path.join(packs, f'Character_{letter}_{lo:02d}-{lo + 8:02d}', f'{ident}.png')).convert('RGBA')
    ang = math.degrees(math.atan2(ry - ly, rx - lx))
    mx, my = (lx + rx) / 2, (ly + ry) / 2
    s = eyed / math.hypot(rx - lx, ry - ly)
    rot = im.rotate(ang - tilt, resample=Image.BICUBIC, center=(mx, my))
    w = SIZE / s
    x0, y0 = mx - ex * w, my - ey * w
    return rot.crop((round(x0), round(y0), round(x0 + w), round(y0 + w))).resize((SIZE * 16, SIZE * 16), Image.LANCZOS)


def base(char, cfg, hi, oe, out):
    pal = PALETTES[char]
    cls, Lref, cref = refclass(hi)
    c, a = cells(hi)
    ctx = dict(hi=hi, oe=oe, c=c, a=a, cls=cls, L=Lref, cref=cref)
    hm = cfg['hair_mat']
    # 3. materials
    mat = [list(r) for r in cfg['materials'](ctx)]
    zone = Canvas(SIZE, SIZE, '0')
    zone.poly(cfg['zone'], '1')
    for y in range(SIZE):
        for x in range(SIZE):
            if zone.g[y][x] != '1':
                continue
            if cfg['skin_cell'](cls[y, x], x, y):
                mat[y][x] = 's'
            elif mat[y][x] == 's':
                mat[y][x] = hm
    for (x0, y0, x1, y1) in cfg['eyebox']:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                mat[y][x] = 's'
    jx0, jy0, jx1, jy1 = cfg['jaw']
    snap = [r[:] for r in mat]
    for y in range(jy0, jy1):
        for x in range(jx0, jx1):
            if zone.g[y][x] == '1' and cls[y, x] in '+#' and any(snap[y + dy][x + dx] == 's' for dx, dy in N4):
                mat[y][x] = 's'
    fx0, fy0, fx1, fy1 = cfg['face_clean']
    for _ in range(3):
        snap = [r[:] for r in mat]
        for y in range(fy0, fy1 + 1):
            for x in range(fx0, fx1 + 1):
                if zone.g[y][x] == '1' and snap[y][x] != 's' and \
                        sum(1 for dx, dy in N4 if snap[y + dy][x + dx] == 's') >= 3:
                    mat[y][x] = 's'
    for _ in range(cfg['wisp_passes']):        # 1-px wisps detached from the hair mass read as stray ink
        snap = [r[:] for r in mat]
        for y in range(SIZE):
            for x in range(SIZE):
                if snap[y][x] == hm and sum(1 for dx, dy in N8 if not (0 <= x + dx < SIZE and 0 <= y + dy < SIZE)
                                            or snap[y + dy][x + dx] == '.') >= 5:
                    mat[y][x] = '.'
    for f in sorted(glob.glob(os.path.join(HERE, 'paint', char, 'm_*.txt'))):
        mat = paint(mat, open(f, encoding='utf-8').readlines())
    write_grid(os.path.join(out, 'materials.txt'), mat)
    mat = np.array(mat)
    # 4. tones
    g = shade(mat, oe, pal, cfg['spec'])
    S = mat == 's'
    inbox = np.zeros_like(S)
    for (x0, y0, x1, y1) in cfg['eyebox']:
        inbox[y0:y1 + 1, x0:x1 + 1] = True
    c0, c1, c2 = cfg['skin_cuts']
    for y, x in zip(*np.nonzero(S)):
        v = Lref[y, x]
        g[y][x] = 's' if inbox[y, x] else ('s' if v >= c0 else 't' if v >= c1 else 'u' if v >= c2 else
                                           ('q' if v < cfg['ink_max'] else 'u'))
    g = orphan_fix(g, S)
    for _ in range(2):        # the skin line q is a 1-px line, never a fill
        snap = [r[:] for r in g]
        for y in range(1, SIZE - 1):
            for x in range(1, SIZE - 1):
                if snap[y][x] != 'q' or not S[y, x]:
                    continue
                block = any(snap[y + p][x + q] == 'q' and snap[y + p][x] == 'q' and snap[y][x + q] == 'q'
                            for p in (-1, 1) for q in (-1, 1))
                if block and all(S[y + dy, x + dx] for dx, dy in N4):
                    g[y][x] = 'u'
    theta = orientation(hi)
    for hmat, hk, cuts, flow in cfg['hairs']:
        H = mat == hmat
        v = norm_blur(flow_smooth(lab(oe[..., :3])[..., 0], H, theta, L=flow, sigma=flow / 1.6), H, cfg['hair_blur'])
        for y, x in zip(*np.nonzero(H)):
            i = 0
            while i < len(cuts) and v[y, x] < cuts[i]:
                i += 1
            g[y][x] = hk[i]
        g = orphan_fix(g, H)
        g = prune_keys(g, H, hk, minsize=cfg['hair_min'])
        pd, pl, mind, minl = cfg['strands']
        Hs = H & np.array([[g[y][x] in hk for x in range(SIZE)] for y in range(SIZE)])
        dr = ridges(hi, Hs, black=True)
        dl = thin_lines(dr, np.percentile(dr[Hs], pd), minlen=mind) & Hs
        lr = ridges(hi, Hs, black=False)
        ll = thin_lines(lr, np.percentile(lr[Hs], pl), minlen=minl) & Hs
        up = {hk[i]: hk[max(i - 2, 0)] for i in range(len(hk))}
        dn = {hk[i]: hk[min(i + 2, len(hk) - 1)] for i in range(len(hk))}
        for y, x in zip(*np.nonzero(ll)):
            g[y][x] = up.get(g[y][x], g[y][x])
        for y, x in zip(*np.nonzero(dl)):
            g[y][x] = dn.get(g[y][x], g[y][x])
    for mk, sp in cfg['spec'].items():
        M = mat == mk
        g = orphan_fix(g, M)
        g = prune_keys(g, M, ''.join(sp['ramp']), minsize=sp.get('min', 3))
    g2 = [r[:] for r in g]        # silhouette outline
    for y in range(SIZE):
        for x in range(SIZE):
            if mat[y, x] != '.' and any(0 <= x + dx < SIZE and 0 <= y + dy < SIZE and mat[y + dy, x + dx] == '.'
                                        for dx, dy in N4):
                g2[y][x] = cfg['line'].get(mat[y, x], g[y][x])
    g = g2
    write_grid(os.path.join(out, 'auto.txt'), g)
    # 5. hand finish
    for f in sorted(glob.glob(os.path.join(HERE, 'paint', char, 'p_*.txt'))):
        g = paint(g, open(f, encoding='utf-8').readlines())
    return g


def header(char, cfg):
    eyed, tilt, ex, ey = cfg['frame']
    return (f'# {char} v3 base, 96 x 96, no face (the eyes, brows, nose and mouth are parts).\n'
            f"# Started from the owner's illustration {cfg['ident']} (eyes {eyed:g} px apart, eye line tilted {tilt:g} deg,"
            f' eye midpoint at ({ex:.2f}, {ey:.2f}) of the frame)\n'
            '# by derive/derive.py, finished by hand (derive/paint/). Keys: palettes.py.\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('char', choices=sorted(CHARS))
    ap.add_argument('--packs', required=True, help="the extracted owner packs (read as images only)")
    ap.add_argument('--work', required=True, help='working directory for the intermediate files')
    ap.add_argument('--pixelize-python', help='a Python with PixelOE installed (step 2)')
    ap.add_argument('--repixelize', action='store_true')
    ap.add_argument('--write', action='store_true', help='replace data/CHAR/base.txt with the result')
    a = ap.parse_args()
    cfg = CHARS[a.char]
    out = os.path.join(a.work, a.char)
    os.makedirs(out, exist_ok=True)
    hi_png, oe_png = os.path.join(out, 'hi.png'), os.path.join(out, 'oe.png')
    crop(a.packs, cfg).save(hi_png)
    if a.repixelize or not os.path.exists(oe_png):
        if not a.pixelize_python:
            raise SystemExit('step 2 needs --pixelize-python (a Python with PixelOE installed)')
        subprocess.run([a.pixelize_python, '-I', os.path.join(HERE, 'pixelize_oe.py'), hi_png, oe_png, str(SIZE)],
                       check=True)
    hi = np.asarray(Image.open(hi_png).convert('RGBA'))
    oe = np.asarray(Image.open(oe_png).convert('RGBA'))
    g = base(a.char, cfg, hi, oe, out)
    write_grid(os.path.join(out, 'base.txt'), g, header(a.char, cfg))
    render(g, PALETTES[a.char], 4).save(os.path.join(out, 'base_x4.png'))
    cur = os.path.join(DATA, a.char, 'base.txt')
    same = os.path.exists(cur) and read_grid(cur) == g
    print(f'{a.char}: base -> {out}/base.txt ({"identical to" if same else "differs from"} data/{a.char}/base.txt)')
    if a.write:
        write_grid(cur, g, header(a.char, cfg))
        print('written', cur)


if __name__ == '__main__':
    main()
