"""竹 bamboo clumps, and the shrubs: 紫陽花 hydrangea (late summer, fading heads), 躑躅 azalea
(clipped cushions), a generic wild shrub."""
import math

import numpy as np

from .. import arch
from .. import raster as R
from ..core import PPM, Rng, normalize, vnoise2
from ..palette import PAL
from ..plant import Plant


def _culm_fx(seed, node_gap):
    def fx(u, v, n, P, base, T):
        ph = (u / node_gap) % 1.0
        node = ph < 0.06
        ring = (ph > 0.06) & (ph < 0.14)
        dv = np.where(node, -0.22, 0.0) + np.where(ring, 0.10, 0.0)
        dv += (vnoise2(v * 1.5, u * 0.8, seed) - 0.5) * 0.10
        return dv, None
    return fx


def bamboo(name, seed):
    rng = Rng(seed)
    n_c = rng.int(6, 12)
    Hmax = rng.range(9.5, 12.5)
    W = int(7.5 * 20 + 60)
    Hc = int((Hmax + 1.5) * 20 + 40)
    p = Plant(name, W, Hc, W // 2, Hc - 26, seed)
    p.meta['species'] = 'bamboo'
    culm_g = p.material('bamboo', PAL['bamboo'])
    culm_o = p.material('bambooOld', PAL['bambooOld'])
    leaf = p.material('bambooLeaf', PAL['bambooLeaf'])
    node_gap = rng.range(0.32, 0.40)
    p.bark_fx[culm_g] = _culm_fx(seed, node_gap)
    p.bark_fx[culm_o] = _culm_fx(seed + 1, node_gap)
    tops = []
    for k in range(n_c):
        a = rng.range(0, 2 * math.pi)
        r = rng.range(0.0, 0.9)
        base = np.array([math.cos(a) * r, 0.0, math.sin(a) * r * 0.8])
        h = Hmax * rng.range(0.75, 1.0)
        out = normalize(np.array([base[0] + rng.range(-0.3, 0.3), 0, base[2] + rng.range(-0.2, 0.2)]) + 1e-6)
        bend = rng.range(0.6, 1.6)
        pts = np.array([base + out * bend * t ** 1.8 + np.array([0, h * t, 0]) for t in np.linspace(0, 1, 30)])
        rc = rng.range(0.055, 0.085)
        mat = culm_o if rng() < 0.25 else culm_g
        p.tube(pts, np.linspace(rc, rc * 0.55, len(pts)), mat, R.PART_TRUNK, dens=3.0, cap=False, cast=k < 3)
        tops.append((pts, h))
    p.trunk_top = np.array([0, Hmax * 0.6, 0])
    # sprays: from the nodes of the upper two thirds, twigs carrying fans of long drooping
    # lanceolate leaves; denser toward the top, where the culm ends in a leafy whip
    for k, (pts, h) in enumerate(tops):
        n_nodes = int(h * 0.68 / node_gap)
        for j in range(n_nodes):
            t = 0.32 + 0.68 * j / max(1, n_nodes - 1)
            if rng() < 0.25 - 0.2 * t:
                continue
            P0 = arch.point_on(pts, t)
            for side in (-1, 1) if t > 0.55 else (rng.sign(),):
                a = rng.range(0, 2 * math.pi)
                d = np.array([math.cos(a), 0, math.sin(a)])
                tw = P0 + d * rng.range(0.4, 0.9) * (1.2 - t * 0.4) + np.array([0, rng.range(0.1, 0.3), 0])
                g = p.group(tw, min(1.0, 0.30 + 0.70 * t))
                p.blade(np.array([P0, (P0 + tw) / 2 + [0, 0.05, 0], tw]), np.array([0.9, 0.8, 0.6]), culm_g, group=g,
                        face=(0, 0, 1), fold=0.2, tone=-0.12)
                for i in range(rng.int(6, 10)):
                    aa = a + rng.range(-1.4, 1.4)
                    dd = np.array([math.cos(aa), 0, math.sin(aa)])
                    L = rng.range(0.24, 0.36)
                    q0 = tw + dd * rng.range(-0.08, 0.12) + np.array([0, rng.range(-0.06, 0.06), 0])
                    lf = np.array([q0, q0 + dd * L * 0.5 + [0, -L * 0.10, 0], q0 + dd * L * 0.85 + [0, -L * 0.45, 0],
                                   q0 + dd * L + [0, -L * 0.75, 0]])
                    p.blade(lf, np.array([1.0, 2.0, 1.4, 0.5]), leaf, group=g, face=(dd[0] * 0.4, 0.85, dd[2] * 0.4 + 0.2),
                            tone=rng.range(-0.1, 0.08) + 0.05 * t, fold=0.6)
    p.leaf_opts.update(dict(blade_base=0.22, blade_tip=0.12, blade_jitter=0.28))
    return p


def _bush(name, seed, kind, leaf_key, height, width, n_masses, cell_r, bumps, opts=None):
    rng = Rng(seed)
    W = int(width * 20 + 50)
    Hc = int((height + 1.0) * 20 + 30)
    p = Plant(name, W, Hc, W // 2, Hc - 14, seed, kind='shrub')
    p.meta['species'] = kind
    leaf = p.material(leaf_key, PAL[leaf_key])
    bark = p.material('barkGrey', PAL['barkGrey'])
    env = p.envelope(np.array([0, height * 0.5, 0]), np.array([width / 2, height / 2, width / 2 * 0.9]))
    # a few woody stems at the foot, seen in the gaps
    for k in range(rng.int(3, 5)):
        a = rng.range(0, 2 * math.pi)
        tip = np.array([math.cos(a) * width * 0.25, height * 0.55, math.sin(a) * width * 0.2])
        p.tube(np.array([[0, 0, 0], tip * 0.5 + [0, 0.05, 0], tip]), np.array([0.04, 0.03, 0.02]), bark, R.PART_LIMB,
               dens=3.0, cast=False)
    for k in range(n_masses):
        a = 2 * math.pi * k / n_masses + rng.range(-0.4, 0.4)
        rr = rng.range(0.15, 0.32) * width
        c = np.array([math.cos(a) * rr, height * rng.range(0.42, 0.6), math.sin(a) * rr * 0.8])
        rm = rng.range(0.32, 0.42) * width
        p.mass(c, np.array([rm, min(rm * 0.8, height * 0.48), rm]), leaf, env, cell_r=cell_r, bumps=bumps,
               sway=rng.range(0.25, 0.45))
    p.mass(np.array([0, height * 0.62, 0]), np.array([width * 0.36, height * 0.40, width * 0.34]), leaf, env,
           cell_r=cell_r, bumps=bumps, sway=0.3)
    p.leaf_opts.update(dict(w_env=0.6, inset=0.10, hl_p=0.5, self_shadow=0.4, shadow_floor=0.45))
    if opts:
        p.leaf_opts.update(opts)
    p.sway_amp = 0.6
    return p, rng


def azalea(name, seed):
    p, rng = _bush(name, seed, 'azalea', 'azalea', rng_h(seed, 0.8, 1.15), rng_h(seed + 1, 1.3, 2.0), 4, 0.10,
                   (5, 8, 0.14, 0.28), dict(hl_p=0.6))
    return p


def shrub(name, seed):
    p, rng = _bush(name, seed, 'shrub', 'broad', rng_h(seed, 1.0, 1.6), rng_h(seed + 1, 1.4, 2.2), 5, 0.15,
                   (4, 7, 0.12, 0.26))
    return p


def hydrangea(name, seed):
    p, rng = _bush(name, seed, 'hydrangea', 'hydLeaf', rng_h(seed, 1.0, 1.35), rng_h(seed + 1, 1.4, 1.9), 4, 0.15,
                   (3, 5, 0.12, 0.22))
    heads = [p.material('hydBlue', PAL['hydBlue']), p.material('hydViolet', PAL['hydViolet']),
             p.material('hydDusty', PAL['hydDusty'])]
    hr = Rng(seed * 5 + 3)
    # mophead flower heads on the upper, outer surface: blue fading through violet to dusty pink
    pick = [heads[0]] * 3 + [heads[1]] * 2 + [heads[2]] * 2

    def flowers(pl, cv):
        cand = np.nonzero((pl.c_pos[:, 1] > 0.45) & (pl.c_pos[:, 2] > -0.2))[0]
        if not len(cand):
            return
        n = hr.int(4, 7)
        chosen = []
        for _ in range(n * 6):
            i = int(hr.pick(cand))
            c = pl.c_pos[i]
            if all(np.linalg.norm(c - q) > 0.40 for q in chosen):
                chosen.append(c)
            if len(chosen) >= n:
                break
        for c in chosen:
            mi = int(pl.c_mass[np.argmin(np.linalg.norm(pl.c_pos - c, axis=1))])
            d = normalize(c - pl.masses[mi]['c'])
            P = c + d * 0.10
            mat = hr.pick(pick)
            rr = hr.range(0.22, 0.29)
            # a head is a tight dome of florets: draw it as small clumps so it is not a smooth ball
            k = 18
            q = P[None, :] + hr.g.normal(scale=rr * 0.42, size=(k, 3)) * np.array([1, 0.7, 1])
            R.ellipsoids(cv, pl.D(q), np.tile([[rr * 0.50, rr * 0.45, rr * 0.50 * pl.kz]], (k, 1)), R.PART_DETAIL, mat,
                         mass=mi, nkz=pl.kz, bumps=np.tile([[5, 0.2, 0.0, 0.7]], (k, 1)))
    p.details.append(flowers)
    return p


def rng_h(seed, lo, hi):
    return Rng(seed * 97 + 13).range(lo, hi)
