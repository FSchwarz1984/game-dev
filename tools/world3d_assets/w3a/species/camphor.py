"""The giant camphor 御神木: the hero of the art sample.

Scale (lead's brief): crown spread about 34 m (radius ~17), crown base 6-8 m, top 20-22 m; trunk
about 6.5 m across, gnarled and twisting, burls and deep furrows; buttress roots spreading to
~9.5 m and sinking into the ground; massive low limbs reaching out 14-17 m with moss and small
ferns on them; a shimenawa with shide around the trunk (the only "cannot take" marker).

One organism: the limbs grow out of the trunk, the branches out of the limbs and into the leaf
masses they carry; the lowest masses hang on the limb ends, so the crown's lower edge shows the
limbs going in. Budget (contract 2): <= 20k triangles for the great camphor.
"""
from __future__ import annotations

import math

import numpy as np

from .. import cards as CD
from .. import foliage as FO
from .. import leaves as LV
from .. import wood as WD
from ..core import PPM, TEXEL_PER_M, hex_rgb, normalize, rng
from ..mesh import MeshData
from ..tube import Spine, tube

SEED = 7001
NAME = 'camphor_great'

# ------------------------------------------------------------------------------- the trunk
BUTTRESS = [  # angle (rad, 0 = north, pi/2 = west, pi = south, 3pi/2 = east), reach at ground (m), width
    (0.35, 1.55, 0.22), (1.25, 1.35, 0.26), (2.05, 1.65, 0.20), (2.75, 1.15, 0.24),
    (3.55, 1.70, 0.21), (4.35, 1.30, 0.25), (5.15, 1.60, 0.22), (5.85, 0.95, 0.20),
]
BURLS = [  # angle, height (m), amplitude (m), angular width, vertical width
    (2.55, 2.9, 0.42, 0.30, 0.7), (3.95, 1.9, 0.30, 0.25, 0.55), (1.6, 3.6, 0.36, 0.28, 0.6),
    (4.9, 3.2, 0.28, 0.22, 0.5), (3.2, 4.3, 0.22, 0.20, 0.45),
]
HOLLOW_AT = (2.42, 0.62, 0.70, 0.30, 0.78)   # angle, centre height, depth, angular half-width, half-height
TWIST = 0.11                                  # rad per metre
ROPE_Y = 2.35                                 # shimenawa height


def _angdiff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def _theta(x, z):
    """Ring angle of a direction (0 = north, pi/2 = west), as the tube frames use for the trunk."""
    t = np.arctan2(-x, -z)
    return np.where(t < 0, t + 2 * math.pi, t)


def trunk_radius(theta, y, r0):
    theta = np.asarray(theta, np.float64)
    th = theta + TWIST * y
    r = r0 * (1 + 0.055 * np.sin(5 * th + 0.7) + 0.035 * np.sin(3 * th + 2.1) + 0.02 * np.sin(11 * th + 0.3))
    g = math.exp(-max(y, 0) / 1.25) * (1 if y > -0.4 else math.exp((y + 0.4) * 0.8))
    for a, reach, w in BUTTRESS:
        d = _angdiff(theta, a)
        r = r + reach * np.exp(-(d / w) ** 2) * g
    r = r + 0.45 * g
    for a, h, amp, wa, wh in BURLS:
        d = _angdiff(th, a)
        r = r + amp * np.exp(-(d / wa) ** 2 - ((y - h) / wh) ** 2)
    a, h, depth, wa, wh = HOLLOW_AT
    d = _angdiff(theta, a)
    r = r - depth * np.exp(-(d / wa) ** 4 - ((y - h) / wh) ** 4)
    r = r * (1 - 0.02 * np.abs(np.sin(17 * th + 0.4 * math.sin(y * 1.3))))
    return r


def trunk_rfun(theta, k, frac, spine):
    return trunk_radius(theta, float(spine.pos[k, 1]), float(spine.rad[k]))


