"""Small plants as pixel-art card sprites at 30 native px per metre (round 4): grasses, sedges,
ferns, clover, horsetail, plantain, bamboo grass, moss cushions, the late-summer flowers (桔梗,
女郎花, 萩, 撫子, 露草, 紫陽花), morning glory and gourd vines, iris and lilies for a turf ridge.

Every painter returns an RGBA uint8 tile: RGB = albedo (sRGB, three or four flat tones per part,
no baked light direction), A = coverage. The card's COLOR tints it (a per-clump hue and value
jitter), the renderer lights it by the card normal. One texel = one native pixel.
Rules (knowledge/25): blades one pixel wide, a dark root pixel or two, the light tone only on the
upper side of arching blades and on tips; flowers are two to five pixels, never noise.
"""
from __future__ import annotations

import math

import numpy as np

from .core import rng
from .leaves import Canvas

# --------------------------------------------------------------------------------- colours (sRGB 0..1)


def hx(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float64) / 255.0


# greens: (dark, body, light) per family, defined in CIELAB LCh: natural and full, never lime. The
# renderer's foliage material adds its own freshness on top (toon_foliage 'lush'), and the ground
# cover sets it low; these albedos sit near C* 20-26 (knowledge/25: the frame's grass came out at
# C* 42 with sRGB-picked greens).
def lch(L, C, h):
    from skimage import color as _c
    lab = np.array([[[L, C * math.cos(math.radians(h)), C * math.sin(math.radians(h))]]])
    return np.clip(_c.lab2rgb(lab)[0, 0], 0, 1)


def _fam(d, b, l):
    return (lch(*d), lch(*b), lch(*l))


GREENS = {
    'grass': _fam((27, 17, 128), (37, 22, 126), (49, 24, 116)),
    'grass_blue': _fam((27, 15, 146), (36, 19, 143), (47, 21, 136)),
    'grass_yellow': _fam((31, 19, 112), (41, 24, 110), (53, 26, 104)),
    'grass_olive': _fam((31, 13, 104), (41, 17, 102), (52, 19, 97)),
    'sedge': _fam((27, 14, 138), (36, 18, 136), (47, 20, 130)),
    'fern': _fam((24, 17, 132), (33, 22, 130), (45, 25, 122)),
    'clover': _fam((26, 17, 135), (35, 21, 132), (46, 24, 126)),
    'moss': _fam((24, 18, 126), (32, 22, 123), (43, 25, 116)),
    'horsetail': _fam((29, 15, 135), (38, 19, 132), (49, 21, 126)),
    'plantain': _fam((27, 16, 130), (36, 20, 128), (47, 22, 122)),
    'sasa': _fam((24, 14, 138), (33, 18, 136), (44, 20, 130)),
    'vine': _fam((25, 17, 132), (34, 21, 130), (45, 24, 124)),
    'iris': _fam((28, 15, 145), (38, 19, 142), (49, 21, 135)),
    'stem': _fam((32, 15, 112), (41, 18, 110), (51, 20, 106)),
}
FLOWERS = {
    'kikyo': (hx('#4a3f8a'), hx('#6b5fc0'), hx('#9a8fe0')),       # balloon flower, blue-violet
    'ominaeshi': (hx('#b08a1c'), hx('#d8b330'), hx('#f0d660')),   # patrinia, yellow
    'hagi': (hx('#8a2f62'), hx('#b8488a'), hx('#d878aa')),        # bush clover, magenta
    'nadeshiko': (hx('#b0507a'), hx('#e07aa0'), hx('#f6b0c8')),   # pink
    'tsuyukusa': (hx('#2a4ca0'), hx('#3f6ad8'), hx('#7aa0f0')),   # dayflower, blue
    'asagao': (hx('#3a3c9a'), hx('#5a5ad0'), hx('#e8e6f4')),      # morning glory, the throat white
    'yuri': (hx('#c8c0a8'), hx('#f0ece0'), hx('#fffcf2')),        # mountain lily, white
    'hozuki': (hx('#b2401c'), hx('#e0602a'), hx('#f6904a')),      # ground cherry, orange lantern
    'tanpopo': (hx('#c09018'), hx('#e8c030'), hx('#f8e070')),     # small yellow composite
    'clover_w': (hx('#c8c8b8'), hx('#eeeee0'), hx('#ffffff')),    # white clover head
    'gourd': (hx('#7a8a3a'), hx('#a8b456'), hx('#d0d88a')),
    'plume': (hx('#a89c82'), hx('#cfc4a8'), hx('#ece2c8')),       # susuki plume
}


