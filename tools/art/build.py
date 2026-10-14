"""Build the character sprite sheets, normal maps, manifest data and contact sheets.

    python3 tools/art/build.py                 # sheets + src/art/characters.data.js
    python3 tools/art/build.py --contact DIR   # also write contact sheets (1x and 4x) to DIR
    python3 tools/art/build.py --anim DIR      # also write 4x animated APNG + GIF of walks and idles

Deterministic: the same sources always give byte-identical PNGs (no timestamps, fixed order).
Outputs:
    assets/sprites/<character>_<sheet>.png      albedo (RGBA, alpha 0/255)
    assets/sprites/<character>_<sheet>_n.png    normal map, same layout (see pixart.normal_map)
    src/art/characters.data.js                  frame tables and anchors (generated)
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)

import pixart as P  # noqa: E402
import rig  # noqa: E402

CHARACTERS = ['tsuzumi', 'saji', 'shione']
VIEW_ORDER = ('front', 'side', 'back')


def save_png(arr: np.ndarray, path: str):
    Image.fromarray(arr, 'RGBA').save(path, optimize=True)


def render_character(mod):
    fw, fh = mod.FRAME
    origin = mod.ORIGIN
    pivot = mod.PIVOT
    out_sheets = {}
    for sheet, flag in mod.SHEETS.items():
        rows = []   # (anim, view, frames[Frame])
        for name, (fn, views, fps, loop, sheets) in mod.ANIMS.items():
            if sheet not in sheets:
                continue
            for v in VIEW_ORDER:
                if v not in views:
                    continue
                frames = fn(v, flag)
                if not frames:
                    raise RuntimeError(f'{mod.NAME}.{name}.{v} produced no frames')
                rows.append((name, v, frames))
        cols = max(len(r[2]) for r in rows)
        W, H = cols * fw, len(rows) * fh
        alb = np.zeros((H, W, 4), np.uint8)
        nrm = np.zeros((H, W, 4), np.uint8)
        table = {}
        problems = []
        colours = set()
        for ri, (name, v, frames) in enumerate(rows):
            entry = table.setdefault(name, {})
            anchors = []
            for ci, fr in enumerate(frames):
                cv = rig.compose(fr, (fw, fh), origin)
                added = P.close_outline(cv, mod.PAL)
                if added:
                    problems.append(f'{name}.{v}[{ci}]: closed {added} outline gaps')
                a = P.albedo(cv, mod.PAL)
                n = P.normal_map(cv, mod.PAL)
                ys, xs = np.nonzero(a[..., 3])
                if len(xs) and (xs.min() < 1 or ys.min() < 1 or xs.max() > fw - 2 or ys.max() > fh - 2):
                    problems.append(f'{name}.{v}[{ci}]: touches the frame edge')
                alb[ri * fh:(ri + 1) * fh, ci * fw:(ci + 1) * fw] = a
                nrm[ri * fh:(ri + 1) * fh, ci * fw:(ci + 1) * fw] = n
                for c in map(tuple, a[a[..., 3] > 0][:, :3]):
                    colours.add(c)
                # anchors: model space -> pixels relative to the foot pivot (x right, y down)
                anchors.append({k: [origin[0] + c - pivot[0], origin[1] + r - pivot[1]] for k, (c, r) in fr.anchors.items()})
            entry[v] = {'row': ri, 'frames': len(frames), 'anchors': anchors}
        out_sheets[sheet] = {'albedo': alb, 'normal': nrm, 'table': table, 'cols': cols, 'rows': len(rows),
                             'problems': problems, 'colours': colours, 'order': [(r[0], r[1]) for r in rows]}
    return out_sheets


def label_font():
    try:
        return ImageFont.load_default()
    except Exception:  # pragma: no cover
        return None


def contact_sheet(mod, sheet_name, data, out_dir):
    """One labelled row per animation/direction: frames at 4x on a checker, plus a 1x strip."""
    fw, fh = mod.FRAME
    alb = data['albedo']
    k = 4
    font = label_font()
    label_w = 120
    rows = data['order']
    cols = data['cols']
    img = Image.new('RGB', (label_w + cols * (fw * k + 4) + 8, len(rows) * (fh * k + 6) + 8), (34, 37, 44))
    d = ImageDraw.Draw(img)
    for ri, (name, v) in enumerate(rows):
        y = 4 + ri * (fh * k + 6)
        d.text((6, y + 6), f'{name}', fill=(230, 230, 220), font=font)
        d.text((6, y + 20), f'{v}', fill=(160, 170, 190), font=font)
        n = data['table'][name][v]['frames']
        for ci in range(n):
            cell = alb[ri * fh:(ri + 1) * fh, ci * fw:(ci + 1) * fw]
            z = P.zoom(cell, k)
            img.paste(z, (label_w + ci * (fw * k + 4), y))
    img.save(os.path.join(out_dir, f'{mod.NAME}_{sheet_name}_contact_4x.png'), optimize=True)
    # 1x on a mid-grey ground
    small = Image.new('RGB', (label_w + cols * (fw + 2) + 4, len(rows) * (fh + 2) + 4), (96, 120, 84))
    ds = ImageDraw.Draw(small)
    for ri, (name, v) in enumerate(rows):
        y = 2 + ri * (fh + 2)
        ds.text((4, y + 2), f'{name} {v}', fill=(250, 250, 240), font=font)
        n = data['table'][name][v]['frames']
        for ci in range(n):
            cell = Image.fromarray(alb[ri * fh:(ri + 1) * fh, ci * fw:(ci + 1) * fw], 'RGBA')
            small.paste(cell, (label_w + ci * (fw + 2), y), cell)
    small.save(os.path.join(out_dir, f'{mod.NAME}_{sheet_name}_contact_1x.png'), optimize=True)


def compact_json(data) -> str:
    """Readable but compact: one line per animation view."""
    out = ['{']
    chars = list(data.items())
    for ci, (cname, c) in enumerate(chars):
        out.append(f' {json.dumps(cname)}: {{')
        out.append(f'  "frame": {json.dumps(c["frame"])}, "pivot": {json.dumps(c["pivot"])}, "palette": {c.get("palette", 0)},')
        if 'rider' in c:
            out.append(f'  "rider": {json.dumps(c["rider"], separators=(", ", ": "))},')
        out.append('  "anims": {')
        an = list(c['anims'].items())
        for ai, (aname, a) in enumerate(an):
            out.append(f'   {json.dumps(aname)}: {json.dumps(a, separators=(", ", ": "))}' + (',' if ai < len(an) - 1 else ''))
        out.append('  },')
        out.append('  "sheets": {')
        sh = list(c['sheets'].items())
        for si, (sname, sd) in enumerate(sh):
            head = {k: v for k, v in sd.items() if k != 'anims'}
            out.append(f'   {json.dumps(sname)}: {{' + json.dumps(head, separators=(', ', ': '))[1:-1] + ', "anims": {')
            al = list(sd['anims'].items())
            for ai, (aname, views) in enumerate(al):
                out.append(f'    {json.dumps(aname)}: {{')
                vl = list(views.items())
                for vi, (vname, vd) in enumerate(vl):
                    out.append(f'     {json.dumps(vname)}: {json.dumps(vd, separators=(",", ":"))}' + (',' if vi < len(vl) - 1 else ''))
                out.append('    }' + (',' if ai < len(al) - 1 else ''))
            out.append('   }}' + (',' if si < len(sh) - 1 else ''))
        out.append('  }')
        out.append(' }' + (',' if ci < len(chars) - 1 else ''))
    out.append('}')
    return '\n'.join(out)


def write_anims(mod, sheet_name, data, out_dir, names=('walk', 'idle'), k=4, bg=(70, 96, 64)):
    """Animated APNG and GIF at k x (one per animation/view), plus a frame-by-frame strip."""
    fw, fh = mod.FRAME
    alb = data['albedo']
    for name in names:
        if name not in data['table']:
            continue
        fps = mod.ANIMS[name][2]
        for view, entry in data['table'][name].items():
            ri, n = entry['row'], entry['frames']
            frames = []
            for ci in range(n):
                cell = alb[ri * fh:(ri + 1) * fh, ci * fw:(ci + 1) * fw]
                ys, xs = np.nonzero(alb[ri * fh:(ri + 1) * fh, :n * fw, 3])
                im = Image.new('RGB', (fw * k, fh * k), bg)
                z = Image.fromarray(cell, 'RGBA').resize((fw * k, fh * k), Image.NEAREST)
                im.paste(z, (0, 0), z)
                frames.append(im)
            base = os.path.join(out_dir, f'{mod.NAME}_{sheet_name}_{name}_{view}')
            dur = int(round(1000 / fps))
            frames[0].save(base + '.png', save_all=True, append_images=frames[1:], duration=dur, loop=0, format='PNG')
            frames[0].save(base + '.gif', save_all=True, append_images=frames[1:], duration=dur, loop=0)
            strip = Image.new('RGB', (n * (fw * k + 4), fh * k), (30, 32, 38))
            for ci, f in enumerate(frames):
                strip.paste(f, (ci * (fw * k + 4), 0))
            strip.save(base + '_strip.png')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--contact', default=None, help='directory for contact sheets')
    ap.add_argument('--only', default=None, help='comma-separated character names')
    ap.add_argument('--anim', default=None, help='directory for animated APNG/GIF previews (4x)')
    args = ap.parse_args()
    names = args.only.split(',') if args.only else CHARACTERS
    sprite_dir = os.path.join(ROOT, 'assets', 'sprites')
    os.makedirs(sprite_dir, exist_ok=True)
    manifest = {}
    for name in names:
        try:
            mod = importlib.import_module(name)
        except ModuleNotFoundError:
            print(f'skip {name}: no module')
            continue
        sheets = render_character(mod)
        man = {'frame': list(mod.FRAME), 'pivot': list(mod.PIVOT), 'sheets': {}, 'anims': {}}
        for sname, data in sheets.items():
            base = f'{name}_{sname}'
            save_png(data['albedo'], os.path.join(sprite_dir, base + '.png'))
            save_png(data['normal'], os.path.join(sprite_dir, base + '_n.png'))
            man['sheets'][sname] = {'file': base, 'width': int(data['albedo'].shape[1]), 'height': int(data['albedo'].shape[0]),
                                    'cols': data['cols'], 'rows': data['rows'], 'anims': data['table']}
            print(f'{base}: {data["albedo"].shape[1]}x{data["albedo"].shape[0]}, {data["rows"]} rows, '
                  f'{len(data["colours"])} colours')
            for p in data['problems']:
                print('   !', p)
            if args.contact:
                os.makedirs(args.contact, exist_ok=True)
                contact_sheet(mod, sname, data, args.contact)
            if args.anim:
                os.makedirs(args.anim, exist_ok=True)
                write_anims(mod, sname, data, args.anim)
        for aname, (fn, views, fps, loop, sh) in mod.ANIMS.items():
            if not any(s in man['sheets'] for s in sh):
                continue
            man['anims'][aname] = {'fps': fps, 'loop': loop, 'views': list(views), 'sheets': list(sh),
                                   'mirrorLeft': 'side' in views}
        man['palette'] = len(mod.PAL.colours())
        if getattr(mod, 'RIDER', None):
            man['rider'] = dict(mod.RIDER)
        manifest[name] = man
    out = os.path.join(ROOT, 'src', 'art', 'characters.data.js')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    existing = {}
    if args.only and os.path.exists(out):
        txt = open(out).read()
        body = txt[txt.index('CHARACTER_DATA = ') + len('CHARACTER_DATA = '):]
        existing = json.loads(body[:body.rindex('}') + 1])
    existing.update(manifest)
    with open(out, 'w') as f:
        f.write('// Generated by tools/art/build.py - do not edit by hand (python3 tools/art/build.py).\n')
        f.write('// Per character: frame [w, h] in px, pivot [x, y] (foot pivot inside a frame), anims (timing),\n')
        f.write('// sheets[name].anims[anim][view] = {row, frames, anchors[]}; anchors are px relative to the\n')
        f.write('// pivot (x right, y down), one object per frame.\n')
        f.write('export const CHARACTER_DATA = ')
        f.write(compact_json(existing))
        f.write(';\n')
    print('wrote', os.path.relpath(out, ROOT))


if __name__ == '__main__':
    main()
