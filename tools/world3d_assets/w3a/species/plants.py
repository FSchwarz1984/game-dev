"""Bamboo clumps, shrubs and large plants.

  take_*     madake bamboo clumps (竹): straight jointed culms, the leaves in hanging fans high up
  tsutsuji_* azalea mounds (つつじ, summer: green), low and dense, small leaves
  ajisai_*   tama-ajisai (玉紫陽花, round 5: the mountain hydrangea that flowers in August; the
             mopheads of June were out of season at Obon): flat lilac heads ringed by pale florets
  tsubaki_*  camellia (椿): a dark glossy shrub-tree; in August no flowers, a few green fruit
  sakaki_*   sakaki (榊), the shrine's sacred evergreen: upright, small glossy leaves in flat sprays
  sarusuberi_* crape myrtle (百日紅, the Obon flower of graves and temples): smooth mottled stems,
             a light crown, pink panicles at the tips
  ikegaki_*  a clipped evergreen hedge (生垣) segment, 2 m
  fern_*     bracken / shield-fern clumps (羊歯) as card sprites
  susuki_*   pampas grass clumps (薄) with silvery plumes, as card sprites
Each species is one folder with several variants (contract: <= 600 cards, <= 8k triangles a tree)."""
from __future__ import annotations

import math

import numpy as np

from .. import cards as CD
from .. import foliage as FO
from .. import leaves as LV
from .. import trees as TR
from .. import wood as WD
from ..core import PPM, hex_rgb, normalize, rng
from ..mesh import MeshData


# --------------------------------------------------------------------------------- tile painters
def bamboo_leaves(W, H, seed, n_fans=None):
    """Long narrow bamboo leaves in hanging fans: sparse, the gaps matter."""
    R = rng(seed)
    c = LV.Canvas(W, H)
    nf = n_fans or int(R.integers(2, 4))
    for f in range(nf):
        bx, by = W * R.uniform(0.25, 0.75), H * R.uniform(0.08, 0.35)
        base_a = math.pi / 2 + R.normal(0, 0.55)
        k = int(R.integers(3, 6))
        for j in range(k):
            a = base_a + (j - (k - 1) / 2) * 0.42 + R.normal(0, 0.1)
            L = R.uniform(7.0, 10.5)
            m, uu = LV._leaf_mask(H, W, bx + math.cos(a) * L * 0.5, by + math.sin(a) * L * 0.5, a, L, 1.5)
            v = np.where(uu < -0.2, LV.TOP, LV.BODY)
            c.mask(m, v, f + j * 0.01)
    c.sep(R, 0.6)
    return c.finish()


def small_leaves(W, H, seed, n=None, size=(2.0, 3.0), wid=(1.4, 1.9)):
    """Azalea: many small leaves in a dense mound tile."""
    return LV.broad_leaves(W, H, seed, n=n or int(W * H / 6.0), size=size, wid=wid, gloss=0.05, droop=0.2)


# --------------------------------------------------------------------------------- bamboo
TAKE = [  # key, culms, height, spread, seed
    ('a', 7, 12.0, 1.3, 1), ('b', 5, 10.0, 1.0, 2), ('c', 9, 13.5, 1.6, 3), ('d', 3, 8.0, 0.7, 4), ('e', 6, 11.0, 1.2, 5),
]
CULM_GREEN = np.array(hex_rgb('#7f9a52')) / 255.0
CULM_OLD = np.array(hex_rgb('#a3a064')) / 255.0