def _jit(c, R, k=0.05):
    return np.clip(c * (1.0 + R.normal(0, k)), 0, 1)


# --------------------------------------------------------------------------------- primitives

def _blade(c, R, x, y, length, ang, curve, cols, d, thick=1, lit_side=True):
    """One blade from (x, y) (y down in tile space), starting angle ang (radians, -pi/2 = up),
    bending by `curve` per pixel. Root pixel dark, body mid, the tip and the upper side light."""
    a = ang
    px, py = x, y
    n = int(length)
    for s in range(n):
        t = s / max(n - 1, 1)
        a += curve
        px += math.cos(a)
        py += math.sin(a)
        if t < 0.15:
            col = cols[0]
        elif t > 0.78 or (lit_side and math.sin(a) > -0.2 and t > 0.4):
            col = cols[2]
        else:
            col = cols[1]
        c.put(px, py, 1.0, d + t * 0.01, col)
        if thick > 1 and t < 0.6:
            c.put(px + (1 if math.cos(a) >= 0 else -1), py, 1.0, d - 0.001, cols[0] if t < 0.2 else cols[1])
    return px, py


def tuft(W, H, seed, family='grass', n=None, spread=0.55, arch=0.9, tall=0.85, thick=1, seeds_col=None):
    """A grass tuft: blades fanning from a root, the outer ones arching over. tall: the longest
    blade as a share of the tile height."""
    R = rng(seed)
    cols = [_jit(x, R, 0.03) for x in GREENS[family]]
    c = Canvas(W, H)
    base_x, base_y = W / 2 + R.normal(0, 0.4), H - 0.5
    n = n or max(5, int(W * 0.7))
    for b in range(n):
        side = R.normal(0, spread)
        ang = -math.pi / 2 + side * 0.9
        L = R.uniform(0.45, 1.0) * H * tall * (1.0 - 0.35 * min(abs(side), 1.0))
        curve = (0.012 + 0.05 * arch * abs(side)) * (1 if side >= 0 else -1)
        d = 1.0 - abs(side) + R.normal(0, 0.2)
        ex, ey = _blade(c, R, base_x + R.normal(0, W * 0.06), base_y, L, ang, curve, cols, d, thick)
        if seeds_col is not None and R.uniform() < 0.25 and L > H * 0.5:
            c.put(ex, ey - 1, 1.0, d + 0.5, seeds_col)
    c.sep(R, 0.25)
    return c.finish()


def sedge(W, H, seed, family='sedge'):
    """Stiff, nearly upright narrow leaves (sedges, young iris): little arch, many blades."""
    return tuft(W, H, seed, family, n=int(W * 0.9), spread=0.32, arch=0.25, tall=0.95)


def iris(W, H, seed):
    """Iris on a turf ridge: a fan of flat sword leaves, two pixels wide at the base."""
    R = rng(seed)
    cols = GREENS['iris']
    c = Canvas(W, H)
    bx, by = W / 2, H - 0.5
    k = int(R.integers(5, 8))
    for i in range(k):
        side = (i - (k - 1) / 2) / max(k - 1, 1) * 1.4
        ang = -math.pi / 2 + side * 0.45 + R.normal(0, 0.05)
        _blade(c, R, bx + side * 1.2, by, H * R.uniform(0.6, 0.98) * (1 - 0.2 * abs(side)), ang, 0.008 * np.sign(side),
               cols, 1 - abs(side), thick=2)
    c.sep(R, 0.3)
    return c.finish()


