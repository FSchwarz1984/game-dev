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
    return stats
