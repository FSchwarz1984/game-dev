"""Pixel materials: each returns, for the pixels of one solid, a ramp id and a tone (0 dark .. 1 light)
plus optional extras. Tones are later shifted by the baked light and ambient occlusion and then
snapped to the ramp (pipeline.py), so every pixel is one of a few hand-picked colours.

Textures are evaluated in the solid's local coordinates (metres), so patterns stick to the object,
and are designed at the pixel scale: board seams 1 px, thatch strands 1-2 px, stone speckle single
pixels in clusters. Noise is used for shapes (patches, stains, moss), never as per-pixel grain.

Material functions: f(ctx, **params) -> dict(pal=int|array, tone=array, [emit=(n,3)], [bump=(n,3)],
[kb=float], [kao=float], [rim=bool]).
"""
import math

import numpy as np

from . import palette as PL
from .core import fbm2, fbm3, hash01, vnoise2, vnoise3, worley2

P = PL.ID


def _q(ctx):
    return ctx.Q[:, 0], ctx.Q[:, 1], ctx.Q[:, 2]


def facing(ctx):
    """'top' / 'front' / 'side' masks from the world normal."""
    N = ctx.N
    top = N[:, 1] > 0.62
    front = (~top) & (N[:, 2] > 0.5)
    side = ~(top | front)
    return top, front, side


def ipx(v):
    """metres -> integer pixel index (20 px per metre)."""
    return np.floor(np.asarray(v) * 20.0).astype(np.int64)


