"""Compiles a character's face stamps (tools/characters3d/faces/<char>_face.py) into the atlas the
character shader reads: godot/characters/<char>/face_atlas.png (8 x 8 cells) and face.json (stamp ->
cell + pivot, the expressions). Also writes a x8 preview sheet when --preview PATH is given.
    python3 -I tools/characters3d/faces/make_faces.py kasasagi [--preview out.png]
"""
import importlib.util
import json
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CELL = 8
COLS = 16
IRIS = set('IiWS')


def load(char):
    spec = importlib.util.spec_from_file_location(char + '_face', os.path.join(HERE, char + '_face.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pad(rows):
    w = max(len(r) for r in rows)
    return [r.ljust(w, '.') for r in rows]


def take_cols(rows, cols):
    return [''.join(r[c] for c in cols if c < len(r)) for r in rows]


def drop_cols(rows, drop):
    return [''.join(ch for c, ch in enumerate(r) if c not in drop) for r in rows]


def mirror(rows, keep_highlight_left=True):
    out = []
    for r in rows:
        m = list(r[::-1])
        if keep_highlight_left and 'W' in m:
            # the highlight stays on the upper left of the iris: swap it with the leftmost iris pixel
            wi = m.index('W')
            left = next((k for k, ch in enumerate(m) if ch in IRIS), wi)
            m[wi], m[left] = m[left], m[wi]
        out.append(''.join(m))
    return out


class Atlas:
    def __init__(self, palette):
        self.pal = palette
        self.cells = []        # (name, rows, pivot)
        self.index = {}

    def add(self, name, rows, pivot):
        rows = pad(rows)
        h, w = len(rows), len(rows[0])
        assert w <= CELL and h <= CELL, (name, w, h)
        self.index[name] = {'cell': len(self.cells), 'pivot': list(pivot), 'size': [w, h]}
        self.cells.append((name, rows, pivot))

    def image(self):
        nrows = (len(self.cells) + COLS - 1) // COLS
        im = Image.new('RGBA', (COLS * CELL, max(1, nrows) * CELL), (0, 0, 0, 0))
        px = im.load()
        for k, (name, rows, pivot) in enumerate(self.cells):
            ox, oy = (k % COLS) * CELL, (k // COLS) * CELL
            for y, r in enumerate(rows):
                for x, ch in enumerate(r):
                    if ch != '.':
                        px[ox + x, oy + y] = self.pal[ch]
        return im


def build(char):
    F = load(char)
    at = Atlas(F.PALETTE)
    keep_left = getattr(F, 'EYE_LIGHT', 'one') != 'mirror'
    eye_pivots = getattr(F, 'EYE_PIVOTS', {})
    for name, rows in F.EYES.items():
        rows = pad(rows)
        ep = eye_pivots.get(name, F.EYE_PIVOT)
        for view, cols in F.VIEW_COLS.items():
            if cols is None:
                cols = list(range(len(rows[0])))
            cols = [c for c in cols if c < len(rows[0])] or [0]
            r = take_cols(rows, cols)
            px = cols.index(min(cols, key=lambda c: abs(c - ep[0])))
            piv = (px, ep[1])
            at.add('eye_R_%s_%s' % (name, view), r, piv)
            # EYE_LIGHT 'one': the mirror keeps the highlight on the screen's left (one light for both
            # eyes); 'mirror': a plain mirror image (both lights on the inner side)
            ml = mirror(r, keep_highlight_left=keep_left)
            at.add('eye_L_%s_%s' % (name, view), ml, (len(ml[0]) - 1 - piv[0], piv[1]))
    for name, rows in F.BROWS.items():
        rows = pad(rows)
        shift = F.BROW_UP_SHIFT.get(name, 0)
        for view in F.VIEW_COLS:
            cols = list(range(len(rows[0])))
            r = take_cols(rows, cols)
            px = cols.index(min(cols, key=lambda c: abs(c - F.BROW_PIVOT[0])))
            piv = (px, F.BROW_PIVOT[1] + shift)
            at.add('brow_R_%s_%s' % (name, view), r, piv)
            ml = mirror(r, keep_highlight_left=False)
            at.add('brow_L_%s_%s' % (name, view), ml, (len(ml[0]) - 1 - piv[0], piv[1]))
    for name, rows in F.MOUTHS.items():
        rows = pad(rows)
        for view, drop in F.MOUTH_VIEW_DROP.items():
            r = drop_cols(rows, drop)
            kept = [c for c in range(len(rows[0])) if c not in drop]
            px = kept.index(min(kept, key=lambda c: abs(c - F.MOUTH_PIVOT[0])))
            at.add('mouth_%s_%s' % (name, view), r, (px, F.MOUTH_PIVOT[1]))
    for name, rows in F.BLUSH.items():
        rows = pad(rows)
        at.add('cheek_R_%s_f' % name, rows, F.BLUSH_PIVOT)
        at.add('cheek_L_%s_f' % name, mirror(rows, False), (len(rows[0]) - 1 - F.BLUSH_PIVOT[0], F.BLUSH_PIVOT[1]))
        # three-quarter: one column narrower (a one-pixel blush stays as it is)
        tr = [r[1:] for r in rows] if len(rows[0]) > 1 else rows
        tl = [r[:-1] for r in rows] if len(rows[0]) > 1 else rows
        at.add('cheek_R_%s_t' % name, tr, (0, F.BLUSH_PIVOT[1]))
        at.add('cheek_L_%s_t' % name, tl, (len(tl[0]) - 1, F.BLUSH_PIVOT[1]))
    for name, rows in F.MARKS.items():
        at.add('mark_%s' % name, rows, F.MARK_PIVOT)
    meta = {'cell': CELL, 'cols': COLS, 'stamps': at.index, 'expressions': F.EXPRESSIONS, 'talk': F.TALK,
            'level_pairs': getattr(F, 'LEVEL_PAIRS', False)}
    return at, meta


def preview(at, path, scale=8):
    im = at.image()
    big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    bg = Image.new('RGBA', big.size, (251, 227, 210, 255))
    bg.alpha_composite(big)
    d = ImageDraw.Draw(bg)
    for x in range(0, bg.width, CELL * scale):
        d.line([(x, 0), (x, bg.height)], fill=(200, 160, 150, 255))
    for y in range(0, bg.height, CELL * scale):
        d.line([(0, y), (bg.width, y)], fill=(200, 160, 150, 255))
    bg.save(path)


def main():
    char = sys.argv[1] if len(sys.argv) > 1 else 'kasasagi'
    at, meta = build(char)
    out_dir = os.path.join(ROOT, 'godot', 'characters', char)
    if '--out' in sys.argv:
        out_dir = sys.argv[sys.argv.index('--out') + 1]
    os.makedirs(out_dir, exist_ok=True)
    at.image().save(os.path.join(out_dir, 'face_atlas.png'))
    with open(os.path.join(out_dir, 'face.json'), 'w') as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    if '--preview' in sys.argv:
        preview(at, sys.argv[sys.argv.index('--preview') + 1])
    print('FACE stamps=%d -> %s' % (len(at.cells), out_dir))


main()
