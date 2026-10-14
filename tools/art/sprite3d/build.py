"""Build the character sprite sheets from the 3D models (docs/knowledge/20-sprites.md).

    python3 -I tools/art/sprite3d/build.py                    # all characters
    python3 -I tools/art/sprite3d/build.py --only saji        # one character
    python3 -I tools/art/sprite3d/build.py --preview DIR      # also contact sheets and GIFs (x4)
    python3 -I tools/art/sprite3d/build.py --jobs 4           # worker processes (default: CPUs)
    python3 -I tools/art/sprite3d/build.py --pitch 39.33 --out DIR --anims idle,walk,run
                                                              # another camera pitch, elsewhere

Outputs (deterministic: the same sources give byte-identical PNGs):
    assets/sprites/<character>_<sheet>.png     albedo, RGBA, alpha 0/255
    assets/sprites/<character>_<sheet>_n.png   normal map (x right, y up, z to the viewer)
    assets/sprites/characters.json             layout: frames, pivots, animations, views, anchors
Then `python3 -I tools/godot/sync_assets.py` copies them into godot/.
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'chars'))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

CHARACTERS = ['tsuzumi', 'saji', 'shione']
# view name -> yaw (degrees; 0 = facing the camera/south, 90 = facing right/east)
VIEWS = {'front': 0, 'front_right': 45, 'right': 90, 'back_right': 135, 'back': 180,
         'back_left': -135, 'left': -90, 'front_left': -45}
VIEW_ORDER = list(VIEWS)
DIR8 = tuple(VIEW_ORDER)
DIR4 = ('front', 'right', 'back', 'left')


def load_model(name):
    mod = importlib.import_module(name)
    for a in dir(mod):
        v = getattr(mod, a)
        if isinstance(v, type) and getattr(v, 'NAME', None) == name:
            return mod, v()
    raise RuntimeError(name)


_cache = {}


def _model(name):
    if name not in _cache:
        _cache[name] = load_model(name)
    return _cache[name]


def render_job(job):
    """One (character, sheet, animation, view) row: returns albedo/normal frames and anchors."""
    name, sheet, anim, view = job
    mod, m = _model(name)
    spec = mod.ANIMS[anim]
    variant = mod.SHEETS[sheet]
    specs = spec['make'](m, view)
    for f in specs:
        f.ctx.setdefault('variant', variant)
    bws = m.simulate(specs, loop=spec['loop'])
    yaw = VIEWS[view]
    # the head keeps the rest pose's sub-pixel phase in this view (no shimmer on the face)
    ref = m.head_phase(yaw, variant)
    alb, nrm, anc = [], [], []
    for f, bw in zip(specs, bws):
        a, n, an, px = m.render_frame(bw, yaw, f.ctx, snap_head=ref if spec.get('snap', True) else None)
        alb.append(a)
        nrm.append(n)
        anc.append(an)
    return job, alb, nrm, anc


def anchors_rel(an, pivot):
    # model.render_frame gives screen px relative to the ground point; keep 1 decimal
    return {k: [round(v[0], 1), round(v[1], 1)] for k, v in an.items()}


def build(names, jobs, preview=None, out_dir=None, only_anims=None):
    import geom as G
    out_dir = out_dir or os.path.join(ROOT, 'assets', 'sprites')
    layout = {}
    for name in names:
        mod, m = load_model(name)
        FW, FH = m.FRAME
        work = []
        for sheet in mod.SHEETS:
            for anim, spec in mod.ANIMS.items():
                if sheet not in spec['sheets'] or (only_anims and anim not in only_anims):
                    continue
                for view in spec['views']:
                    work.append((name, sheet, anim, view))
        print(f'{name}: {len(work)} rows to render', flush=True)
        if jobs > 1:
            with ProcessPoolExecutor(max_workers=jobs) as ex:
                results = list(ex.map(render_job, work, chunksize=1))
        else:
            results = [render_job(w) for w in work]
        res = {r[0]: r for r in results}
        man = {'frame': [FW, FH], 'pivot': list(m.PIVOT),
               'camera': {'pitch': round(G.PITCH, 3), 'ppm': 20}, 'anims': {}, 'sheets': {}}
        for anim, spec in mod.ANIMS.items():
            if only_anims and anim not in only_anims:
                continue
            man['anims'][anim] = {'fps': spec['fps'], 'loop': spec['loop'], 'views': list(spec['views']),
                                  'sheets': [s for s in spec['sheets'] if s in mod.SHEETS], 'mirrorLeft': False}
            for k in ('speed', 'kind', 'from'):
                if k in spec:
                    man['anims'][anim][k] = spec[k]
        for sheet in mod.SHEETS:
            rows = [w for w in work if w[1] == sheet]
            cols = max(len(res[w][1]) for w in rows)
            alb = np.zeros((len(rows) * FH, cols * FW, 4), np.uint8)
            nrm = np.zeros_like(alb)
            table = {}
            problems = []
            for ri, w in enumerate(rows):
                _, A, N, AN = res[w]
                for ci, (a, n) in enumerate(zip(A, N)):
                    alb[ri * FH:(ri + 1) * FH, ci * FW:(ci + 1) * FW] = a
                    nrm[ri * FH:(ri + 1) * FH, ci * FW:(ci + 1) * FW] = n
                    ys, xs = np.nonzero(a[..., 3])
                    if len(xs) and (xs.min() < 1 or ys.min() < 1 or xs.max() > FW - 2 or ys.max() > FH - 2):
                        problems.append(f'{w[2]}.{w[3]}[{ci}] touches the cell edge')
                table.setdefault(w[2], {})[w[3]] = {'row': ri, 'frames': len(A),
                                                    'anchors': [anchors_rel(x, m.PIVOT) for x in AN]}
            base = f'{name}_{sheet}'
            out = out_dir
            os.makedirs(out, exist_ok=True)
            Image.fromarray(alb, 'RGBA').save(os.path.join(out, base + '.png'), optimize=True)
            Image.fromarray(nrm, 'RGBA').save(os.path.join(out, base + '_n.png'), optimize=True)
            man['sheets'][sheet] = {'file': base, 'width': int(alb.shape[1]), 'height': int(alb.shape[0]),
                                    'cols': cols, 'rows': len(rows), 'anims': table}
            ncol = len({tuple(c) for c in alb[alb[..., 3] > 0][:, :3]})
            print(f'  {base}: {alb.shape[1]}x{alb.shape[0]}, {len(rows)} rows, {ncol} colours', flush=True)
            for p in problems:
                print('   !', p)
            if preview:
                import preview as Pv
                Pv.sheet_previews(name, sheet, m, mod, work, res, preview)
        man['palette'] = len(m.pal.colours())
        if getattr(mod, 'RIDER', None):
            man['rider'] = dict(mod.RIDER)
        layout[name] = man
    path = os.path.join(out_dir, 'characters.json')
    old = {}
    if os.path.exists(path):
        try:
            old = json.load(open(path, encoding='utf-8'))
        except ValueError:
            old = {}
    old.update(layout)
    ordered = {k: old[k] for k in CHARACTERS if k in old}
    with open(path, 'w', encoding='utf-8') as f:
        f.write(compact_json(ordered))
    print('wrote', path)


def compact_json(data) -> str:
    """Readable but compact: one line per animation view."""
    out = ['{']
    chars = list(data.items())
    for ci, (cname, c) in enumerate(chars):
        out.append(f' {json.dumps(cname)}: {{')
        out.append(f'  "frame": {json.dumps(c["frame"])}, "pivot": {json.dumps(c["pivot"])}, "palette": {c.get("palette", 0)},')
        if 'camera' in c:
            out.append(f'  "camera": {json.dumps(c["camera"])},')
        if 'rider' in c:
            out.append(f'  "rider": {json.dumps(c["rider"])},')
        out.append('  "anims": {')
        an = list(c['anims'].items())
        for ai, (aname, a) in enumerate(an):
            out.append(f'   {json.dumps(aname)}: {json.dumps(a)}' + (',' if ai < len(an) - 1 else ''))
        out.append('  },')
        out.append('  "sheets": {')
        sh = list(c['sheets'].items())
        for si, (sname, sd) in enumerate(sh):
            head = {k: v for k, v in sd.items() if k != 'anims'}
            out.append(f'   {json.dumps(sname)}: {{' + json.dumps(head)[1:-1] + ', "anims": {')
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
    return '\n'.join(out) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default=None)
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    ap.add_argument('--preview', default=None)
    ap.add_argument('--pitch', type=float, default=None, help='camera pitch in degrees (default 20)')
    ap.add_argument('--out', default=None, help='output directory (default assets/sprites)')
    ap.add_argument('--anims', default=None, help='only these animations (comma separated)')
    args = ap.parse_args()
    if args.pitch is not None:
        if args.out is None:
            sys.exit('--pitch needs --out: the sheets in assets/sprites are the 20 degree set')
        os.environ['TENGAN_SPRITE_PITCH'] = str(args.pitch)
    names = args.only.split(',') if args.only else CHARACTERS
    build(names, args.jobs, args.preview, args.out, set(args.anims.split(',')) if args.anims else None)


if __name__ == '__main__':
    main()
