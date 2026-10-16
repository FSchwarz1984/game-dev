"""Sugi 杉 (Japanese cedar): tall, straight, a narrow cone of drooping tiers.

Each tier is a skirt of foliage masses around the trunk on short drooping branches; tiers shrink
toward a spire top. The leaf tile is a drooping skirt with a jagged fringe of points (the way pixel
art draws cedar layers), dark blue-green, its top edge lit by the sky. Bark: reddish-brown,
fibrous, in long vertical strips. Five variants from a young 9 m tree to a 26 m giant.
"""
from __future__ import annotations

import math

import numpy as np

from .. import cards as CD
from .. import foliage as FO
from .. import leaves as LV
from .. import trees as TR
from .. import wood as WD
from ..core import normalize, rng

SEED = 7101
NAME = 'sugi'

VARIANTS = [  # key, height, crown base, base radius (trunk), crown radius at base, lean (rad), seed
    ('a', 22.0, 6.5, 0.42, 3.2, 0.02, 1),
    ('b', 17.0, 4.8, 0.34, 2.7, -0.03, 2),
    ('c', 12.0, 2.6, 0.24, 2.2, 0.04, 3),
    ('d', 26.0, 8.0, 0.52, 3.6, -0.015, 4),
    ('e', 9.0, 1.6, 0.18, 1.8, 0.0, 5),
]


def tiles():
    S = SEED
    specs = {
        'mass': [(LV.sugi_spray, dict(W=int(16 + (i % 3) * 2), H=int(11 + (i % 2)), seed=S + i)) for i in range(9)],
        'small': [(LV.sugi_spray, dict(W=12, H=8, seed=S + 50 + i)) for i in range(4)],
        'interior': [(LV.sugi_spray, dict(W=18, H=12, seed=S + 80 + i)) for i in range(2)],
    }
    return FO.build_tiles(specs)


def variant(R, key, H, cb, r0, cr, lean, vseed):
    Rv = rng(SEED * 10 + vseed)
    top = np.array([math.sin(lean) * H * 0.4, H, Rv.normal(0, 0.15)])
    pts = [[0, -0.5, 0], [0, H * 0.3, 0], [top[0] * 0.5, H * 0.65, top[2] * 0.5], top.tolist()]
    trunk = WD.Limb('trunk', pts, [r0 * 1.15, r0 * 0.85, r0 * 0.5, 0.04], kind='trunk', n_around=12,
                    step_fn=lambda f: 0.6, moss=0.2,
                    rfun=lambda th, k, f, sp: sp.rad[k] * (1 + 0.25 * np.exp(-max(sp.pos[k, 1], 0) / 0.5)
                                                          * (1 + 0.3 * np.cos(4 * th + 0.5))))
    limbs = [trunk]
    masses = []
    # tiers
    h = cb
    tier = 0
    golden = math.pi * (3 - math.sqrt(5))
    az0 = Rv.uniform(0, 2 * math.pi)
    while h < H - 0.8:
        f = (h - cb) / max(H - cb, 1e-6)
        rad = cr * (1 - f) ** 0.85 + 0.35
        nb = 3 if rad < 1.2 else (4 if rad < 2.2 else 5)
        cx = top[0] * (h / H) ** 2 * 0.5
        for b in range(nb):
            az = az0 + tier * golden + b * 2 * math.pi / nb + Rv.normal(0, 0.25)
            d = np.array([math.cos(az), 0, math.sin(az)])
            reach = rad * Rv.uniform(0.75, 1.0)
            # short drooping branch carrying the mass
            if rad > 0.9 and tier % 2 == 0:
                b0 = np.array([cx, h, 0.0])
                b1 = b0 + d * reach * 0.6 + np.array([0, -0.25, 0])
                limbs.append(WD.Limb(f't{tier}b{b}', [b0, b0 + d * reach * 0.3 + [0, -0.05, 0], b1],
                                     [max(0.05, r0 * 0.25 * (1 - f)), 0.05, 0.03], kind='branch', n_around=5,
                                     step_fn=lambda f_: 0.6, moss=0.0))
            mc = np.array([cx, h - 0.15, 0.0]) + d * reach * 0.55
            masses.append(CD.Mass(mc, (reach * 0.62, 0.42 + 0.25 * (1 - f), reach * 0.5), yaw=-az, flat=0.2,
                                  seed=SEED + vseed * 1000 + tier * 10 + b, clumps=0.0, sag=0.5,
                                  tiles='mass', interior=rad > 1.2, lump=0.06))
        h += 0.85 + 0.25 * Rv.uniform() + 0.3 * (1 - f)
        tier += 1
    # the spire
    masses.append(CD.Mass(top + np.array([0, -0.7, 0]), (0.45, 0.9, 0.45), seed=SEED + vseed * 1000 + 999,
                          clumps=0.0, tiles='small', interior=False))
    crown_kw = dict(centre=(top[0] * 0.3, (cb + H) / 2, 0.0), radii=(cr, (H - cb) / 2, cr),
                    base_tint=TR.tint_for('#3d5e48'), young_tint=TR.tint_for('#526e48'), old_tint=TR.tint_for('#31504a'),
                    overlap=1.4, fill_density=1.0, clump_overlap=1.0, interior_frac=0.2, spray_rate=0.0,
                    env_k=0.55, up_bias=0.4, trunk_axis=(0.0, 0.0), flex_r=cr)
    cat = {'category': 'tree', 'species': 'sugi', 'footprint': [[0.0, 0.0, r0 * 1.3]], 'height': H,
           'crown': {'centre': [0.0, (cb + H) / 2, 0.0], 'radius': cr, 'base': cb}, 'tags': ['tree', 'conifer'],
           'anchors': {}, 'notes': f'杉 {H:.0f} m, crown from {cb:.1f} m.'}
    return limbs, masses, crown_kw, cat