def fern(W, H, seed, family='fern', fronds=None, droop=1.0):
    """Fronds fanning from the crown and arching over; pinnae as short strokes on both sides."""
    R = rng(seed)
    cols = [_jit(x, R, 0.03) for x in GREENS[family]]
    c = Canvas(W, H)
    bx, by = W * 0.5, H - 1.0
    n = fronds or int(R.integers(5, 9))
    angs = np.linspace(-math.pi + 0.45, -0.45, n) + R.normal(0, 0.1, n)
    order = np.argsort(np.abs(angs + math.pi / 2))[::-1]
    for rank, f in enumerate(order):
        a = angs[f]
        outer = abs(a + math.pi / 2) / (math.pi / 2)
        L = R.uniform(H * 0.55, H * 0.95) * (1.05 - 0.3 * outer)
        steps = max(4, int(L / 1.1))
        x, y = bx, by
        sgn = 1 if math.cos(a) >= 0 else -1
        for s in range(steps):
            t = s / steps
            a += sgn * (0.02 + 0.1 * t * t) * (0.5 + outer) * droop
            x += math.cos(a) * 1.1
            y += math.sin(a) * 1.1
            c.put(x, y, 1.0, rank, cols[0] if t < 0.2 else cols[1])
            if s >= 1:
                pl = (1 - t) * 2.4 + 0.8
                for sd in (-1, 1):
                    pa = a + sd * 1.3
                    up = math.sin(pa) < 0
                    c.line(x, y, x + math.cos(pa) * pl, y + math.sin(pa) * pl, 1.0, rank - 0.01, cols[2] if up else cols[1])
    c.sep(R, 0.35)
    return c.finish()


def clover(W, H, seed, flowers=0):
    """Clover: round trefoil leaves (2x2 leaflets) in a loose low mat; a few white heads."""
    R = rng(seed)
    cols = GREENS['clover']
    c = Canvas(W, H)
    n = max(3, int(W * H / 14))
    pts = sorted([(R.uniform(1.5, W - 1.5), R.uniform(H * 0.35, H - 1.2)) for _ in range(n)], key=lambda p: p[1])
    for k, (x, y) in enumerate(pts):
        c.line(x, y, x + R.normal(0, 0.6), H - 0.5, 1.0, y * 0.01, cols[0])
        for dx, dy in ((-1, 0), (1, 0), (0, -1)):
            for ex, ey in ((0, 0), (1, 0), (0, 1), (1, 1)):
                col = cols[2] if (ey == 0 and dy < 0) else cols[1]
                c.put(x + dx * 1.5 + ex - 0.5, y + dy * 1.5 + ey - 0.5, 1.0, y * 0.01 + 0.001, col)
        c.put(x, y, 1.0, y * 0.01 + 0.002, cols[0])
    fc = FLOWERS['clover_w']
    for k in range(flowers):
        x, y = R.uniform(2, W - 2), R.uniform(1.5, H * 0.45)
        c.line(x, y + 1, x, H - 0.5, 1.0, 5, cols[1])
        for dx, dy in ((0, 0), (1, 0), (0, -1), (1, -1)):
            c.put(x + dx, y + dy, 1.0, 6, fc[2] if dy < 0 else fc[1])
    c.sep(R, 0.2)
    return c.finish()


def moss_cushion(W, H, seed):
    """A moss cushion: a low rounded mound, the sky-lit top rim light, sporophyte specks."""
    R = rng(seed)
    cols = GREENS['moss']
    c = Canvas(W, H)
    ys, xs = np.mgrid[0:H, 0:W]
    cx = W / 2
    prof = H - 0.5 - (H - 1.5) * np.sqrt(np.clip(1 - ((xs + 0.5 - cx) / (W / 2)) ** 2, 0, 1))
    bumps = 0.8 * np.sin(xs * 1.7 + R.uniform(0, 6))
    m = (ys + 0.5) >= prof + bumps
    col = np.where(((ys + 0.5) < prof + bumps + 1.2)[..., None], cols[2], cols[1])
    col = np.where(((ys + 0.5) > H - 1.5)[..., None], cols[0], col)
    c.mask(m, 1.0, 0.0, col=np.array([1.0, 1.0, 1.0]))
    c.rgb[m] = col[m]
    for k in range(int(W / 3)):
        x = R.uniform(1, W - 1)
        y0 = prof[0, int(x)] + bumps[0, int(x)] - 0.5
        c.put(x, y0 - 1, 1.0, 1.0, hx('#9a8a40'))
    return c.finish()


