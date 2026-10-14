"""大楠 the great camphor (御神木) at the shrine clearing: one organism.

Buttress fins flare out of the trunk and run on as surface roots over the ground; the trunk carries
a shimenawa with shide; eight main limbs (two long low ones reaching west over the hut and east over
the shrine) leave the trunk and end inside the foliage masses they carry, so the crown is held by
its limbs instead of floating above a stump. ~22 m crown, ~3.2 m trunk, buttresses ~6 m across.
Modelled in natural metres (plant.py): the canopy's cast shade covers the clearing.
"""
import math

import numpy as np

from .. import arch
from .. import raster as R
from ..core import PPM, Rng, normalize, vnoise2
from ..palette import PAL
from ..plant import Plant


def _rope_fx(seed):
    def fx(u, v, n, P, base, T):
        tw = ((u * 7.5 + v * 1.0 / math.pi) % 1.0)
        dv = np.where(tw < 0.45, 0.12, -0.06) + np.where(tw > 0.86, -0.16, 0.0)
        return dv, None
    return fx


def _camphor_bark(seed, moss, lichen):
    base_fx = arch.bark_furrowed(seed, depth=0.24, lichen_mat=lichen)

    def fx(u, v, n, P, base, T):
        dv, mat = base_fx(u, v, n, P, base, T)
        # moss: cushions on the buttresses and lower trunk, more on the shaded north-west side,
        # and along the top of the big limbs
        q = vnoise2(P[:, 0] * 1.1 + P[:, 2] * 0.7, P[:, 1] * 0.9, seed + 21) * 0.72 + \
            vnoise2(P[:, 0] * 3.5, P[:, 1] * 3.5 + P[:, 2], seed + 22) * 0.28
        low = np.clip(1.0 - P[:, 1] / 2.6, 0, 1)
        side = np.clip(-P[:, 0] * 0.2 - P[:, 2] * 0.25, -0.3, 0.3)
        up = np.clip(n[:, 1], 0, 1)
        k = 0.70 - low * 0.20 - side * 0.35 - up * 0.18
        mm = (q > k) & (dv > -0.15)
        mat = np.where(mm & (mat == 0), moss, mat)
        dv = np.where(mm, dv * 0.25 + (q - k) * 0.7 - 0.05, dv)
        return dv, mat
    return fx


def _limb_bark(seed, moss):
    base_fx = arch.bark_furrowed(seed + 3, depth=0.10, n_furrows=9)

    def fx(u, v, n, P, base, T):
        dv, mat = base_fx(u, v, n, P, base, T)
        q = vnoise2(P[:, 0] * 1.4, P[:, 2] * 1.4 + P[:, 1], seed + 31)
        mm = (n[:, 1] > 0.35) & (q > 0.45)          # moss along the top of the limbs
        mat = np.where(mm, moss, mat)
        dv = np.where(mm, -0.06, dv)
        return dv, mat
    return fx