def take_variant(key, n, H, spread, vs, R):
    limbs, masses = [], []
    for i in range(n):
        a = R.uniform(0, 2 * math.pi)
        r = spread * math.sqrt(R.uniform(0.05, 1.0))
        base = np.array([math.cos(a) * r, -0.3, math.sin(a) * r])
        h = H * R.uniform(0.75, 1.0)
        lean = np.array([R.normal(0, 0.06) + base[0] * 0.05, 1.0, R.normal(0, 0.06) + base[2] * 0.05])
        top = base + normalize(lean) * h
        mid = base + normalize(lean) * h * 0.55 + np.array([R.normal(0, 0.15), 0, R.normal(0, 0.15)])
        bend = top + np.array([R.normal(0, 0.6), -0.4, R.normal(0, 0.6)])
        pts = [base, base + (mid - base) * 0.5, mid, (mid + top) / 2, bend]
        r0 = 0.055 + 0.015 * R.uniform()
        old = R.uniform() < 0.35
        L = WD.Limb(f'c{i}', pts, [r0, r0 * 0.95, r0 * 0.85, r0 * 0.6, 0.012], kind='trunk', n_around=4,
                    step_fn=lambda f: 0.48, moss=0.0, tint=CULM_OLD if old else CULM_GREEN)
        L.tags['old'] = old
        limbs.append(L)
        # leaves hang in a few airy masses on the upper third, offset toward the bend
        for k in range(3):
            t = 0.62 + 0.13 * k
            c = base + (bend - base) * t + np.array([R.normal(0, 0.25), 0.0, R.normal(0, 0.25)])
            rr = 0.9 + 0.5 * R.uniform()
            masses.append(CD.Mass(c, (rr, rr * 1.3, rr), seed=8400 + vs * 100 + i * 10 + k, clumps=0.0, tiles='mass',
                                  interior=False, flat=0.0, sag=0.4, lump=0.25, density=0.55))
    cc = np.mean([m.c for m in masses], axis=0)
    span = max(np.max([np.linalg.norm((m.c - cc)[[0, 2]]) + m.r[0] for m in masses]), 1.5)
    crown_kw = dict(centre=tuple(cc), radii=(span, H * 0.25, span),
                    base_tint=TR.tint_for('#6a8442'), young_tint=TR.tint_for('#7f9446'), old_tint=TR.tint_for('#56703f'),
                    overlap=0.8, fill_density=0.7, clump_overlap=1.0, interior_frac=0.0, spray_rate=0.0, env_k=0.3,
                    up_bias=0.35, flex_r=span, max_cards=260)
    cat = {'category': 'tree', 'species': 'bamboo', 'footprint': [[0.0, 0.0, spread * 0.8 + 0.2]], 'height': H,
           'crown': {'centre': [float(cc[0]), float(cc[1]), float(cc[2])], 'radius': float(span), 'base': H * 0.55},
           'tags': ['tree', 'bamboo', 'choppable'], 'anchors': {},
           'notes': f'Madake clump, {n} culms, {H:.0f} m.'}
    return limbs, masses, crown_kw, cat


def culm_colour(P, N, L):
    """Jointed culms: a pale ring at every node (every 0.32 m), greener young, yellower old."""
    y = P[:, 1]
    node = (np.mod(y, 0.48) < 0.12)
    col = np.ones((len(P), 3))
    col[node] = np.array([1.15, 1.12, 1.02])
    g = np.clip((0.3 - y) / 0.4, 0, 1)[:, None]
    return col * (1 - g) + np.array([0.75, 0.7, 0.58]) * g


def build_take(out):
    a = out.asset('take', 'trees')
    m_bark = a.material('culm', 'toon_solid.gdshader', params={'albedo_mode': 0, 'porosity': 0.5})
    specs = {'mass': [(bamboo_leaves, dict(W=int(18 + (i % 3) * 3), H=int(15 + (i % 2) * 3), seed=8401 + i)) for i in range(10)],
             'small': [(bamboo_leaves, dict(W=14, H=12, seed=8450 + i, n_fans=2)) for i in range(4)]}
    atlas, rects, sets = FO.build_tiles(specs)
    leaf_res = a.texture('leaves', atlas)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=2.0), textures={'leaf_tex': leaf_res})
    R = rng(8400)
    stats = {}
    for key, n, H, sp, vs in TAKE:
        limbs, masses, crown_kw, cat = take_variant(key, n, H, sp, vs, R)
        stats[key] = TR.build_variant(a, key, limbs, masses, (atlas, rects), sets, crown_kw, m_bark, m_leaf, cat,
                                      colour_fn=culm_colour, seed=8400 + vs, max_tris=4000, max_cards=260)
    return stats


