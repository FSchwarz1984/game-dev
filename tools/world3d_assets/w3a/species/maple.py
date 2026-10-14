"""Iroha-momiji イロハモミジ (Japanese maple): a small multi-stemmed tree, smooth grey bark, branches
spreading in airy horizontal layers of small star leaves. Summer green (three variants) and a red
one for accents (two variants; the same tiles, tinted).
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

SEED = 7301
NAME = 'maple'

GREEN = ('#6b8a43', '#7e9a49', '#58773f')
RED = ('#a8452e', '#bd5a34', '#8a3528')
VARIANTS = [  # key, height, stems, spread, palette, seed
    ('a', 7.0, 3, 4.2, GREEN, 1),
    ('b', 5.5, 2, 3.4, GREEN, 2),
    ('c', 8.0, 3, 4.8, GREEN, 3),
    ('red_a', 6.5, 2, 4.0, RED, 4),
    ('red_b', 5.0, 3, 3.2, RED, 5),
]


def tiles():
    S = SEED
    specs = {
        'mass': [(LV.star_leaves, dict(W=int(16 + (i % 3) * 3), H=int(12 + (i % 2) * 3), seed=S + i)) for i in range(10)],
        'small': [(LV.star_leaves, dict(W=12, H=10, seed=S + 50 + i, airy=0.5)) for i in range(4)],
        'interior': [(LV.star_leaves, dict(W=16, H=12, seed=S + 80 + i, airy=0.6)) for i in range(2)],
    }
    return FO.build_tiles(specs)


def variant(key, H, stems, spread, pal, vs):
    R = rng(SEED * 10 + vs)
    limbs = []
    masses = []
    az0 = R.uniform(0, 2 * math.pi)
    for s in range(stems):
        az = az0 + s * 2 * math.pi / stems + R.normal(0, 0.3)
        d = np.array([math.cos(az) * 0.35, 1.0, math.sin(az) * 0.35])
        L = H * R.uniform(0.62, 0.8)
        path = TR.wander(R, [math.cos(az) * 0.08, -0.3, math.sin(az) * 0.08], d, L, 4, bend=0.16, up=0.0)
        r0 = 0.11 + 0.03 * (stems == 2)
        stem = WD.Limb(f's{s}', path, [r0 * 1.2, r0, r0 * 0.7, r0 * 0.45, 0.04], kind='trunk', n_around=7,
                       step_fn=lambda f: 0.5, moss=0.15)
        WD.build_limb(stem)
        limbs.append(stem)
        # layered side branches with flat foliage layers
        for k in range(3):
            f = 0.35 + 0.22 * k + R.normal(0, 0.04)
            p0, t0, rr = stem.spine.point_at(min(f, 0.95))
            baz = az + R.normal(0, 0.7) + (k - 1) * 0.9
            bd = np.array([math.cos(baz), 0.15, math.sin(baz)])
            bl = spread * R.uniform(0.35, 0.55) * (1.1 - 0.2 * k)
            bp = TR.wander(R, p0, bd, bl, 2, bend=0.15, up=0.05)
            limbs.append(WD.Limb(f's{s}b{k}', bp, [rr * 0.6, rr * 0.4, 0.03], kind='branch', n_around=5,
                                 step_fn=lambda f_: 0.5))
            lr = bl * R.uniform(0.75, 1.0)
            masses.append(CD.Mass(bp[-1] + np.array([0, 0.15, 0]), (lr, 0.45, lr * 0.85), yaw=-baz, flat=0.7,
                                  seed=SEED + vs * 100 + s * 10 + k, clumps=0.0, tiles='mass', interior=False, lump=0.1))
        top = stem.spine.pos[-1]
        masses.append(CD.Mass(top + np.array([0, 0.1, 0]), (spread * 0.32, 0.55, spread * 0.3), flat=0.7,
                              seed=SEED + vs * 100 + s * 10 + 9, clumps=0.0, tiles='mass', interior=False))
    cc = np.mean([m.c for m in masses], axis=0)
    span = max(np.max([np.linalg.norm((m.c - cc)[[0, 2]]) + m.r[0] for m in masses]), 1.5)
    crown_kw = dict(centre=tuple(cc), radii=(span, H * 0.3, span),
                    base_tint=TR.tint_for(pal[0]), young_tint=TR.tint_for(pal[1]), old_tint=TR.tint_for(pal[2]),
                    overlap=1.2, fill_density=1.0, clump_overlap=1.0, interior_frac=0.0, spray_rate=0.0,
                    env_k=0.3, up_bias=0.45, flex_r=span, max_cards=480)
    cat = {'category': 'tree', 'species': 'japanese maple' + (' (red)' if pal is RED else ''),
           'footprint': [[0.0, 0.0, 0.35]], 'height': H,
           'crown': {'centre': [float(cc[0]), float(cc[1]), float(cc[2])], 'radius': float(span), 'base': float(H * 0.35)},
           'tags': ['tree', 'accent' if pal is RED else 'broadleaf'], 'anchors': {},
           'notes': 'イロハモミジ, ' + ('red (accent)' if pal is RED else 'summer green')}
    return limbs, masses, crown_kw, cat


def bark(seed):
    """Smooth grey maple bark: soft tone patches, faint vertical streaks, a few lenticels."""
    return WD.bark_texture(seed, spacing=(6, 11), ridge=('#8a8a80', '#94948a', '#9e9e92'), lip='#a6a69a',
                           fissure='#7a7a70', deep='#6e6e66', lichen=('#a9ab94', '#b6b8a0'), lichen_p=0.002,
                           moss=('#6a7a4a',), moss_p=0.0004, break_p=0.02, wave=(0.8, 0.4), merge_p=0.6)


def build(out):
    a = out.asset(NAME, 'trees')
    bark_res = a.texture('bark', bark(SEED))
    m_bark = a.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 0.8},
                        textures={'albedo_tex': bark_res})
    atlas, rects, sets = tiles()
    leaf_res = a.texture('leaves', atlas)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=1.5),
                        textures={'leaf_tex': leaf_res})
    stats = {}
    for key, H, stems, spread, pal, vs in VARIANTS:
        limbs, masses, crown_kw, cat = variant(key, H, stems, spread, pal, vs)
        stats[key] = TR.build_variant(a, key, limbs, masses, (atlas, rects), sets, crown_kw, m_bark, m_leaf, cat,
                                      colour_fn=TR.default_colour(), seed=SEED + vs)
    return stats
