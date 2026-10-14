"""Bake a prop definition into Godot-ready layers.

  PropDef (solids + lines + layer settings)  --render-->  per-layer G-buffers
  --materials--> ramp + tone per pixel  --light, AO, key shadow-->  tone shift  --snap--> ramp colour
  --outline--> selective outline and contact lines  --> albedo RGBA, normal RGB, emission RGBA
  --heightfield--> horizon shadow map (R top angle, G bottom angle, B contact shade)

See docs/knowledge/19-props.md for the conventions (sizes, light, layers, states, shadows).
"""
import math

import numpy as np
from scipy import ndimage as ndi

from . import palette as PL
from .core import (LIGHT_C, PPM, SHADOW_DIR, SHADOW_MIN_ELEV, cam_to_rgb, hash01, normalize,
                   world_to_cam)
from .render import (Frame, GBuffer, ao_field, heightfield, occlusion_toward, render_part)

# the key light in world space for the baked self-shadow (soffits, under eaves and hat brims): the
# screen-space light "upper left, a little in front" read as a direction from the west, above and
# a little south, so eaves shade the wall below them as in hand-drawn 3/4 art.
KEY_W = normalize(np.array([-0.42, 0.78, 0.46]))


class Layer:
    """One sprite layer of a prop. sort_px: its sort point below the prop's origin (px, + = south).
    z_index: 0 sorted with the world; -8 lies on the ground under every thing (mats, borders).
    occluder: cuts an x-ray hole when she stands behind it. glow: has an emissive overlay."""

    def __init__(self, name, sort_px=0, z_index=0, occluder=False, outline=2, rim=1, kb=0.30,
                 kao=1.0, ks=0.16, contact=True):
        self.name = name
        self.sort_px = int(sort_px)
        self.z_index = int(z_index)
        self.occluder = occluder
        self.outline = outline
        self.rim = rim
        self.kb = kb
        self.kao = kao
        self.ks = ks
        self.contact = contact


class PropDef:
    def __init__(self, name, solids, lines=(), layers=None, kind='dressing', meta=None, paint=None,
                 shadow=True, contact_k=1.0, emit_only=False):
        self.name = name
        self.solids = list(solids)
        self.lines = list(lines)
        self.layers = layers or [Layer('body')]
        self.kind = kind
        self.meta = meta or {}
        self.paint = paint             # f(layer_name, out_dict, frame) after the colours are set
        self.shadow = shadow
        self.contact_k = contact_k

    def bbox(self):
        los, his = [], []
        for s in self.solids:
            lo, hi = s.bbox()
            los.append(lo)
            his.append(hi)
        for ln in self.lines:
            lo, hi = ln.bbox()
            los.append(lo)
            his.append(hi)
        return np.min(los, 0), np.max(his, 0)


class Ctx:
    """What a material sees for the pixels of one solid (or line) in one layer."""

    def __init__(self, G, sel, solid, is_line, ao, vis):
        self.ys, self.xs = np.nonzero(sel)
        self.n = len(self.ys)
        self.P = G.P[sel]
        self.N = G.N[sel]
        self.u = G.u[sel]
        self.solid = solid
        self.is_line = is_line
        self.Q = self.P if is_line else solid.local(self.P)
        self.Nc = world_to_cam(self.N)
        self.ao = ao[sel]
        self.vis = vis[sel]


def _call(mat, ctx):
    if callable(mat):
        return mat(ctx)
    fn, kw = mat
    return fn(ctx, **kw)


def _neighbors(mask):
    """empty-neighbour flags (right, down, left, up) for a boolean mask."""
    H, W = mask.shape
    pad = np.pad(mask, 1, constant_values=False)
    right = ~pad[1:-1, 2:]
    down = ~pad[2:, 1:-1]
    left = ~pad[1:-1, :-2]
    up = ~pad[:-2, 1:-1]
    return right & mask, down & mask, left & mask, up & mask