# --------------------------------------------------------------------------------- shrubs
def shrub_variant(name, key, H, W, stems, R, vs, tiles='mass', mass_n=3, tint=None, flat=0.3, lean=0.15):
    limbs, masses = [], []
    for s in range(stems):
        a = R.uniform(0, 2 * math.pi)
        d = np.array([math.cos(a) * lean, 1.0, math.sin(a) * lean])
        path = TR.wander(R, [math.cos(a) * 0.05, -0.1, math.sin(a) * 0.05], d, H * R.uniform(0.6, 0.85), 3, bend=0.2)
        limbs.append(WD.Limb(f's{s}', path, [0.04, 0.03, 0.02, 0.012], kind='branch', n_around=4, step_fn=lambda f: 0.4))
    for k in range(mass_n):
        a = 2 * math.pi * k / mass_n + R.normal(0, 0.4)
        rr = W * 0.5 * R.uniform(0.55, 0.8)
        c = np.array([math.cos(a) * W * 0.22, H * R.uniform(0.45, 0.6), math.sin(a) * W * 0.2])
        masses.append(CD.Mass(c, (rr, H * 0.42, rr * 0.9), seed=8500 + vs * 100 + k, clumps=0.25, clump_r=(0.25, 0.5),
                              tiles=tiles, interior=True, flat=flat, lump=0.15, lump_scale=1.5))
    cc = np.mean([m.c for m in masses], axis=0)
    span = max(np.max([np.linalg.norm((m.c - cc)[[0, 2]]) + m.r[0] for m in masses]), 0.5)
    return limbs, masses, cc, span


