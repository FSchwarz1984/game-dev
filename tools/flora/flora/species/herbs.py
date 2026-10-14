"""Herbs and grasses: 芒 susuki, ferns, 彼岸花 higanbana, 露草 tsuyukusa, 女郎花 ominaeshi.
All single-layer bodies sorted at their foot; blades and flower parts sway in small groups."""
import math

import numpy as np

from .. import raster as R
from ..core import Rng, normalize
from ..palette import PAL
from ..plant import Plant


def _arc(base, a_horiz, length, rise, droop, n=10, wobble=0.0, rng=None):
    """A blade that rises and arches over: base point, horizontal heading, length (m)."""
    pts = []
    d = np.array([math.cos(a_horiz), 0.0, math.sin(a_horiz)])
    for i in range(n + 1):
        t = i / n
        h = rise * math.sin(min(1.0, t * 1.15) * math.pi * 0.5) - droop * t ** 2.2
        r = length * t
        w = (rng.range(-1, 1) * wobble * t) if rng is not None else 0.0
        pts.append(base + d * r + np.array([0, h, 0]) + np.array([-d[2], 0, d[0]]) * w)
    return np.array(pts)


def susuki(name, seed):
    """Susuki: a wide fountain of long arching blades (dark at the heart, paler and drier at the
    tips), and above it a few plumes on bare stalks: late summer, the first plumes, still closed
    and tinged red-brown, a whisk of silky threads hanging to the lee."""
    rng = Rng(seed)
    Hh = rng.range(1.4, 1.9)
    W, Hc = 120, int(Hh * 20 + 40)
    p = Plant(name, W, Hc, W // 2, Hc - 10, seed, kind='herb')
    p.meta['species'] = 'susuki'
    blade = p.material('susukiLeaf', PAL['susukiLeaf'])
    dry = p.material('susuki', PAL['susuki'])
    plume = p.material('plume', PAL['plume'])
    stem = p.material('susuki', PAL['susuki'])
    lean = rng.range(-0.6, 0.6)              # the whole tuft is combed one way by the wind
    groups = [p.group(np.array([math.cos(a) * 0.5, 0.6, math.sin(a) * 0.4]), 0.35 + 0.08 * k)
              for k, a in enumerate(np.linspace(0, 2 * math.pi, 6, endpoint=False))]
    n_bl = rng.int(30, 40)
    for k in range(n_bl):
        a = rng.range(0, 2 * math.pi)
        base = np.array([rng.range(-0.16, 0.16), 0.0, rng.range(-0.08, 0.08)])
        L = rng.range(0.9, 1.5)
        a2 = math.atan2(math.sin(a) * 0.55, math.cos(a) + lean * 0.5)
        reach = L * rng.range(0.45, 0.75)
        pts = _arc(base, a2, reach, L * rng.range(0.55, 0.85), L * rng.range(0.40, 0.85), n=14)
        g = groups[int(((a % (2 * math.pi)) / (2 * math.pi)) * 6) % 6]
        w = np.concatenate([np.full(5, 1.3), np.linspace(1.0, 0.5, len(pts) - 5)])
        m = dry if rng() < 0.12 else blade
        p.blade(pts, w, m, group=g, face=(math.cos(a2) * 0.5, 0.8, math.sin(a2) * 0.5),
                tone=rng.range(-0.26, 0.0) + (0.05 if reach > L * 0.62 else 0.0))
    side = 1.0 if lean >= 0 else -1.0
    for k in range(rng.int(4, 7)):
        base = np.array([rng.range(-0.10, 0.10), 0.0, rng.range(-0.05, 0.05)])
        top_h = Hh * rng.range(0.80, 1.05)
        bend = side * rng.range(0.05, 0.22)
        g = p.group(np.array([bend, top_h, 0]), 0.95)
        stalk = np.array([base + np.array([bend * t * t + rng.range(-0.01, 0.01), top_h * t, 0])
                          for t in np.linspace(0, 1, 12)])
        p.blade(stalk, np.full(len(stalk), 0.5), stem, group=g, face=(0, 0, 1), fold=0.2, tone=0.08)
        tip = stalk[-1]
        # the plume: a narrow brush of silky spikelet threads around the top 0.3 m of the stalk,
        # on both sides of it, nodding to the lee; one-pixel threads, light and dark alternating,
        # so it reads as a feathery brush and not as a flag
        n_th = rng.int(9, 13)
        for j in range(n_th):
            s = j / (n_th - 1)
            st = tip - np.array([0, 0.28 * s, 0]) + np.array([bend * 0.25 * s, 0, 0])
            L = rng.range(0.10, 0.18) * (1.0 - 0.35 * s)
            sd = 1.0 if j % 2 else -1.0
            sp = sd * rng.range(0.02, 0.05) + side * 0.03
            th = np.array([st, st + np.array([sp, L * 0.55, 0.01]), st + np.array([sp * 1.6 + side * 0.03, L * 0.75, 0.02])])
            p.blade(th, np.array([0.5, 0.5, 0.5]), plume, group=g, face=(sd * 0.4, 0.6, 0.6),
                    tone=(0.10 if j % 3 else -0.25) - 0.15 * s, fold=0.1)
    p.leaf_opts.update(dict(blade_base=0.12, blade_tip=0.14, blade_jitter=0.20, blade_light=0.42))
    return p


def fern(name, seed):
    """A shield fern: a fountain of 6-9 broad fronds, each with clear pairs of leaflets that
    shorten toward the tip; the young fronds at the heart paler."""
    rng = Rng(seed)
    Hh = rng.range(0.55, 0.80)
    p = Plant(name, 96, 64, 48, 52, seed, kind='herb')
    p.meta['species'] = 'fern'
    fm = p.material('fern', PAL['fern'])
    rach_m = p.material('stem', PAL['stem'])
    n_fr = rng.int(6, 9)
    angs = np.linspace(0, 2 * math.pi, n_fr, endpoint=False) + rng.range(0, 1)
    for k, a in enumerate(angs):
        a += rng.range(-0.25, 0.25)
        L = rng.range(0.65, 1.0)
        young = k % 3 == 0
        g = p.group(np.array([math.cos(a) * L * 0.5, Hh * 0.6, math.sin(a) * L * 0.5]), 0.35)
        rach = _arc(np.array([0, 0.02, 0]), a, L * 0.70, Hh * rng.range(1.0, 1.3), Hh * rng.range(0.6, 1.0), n=16)
        face = (math.cos(a) * 0.3, 0.9, math.sin(a) * 0.3)
        p.blade(rach, np.linspace(1.0, 0.5, len(rach)), rach_m, group=g, face=face, tone=-0.04, fold=0.2)
        for i in range(2, len(rach) - 1):
            t = i / (len(rach) - 1)
            P0 = rach[i]
            d = normalize(rach[i + 1] - rach[i - 1])
            side = normalize(np.cross(d, [0, 1, 0]))
            ln = 0.20 * (1 - t) ** 0.6 * (0.5 + 0.5 * min(1.0, t * 4)) + 0.025
            sd = 1 if i % 2 else -1
            tip = P0 + side * sd * ln + d * ln * 0.6 + np.array([0, -ln * 0.35, 0])
            p.blade(np.array([P0, (P0 + tip) / 2 + [0, 0.012, 0], tip]), np.array([1.8, 2.2, 0.8]), fm, group=g,
                    face=face, tone=(0.02 if sd < 0 else -0.14) + (0.08 if young else -0.04), fold=0.45)
    p.leaf_opts.update(dict(blade_base=0.20, blade_tip=0.10, blade_jitter=0.14, blade_light=0.42))
    return p


def higanbana(name, seed):
    """Red spider lilies, a small drift of them: bare stems, each umbel a ring of narrow recurved
    petals with long upswept stamens (one-pixel lines), so a head reads as a spidery red crown."""
    rng = Rng(seed)
    p = Plant(name, 72, 50, 36, 42, seed, kind='herb')
    p.meta['species'] = 'higanbana'
    stem = p.material('stem', PAL['stem'])
    red = p.material('higan', PAL['higan'])
    for k in range(rng.int(3, 6)):
        base = np.array([rng.range(-0.38, 0.38), 0, rng.range(-0.15, 0.15)])
        h = rng.range(0.36, 0.56)
        lean = np.array([rng.range(-0.05, 0.05), 0, rng.range(-0.03, 0.03)])
        g = p.group(base + np.array([0, h, 0]), 0.55)
        st = np.array([base + lean * t + np.array([0, h * t, 0]) for t in np.linspace(0, 1, 8)])
        p.blade(st, np.full(len(st), 0.5), stem, group=g, face=(0, 0, 1), fold=0.2)
        c = st[-1]
        m = rng.int(6, 8)
        for j in range(m):
            a = 2 * math.pi * j / m + rng.range(-0.25, 0.25)
            d = np.array([math.cos(a), 0, math.sin(a)])
            # petal: out and curling back down
            pet = np.array([c, c + d * 0.06 + [0, 0.03, 0], c + d * 0.10 + [0, 0.0, 0], c + d * 0.09 - [0, 0.03, 0]])
            p.blade(pet, np.array([1.1, 1.0, 0.8, 0.5]), red, group=g, face=(d[0] * 0.5, 0.8, d[2] * 0.5 + 0.2),
                    tone=-0.05, fold=0.5)
            # stamens: long, thin, sweeping up and out
            stm = np.array([c + [0, 0.02, 0], c + d * 0.08 + [0, 0.10, 0], c + d * 0.16 + [0, 0.15, 0],
                            c + d * 0.21 + [0, 0.15, 0]])
            p.blade(stm, np.array([0.5, 0.5, 0.5, 0.5]), red, group=g, face=(d[0] * 0.3, 0.9, 0.3), tone=0.22, fold=0.1)
    p.leaf_opts.update(dict(blade_base=0.30, blade_tip=0.10, blade_jitter=0.12))
    return p


def tsuyukusa(name, seed):
    """Asiatic dayflower: a low sprawl of pointed leaves on creeping stems, a scatter of small
    bright blue two-petal flowers with a yellow eye."""
    rng = Rng(seed)
    p = Plant(name, 60, 28, 30, 22, seed, kind='herb')
    p.meta['species'] = 'tsuyukusa'
    leaf = p.material('fern', PAL['fern'])
    blue = p.material('tsuyu', PAL['tsuyu'])
    yel = p.material('omina', PAL['omina'])
    g = p.group(np.array([0, 0.1, 0]), 0.25)
    for k in range(rng.int(14, 20)):
        a = rng.range(0, 2 * math.pi)
        b = np.array([rng.range(-0.42, 0.42), 0.01, rng.range(-0.18, 0.18)])
        d = np.array([math.cos(a), 0, math.sin(a)])
        pts = np.array([b, b + d * 0.07 + [0, 0.05, 0], b + d * 0.14 + [0, 0.06, 0]])
        p.blade(pts, np.array([1.6, 2.2, 0.7]), leaf, group=g, face=(d[0] * 0.3, 0.9, d[2] * 0.3 + 0.2),
                tone=rng.range(-0.1, 0.08))
    for k in range(rng.int(4, 7)):
        c = np.array([rng.range(-0.35, 0.35), rng.range(0.08, 0.14), rng.range(-0.12, 0.14)])
        for sd in (-1, 1):
            q = c + np.array([sd * 0.03, 0.01, 0])
            p.blade(np.array([q, q + [sd * 0.025, 0.03, 0]]), np.array([2.2, 2.0]), blue, group=g, face=(0, 0.7, 0.7),
                    tone=0.12, fold=0.3)
        p.blade(np.array([c - [0, 0.015, 0], c - [0, 0.03, 0]]), np.array([1.0, 0.8]), yel, group=g, face=(0, 0.7, 0.7),
                tone=0.2)
    p.leaf_opts.update(dict(blade_base=0.28, blade_tip=0.1, blade_jitter=0.2))
    return p


def ominaeshi(name, seed):
    """Patrinia: tall thin stems topped with flat, airy clusters of tiny yellow flowers; leaves
    only low on the stems."""
    rng = Rng(seed)
    Hh = rng.range(1.0, 1.35)
    p = Plant(name, 60, int(Hh * 20 + 30), 30, int(Hh * 20 + 30) - 8, seed, kind='herb')
    p.meta['species'] = 'ominaeshi'
    stem = p.material('stem', PAL['stem'])
    leaf = p.material('fern', PAL['fern'])
    yel = p.material('omina', PAL['omina'])
    for k in range(rng.int(3, 5)):
        base = np.array([rng.range(-0.15, 0.15), 0, rng.range(-0.06, 0.06)])
        h = Hh * rng.range(0.75, 1.0)
        lean = np.array([rng.range(-0.15, 0.15), 0, 0])
        g = p.group(base + np.array([0, h, 0]), 0.7)
        st = np.array([base + lean * t * t + np.array([0, h * t, 0]) for t in np.linspace(0, 1, 10)])
        p.blade(st, np.full(len(st), 0.5), stem, group=g, face=(0, 0, 1), fold=0.2)
        for i in (1, 2, 4):
            for sd in (-1, 1):
                q = st[i]
                ln = 0.16 if i < 3 else 0.10
                p.blade(np.array([q, q + [sd * ln * 0.6, 0.04, 0.02], q + [sd * ln, 0.0, 0.03]]),
                        np.array([1.4, 1.8, 0.6]), leaf, group=g, face=(sd * 0.3, 0.9, 0.3), tone=-0.05)
        top = st[-1]
        # a flat-topped corymb: short branches to a broad, open cap of tiny flowers
        for j in range(rng.int(5, 7)):
            a = rng.range(0, 2 * math.pi)
            r = rng.range(0.05, 0.14)
            q = top + np.array([math.cos(a) * r, rng.range(0.0, 0.04), math.sin(a) * r * 0.6])
            p.blade(np.array([top - [0, 0.05, 0], q]), np.array([0.5, 0.5]), stem, group=g, face=(0, 0.8, 0.6))
            for i in range(rng.int(3, 5)):
                f = q + np.array([rng.range(-0.04, 0.04), rng.range(0.0, 0.02), rng.range(-0.02, 0.02)])
                p.blade(np.array([f, f + [0.014, 0.006, 0]]), np.array([1.6, 1.4]), yel, group=g, face=(0, 0.8, 0.6),
                        tone=rng.range(-0.08, 0.16), fold=0.2)
    p.leaf_opts.update(dict(blade_base=0.28, blade_tip=0.1, blade_jitter=0.2))
    return p
