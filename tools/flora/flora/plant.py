"""Plant = one organism modelled in 3D, drawn once, painted, then split into game layers.

Two spaces:
  natural  the plant as it stands in the world (true metres). Light, the crown's own shadow and
           the shadow cast on the ground are computed here, so the canopy's shade covers the
           ground it really covers.
  drawn    the same model with its north-south depth compressed by `kz` (default core.KZ) before
           projection. This is how a pixel artist draws tall round things in 3/4 view: the trunk
           seen front-on with a shallow base, the crown's underside and the limbs going into it
           visible above the trunk instead of hidden behind the crown's front.

Species modules call tube() / mass() / envelope() in natural coordinates, then render.render().
"""
import math

import numpy as np

from . import raster as R
from .core import (KZ, LIGHT_C, LIGHT_W, PPM, SHADOW_LIGHT_W, Rng, hash01, normalize, poisson_disc_sphere,
                   smoothstep, vnoise3, world_to_cam)

LC = LIGHT_C


class Material:
    def __init__(self, name, ramp, kind='leaf'):
        self.name = name
        self.ramp = np.asarray(ramp, dtype=np.uint8)
        self.kind = kind


class Plant:
    def __init__(self, name, W, H, ax, ay, seed, kind='tree', kz=None):
        self.name = name
        self.seed = seed
        self.rng = Rng(seed)
        self.kind = kind                  # tree | shrub | herb
        self.kz = KZ if kz is None else kz
        self.cv = R.Canvas(W, H, ax, ay)
        self.mats = [None]                # id 0 = none
        self.mat_ids = {}
        self.tube_specs = []              # natural-space wood
        self.masses = []                  # natural-space foliage masses
        self.envs = []                    # natural-space envelopes (c, r)
        self.interiors = []               # natural-space dark inner volumes of the crown
        self.groups = []                  # sway groups for blades that belong to no mass
        self.blades = []                  # natural-space leaf / grass blades (strokes)
        self.single_layer = kind in ('shrub', 'herb')   # one body layer, sorted at its foot
        self.bark_fx = {}                 # mat id -> texture function
        self.leaf_opts = {}
        self.wood_details = []            # callables(plant, cv): drawn with the wood (rope, shide)
        self.details = []                 # callables(plant, cv): drawn after the foliage (fruit)
        self.meta = {'kind': kind, 'seed': seed}
        self.sway_amp = 1.0
        self.trunk_top = np.array([0.0, 3.0, 0.0])

    # ---------------------------------------------------------------- spaces
    def D(self, P):
        """natural -> drawn"""
        P = np.array(P, dtype=np.float64)
        P[..., 2] *= self.kz
        return P

    def Nat(self, P):
        """drawn -> natural"""
        P = np.array(P, dtype=np.float64)
        P[..., 2] /= self.kz
        return P

    # ---------------------------------------------------------------- materials
    def material(self, name, ramp, kind='leaf'):
        if name in self.mat_ids:
            return self.mat_ids[name]
        self.mats.append(Material(name, ramp, kind))
        self.mat_ids[name] = len(self.mats) - 1
        return self.mat_ids[name]

    # ---------------------------------------------------------------- wood
    def tube(self, path, radius, mat, part=R.PART_TRUNK, rfun=None, tone=0.0, cast=True, u0=0.0,
             cap=True, dens=2.6, kz_cs=None, ky=1.0):
        path = np.asarray(path, dtype=np.float64)
        if callable(radius):
            rr = np.array([radius(t) for t in np.linspace(0, 1, len(path))])
        else:
            rr = np.broadcast_to(np.asarray(radius, dtype=np.float64), (len(path),)).copy()
        self.tube_specs.append(dict(path=path, radius=radius, rr=rr, mat=mat, part=part, rfun=rfun,
                                    tone=tone, cast=cast, u0=u0, cap=cap, dens=dens, kz_cs=kz_cs, ky=ky))

    def draw_wood(self, cv):
        for t in self.tube_specs:
            R.tube(cv, self.D(t['path']), t['radius'], t['part'], t['mat'], rfun=t['rfun'],
                   tone=t['tone'], u0=t['u0'], cap=t['cap'], dens=t['dens'],
                   kz=self.kz if t.get('kz_cs') is None else t['kz_cs'], ky=t.get('ky', 1.0))

    # ---------------------------------------------------------------- foliage
    def envelope(self, c, r):
        self.envs.append((np.asarray(c, float), np.asarray(r, float)))
        return len(self.envs) - 1

    def mass(self, c, r, mat, env, cell_r=0.26, flat=0.62, density=1.0, core=0.93, protrude=0.12,
             tone=0.0, sway=None, lit_mat=None, hl=1.0, under=None, bumps=(4, 7, 0.10, 0.24),
             shape='blob', fringe=0.0):
        """A foliage mass (natural space ellipsoid) covered with leaf clumps. cell_r: clump radius
        (m); flat: clump thickness / width; core: the inner shell between clumps; sway: 0..1
        flexibility (default: from its reach out of the trunk); lit_mat: material for the sunlit
        clumps (new growth); under: material for the shaded underside."""
        self.masses.append(dict(c=np.asarray(c, float), r=np.asarray(r, float), mat=mat, env=env,
                                cell_r=cell_r, flat=flat, density=density, core=core,
                                protrude=protrude, tone=tone, sway=sway, lit_mat=lit_mat, hl=hl,
                                under=under, bumps=bumps, shape=shape, fringe=fringe))
        return len(self.masses) - 1

    def group(self, c, sway):
        """A sway group (bamboo spray, grass tuft) for blades that belong to no foliage mass."""
        self.groups.append(dict(c=np.asarray(c, float), sway=float(sway)))
        return len(self.groups) - 1

    def blade(self, pts, widths, mat, group=None, mass=None, face=(0.0, 1.0, 0.0), tone=0.0, fold=0.55,
              part=None, kind='leaf'):
        """A leaf or grass blade: a ribbon along natural points `pts` (N, 3), `widths` in px per
        point. face: the natural-space direction its blade plane faces (lit by it). fold tilts the
        normal across the blade (a midrib), so the lit half and the shaded half read."""
        self.blades.append(dict(pts=np.asarray(pts, float), w=np.broadcast_to(np.asarray(widths, float), (len(pts),)).copy(),
                                mat=mat, group=group, mass=mass, face=np.asarray(face, float), tone=tone,
                                fold=fold, part=R.PART_BLADE if part is None else part, kind=kind))

    def draw_blades(self, cv):
        if not self.blades:
            return
        nm = len(self.masses)
        base_id = len(self.c_pos) if hasattr(self, 'c_pos') else 0
        for bi, b in enumerate(self.blades):
            P = self.D(b['pts'])
            sx = cv.ax + P[:, 0] * PPM
            sy = cv.ay + (P[:, 2] - P[:, 1]) * PPM
            D = P[:, 1] + P[:, 2]
            face_c = world_to_cam(normalize(b['face']))
            mid = b['mass'] if b['mass'] is not None else (nm + b['group'] if b['group'] is not None else -1)
            n = len(P)
            for i in range(n - 1):
                x0, y0, x1, y1 = sx[i], sy[i], sx[i + 1], sy[i + 1]
                L = math.hypot(x1 - x0, y1 - y0)
                if L < 1e-3:
                    continue
                dx, dy = (x1 - x0) / L, (y1 - y0) / L
                perp = np.array([-dy, -dx, 0.0])          # screen perpendicular, camera space (y up)
                t0, t1 = i / (n - 1), (i + 1) / (n - 1)
                fold = b['fold']

                def ncam(t, s_, perp=perp, face_c=face_c, fold=fold):
                    nn = face_c[None, :] + perp[None, :] * (s_[:, None] * fold)
                    return normalize(nn)
                R.stroke2d(cv, x0, y0, x1, y1, b['w'][i] / 2, b['w'][i + 1] / 2, D[i] + 0.01, D[i + 1] + 0.01, ncam, {
                    'part': b['part'], 'mat': b['mat'], 'cell': base_id + bi, 'mass': mid, 'tone': b['tone'],
                    'u': (lambda t, s_, t0=t0, t1=t1: t0 + (t1 - t0) * t), 'v': (lambda t, s_: s_),
                    'wpos': (lambda t, s_, a=P[i], c=P[i + 1]: a[None, :] + (c - a)[None, :] * t[:, None]),
                })

    def shade_blades(self, cv, sel):
        """Blades: flat light per blade from its facing, a lit half and a shaded half across it,
        tips a step lighter; jittered per blade so a tuft is not one flat shape."""
        ys, xs = np.nonzero(sel)
        if not len(ys):
            return
        o = self.leaf_opts
        n = cv.n[ys, xs]
        P = self.Nat(cv.wpos[ys, xs])
        T = self.transmission(P, noise=0.5) if self.masses else np.ones(len(ys))
        lam = n @ LC
        u = cv.u[ys, xs]
        cid = cv.cell[ys, xs]
        jit = (hash01(cid, np.int64(self.seed) + 61) - 0.5) * o.get('blade_jitter', 0.25)
        v = (o.get('blade_base', 0.22) + 0.62 * np.maximum(0, lam) * (0.35 + 0.65 * T)
             + o.get('blade_tip', 0.12) * u + jit + cv.tone[ys, xs])
        mats = cv.mat[ys, xs]
        nt = np.array([len(self.mats[int(m)].ramp) for m in mats])
        self.tidx[ys, xs] = np.clip(np.floor(v * nt), 0, nt - 1).astype(np.int16)
        self.tmat[ys, xs] = mats
        self.nrm[ys, xs] = n

    def interior(self, c, r, mat):
        """The crown's dark inside: what a gap between masses shows (limbs pass in front of it)."""
        self.interiors.append(dict(c=np.asarray(c, float), r=np.asarray(r, float), mat=mat))

    # ---------------------------------------------------------------- the crown's own shadow
    def transmission(self, P, exclude=None, dens_k=1.0, noise=0.55, L=None):
        """Light transmission from natural points P (N, 3) toward a light (default: the shading
        light) through the masses, dappled by a 3D noise. exclude: (N,) mass id to skip."""
        P = np.atleast_2d(P)
        tau = np.zeros(len(P))
        if not self.masses:
            return np.ones(len(P))
        L = LIGHT_W if L is None else L
        for mi, m in enumerate(self.masses):
            c, r = m['c'], m['r'] * 0.92
            o = (P - c) / r
            d = L / r
            a = np.dot(d, d)
            b = 2 * o @ d
            cc = np.einsum('ij,ij->i', o, o) - 1
            disc = b * b - 4 * a * cc
            hit = disc > 0
            sq = np.sqrt(np.maximum(disc, 0))
            t0 = (-b - sq) / (2 * a)
            t1 = (-b + sq) / (2 * a)
            chord = np.where(hit, np.maximum(0, t1 - np.maximum(t0, 0)), 0)
            if exclude is not None:
                chord = np.where(exclude == mi, 0, chord)
            dens = 1.25 * m['density'] / max(0.5, float(np.mean(m['r'])))
            tau += chord * dens
        if noise:
            q = P * 1.7
            nz = vnoise3(q[:, 0], q[:, 1] * 0.7, q[:, 2], self.seed + 5)
            tau *= (1 - noise) + noise * 2 * nz
        return np.exp(-tau * dens_k)

    # ---------------------------------------------------------------- foliage geometry
    def _clusters(self):
        rng = Rng(self.seed * 7 + 11)
        C, Rr, M, OFF, MAT, BUMP = [], [], [], [], [], []
        for mi, m in enumerate(self.masses):
            c, r = m['c'], m['r']
            cr = m['cell_r']
            p = 1.6075
            a_, b_, c_ = r
            area = 4 * math.pi * (((a_ * b_) ** p + (a_ * c_) ** p + (b_ * c_) ** p) / 3) ** (1 / p)
            n = int(area / (math.pi * cr * cr) * 1.35 * m['density']) + 6
            d = poisson_disc_sphere(n, rng)
            nw = normalize(d / r)
            ncam = world_to_cam(nw * np.array([1, 1, 1]))
            keep = ncam[:, 2] > -0.25                   # back clumps are never seen
            d = d[keep]
            k = len(d)
            jitter = 1 + rng.g.uniform(-m['protrude'], m['protrude'] * 0.6, size=k)
            pos = c + d * r * jitter[:, None]
            rad = cr * rng.g.uniform(0.62, 1.38, size=k) ** 1.2
            if m.get('fringe', 0) > 0:
                # sprays hanging from the underside: the lower edge is ragged, not a smooth arc
                nf = int(math.pi * (r[0] + r[2]) / cr * m['fringe'])
                th = rng.g.uniform(0, 2 * math.pi, size=nf)
                dy = rng.g.uniform(-0.85, -0.45, size=nf)
                rad_h = np.sqrt(np.maximum(0, 1 - dy * dy))
                df = np.stack([np.cos(th) * rad_h, dy, np.sin(th) * rad_h], axis=-1)
                keep_f = world_to_cam(normalize(df / r))[:, 2] > -0.2
                df = df[keep_f]
                drop = rng.g.uniform(0.4, 1.2, size=len(df)) * cr
                pf = c + df * r - np.array([0, 1.0, 0]) * drop[:, None]
                pos = np.concatenate([pos, pf])
                rad = np.concatenate([rad, cr * rng.g.uniform(0.55, 0.85, size=len(df))])
                d = np.concatenate([d, df])
                k = len(pos)
            C.append(pos)
            Rr.append(np.stack([rad, rad * m['flat'], rad], axis=-1))
            M.append(np.full(k, mi))
            OFF.append(rng.g.uniform(-0.5, 0.5, size=k))
            MAT.append(np.full(k, m['mat']))
            bk = m['bumps']
            BUMP.append(np.stack([rng.g.integers(bk[0], bk[1] + 1, size=k).astype(float),
                                  rng.g.uniform(bk[2], bk[3], size=k),
                                  rng.g.uniform(0, 6.283, size=k),
                                  np.full(k, bk[4] if len(bk) > 4 else 0.7)], axis=-1))
        self.c_pos = np.concatenate(C)            # natural
        self.c_rad = np.concatenate(Rr)           # natural
        self.c_mass = np.concatenate(M)
        self.c_off = np.concatenate(OFF)
        self.c_mat = np.concatenate(MAT)
        self.c_bump = np.concatenate(BUMP)
        if getattr(self, 'clump_mat_fn', None) is not None:
            self.c_mat = self.clump_mat_fn(self, self.c_pos, self.c_mass, self.c_mat)

    def draw_foliage(self, cv):
        if not self.masses:
            self.draw_blades(cv)
            return
        self._clusters()
        sq = np.array([1.0, 1.0, self.kz])
        if self.interiors:
            # the dark inside may only show where masses surround it: clip it to the masses'
            # silhouette, shrunk, so its own smooth outline is never exposed
            tmp = R.Canvas(cv.W, cv.H, cv.ax, cv.ay)
            for m in self.masses:
                R.ellipsoids(tmp, self.D([m['c']]), [m['r'] * sq], R.PART_CORE, 1)
            from scipy import ndimage as ndi
            allow = ndi.binary_erosion(tmp.filled, iterations=self.leaf_opts.get('inner_margin', 7))
            for it in self.interiors:
                R.ellipsoids(cv, self.D([it['c']]), [it['r'] * sq], R.PART_INNER, it['mat'], nkz=self.kz,
                             mask=allow)
        for mi, m in enumerate(self.masses):
            R.ellipsoids(cv, self.D([m['c']]), [m['r'] * m['core'] * sq], R.PART_CORE, m['mat'], mass=mi,
                         nkz=self.kz)
        R.ellipsoids(cv, self.D(self.c_pos), self.c_rad * sq, R.PART_LEAF, self.c_mat,
                     cell=np.arange(len(self.c_pos)), mass=self.c_mass, bumps=self.c_bump, nkz=self.kz)
        self.draw_blades(cv)

    # ---------------------------------------------------------------- shading
    def _env_normal(self, P, env_ids):
        n = np.zeros_like(P)
        for ei, (c, r) in enumerate(self.envs):
            sel = env_ids == ei
            if sel.any():
                n[sel] = normalize((P[sel] - c) / (r * r))
        return n

    def shade_wood(self, cv, sel):
        """Bark: banded cylinder light from the key light, the crown's dappled shadow, texture."""
        ys, xs = np.nonzero(sel)
        if len(ys) == 0:
            return
        n = cv.n[ys, xs]
        P = self.Nat(cv.wpos[ys, xs])
        T = self.transmission(P, noise=0.6) if self.masses else np.ones(len(ys))
        lam = n @ LC
        diffuse = np.maximum(0, lam)
        o = self.leaf_opts
        v = 0.12 + 0.58 * diffuse * (0.35 + 0.65 * T) + 0.22 * (0.5 + 0.5 * n[:, 1]) * (0.55 + 0.45 * T) + 0.08 * n[:, 2]
        v = v * o.get('wood_gain', 1.0) + cv.tone[ys, xs]
        mats = cv.mat[ys, xs]
        out_t = np.zeros(len(ys))
        out_m = mats.astype(np.int64).copy()
        for mid in np.unique(mats):
            mm = mats == mid
            fx = self.bark_fx.get(int(mid))
            base = v[mm]
            if fx is not None:
                dv, newmat = fx(cv.u[ys, xs][mm], cv.v[ys, xs][mm], n[mm], P[mm], base, T[mm])
                base = base + dv
                if newmat is not None:
                    out_m[mm] = np.where(newmat > 0, newmat, mid)
            out_t[mm] = base
        nt = np.array([len(self.mats[int(m)].ramp) for m in out_m])
        self.tidx[ys, xs] = np.clip(np.floor(out_t * nt), 0, nt - 1).astype(np.int16)
        self.tmat[ys, xs] = out_m
        self.nrm[ys, xs] = n

    def _leaf_v(self, P, n_mass_w, mass_ids, exclude=None, noise=0.5):
        """Light value 0..1 for foliage at natural points P: the whole crown's form, the mass's
        own form, the key light, the sky, the crown's own (dappled) shadow."""
        o = self.leaf_opts
        env_of = np.array([m['env'] for m in self.masses])
        n_env = self._env_normal(P, env_of[mass_ids])
        w_env = o.get('w_env', 0.40)
        nb = normalize(w_env * n_env + (1 - w_env) * n_mass_w)
        nb_c = world_to_cam(nb)
        T = self.transmission(P, exclude=exclude, noise=noise, dens_k=o.get('self_shadow', 0.55))
        Ts = o.get('shadow_floor', 0.30) + (1 - o.get('shadow_floor', 0.30)) * T
        lam = nb_c @ LC
        direct = np.maximum(0, lam) * Ts
        sky = 0.5 + 0.5 * nb_c[:, 1]
        bounce = np.clip(-nb[:, 1], 0, 1) * o.get('k_bounce', 0.10)
        v = o.get('k_direct', 0.62) * direct + o.get('k_sky', 0.30) * sky * (0.5 + 0.5 * T) + bounce
        v += np.array([m['tone'] for m in self.masses])[mass_ids]
        return v, nb_c, T

    def shade_leaves(self, cv, sel_leaf, sel_core):
        o = self.leaf_opts
        mass_c = np.array([m['c'] for m in self.masses])
        mass_r = np.array([m['r'] for m in self.masses])
        # ---- per clump light (flat over the clump)
        cp = self.c_pos
        n_mass = normalize((cp - mass_c[self.c_mass]) / mass_r[self.c_mass] ** 2)
        v, nb_c, T = self._leaf_v(cp, n_mass, self.c_mass, exclude=self.c_mass, noise=o.get('dapple', 0.5))
        self.c_v, self.c_T, self.c_ncam = v, T, nb_c
        jit = o.get('jitter', 0.28)
        lo = o.get('lo', 1)
        top_res = o.get('top_res', 1)
        gain = o.get('gain', 1.0)
        bias = o.get('bias', 0.0)
        H, W = cv.H, cv.W
        vpix = np.zeros((H, W))
        # ---- inner shell = the mass surface between clumps: same light, per pixel, a step down
        ys, xs = np.nonzero(sel_core)
        if len(ys):
            P = self.Nat(cv.wpos[ys, xs])
            mi = cv.mass[ys, xs]
            nm = normalize((P - mass_c[mi]) / mass_r[mi] ** 2)
            vc, nbc, _ = self._leaf_v(P, nm, mi, exclude=mi, noise=0.5)
            vpix[ys, xs] = vc - o.get('inset', 0.12)
            mats = cv.mat[ys, xs]
            nt = np.array([len(self.mats[int(m)].ramp) for m in mats])
            span = nt - 1 - lo - top_res
            t = np.floor(lo + vpix[ys, xs] * (span + 0.999) * gain + bias)
            t = np.clip(t, 0, nt - 2)
            self.tidx[ys, xs] = t.astype(np.int16)
            self.tmat[ys, xs] = mats
            self.nrm[ys, xs] = normalize(0.7 * nbc + 0.3 * cv.n[ys, xs])
        # ---- the crown's dark inside
        iy, ix = np.nonzero((cv.part == R.PART_INNER) & cv.filled)
        if len(iy):
            lam = cv.n[iy, ix] @ LC
            self.tidx[iy, ix] = np.where((lam > 0.55) & (hash01(iy // 3, ix // 4, np.int64(self.seed)) < 0.5), 1, 0)
            self.tmat[iy, ix] = cv.mat[iy, ix]
            self.nrm[iy, ix] = normalize(np.array([0.0, -0.35, 0.94]) + 0 * cv.n[iy, ix])
        # ---- clumps
        ys, xs = np.nonzero(sel_leaf)
        cid = cv.cell[ys, xs]
        npx = cv.n[ys, xs]
        mats = cv.mat[ys, xs]
        nt = np.array([len(self.mats[int(m)].ramp) for m in mats])
        span = nt - 1 - lo - top_res
        tf = lo + v[cid] * (span + 0.999) * gain + self.c_off[cid] * jit + bias
        t = np.floor(tf)
        vpix[ys, xs] = v[cid]
        band = (t - lo) / np.maximum(1, span)
        hl = npx @ LC
        rnd = hash01(cid, np.int64(self.seed) + 3)
        hl_p = np.array([m['hl'] for m in self.masses])[self.c_mass[cid]] * o.get('hl_p', 0.55)
        top = t >= lo + span
        # highlight = the clump's own upper contour (where nothing nearer sits on it), on the
        # sunlit clumps: a 1 px arc that traces the leaf clump, never a stripe across it
        cellmap = cv.cell
        up_c = np.full_like(cellmap, -2)
        up_c[1:] = cellmap[:-1]
        up_d = np.full(cv.depth.shape, -np.inf)
        up_d[1:] = cv.depth[:-1]
        lf_c = np.full_like(cellmap, -2)
        lf_c[:, 1:] = cellmap[:, :-1]
        lf_d = np.full(cv.depth.shape, -np.inf)
        lf_d[:, 1:] = cv.depth[:, :-1]
        d0 = cv.depth[ys, xs]
        top_edge = ((up_c[ys, xs] != cid) & (up_d[ys, xs] < d0 + 0.02)) | \
                   ((lf_c[ys, xs] != cid) & (lf_d[ys, xs] < d0 + 0.02) & (hl > 0.55))
        # second row of the crescent toward the light: the arc reads as a lit leaf edge, not a crack
        up2_c = np.full_like(cellmap, -2)
        up2_c[2:] = cellmap[:-2]
        ul_c = np.full_like(cellmap, -2)
        ul_c[1:, 1:] = cellmap[:-1, :-1]
        top_edge2 = ((up2_c[ys, xs] != cid) | (ul_c[ys, xs] != cid)) & (hl > o.get('hl_thr2', 0.55))
        crest = top_edge | top_edge2
        t = np.where(top & crest & (hl > o.get('hl_thr', 0.25)) & (rnd < hl_p), t + 1, t)
        # lighter crest on mid-lit clumps too (one tone up), so the light side reads as leaves
        mid_lit = (band > 0.3) & ~top
        rnd2 = hash01(cid, np.int64(self.seed) + 5)
        t = np.where(mid_lit & crest & (hl > 0.35) & (rnd2 < o.get('crest_p', 0.6)), t + 1, t)
        t = np.where((hl < o.get('dk_thr', -0.30)) & (band > 0.3), t - 1, t)
        t = np.clip(t, 0, nt - 1)
        m_out = mats.copy()
        cm = self.c_mass[cid]
        for mi, m in enumerate(self.masses):
            own = (cm == mi) & (mats == m['mat'])
            if m['lit_mat'] is not None:
                sel = own & (v[cid] > o.get('lit_thr', 0.62))
                m_out[sel] = m['lit_mat']
            if m.get('under') is not None:
                sel = own & (v[cid] < o.get('under_thr', 0.25))
                m_out[sel] = m['under']
        self.tidx[ys, xs] = t.astype(np.int16)
        self.tmat[ys, xs] = m_out
        self.nrm[ys, xs] = normalize(0.6 * nb_c[cid] + 0.4 * npx)
        # ---- each clump drops a small shadow down-right onto what lies behind it (lit areas)
        allf = sel_leaf | sel_core
        dep = np.where(allf, cv.depth, -np.inf)
        cell = np.where(sel_leaf, cv.cell, -1)
        massm = np.where(allf, cv.mass, -1)
        # within one mass the clumps merge into one surface; the drop shadow marks where one mass
        # (or a clump standing well proud of the surface) lies over another
        sep_dz = o.get('sep_dz', 0.45)
        shadowed = np.zeros((H, W), bool)
        for k in (1, 2):
            src_d = np.full((H, W), -np.inf)
            src_c = np.full((H, W), -1)
            src_m = np.full((H, W), -1)
            src_d[k:, k:] = dep[:-k, :-k]
            src_c[k:, k:] = cell[:-k, :-k]
            src_m[k:, k:] = massm[:-k, :-k]
            other = (src_m != massm) | (src_d > dep + sep_dz)
            shadowed |= allf & (src_c >= 0) & (src_c != cell) & (src_d > dep + o.get('drop_dz', 0.10)) & other
        lit_here = vpix > o.get('drop_min', 0.42)
        sh = shadowed & lit_here & (hash01(np.where(cell >= 0, cell, 0), np.int64(self.seed) + 29) < o.get('drop_p', 0.85))
        self.tidx[sh] = np.maximum(0, self.tidx[sh] - 1)
        # ---- separation line under clumps that sit on one behind them (lit and half-lit only)
        below = np.full_like(cell, -2)
        below[:-1] = cell[1:]
        dbelow = np.full((H, W), -np.inf)
        dbelow[:-1] = dep[1:]
        below_m = np.full_like(massm, -2)
        below_m[:-1] = massm[1:]
        # the pixel row where a clump disappears behind the clump in front of it: a dark seam
        # (always between masses; inside a mass only on the lit side, where it draws the shingles)
        # shingles only inside a mass: between masses the lit top of the front one against the
        # shaded underside of the one behind already separates them (a seam there reads as a crack)
        edge_between = sel_leaf & (below != cell) & (dbelow > dep + 0.02) & (below >= 0) & (below_m == massm)
        edge_out = sel_leaf & (below != cell) & (dbelow < dep - 0.05) & ((below_m != massm) | (dbelow < dep - sep_dz))
        ey, ex = np.nonzero(edge_out)
        if len(ey):
            self.tidx[ey, ex] = np.maximum(0, self.tidx[ey, ex] - 1)
        edge = edge_between
        ey, ex = np.nonzero(edge)
        if len(ey):
            vv = self.c_v[cv.cell[ey, ex]]
            p_edge = o.get('edge_p', 0.55) * smoothstep(0.30, 0.60, vv)
            hc = hash01(cv.cell[ey, ex], np.int64(self.seed) + 17)
            dark = hc < p_edge
            self.tidx[ey[dark], ex[dark]] = np.maximum(0, self.tidx[ey[dark], ex[dark]] - 1)
        self.vpix = vpix

    # ---------------------------------------------------------------- outlines and cleanup
    def outline(self, sel, k=1, lit_keep=True):
        """Selective outline: silhouette pixels facing away from the light go one tone darker."""
        pad = np.pad(sel, 1)
        empty_r = ~pad[1:-1, 2:]
        empty_d = ~pad[2:, 1:-1]
        empty_l = ~pad[1:-1, :-2]
        empty_u = ~pad[:-2, 1:-1]
        edge_dark = sel & (empty_r | empty_d)
        edge_lit = sel & (empty_l | empty_u) & ~edge_dark
        self.tidx[edge_dark] = np.maximum(0, self.tidx[edge_dark] - k)
        if not lit_keep:
            self.tidx[edge_lit] = np.maximum(0, self.tidx[edge_lit] - 1)
        return edge_dark

    def cleanup(self, sel, keep_top=True):
        """Remove lone pixels whose four neighbours agree on another tone (pixel-art noise)."""
        t = self.tidx.astype(np.int32)
        m = self.tmat.astype(np.int32)
        key = np.where(sel, m * 64 + t, -1)
        pad = np.pad(key, 1, constant_values=-1)
        nb = [pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]]
        same = (nb[0] == nb[1]) & (nb[1] == nb[2]) & (nb[2] == nb[3]) & (nb[0] >= 0)
        lone = sel & same & (key != nb[0])
        if keep_top:
            ntab = np.array([1] + [len(mm.ramp) for mm in self.mats[1:]])
            nt = ntab[np.where(sel, m, 0)]
            lone &= ~((t == nt - 1) & (nb[0] % 64 >= nt - 3))
        self.tidx[lone] = (nb[0][lone] % 64).astype(np.int16)
        self.tmat[lone] = (nb[0][lone] // 64).astype(np.uint8)
        return int(lone.sum())

    def facet_normals(self, sel, group):
        """Average the normal over each (group, tone) patch: dynamic lights then step like the art."""
        ys, xs = np.nonzero(sel)
        if not len(ys):
            return
        key = group[ys, xs].astype(np.int64) * 64 + self.tidx[ys, xs] + self.tmat[ys, xs].astype(np.int64) * 4096
        u, inv = np.unique(key, return_inverse=True)
        acc = np.zeros((len(u), 3))
        np.add.at(acc, inv, self.nrm[ys, xs])
        acc = normalize(acc)
        self.nrm[ys, xs] = normalize(0.75 * acc[inv] + 0.25 * self.nrm[ys, xs])

    # ---------------------------------------------------------------- colour
    def colorize(self, sel):
        H, W = sel.shape
        out = np.zeros((H, W, 4), np.uint8)
        ys, xs = np.nonzero(sel)
        for mid in np.unique(self.tmat[ys, xs]):
            mm = self.tmat[ys, xs] == mid
            rp = self.mats[int(mid)].ramp
            ti = np.clip(self.tidx[ys[mm], xs[mm]], 0, len(rp) - 1)
            out[ys[mm], xs[mm], :3] = rp[ti]
            out[ys[mm], xs[mm], 3] = 255
        return out

    def normal_rgba(self, sel):
        H, W = sel.shape
        out = np.zeros((H, W, 4), np.uint8)
        n = normalize(self.nrm)
        rgb = np.clip(np.round((n * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8)
        out[..., :3] = rgb
        out[..., 3] = np.where(sel, 255, 0)
        out[~sel, :3] = (128, 128, 255)
        return out

    # ---------------------------------------------------------------- shadows on the ground
    def shadow_bounds(self, margin=6):
        """Pixel box (x0, y0, x1, y1) in sprite coordinates that holds the cast shadow."""
        cv = self.cv
        L = SHADOW_LIGHT_W
        xs, zs = [0.0], [0.0]
        for m in self.masses:
            c, r = m['c'], m['r']
            g = c - L * (c[1] / L[1])
            ext = r[0] + r[1] / L[1] * 0.7
            xs += [g[0] - ext, g[0] + ext]
            zs += [g[2] - ext, g[2] + ext]
        for t in self.tube_specs:
            if t['part'] != R.PART_TRUNK:
                continue
            for q in t['path'][::4]:
                g = q - L * (q[1] / L[1])
                xs.append(g[0])
                zs.append(g[2])
        x0 = int(math.floor(cv.ax + min(xs) * PPM)) - margin
        x1 = int(math.ceil(cv.ax + max(xs) * PPM)) + margin
        y0 = int(math.floor(cv.ay + min(zs) * PPM)) - margin
        y1 = int(math.ceil(cv.ay + max(zs) * PPM)) + margin
        return x0, y0, x1, y1

    def ground_shadow(self):
        """Shadow cast on the ground plane (true world scale) by the reference key light.
        Returns crown shade (0..1), trunk shade (0..1) and the box in sprite coordinates."""
        cv = self.cv
        x0, y0, x1, y1 = self.shadow_bounds()
        W, H = x1 - x0, y1 - y0
        gy, gx = np.mgrid[y0:y1, x0:x1]
        X = (gx + 0.5 - cv.ax) / PPM
        Z = (gy + 0.5 - cv.ay) / PPM
        P = np.stack([X.ravel(), np.zeros(X.size), Z.ravel()], axis=-1)
        sh_c = np.zeros(X.size)
        saved = None
        if not self.masses and self.groups and self.kind == 'tree':
            # blade canopies (bamboo): each spray shades the ground like a small, thin mass
            saved = self.masses
            self.masses = [dict(c=g['c'], r=np.array([0.55, 0.35, 0.55]), density=0.55) for g in self.groups]
        if self.masses:
            T = np.ones(X.size)
            for s in range(0, len(P), 200000):
                T[s:s + 200000] = self.transmission(P[s:s + 200000], noise=0.62, dens_k=1.15, L=SHADOW_LIGHT_W)
            sh_c = 1 - T
        if saved is not None:
            self.masses = saved
        sh_t = np.zeros((H, W))
        Lw = SHADOW_LIGHT_W
        for t in self.tube_specs:
            # only trunks cast a line: limbs sit inside the crown, whose shade already covers them
            if t['part'] != R.PART_TRUNK or not t['cast']:
                continue
            path, rr = t['path'], t['rr']
            pts, s = R.resample(path, 0.04)
            s_in = np.r_[0, np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))]
            rad = np.interp(s, s_in, rr) * (0.9 if t['part'] == R.PART_TRUNK else 1.0)
            G = pts - Lw[None, :] * (pts[:, 1] / Lw[1])[:, None]
            gxs = cv.ax + G[:, 0] * PPM - x0
            gys = cv.ay + G[:, 2] * PPM - y0
            for xc, yc, rp in zip(gxs, gys, rad * PPM):
                r = max(0.7, rp)
                xa, xb = max(int(xc - r - 1), 0), min(int(xc + r + 2), W)
                ya, yb = max(int(yc - r - 1), 0), min(int(yc + r + 2), H)
                if xa >= xb or ya >= yb:
                    continue
                yy, xx = np.mgrid[ya:yb, xa:xb]
                d = np.hypot(xx + 0.5 - xc, yy + 0.5 - yc)
                sh_t[ya:yb, xa:xb] = np.maximum(sh_t[ya:yb, xa:xb], (d <= r).astype(float))
        return sh_c.reshape(H, W), sh_t, (x0, y0, x1, y1)