def build_shrubs(out):
    stats = {}
    # azalea: low dense green mounds
    a = out.asset('tsutsuji', 'trees')
    bark_res = a.texture('bark', WD.bark_texture(8601, size=64, spacing=(3, 5), ridge=('#5a4a3c', '#655444', '#6e5c4a')))
    m_bark = a.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 0.8}, textures={'albedo_tex': bark_res})
    specs = {'mass': [(small_leaves, dict(W=int(14 + (i % 3) * 2), H=int(12 + (i % 2) * 2), seed=8602 + i)) for i in range(8)],
             'interior': [(small_leaves, dict(W=16, H=13, seed=8650 + i)) for i in range(2)]}
    atlas, rects, sets = FO.build_tiles(specs)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=0.8),
                        textures={'leaf_tex': a.texture('leaves', atlas)})
    R = rng(8600)
    st = {}
    for key, H, W, vs in (('a', 0.9, 1.6, 1), ('b', 0.7, 1.2, 2), ('c', 1.1, 2.0, 3)):
        limbs, masses, cc, span = shrub_variant('tsutsuji', key, H, W, 3, R, vs, mass_n=3, flat=0.5)
        kw = dict(centre=tuple(cc), radii=(span, H * 0.5, span), base_tint=TR.tint_for('#4f6a3a'),
                  young_tint=TR.tint_for('#5f7a3e'), old_tint=TR.tint_for('#3f5a3c'), overlap=1.4, fill_density=1.1,
                  clump_overlap=1.0, interior_frac=0.3, spray_rate=0.0, env_k=0.35, up_bias=0.35, flex_r=span, max_cards=220)
        cat = {'category': 'shrub', 'species': 'azalea', 'footprint': [[0.0, 0.0, W * 0.4]], 'height': H,
               'crown': {'centre': [float(x) for x in cc], 'radius': float(span), 'base': 0.1}, 'tags': ['shrub'], 'anchors': {},
               'notes': 'つつじ mound (summer green).'}
        st[key] = TR.build_variant(a, key, limbs, masses, (atlas, rects), sets, kw, m_bark, m_leaf, cat, seed=8600 + vs,
                                   max_tris=1600, max_cards=220)
    stats['tsutsuji'] = st
    # hydrangea: a rounded bush with mophead flowers (RGB tiles, card tint white)
    a = out.asset('ajisai', 'trees')
    m_bark = a.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 0.8},
                        textures={'albedo_tex': a.texture('bark', WD.bark_texture(8701, size=64, spacing=(3, 5),
                                                                                  ridge=('#6a5a48', '#756450', '#7e6c58')))})
    # tama-ajisai: lilac and blue-violet fertile florets, pale sterile ones round the rim
    blues = [((112, 104, 168), (138, 132, 192), (168, 162, 210)), ((126, 106, 164), (152, 132, 186), (182, 164, 206)),
             ((118, 118, 160), (146, 146, 184), (176, 176, 204))]
    specs = {'mass': [(LV.broad_leaves, dict(W=int(15 + (i % 3) * 2), H=int(13 + (i % 2) * 2), seed=8702 + i, size=(4.0, 6.0),
                                             wid=(2.6, 3.4), gloss=0.1)) for i in range(7)],
             'interior': [(LV.broad_leaves, dict(W=16, H=14, seed=8750 + i, gloss=0.0)) for i in range(2)]}
    for j, cols in enumerate(blues):
        specs[f'flower{j}'] = [(LV.lacecap, dict(W=int(8 + (k % 2) * 2), seed=8760 + j * 10 + k, colours=cols)) for k in range(3)]
    atlas, rects, sets = FO.build_tiles(specs)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=0.8),
                        textures={'leaf_tex': a.texture('leaves', atlas)})
    R = rng(8700)
    st = {}
    back = WD.view_back_upright()
    for key, H, W, fl, vs in (('blue', 1.3, 1.8, 0, 1), ('violet', 1.1, 1.5, 1, 2), ('dusty', 1.4, 2.0, 2, 3)):
        limbs, masses, cc, span = shrub_variant('ajisai', key, H, W, 4, R, vs, mass_n=3, flat=0.4)
        flowers = []
        for m in masses:
            for k in range(6):
                for _ in range(20):
                    dd = normalize(R.normal(0, 1, 3) + back * 0.8 + np.array([0, 0.5, 0]))
                    if dd @ back > 0.1:
                        break
                p = m.c + dd * m.r * 0.95
                t = sets[f'flower{fl}'][int(R.integers(0, 3))]
                flowers.append(CD.Card(p, normalize(dd + np.array([0, 0.6, 0])), t[1], t[2], t[0], 0.95,
                                       np.array([1.0, 1.0, 1.0]), 0.5, 'flower', 3.0))
        kw = dict(centre=tuple(cc), radii=(span, H * 0.5, span), base_tint=TR.tint_for('#55703c'),
                  young_tint=TR.tint_for('#678040'), old_tint=TR.tint_for('#41603e'), overlap=1.3, fill_density=1.0,
                  clump_overlap=1.0, interior_frac=0.3, spray_rate=0.0, env_k=0.35, up_bias=0.35, flex_r=span,
                  max_cards=260 - len(flowers))
        cat = {'category': 'shrub', 'species': 'hydrangea', 'footprint': [[0.0, 0.0, W * 0.4]], 'height': H,
               'crown': {'centre': [float(x) for x in cc], 'radius': float(span), 'base': 0.1}, 'tags': ['shrub', 'flower'],
               'anchors': {}, 'notes': f'玉紫陽花 (tama-ajisai, flowers in August), {key}.'}
        st[key] = TR.build_variant(a, key, limbs, masses, (atlas, rects), sets, kw, m_bark, m_leaf, cat, extra_cards=flowers,
                                   seed=8700 + vs, max_tris=1800, max_cards=260)
    stats['ajisai'] = st
    # camellia: a dark glossy small tree, a few red flowers
    a = out.asset('tsubaki', 'trees')
    m_bark = a.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 0.8},
                        textures={'albedo_tex': a.texture('bark', WD.bark_texture(8801, size=64, spacing=(5, 9),
                                                                                  ridge=('#7e7a70', '#888478', '#928e82'),
                                                                                  break_p=0.01))})
    specs = {'mass': [(LV.broad_leaves, dict(W=int(14 + (i % 3) * 2), H=int(12 + (i % 2) * 2), seed=8802 + i, size=(3.0, 4.5),
                                             wid=(1.8, 2.4), gloss=0.6)) for i in range(8)],
             'interior': [(LV.broad_leaves, dict(W=16, H=14, seed=8850 + i, gloss=0.0)) for i in range(2)],
             'flower': [(LV.fruit, dict(W=3, seed=8860 + k, colours=[(74, 92, 44), (98, 120, 56), (128, 146, 74)])) for k in range(2)]}
    atlas, rects, sets = FO.build_tiles(specs)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=0.6),
                        textures={'leaf_tex': a.texture('leaves', atlas)})
    R = rng(8800)
    st = {}
    for key, H, W, vs in (('a', 2.6, 1.8, 1), ('b', 2.0, 1.5, 2)):
        limbs, masses, cc, span = shrub_variant('tsubaki', key, H, W, 2, R, vs, mass_n=3, flat=0.2, lean=0.08)
        for m in masses:
            m.r = np.array([m.r[0] * 0.85, m.r[1] * 0.9, m.r[2] * 0.85])
        flowers = []
        for m in masses:
            for k in range(2):
                dd = normalize(R.normal(0, 1, 3) + back * 0.9)
                t = sets['flower'][int(R.integers(0, 2))]
                flowers.append(CD.Card(m.c + dd * m.r * 0.9, normalize(dd + np.array([0, 0.4, 0])), t[1], t[2], t[0], 0.9,
                                       np.array([1.0, 1.0, 1.0]), 0.4, 'flower', 3.0))
        kw = dict(centre=tuple(cc), radii=(span, H * 0.5, span), base_tint=TR.tint_for('#34503a'),
                  young_tint=TR.tint_for('#42603e'), old_tint=TR.tint_for('#2a4436'), overlap=1.5, fill_density=1.2,
                  clump_overlap=1.0, interior_frac=0.3, spray_rate=0.0, env_k=0.3, up_bias=0.3, flex_r=span,
                  max_cards=300 - len(flowers))
        cat = {'category': 'shrub', 'species': 'camellia', 'footprint': [[0.0, 0.0, W * 0.35]], 'height': H,
               'crown': {'centre': [float(x) for x in cc], 'radius': float(span), 'base': 0.3}, 'tags': ['shrub', 'flower'],
               'anchors': {}, 'notes': '椿: dark glossy leaves; in August a few green fruit, no flowers.'}
        st[key] = TR.build_variant(a, key, limbs, masses, (atlas, rects), sets, kw, m_bark, m_leaf, cat, extra_cards=flowers,
                                   seed=8800 + vs, max_tris=2000, max_cards=300)
    stats['tsubaki'] = st
    stats.update(build_sacred_shrubs(out, back))
    return stats