TRUNK_PTS = [[0, -0.9, 0], [0.05, 0.6, 0.05], [0.25, 2.4, -0.05], [0.4, 4.2, -0.15], [0.35, 5.6, -0.25]]
TRUNK_R = [3.15, 3.05, 2.85, 2.6, 2.3]


def skeleton(R):
    limbs = []
    trunk = WD.Limb('trunk', TRUNK_PTS, TRUNK_R, kind='trunk', rfun=trunk_rfun, n_around=64, step=0.32,
                    cap_end=False, moss=0.35)
    limbs.append(trunk)
    main = [  # name, control points, radii, moss
        ('E', [[0.9, 4.3, 0.35], [4.6, 5.5, 1.1], [8.6, 6.1, 2.3], [12.1, 7.1, 3.1], [14.9, 8.4, 3.3], [16.3, 9.7, 2.9]], [1.35, 1.05, 0.8, 0.55, 0.36, 0.2], 0.7),
        ('W', [[-1.0, 4.1, 0.45], [-4.9, 5.2, 1.6], [-9.1, 5.8, 3.0], [-12.7, 6.9, 3.6], [-15.3, 8.4, 3.2], [-16.5, 9.7, 2.6]], [1.4, 1.1, 0.82, 0.56, 0.36, 0.2], 0.7),
        ('S', [[0.2, 4.7, 1.0], [0.9, 6.9, 4.5], [1.8, 8.4, 8.5], [1.2, 9.8, 12.0], [0.4, 10.8, 14.2]], [1.12, 0.86, 0.6, 0.38, 0.22], 0.6),
        ('NW', [[-0.6, 4.9, -0.7], [-3.5, 7.7, -4.5], [-6.5, 9.9, -8.6], [-8.6, 11.9, -11.6]], [1.2, 0.9, 0.6, 0.34], 0.5),
        ('NE', [[0.7, 4.9, -0.6], [4.0, 7.9, -4.0], [7.5, 10.4, -8.1], [9.6, 12.4, -10.6]], [1.15, 0.86, 0.56, 0.3], 0.5),
        ('L', [[0.1, 5.0, -0.1], [-0.4, 8.8, -0.8], [0.6, 12.8, -1.5], [0.2, 16.4, -2.0], [-0.3, 18.6, -2.2]], [1.32, 0.96, 0.6, 0.32, 0.18], 0.3),
        ('SEu', [[-0.1, 8.4, -0.6], [3.5, 11.4, 2.0], [7.0, 13.4, 3.0], [9.1, 14.4, 2.6]], [0.62, 0.46, 0.3, 0.18], 0.25),
        ('SWu', [[0.0, 9.8, -0.9], [-4.0, 12.7, 1.5], [-7.5, 14.4, 2.6], [-9.1, 15.1, 2.2]], [0.56, 0.42, 0.28, 0.16], 0.25),
    ]
    named = {}
    for name, pts, rr, moss in main:
        L = WD.Limb(name, pts, rr, kind='limb', moss=moss, n_around=12 if rr[0] > 1.0 else 9, step=0.7)
        limbs.append(L)
        named[name] = L
    # surface roots: out of the buttresses, along the ground, diving in
    for i, (a, reach, w) in enumerate(BUTTRESS):
        d = np.array([-math.sin(a), 0, -math.cos(a)])          # theta 0 = north (-z), pi/2 = west (-x)
        L1 = R.uniform(3.2, 5.6) + reach
        side = np.array([d[2], 0, -d[0]]) * R.normal(0, 0.6)
        pts = [d * 2.2 + [0, 0.65, 0], d * 3.6 + [0, 0.35, 0] + side * 0.2, d * (3.6 + L1 * 0.45) + [0, 0.12, 0] + side * 0.6,
               d * (3.6 + L1 * 0.8) + [0, -0.05, 0] + side, d * (3.6 + L1) + [0, -0.35, 0] + side * 1.2]
        rr = [0.62, 0.5, 0.34, 0.22, 0.12]
        limbs.append(WD.Limb(f'root{i}', pts, rr, kind='root', step=0.45, n_around=9, moss=0.45,
                             yscale=lambda k, f: 0.85 - 0.3 * f))
    return limbs, named


