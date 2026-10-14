"""Conifers: 杉 sugi cedar (a tall spire of drooping tiers of rounded tufts) and 赤松 red pine
(a leaning red trunk carrying a few flat layered plates of needles, the shape v0.1's owner liked)."""
import math

import numpy as np

from .. import arch
from .. import raster as R
from ..core import PPM, Rng, normalize, vnoise2
from ..palette import PAL
from ..plant import Plant


# ------------------------------------------------------------------------------------------ sugi
def cedar(name, seed, height=None, lean=None, thin=0.0):
    rng = Rng(seed)
    H_t = height if height is not None else rng.range(13.0, 18.0)
    crown_base = H_t * rng.range(0.30, 0.40)
    base_r = rng.range(1.7, 2.3) * (1 - thin * 0.3)          # crown radius at its base
    W = int(base_r * 2 * 20 + 70)
    Hc = int((H_t + 1.5) * 20 + 50)
    p = Plant(name, W, Hc, W // 2, Hc - 24, seed)
    p.meta['species'] = 'cedar'
    leaf = p.material('cedar', PAL['cedar'])
    bark = p.material('barkCedar', PAL['barkCedar'])
    moss = p.material('moss', PAL['moss'])
    p.bark_fx[bark] = arch.bark_fibrous(seed, moss_mat=moss)
    lean = lean if lean is not None else (rng.range(-0.35, 0.35), rng.range(-0.15, 0.15))
    tp = arch.trunk_path(H_t, lean=lean, wobble=0.06, seed=seed, n=40)
    r0 = rng.range(0.28, 0.36)
    p.tube(tp, lambda t: r0 * (1 + 0.6 * math.exp(-t * 30)) * (1 - 0.82 * t) + 0.03, bark, R.PART_TRUNK, dens=2.6)
    p.trunk_top = tp[int(len(tp) * 0.55)]
    # dead branch stubs below the crown (sugi self-prunes): short, thin, a few
    for k in range(rng.int(2, 4)):
        h = rng.range(crown_base * 0.45, crown_base * 0.92)
        a = rng.range(0, 2 * math.pi)
        st = arch.point_on(tp, h / H_t)
        L = rng.range(0.5, 1.1)
        en = st + np.array([math.cos(a) * L, -0.15 * L, math.sin(a) * L])
        p.tube(np.array([st, (st + en) / 2 + [0, 0.05, 0], en]), np.array([0.06, 0.045, 0.03]), bark, R.PART_LIMB, dens=3.0)
    # dark spire inside: what the gaps between tiers show
    deep = p.material('cedarDeep', PAL['cedar'])
    env_c = arch.point_on(tp, (crown_base + H_t) / 2 / H_t)
    env = p.envelope(env_c, np.array([base_r * 0.9, (H_t - crown_base) / 2, base_r * 0.9]))
    # tiers from the bottom up: each tier is a skirt of drooping tufts around the axis, with a dark
    # gap under it (the spire inside shows), narrowing to a sharp leader
    y = crown_base
    tier = 0
    while y < H_t - 0.25:
        t = (y - crown_base) / (H_t - crown_base)
        prof = (1 - t) ** 1.05 if t < 0.82 else (1 - 0.82) ** 1.05 * (1 - (t - 0.82) / 0.18) ** 0.8
        rad = base_r * prof * (1 - thin * 0.25) + 0.18
        axis = arch.point_on(tp, y / H_t)
        n_tufts = max(3, int(rad * 4.2))
        ph = rng.range(0, 2 * math.pi)
        for j in range(n_tufts):
            a = ph + j * 2 * math.pi / n_tufts + rng.range(-0.25, 0.25)
            rr = rad * rng.range(0.55, 0.80)
            droop = rr * 0.42
            c = axis + np.array([math.cos(a) * rr, -droop + rng.range(-0.08, 0.08), math.sin(a) * rr])
            sz = rng.range(0.42, 0.56) * (0.65 + 0.5 * (1 - t))
            p.mass(c, np.array([sz * 1.2, sz * 0.48, sz * 1.2]), leaf, env, cell_r=0.12,
                   bumps=(8, 12, 0.24, 0.44), flat=0.8, sway=0.25 + 0.6 * t)
            p.tube(np.array([axis, (axis + c) / 2 + [0, 0.06, 0], c]), np.array([0.07, 0.05, 0.035]), bark,
                   R.PART_LIMB, dens=3.0, cast=False)
        p.mass(axis + np.array([0, 0.05, 0]), np.array([rad * 0.42 + 0.15, 0.34, rad * 0.42 + 0.15]), leaf, env,
               cell_r=0.12, bumps=(8, 12, 0.24, 0.44), flat=0.8, sway=0.2 + 0.6 * t)
        y += rng.range(0.70, 0.95) * (0.8 if t > 0.6 else 1.0)
        tier += 1
    # the leader: a spike at the very top
    top = tp[-1]
    p.mass(top + np.array([0, -0.05, 0]), np.array([0.26, 0.55, 0.26]), leaf, env, cell_r=0.10, bumps=(6, 9, 0.2, 0.3), sway=1.0)
    p.interior(env_c + np.array([0, -0.2, 0]), np.array([base_r * 0.42, (H_t - crown_base) / 2 * 0.9, base_r * 0.42]), deep)
    p.leaf_opts.update(dict(w_env=0.55, inset=0.12, hl_p=0.35, crest_p=0.45, inner_margin=4,
                            k_direct=0.60, k_sky=0.30, edge_p=0.6))
    return p


# ------------------------------------------------------------------------------------------ red pine
def red_pine(name, seed, height=None):
    """Akamatsu as the owner liked v0.1's pines: a bending red trunk and a crown of flat layered
    plates (5-7 layers, widest in the middle), each plate held by its own branch."""
    rng = Rng(seed)
    H_t = height if height is not None else rng.range(9.5, 12.5)
    spread = rng.range(2.6, 3.4)
    W = int(spread * 2 * 20 + 130)
    Hc = int((H_t + 2.0) * 20 + 40)
    p = Plant(name, W, Hc, W // 2, Hc - 24, seed)
    p.meta['species'] = 'red_pine'
    needle = p.material('pine', PAL['pine'])
    bark = p.material('barkPine', PAL['barkPine'])
    red = p.material('barkPineRed', PAL['barkPineRed'])
    moss = p.material('moss', PAL['moss'])
    p.bark_fx[bark] = arch.bark_plates(seed, red_mat=red, red_from=H_t * 0.30, moss_mat=moss)
    p.bark_fx[red] = arch.bark_plates(seed + 1)
    side = rng.sign()
    lean = (side * rng.range(0.6, 1.6), rng.range(-0.3, 0.3))
    tp = arch.trunk_path(H_t * 0.88, lean=lean, wobble=0.30, seed=seed, n=40, bend=0.6)
    r0 = rng.range(0.22, 0.27)
    p.tube(tp, lambda t: r0 * (1 + 0.5 * math.exp(-t * 25)) * (1 - 0.62 * t) + 0.04, bark, R.PART_TRUNK, dens=2.6, cap=False)
    top = tp[-1]
    p.trunk_top = top
    crown_from = rng.range(0.42, 0.52)
    n_layers = rng.int(5, 7)
    deep = p.material('pineDeep', PAL['pine'])
    k = 0
    for L in range(n_layers):
        tf = crown_from + (1 - crown_from) * L / (n_layers - 1)
        mid = 1 - abs((L / (n_layers - 1)) - 0.35) * 1.15            # widest a little below the middle
        width = spread * max(0.35, mid) * rng.range(0.85, 1.05)
        anchor = arch.point_on(tp, min(1.0, tf))
        sides = [rng.sign()] if (L % 2 == 0 and L < n_layers - 1) else [-1, 1]
        if L == n_layers - 1:
            sides = [0]
        for sd in sides:
            reach = width * rng.range(0.55, 0.80) if sd else 0.2
            a = (0 if sd > 0 else math.pi) + rng.range(-0.55, 0.55)
            c = anchor + np.array([math.cos(a) * reach, rng.range(0.25, 0.55), math.sin(a) * reach * 0.7])
            if sd:
                path = arch.limb_to(anchor, c, rise=0.25, seed=seed * 13 + k, n=16)
                rb = r0 * rng.range(0.35, 0.45) * (1.25 - tf * 0.5)
                p.tube(path, arch.collar(np.linspace(rb, rb * 0.5, len(path)), k=1.3), red, R.PART_LIMB, dens=2.6)
            w = width * rng.range(0.55, 0.72) if sd else width * 0.55
            e = p.envelope(c + np.array([0, -0.05, 0]), np.array([w * 1.2, 0.55, w * 1.0]))
            # a plate: a flat central pad and lobes along its rim, all thin
            sway = 0.45 + 0.5 * L / n_layers
            p.mass(c, np.array([w, 0.36, w * 0.82]), needle, e, cell_r=0.16, bumps=(7, 11, 0.20, 0.36), flat=0.55,
                   sway=sway)
            for j in range(rng.int(3, 5)):
                aa = rng.range(0, 2 * math.pi)
                off = np.array([math.cos(aa) * w * 0.62, rng.range(-0.10, 0.06), math.sin(aa) * w * 0.50])
                ww = w * rng.range(0.38, 0.55)
                p.mass(c + off, np.array([ww, 0.30, ww * 0.85]), needle, e, cell_r=0.15, bumps=(7, 11, 0.20, 0.36),
                       flat=0.55, sway=min(1.0, sway + 0.1))
            p.interior(c + np.array([0, -0.08, 0]), np.array([w * 0.75, 0.22, w * 0.6]), deep)
            k += 1
    p.leaf_opts.update(dict(w_env=0.66, inset=0.16, hl_p=0.30, crest_p=0.40, k_direct=0.66, k_sky=0.30,
                            self_shadow=0.45, shadow_floor=0.38, inner_margin=3))
    return p