def old_broken(R, var='a'):
    """An old cedar whose top a storm broke off long ago (the gates' trees, round 4b): a thick old
    trunk ending in a splintered break, side branches turned up into new leaders, small crowns on
    them, tufts sprouting from the trunk. Short on purpose: at the gates a 22-26 m cedar would cover
    everything 25-30 m north of it in the 3/4 view (the camphor, the graves); this one hides at most 11 m.
    Round 5 (G5R3-5: "其中有一颗他的顶冠的叶子是完全对称的……现实中怎么可能有这样完全对称的树"): no two
    leaders mirror each other. Variant 'a': one strong leader leaning with the wind and a short
    second one low on the other side, a dead snag above the break. Variant 'b': three leaders of
    unequal height fanned to one side, a long bleached dead limb, a heavy tuft low on the trunk.
    Tiers are uneven: sizes, gaps and sideways drift differ, some are missing."""
    Rv = rng(SEED * 10 + (77 if var == 'a' else 91))
    H = 7.2 if var == 'a' else 6.4
    r0 = 0.62 if var == 'a' else 0.58
    lean = np.array([0.18, 0.0, 0.05]) if var == 'a' else np.array([-0.12, 0.0, -0.08])
    pts = [[0, -0.5, 0], [0, 2.4, 0], (np.array([0.04, 4.8, 0.02]) + lean * 0.5).tolist(), (np.array([0.07, H, 0.04]) + lean).tolist()]
    trunk = WD.Limb('trunk', pts, [r0 * 1.2, r0 * 0.95, r0 * 0.82, r0 * 0.7], kind='trunk', n_around=12,
                    step_fn=lambda f: 0.6, moss=0.35, cap_end=True,
                    rfun=lambda th, k, f, sp: sp.rad[k] * (1 + 0.28 * np.exp(-max(sp.pos[k, 1], 0) / 0.6)
                                                          * (1 + 0.3 * np.cos(4 * th + 0.5)) + 0.04 * np.sin(7 * th + sp.pos[k, 1])))
    limbs = [trunk]
    top = np.array([0.07, H, 0.04]) + lean
    # the splintered break: wedges of different heights round the rim, one tall dead snag
    for k in range(6):
        a = k * 2 * math.pi / 6 + Rv.normal(0, 0.35)
        d = np.array([math.cos(a), 0, math.sin(a)])
        b0 = top + d * r0 * 0.55 + np.array([0, -0.12, 0])
        tall = 1.35 if (k == 2 and var == 'a') else Rv.uniform(0.2, 0.7)
        b1 = b0 + d * 0.05 + np.array([0, tall, 0])
        limbs.append(WD.Limb(f'sp{k}', [b0, b1], [0.1 if tall > 1 else 0.09, 0.012], kind='branch', n_around=4, step_fn=lambda f: 0.3))
    if var == 'a':
        # one strong leader east, leaning with the wind; a short one low on the west
        leaders = [((0.55, 5.4, 0.25), (1.35, 7.1, 0.5), (1.85, 9.6, 0.55), 1.0),
                   ((-0.45, 4.6, -0.3), (-1.15, 5.6, -0.65), (-1.3, 7.7, -0.8), 0.62)]
    else:
        # three leaders fanned to the north-west (the prevailing wind from the south-east)
        leaders = [((-0.5, 5.0, -0.15), (-1.25, 6.4, -0.55), (-1.55, 9.2, -0.95), 0.92),
                   ((0.2, 5.6, -0.45), (0.3, 6.9, -1.05), (0.15, 8.2, -1.55), 0.74),
                   ((0.45, 4.2, 0.2), (0.95, 5.1, 0.3), (1.05, 6.8, 0.1), 0.5)]
    masses = []
    for i, (a_, b_, c_, size) in enumerate(leaders):
        limbs.append(WD.Limb(f'ld{i}', [np.array([0.0, a_[1] - 0.2, 0.0]), a_, b_, c_], [0.24 * size + 0.04, 0.2 * size + 0.02, 0.13 * size, 0.04],
                             kind='branch', n_around=6, step_fn=lambda f: 0.5, moss=0.2))
        c = np.array(c_)
        # uneven tiers: each its own size, gap and sideways drift; now and then one missing
        n_t = int(Rv.integers(3, 5)) if size > 0.7 else 2
        yy = -2.0 * size
        for t in range(n_t):
            if t > 0 and Rv.uniform() < 0.22:
                yy += Rv.uniform(0.5, 0.9) * size
                continue
            rr = (1.4 - 0.28 * t) * size * Rv.uniform(0.75, 1.2)
            drift = np.array([Rv.normal(0, 0.25), 0, Rv.normal(0, 0.2)]) + lean * (t + 1) * 0.8
            masses.append(CD.Mass(c + np.array([0, yy, 0]) + drift, (rr, Rv.uniform(0.38, 0.6), rr * Rv.uniform(0.7, 0.95)),
                                  seed=SEED + 7700 + i * 10 + t + (0 if var == 'a' else 300), clumps=0.0, sag=0.5,
                                  tiles='mass' if rr > 0.5 else 'small', interior=rr > 1.0, lump=0.07))
            yy += Rv.uniform(0.55, 0.95) * size
    tufts = ((2.9, 0.6, 0.55), (3.6, 3.4, 0.5), (4.4, 5.0, 0.45)) if var == 'a' else ((2.2, 4.1, 0.85), (3.9, 1.2, 0.45))
    for i, (h, az, rr) in enumerate(tufts):
        d = np.array([math.cos(az), 0, math.sin(az)])
        masses.append(CD.Mass(np.array([0, h, 0]) + d * (r0 * 0.9 + 0.35), (rr, rr * 0.65, rr * 0.8), seed=SEED + 7800 + i + (0 if var == 'a' else 50),
                              clumps=0.0, sag=0.4, tiles='small', interior=False, lump=0.05))
    if var == 'a':
        limbs.append(WD.Limb('stub', [[0.0, 3.2, 0.0], [-0.8, 3.4, 0.35], [-1.2, 3.35, 0.5]], [0.12, 0.08, 0.04], kind='branch',
                             n_around=5, step_fn=lambda f: 0.4))
    else:
        # a long dead limb bleached by the weather, sticking out over the lane
        limbs.append(WD.Limb('dead', [[0.0, 4.9, 0.0], [0.9, 5.15, 0.55], [1.9, 5.05, 1.0], [2.6, 4.8, 1.25]], [0.14, 0.1, 0.06, 0.025],
                             kind='branch', n_around=5, step_fn=lambda f: 0.4))
        limbs.append(WD.Limb('stub', [[0.0, 2.7, 0.0], [0.55, 2.9, -0.5]], [0.1, 0.05], kind='branch', n_around=5, step_fn=lambda f: 0.4))
    top_y = max(c_[1] for _, _, c_, _ in leaders) + 0.4
    crown_kw = dict(centre=(float(lean[0] * 2), 7.2 if var == 'a' else 6.9, float(lean[2] * 2)), radii=(1.9, 2.6, 1.8),
                    base_tint=TR.tint_for('#3d5e48'), young_tint=TR.tint_for('#526e48'), old_tint=TR.tint_for('#31504a'),
                    overlap=1.4, fill_density=1.0, clump_overlap=1.0, interior_frac=0.2, spray_rate=0.0,
                    env_k=0.55, up_bias=0.4, trunk_axis=(0.0, 0.0), flex_r=1.8)
    cat = {'category': 'tree', 'species': 'furusugi', 'footprint': [[0.0, 0.0, r0 * 1.35]], 'height': round(top_y + 0.2, 2),
           'crown': {'centre': [0.0, top_y - 2.0, 0.0], 'radius': 1.9, 'base': 4.6}, 'tags': ['tree', 'conifer', 'old'],
           'anchors': {'rope': [0.0, 4.6, 0.0]},
           'notes': ('An old cedar broken long ago; ' + ('one strong leader leaning east to 9.6 m, a short one low on the west, a dead snag. '
                     if var == 'a' else 'three unequal leaders fanned north-west, a long bleached dead limb. ') +
                     'The gates\' trees (the michikiri rope is tied round it at 4.6 m).')}
    return limbs, masses, crown_kw, cat


