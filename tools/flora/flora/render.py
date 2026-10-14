"""Render a built Plant into game layers and write them to disk.

Two passes over the same 3D model:
  wood pass  -> trunk and limbs as complete shapes (the static layer; what the crown uncovers when
                it sways) and the roots lying on the ground (the ground layer);
  full pass  -> wood + foliage z-buffered together; the crown layer is every foliage pixel of it.
So roots, trunk, limbs and crown come from one organism: limbs vanish into the masses because
the masses are nearer at those pixels, not because two pictures were laid on top of each other.
"""
import copy
import json
import math
import os

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from . import raster as R
from .core import LIGHT_W, PPM, SHADOW_DIR, SUN_ELEV_REF, hash01, normalize, world_to_cam


class Buf:
    def __init__(self, H, W):
        self.tidx = np.zeros((H, W), np.int16)
        self.tmat = np.zeros((H, W), np.uint8)
        self.nrm = np.zeros((H, W, 3))
        self.nrm[..., 2] = 1


def _use(p, b):
    p.tidx, p.tmat, p.nrm = b.tidx, b.tmat, b.nrm


def render(p):
    cv = p.cv
    H, W = cv.H, cv.W
    p.draw_wood(cv)
    for d in p.wood_details:                       # things on the wood (rope, shide)
        d(p, cv)
    wood = copy.deepcopy(cv)                       # wood only (built before foliage)
    p.draw_foliage(cv)
    for d in p.details:
        d(p, cv)
    WOOD = (R.PART_TRUNK, R.PART_LIMB, R.PART_ROOT, R.PART_DETAIL)
    # ---------------- wood layer (complete trunk and limbs, roots)
    bw = Buf(H, W)
    _use(p, bw)
    wsel = np.isin(wood.part, WOOD) & wood.filled
    p.shade_wood(wood, wsel)
    for fn in getattr(p, 'wood_post', []):
        fn(wood, bw)
    p.outline(wsel & (wood.part != R.PART_ROOT), k=1)
    p.cleanup(wsel)
    p.facet_normals(wsel, (wood.u * 2).astype(np.int64) * 7 + (wood.v * 3).astype(np.int64))
    # ---------------- crown layer (foliage pixels of the full render)
    bc = Buf(H, W)
    _use(p, bc)
    f = cv.filled
    leaf = (cv.part == R.PART_LEAF) & f
    core = (cv.part == R.PART_CORE) & f
    inner = (cv.part == R.PART_INNER) & f
    blade = (cv.part == R.PART_BLADE) & f
    crown_detail = (cv.part == R.PART_DETAIL) & f & (cv.mass >= 0)
    if p.masses:
        p.shade_leaves(cv, leaf, core)
    if blade.any():
        p.shade_blades(cv, blade)
    if crown_detail.any():
        p.shade_wood(cv, crown_detail)          # fruit, flowers on the crown: plain lit forms
    for fn in getattr(p, 'crown_post', []):
        fn(cv, bc)
    csel = leaf | core | inner | blade | crown_detail
    if p.single_layer:
        # shrubs and herbs: one body layer, sorted at its foot; visible wood joins it as painted
        woodvis = np.isin(cv.part, (R.PART_TRUNK, R.PART_LIMB, R.PART_DETAIL)) & f & ~crown_detail
        bc.tidx[woodvis] = bw.tidx[woodvis]
        bc.tmat[woodvis] = bw.tmat[woodvis]
        bc.nrm[woodvis] = bw.nrm[woodvis]
        csel = csel | woodvis
    if csel.any():
        p.outline(csel, k=1)
        p.cleanup(csel)
        p.facet_normals(leaf, np.where(cv.cell >= 0, cv.cell, 0))
    p.wood_buf, p.crown_buf = bw, bc
    p.wood_cv = wood
    p.sel_wood = (wsel & (wood.part != R.PART_ROOT)) if not p.single_layer else np.zeros_like(wsel)
    p.sel_ground = wsel & (wood.part == R.PART_ROOT)
    p.sel_crown = csel
    return p


