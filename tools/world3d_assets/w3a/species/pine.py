"""Akamatsu 赤松 (Japanese red pine): a leaning, bending trunk, red-orange flaking bark up top and
grey-brown plates below; long angular branches each ending in flat cloud plates of needles - the
layered silhouette v0.1 did well. Four variants.
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

SEED = 7201
NAME = 'pine'

VARIANTS = [  # key, height, base radius, lean x, lean z, branches, seed
    ('a', 13.0, 0.34, 2.2, -0.6, 6, 1),
    ('b', 10.0, 0.27, -1.8, 0.4, 5, 2),
    ('c', 15.0, 0.38, 0.8, -1.0, 7, 3),
    ('d', 8.0, 0.22, -2.6, -0.3, 4, 4),
]


def tiles():
    S = SEED
    specs = {
        'mass': [(LV.pine_tufts, dict(W=int(16 + (i % 4) * 2), H=int(9 + (i % 3)), seed=S + i)) for i in range(10)],
        'small': [(LV.pine_tufts, dict(W=12, H=8, seed=S + 50 + i, n=2)) for i in range(4)],
        'interior': [(LV.pine_pad, dict(W=18, H=9, seed=S + 80 + i)) for i in range(2)],
    }
    return FO.build_tiles(specs)


def variant(key, H, r0, lx, lz, nbr, vs):
    R = rng(SEED * 10 + vs)
    # an S-bent trunk leaning (lx, lz) at the top
    pts = [np.array([0.0, -0.4, 0.0])]
    for i, f in enumerate((0.2, 0.42, 0.62, 0.8, 1.0)):
        bend = math.sin(f * math.pi * 1.4 + R.uniform(0, 1)) * 0.5
        pts.append(np.array([lx * f ** 1.4 + bend * 0.6, H * f * 0.92, lz * f ** 1.4 + R.normal(0, 0.15)]))
    radii = [r0 * 1.2, r0, r0 * 0.85, r0 * 0.66, r0 * 0.45, r0 * 0.22]
    trunk = WD.Limb('trunk', pts, radii, kind='trunk', n_around=10, step_fn=lambda f: 0.55, moss=0.1)
    WD.build_limb(trunk)
    limbs = [trunk]
    masses = []
    sp = trunk.spine
    az = R.uniform(0, 2 * math.pi)
    for b in range(nbr):
        f = 0.45 + 0.5 * b / max(nbr - 1, 1) + R.normal(0, 0.03)
        p0, t0, rr = sp.point_at(min(f, 0.97))
        az += 2.2 + R.normal(0, 0.5)
        d = np.array([math.cos(az), 0.08 + 0.12 * R.uniform(), math.sin(az)])
        L = (H * 0.32) * (1.15 - f) * R.uniform(0.85, 1.2) + 1.2
        path = TR.wander(R, p0, d, L, 3, bend=0.22, up=0.02)
        limbs.append(WD.Limb(f'b{b}', path, [rr * 0.55, rr * 0.4, rr * 0.3, 0.05], kind='branch', n_around=6,
                             step_fn=lambda f_: 0.55))
        end = path[-1]
        pr = (1.6 + 1.2 * (1.1 - f)) * R.uniform(0.85, 1.15)
        masses.append(CD.Mass(end + np.array([0, 0.2, 0]), (pr, 0.3 + 0.06 * pr, pr * 0.8), yaw=-az, flat=0.9,
                              seed=SEED + vs * 100 + b, clumps=0.0, tiles='mass', interior=False, lump=0.08))
        if pr > 1.8 and R.uniform() < 0.7:          # a second, smaller plate along the branch
            mid = path[-2]
            masses.append(CD.Mass(mid + np.array([0, 0.3, 0]), (pr * 0.6, 0.3, pr * 0.5), yaw=-az + 0.4, flat=0.9,
                                  seed=SEED + vs * 100 + 50 + b, clumps=0.0, tiles='mass', interior=False))
    topp = sp.pos[-1]
    masses.append(CD.Mass(topp + np.array([0, 0.25, 0]), (1.4, 0.4, 1.2), flat=0.85, seed=SEED + vs * 100 + 99,
                          clumps=0.0, tiles='mass', interior=False))
    cc = np.mean([m.c for m in masses], axis=0)
    span = max(np.max([np.linalg.norm((m.c - cc)[[0, 2]]) + m.r[0] for m in masses]), 2.0)
    crown_kw = dict(centre=tuple(cc), radii=(span, H * 0.3, span),
                    base_tint=TR.tint_for('#41613f'), young_tint=TR.tint_for('#55703f'), old_tint=TR.tint_for('#355344'),
                    overlap=1.5, fill_density=1.2, clump_overlap=1.0, interior_frac=0.0, spray_rate=0.0,
                    env_k=0.25, up_bias=0.45, flex_r=span)
    cat = {'category': 'tree', 'species': 'red pine', 'footprint': [[0.0, 0.0, r0 * 1.3]], 'height': H,
           'crown': {'centre': [float(cc[0]), float(cc[1]), float(cc[2])], 'radius': float(span), 'base': float(H * 0.4)},
           'tags': ['tree', 'conifer'], 'anchors': {}, 'notes': f'赤松 {H:.0f} m, layered plates.'}
    return limbs, masses, crown_kw, cat


def colour(P, N, L):
    """Grey-brown plated bark low, the red-orange flakes of a red pine higher up."""
    y = P[:, 1]
    lo = np.array([0.70, 0.64, 0.58])
    hi = np.array([0.95, 0.56, 0.38])
    t = np.clip((y - 2.5) / 3.5, 0, 1)[:, None]
    if L.kind == 'branch':
        t = np.ones_like(t) * 0.8
    col = lo * (1 - t) + hi * t
    g = np.clip((0.35 - y) / 0.5, 0, 1)[:, None]
    return col * (1 - g) + np.array([0.6, 0.55, 0.48]) * g


def bark(seed):
    return WD.bark_texture(seed, spacing=(4, 8), ridge=('#9c948a', '#aaa296', '#b8b0a2'), lip='#c6beae',
                           fissure='#4c443e', deep='#3a3430', lichen=('#a8aa90', '#b4b69c'), lichen_p=0.001,
                           moss=('#5a6a3a',), moss_p=0.0003, break_p=0.08, wave=(1.6, 0.8), merge_p=0.3)


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
    for key, H, r0, lx, lz, nbr, vs in VARIANTS:
        limbs, masses, crown_kw, cat = variant(key, H, r0, lx, lz, nbr, vs)
        stats[key] = TR.build_variant(a, key, limbs, masses, (atlas, rects), sets, crown_kw, m_bark, m_leaf, cat,
                                      colour_fn=colour, seed=SEED + vs)
    return stats
