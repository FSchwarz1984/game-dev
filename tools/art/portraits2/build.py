"""Hand-drawn pixel dialogue portraits, v2 (rebuild: one command).

    python3 -I tools/art/portraits2/build.py               # write assets/portraits/pixel/<char>/<expr>.png + portraits.json
    python3 -I tools/art/portraits2/build.py --check       # validate only (sizes, palette, alpha, stray pixels)
    python3 -I tools/art/portraits2/build.py --preview DIR [--packs DIR]
                                                           # also write review sheets (x1 x2 x4 x8, dialogue box at
                                                           # 480x270, blind readability grids, ponytail check, v1 and
                                                           # pack side by side; --packs = the extracted owner packs)

The build reads only the text data under data/ (the owner's packs are opened only by --packs, for the side-by-side
sheet). Every pixel lives in that data:
  data/<char>/base.txt   the bust without a face (80 rows of 80 palette keys)
  data/<char>/parts.txt  the character's own parts (brows; Shione's blush, which keeps her two red marks on top)
  data/common/parts.txt  the house parts every face uses: eyes (all states), mouths, nose, tears, blush, sweat,
                         anger mark, question mark, thought dots, huff, cheek puffs (face keys, any character)
  data/<char>/faces.txt  each expression = the parts layered on the base, in order
palettes.py maps the keys to colours. Method and conventions: docs/knowledge/13-pixel-portraits.md (section 8).
Dependencies: Pillow, numpy; fontTools (with brotli) only for the dialogue mock-up when FreeType cannot read WOFF2.
"""

import argparse
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import pxgrid  # noqa: E402
from palettes import PALETTES  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(ROOT, 'assets', 'portraits', 'pixel')
V1 = os.path.join(ROOT, 'assets', 'portraits', 'pixel_v1')
CHARS = ('tsuzumi', 'shione', 'saji')
ORDER = ('neutral', 'smile', 'grin', 'laugh', 'surprise', 'shout', 'sad', 'cry', 'pout', 'angry', 'doubt', 'think',
         'embarrassed', 'serious', 'determined', 'tired', 'calm', 'blank')
EYE_LINE = (39.0, 41.5)     # midpoint between the irises, shared by all faces (swap expressions without offsets)
CARD_BG = (78, 70, 86)
NAMES = {'tsuzumi': '百々つゞみ', 'shione': '垣外しをね', 'saji': '家守さぢ'}
# where each stray pixel is allowed (glints, tear highlights, bell slit...): keys never counted as noise
STRAY_OK = set('lcazxXGqpbjkyR')


def expressions(char):
    faces = pxgrid.read_faces(char)
    return [e for e in ORDER if e in faces] + [e for e in faces if e not in ORDER]


def render(char, expr, data=None):
    base, parts, faces = data or pxgrid.load(char)
    return pxgrid.to_image(pxgrid.compose(base, parts, faces[expr]), char), \
        pxgrid.compose(base, parts, faces[expr])