# ------------------------------------------------------------------------------- the crown
def masses():
    """Three tiers, the way old camphors hold their foliage: broad shelves on the long low limbs,
    a mid layer, a high dome; small fringe masses break the outline."""
    M = []

    def add(c, r, **kw):
        kw.setdefault('seed', len(M) * 31 + 5)
        M.append(CD.Mass(c, r, **kw))
    # tier A: shelves on the low limbs (8-11 m), flat, drooping at the rim
    add((13.4, 9.4, 3.2), (5.0, 2.2, 4.8), flat=0.65, sag=0.5)          # E
    add((-13.8, 9.2, 3.0), (5.2, 2.2, 4.8), flat=0.65, sag=0.5)         # W
    add((1.2, 10.6, 12.2), (5.4, 2.2, 3.8), flat=0.65, sag=0.45)        # S, over the home
    add((8.0, 9.7, 8.0), (3.4, 1.8, 3.0), flat=0.6, sag=0.3)            # SE
    add((-7.6, 9.4, 8.2), (3.6, 1.8, 3.2), flat=0.6, sag=0.3)           # SW
    add((-8.8, 11.0, -9.0), (4.8, 2.4, 4.6), flat=0.6, sag=0.35)        # NW
    add((9.2, 11.4, -8.6), (4.8, 2.4, 4.6), flat=0.6, sag=0.35)         # NE
    # tier B: the middle (11-15 m)
    add((-6.5, 13.2, 3.0), (5.0, 2.6, 4.6), flat=0.5)
    add((6.8, 13.4, 2.4), (5.2, 2.6, 4.6), flat=0.5)
    add((0.5, 13.6, -6.8), (6.2, 2.8, 4.8), flat=0.5)
    add((-1.0, 12.6, 6.4), (4.4, 2.4, 3.6), flat=0.5)
    # tier C: the dome (15-21 m)
    add((-1.0, 17.4, -1.4), (6.4, 3.4, 5.6), flat=0.4, clumps=0.55)
    add((4.6, 16.0, 1.6), (4.2, 2.8, 4.0), flat=0.4)
    add((-5.8, 15.6, -3.6), (4.0, 2.6, 3.8), flat=0.4)
    # fringe: outline breakers
    add((16.6, 9.0, 0.0), (2.4, 1.6, 2.4), flat=0.5, clumps=0.3)
    add((-17.0, 8.8, 0.4), (2.3, 1.5, 2.3), flat=0.5, clumps=0.3)
    add((2.0, 20.8, -2.4), (2.6, 1.6, 2.4), flat=0.4, clumps=0.3)
    add((-3.6, 10.0, 14.2), (2.2, 1.4, 2.0), flat=0.5, clumps=0.2, sag=0.4)
    return M


def fern_tile(W, seed):
    """ノキシノブ: a tuft of strap-shaped fronds fanning up from a point."""
    R = rng(seed)
    H = W
    val = np.zeros((H, W))
    cov = np.zeros((H, W), bool)
    base = (W * 0.5, H * 0.92)
    for k in range(int(R.integers(4, 7))):
        a = -math.pi / 2 + R.normal(0, 0.75)
        L = R.uniform(H * 0.5, H * 0.85)
        m, uu = LV._leaf_mask(H, W, base[0] + math.cos(a) * L * 0.5, base[1] + math.sin(a) * L * 0.5, a, L, R.uniform(1.6, 2.2))
        val[m] = np.where(uu[m] > 0.3, LV.TOP, LV.BODY)
        cov |= m
    return LV._finish(val, cov)