# ---------------------------------------------------------------- sway data for the crown shader
def sway_data(p):
    """RGBA8: R = sway group (ranked by depth: higher = nearer, wins overlaps), G = flexibility,
    B = inner shell coverage (what a moving group uncovers), A = occlusion mask (crown dense
    enough to hide an actor)."""
    cv = p.cv
    H, W = cv.H, cv.W
    out = np.zeros((H, W, 4), np.uint8)
    sel = p.sel_crown
    if not sel.any():
        return out
    masses = p.masses
    items = [(m['c'], m.get('sway')) for m in masses] + [(g['c'], g['sway']) for g in p.groups]
    nm = len(items)
    trunk_top = getattr(p, 'trunk_top', np.array([0.0, 4.0, 0.0]))
    flex = np.zeros(max(1, nm))
    depth = np.zeros(max(1, nm))
    for i, (c, sw) in enumerate(items):
        if sw is not None:
            flex[i] = sw
        else:
            dh = math.hypot(c[0] - trunk_top[0], c[2] - trunk_top[2])
            flex[i] = np.clip(0.35 + 0.12 * dh + 0.06 * max(0.0, c[1] - trunk_top[1]), 0.3, 1.0)
        depth[i] = c[1] + c[2]
    rank = np.argsort(np.argsort(depth))            # 0 = farthest
    gid = 1 + (rank * 254 // max(1, nm - 1) if nm > 1 else np.zeros(max(1, nm), int))
    moving = sel & (cv.mass >= 0) & (cv.mass < nm)
    mass = np.where(moving, cv.mass, 0)
    # every mass (or blade group) is one sway group; the crown's inside and wood stay still
    out[..., 0] = np.where(moving, gid[mass], 0)
    out[..., 1] = np.where(moving, np.clip(flex[mass] * 255, 0, 255), 0)
    # the shell under the clusters: union of every mass's inner shell, slightly eroded
    shell = np.zeros((H, W), bool)
    tmp = R.Canvas(W, H, cv.ax, cv.ay)
    sq = np.array([1.0, 1.0, p.kz])
    for mi, m in enumerate(masses):
        R.ellipsoids(tmp, p.D([m['c']]), [m['r'] * m['core'] * sq], R.PART_CORE, 1, mass=mi)
    shell = tmp.filled & sel
    shell = ndi.binary_erosion(shell, iterations=1) | (shell & ndi.binary_erosion(sel, iterations=2))
    occ = ndi.binary_closing(sel, iterations=2) & ndi.binary_fill_holes(sel)
    occ = ndi.binary_erosion(occ, iterations=1)
    # B: bit 7 = the crown's inside lies under this texel, bit 6 = dense enough to hide an actor
    out[..., 2] = np.where(shell, 128, 0) + np.where(occ, 64, 0)
    # A: 255 on every texel of the layer, so importers that bleed colour into transparent texels
    # (fix_alpha_border) never touch the data
    out[..., 3] = np.where(sel | occ, 255, 0)
    p.flex = flex
    return out


# ---------------------------------------------------------------- shadows
def shadow_layer(p):
    """Cast shadow for the reference sun: R = crown part, G = trunk and limbs. Its own canvas:
    shadows reach past the sprite to the lower right."""
    sh_c, sh_t, box = p.ground_shadow()
    # pixel-art treatment: three levels for the crown (dapples stay crisp), solid trunk line
    c = np.zeros_like(sh_c)
    c[sh_c > 0.30] = 0.55
    c[sh_c > 0.52] = 1.0
    # sun flecks: light coming through gaps in the canopy, a few px each, softer near the edge
    from .core import vnoise2
    x0, y0, x1, y1 = box
    gy, gx = np.mgrid[y0:y1, x0:x1]
    X = (gx + 0.5 - p.cv.ax) / PPM
    Z = (gy + 0.5 - p.cv.ay) / PPM
    f1 = vnoise2(X * 2.1, Z * 2.1, p.seed + 41) * 0.75 + vnoise2(X * 5.0, Z * 5.0, p.seed + 42) * 0.25
    fk = p.leaf_opts.get('flecks', 0.70)
    c[(c >= 1.0) & (f1 > fk)] = 0.55
    c[(c >= 0.55) & (f1 > fk + 0.07)] = 0.0
    # tiny specks only: drop lone pixels so it never looks like dithering noise
    lone = (c > 0) & (ndi.uniform_filter((c > 0).astype(float), 3) < 0.3)
    c[lone] = 0
    t = (sh_t > 0.5).astype(float)
    # contact shade: where roots, the trunk foot or a bush's low leaves meet the ground (it does
    # not move with the sun): the drawn footprint of everything within ~0.5 m of the ground, blurred
    k = np.zeros_like(c)
    src = p.cv
    h_contact = {'tree': 0.45, 'shrub': 0.22, 'herb': 0.06}.get(p.kind, 0.3)
    low = src.filled & (src.wpos[..., 1] < h_contact) & np.isin(src.part, (R.PART_TRUNK, R.PART_ROOT, R.PART_LEAF,
                                                                           R.PART_CORE, R.PART_BLADE, R.PART_LIMB))
    ys, xs = np.nonzero(low)
    if len(ys):
        P = src.wpos[ys, xs]
        gx = np.round(src.ax + P[:, 0] * PPM - x0).astype(int)
        gy = np.round(src.ay + P[:, 2] * PPM - y0).astype(int)
        ok = (gx >= 0) & (gy >= 0) & (gx < k.shape[1]) & (gy < k.shape[0])
        k[gy[ok], gx[ok]] = 1.0
        k = ndi.gaussian_filter(k, 2.2 if p.kind == 'tree' else 1.4)
        k = np.where(k > 0.12, 1.0, np.where(k > 0.04, 0.5, 0.0))
    return c, t, k, box


# ---------------------------------------------------------------- write files
def crop_box(mask, margin=1):
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return None
    return (max(0, xs.min() - margin), max(0, ys.min() - margin),
            min(mask.shape[1], xs.max() + 1 + margin), min(mask.shape[0], ys.max() + 1 + margin))


def save_rgba(path, arr):
    Image.fromarray(arr, 'RGBA').save(path, optimize=True)


def export(p, outdir, extra_meta=None):
    os.makedirs(outdir, exist_ok=True)
    cv = p.cv
    meta = {'name': p.name, 'kind': p.kind, 'seed': p.seed, 'ppm': PPM,
            'anchor_note': 'offsets are px from the anchor (trunk foot on the ground)',
            'layers': {}}
    if extra_meta:
        meta.update(extra_meta)
    ax, ay = cv.ax, cv.ay

    def put(layer, rgba, nrm=None, data=None, box_mask=None):
        m = box_mask if box_mask is not None else rgba[..., 3] > 0
        box = crop_box(m)
        if box is None:
            return
        x0, y0, x1, y1 = box
        f = {}
        save_rgba(os.path.join(outdir, f'{layer}.png'), np.ascontiguousarray(rgba[y0:y1, x0:x1]))
        f['albedo'] = f'{layer}.png'
        if nrm is not None:
            save_rgba(os.path.join(outdir, f'{layer}_n.png'), np.ascontiguousarray(nrm[y0:y1, x0:x1]))
            f['normal'] = f'{layer}_n.png'
        if data is not None:
            save_rgba(os.path.join(outdir, f'{layer}_d.png'), np.ascontiguousarray(data[y0:y1, x0:x1]))
            f['data'] = f'{layer}_d.png'
        f['offset'] = [int(x0 - round(ax)), int(y0 - round(ay))]
        f['size'] = [int(x1 - x0), int(y1 - y0)]
        meta['layers'][layer] = f

    _use(p, p.wood_buf)
    wood_rgba = p.colorize(p.sel_wood)
    wood_n = p.normal_rgba(p.sel_wood)
    ground_rgba = p.colorize(p.sel_ground)
    ground_n = p.normal_rgba(p.sel_ground)
    _use(p, p.crown_buf)
    crown_rgba = p.colorize(p.sel_crown)
    crown_n = p.normal_rgba(p.sel_crown)
    data = sway_data(p)
    put('ground', ground_rgba, ground_n)
    trunk_data = None
    if p.meta.get('trunk_occluder'):
        # a big trunk hides whoever walks behind it: same x-ray hole as the crown, no sway
        tsel = p.sel_wood
        trunk_data = np.zeros(tsel.shape + (4,), np.uint8)
        trunk_data[..., 2] = np.where(ndi.binary_erosion(tsel, iterations=2), 64, 0)
        trunk_data[..., 3] = np.where(tsel, 255, 0)
    put('trunk', wood_rgba, wood_n, trunk_data)
    put('crown', crown_rgba, crown_n, data)
    # composite preview (for sheets): ground, trunk, crown
    comp = np.zeros_like(crown_rgba)
    for layer in (ground_rgba, wood_rgba, crown_rgba):
        a = layer[..., 3] > 0
        comp[a] = layer[a]
    p.composite = comp
    p.layers_rgba = {'ground': ground_rgba, 'trunk': wood_rgba, 'crown': crown_rgba}
    # shadow (own box: it reaches past the sprite to the lower right)
    c, t, k, box = shadow_layer(p)
    sh = np.zeros(c.shape + (4,), np.uint8)
    sh[..., 0] = np.round(c * 255)
    sh[..., 1] = np.round(t * 255)
    sh[..., 2] = np.round(k * 255)
    sh[..., 3] = np.round(np.maximum(np.maximum(c, t), k) * 255)
    p.shadow = sh
    p.shadow_box = box
    m = sh[..., 3] > 0
    if m.any():
        bb = crop_box(m)
        x0, y0, x1, y1 = bb
        save_rgba(os.path.join(outdir, 'shadow.png'), np.ascontiguousarray(sh[y0:y1, x0:x1]))
        meta['layers']['shadow'] = {'albedo': 'shadow.png',
                                    'offset': [int(box[0] + x0 - round(ax)), int(box[1] + y0 - round(ay))],
                                    'size': [int(x1 - x0), int(y1 - y0)],
                                    'channels': 'R = crown shade, G = trunk shade, B = contact shade (still), A = max'}
    # crown sort: the crown is drawn after every actor standing under it
    if p.sel_crown.any():
        ys, xs = np.nonzero(p.sel_crown)
        gz = cv.wpos[ys, xs, 2]
        meta['crown_sort_px'] = int(round(min(np.percentile(gz, 99) * PPM, (cv.H - ay))))
        core = p.masses[0]['mat'] if p.masses else (p.blades[0]['mat'] if p.blades else 0)
        if core:
            meta['core_color'] = [int(v) for v in p.mats[core].ramp[0]]
        hs = [m['c'][1] for m in p.masses] + [g['c'][1] for g in p.groups]
        if hs:
            meta['crown_height_m'] = [round(float(min(hs)), 2), round(float(max(hs)), 2)]
    meta['sun_ref'] = {'elevation_deg': round(SUN_ELEV_REF, 1), 'shadow_dir_xz': [round(float(v), 4) for v in SHADOW_DIR]}
    meta['sway_amp'] = p.sway_amp
    meta['species'] = p.meta.get('species', '')
    meta['trunk_occluder'] = bool(p.meta.get('trunk_occluder', False))
    meta['layout'] = 'body' if p.single_layer else 'tree'
    if p.single_layer:
        meta['crown_sort_px'] = 0
    if hasattr(p, 'collision'):
        meta['collision'] = p.collision
    with open(os.path.join(outdir, 'meta.json'), 'w') as fh:
        json.dump(meta, fh, indent=1)
    return meta