def horsetail(W, H, seed):
    """Field horsetail (スギナ): two or three thin stems, at every node a whorl of fine branches
    angled down (one pixel strokes), the tips lighter."""
    R = rng(seed)
    cols = GREENS['horsetail']
    c = Canvas(W, H)
    for k in range(int(R.integers(2, 4))):
        x = W / 2 + (k - 1) * R.uniform(1.6, 2.6) + R.normal(0, 0.3)
        top = R.uniform(1, H * 0.3)
        lean = R.normal(0, 0.06)
        y = H - 0.5
        node = 0
        while y > top:
            xx = x + (H - y) * lean
            c.put(xx, y, 1.0, k, cols[0] if y > H - 2 else cols[1])
            if node % 2 == 1 and y < H - 2.5:
                L = 1 + int(2.2 * (y - top) / (H - top))
                for s_ in (-1, 1):
                    for j in range(1, L + 1):
                        c.put(xx + s_ * j, y + j * 0.6, 1.0, k - 0.01, cols[2] if j == L else cols[1])
            y -= 1.0
            node += 1
        c.put(x + (H - top) * lean, top, 1.0, k, cols[2])
    return c.finish()


def plantain(W, H, seed):
    """Plantain (オオバコ) of trodden ground: a flat rosette of broad ribbed leaves seen from above at
    an angle (a low wide star), one short seed spike."""
    R = rng(seed)
    cols = GREENS['plantain']
    c = Canvas(W, H)
    cx, cy = W / 2, H - 2.0
    k = int(R.integers(5, 8))
    angs = np.linspace(0, 2 * math.pi, k, endpoint=False) + R.uniform(0, 1)
    for i, a in enumerate(sorted(angs, key=lambda q: -math.sin(q))):
        L = R.uniform(W * 0.32, W * 0.47)
        for t in np.linspace(0.15, 1.0, int(L * 2)):
            w = math.sin(t * math.pi) * 1.5
            x = cx + math.cos(a) * L * t
            y = cy + math.sin(a) * L * t * 0.38
            for s_ in np.linspace(-w, w, max(1, int(w * 2) + 1)):
                xx = x - math.sin(a) * s_
                yy = y + math.cos(a) * s_ * 0.38
                rib = abs(s_) < 0.4
                col = cols[0] if rib and t > 0.3 else (cols[2] if (math.sin(a) < 0 and s_ < 0) else cols[1])
                c.put(xx, yy, 1.0, math.sin(a) + t * 0.01, col)
    sx = cx + R.normal(0, 0.6)
    top = max(1.0, cy - H * 0.55)
    c.line(cx, cy - 1, sx, top, 1.0, 5, cols[1])
    for y in range(int(top), int(top) + 2):
        c.put(sx, y, 1.0, 5.1, hx('#7a7a4a'))
    c.sep(R, 0.3)
    return c.finish()