def bark(seed):
    return WD.bark_texture(seed, spacing=(2, 4), ridge=('#5b392b', '#6a4532', '#7a5039'), lip='#8a5c42',
                           fissure='#3a241c', deep='#2a1b16', lichen=('#7e8466', '#8e9474'), lichen_p=0.0008,
                           moss=('#4c5a33',), moss_p=0.0005, break_p=0.01, wave=(1.2, 0.6), merge_p=0.15)


def build(out):
    R = rng(SEED)
    a = out.asset(NAME, 'trees')
    bark_res = a.texture('bark', bark(SEED))
    m_bark = a.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 1.0},
                        textures={'albedo_tex': bark_res})
    atlas, rects, sets = tiles()
    leaf_res = a.texture('leaves', atlas)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=1.0),
                        textures={'leaf_tex': leaf_res})
    stats = {}
    for key, H, cb, r0, cr, lean, vs in VARIANTS:
        limbs, masses, crown_kw, cat = variant(R, key, H, cb, r0, cr, lean, vs)
        stats[key] = TR.build_variant(a, key, limbs, masses, (atlas, rects), sets, crown_kw, m_bark, m_leaf, cat,
                                      colour_fn=TR.default_colour(), seed=SEED + vs)
    # the gates' old broken cedar: its own asset (furusugi_a, placement kind 'furusugi'), so the random
    # cedars never pick it
    b = out.asset('furusugi', 'trees')
    b_bark = b.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 1.0},
                        textures={'albedo_tex': b.texture('bark', bark(SEED + 1))})
    b_leaf = b.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=1.0),
                        textures={'leaf_tex': b.texture('leaves', atlas)})
    for var in ('a', 'b'):
        limbs, masses, crown_kw, cat = old_broken(R, var)
        stats['old_' + var] = TR.build_variant(b, var, limbs, masses, (atlas, rects), sets, crown_kw, b_bark, b_leaf, cat,
                                               colour_fn=TR.default_colour(), seed=SEED + (77 if var == 'a' else 91))
    return stats