def leaf_tiles():
    S = SEED
    specs = {
        'mass': [(LV.clumps, dict(W=22, seed=S + 100 + i, r=(1.6, 3.0), gloss=0.3, tips=7, fill=2.2)) for i in range(10)],
        'small': [(LV.clumps, dict(W=15, seed=S + 200 + i, r=(1.5, 2.6), gloss=0.3, tips=5, shape=0.40)) for i in range(5)],
        'interior': [(LV.clumps, dict(W=22, seed=S + 300 + i, r=(2.2, 3.4), gloss=0.0, tips=2, shape=0.44, ragged=0.1, top_p=0.3)) for i in range(2)],
        'fern': [(fern_tile, dict(W=12, seed=S + 500 + i)) for i in range(3)],
        'moss': [(LV.clumps, dict(W=9, seed=S + 600 + i, r=(1.2, 2.0), gloss=0.0, tips=2, shape=0.42, aspect=0.6, top_p=0.6)) for i in range(2)],
    }
    for d in range(8):
        specs[f'spray{d}'] = [(LV.spray, dict(W=18, seed=S + 400 + d * 10, direction=-d * math.pi / 4, n_twigs=3,
                                               gloss=0.15, reach=0.46))]
    return FO.build_tiles(specs)


def _tint(hexcol, body=LV.BODY):
    """The card tint that makes the tile's BODY tone come out as hexcol."""
    c = np.array(hex_rgb(hexcol), np.float64) / 255.0
    return np.clip(c / body, 0, 1)


def crown(M, sets):
    return CD.crown_cards(M, (0.0, 12.5, 0.5), (17.0, 7.0, 15.5), sets, seed=SEED + 9,
                          base_tint=_tint('#5b7340'), young_tint=_tint('#687a40'), old_tint=_tint('#4d6740'),
                          base_y=7.0, top_y=21.0, overlap=1.7, clump_overlap=1.9, fill_density=0.45,
                          max_cards=4300)


def epiphytes(R, named, sets):
    """Ferns and moss cushions on the tops of the big low limbs (cards, normal up)."""
    out = []
    for key, n_f, n_m in (('E', 9, 10), ('W', 9, 10), ('S', 6, 7), ('NW', 4, 5), ('NE', 4, 5)):
        sp = named[key].spine
        for i in range(n_f + n_m):
            f = R.uniform(0.08, 0.75)
            p, t, r = sp.point_at(f)
            side = normalize(np.cross(t, [0, 1, 0]) + 1e-6)
            top = p + side * R.normal(0, r * 0.35) + np.array([0, r * 0.92, 0])
            is_fern = i < n_f
            lst = sets['fern' if is_fern else 'moss']
            tl = lst[R.integers(0, len(lst))]
            tint = _tint('#5f7a3c') if is_fern else _tint('#4f6232')
            pos = top + np.array([0, tl[2] / PPM * 0.35, 0]) if is_fern else top
            out.append(CD.Card(pos, normalize(np.array([0.0, 1.0, 0.25])), tl[1], tl[2], tl[0], 0.95,
                               np.clip(tint * (1 + R.normal(0, 0.03)), 0, 1), 0.15 if is_fern else 0.0, 'epi', 2.0))
    return out


# ------------------------------------------------------------------------------- wood colour, ao, moss
def wood_colour(P, N, L):
    y = P[:, 1]
    col = np.ones((len(P), 3))
    g = np.clip((0.55 - y) / 0.7, 0, 1)[:, None]                      # earth at the foot
    col = col * (1 - g) + np.array([0.80, 0.74, 0.64]) * g
    damp = np.clip(-N[:, 2] * 0.7 + 0.3, 0, 1) * np.clip(1.4 - y / 4.0, 0, 1)
    if L.kind == 'limb':
        damp = damp * 0.5 + np.clip(N[:, 1], 0, 1) * 0.35
    col = col * (1 - 0.35 * damp[:, None]) + np.array([0.78, 0.86, 0.70]) * 0.35 * damp[:, None]
    hi = np.clip((y - 8.0) / 8.0, 0, 1)[:, None]                      # high branches paler
    col = col * (1 - hi * 0.3) + np.array([1.06, 1.04, 1.02]) * hi * 0.3
    return col