def sasa(W, H, seed):
    """Kumazasa (dwarf bamboo grass): a low thicket of broad lance leaves on thin dark canes, the
    leaves held level or drooping, their edges whitened in late summer."""
    R = rng(seed)
    cols = GREENS['sasa']
    c = Canvas(W, H)
    canes = int(R.integers(3, 5))
    for k in range(canes):
        x = W * (0.2 + 0.6 * (k + R.uniform(0.2, 0.8)) / canes)
        top = R.uniform(H * 0.2, H * 0.45)
        c.line(x, H - 0.5, x + R.normal(0, 0.7), top, 1.0, k - 1, cols[0])
        for j in range(int(R.integers(3, 5))):
            ax_, ay_ = x + R.normal(0, 0.8), top + j * R.uniform(1.0, 2.2)
            ang = (R.uniform(-0.5, 0.35) if R.uniform() < 0.5 else math.pi - R.uniform(-0.5, 0.35))
            L = R.uniform(5.5, 8.5)
            for t in np.linspace(0, 1, int(L * 2)):
                w = math.sin(t * math.pi) ** 0.8 * 1.3
                px = ax_ + math.cos(ang) * L * t
                py = ay_ + math.sin(ang) * L * t * 0.6 + t * t * 1.4
                for s_ in np.linspace(-w, w, max(1, int(w * 2) + 1)):
                    edge = abs(s_) > w - 0.55 and w > 0.9 and s_ > 0
                    col = hx('#c4c49a') if (edge and R.uniform() < 0.55) else (cols[2] if s_ < -0.2 else cols[1])
                    c.put(px, py + s_ * 0.7, 1.0, k + j * 0.1 + t * 0.01, col)
    c.sep(R, 0.4)
    return c.finish()


def flower_stems(W, H, seed, kind, n=None, leaves='grass'):
    """Late-summer flowers on stems among a few leaves:
      kikyo      balloon flower: star-shaped open bells (5 px) and closed balloons (2 px)
      ominaeshi  patrinia: flat-topped sprays of tiny yellow flowers high on thin stems
      hagi       bush clover: arching sprays of small magenta pea-flowers
      nadeshiko  fringed pink: single small pink flowers
      tsuyukusa  dayflower: two round blue petals, low
      tanpopo    small yellow composites, low"""
    R = rng(seed)
    gc = GREENS['stem']
    fc = FLOWERS[kind]
    c = Canvas(W, H)
    n = n or int(R.integers(2, 5))
    # a few leaves at the foot
    for k in range(int(W * 0.5)):
        side = R.normal(0, 0.6)
        _blade(c, R, W / 2 + R.normal(0, W * 0.12), H - 0.5, R.uniform(0.15, 0.4) * H, -math.pi / 2 + side,
               0.04 * np.sign(side), GREENS[leaves], -1.0)
    for s in range(n):
        x0 = W / 2 + R.normal(0, W * 0.16)
        if kind == 'hagi':
            # an arching spray
            sgn = 1 if R.uniform() < 0.5 else -1
            a = -math.pi / 2 + sgn * R.uniform(0.2, 0.5)
            x, y = x0, H - 0.5
            L = R.uniform(0.7, 1.0) * H
            for t in range(int(L)):
                a += sgn * 0.045
                x += math.cos(a)
                y += math.sin(a)
                c.put(x, y, 1.0, s, gc[1])
                if t > L * 0.3 and t % 2 == 0:
                    c.put(x + sgn, y - 1, 1.0, s + 0.5, fc[1] if R.uniform() < 0.6 else fc[2])
                    if R.uniform() < 0.4:
                        c.put(x - sgn, y, 1.0, s + 0.5, fc[0])
                elif t % 3 == 0:
                    c.put(x - sgn, y + 1, 1.0, s - 0.1, GREENS['vine'][1])
            continue
        top = R.uniform(0.15, 0.4) * H if kind in ('kikyo', 'ominaeshi') else R.uniform(0.45, 0.7) * H
        if kind in ('tsuyukusa', 'tanpopo'):
            top = R.uniform(0.55, 0.8) * H
        x1 = x0 + R.normal(0, 1.0)
        c.line(x0, H - 0.5, x1, top, 1.0, s, gc[1])
        if kind == 'kikyo':
            if R.uniform() < 0.7:
                # an open star: centre light, five petals around
                for dx, dy, col in ((0, 0, fc[2]), (-1, 0, fc[1]), (1, 0, fc[1]), (0, -1, fc[1]), (-1, 1, fc[0]), (1, 1, fc[0]),
                                    (-2, -1, fc[1]), (2, -1, fc[1])):
                    c.put(x1 + dx, top + dy, 1.0, s + 1, col)
            else:
                for dx, dy, col in ((0, 0, fc[1]), (0, -1, fc[2]), (1, 0, fc[0])):
                    c.put(x1 + dx, top + dy, 1.0, s + 1, col)
        elif kind == 'ominaeshi':
            w = int(R.integers(2, 4))
            for dx in range(-w, w + 1):
                for dy in (-1, 0):
                    if R.uniform() < 0.8:
                        c.put(x1 + dx, top + dy - (1 if abs(dx) < w else 0) * 0, 1.0, s + 1, fc[2] if dy < 0 else fc[1])
            c.line(x1 - w, top, x1, top + 2, 1.0, s + 0.9, gc[1])
            c.line(x1 + w, top, x1, top + 2, 1.0, s + 0.9, gc[1])
        elif kind == 'nadeshiko':
            for dx, dy, col in ((0, 0, fc[0]), (-1, -1, fc[1]), (1, -1, fc[1]), (0, -1, fc[2]), (-1, 0, fc[1]), (1, 0, fc[1])):
                c.put(x1 + dx, top + dy, 1.0, s + 1, col)
        elif kind == 'tsuyukusa':
            for dx, dy, col in ((-1, -1, fc[1]), (0, -1, fc[2]), (1, -1, fc[1]), (0, 0, hx('#e8d040'))):
                c.put(x1 + dx, top + dy, 1.0, s + 1, col)
        elif kind == 'tanpopo':
            for dx, dy, col in ((0, 0, fc[0]), (-1, -1, fc[1]), (0, -1, fc[2]), (1, -1, fc[1]), (-1, 0, fc[1]), (1, 0, fc[1])):
                c.put(x1 + dx, top + dy, 1.0, s + 1, col)
    c.sep(R, 0.2)
    return c.finish()