# ------------------------------------------------------------------ wood
def boards(ctx, pal='wood_old', vertical=True, board=0.3, base=0.58, seam=0.22, weather=0.18,
           seed=0, nails=None, stain=True):
    """Board cladding. Boards run along local y (vertical) or local x (horizontal); 1-px seams, a
    lighter left edge on every board (it catches the upper-left light), grain streaks, knots,
    weathering darker toward the ground (rain splash) and nail rust streaks."""
    x, y, z = _q(ctx)
    across = x if vertical else y
    along = y if vertical else x
    bi = np.floor(across / board).astype(np.int64)
    fpx = ipx(across) - ipx(bi * board)               # pixel within the board (0 at its left/bottom)
    wpx = max(2, int(round(board * 20)))
    tone = base + (hash01(bi, seed) - 0.5) * 0.10
    # grain: long streaks inside the board (2-3 px clusters, not per-pixel noise)
    g = vnoise2(ipx(across) * 0.55 + bi * 7.1, along * 1.6, seed + 3)
    tone = tone + (g - 0.5) * 0.10
    if vertical:
        tone = np.where(fpx == 0, tone - seam, tone)              # the seam
        tone = np.where(fpx == 1, tone + 0.05, tone)              # lit edge of the next board
        tone = np.where(fpx == wpx - 1, tone - 0.05, tone)
    else:
        tone = np.where(fpx == wpx - 1, tone - seam, tone)        # shadow under the board above
        tone = np.where(fpx == 0, tone + 0.06, tone)
    # knots
    kn = hash01(bi, np.floor(along / 0.45).astype(np.int64), seed + 11)
    kx = ipx(across) - ipx(bi * board) - (wpx // 2)
    ky = ipx(along) - ipx(np.floor(along / 0.45) * 0.45 + 0.22)
    knot = (kn < 0.18) & (np.abs(kx) <= 0) & (np.abs(ky) <= 0)
    tone = np.where(knot, tone - 0.22, tone)
    # weathering: darker and greyer near the ground (rain splash), patchy
    if weather:
        wy = ctx.P[:, 1]
        wn = vnoise2(ctx.P[:, 0] * 3.0, 0.0, seed + 5)
        tone = tone - weather * np.clip(1.0 - (wy - 0.1) / (0.55 + wn * 0.3), 0, 1)
    if stain:
        st = fbm2(ctx.P[:, 0] * 1.4, ctx.P[:, 1] * 0.6, 2, seed + 21)
        tone = tone - np.clip(st - 0.62, 0, 1) * 0.6
    if nails is not None:
        for (nx, ny) in nails:
            d_x = ipx(across) - ipx(nx)
            d_y = ipx(along) - ipx(ny)
            head = (d_x == 0) & (d_y == 0)
            streak = (d_x == 0) & (d_y < 0) & (d_y > -4 - (hash01(int(nx * 100), seed) * 4).astype(int))
            tone = np.where(streak, tone - 0.12, tone)
            tone = np.where(head, 0.12, tone)
    return dict(pal=P[pal], tone=tone)


def timber(ctx, pal='wood_dark', axis=1, base=0.55, seed=0, checks=True):
    """A squared timber: grain along `axis` of the local frame, occasional drying checks (cracks)."""
    Q = ctx.Q
    along = Q[:, axis]
    other = [Q[:, i] for i in range(3) if i != axis]
    a = ipx(other[0]) + ipx(other[1]) * 3
    tone = base + (vnoise2(a * 0.6, along * 2.2, seed) - 0.5) * 0.14
    if checks:
        c = hash01(a, seed + 4)
        crack = (c < 0.07) & (vnoise2(along * 1.3, a * 0.1, seed + 9) > 0.5)
        tone = np.where(crack, tone - 0.25, tone)
    return dict(pal=P[pal], tone=tone)


def end_grain(ctx, pal='wood_end', r=0.1, seed=0, center=None):
    """The sawn end of a log: rings around the pith, a darker bark rim, a radial check."""
    Q = ctx.Q
    cx, cz = (0.0, 0.0) if center is None else center
    d = np.hypot(Q[:, 0] - cx, Q[:, 2] - cz) / max(r, 1e-6)
    ring = (np.floor(d * 4.0 + hash01(ipx(Q[:, 0]), ipx(Q[:, 2]), seed) * 0.4) % 2) * 0.06
    tone = 0.62 - d * 0.18 + ring
    tone = np.where(d > 0.82, 0.25, tone)
    return dict(pal=P[pal], tone=tone)


# ------------------------------------------------------------------ plaster and mud
def plaster(ctx, base=0.62, seed=0, fallen=0.0, cracks=0.5, tide=0.25):
    """Earth plaster: soft mottling in two or three tones, hairline cracks, a tide mark near the
    bottom, and (fallen > 0) patches where the finish fell and the straw-laced mud shows."""
    X = ctx.P[:, 0]
    Y = ctx.P[:, 1]
    Z = ctx.P[:, 2]
    s = X + Z * 0.7
    m = fbm2(s * 1.1, Y * 1.1, 3, seed)
    tone = base + np.round((m - 0.5) * 3.0) / 3.0 * 0.07
    pal = np.full(len(X), P['plaster'])
    if fallen > 0:
        f = fbm2(s * 1.8 + 3.1, Y * 1.8, 3, seed + 5)
        hole = f > 1.0 - fallen * 0.35
        rim = (f > 1.0 - fallen * 0.35 - 0.035) & ~hole
        pal = np.where(hole, P['mud'], pal)
        straw = hash01(ipx(s), ipx(Y), seed + 8) < 0.16
        tone = np.where(hole, 0.42 + straw * 0.25 + (hash01(ipx(s) // 2, ipx(Y), seed) - 0.5) * 0.1, tone)
        tone = np.where(rim, tone + 0.10, tone)
    if cracks > 0:
        # thin dark cracks along the ridges of a warped worley field
        w1, w2, _ = worley2(s * 2.2 + vnoise2(Y * 3, s * 3, seed) * 0.5, Y * 2.2, seed + 13)
        crack = ((w2 - w1) < 0.045) & (vnoise2(s * 1.5, Y * 1.5, seed + 17) < cracks)
        tone = np.where(crack & (pal == P['plaster']), tone - 0.20, tone)
    if tide > 0:
        tm = Y < (0.32 + vnoise2(s * 2.0, 0.0, seed + 19) * 0.18)
        tone = np.where(tm & (pal == P['plaster']), tone - tide * 0.5, tone)
    return dict(pal=pal, tone=tone)


# ------------------------------------------------------------------ thatch
def thatch(ctx, seed=0, course=0.42, moss=0.35, base=0.56, along_axis='slope', weeds=0.0):
    """Aged thatch on a slope: courses (bands of the thatcher's layers) with a lighter upper part and a
    shadowed lower lip, vertical strand clusters 1-2 px wide that follow the fall line, damp darker
    patches and moss cushions (more toward the eaves and on the shaded east)."""
    X = ctx.P[:, 0]
    Y = ctx.P[:, 1]
    Z = ctx.P[:, 2]
    # position down the fall line in screen terms, so courses read as bands on screen
    fall = Z - Y                                     # grows downward on screen
    wob = (vnoise2(X * 0.7, 0.0, seed) - 0.5) * 0.5
    k = fall / course + wob
    cf = k - np.floor(k)
    ci = np.floor(k).astype(np.int64)
    sx = ipx(X)
    # bundles: irregular vertical strokes 2-5 px wide inside each course
    bw = 3 + (hash01(ci, seed + 9) * 2).astype(np.int64)
    bi = (sx + (hash01(ci, seed + 8) * 7).astype(np.int64)) // bw
    btone = (hash01(bi, ci, seed + 1) - 0.5) * 0.16
    gap = ((sx + (hash01(ci, seed + 8) * 7).astype(np.int64)) % bw == 0) & (hash01(bi, ci, seed + 3) < 0.45)
    tone = base + btone
    tone = tone + np.where(cf < 0.22, 0.09, 0.0) - np.where(cf > 0.78, 0.12, 0.0)
    tone = np.where(gap & (cf > 0.22), tone - 0.07, tone)
    # long combed streaks that run across courses (soft, low amplitude)
    streak = vnoise2(sx * 0.35, fall * 0.8, seed + 3)
    tone = tone + np.round((streak - 0.5) * 2.0) * 0.035
    # damp, darker areas (big and soft)
    damp = fbm2(X * 0.6, fall * 0.6, 3, seed + 4)
    tone = tone - np.clip(damp - 0.58, 0, 1) * 0.45
    pal = np.full(len(X), P['thatch'])
    if moss > 0:
        mz = fbm2(X * 1.0 + 7.0, fall * 1.1, 3, seed + 5) + np.clip(ctx.N[:, 0], 0, 1) * 0.10 \
            + np.clip(fall - np.median(fall), 0, 3) * 0.035
        mm = mz > (0.84 - moss * 0.22)
        pal = np.where(mm, P['moss'], pal)
        cush = vnoise2(X * 6.0, fall * 6.0, seed + 6)
        tone = np.where(mm, 0.40 + np.clip(mz - 0.66, 0, 0.3) * 0.9 + np.round((cush - 0.5) * 2) * 0.08
                        + np.where(cf < 0.25, 0.08, 0.0), tone)
    if weeds > 0:
        w = (hash01(sx // 4, ipx(fall) // 5, seed + 7) < weeds * 0.035) & (cf < 0.4)
        pal = np.where(w, P['leaf'], pal)
        tone = np.where(w, 0.5 + hash01(sx, ipx(fall), seed) * 0.3, tone)
    return dict(pal=pal, tone=tone)


def thatch_cut(ctx, seed=0, base=0.66):
    """The cut face of thick thatch at the eave: densely packed straw ends, 1-px vertical streaks,
    lighter than the slope above (the ends face out), a ragged dark underside."""
    X = ctx.P[:, 0]
    Y = ctx.P[:, 1]
    Z = ctx.P[:, 2]
    sx = ipx(X + Z * 0.3)
    v = Y - ctx.solid.data.get('cut_y0', np.min(Y))
    h = max(1e-3, ctx.solid.data.get('cut_h', np.ptp(Y) + 1e-3))
    f = np.clip(v / h, 0, 1)
    tone = base + (hash01(sx, seed) - 0.5) * 0.22 + (hash01(sx // 3, seed + 1) - 0.5) * 0.08
    tone = tone - (1 - f) * 0.16
    tone = np.where(f < 0.16 + hash01(sx, seed + 2) * 0.1, tone - 0.28, tone)
    return dict(pal=P['thatch'], tone=tone)


# ------------------------------------------------------------------ stone
def stone(ctx, pal='stone', base=0.56, seed=0, moss=0.25, lichen=0.2, speckle=0.06, blocks=None,
          chips=True):
    """Granite / andesite: soft two-tone mottling, sparse single-pixel speckles in pairs, chipped dark
    pits, moss where the surface faces up and sits in occlusion, pale lichen rosettes."""
    X = ctx.P[:, 0]
    Y = ctx.P[:, 1]
    Z = ctx.P[:, 2]
    m = fbm3(X * 2.4, Y * 2.4, Z * 2.4, 3, seed)
    tone = base + np.round((m - 0.5) * 4.0) / 4.0 * 0.10
    sx = ipx(X)
    sy = ipx(Z - Y)
    sp = hash01(sx, sy, seed + 1)
    tone = np.where(sp < speckle, tone + 0.12, tone)
    tone = np.where((sp > 1 - speckle * 0.7), tone - 0.12, tone)
    if chips:
        pit = (hash01(sx // 2, sy // 2, seed + 2) < 0.025)
        tone = np.where(pit, tone - 0.22, tone)
    pal_arr = np.full(len(X), P[pal])
    if blocks is not None:
        pass
    up = ctx.N[:, 1]
    if moss > 0:
        mz = fbm3(X * 3.0 + 4, Y * 3.0, Z * 3.0, 3, seed + 3) + up * 0.25 + (1 - ctx.ao) * 0.35
        mm = mz > (1.02 - moss * 0.45)
        pal_arr = np.where(mm, P['moss'], pal_arr)
        tone = np.where(mm, 0.42 + (mz - 0.8) * 0.8 + up * 0.15 +
                        (hash01(sx // 2, sy // 2, seed + 4) - 0.5) * 0.18, tone)
    if lichen > 0:
        lz = vnoise3(X * 7.0, Y * 7.0, Z * 7.0, seed + 5)
        lm = (lz > 1 - lichen * 0.25) & (pal_arr == P[pal])
        pal_arr = np.where(lm, P['lichen'], pal_arr)
        tone = np.where(lm, 0.55 + (lz - 0.8) * 1.2, tone)
    return dict(pal=pal_arr, tone=tone)


def stonework(ctx, pal='stone', base=0.56, seed=0, size=0.32, moss=0.3, mortar=False):
    """Dry-laid stones on a face (wall, base): elongated cells, each stone its own tone and a lit
    upper-left bevel, dark joints, moss in the joints."""
    X = ctx.P[:, 0]
    Y = ctx.P[:, 1]
    Z = ctx.P[:, 2]
    s = X + Z * 0.5
    w1, w2, cid = worley2(s / (size * 1.4), Y / size, seed, jitter=0.85)
    edge = (w2 - w1)
    tone = base + (hash01(cid, seed + 1) - 0.5) * 0.18
    # bevel: pixels just inside the upper-left boundary light, lower-right dark
    gx = worley2((s + 0.05) / (size * 1.4), Y / size, seed, jitter=0.85)[2] != cid
    gy = worley2(s / (size * 1.4), (Y - 0.05) / size, seed, jitter=0.85)[2] != cid
    tone = np.where(gx | gy, tone - 0.10, tone)
    joint = edge < 0.07
    tone = np.where(joint, 0.12, tone)
    pal_arr = np.full(len(X), P[pal])
    if moss > 0:
        mj = joint & (vnoise2(s * 4, Y * 4, seed + 3) < moss)
        pal_arr = np.where(mj, P['moss'], pal_arr)
        tone = np.where(mj, 0.38, tone)
    return dict(pal=pal_arr, tone=tone)


# ------------------------------------------------------------------ roofs: bark shingles
def shingles(ctx, pal='bark', seed=0, row=0.09, width=0.11, base=0.56, moss=0.25):
    """Bark / board shingles: short overlapping rows (each 2 px on screen), staggered splits, a dark
    shadow line under every row, moss in damp patches."""
    X = ctx.P[:, 0]
    Y = ctx.P[:, 1]
    Z = ctx.P[:, 2]
    fall = Z - Y
    k = fall / row
    ri = np.floor(k).astype(np.int64)
    cf = k - ri
    off = (ri % 2) * 0.5
    ci = np.floor(X / width + off + hash01(ri, seed) * 0.3).astype(np.int64)
    tone = base + (hash01(ci, ri, seed + 1) - 0.5) * 0.16
    tone = np.where(cf > 0.62, tone - 0.18, tone)
    split = (ipx(X) - ipx((ci - off) * width)) == 0
    tone = np.where(split & (cf < 0.62), tone - 0.10, tone)
    pal_arr = np.full(len(X), P[pal])
    if moss > 0:
        mz = fbm2(X * 2.2, fall * 2.2, 3, seed + 3) + np.clip(ctx.N[:, 0], 0, 1) * 0.1
        mm = mz > 0.9 - moss * 0.3
        pal_arr = np.where(mm, P['moss'], pal_arr)
        tone = np.where(mm, 0.45 + (mz - 0.75) + np.where(cf > 0.62, -0.1, 0.05), tone)
    return dict(pal=pal_arr, tone=tone)


# ------------------------------------------------------------------ fibres
def bamboo(ctx, pal='bamboo', node=0.24, seed=0, base=0.6):
    """A bamboo culm along local y: a node ring every `node` metres (light ridge over a dark line),
    faint vertical striations."""
    Q = ctx.Q
    a = Q[:, 1] / node + hash01(seed) * 0.7
    f = a - np.floor(a)
    tone = base + (vnoise2(ipx(Q[:, 0] + Q[:, 2]) * 0.7, Q[:, 1] * 3.0, seed) - 0.5) * 0.08
    tone = np.where(f < 0.06, tone + 0.14, tone)
    tone = np.where((f >= 0.06) & (f < 0.12), tone - 0.20, tone)
    return dict(pal=P[pal], tone=tone)


def rope(ctx, pal='rope', twist=0.07, seed=0, base=0.6):
    """Twisted straw rope (lines or capsules): diagonal strands alternating light/dark along the cord."""
    if ctx.is_line:
        u = ctx.u
    else:
        h, ang, _ = ctx.solid.axial(ctx.P)
        L = np.linalg.norm(ctx.solid.b - ctx.solid.a)
        u = h * L + ang / (2 * math.pi) * twist
    ph = np.floor(u / (twist * 0.5)).astype(np.int64)
    tone = base + np.where(ph % 2 == 0, 0.10, -0.08) + (hash01(ph, seed) - 0.5) * 0.06
    return dict(pal=P[pal], tone=tone)


def straw(ctx, seed=0, base=0.6, pal='straw', axis=1):
    """Bundled straw: dense parallel 1-px streaks along the bundle's axis."""
    Q = ctx.Q
    along = Q[:, axis]
    others = [Q[:, i] for i in range(3) if i != axis]
    acr = ipx(others[0] + others[1] * 0.37)
    tone = base + (hash01(acr, seed) - 0.5) * 0.24 + (vnoise2(acr * 0.5, along * 4.0, seed + 1) - 0.5) * 0.1
    return dict(pal=P[pal], tone=tone)


def paper(ctx, seed=0, base=0.66, ribs=None, rib_axis=1):
    """Washi: a faint fibre mottle; lantern ribs as darker rings every `ribs` metres."""
    Q = ctx.Q
    tone = base + (vnoise3(Q[:, 0] * 18, Q[:, 1] * 18, Q[:, 2] * 18, seed) - 0.5) * 0.06
    if ribs:
        a = Q[:, rib_axis] / ribs
        f = a - np.floor(a)
        tone = np.where(f < 0.22, tone - 0.14, tone)
    return dict(pal=P['paper'], tone=tone)


def cloth(ctx, pal='indigo', seed=0, base=0.55, folds=0.12):
    Q = ctx.Q
    f = vnoise3(Q[:, 0] * 6, Q[:, 1] * 6, Q[:, 2] * 6, seed)
    tone = base + np.round((f - 0.5) * 3) / 3 * folds
    return dict(pal=P[pal], tone=tone)


def iron(ctx, seed=0, base=0.5, rust=0.4):
    X, Y, Z = ctx.P[:, 0], ctx.P[:, 1], ctx.P[:, 2]
    tone = base + (vnoise3(X * 30, Y * 30, Z * 30, seed) - 0.5) * 0.12
    r = fbm3(X * 12, Y * 12, Z * 12, 2, seed + 1) > 1 - rust * 0.5
    pal = np.where(r, P['rust'], P['iron'])
    return dict(pal=pal, tone=tone)


def moss_cushion(ctx, seed=0, base=0.52):
    X, Y, Z = ctx.P[:, 0], ctx.P[:, 1], ctx.P[:, 2]
    c = vnoise3(X * 14, Y * 14, Z * 14, seed)
    tone = base + (c - 0.5) * 0.3 + ctx.N[:, 1] * 0.1
    return dict(pal=P['moss'], tone=tone)


def flat(ctx, pal, tone=0.55, jitter=0.0, seed=0):
    t = np.full(ctx.n, float(tone))
    if jitter:
        t = t + (hash01(ipx(ctx.P[:, 0]), ipx(ctx.P[:, 2] - ctx.P[:, 1]), seed) - 0.5) * jitter
    return dict(pal=P[pal], tone=t)


def interior(ctx, base=0.25):
    """The dark inside of a doorway, niche or window: near-black with a faint warm floor bounce."""
    Y = ctx.P[:, 1]
    t = base + np.clip(0.4 - Y, 0, 0.4) * 0.3
    return dict(pal=P['dark'], tone=t, kb=0.0, kao=0.0)


def water(ctx, seed=0, base=0.45):
    X, Z = ctx.P[:, 0], ctx.P[:, 2]
    w = vnoise2(X * 12, Z * 30, seed)
    tone = base + np.where(w > 0.78, 0.25, 0.0) + (vnoise2(X * 4, Z * 4, seed + 1) - 0.5) * 0.08
    return dict(pal=P['water'], tone=tone)