def wood_ao(P, N, L):
    y = P[:, 1]
    ao = np.ones(len(P))
    if L.kind == 'trunk':
        th = _theta(P[:, 0], P[:, 2])
        fin = np.zeros(len(P))
        for a, reach, w in BUTTRESS:
            fin = np.maximum(fin, np.exp(-(_angdiff(th, a) / (w * 1.6)) ** 2))
        low = np.exp(-np.maximum(y, 0) / 1.4)
        ao -= 0.38 * (1 - fin) * low                                    # folds between the fins
        a, h, depth, wa, wh = HOLLOW_AT
        hk = np.exp(-(_angdiff(th, a) / (wa * 0.9)) ** 4 - ((y - h) / (wh * 0.9)) ** 4)
        ao -= 0.6 * hk                                                  # the hollow
        ao -= 0.3 * np.clip((y - 4.3) / 1.2, 0, 1)                      # the crotch
    if L.kind in ('limb', 'branch'):
        ao -= 0.18 * np.clip(-N[:, 1], 0, 1)
        f = np.linalg.norm(P[:, [0, 2]], axis=1)
        ao -= 0.25 * np.clip(1 - f / 3.5, 0, 1) * np.clip(-N[:, 1] + 0.5, 0, 1)
    if L.kind == 'root':
        ao -= 0.25 * np.clip(0.4 - y, 0, 1)
    return np.clip(ao, 0.2, 1)


def wood_moss(P, N, L):
    if L.kind == 'trunk':
        return np.clip(0.25 + 0.5 * np.clip((P[:, 1] - 4.0) / 1.5, 0, 1) + 0.3 * np.clip(-N[:, 2], 0, 1), 0, 1)
    return np.full(len(P), L.moss)


# ------------------------------------------------------------------------------- the shimenawa
def _tube_uv(info, n_rows, u_scale=0.5, v_div=32.0):
    """uv for a tube made by tube(): u around (0..u_scale), v along (texels / v_div)."""
    k = info['P'].shape[1]
    m = info['P'].shape[0]
    U = info['U'] / np.maximum(info['U'][:, -1:], 1e-6) * u_scale
    V = info['V'] * TEXEL_PER_M / v_div
    uv = np.stack([U.reshape(-1), V.reshape(-1)], axis=1)
    extra = n_rows - m * k
    if extra > 0:
        uv = np.vstack([uv, np.tile([u_scale * 0.5, V.max()], (extra, 1))])
    return uv


def shimenawa(trunk):
    """A thick twisted straw rope around the trunk at ROPE_Y following its surface, sagging a little
    in front, with a bundled knot and shide (zigzag paper) hanging in front."""
    sp = trunk.spine
    k = int(np.argmin(np.abs(sp.pos[:, 1] - ROPE_Y)))
    c = sp.pos[k]
    r0 = float(sp.rad[k])
    rope_r = 0.17
    th = np.linspace(0, 2 * math.pi, 73)
    pts = []
    for t in th:
        rr = float(trunk_radius(np.array([t]), ROPE_Y, r0)[0]) + rope_r * 0.85
        d = np.array([-math.sin(t), 0, -math.cos(t)])
        sag = 0.22 * max(0.0, -math.cos(t)) ** 2
        pts.append(c + d * rr + np.array([0, -sag, 0]))
    spine = Spine(pts, [rope_r] * len(pts), step=0.12)
    md, info = tube(spine, n_around=8, cap_end=False)
    a = md.arrays()
    rope = MeshData()
    rope.add(a['p'], a['n'], _tube_uv(info, len(a['p'])), a['idx'], uv2=np.tile([0.0, 0.0], (len(a['p']), 1)),
             col=np.ones((len(a['p']), 4)))
    front_r = float(trunk_radius(np.array([math.pi]), ROPE_Y, r0)[0])
    knot_c = c + np.array([0, -0.24, front_r + rope_r * 1.5])
    for dx, Ln in ((-0.22, 0.55), (0.18, 0.72)):                         # two tails hanging
        s2 = Spine([knot_c + [dx, 0.05, 0.02], knot_c + [dx * 1.3, -Ln * 0.5, 0.08], knot_c + [dx * 1.5, -Ln, 0.12]],
                   [0.11, 0.09, 0.05], step=0.1)
        m2, i2 = tube(s2, n_around=6, cap_end=True)
        a2 = m2.arrays()
        rope.add(a2['p'], a2['n'], _tube_uv(i2, len(a2['p'])), a2['idx'], uv2=np.zeros((len(a2['p']), 2)),
                 col=np.ones((len(a2['p']), 4)))
    s3 = Spine([knot_c + [-0.34, 0.0, -0.06], knot_c + [0.0, 0.03, 0.06], knot_c + [0.34, 0.0, -0.06]],
               [0.2, 0.25, 0.2], step=0.08)                              # the bundle
    m3, i3 = tube(s3, n_around=8, cap_end=True, cap_start=True)
    a3 = m3.arrays()
    rope.add(a3['p'], a3['n'], _tube_uv(i3, len(a3['p'])), a3['idx'], uv2=np.zeros((len(a3['p']), 2)),
             col=np.ones((len(a3['p']), 4)))
    shide = MeshData()
    for ang in (math.pi - 0.62, math.pi - 0.31, math.pi + 0.31, math.pi + 0.62):
        rr = float(trunk_radius(np.array([ang]), ROPE_Y, r0)[0]) + rope_r * 1.4
        d = np.array([-math.sin(ang), 0, -math.cos(ang)])
        sag = 0.22 * max(0.0, -math.cos(ang)) ** 2
        shide.merge(zigzag(c + d * rr + np.array([0, -sag - rope_r * 0.6, 0]), d))
    for side in (-1, 1):
        shide.merge(zigzag(knot_c + np.array([side * 0.48, -0.16, 0.05]), np.array([0.0, 0.0, 1.0])))
    return rope, shide