def lily(W, H, seed):
    """Mountain lily (山百合) on the turf ridge: a stem, two leaves, a white flower facing out."""
    R = rng(seed)
    gc = GREENS['stem']
    fc = FLOWERS['yuri']
    c = Canvas(W, H)
    x = W / 2 + R.normal(0, 0.5)
    top = H * 0.2
    c.line(x, H - 0.5, x + 1, top + 3, 1.0, 0, gc[1])
    for y in (H * 0.6, H * 0.45):
        c.line(x, y, x - 2, y + 1, 1.0, 0.1, GREENS['iris'][2])
        c.line(x + 1, y - 2, x + 3, y - 1, 1.0, 0.1, GREENS['iris'][1])
    fx, fy = x + 1, top + 2
    for dx, dy, col in ((0, 0, fc[0]), (-1, -1, fc[1]), (1, -1, fc[1]), (-2, -2, fc[2]), (2, -2, fc[2]), (-2, 0, fc[1]),
                        (2, 0, fc[1]), (0, -2, fc[2]), (0, 1, hx('#c8962c'))):
        c.put(fx + dx, fy + dy, 1.0, 2, col)
    return c.finish()


def vine_leaves(W, H, seed, n=None, flowers=0, flower='asagao', fruit=0):
    """A climbing vine's mass: heart-shaped leaves (3x3 to 4x4) on thin tendrils; morning-glory
    trumpets (blue-violet with the white throat) or hanging gourds."""
    R = rng(seed)
    cols = GREENS['vine']
    c = Canvas(W, H)
    n = n or int(W * H / 12)
    pts = sorted([(R.uniform(1.5, W - 1.5), R.uniform(1.5, H - 1.5)) for _ in range(n)], key=lambda p: p[1])
    for k, (x, y) in enumerate(pts):
        s = 1 if R.uniform() < 0.7 else 2
        for dx in range(-s, s + 1):
            for dy in range(-s, s + 1):
                if abs(dx) + abs(dy) <= s + (1 if dy < 0 else 0) and not (dy == s and dx != 0):
                    col = cols[2] if dy < 0 and dx <= 0 else (cols[0] if dy == s else cols[1])
                    c.put(x + dx, y + dy, 1.0, y * 0.01 + k * 1e-4, col)
    fc = FLOWERS[flower]
    for k in range(flowers):
        x, y = R.uniform(2, W - 2), R.uniform(2, H - 2)
        for dx, dy, col in ((0, 0, fc[2]), (-1, 0, fc[1]), (1, 0, fc[1]), (0, -1, fc[1]), (0, 1, fc[0]), (-1, -1, fc[0]),
                            (1, -1, fc[0])):
            c.put(x + dx, y + dy, 1.0, 9, col)
    gc = FLOWERS['gourd']
    for k in range(fruit):
        x, y = R.uniform(3, W - 3), R.uniform(H * 0.4, H - 4)
        for dy, w in ((0, 1), (1, 1), (2, 2), (3, 2), (4, 1)):
            for dx in range(-w + 1, w):
                c.put(x + dx, y + dy, 1.0, 10, gc[2] if dx < 0 else gc[1])
        c.put(x, y - 1, 1.0, 10, cols[0])
    c.sep(R, 0.25)
    return c.finish()