def bake(prop, verbose=False):
    lo, hi = prop.bbox()
    frame = Frame(lo, hi, margin=4)
    out = {'name': prop.name, 'frame': frame, 'layers': {}, 'meta': dict(prop.meta), 'kind': prop.kind}
    all_solids = prop.solids
    for L in prop.layers:
        G = render_part(prop.solids, prop.lines, frame, L.name)
        hit = G.hit
        if not hit.any():
            continue
        H, W = hit.shape
        ao = np.ones((H, W))
        vis = np.ones((H, W))
        sel_solid = hit & (G.sid < 10000)
        if sel_solid.any():
            Pp = G.P[sel_solid]
            Np = G.N[sel_solid]
            ao[sel_solid] = ao_field(all_solids, Pp + Np * 0.004, Np)
            vis[sel_solid] = occlusion_toward(all_solids, Pp + Np * 0.01, KEY_W)
        pal = np.full((H, W), PL.ID['dark'], np.int32)
        tone = np.zeros((H, W))
        emit = np.zeros((H, W, 3))
        bump = np.zeros((H, W, 3))
        kb = np.full((H, W), L.kb)
        kao = np.full((H, W), L.kao)
        noshade = np.zeros((H, W), bool)
        dith = np.zeros((H, W), bool)
        outl = np.full((H, W), L.outline, np.int32)
        for sid in np.unique(G.sid[hit]):
            sel = G.sid == sid
            is_line = sid >= 10000
            obj = prop.lines[sid - 10000] if is_line else prop.solids[sid]
            ctx = Ctx(G, sel, obj, is_line, ao, vis)
            r = _call(obj.mat, ctx)
            pal[sel] = r['pal']
            tone[sel] = r['tone']
            if 'emit' in r:
                emit[sel] = r['emit']
            if 'bump' in r:
                bump[sel] = r['bump']
            if 'kb' in r:
                kb[sel] = r['kb']
            if 'kao' in r:
                kao[sel] = r['kao']
            if r.get('flat'):
                noshade[sel] = True
            if r.get('dither'):
                dith[sel] = True
            if 'outline' in r:
                outl[sel] = r['outline']
            if obj.data.get('outline') is not None:
                outl[sel] = obj.data['outline']
        Nc = world_to_cam(G.N)
        ndl = np.clip(Nc @ LIGHT_C, 0.0, 1.0)
        shade = kb * (ndl - 0.62) + kao * (ao - 1.0) * 0.55 - L.ks * (1.0 - vis)
        tone = np.where(noshade, tone, tone + shade)
        sizes = PL.SIZES[pal]
        f = tone * (sizes - 1)
        bayer = np.array([[0, 2], [3, 1]]) / 4.0 - 0.375
        yy, xx = np.mgrid[0:H, 0:W]
        f = np.where(dith, f + bayer[yy % 2, xx % 2] * 0.9, f)
        idx = np.clip(np.round(f), 0, sizes - 1).astype(np.int32)
        # ---------------------------------------------------------- outlines
        r_, d_, l_, u_ = _neighbors(hit)
        dark_edge = (r_ | d_)
        lit_edge = (l_ | u_) & ~dark_edge
        idx = np.where(dark_edge, idx - outl, idx)
        idx = np.where(lit_edge & (outl > 0), idx - np.maximum(outl - 2, 0), idx)
        # rim: the top edge of the silhouette catches the light (one step up)
        idx = np.where(u_ & ~r_ & (ndl > 0.35), idx + L.rim, idx)
        # contact lines: a far surface right next to a much nearer one darkens (separates parts)
        if L.contact:
            t = np.where(hit, G.t, -np.inf)
            near_r = np.zeros_like(hit)
            for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                tn = np.full_like(t, -np.inf)
                ys0, ys1 = max(0, -dy), H - max(0, dy)
                xs0, xs1 = max(0, -dx), W - max(0, dx)
                tn[ys0:ys1, xs0:xs1] = t[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
                near_r |= hit & (tn - t > 0.14)
            idx = np.where(near_r, idx - 2, idx)
        idx = np.clip(idx, 0, sizes - 1)
        rgb = PL.color(pal, idx)
        alpha = hit.astype(np.float64)
        # ---------------------------------------------------------- normals
        nc = normalize(Nc + bump)
        nc = normalize(np.round(nc * 12.0) / 12.0)
        nrgb = cam_to_rgb(nc)
        layer = {'rgb': rgb, 'a': alpha, 'nrgb': nrgb, 'emit': emit, 'pal': pal, 'idx': idx,
                 'ndl': ndl, 'P': G.P, 't': G.t, 'hit': hit, 'sid': G.sid, 'L': L}
        if prop.paint is not None:
            prop.paint(L.name, layer, frame)
        out['layers'][L.name] = layer
        if verbose:
            print('  layer', L.name, int(hit.sum()), 'px')
    if prop.shadow:
        out['shadow'] = shadow_map(prop)
    return out


# ------------------------------------------------------------------ cast shadows
def shadow_map(prop, min_elev=SHADOW_MIN_ELEV):
    """Horizon shadow map of the prop on the ground plane (y = 0), in ground pixels (20 px/m)
    relative to the prop's origin. R = elevation (deg * 255/90) below which the texel is in the
    prop's shadow (the top of the casters along the ray toward the sun), G = the elevation above
    which it is lit again (the bottom of floating casters; 0 for things that stand on the ground),
    B = contact shade (sun-independent ambient occlusion at the base). Shading at run time:
    cast = (1 - smoothstep(R - soft, R + soft, e)) * smoothstep(G - soft, G + soft, e)."""
    casters = [s for s in prop.solids if not s.data.get('no_shadow')]
    if not casters:
        return None
    los, his = zip(*[s.bbox() for s in casters])
    lo = np.min(los, 0)
    hi = np.max(his, 0)
    top, bot, x0, z0 = heightfield(casters, lo, hi)
    if np.all(np.isnan(top)):
        return None
    hmax = float(np.nanmax(top))
    reach = hmax / math.tan(math.radians(min_elev))        # metres
    sx, sz = SHADOW_DIR
    pad = 3
    ex = int(math.ceil(max(0.0, sx) * reach * PPM)) + pad
    ez = int(math.ceil(max(0.0, sz) * reach * PPM)) + pad
    wx = int(math.ceil(max(0.0, -sx) * reach * PPM)) + pad
    wz = int(math.ceil(max(0.0, -sz) * reach * PPM)) + pad
    nz, nx = top.shape
    W = nx + wx + ex
    H = nz + wz + ez
    T = np.full((H, W), np.nan)
    B = np.full((H, W), np.nan)
    T[wz:wz + nz, wx:wx + nx] = top
    B[wz:wz + nz, wx:wx + nx] = bot
    Tz = np.where(np.isnan(T), 0.0, T)
    has = ~np.isnan(T) & (Tz > 0.02)
    maxtan = np.where(has, 1e9, 0.0)          # under the caster itself: always shaded
    mintan = np.where(has, 0.0, 1e9)
    steps = int(math.ceil(reach * PPM)) + 2
    for k in range(1, steps + 1):
        dx = int(round(sx * k))
        dz = int(round(sz * k))
        dist = k / PPM
        src_T = np.full((H, W), np.nan)
        src_B = np.full((H, W), np.nan)
        ys0, ys1 = max(0, dz), H + min(0, dz)
        xs0, xs1 = max(0, dx), W + min(0, dx)
        if ys1 <= ys0 or xs1 <= xs0:
            break
        src_T[ys0:ys1, xs0:xs1] = T[ys0 - dz:ys1 - dz, xs0 - dx:xs1 - dx]
        src_B[ys0:ys1, xs0:xs1] = B[ys0 - dz:ys1 - dz, xs0 - dx:xs1 - dx]
        ok = ~np.isnan(src_T)
        if not ok.any():
            continue
        tt = np.where(ok, src_T / dist, 0.0)
        tb = np.where(ok, src_B / dist, 1e9)
        maxtan = np.maximum(maxtan, tt)
        mintan = np.where(ok, np.minimum(mintan, tb), mintan)
    top_ang = np.degrees(np.arctan(maxtan))
    bot_ang = np.where(mintan >= 1e8, 0.0, np.degrees(np.arctan(mintan)))
    bot_ang = np.where(top_ang <= 0.0, 0.0, bot_ang)
    # contact shade: soft occlusion around the base of what stands on the ground
    base = np.where(has & (np.nan_to_num(B, nan=9.0) < 0.05), np.clip(Tz / 0.5, 0, 1), 0.0)
    contact = ndi.gaussian_filter(base, 2.2) * 2.2
    contact = np.clip(np.maximum(contact, base * 0.0), 0, 1)
    contact = contact * prop.contact_k
    img = np.zeros((H, W, 4), np.uint8)
    img[..., 0] = np.clip(np.round(top_ang * 255.0 / 90.0), 0, 255)
    img[..., 1] = np.clip(np.round(bot_ang * 255.0 / 90.0), 0, 255)
    img[..., 2] = np.clip(np.round(contact * 255.0), 0, 255)
    keep = (img[..., 0] >= int(math.floor(min_elev * 255 / 90)) - 2) | (img[..., 2] > 3)
    img[..., 3] = np.where(keep, 255, 0)
    # crop to the used area
    ys, xs = np.nonzero(img[..., 3])
    if ys.size == 0:
        return None
    y0, y1, x0p, x1p = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    img = img[y0:y1, x0p:x1p]
    # texel (0,0) <-> ground point: x = x0 + (x0p - wx) / PPM, z = z0 + (y0 - wz) / PPM
    ox = int(round(x0 * PPM)) + (x0p - wx)
    oz = int(round(z0 * PPM)) + (y0 - wz)
    return {'img': img, 'offset': (ox, oz), 'hmax': hmax}