def build_sacred_shrubs(out, back):
    """Round 5 (composition plan): the sakaki beside the shrine, the crape myrtle behind the graves,
    the clipped hedge between the yard and the forecourt."""
    stats = {}
    # sakaki: upright, dense, small glossy dark leaves; in August a few small green berries
    a = out.asset('sakaki', 'trees')
    m_bark = a.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 0.8},
                        textures={'albedo_tex': a.texture('bark', WD.bark_texture(9001, size=64, spacing=(5, 9),
                                                                                  ridge=('#6e6a5e', '#78746a', '#827e72')))})
    specs = {'mass': [(LV.broad_leaves, dict(W=int(13 + (i % 3) * 2), H=int(12 + (i % 2) * 2), seed=9002 + i, size=(2.4, 3.4),
                                             wid=(1.4, 1.9), gloss=0.65, droop=0.1)) for i in range(8)],
             'interior': [(LV.broad_leaves, dict(W=15, H=13, seed=9050 + i, size=(2.4, 3.2), gloss=0.0)) for i in range(2)]}
    atlas, rects, sets = FO.build_tiles(specs)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=0.6),
                        textures={'leaf_tex': a.texture('leaves', atlas)})
    R = rng(9000)
    st = {}
    for key, H, W, vs in (('a', 3.0, 1.4, 1), ('b', 2.3, 1.1, 2)):
        limbs, masses, cc, span = shrub_variant('sakaki', key, H, W, 2, R, vs, mass_n=4, flat=0.1, lean=0.05)
        for k, m in enumerate(masses):
            # an upright, slightly columnar habit: masses stacked up the stems
            m.c = np.array([m.c[0] * 0.6, H * (0.35 + 0.16 * k), m.c[2] * 0.6])
            m.r = np.array([m.r[0] * (0.9 - 0.1 * k), H * 0.2, m.r[2] * (0.9 - 0.1 * k)])
        kw = dict(centre=tuple(np.mean([m.c for m in masses], axis=0)), radii=(span * 0.7, H * 0.45, span * 0.7),
                  base_tint=TR.tint_for('#2f4a36'), young_tint=TR.tint_for('#3e5c3e'), old_tint=TR.tint_for('#263e32'),
                  overlap=1.5, fill_density=1.25, clump_overlap=1.0, interior_frac=0.3, spray_rate=0.0, env_k=0.3, up_bias=0.3,
                  flex_r=span, max_cards=300)
        cat = {'category': 'shrub', 'species': 'sakaki', 'footprint': [[0.0, 0.0, W * 0.3]], 'height': H,
               'crown': {'centre': [0.0, H * 0.55, 0.0], 'radius': float(span * 0.7), 'base': 0.3}, 'tags': ['shrub', 'sacred'],
               'anchors': {}, 'notes': '榊: the shrine\'s evergreen (its sprays go on the altar), upright, small glossy leaves.'}
        st[key] = TR.build_variant(a, key, limbs, masses, (atlas, rects), sets, kw, m_bark, m_leaf, cat, seed=9000 + vs,
                                   max_tris=2000, max_cards=300)
    stats['sakaki'] = st
    # crape myrtle: three to five smooth mottled stems leaning out, a light crown, pink panicles
    a = out.asset('sarusuberi', 'trees')
    m_bark = a.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 0.6},
                        textures={'albedo_tex': a.texture('bark', WD.bark_texture(9101, size=64, spacing=(8, 14),
                                                                                  ridge=('#a08c78', '#b29c86', '#c0aa92'), lip='#cdb8a0',
                                                                                  fissure='#8c7866', deep='#7c6a5a', break_p=0.03,
                                                                                  lichen=('#b9b49c', '#c6c0a6'), lichen_p=0.004))})
    pinks = ((176, 72, 118), (204, 98, 142), (226, 138, 172))
    specs = {'mass': [(LV.broad_leaves, dict(W=int(13 + (i % 3) * 2), H=int(11 + (i % 2) * 2), seed=9102 + i, size=(2.2, 3.0),
                                             wid=(1.5, 2.0), gloss=0.2, droop=0.2)) for i in range(7)],
             'interior': [(LV.broad_leaves, dict(W=14, H=12, seed=9150 + i, size=(2.2, 3.0), gloss=0.0)) for i in range(2)],
             'flower': [(LV.panicle, dict(W=int(5 + (k % 2)), seed=9160 + k, colours=pinks)) for k in range(4)]}
    atlas, rects, sets = FO.build_tiles(specs)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=1.0),
                        textures={'leaf_tex': a.texture('leaves', atlas)})
    R = rng(9100)
    st = {}
    for key, H, W, stems, vs in (('a', 4.6, 3.4, 4, 1),):
        limbs, masses = [], []
        az0 = R.uniform(0, 2 * math.pi)
        for s_ in range(stems):
            az = az0 + s_ * 2 * math.pi / stems + R.normal(0, 0.3)
            d = np.array([math.cos(az) * 0.45, 1.0, math.sin(az) * 0.45])
            path = TR.wander(R, [math.cos(az) * 0.08, -0.2, math.sin(az) * 0.08], d, H * R.uniform(0.62, 0.8), 4, bend=0.22, up=0.0)
            stem = WD.Limb(f's{s_}', path, [0.1, 0.085, 0.065, 0.045, 0.025], kind='trunk', n_around=7, step_fn=lambda f: 0.5, moss=0.05)
            WD.build_limb(stem)
            limbs.append(stem)
            top = stem.spine.pos[-1]
            masses.append(CD.Mass(top + np.array([0, 0.15, 0]), (W * 0.28, 0.6, W * 0.26), flat=0.5, seed=9100 + vs * 50 + s_,
                                  clumps=0.2, clump_r=(0.3, 0.5), tiles='mass', interior=True, lump=0.12))
        flowers = []
        for m in masses:
            for k in range(7):
                dd = normalize(R.normal(0, 1, 3) * np.array([1, 0.4, 1]) + np.array([0, 0.9, 0]) + back * 0.4)
                t = sets['flower'][int(R.integers(0, 4))]
                flowers.append(CD.Card(m.c + dd * m.r * 0.95, normalize(dd + np.array([0, 0.5, 0])), t[1], t[2], t[0], 0.95,
                                       np.array([1.0, 1.0, 1.0]), 0.6, 'flower', 3.0))
        cc = np.mean([m.c for m in masses], axis=0)
        span = max(np.max([np.linalg.norm((m.c - cc)[[0, 2]]) + m.r[0] for m in masses]), 1.0)
        kw = dict(centre=tuple(cc), radii=(span, 0.9, span), base_tint=TR.tint_for('#55703e'), young_tint=TR.tint_for('#678244'),
                  old_tint=TR.tint_for('#45603c'), overlap=1.1, fill_density=0.9, clump_overlap=1.0, interior_frac=0.2,
                  spray_rate=0.0, env_k=0.35, up_bias=0.4, flex_r=span, max_cards=420 - len(flowers))
        cat = {'category': 'tree', 'species': 'crape myrtle', 'footprint': [[0.0, 0.0, 0.3]], 'height': H + 0.6,
               'crown': {'centre': [float(x) for x in cc], 'radius': float(span), 'base': float(H * 0.5)}, 'tags': ['tree', 'flower'],
               'anchors': {}, 'notes': '百日紅: flowers through the summer (July to September), the tree of Obon by graves and temples.'}
        st[key] = TR.build_variant(a, key, limbs, masses, (atlas, rects), sets, kw, m_bark, m_leaf, cat, extra_cards=flowers,
                                   seed=9100 + vs, max_tris=4000, max_cards=420)
    stats['sarusuberi'] = st
    # the clipped hedge: a 2 m segment of camellia trimmed square, a few stems showing at the foot
    a = out.asset('ikegaki', 'trees')
    m_bark = a.material('bark', 'toon_solid.gdshader', params={'albedo_mode': 1, 'porosity': 0.8},
                        textures={'albedo_tex': a.texture('bark', WD.bark_texture(9201, size=64, spacing=(5, 9),
                                                                                  ridge=('#6e6a5e', '#78746a', '#827e72')))})
    specs = {'mass': [(LV.broad_leaves, dict(W=int(13 + (i % 3) * 2), H=int(12 + (i % 2) * 2), seed=9202 + i, size=(2.6, 3.6),
                                             wid=(1.6, 2.1), gloss=0.55, droop=0.05)) for i in range(8)],
             'interior': [(LV.broad_leaves, dict(W=15, H=13, seed=9250 + i, gloss=0.0)) for i in range(2)]}
    atlas, rects, sets = FO.build_tiles(specs)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=0.3),
                        textures={'leaf_tex': a.texture('leaves', atlas)})
    R = rng(9200)
    st = {}
    for key, Lh, H, vs in (('a', 2.0, 1.25, 1), ('b', 2.0, 1.15, 2)):
        limbs, masses = [], []
        for s_ in range(4):
            x = -Lh / 2 + (s_ + 0.5) * Lh / 4 + R.normal(0, 0.06)
            limbs.append(WD.Limb(f's{s_}', [[x, -0.1, 0.0], [x + R.normal(0, 0.03), H * 0.4, R.normal(0, 0.03)]], [0.035, 0.025],
                                 kind='branch', n_around=4, step_fn=lambda f: 0.4))
        for k in range(4):
            x = -Lh / 2 + (k + 0.5) * Lh / 4
            masses.append(CD.Mass(np.array([x, H * 0.62, 0.0]), (Lh / 4 * 0.85, H * 0.36, 0.34), flat=0.9, seed=9200 + vs * 40 + k,
                                  clumps=0.0, tiles='mass', interior=True, lump=0.04, lump_scale=1.0))
        kw = dict(centre=(0.0, H * 0.62, 0.0), radii=(Lh / 2, H * 0.36, 0.35), base_tint=TR.tint_for('#33503a'),
                  young_tint=TR.tint_for('#41603e'), old_tint=TR.tint_for('#2a4436'), overlap=1.6, fill_density=1.5,
                  clump_overlap=1.0, interior_frac=0.35, spray_rate=0.0, env_k=0.2, up_bias=0.2, flex_r=0.6, max_cards=320)
        cat = {'category': 'shrub', 'species': 'hedge', 'footprint': [[-0.5, 0.0, 0.42], [0.5, 0.0, 0.42]], 'height': H,
               'crown': {'centre': [0.0, H * 0.62, 0.0], 'radius': Lh / 2, 'base': 0.2}, 'tags': ['shrub', 'hedge'], 'anchors': {},
               'notes': '生垣: a clipped camellia hedge, 2 m a segment (place along a line, yaw along it).'}
        st[key] = TR.build_variant(a, key, limbs, masses, (atlas, rects), sets, kw, m_bark, m_leaf, cat, seed=9200 + vs,
                                   max_tris=1800, max_cards=320)
    stats['ikegaki'] = st
    return stats