def hozuki(W, H, seed):
    """Ground cherry: a few big leaves, orange paper lanterns hanging under them."""
    R = rng(seed)
    cols = GREENS['plantain']
    fc = FLOWERS['hozuki']
    c = Canvas(W, H)
    x = W / 2
    c.line(x, H - 0.5, x + R.normal(0, 1), H * 0.25, 1.0, 0, GREENS['stem'][1])
    for k in range(int(R.integers(3, 5))):
        y = H * R.uniform(0.25, 0.7)
        sgn = 1 if k % 2 else -1
        for t in range(int(R.uniform(3, 5))):
            for w in (-1, 0, 1):
                c.put(x + sgn * (t + 1), y + w + t * 0.3, 1.0, 1, cols[2] if w < 0 else cols[1])
        lx, ly = x + sgn * R.uniform(1, 3), y + 2
        for dy, w in ((0, 1), (1, 2), (2, 2), (3, 1)):
            for dx in range(-w + 1, w):
                c.put(lx + dx, ly + dy, 1.0, 3, fc[2] if (dx < 0 and dy < 2) else (fc[0] if dy == 3 else fc[1]))
    c.sep(R, 0.2)
    return c.finish()


def susuki(W, H, seed, plume=True):
    """Pampas grass: long arching blades, silvery-tan plumes on stalks above them."""
    R = rng(seed)
    cols = GREENS['grass_olive']
    c = Canvas(W, H)
    bx, by = W / 2, H - 0.5
    for b in range(int(W * 0.8)):
        side = R.normal(0, 0.5)
        L = R.uniform(0.35, 0.65) * H
        _blade(c, R, bx + R.normal(0, 1.0), by, L, -math.pi / 2 + side * 0.8, 0.05 * np.sign(side) * (0.4 + abs(side)), cols,
               1 - abs(side))
    if plume:
        pc = FLOWERS['plume']
        for p in range(int(R.integers(2, 5))):
            a = -math.pi / 2 + R.normal(0, 0.2)
            L = R.uniform(0.75, 0.97) * H
            x, y = bx + R.normal(0, 1.2), by
            for s in range(int(L)):
                x += math.cos(a)
                y += math.sin(a)
                c.put(x, y, 1.0, 5.0, GREENS['stem'][1] if s < L - 6 else pc[0])
            sgn = 1 if R.uniform() < 0.5 else -1
            for k in range(5):
                fa = math.pi / 2 - sgn * (1.0 - k * 0.15) + R.normal(0, 0.08)
                fl = R.uniform(3, 6)
                c.line(x, y + k * 0.8, x + math.cos(fa) * fl, y + k * 0.8 + math.sin(fa) * fl, 1.0, 6.0, pc[2] if k % 2 else pc[1])
    c.sep(R, 0.3)
    return c.finish()


