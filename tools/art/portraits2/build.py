"""Pixel dialogue portraits, v3 (rebuild: one command).

    python3 -I tools/art/portraits2/build.py               # write assets/portraits/pixel_v3/<char>/<expr>.png + portraits.json (v3, superseded by v4)
    python3 -I tools/art/portraits2/build.py --check       # validate only (sizes, palette, alpha, stray pixels)
    python3 -I tools/art/portraits2/build.py --preview DIR [--packs DIR] [--seed N]
                                                           # also write review sheets (x1 x2 x4, faces x8, dialogue box
                                                           # on the 480x270, 426x240 and 600x270 canvases, blind
                                                           # readability grids + key (new seed = new shuffle), ponytail
                                                           # check, owner's art | v1 | v2 | v3 side by side; --packs =
                                                           # the extracted owner packs, read as images only)

The build reads only the text data under data/ (the owner's packs are opened only by --packs, for the side-by-side
sheet). Every pixel of the output lives in that data:
  data/<char>/base.txt   the bust without a face, 96 rows of 96 palette keys. v3 bases were started from the owner's
                         illustration (derive/: tilted crop, PixelOE, palette lock per material, strand cleanup) and
                         finished by hand (derive/paint/); base.txt is the result and the source of truth
  data/<char>/parts.txt  the character's parts, drawn at her head tilt: eyes (all states), brows, nose, mouths,
                         blush, tears, cheek puff
  data/common/parts.txt  the symbols every face uses (anger mark, question mark, thought dots, huff, sweat)
  data/<char>/faces.txt  each expression = the parts layered on the base, in order
palettes.py maps the keys to colours. Method and conventions: docs/knowledge/13-pixel-portraits.md (section 9).
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
OUT = os.path.join(ROOT, 'assets', 'portraits', 'pixel_v3')   # v3 (superseded by v4, tools/art/portraits4)
V1 = os.path.join(ROOT, 'assets', 'portraits', 'pixel_v1')
V2 = os.path.join(ROOT, 'assets', 'portraits', 'pixel_v2')
CHARS = ('tsuzumi', 'shione', 'saji')
S = pxgrid.SIZE
ORDER = ('neutral', 'smile', 'grin', 'laugh', 'surprise', 'shout', 'sad', 'cry', 'pout', 'angry', 'doubt', 'think',
         'embarrassed', 'serious', 'determined', 'tired', 'calm', 'blank')
# midpoint between the two irises in each base (the heads keep the illustration's tilt, so it differs per character)
EYES = {'tsuzumi': (49.5, 49.5), 'shione': (63.0, 39.0), 'saji': (49.5, 43.0)}
# the face for the x8 review crops
FACEBOX = {'tsuzumi': (26, 32, 78, 76), 'shione': (40, 20, 92, 64), 'saji': (26, 20, 78, 64)}
CARD_BG = (78, 70, 86)
NAMES = {'tsuzumi': '百々つゞみ', 'shione': '垣外しをね', 'saji': '家守さぢ'}
# keys whose lone pixels are intended (glints, tear and sweat highlights, symbol rims, blush hatching, skin lines)
STRAY_OK = set('lcCzxXkjpbqywaeiEvtun')


def expressions(char):
    faces = pxgrid.read_faces(char)
    return [e for e in ORDER if e in faces] + [e for e in faces if e not in ORDER]


def render(char, expr, data=None):
    base, parts, faces = data or pxgrid.load(char)
    grid = pxgrid.compose(base, parts, faces[expr])
    return pxgrid.to_image(grid, char), grid


def build(write=True):
    report = {}
    manifest = {'size': S, 'version': 3, 'source': 'tools/art/portraits2 (pixel data; bases started from the owner\'s '
                'illustrations and finished by hand)', 'characters': {}}
    for char in CHARS:
        data = pxgrid.load(char)
        base, parts, faces = data
        exprs = expressions(char)
        used = set()
        stray = {}
        base_stray = {(x, y) for x, y, k in pxgrid.orphans(base)}
        for e in exprs:
            im, grid = render(char, e, data)
            assert im.size == (S, S), (char, e, im.size)
            alpha = set(im.getchannel('A').tobytes())
            assert alpha <= {0, 255}, (char, e, alpha)
            for row in grid:
                used.update(k for k in row if k != '.')
            # strays the expression parts add (the base is checked once, below)
            stray[e] = [p for p in pxgrid.orphans(grid) if p[2] not in STRAY_OK and (p[0], p[1]) not in base_stray]
            if write:
                d = os.path.join(OUT, char)
                os.makedirs(d, exist_ok=True)
                im.save(os.path.join(d, e + '.png'))
        pal = PALETTES[char]
        manifest['characters'][char] = {
            'name': NAMES[char],
            'expressions': exprs,
            'eye_mid': list(EYES[char]),
            'palette': {k: pal[k] for k in sorted(used)},
            'recipes': {e: faces[e] for e in exprs},
        }
        report[char] = {'expressions': len(exprs), 'colours': len(used), 'stray': stray,
                        'base_stray': len(base_stray)}
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
        crops = [im.crop(FACEBOX[char]) for im in ims]
        pxgrid.sheet(crops, 8, cols=4, labels=labels).save(os.path.join(out, f'{char}_faces_x8.png'))
        pxgrid.zoom(ims[0], 8).save(os.path.join(out, f'{char}_neutral_grid_x8.png'))


def readability(out, seed=9696):
    """Unlabelled, shuffled grids at x1 and x2; the key goes to a separate file (read it only after guessing)."""
    rng = random.Random(seed)
    keys = []
    for char in CHARS:
        items = _all(char)
        order = list(range(len(items)))
        rng.shuffle(order)
        ims = [items[i][1] for i in order]
        for k in (1, 2):
            gap = 6 if k == 1 else 8
            sh = pxgrid.sheet(ims, k, cols=6, gap=gap)
            d = ImageDraw.Draw(sh)
            for n in range(len(ims)):
                x = gap + (n % 6) * (S * k + gap)
                y = gap + (n // 6) * (S * k + gap)
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
            x = gap + (n % 10) * (S * k + gap)
            y = gap + (n // 10) * (S * k + gap)
            d.text((x + 1, y + 1), str(n + 1), fill=(255, 255, 255), font=_font(9 if k == 1 else 12))
        sh.save(os.path.join(out, f'blind_mixed_x{k}.png'))
    keys.append('mixed: ' + ', '.join(f'{n + 1}={c}/{e}' for n, (c, e, _) in enumerate(pool)))
    with open(os.path.join(out, 'blind_KEY.txt'), 'w') as f:
        f.write('\n'.join(keys) + '\n')


# The dialogue box as godot/story/dialogue_box.gd lays it out, with the v3 card: the 96 px portrait in a 100 px card
# rising 40 px above the box (its bottom stays 4 px above the box's bottom edge, as before). These two numbers are
# the only change the Godot side needs (CARD := 100, CARD_RISE := 40); everything else is the current layout.
BOX_W, BOX_H, BOTTOM = 468, 64, 6
CARD = S + 4
CARD_RISE = 40
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
    """Returns (native image, geometry). Mirrors DialogueBox.relayout() and _draw() (with CARD/CARD_RISE above)."""
    vw, vh = view
    img = world.convert('RGBA').resize(view, Image.BOX) if world else Image.new('RGBA', view, (60, 70, 60, 255))
    bw = min(BOX_W, vw - 12)
    bx = math.floor((vw - bw) * 0.5)
    by = vh - BOTTOM - BOX_H
    box = (bx, by, bx + bw, by + BOX_H)
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
    tw = bx + bw - 9 - tx
    lines = _wrap(f, text, tw)
    for i, ln in enumerate(lines[:2]):
        d.text((tx, by + 12 + i * LINE - asc + 1), ln, font=f, fill=TEXT)
    p = (box[2] - 11, box[3] - 9)
    d.polygon([p, (p[0] + 6, p[1]), (p[0] + 3, p[1] + 3)], fill=(230, 211, 172))
    geo = {'view': view, 'box': box, 'card': card, 'portrait': (card[0] + 2, card[1] + 2, card[0] + 2 + S, card[1] + 2 + S),
           'text': (tx, by + 12, tx + tw, by + 12 + LINE * 2 + 2), 'plate': plate, 'lines': lines,
           'chars_per_line': int(tw // 12)}
    return img, geo


def layout_ok(geo):
    p, t, pl = geo['portrait'], geo['text'], geo['plate']
    return t[0] >= p[2] + 1 and pl[0] >= geo['card'][2] and len(geo['lines']) <= 2 and geo['card'][1] >= 0


def mocks(out):
    shots = os.path.join(ROOT, '.shots', 'seg1-desk')
    bgs = [os.path.join(shots, n) for n in ('15-morning.png', '04-switchbacks.png', '07-night-camphor.png')]
    bgs = [Image.open(p) for p in bgs if os.path.exists(p)] or [None]
    # layout samples only (not story lines: the sample script was rejected, G5R-9); one two-line sample with the
    # longest name checks that the second line also stays right of the portrait card
    lines = {
        'tsuzumi': [('neutral', '版式样张：名牌在卡片右边，正文不进立绘栏。'), ('cry', '版式样张：哭，泪沿脸颊流下。'),
                    ('laugh', '版式样张：大笑。'), ('angry', '版式样张：生气，怒筋在头的右上方。'),
                    ('serious', '版式样张：两行的长句。第二行同样从立绘卡片的右边开始，标点不放在行首，整句不会伸进立绘栏里。')],
        'shione': [('smile', '版式样张：微笑。'), ('cry', '版式样张：哭。'),
                   ('surprise', '版式样张：惊讶。'), ('embarrassed', '版式样张：害羞，红晕带横过两颊。')],
        'saji': [('pout', '版式样张：嘟嘴，鼓起的脸颊和一团哼气。'), ('cry', '版式样张：哭。'),
                 ('laugh', '版式样张：大笑。'), ('shout', '版式样张：大喊。')],
    }
    checks = []
    # the stage canvas is the window divided by s = round(h / 270) (aspect = expand, no black bars; knowledge/16 §13):
    # 1920x1080 -> 480x270 at x4, 1280x720 -> 426x240 at x3, a 2400x1080 phone in landscape -> 600x270 at x4
    for view in ((480, 270), (426, 240), (600, 270)):
        tag = f'{view[0]}x{view[1]}'
        tiles = []
        for ci, char in enumerate(CHARS):
            data = pxgrid.load(char)
            for li, (e, text) in enumerate(lines[char]):
                port = render(char, e, data)[0]
                img, geo = dialogue(bgs[(ci + li) % len(bgs)], port, NAMES[char], text, view)
                ok = layout_ok(geo)
                checks.append(f'{tag} {char}/{e}: card {geo["card"]} portrait {geo["portrait"]} text x>={geo["text"][0]} '
                              f'width {geo["text"][2] - geo["text"][0]} (~{geo["chars_per_line"]} CJK/line) '
                              f'lines={len(geo["lines"])} plate x>={geo["plate"][0]} -> {"OK" if ok else "FAIL"}')
                img.convert('RGB').save(os.path.join(out, f'dialogue_{tag}_{char}_{e}_native.png'))
                tiles.append(img.convert('RGB'))
        # one overview at x2 (all fifteen lines)
        W, H = view[0] * 2, view[1] * 2
        ov = Image.new('RGB', (3 * (W + 8), 5 * (H + 8)), (20, 20, 24))
        for i, t in enumerate(tiles):
            ov.paste(t.resize((W, H), Image.NEAREST), ((i // 5) * (W + 8), (i % 5) * (H + 8)))
        ov.save(os.path.join(out, f'dialogue_{tag}_all_x2.png'))
        if view == (600, 270):   # phone landscape 2400x1080: the 600x270 canvas at x4
            tiles[1].resize((2400, 1080), Image.NEAREST).save(os.path.join(out, 'phone_2400x1080.png'))
        elif view == (426, 240):  # desktop 1280x720: the 426x240 canvas at x3 (1278 px; the stage centres it)
            tiles[5].resize((1278, 720), Image.NEAREST).save(os.path.join(out, 'desktop_1280x720.png'))
    with open(os.path.join(out, 'dialogue_checks.txt'), 'w') as f:
        f.write('\n'.join(checks) + '\n')
    return checks


def ponytail(out):
    """Shione: every expression with the ponytail region boxed (red tie and the long bundle over the shoulder), x2."""
    items = _all('shione')
    sh = Image.new('RGB', (6 * (2 * S + 6) + 6, ((len(items) + 5) // 6) * (2 * S + 20) + 6), (24, 22, 28))
    d = ImageDraw.Draw(sh)
    for i, (e, im) in enumerate(items):
        c = Image.new('RGBA', im.size, CARD_BG + (255,))
        c.alpha_composite(im)
        c = c.convert('RGB').resize((2 * S, 2 * S), Image.NEAREST)
        ImageDraw.Draw(c).rectangle([0, 2 * 54, 2 * 38, 2 * S - 1], outline=(0, 255, 200))
        x, y = 6 + (i % 6) * (2 * S + 6), 6 + (i // 6) * (2 * S + 20)
        sh.paste(c, (x, y))
        d.text((x, y + 2 * S + 2), e, fill=(240, 230, 210), font=_font(11))
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
# the v3 framing: eye distance (px), eye-line tilt (deg, falling to the right), eye midpoint (fraction of the frame)
FRAME = {'tsuzumi': (21.0, 12.0, 0.52, 0.52), 'shione': (21.0, 15.0, 0.66, 0.42), 'saji': (22.0, 15.0, 0.52, 0.45)}


def _pack_crop(packs, char, ident, le, re_, size=S):
    letter, n = ident[0], int(ident[2:])
    lo = (n - 1) // 9 * 9 + 1
    path = os.path.join(packs, f'Character_{letter}_{lo:02d}-{lo + 8:02d}', f'{ident}.png')
    im = Image.open(path).convert('RGBA')
    eyed, tilt, ex, ey = FRAME[char]
    ang = math.degrees(math.atan2(re_[1] - le[1], re_[0] - le[0]))
    mx, my = (le[0] + re_[0]) / 2, (le[1] + re_[1]) / 2
    s = eyed / math.hypot(re_[0] - le[0], re_[1] - le[1])
    rot = im.rotate(ang - tilt, resample=Image.BICUBIC, center=(mx, my))
    w = size / s
    box = (round(mx - ex * w), round(my - ey * w), round(mx - ex * w + w), round(my - ey * w + w))
    return rot.crop(box).resize((size * 3, size * 3), Image.LANCZOS)


def compare(out, packs=None):
    """Rows per character: the owner's illustration (same framing, smooth), v1, v2 (both rejected), v3; each pixel
    version at x3 of its own size, so the sizes compare as they will in the game."""
    k = 3
    for char in CHARS:
        data = pxgrid.load(char)
        cols = ['neutral', 'smile', 'laugh', 'surprise', 'cry', 'pout']
        rows = []
        if packs and os.path.isdir(packs):
            rows.append(('owner\'s art', [_pack_crop(packs, char, *PACK_EYES[char][e]) for e in cols]))
        for lab, d in (('v1 (rejected)', V1), ('v2 (rejected)', V2)):
            ps = [os.path.join(d, char, e + '.png') for e in cols]
            if all(os.path.exists(p) for p in ps):
                rows.append((lab, [Image.open(p).convert('RGBA') for p in ps]))
        rows.append(('v3 (this)', [render(char, e, data)[0] for e in cols]))
        T = S * k
        sh = Image.new('RGB', (130 + len(cols) * (T + 8), len(rows) * (T + 10) + 24), (24, 22, 28))
        d = ImageDraw.Draw(sh)
        for j, e in enumerate(cols):
            d.text((130 + j * (T + 8), 4), e, fill=(255, 230, 160), font=_font(14))
        for i, (lab, ims) in enumerate(rows):
            y = 24 + i * (T + 10)
            d.text((4, y + T // 2 - 8), lab, fill=(240, 230, 210), font=_font(13))
            for j, im in enumerate(ims):
                x = 130 + j * (T + 8)
                if im.width == T:          # the smooth reference, already at the tile size
                    c = Image.new('RGBA', im.size, CARD_BG + (255,))
                    c.alpha_composite(im)
                    sh.paste(c.convert('RGB'), (x, y))
                    continue
                c = Image.new('RGBA', im.size, CARD_BG + (255,))
                c.alpha_composite(im)
                c = c.convert('RGB').resize((im.width * k, im.height * k), Image.NEAREST)
                sh.paste(c, (x + (T - c.width) // 2, y + (T - c.height)))
        sh.save(os.path.join(out, f'compare_{char}_x3.png'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='validate only, write nothing')
    ap.add_argument('--preview', metavar='DIR', help='also write review sheets into DIR')
    ap.add_argument('--packs', metavar='DIR', help="extracted owner packs (only for the side-by-side sheet)")
    ap.add_argument('--seed', type=int, default=9696, help='shuffle of the blind grids (change it for each new round)')
    a = ap.parse_args()
    rep = build(write=not a.check)
    for char, r in rep.items():
        n = sum(len(v) for v in r['stray'].values())
        print(f'{char}: {r["expressions"]} expressions, {r["colours"]} colours, stray pixels added by parts {n} '
              f'(base: {r["base_stray"]} lone pixels, reviewed by eye)')
        for e, v in r['stray'].items():
            if v:
                print('   ', e, v[:12])
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
        sheets(a.preview)
        readability(a.preview, a.seed)
        for ln in mocks(a.preview):
            print(ln)
        ponytail(a.preview)
        compare(a.preview, a.packs)
        print('previews ->', a.preview)


if __name__ == '__main__':
    main()