def build(write=True):
    report = {}
    manifest = {'size': pxgrid.SIZE, 'version': 2, 'eye_line': list(EYE_LINE),
                'source': 'tools/art/portraits2 (hand-drawn pixel data)', 'characters': {}}
    for char in CHARS:
        data = pxgrid.load(char)
        base, parts, faces = data
        exprs = expressions(char)
        used = set()
        stray = {}
        for e in exprs:
            im, grid = render(char, e, data)
            assert im.size == (pxgrid.SIZE, pxgrid.SIZE), (char, e, im.size)
            alpha = set(im.getchannel('A').tobytes())
            assert alpha <= {0, 255}, (char, e, alpha)
            for row in grid:
                used.update(k for k in row if k != '.')
            stray[e] = [p for p in pxgrid.orphans(grid) if p[2] not in STRAY_OK]
            if write:
                d = os.path.join(OUT, char)
                os.makedirs(d, exist_ok=True)
                im.save(os.path.join(d, e + '.png'))
        pal = PALETTES[char]
        manifest['characters'][char] = {
            'name': NAMES[char],
            'expressions': exprs,
            'palette': {k: pal[k] for k in sorted(used)},
            'recipes': {e: faces[e] for e in exprs},
        }
        report[char] = {'expressions': len(exprs), 'colours': len(used), 'stray': stray}
    if write:
        with open(os.path.join(OUT, 'portraits.json'), 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
    return report


# ------------------------------------------------------------------------------------------------- previews

def _font(size, bold=True):
    p = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()


_PF = []


def _pixel_font():
    """The game's UI font (Fusion Pixel 12px Proportional, zh_hans, OFL), the same file Godot loads."""
    if _PF:
        return _PF[0]
    p = os.path.join(ROOT, 'godot', 'art', 'fonts', 'fusion-pixel-12px-proportional-zh_hans.woff2')
    try:
        f = ImageFont.truetype(p, 12)
    except OSError:                      # this FreeType cannot read WOFF2: unpack it with fontTools first
        import io
        from fontTools.ttLib import TTFont
        t = TTFont(p)
        t.flavor = None
        buf = io.BytesIO()
        t.save(buf)
        buf.seek(0)
        f = ImageFont.truetype(buf, 12)
    _PF.append(f)
    return f


def _all(char):
    data = pxgrid.load(char)
    return [(e, render(char, e, data)[0]) for e in expressions(char)]


def sheets(out):
    for char in CHARS:
        items = _all(char)
        ims = [im for _, im in items]
        labels = [e for e, _ in items]
        for k in (1, 2, 4):
            pxgrid.sheet(ims, k, cols=6, labels=labels if k > 1 else None).save(os.path.join(out, f'{char}_x{k}.png'))
        # x8 faces (crop) for pixel-level review
        crops = [im.crop((14, 26, 66, 66)) for im in ims]
        pxgrid.sheet(crops, 8, cols=4, labels=labels).save(os.path.join(out, f'{char}_faces_x8.png'))
        pxgrid.zoom(ims[0], 10).save(os.path.join(out, f'{char}_neutral_grid_x10.png'))


def readability(out, seed=8080):
    """Unlabelled, shuffled grids at x1 and x2; the key goes to a separate file (read it only after guessing)."""
    rng = random.Random(seed)
    keys = []
    for char in CHARS:
        items = _all(char)
        order = list(range(len(items)))
        rng.shuffle(order)
        ims = [items[i][1] for i in order]
        for k in (1, 2):
            sh = pxgrid.sheet(ims, k, cols=6, gap=6 if k == 1 else 8)
            d = ImageDraw.Draw(sh)
            w = 80 * k
            gap = 6 if k == 1 else 8
            for n in range(len(ims)):
                x = gap + (n % 6) * (w + gap)
                y = gap + (n // 6) * (w + gap)
                d.text((x + 1, y + 1), str(n + 1), fill=(255, 255, 255), font=_font(9 if k == 1 else 12))
            sh.save(os.path.join(out, f'blind_{char}_x{k}.png'))
        keys.append(char + ': ' + ', '.join(f'{n + 1}={items[i][0]}' for n, i in enumerate(order)))
    # all characters mixed in one grid (no position cue at all), x1 and x2
    pool = [(c, e, im) for c in CHARS for e, im in _all(c)]
    rng.shuffle(pool)
    for k in (1, 2):
        gap = 6 if k == 1 else 8
        sh = pxgrid.sheet([im for _, _, im in pool], k, cols=10, gap=gap)
        d = ImageDraw.Draw(sh)
        for n in range(len(pool)):
            x = gap + (n % 10) * (80 * k + gap)
            y = gap + (n // 10) * (80 * k + gap)
            d.text((x + 1, y + 1), str(n + 1), fill=(255, 255, 255), font=_font(9 if k == 1 else 12))
        sh.save(os.path.join(out, f'blind_mixed_x{k}.png'))
    keys.append('mixed: ' + ', '.join(f'{n + 1}={c}/{e}' for n, (c, e, _) in enumerate(pool)))
    with open(os.path.join(out, 'blind_KEY.txt'), 'w') as f:
        f.write('\n'.join(keys) + '\n')


# the dialogue box exactly as godot/story/dialogue_box.gd lays it out at native 480x270
BOX_W, BOX_H, BOTTOM, CARD, CARD_RISE = 468, 64, 6, 84, 24
PANEL = (14, 12, 18, 238)
BORDER = (214, 182, 120, 150)
BORDER_IN = (10, 9, 13, 255)
PLATE_BG = (26, 20, 24, 255)
DIAMOND = (196, 70, 46, 255)
TEXT = (243, 236, 220)
LINE = 16


def _blend(img, rect, rgba, fill=True):
    over = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    x0, y0, x1, y1 = rect
    if fill:
        d.rectangle([x0, y0, x1 - 1, y1 - 1], fill=rgba)
    else:
        d.rectangle([x0, y0, x1 - 1, y1 - 1], outline=rgba)
    img.alpha_composite(over)


def _wrap(font, text, width):
    lines, cur = [], ''
    for ch in text:
        if font.getlength(cur + ch) > width and cur:
            if ch in '，。、！？…」』）：；':     # never start a line with closing punctuation
                cur += ch
                continue
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def dialogue(world, portrait, name, text, view=(480, 270)):
    """Returns (native image, geometry). Mirrors DialogueBox.relayout() and _draw()."""
    vw, vh = view
    img = world.convert('RGBA').resize(view, Image.BOX) if world else Image.new('RGBA', view, (60, 70, 60, 255))
    bx = math.floor((vw - BOX_W) * 0.5)
    by = vh - BOTTOM - BOX_H
    box = (bx, by, bx + BOX_W, by + BOX_H)
    card = (bx + 4, by - CARD_RISE, bx + 4 + CARD, by - CARD_RISE + CARD)
    tx = card[2] + 8
    f = _pixel_font()
    nw = math.ceil(f.getlength(name))
    px = card[2] + 6
    plate = (px, by - 8, px + 15 + nw, by - 8 + 15)
    _blend(img, box, PANEL)
    _blend(img, box, BORDER, fill=False)
    _blend(img, (box[0] + 1, box[1] + 1, box[2] - 1, box[3] - 1), BORDER_IN, fill=False)
    _blend(img, card, BORDER)
    _blend(img, (card[0] + 1, card[1] + 1, card[2] - 1, card[3] - 1), BORDER_IN)
    _blend(img, (card[0] + 2, card[1] + 2, card[2] - 2, card[3] - 2), CARD_BG + (255,))
    img.alpha_composite(portrait, (card[0] + 2, card[1] + 2))
    _blend(img, plate, PLATE_BG)
    _blend(img, plate, BORDER, fill=False)
    d = ImageDraw.Draw(img)
    d.fontmode = '1'
    c = (plate[0] + 6, plate[1] + 7)
    d.polygon([(c[0], c[1] - 3), (c[0] + 3, c[1]), (c[0], c[1] + 3), (c[0] - 3, c[1])], fill=DIAMOND)
    asc = f.getbbox('百')[1]
    d.text((px + 12, by - 9 + 1 - asc + 1), name, font=f, fill=(246, 238, 219))
    tw = bx + BOX_W - 9 - tx
    lines = _wrap(f, text, tw)
    for i, ln in enumerate(lines[:2]):
        d.text((tx, by + 12 + i * LINE - asc + 1), ln, font=f, fill=TEXT)
    p = (box[2] - 11, box[3] - 9)
    d.polygon([p, (p[0] + 6, p[1]), (p[0] + 3, p[1] + 3)], fill=(230, 211, 172))
    geo = {'box': box, 'card': card, 'portrait': (card[0] + 2, card[1] + 2, card[0] + 82, card[1] + 82),
           'text': (tx, by + 12, tx + tw, by + 12 + LINE * 2 + 2), 'plate': plate, 'lines': lines}
    return img, geo


def layout_ok(geo):
    p, t, pl = geo['portrait'], geo['text'], geo['plate']
    return t[0] >= p[2] + 1 and pl[0] >= geo['card'][2] and len(geo['lines']) <= 2


def mocks(out):
    shots = os.path.join(ROOT, '.shots', 'seg1-desk')
    bgs = [os.path.join(shots, n) for n in ('15-morning.png', '04-switchbacks.png', '07-night-camphor.png')]
    bgs = [Image.open(p) for p in bgs if os.path.exists(p)] or [None]
    lines = {
        'tsuzumi': [('neutral', '减掉的那部分在您的草鞋上。'), ('cry', '……没什么。风沙进了眼睛。'),
                    ('laugh', '那么，房租请用供品支付。'), ('angry', '请把我的柱子放回去。')],
        'shione': [('smile', '打扰了。我只是路过，这就走。'), ('cry', '那里是空白。我……想不起来。'),
                   ('surprise', '我好像见过您。'), ('embarrassed', '……不要紧的。我这就把它插回去。')],
        'saji': [('pout', '哪有座敷童子交房租的啦！'), ('cry', '我的家……我的家没有了啦！'),
                 ('laugh', '背负子也是房子嘛！有柱子有横梁！'), ('shout', '救命！压扁了！')],
    }
    # a two-line line with the longest name: the text column must stay right of the portrait card
    lines['tsuzumi'].append(('serious', '梁有多重，我现在就有多重。减掉的那部分在您的草鞋上，重量不会凭空消失，请您别乱动。'))
    tiles = []
    checks = []
    for ci, char in enumerate(CHARS):
        data = pxgrid.load(char)
        for li, (e, text) in enumerate(lines[char]):
            port = render(char, e, data)[0]
            img, geo = dialogue(bgs[(ci + li) % len(bgs)], port, NAMES[char], text)
            ok = layout_ok(geo)
            checks.append(f'{char}/{e}: portrait {geo["portrait"]} text x>={geo["text"][0]} lines={len(geo["lines"])} '
                          f'plate x>={geo["plate"][0]} -> {"OK" if ok else "FAIL"}')
            img.convert('RGB').save(os.path.join(out, f'dialogue_{char}_{e}_native.png'))
            img.convert('RGB').resize((1920, 1080), Image.NEAREST).save(os.path.join(out, f'dialogue_{char}_{e}_x4.png'))
            tiles.append(img.convert('RGB'))
    # one overview at x2 (all twelve), and the phone landscape at 2400x1080 (x4, integer)
    W, H = 480 * 2, 270 * 2
    ov = Image.new('RGB', (3 * (W + 8), 5 * (H + 8)), (20, 20, 24))
    for i, t in enumerate(tiles):
        ov.paste(t.resize((W, H), Image.NEAREST), ((i // 5) * (W + 8), (i % 5) * (H + 8)))
    ov.save(os.path.join(out, 'dialogue_all_x2.png'))
    dev = Image.new('RGB', (2400, 1080), (0, 0, 0))
    dev.paste(tiles[1].resize((1920, 1080), Image.NEAREST), (240, 0))
    dev.save(os.path.join(out, 'phone_2400x1080.png'))
    with open(os.path.join(out, 'dialogue_checks.txt'), 'w') as f:
        f.write('\n'.join(checks) + '\n')
    return checks


def ponytail(out):
    """Shione: every expression with the ponytail region boxed (tie and hanging bundle) at x2."""
    items = _all('shione')
    ims = []
    for e, im in items:
        c = Image.new('RGBA', im.size, CARD_BG + (255,))
        c.alpha_composite(im)
        c = c.convert('RGB').resize((160, 160), Image.NEAREST)
        d = ImageDraw.Draw(c)
        d.rectangle([0, 110, 50, 159], outline=(0, 255, 200))
        ims.append(c)
    sh = Image.new('RGB', (6 * 166 + 6, ((len(ims) + 5) // 6) * 180 + 6), (24, 22, 28))
    d = ImageDraw.Draw(sh)
    for i, (c, (e, _)) in enumerate(zip(ims, items)):
        x, y = 6 + (i % 6) * 166, 6 + (i // 6) * 180
        sh.paste(c, (x, y))
        d.text((x, y + 162), e, fill=(240, 230, 210), font=_font(11))
    sh.save(os.path.join(out, 'shione_ponytail_check_x2.png'))


# eye centres (left, right) in the owner's packs, from the v1 measurements; used only to frame the reference crops
PACK_EYES = {
    'tsuzumi': {'neutral': ('A_35', (532, 209), (593, 237)), 'smile': ('A_01', (497, 207), (558, 235)),
                'laugh': ('A_22', (496, 201), (553, 238)), 'cry': ('A_24', (491, 207), (551, 235)),
                'surprise': ('A_13', (490, 209), (546, 238)), 'pout': ('A_04', (495, 208), (562, 234))},
    'shione': {'neutral': ('B_10', (524, 167), (581, 192)), 'smile': ('B_01', (519, 167), (582, 192)),
               'laugh': ('B_22', (537, 152), (616, 191)), 'cry': ('B_24', (528, 166), (589, 195)),
               'surprise': ('B_13', (530, 182), (588, 210)), 'pout': ('B_04', (531, 166), (594, 191))},
    'saji': {'neutral': ('C_10', (526, 169), (585, 203)), 'smile': ('C_01', (495, 184), (559, 218)),
             'laugh': ('C_22', (514, 177), (580, 218)), 'cry': ('C_24', (513, 182), (576, 218)),
             'surprise': ('C_13', (524, 188), (587, 220)), 'pout': ('C_04', (495, 184), (562, 218))},
}


def _pack_crop(packs, ident, le, re_, size=80, eyed=20.0):
    letter, n = ident[0], int(ident[2:])
    lo = (n - 1) // 9 * 9 + 1
    path = os.path.join(packs, f'Character_{letter}_{lo:02d}-{lo + 8:02d}', f'{ident}.png')
    im = Image.open(path).convert('RGBA')
    ang = math.degrees(math.atan2(re_[1] - le[1], re_[0] - le[0]))
    mx, my = (le[0] + re_[0]) / 2, (le[1] + re_[1]) / 2
    s = eyed / math.hypot(re_[0] - le[0], re_[1] - le[1])
    rot = im.rotate(ang, resample=Image.BICUBIC, center=(mx, my))
    w = size / s
    box = (round(mx - 0.5 * w), round(my - 0.52 * w), round(mx + 0.5 * w), round(my + 0.48 * w))
    return rot.crop(box).resize((size, size), Image.LANCZOS)


def compare(out, packs=None):
    """Rows per character: owner's pack (straightened, smooth), rejected v1, new v2; same expressions."""
    for char in CHARS:
        data = pxgrid.load(char)
        cols = [e for e in ('neutral', 'smile', 'laugh', 'surprise', 'cry', 'pout')]
        rows = []
        if packs and os.path.isdir(packs):
            rows.append(('pack (owner, smooth)', [_pack_crop(packs, *PACK_EYES[char][e]) for e in cols]))
        v1 = [os.path.join(V1, char, e + '.png') for e in cols]
        if all(os.path.exists(p) for p in v1):
            rows.append(('v1 (rejected)', [Image.open(p).convert('RGBA') for p in v1]))
        rows.append(('v2 (this)', [render(char, e, data)[0] for e in cols]))
        k = 3
        sh = Image.new('RGB', (150 + len(cols) * (80 * k + 8), len(rows) * (80 * k + 24) + 24), (24, 22, 28))
        d = ImageDraw.Draw(sh)
        for j, e in enumerate(cols):
            d.text((150 + j * (80 * k + 8), 4), e, fill=(255, 230, 160), font=_font(14))
        for i, (lab, ims) in enumerate(rows):
            y = 24 + i * (80 * k + 24)
            d.text((4, y + 100), lab, fill=(240, 230, 210), font=_font(13))
            for j, im in enumerate(ims):
                c = Image.new('RGBA', im.size, CARD_BG + (255,))
                c.alpha_composite(im)
                sh.paste(c.convert('RGB').resize((80 * k, 80 * k), Image.NEAREST), (150 + j * (80 * k + 8), y))
        sh.save(os.path.join(out, f'compare_{char}_x3.png'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='validate only, write nothing')
    ap.add_argument('--preview', metavar='DIR', help='also write review sheets into DIR')
    ap.add_argument('--packs', metavar='DIR', help="extracted owner packs (only for the side-by-side sheet)")
    a = ap.parse_args()
    rep = build(write=not a.check)
    for char, r in rep.items():
        n = sum(len(v) for v in r['stray'].values())
        print(f'{char}: {r["expressions"]} expressions, {r["colours"]} colours, stray pixels {n}')
        for e, v in r['stray'].items():
            if v:
                print('   ', e, v[:12])
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
        sheets(a.preview)
        readability(a.preview)
        for ln in mocks(a.preview):
            print(ln)
        ponytail(a.preview)
        compare(a.preview, a.packs)
        print('previews ->', a.preview)


if __name__ == '__main__':
    main()