def camphor(name='camphor_a', seed=1):
    rng = Rng(seed)
    W, H = 640, 600
    ax, ay = 320, 500
    p = Plant(name, W, H, ax, ay, seed)
    p.meta['species'] = 'camphor'
    leaf = p.material('camphor', PAL['camphor'])
    new = p.material('camphorNew', PAL['camphorNew'])
    bark = p.material('barkCamphor', PAL['barkCamphor'])
    moss = p.material('moss', PAL['moss'])
    lichen = p.material('lichen', PAL['lichen'])
    rope = p.material('rope', PAL['rope'])
    paper = p.material('paper', PAL['paper'])
    p.bark_fx[bark] = _camphor_bark(seed, moss, None)
    limb_bark = p.material('barkCamphorLimb', PAL['barkCamphor'])
    p.bark_fx[limb_bark] = _limb_bark(seed, moss)
    p.bark_fx[rope] = _rope_fx(seed)

    # ---------------- trunk with buttress fins (natural metres)
    Ht = 7.4
    lean = (rng.range(-0.4, 0.4), rng.range(0.0, 0.4))
    tp = arch.trunk_path(Ht, lean=lean, wobble=0.22, seed=seed, n=48)
    r_at = lambda t: 1.55 - 0.32 * t + 0.08 * math.sin(t * 6.0 + seed)
    nf = 7
    angs = np.linspace(-2.7, 2.5, nf) + np.array([rng.range(-0.15, 0.15) for _ in range(nf)])
    fins = [dict(th=float(a), A=rng.range(1.0, 1.7) * (1.0 if abs(a) < 2.0 else 0.75),
                 Hs=rng.range(0.9, 1.5), p=rng.range(4.0, 7.0)) for a in angs]

    def rfun(s, th, R0):
        out = R0.copy()
        for f in fins:
            c = np.cos(th - f['th'])
            out = out + f['A'] * np.exp(-s / f['Hs']) * np.maximum(0, c) ** f['p']
        out = out + 0.09 * np.sin(th * 5 + s * 0.35 + seed) * np.exp(-s / 3.0) + 0.05 * np.sin(th * 3 - s * 0.5)
        return out

    p.tube(tp, r_at, bark, R.PART_TRUNK, rfun=rfun, dens=2.4, cap=False)
    p.trunk_top = tp[-1]

    # ---------------- surface roots: the front fins run on over the ground and dive into the soil
    def fdir(th):
        return np.array([math.sin(th), 0.0, math.cos(th)])   # 0 = south (toward the camera)

    for k, f in enumerate(fins):
        if abs(f['th']) > 2.3:        # behind the trunk: hidden anyway
            continue
        d = fdir(f['th'])
        r_tip = r_at(0) + f['A']
        start = d * r_tip * 0.85
        front = max(0.0, math.cos(f['th']))           # 1 = straight at the camera
        L = rng.range(1.8, 3.4) * (1 - 0.45 * front)
        ang = math.atan2(d[2], d[0])
        pts = [start.copy()]
        cur = start.copy()
        n = 16
        for i in range(1, n + 1):
            ang += rng.range(-0.14, 0.14)
            cur = cur + np.array([math.cos(ang), 0, math.sin(ang)]) * (L / n)
            pts.append(cur.copy())
        pts = np.array(pts)
        t = np.linspace(0, 1, len(pts))
        rr = (0.40 * (1 - t) ** 1.1 + 0.12) * (1 - 0.35 * front)
        pts[:, 1] = rr * 0.25 - np.clip((t - 0.55) / 0.45, 0, 1) * rr * 1.6
        p.tube(pts, rr, bark, R.PART_ROOT, cast=False, dens=2.2, cap=False)

    # ---------------- shimenawa at ~2.4 m, following the bark, a little lower at the front
    s_r = 2.4
    c_r = arch.point_on(tp, s_r / Ht)
    th = np.linspace(-math.pi, math.pi, 241)
    Rr = rfun(np.full_like(th, s_r), th, np.full_like(th, r_at(s_r / Ht))) - 0.02
    ring = np.stack([c_r[0] + np.sin(th) * Rr, c_r[1] - 0.12 * (1 + np.cos(th)) / 2,
                     c_r[2] + np.cos(th) * Rr], axis=-1)
    p.tube(ring, 0.22, rope, R.PART_DETAIL, cast=False, cap=False, dens=3.0)
    shide_at = [-0.95, -0.36, 0.24, 0.84]

    def draw_shide(pl, cv):
        # 紙垂: a paper strip folded down in four zigzag steps, 2 px wide, hung from the rope
        ringd = pl.D(ring)
        for a in shide_at:
            i = int(np.argmin(np.abs(th - a)))
            P0 = ringd[i]
            sx = int(round(cv.ax + P0[0] * PPM)) - 2
            sy = int(round(cv.ay + (P0[2] - P0[1]) * PPM)) + 4
            D = P0[1] + P0[2] + 0.4
            cells = []
            for k, (dx, y0, y1) in enumerate([(0, 0, 4), (2, 3, 7), (0, 6, 10), (2, 9, 13)]):
                for y in range(y0, y1):
                    for w in range(3):
                        cells.append((sx + dx + w, sy + y, 0.30 if w == 0 else (0.18 if w == 1 else 0.02)))
            for x, y, tone in cells:
                if 0 <= x < cv.W and 0 <= y < cv.H:
                    cv.depth[y, x] = D
                    cv.part[y, x] = R.PART_DETAIL
                    cv.mat[y, x] = paper
                    cv.mass[y, x] = -1
                    cv.n[y, x] = (-0.2 if tone > 0.25 else 0.25, 0.1, 0.95)
                    cv.wpos[y, x] = P0
                    cv.tone[y, x] = tone
    p.wood_details = [draw_shide]

    # ---------------- limbs (natural metres): two long low ones that dip and rise, six that climb
    limbs = [
        # start (m up the trunk), end point, base radius, sag
        (4.0, (-10.6, 6.4, 2.2), 0.80, 0.45),
        (5.3, (10.6, 8.4, -0.6), 0.74, 0.30),
        (6.0, (-5.0, 12.4, 5.4), 0.66, 0.0),
        (6.2, (5.4, 12.8, 5.8), 0.66, 0.0),
        (6.4, (-6.6, 14.4, -4.6), 0.66, 0.0),
        (6.5, (7.0, 14.8, -4.2), 0.66, 0.0),
        (6.9, (0.4, 17.0, -1.8), 0.80, 0.0),
        (6.7, (0.2, 14.0, 7.2), 0.58, 0.0),
    ]
    paths = []
    for k, (s0, end, r0, sag) in enumerate(limbs):
        end = np.array(end) + np.array([rng.range(-0.6, 0.6), rng.range(-0.4, 0.4), rng.range(-0.6, 0.6)])
        start = arch.point_on(tp, min(1.0, s0 / Ht))
        if k == 6:          # the leader is the trunk going on: same radius, no seam, no stump
            start = tp[-1].copy()
            r0 = r_at(1.0) * 0.86
        path = arch.limb_to(start, end, rise=0.55 if sag == 0 else 0.15, seed=seed * 17 + k, n=30, sag=sag)
        if sag > 0:   # the long low limbs: a slow S, dipping out of the trunk and lifting at the tip
            t = np.linspace(0, 1, len(path))
            path[:, 1] += -0.9 * np.sin(t * math.pi) * (1 - t) + 0.8 * t ** 3
            path[:, 2] += 0.9 * np.sin(t * math.pi * 1.3 + seed) * t
        rr = arch.collar(np.linspace(r0, r0 * 0.34, len(path)), k=1.0 if k == 6 else 1.5, length=0.10)
        p.tube(path, rr, limb_bark, R.PART_LIMB, dens=2.4)
        paths.append((path, rr))

    # ---------------- masses: a dome of overlapping masses, each one carried by a branch
    env_c = np.array([0.0, 12.2, 0.6])
    env_r = np.array([12.4, 6.4, 9.6])
    env = p.envelope(env_c, env_r)
    centres = []
    # along the two low limbs: masses hang from them, the limb runs through their upper part
    low_envs = []
    for side, ((path, rr), ts) in enumerate(zip(paths[:2], ([0.40, 0.58, 0.74, 0.88, 1.0], [0.40, 0.57, 0.73, 0.87, 1.0]))):
        a, b = arch.point_on(path, 0.35), arch.point_on(path, 1.0)
        ec = (a + b) / 2 + np.array([0, 1.0, 0])
        er = np.array([abs(b[0] - a[0]) / 2 + 2.5, 2.6, 3.4])
        e_low = p.envelope(ec, er)
        for tm in ts:
            c = arch.point_on(path, tm) + np.array([rng.range(-0.4, 0.4), rng.range(0.0, 0.45), rng.range(-0.6, 0.6)])
            rm = rng.range(1.7, 2.2) * (1.12 if tm > 0.8 else 0.95)
            centres.append((c, rm, e_low))
    # the dome: points on the outer shell of the envelope, none deep below the belly
    golden = math.pi * (3 - math.sqrt(5))
    n_dome = 36
    for i in range(n_dome * 3):
        if len([c for c in centres if c[2] is None]) >= n_dome:
            break
        yv = 1 - (i + 0.5) / (n_dome * 1.4)
        if yv < -0.30:
            break
        rad = math.sqrt(max(0.0, 1 - yv * yv))
        a = golden * i + rng.range(-0.25, 0.25)
        d = np.array([math.cos(a) * rad, yv, math.sin(a) * rad])
        shell = rng.range(0.80, 0.94)
        c = env_c + d * env_r * shell
        rm = rng.range(2.5, 3.2) * (0.9 if yv < 0 else 1.0)
        centres.append((c, rm, None))
    # fork-level masses: short branches near the trunk top make the crown's lower edge uneven
    for x, y, z, rm in [(-2.6, 9.0, 2.6, 1.8), (2.8, 9.4, 2.2, 1.7), (-0.6, 9.8, 4.2, 1.6)]:
        c = np.array([x, y, z]) + np.array([rng.range(-0.4, 0.4), rng.range(-0.3, 0.3), rng.range(-0.4, 0.4)])
        centres.append((c, rm * rng.range(0.9, 1.1), None))
    # attach every mass that is not on a low limb to the nearest point of the limb system
    for c, rm, e_own in centres:
        if e_own is None:
            best = None
            for path, rr in paths:
                d = np.linalg.norm(path - c, axis=1)
                j = int(np.argmin(d + np.linspace(0, 1.5, len(path))[::-1] * 0.3))
                if best is None or d[j] < best[0]:
                    best = (d[j], path[j], rr[j])
            dist, a, ra = best
            if dist > 1.2:
                sp = arch.limb_to(a, c, rise=0.35, seed=int(abs(c[0] * 97 + c[2] * 31)) + seed, n=14)
                r_b = min(0.24, max(0.12, ra * 0.45))
                p.tube(sp, arch.collar(np.linspace(r_b, 0.08, len(sp)), k=1.3), limb_bark, R.PART_LIMB, dens=2.4)
        p.mass(c, np.array([rm, rm * 0.74, rm]), leaf, env if e_own is None else e_own, cell_r=0.27, lit_mat=new)
    # the crown's dark inside, around the fork and along its belly
    deep = p.material('camphorDeep', PAL['camphorDeep'])
    p.interior(np.array([0.0, 11.0, -0.4]), np.array([8.0, 3.2, 6.0]), deep)
    p.leaf_opts.update(dict(w_env=0.55, inset=0.10, hl_p=0.40))
    # collision footprint: trunk and buttresses as drawn on the ground, px from the anchor
    poly = []
    for a in np.linspace(-math.pi, math.pi, 24, endpoint=False):
        rr = float(rfun(np.array([0.3]), np.array([a]), np.array([r_at(0.04)]))[0]) * 0.85
        poly.append([round(math.sin(a) * rr * PPM, 1), round(math.cos(a) * rr * p.kz * PPM, 1)])
    p.collision = poly
    return p