def mophead(W, seed, kind='blue'):
    """Hydrangea mophead (RGB): florets of four petals in three tones, the top lightest."""
    cols = {'blue': ((70, 96, 158), (106, 134, 200), (156, 178, 228)),
            'violet': ((108, 82, 156), (142, 114, 192), (184, 158, 222)),
            'pink': ((168, 96, 132), (204, 128, 164), (232, 172, 200)),
            'white': ((180, 188, 172), (214, 220, 204), (240, 244, 232))}[kind]
    R = rng(seed)
    c = Canvas(W, W)
    cx, cy, r = W / 2, W / 2, W * 0.46
    pts = []
    for i in range(int(W * W / 5)):
        a = R.uniform(0, 2 * math.pi)
        rr = math.sqrt(R.uniform()) * r
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.9, rr / r))
    pts.sort(key=lambda p: p[1])
    for px, py, rr in pts:
        col = np.array(cols[2] if py < cy - r * 0.25 else (cols[1] if rr < 0.7 else cols[0])) / 255.0
        for dx, dy in ((0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)):
            c.put(px + dx, py + dy, 1.0, py * 0.01 + R.uniform(0, 0.005), col if (dx, dy) == (0, 0) else col * 0.94)
    c.sep(R, 0.35)
    return c.finish()


def eggplant(W, H, seed):
    """An eggplant plant: broad dark leaves on a purple-green stem, two or three glossy purple fruits
    hanging under them."""
    R = rng(seed)
    cols = GREENS['plantain']
    c = Canvas(W, H)
    x = W / 2
    c.line(x, H - 0.5, x + R.normal(0, 0.6), H * 0.3, 1.0, 0, hx('#4a3a4a'))
    for k in range(int(R.integers(4, 6))):
        y = H * R.uniform(0.15, 0.6)
        sgn = 1 if k % 2 else -1
        L = R.uniform(3, 5)
        for t in range(int(L)):
            for w in (-1, 0, 1):
                c.put(x + sgn * (t + 1), y + w + t * 0.25, 1.0, 1 + k * 0.01, cols[2] if w < 0 else (cols[0] if w > 0 and t > L - 2 else cols[1]))
    for k in range(int(R.integers(2, 4))):
        fx, fy = x + R.normal(0, 2.0), H * R.uniform(0.55, 0.8)
        for dy, w in ((0, 1), (1, 2), (2, 2), (3, 2), (4, 1)):
            for dx in range(-w + 1, w):
                c.put(fx + dx, fy + dy, 1.0, 3, hx('#6a4a8a') if (dx < 0 and dy == 1) else hx('#3a2450'))
        c.put(fx, fy - 1, 1.0, 3, hx('#3a5a2e'))
    c.sep(R, 0.2)
    return c.finish()


def negi(W, H, seed):
    """Green onions: a row of hollow upright leaves, pale at the foot, a white flower ball or two."""
    R = rng(seed)
    c = Canvas(W, H)
    for k in range(int(W / 2)):
        x = 1 + k * 2 + R.normal(0, 0.3)
        top = R.uniform(1, H * 0.35)
        for y in range(int(H - 1), int(top), -1):
            t = (H - y) / (H - top)
            col = hx('#d8dcc8') if t < 0.2 else (hx('#5f8a42') if t < 0.85 else hx('#86ac5a'))
            c.put(x, y, 1.0, k, col)
        if R.uniform() < 0.25:
            for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1)):
                c.put(x + dx, top + dy, 1.0, k + 0.5, hx('#e8e6d8'))
    return c.finish()


def cucumber_vine(W, H, seed):
    """Cucumber on its frame: big lobed leaves, yellow flowers, long dark-green fruits hanging."""
    R = rng(seed)
    t = vine_leaves(W, H, seed, n=int(W * H / 10))
    c = Canvas(W, H)
    c.val[:] = 1.0
    cov = t[..., 3] > 0
    c.cov[:] = cov
    c._rgb()[:] = t[..., :3] / 255.0
    c.depth[cov] = 0.0
    for k in range(int(R.integers(2, 4))):
        x, y = R.uniform(2, W - 2), R.uniform(H * 0.3, H - 6)
        for dy in range(int(R.uniform(4, 6))):
            c.put(x, y + dy, 1.0, 5, hx('#2e5a26') if dy % 2 else hx('#3e6e30'))
    for k in range(int(R.integers(1, 3))):
        x, y = R.uniform(2, W - 2), R.uniform(2, H * 0.6)
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            c.put(x + dx, y + dy, 1.0, 6, hx('#f0d040'))
    return c.finish()