# --------------------------------------------------------------------------------- card plants
def card_plant(asset, key, cards, atlas, rects, leaf_mat, catalog):
    md = CD.cards_mesh(cards, atlas.shape[1], atlas.shape[0], rects)
    lo = np.min([c.p for c in cards], axis=0) - 1.5
    hi = np.max([c.p for c in cards], axis=0) + 1.5
    mesh = asset.mesh(f'{key}_leaves', [(leaf_mat, md)], custom_aabb=[lo.tolist(), (hi - lo + np.array([0, 2, 0])).tolist()])
    scene = asset.scene([{'name': 'Leaves', 'type': 'mesh', 'mesh': mesh, 'extra_cull_margin': 1.0}], key=key)
    e = dict(catalog)
    e['scene'] = scene
    asset.entries[f'{asset.name}_{key}'] = e
    return {'cards': len(cards), 'tris': 2 * len(cards)}


def plant_cards(R, tiles, n, spread, height, tint, flex=0.8, ao=0.9):
    """A clump: the biggest sprite in the middle, smaller ones around and a little behind."""
    out = []
    back = WD.view_back_upright()
    for k in range(n):
        t = tiles[int(R.integers(0, len(tiles)))] if k else max(tiles, key=lambda q: q[2])
        a = R.uniform(0, 2 * math.pi)
        r = 0.0 if k == 0 else spread * math.sqrt(R.uniform(0.2, 1.0))
        p = np.array([math.cos(a) * r, t[2] / PPM * 0.5 - 0.02, math.sin(a) * r * 0.7 - (0.0 if k == 0 else 0.1)])
        nrm = normalize(np.array([math.cos(a) * 0.3, 1.0, 0.4 + math.sin(a) * 0.3]))
        out.append(CD.Card(p, nrm, t[1], t[2], t[0], ao - 0.1 * (k > 0), np.clip(tint * (1 + R.normal(0, 0.04)), 0, 1),
                           flex, 'plant', 1.0))
    return out


