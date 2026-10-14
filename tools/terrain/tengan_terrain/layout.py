"""Layout JSON (vector data) -> world-space rasters.

The world is a stack of flat levels (heights in 0.5 m steps) with organic
outlines, plus stairs, gentle ramps, water, material patches and roads.
See tools/terrain/README.md for the schema. Units: metres, x east, z south,
h up; rasters are 20 px per metre."""
import json
import numpy as np
from scipy import ndimage as ndi

from . import geom, noise
from .geom import PPM

# ---- top materials (horizontal surfaces) -------------------------------------
TOP = {
    'void': 0, 'meadow': 1, 'lawn': 2, 'moss': 3, 'forest': 4, 'dirt': 5, 'earth': 6, 'gravel': 7,
    'tread': 8, 'paving': 9, 'rock': 10, 'cheek': 11, 'water': 12, 'wetbank': 13, 'scree': 14,
}
TOP_NAME = {v: k for k, v in TOP.items()}
# ---- face styles (the visible south-facing wall below an upper surface) ------
FACE = {'none': 0, 'rock': 1, 'earth': 2, 'wall': 3, 'riser': 4, 'cheekface': 5, 'bank': 6, 'rampfill': 7, 'wetbank': 8}
FACE_NAME = {v: k for k, v in FACE.items()}
# ---- surface kinds -------------------------------------------------------------
KIND = {'level': 1, 'ramp': 2, 'tread': 3, 'cheek': 4, 'water': 5, 'landing': 6}