def zigzag(top, facing, width=0.2, seg=0.16, n=4, thick=0.02):
    """A shide: a paper strip cut and folded into n steps zigzagging down; both sides drawn."""
    facing = normalize(np.asarray(facing, np.float64) * np.array([1, 0, 1]))
    right = normalize(np.cross([0, 1, 0], facing))
    pts, nrm, tri = [], [], []
    for i in range(n):
        x0 = (width * 0.45 if i % 2 else 0.0) - width * 0.25
        a = top + right * x0 + np.array([0, -i * seg, 0]) + facing * thick * (i % 2)
        quad = [a, a + right * width * 0.62, a + right * width * 0.62 + np.array([0, -seg, 0]), a + np.array([0, -seg, 0])]
        for sgn in (1, -1):
            b = len(pts)
            for q in quad:
                pts.append(q + facing * 0.004 * sgn)
                nrm.append(facing * sgn)
            t1, t2 = (b, b + 1, b + 2), (b, b + 2, b + 3)
            pa, pb, pc = (np.array(pts[t]) for t in t1)
            if np.dot(np.cross(pb - pa, pc - pa), facing * sgn) < 0:
                t1, t2 = (b, b + 2, b + 1), (b, b + 3, b + 2)
            tri += [t1, t2]
    md = MeshData()
    k = len(pts)
    md.add(np.array(pts), np.array(nrm), np.zeros((k, 2)), np.array(tri), uv2=np.tile([6.0, 0.0], (k, 1)),
           col=np.tile([0.95, 0.94, 0.90, 1.0], (k, 1)))
    return md