def build_card_plants(out):
    stats = {}
    a = out.asset('fern', 'plants')
    specs = {'big': [(LV.fern_clump, dict(W=int(22 + 2 * (i % 2)), H=int(16 + (i % 3)), seed=8901 + i)) for i in range(4)],
             'small': [(LV.fern_clump, dict(W=14, H=11, seed=8920 + i, n_fronds=6)) for i in range(4)]}
    atlas, rects, sets = FO.build_tiles(specs)
    # ferns are ground cover: drawn without the foliage outline (art sample round 2: with it every
    # clump read as a sticker on the forest floor; the readability order puts plants last)
    m_leaf = a.material('leaves', 'toon_foliage_noline.gdshader', params=FO.foliage_params(wind_px=1.2, cutaway=False),
                        textures={'leaf_tex': a.texture('leaves', atlas)})
    R = rng(8900)
    st = {}
    for key, n, sp, col in (('a', 3, 0.35, '#5a7a3a'), ('b', 2, 0.25, '#4f6e38'), ('c', 4, 0.45, '#617f3d'), ('d', 1, 0.0, '#55743a')):
        tiles = sets['big'] + (sets['small'] if n > 1 else [])
        cards = plant_cards(R, tiles if n > 1 else sets['big'], n, sp, 0.8, TR.tint_for(col))
        cat = {'category': 'plant', 'species': 'fern', 'footprint': [], 'height': 0.9, 'tags': ['plant'], 'anchors': {},
               'notes': '羊歯 clump (card sprites).'}
        st[key] = card_plant(a, key, cards, atlas, rects, m_leaf, cat)
    stats['fern'] = st
    a = out.asset('susuki', 'plants')
    plume = [(222, 214, 192), (196, 186, 160)]
    specs = {'big': [(LV.grass_clump, dict(W=int(22 + 2 * (i % 2)), H=int(28 + 2 * (i % 3)), seed=8951 + i, plume=True,
                                           plume_col=plume, n=int(22 + 3 * (i % 3)), thick=2)) for i in range(4)],
             'small': [(LV.grass_clump, dict(W=16, H=18, seed=8970 + i, n=18, thick=2)) for i in range(3)]}
    atlas, rects, sets = FO.build_tiles(specs)
    m_leaf = a.material('leaves', 'toon_foliage.gdshader', params=FO.foliage_params(wind_px=2.0, cutaway=False),
                        textures={'leaf_tex': a.texture('leaves', atlas)})
    R = rng(8950)
    st = {}
    for key, n, sp, col in (('a', 2, 0.3, '#a0a668'), ('b', 3, 0.4, '#959e60'), ('c', 1, 0.0, '#a8ac6e'), ('d', 2, 0.25, '#8f985c')):
        cards = plant_cards(R, sets['big'] + (sets['small'] if n > 1 else []), n, sp, 1.4, TR.tint_for(col), flex=1.0)
        cat = {'category': 'plant', 'species': 'susuki', 'footprint': [], 'height': 1.5, 'tags': ['plant'], 'anchors': {},
               'notes': '薄 clump with silvery plumes (card sprites).'}
        st[key] = card_plant(a, key, cards, atlas, rects, m_leaf, cat)
    stats['susuki'] = st
    return stats


def build(out):
    stats = {'take': build_take(out)}
    stats.update(build_shrubs(out))
    stats.update(build_card_plants(out))
    return stats
