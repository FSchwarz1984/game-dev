"""Kaki 柿 (persimmon): a crooked dark trunk splitting low into gnarled limbs, an open rounded crown
of large glossy leaves, fruit hanging on the outside. Round 5 (Obon, mid-August): the fruit is still green,
half hidden among the leaves (ripe orange is October; the hanging dried persimmons of round 4 were late autumn).
Three variants. The fruit positions are listed in the catalog anchors ('fruit') for picking.
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

SEED = 7401
NAME = 'kaki'

VARIANTS = [  # key, height, limbs, spread, fruits, seed
    ('a', 7.5, 4, 3.4, 16, 1),
    ('b', 6.0, 3, 2.8, 11, 2),
    ('c', 8.5, 4, 3.9, 18, 3),
]
FRUIT_RIPE = [(66, 92, 40), (98, 128, 54), (138, 160, 78)]       # (named for the old slot) green in August
FRUIT_GOLD = [(84, 98, 42), (124, 136, 58), (160, 170, 84)]       # a little yellower


def tiles():
    S = SEED
    specs = {
        'mass': [(LV.broad_leaves, dict(W=int(16 + (i % 3) * 3), H=int(14 + (i % 2) * 3), seed=S + i)) for i in range(9)],
        'small': [(LV.broad_leaves, dict(W=12, H=11, seed=S + 50 + i)) for i in range(4)],
        'interior': [(LV.broad_leaves, dict(W=18, H=15, seed=S + 80 + i, gloss=0.0)) for i in range(2)],
        'fruit': [(LV.fruit, dict(W=7, seed=S + 90, colours=FRUIT_RIPE)), (LV.fruit, dict(W=6, seed=S + 91, colours=FRUIT_RIPE)),
                  (LV.fruit, dict(W=6, seed=S + 92, colours=FRUIT_GOLD))],
    }
    return FO.build_tiles(specs)


def variant(key, H, nl, spread, nfruit, vs, sets):
    R = rng(SEED * 10 + vs)
    fork = H * 0.32
    trunk = WD.Limb('trunk', TR.wander(R, [0, -0.3, 0], [R.normal(0, 0.2), 1, R.normal(0, 0.2)], fork + 0.3, 3, bend=0.12),
                    [0.24, 0.2, 0.18, 0.17], kind='trunk', n_around=9, step_fn=lambda f: 0.4, moss=0.25)
    WD.build_limb(trunk)
    limbs = [trunk]
    masses = []
    top = trunk.spine.pos[-1]
    az0 = R.uniform(0, 2 * math.pi)
    for i in range(nl):
        az = az0 + i * 2 * math.pi / nl + R.normal(0, 0.35)
        d = np.array([math.cos(az) * 0.8, 0.9, math.sin(az) * 0.8])
        L = (H - fork) * R.uniform(0.75, 1.0)
        path = TR.wander(R, top - np.array([0, 0.2, 0]), d, L, 4, bend=0.3, up=0.02)     # crooked
        limbs.append(WD.Limb(f'l{i}', path, [0.13, 0.1, 0.07, 0.05, 0.03], kind='limb', n_around=6,
                             step_fn=lambda f: 0.5, moss=0.2))
        for k, f in enumerate((0.55, 1.0)):
            p = path[2] if k == 0 else path[-1]
            r = spread * (0.4 if k == 0 else 0.48) * R.uniform(0.85, 1.1)
            masses.append(CD.Mass(p + np.array([0, 0.1, 0]), (r, r * 0.75, r * 0.9), seed=SEED + vs * 100 + i * 10 + k,
                                  clumps=0.3, clump_r=(0.6, 1.0), tiles='mass', interior=k == 1, flat=0.4, lump=0.12))
    cc = np.mean([m.c for m in masses], axis=0)
    span = max(np.max([np.linalg.norm((m.c - cc)[[0, 2]]) + m.r[0] for m in masses]), 1.5)
    crown_kw = dict(centre=tuple(cc), radii=(span, H * 0.35, span),
                    base_tint=TR.tint_for('#4d6c3a'), young_tint=TR.tint_for('#5f7a3a'), old_tint=TR.tint_for('#3f5f3e'),
                    overlap=1.1, fill_density=0.8, clump_overlap=1.0, interior_frac=0.25, spray_rate=0.0,
                    env_k=0.35, up_bias=0.35, flex_r=span, max_cards=1000 - nfruit)
    # fruit: hanging on the outer, camera-facing side of the masses
    fruits = []
    back = WD.view_back_upright()
    for j in range(nfruit):
        m = masses[R.integers(0, len(masses))]
        for _ in range(30):
            dd = normalize(R.normal(0, 1, 3) + back * 0.9 + np.array([0, -0.2, 0]))
            if dd @ back > 0.2:
                break
        p = m.c + dd * m.r * 1.0 + np.array([0, -0.12, 0])
        ft = sets['fruit'][0 if R.uniform() < 0.55 else (1 if R.uniform() < 0.6 else 2)]
        fruits.append(CD.Card(p, normalize(dd + np.array([0, 0.5, 0])), ft[1], ft[2], ft[0], 0.95,
                              np.array([1.0, 1.0, 1.0]), 0.6, 'fruit', 3.0))
    cat = {'category': 'tree', 'species': 'persimmon', 'footprint': [[0.0, 0.0, 0.32]], 'height': H,
           'crown': {'centre': [float(cc[0]), float(cc[1]), float(cc[2])], 'radius': float(span), 'base': float(fork)},
           'tags': ['tree', 'broadleaf', 'fruit'],
           'anchors': {'fruit': [[round(float(v), 3) for v in f.p] for f in fruits]},
           'notes': '柿 in August: green fruit among the leaves; anchors.fruit lists them.'}
    return limbs, masses, crown_kw, cat, fruits


def bark(seed):
    """Persimmon bark: dark, broken into small square blocks."""
    return WD.bark_texture(seed, spacing=(3, 5), ridge=('#463e37', '#514840', '#5c524a'), lip='#665c53',
                           fissure='#26211e', deep='#1d1916', lichen=('#7f826c', '#8c907a'), lichen_p=0.002,
                           moss=('#4c5a33',), moss_p=0.0008, break_p=0.22, wave=(1.0, 0.5), merge_p=0.1)


def build(out):
    a = out.asset(NAME, 'trees')
    bark_res = a.texture('bark', bark(SEED))
    m_bark = a.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 1.0},
                        textures={'albedo_tex': bark_res})
    atlas, rects, sets = tiles()
    leaf_res = a.texture('leaves', atlas)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=1.0),
                        textures={'leaf_tex': leaf_res})
    stats = {}
    for key, H, nl, spread, nf, vs in VARIANTS:
        limbs, masses, crown_kw, cat, fruits = variant(key, H, nl, spread, nf, vs, sets)
        stats[key] = TR.build_variant(a, key, limbs, masses, (atlas, rects), sets, crown_kw, m_bark, m_leaf, cat,
                                      colour_fn=TR.default_colour(), extra_cards=fruits, seed=SEED + vs)
    return stats