class World:
    """All world-space rasters for one region."""

    def __init__(self, spec):
        self.spec = spec
        b = spec['bounds']
        self.frame = geom.Frame(*b)
        H, W = self.frame.H, self.frame.W
        self.H, self.W = H, W
        self.seed = int(spec.get('seed', 1))
        self.void_h = float(spec.get('void_height', -12.0))
        self.h = np.full((H, W), np.nan, np.float32)        # walkable/visible surface height (m)
        self.sid = np.zeros((H, W), np.int32)               # surface id (index into self.surfaces)
        self.top = np.zeros((H, W), np.uint8)               # TOP id
        self.face = np.zeros((H, W), np.uint8)              # FACE id used when this cell is the upper side of a drop
        self.water = np.full((H, W), np.nan, np.float32)    # water surface (m) where there is water
        self.wdepth = np.zeros((H, W), np.float32)          # water depth (m)
        self.stair_k = np.full((H, W), -1, np.int16)        # step index on stairs (0 = bottom tread)
        self.stair_u = np.zeros((H, W), np.float32)         # px across the flight from its west edge
        self.stair_v = np.zeros((H, W), np.float32)         # px into the tread from its front (south) edge
        self.road_d = np.full((H, W), 1e6, np.float32)      # px to the nearest road centreline
        self.road_hw = np.zeros((H, W), np.float32)         # that road's half width (px)
        self.road_along = np.zeros((H, W), np.float32)
        self.road_side = np.zeros((H, W), np.float32)
        self.road_kind = np.zeros((H, W), np.uint8)         # TOP id of that road's surface
        self.road_wear = np.zeros((H, W), np.float32)
        self.road_curv = np.zeros((H, W), np.float32)       # signed curvature proxy (outer side of bends)
        self.patch = np.zeros((H, W), np.float32)           # generic 0..1 field written by patches ('wild', 'wear')
        self.wild = np.zeros((H, W), np.float32)            # vegetation wildness 0..1 (meadow vs lawn detail)
        self.surfaces = [{'id': 'void', 'kind': 0}]
        self.markers = []
        self.notes = []

    # -------------------------------------------------------------------------
    def _new_surface(self, **kw):
        self.surfaces.append(kw)
        return len(self.surfaces) - 1

    def anchors_damp(self):
        """1 far from stairs/ramps, 0 near them: straightens organic edges where they attach."""
        H, W = self.H, self.W
        m = np.zeros((H, W), bool)
        f = self.frame
        for st in self.spec.get('stairs', []):
            x, zb = st['x'], st['z_bottom']
            w = st['width'] / 2 + st.get('cheek', 0.5) + st.get('wall', 1.2)
            n, tr = st['steps'], st.get('tread', 0.42)
            ztop = zb - (n - 1) * tr - st.get('landing', 0.8)
            j0, j1 = int((x - w - f.x0) * PPM), int((x + w - f.x0) * PPM)
            i0, i1 = int((ztop - f.z0) * PPM), int((zb + st.get('apron', 0.8) - f.z0) * PPM)
            m[max(i0, 0):max(i1, 0), max(j0, 0):max(j1, 0)] = True
        for rp in self.spec.get('ramps', []):
            m |= geom.fill_polygon(f, rp['shape'])
        if not m.any():
            return None
        d = ndi.distance_transform_edt(~m) / PPM
        return geom.smoothstep(0.5, 3.5, d).astype(np.float32)

    # -------------------------------------------------------------------------
    def build(self):
        spec = self.spec
        damp = self.anchors_damp()
        for i, lv in enumerate(spec.get('levels', [])):
            self._level(lv, i, damp)
        for rp in spec.get('ramps', []):
            self._ramp(rp)
        for st in spec.get('stairs', []):
            self._stair(st)
        for wt in spec.get('water', []):
            self._water(wt)
        for pt in spec.get('patches', []):
            self._patch(pt)
        for rd in spec.get('roads', []):
            self._road(rd)
        self._wildness()
        for mk in spec.get('markers', []):
            self._marker(mk)
        return self

    def _level(self, lv, i, damp):
        edge = lv.get('edge', {})
        seed = self.seed * 1000 + 37 * i + int(lv.get('seed', 0))
        if lv.get('rect'):
            m = geom.fill_polygon(self.frame, lv['shape'])
        else:
            m = geom.organic_mask(self.frame, lv['shape'], edge, seed, damp=damp, smooth=lv.get('smooth', True))
        if 'clip' in lv:   # optional: only inside another polygon (e.g. a level that must stay inside its parent)
            m &= geom.fill_polygon(self.frame, lv['clip'])
        s = self._new_surface(id=lv.get('id', f'level{i}'), kind=KIND['level'], height=float(lv['height']))
        self.h[m] = lv['height']
        self.sid[m] = s
        self.top[m] = TOP[lv.get('top', 'meadow')]
        self.face[m] = FACE[lv.get('face', 'rock')]
        if 'wild' in lv:
            self.patch_wild = getattr(self, 'patch_wild', np.zeros_like(self.wild))
            self.patch_wild[m] = lv['wild']

    def _ramp(self, rp):
        f = self.frame
        m = geom.fill_polygon(f, rp['shape']) if rp.get('exact', True) else geom.organic_mask(f, rp['shape'], rp.get('edge', {}), self.seed + 77)
        A = np.array(rp['from']['at'], np.float64)
        B = np.array(rp['to']['at'], np.float64)
        ha, hb = float(rp['from']['height']), float(rp['to']['height'])
        L = np.linalg.norm(B - A)
        slope = abs(hb - ha) / max(L, 1e-6)
        if slope > 1 / 3 + 1e-6:
            self.notes.append(f"ramp {rp.get('id')}: slope 1:{1/slope:.2f} is steeper than 1:3")
        X, Y = f.grid()
        px = X / PPM
        pz = Y / PPM
        t = ((px - A[0]) * (B[0] - A[0]) + (pz - A[1]) * (B[1] - A[1])) / (L * L)
        t = np.clip(t, 0.0, 1.0)
        hh = (ha + (hb - ha) * t).astype(np.float32)
        s = self._new_surface(id=rp.get('id', 'ramp'), kind=KIND['ramp'], slope=slope)
        self.h[m] = hh[m]
        self.sid[m] = s
        if 'top' in rp:
            self.top[m] = TOP[rp['top']]
        self.face[m] = FACE[rp.get('face', 'earth')]
        self.ramp_mask = getattr(self, 'ramp_mask', np.zeros((self.H, self.W), bool)) | m

    def _stair(self, st):
        """A flight climbing north, cut into the cliff between two levels.

        Treads and risers in the middle, stepped stone cheeks on both sides
        (their south faces show), posts at the top, a short landing and apron
        so both ends sit on clean ground, and dressed-stone retaining walls
        straightening the cliff for `wall` metres either side."""
        f = self.frame
        x, zb = float(st['x']), float(st['z_bottom'])
        w2 = st['width'] / 2.0
        c = st.get('cheek', 0.5)
        n = int(st['steps'])
        tr = st.get('tread', 0.42)
        h0, h1 = float(st['from']), float(st['to'])
        dh = (h1 - h0) / n
        curb = st.get('curb', 0.25)
        land = st.get('landing', 0.8)
        apron = st.get('apron', 0.8)
        wall = st.get('wall', 1.2)
        wall_depth = st.get('wall_depth', 2.0)
        ztop = zb - (n - 1) * tr                      # the last riser (up onto the landing)
        # work in a window around the flight
        half = w2 + c + wall + 0.6
        j0 = max(0, int(np.floor((x - half - f.x0) * PPM)))
        j1 = min(self.W, int(np.ceil((x + half - f.x0) * PPM)))
        i0 = max(0, int(np.floor((min(ztop - land, zb - wall_depth) - 0.6 - f.z0) * PPM)))
        i1 = min(self.H, int(np.ceil((zb + apron + 0.6 - f.z0) * PPM)))
        win = (slice(i0, i1), slice(j0, j1))
        Xg, Yg = f.grid()
        X, Y = Xg[win], Yg[win]
        px, pz = X / PPM, Y / PPM
        ax = np.abs(px - x)
        h, sid, top, face = self.h[win], self.sid[win], self.top[win], self.face[win]
        sk, su, sv = self.stair_k[win], self.stair_u[win], self.stair_v[win]
        sid_t = self._new_surface(id=st.get('id', 'stair'), kind=KIND['tread'], height=h0)
        sid_c = self._new_surface(id=st.get('id', 'stair') + '.cheek', kind=KIND['cheek'], height=h0)
        # --- retaining walls beside the flight: straighten the cliff, face it with dressed stone.
        # Only cells of the two levels the flight joins are touched (never a third feature).
        inwall = (ax <= w2 + c + wall) & (pz >= zb - wall_depth) & (pz < zb + apron)
        jit = (noise.fbm(X / 9.0, np.full_like(X, 3.0), self.seed + 911, 2) - 0.5) * 3.0 / PPM
        is0 = np.abs(h - h0) < 0.01
        is1 = np.abs(h - h1) < 0.01
        up = inwall & (pz < zb + jit) & (is0 | is1)
        dn = inwall & (pz >= zb + jit) & (is0 | is1)
        def mode(a, m, default):
            return np.bincount(a[m].ravel()).argmax() if m.any() else default
        upper_sid = mode(sid, up & is1, sid_c)
        lower_sid = mode(sid, dn & is0, sid_t)
        upper_top = mode(top, up & is1, TOP['meadow'])
        lower_top = mode(top, dn & is0, TOP['meadow'])
        h[up] = h1
        sid[up] = upper_sid
        top[up & ~is1] = upper_top
        face[up] = FACE['wall']
        h[dn] = h0
        sid[dn] = lower_sid
        top[dn & ~is0] = lower_top
        # --- the flight
        inx = ax <= w2
        inc = (ax > w2) & (ax <= w2 + c)
        flight = (pz >= ztop) & (pz < zb)
        k = np.clip(np.floor((zb - pz) / tr).astype(np.int32), 0, n - 2)   # 0 = bottom tread
        th = h0 + (k + 1) * dh
        t_mask = inx & flight
        h[t_mask] = th[t_mask]
        sid[t_mask] = sid_t
        top[t_mask] = TOP['tread']
        face[t_mask] = FACE['riser']
        sk[t_mask] = k[t_mask]
        su[t_mask] = ((px - (x - w2)) * PPM)[t_mask]
        sv[t_mask] = ((zb - k * tr - pz) * PPM)[t_mask]      # px from the tread's front edge
        # cheeks: stepped stone curbs `curb` proud of the treads
        c_mask = inc & flight
        ch = np.minimum(th + curb, h1 + curb)
        h[c_mask] = ch[c_mask]
        sid[c_mask] = sid_c
        top[c_mask] = TOP['cheek']
        face[c_mask] = FACE['cheekface']
        sk[c_mask] = k[c_mask]
        su[c_mask] = ((px - x) * PPM)[c_mask]
        sv[c_mask] = ((zb - k * tr - pz) * PPM)[c_mask]
        # posts: the cheeks run one tread onto the landing
        post = inc & (pz >= ztop - tr * 0.9) & (pz < ztop)
        h[post] = h1 + curb
        sid[post] = sid_c
        top[post] = TOP['cheek']
        face[post] = FACE['cheekface']
        sk[post] = n - 1
        su[post] = ((px - x) * PPM)[post]
        sv[post] = ((ztop - pz) * PPM)[post]
        # landing and apron: clean ground at both ends
        landm = (ax <= w2 + c) & (pz >= ztop - land) & (pz < ztop) & ~post
        h[landm] = h1
        sid[landm] = upper_sid
        top[landm & (top == 0)] = upper_top
        face[landm] = np.where(ax[landm] <= w2, FACE['riser'], FACE['wall'])
        apm = (ax <= w2 + c) & (pz >= zb) & (pz < zb + apron)
        h[apm] = h0
        sid[apm] = lower_sid
        top[apm & (top == 0)] = lower_top
        if not hasattr(self, 'stair_mask'):
            self.stair_mask = np.zeros((self.H, self.W), bool)
        self.stair_mask[win] |= t_mask | c_mask | post
        self.stairs_out = getattr(self, 'stairs_out', [])
        self.stairs_out.append({'id': st.get('id'), 'x': x, 'z_bottom': zb, 'z_top': ztop, 'width': st['width'],
                                'from': h0, 'to': h1, 'steps': n, 'tread': tr})

    def _water(self, wt):
        f = self.frame
        m = geom.organic_mask(f, wt['shape'], wt.get('edge', {'amp': 0.25, 'wave': 3, 'rough': 0.08}), self.seed + 501)
        d = geom.sdf(m) / PPM
        s = float(wt['surface'])
        depth = float(wt.get('depth', 0.6))
        prof = geom.smoothstep(0.0, wt.get('shelf', 1.6), d)
        self.water[m] = s
        self.wdepth[m] = (0.04 + depth * prof)[m]
        self.h[m] = s
        self.top[m] = TOP['water']
        self.face[m] = FACE['wetbank']
        sid = self._new_surface(id=wt.get('id', 'water'), kind=KIND['water'], height=s)
        self.sid[m] = sid
        # a wet margin of soil round the water, wide in places and pinched to nothing in others
        X, Y = f.grid()
        width = wt.get('wet', 0.5) * PPM * np.clip(noise.fbm(X / 40.0, Y / 40.0, self.seed + 503, 2) * 1.8 - 0.25, 0.15, 1.3)
        ring = (~m) & (ndi.distance_transform_edt(~m) < width)
        ring &= np.isin(self.top, [TOP['meadow'], TOP['lawn'], TOP['moss'], TOP['forest'], TOP['earth']])
        self.top[ring] = TOP['wetbank']

    def _patch(self, pt):
        f = self.frame
        m = geom.organic_mask(f, pt['shape'], pt.get('edge', {'amp': 0.6, 'wave': 3, 'rough': 0.2, 'bite': 0.5}), self.seed + 701 + len(pt['shape']))
        if 'on' in pt:
            m &= np.isin(self.top, [TOP[t] for t in pt['on']])
        if 'top' in pt:
            self.top[m] = TOP[pt['top']]
        if 'face' in pt:
            self.face[m & ~np.isnan(self.h)] = FACE[pt['face']]
        if 'wild' in pt:
            self.patch_wild = getattr(self, 'patch_wild', np.zeros_like(self.wild))
            self.patch_wild[m] = pt['wild']
        if 'wear' in pt:
            self.patch[m] = np.maximum(self.patch[m], pt['wear'])

    def _road(self, rd):
        f = self.frame
        dist, along, side, total = geom.polyline_field(f, rd['points'])
        hw = rd['width'] / 2.0 * PPM
        X, Y = f.grid()
        # the edge wanders: worn wider in places, grass tongues biting in elsewhere
        near = dist < hw + 3 * PPM
        wob = np.zeros_like(dist)
        wob[near] = (noise.fbm(X[near] / 37.0, Y[near] / 37.0, self.seed + 333, 3) - 0.5) * 2.0 * rd.get('wobble', 0.22) * PPM
        dd = dist + wob
        closer = dd < self.road_d
        self.road_d = np.where(closer, dd, self.road_d)
        self.road_hw = np.where(closer, hw, self.road_hw)
        self.road_along = np.where(closer, along, self.road_along)
        self.road_side = np.where(closer, side, self.road_side)
        self.road_kind = np.where(closer, TOP[rd.get('surface', 'dirt')], self.road_kind)
        self.road_wear = np.where(closer, rd.get('wear', 0.7), self.road_wear)
        on = (dd < hw) & np.isin(self.top, [TOP[t] for t in ('meadow', 'lawn', 'moss', 'forest', 'earth', 'wetbank', 'scree', 'rock')])
        if 'only_height' in rd:
            on &= np.abs(self.h - rd['only_height']) < 0.01
        self.top[on] = TOP[rd.get('surface', 'dirt')]

    def _wildness(self):
        """How much small vegetation detail a ground pixel gets (0 calm .. 1 wild)."""
        X, Y = self.frame.grid()
        base = noise.fbm(X / 160.0, Y / 160.0, self.seed + 61, 3)
        w = geom.smoothstep(0.3, 0.75, base) * 0.6
        if hasattr(self, 'patch_wild'):
            w = np.maximum(w * 0.5, self.patch_wild) if self.patch_wild.any() else w
        self.wild = w.astype(np.float32)

    def _marker(self, mk):
        x, z = mk['at']
        j = int((x - self.frame.x0) * PPM)
        i = int((z - self.frame.z0) * PPM)
        h = float(self.h[i, j]) if 0 <= i < self.H and 0 <= j < self.W and not np.isnan(self.h[i, j]) else None
        o = dict(mk)
        o['ground_h'] = h
        self.markers.append(o)


def load(path):
    with open(path, 'r', encoding='utf-8') as fh:
        spec = json.load(fh)
    if spec.get('format') != 'tengan-terrain/1':
        raise ValueError('not a tengan-terrain/1 layout: ' + str(spec.get('format')))
    return spec