def rope_texture(seed=SEED):
    """Twisted straw: diagonal strands, 32 x 32, tiles both ways."""
    R = rng(seed)
    S = 32
    ys, xs = np.mgrid[0:S, 0:S]
    pal = [np.array(hex_rgb(h), np.float64) for h in ('#7e6a43', '#a08a58', '#bba56c', '#cdb87e')]
    strand = ((xs * 2 + ys) // 6) % 4
    v = np.select([strand == 0, strand == 1, strand == 2, strand == 3], [1, 2, 3, 2])
    v = np.where(((xs * 2 + ys) % 6) == 0, 0, v)
    v = np.where((R.uniform(size=(S, S)) < 0.08) & (v > 0), v - 1, v)
    img = np.zeros((S, S, 3))
    for i in range(4):
        img[v == i] = pal[i]
    return img.astype(np.uint8)


# ------------------------------------------------------------------------------- build
def build(out):
    R = rng(SEED)
    limbs, named = skeleton(R)
    for key, n, fr, ln in (('E', 4, (0.55, 0.95), (2.4, 4.0)), ('W', 4, (0.55, 0.95), (2.4, 4.0)),
                           ('S', 3, (0.5, 0.9), (2.0, 3.4)), ('NW', 3, (0.5, 0.9), (2.4, 3.8)),
                           ('NE', 3, (0.5, 0.9), (2.4, 3.8)), ('L', 4, (0.45, 0.9), (2.4, 4.4)),
                           ('SEu', 2, (0.5, 0.9), (2.0, 3.2)), ('SWu', 2, (0.5, 0.9), (2.0, 3.2))):
        L = named[key]
        WD.build_limb(L)
        for b in WD.offshoots(L, R, n, frac_range=fr, length=ln, radius_k=(0.4, 0.6), up_bias=0.45, name=key + 'b',
                              min_r=0.06, moss=0.15, segs=3):
            b.n_around = 6
            b.step = 0.8
            limbs.append(b)
    for L in limbs:
        if L.spine is None:
            WD.build_limb(L)
    a = out.asset(NAME, 'trees')
    bark_res = a.texture('bark', WD.bark_texture(SEED, size=256))
    m_bark = a.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 1.0, 'cutaway': True},
                        textures={'albedo_tex': bark_res})
    wood = WD.wood_mesh(limbs, tex_size=256, colour_fn=wood_colour, ao_fn=wood_ao, moss_fn=wood_moss)
    rope, shide = shimenawa(limbs[0])
    rope_res = a.texture('rope', rope_texture())
    m_rope = a.material('rope', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 1.0},
                        textures={'albedo_tex': rope_res})
    m_paper = a.material('shide', 'toon_solid.gdshader', params={'porosity': 0.6})
    atlas, rects, sets = leaf_tiles()
    cards = crown(masses(), sets) + epiphytes(R, named, sets)
    leaf_md = CD.cards_mesh(cards, atlas.shape[1], atlas.shape[0], rects)
    leaf_res = a.texture('leaves', atlas)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=1.0),
                        textures={'leaf_tex': leaf_res})
    wood_mesh = a.mesh('wood', [(m_bark, wood), (m_rope, rope), (m_paper, shide)])
    leaf_mesh = a.mesh('leaves', [(m_leaf, leaf_md)], custom_aabb=[[-20, 4, -20], [40, 20, 40]])
    a.scene([
        {'name': 'Wood', 'type': 'mesh', 'mesh': wood_mesh},
        {'name': 'Leaves', 'type': 'mesh', 'mesh': leaf_mesh, 'extra_cull_margin': 4.0},
    ], meta={'w3a_kind': 'tree', 'w3a_species': 'camphor'})
    a.catalog = {
        'category': 'tree',
        'footprint': [[0.0, 0.0, 3.3], [3.4, 0.4, 1.0], [-3.4, 0.2, 1.0], [0.3, 3.4, 1.0], [-0.3, -3.4, 1.0]],
        'height': 21.5,
        'crown': {'centre': [0.0, 13.0, 0.5], 'radius': 17.0, 'base': 7.0},
        'tags': ['landmark', 'climbable', 'sacred'],
        'anchors': {'shimenawa_front': [0.0, ROPE_Y - 0.2, 3.3]},
        'notes': '御神木. Trunk 6.5 m across, buttresses to ~9.5 m, low limbs reach 16.5 m. Shimenawa at %.2f m.' % ROPE_Y,
    }
    nt = len(wood.arrays()['idx']) + len(rope.arrays()['idx']) + len(shide.arrays()['idx'])
    return {'cards': len(cards), 'wood_tris': nt, 'leaf_tris': len(cards) * 2, 'atlas': list(atlas.shape[:2])}
