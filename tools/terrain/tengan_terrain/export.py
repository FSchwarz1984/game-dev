"""Write a bake to disk: screen-space render chunks, world-space ground masks,
walk polygons, markers and region.json. Formats are documented in
docs/knowledge/17-terrain-pipeline.md and tools/terrain/README.md."""
import json
import os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure

from .geom import PPM
from .layout import TOP, FACE, KIND
from .painter import KIND_TOP, KIND_FACE, KIND_SIDE

SQ2 = np.float32(np.sqrt(0.5))
DEPTH_OFFSET = 8192          # depth code = round(D * 2) + DEPTH_OFFSET, D = z + h in world px
H_CODE_OFFSET, H_CODE_SCALE = 0.0, 4.0      # height byte = round(h_m * 4), datum included (0..63.75 m)
STEP_M = 0.3                 # largest height change a character steps over


def screen_normal_rgb(n):
    """World normal (x east, y up, z south) -> Godot 2D normal map RGB
    (R = screen right, G = screen up, B = out of the screen)."""
    sx = n[..., 0]
    sy = (n[..., 1] - n[..., 2]) * SQ2
    sz = (n[..., 1] + n[..., 2]) * SQ2
    v = np.stack([sx, sy, sz], -1)
    v /= np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-6)
    return np.clip(np.round((v * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8)


def _save(arr, path):
    Image.fromarray(arr).save(path, optimize=True)


def walkable_mask(world):
    w = world
    valid = ~np.isnan(w.h)
    surf = np.zeros(w.h.shape, np.uint8)
    kinds = np.array([s.get('kind', 0) for s in w.surfaces], np.uint8)
    k = kinds[w.sid]
    walk = valid & (k != KIND['cheek']) & ~(k == KIND['water'])
    # shallow water margins (< 0.25 m) stay walkable
    walk |= valid & (k == KIND['water']) & (w.wdepth < 0.25)
    return walk


def barrier_mask(world, walk):
    """1 px barrier on the upper side of every step taller than STEP_M between
    two walkable cells, so the walk regions are split along cliff lines."""
    h = np.nan_to_num(world.h, nan=-1e3)
    bar = np.zeros(h.shape, bool)
    for dy, dx in ((1, 0), (0, 1)):
        a = h[: h.shape[0] - dy, : h.shape[1] - dx]
        b = h[dy:, dx:]
        wa = walk[: h.shape[0] - dy, : h.shape[1] - dx]
        wb = walk[dy:, dx:]
        big = wa & wb & (np.abs(a - b) > STEP_M)
        up_a = big & (a > b)
        up_b = big & (b > a)
        bar[: h.shape[0] - dy, : h.shape[1] - dx] |= up_a
        bar[dy:, dx:] |= up_b
    return bar


def walk_polygons(world, walk, bar, tol_px=1.2):
    """Connected walkable regions (split at cliffs) as polygons in metres."""
    m = walk & ~bar
    lab, n = ndi.label(m)
    out = []
    f = world.frame
    for i in range(1, n + 1):
        reg = lab == i
        area = int(reg.sum())
        if area < 40:
            continue
        sl = ndi.find_objects(reg.astype(np.int32))[0]
        sub = np.pad(reg[sl], 1)
        cs = measure.find_contours(sub.astype(np.float32), 0.5)
        polys = []
        for c in cs:
            c = measure.approximate_polygon(c, tol_px)
            if len(c) < 4:
                continue
            pts = [[round(f.x0 + (p[1] - 1 + sl[1].start) / PPM, 3), round(f.z0 + (p[0] - 1 + sl[0].start) / PPM, 3)] for p in c]
            polys.append(pts)
        if not polys:
            continue
        polys.sort(key=lambda p: -abs(_area(p)))
        hs = world.h[reg]
        out.append({'id': i, 'area_m2': round(area / PPM / PPM, 2), 'h_min': round(float(np.nanmin(hs)), 2),
                    'h_max': round(float(np.nanmax(hs)), 2), 'outer': polys[0], 'holes': polys[1:]})
    return out


def _area(p):
    a = np.asarray(p)
    return 0.5 * np.sum(a[:, 0] * np.roll(a[:, 1], -1) - np.roll(a[:, 0], -1) * a[:, 1])


# the Godot core's RegionData ids (godot/world/region_data.gd MATERIALS)
CORE_MAT = {'void': 0, 'grass': 1, 'dirt': 2, 'stone': 3, 'stairs': 4, 'water': 5, 'deep_water': 6, 'cliff': 7, 'wood': 8, 'sand': 9}
TOP_TO_CORE = {
    TOP['void']: 0, TOP['meadow']: 1, TOP['lawn']: 1, TOP['moss']: 1, TOP['forest']: 1, TOP['wetbank']: 1,
    TOP['scree']: 3, TOP['dirt']: 2, TOP['earth']: 2, TOP['gravel']: 2, TOP['tread']: 4, TOP['paving']: 3,
    TOP['rock']: 3, TOP['cheek']: 7, TOP['water']: 5,
}


def logic_mask(world, datum_m, cell_m=0.25):
    """The core's ground model (RegionData): one pixel per cell_m, RGB8,
    R*256+G = ground height in cm (datum included, so never negative),
    B = core material id. Sampled at each cell centre."""
    step = int(round(cell_m * PPM))
    H, W = world.h.shape
    ys = np.arange(step // 2, H, step)
    xs = np.arange(step // 2, W, step)
    h = world.h[np.ix_(ys, xs)]
    top = world.top[np.ix_(ys, xs)]
    valid = ~np.isnan(h)
    lut = np.zeros(256, np.uint8)
    for k, v in TOP_TO_CORE.items():
        lut[k] = v
    mat = lut[top]
    deep = (~np.isnan(world.water[np.ix_(ys, xs)])) & (world.wdepth[np.ix_(ys, xs)] >= 0.25)
    mat = np.where(deep, CORE_MAT['deep_water'], mat)
    mat = np.where(valid, mat, 0).astype(np.uint8)
    cm = np.where(valid, np.round((np.nan_to_num(h) + datum_m) * 100), 0)
    if (cm < 0).any() or (cm > 65535).any():
        raise ValueError('heights + datum must stay within 0..655 m; raise datum_m')
    cm = cm.astype(np.int64)
    return np.dstack([(cm >> 8).astype(np.uint8), (cm & 255).astype(np.uint8), mat])


def export(B, out_dir, chunk=512, log=print):
    os.makedirs(out_dir, exist_ok=True)
    cdir = os.path.join(out_dir, 'chunks')
    mdir = os.path.join(out_dir, 'masks')
    os.makedirs(cdir, exist_ok=True)
    os.makedirs(mdir, exist_ok=True)
    S, W_, SP = B.screen, B.world, B.paint
    Hs, Ws = S.kind.shape
    f = W_.frame
    x0px = int(round(f.x0 * PPM))
    z0px = int(round(f.z0 * PPM))
    datum = float(B.spec.get('datum_m', 0.0))
    dpx = int(round(datum * PPM))
    # game px of the screen raster's top-left: X = x*20, Y = (z - (h + datum))*20
    origin = [x0px, z0px + S.rmin - dpx]
    # ---- screen layers
    alpha = np.where(B.mask, 255, 0).astype(np.uint8)
    albedo = np.dstack([B.albedo, alpha])
    normal = screen_normal_rgb(SP.n)
    normal[~B.mask] = (128, 128, 255)
    light = np.zeros((Hs, Ws, 3), np.uint8)
    light[..., 0] = np.clip(np.round(B.horizon / 90.0 * 255), 0, 255)
    light[..., 1] = np.clip(np.round(B.sky * 255), 0, 255)
    light[..., 2] = SP.mat
    light[~B.mask] = 0
    D = S.depth + z0px + dpx                             # absolute world px (z + h, datum included)
    dcode = np.clip(np.round(D * 2) + DEPTH_OFFSET, 0, 65535).astype(np.int64)
    hpix = S.hpx / PPM + datum
    hcode = np.clip(np.round((hpix + H_CODE_OFFSET) * H_CODE_SCALE), 0, 255).astype(np.uint8)
    depth = np.dstack([(dcode >> 8).astype(np.uint8), (dcode & 255).astype(np.uint8), hcode])
    depth[~B.mask] = 0
    chunks = []
    for cy in range(0, Hs, chunk):
        for cx in range(0, Ws, chunk):
            m = B.mask[cy:cy + chunk, cx:cx + chunk]
            if not m.any():
                continue
            name = f'c{cx // chunk:02d}_{cy // chunk:02d}'
            files = {}
            for key, arr in (('albedo', albedo), ('normal', normal), ('light', light), ('depth', depth)):
                tile = np.zeros((chunk, chunk, arr.shape[2]), np.uint8)
                if key == 'normal':
                    tile[...] = (128, 128, 255)
                part = arr[cy:cy + chunk, cx:cx + chunk]
                tile[:part.shape[0], :part.shape[1]] = part
                fn = f'{name}_{key}.png'
                _save(tile, os.path.join(cdir, fn))
                files[key] = 'chunks/' + fn
            chunks.append({'name': name, 'col': cx // chunk, 'row': cy // chunk,
                           'pos_px': [origin[0] + cx, origin[1] + cy], 'size_px': [chunk, chunk], 'files': files})
    log(f'  export: {len(chunks)} chunks of {chunk} px')
    # ---- world masks
    h = W_.h
    valid = ~np.isnan(h)
    hc = np.where(valid, np.clip(np.round((np.nan_to_num(h) + datum) * 100) + 32768, 1, 65535), 0).astype(np.int64)
    kinds = np.array([s.get('kind', 0) for s in W_.surfaces], np.uint8)
    surf = np.where(valid, kinds[W_.sid], 0).astype(np.uint8)
    walk = walkable_mask(W_)
    bar = barrier_mask(W_, walk)
    hmask = np.dstack([(hc >> 8).astype(np.uint8), (hc & 255).astype(np.uint8), surf])
    _save(hmask, os.path.join(mdir, 'height.png'))
    flags = np.zeros(h.shape, np.uint8)
    flags |= np.isin(W_.top, [TOP['dirt'], TOP['earth'], TOP['paving'], TOP['gravel']]).astype(np.uint8) * 1
    flags |= (surf == KIND['tread']).astype(np.uint8) * 2
    flags |= (~np.isnan(W_.water)).astype(np.uint8) * 4
    flags |= ((~np.isnan(W_.water)) & (W_.wdepth >= 0.25)).astype(np.uint8) * 8
    flags |= bar.astype(np.uint8) * 16
    E = getattr(W_, 'edges', None)
    if E is not None:
        flags |= ((E['sfoot'] < 6) & valid).astype(np.uint8) * 32
    if hasattr(W_, 'ramp_mask'):
        flags |= W_.ramp_mask.astype(np.uint8) * 64
    mat = np.dstack([W_.top, np.where(walk & ~bar, 255, 0).astype(np.uint8), flags])
    _save(mat, os.path.join(mdir, 'material.png'))
    hor = np.dstack([np.clip(np.round(W_.horizon / 90 * 255), 0, 255).astype(np.uint8),
                     np.clip(np.round(W_.sky * 255), 0, 255).astype(np.uint8), np.zeros(h.shape, np.uint8)])
    _save(hor, os.path.join(mdir, 'sun.png'))
    _save(logic_mask(W_, datum), os.path.join(mdir, 'logic.png'))
    polys = walk_polygons(W_, walk, bar)
    with open(os.path.join(out_dir, 'walk_regions.json'), 'w', encoding='utf-8') as fh:
        json.dump({'format': 'tengan-terrain-walk/1', 'units': 'metres (x east, z south)', 'step_m': STEP_M,
                   'regions': polys}, fh, ensure_ascii=False)
    with open(os.path.join(out_dir, 'markers.json'), 'w', encoding='utf-8') as fh:
        stairs = [dict(st, **{'from': st['from'] + datum, 'to': st['to'] + datum}) for st in getattr(W_, 'stairs_out', [])]
        json.dump({'format': 'tengan-terrain-markers/1', 'datum_m': datum, 'markers': W_.markers,
                   'stairs': stairs}, fh, ensure_ascii=False, indent=1)
    for mk in W_.markers:
        if mk.get('ground_h') is not None:
            mk['ground_h'] = round(mk['ground_h'] + datum, 3)
    region = {
        'format': 'tengan-terrain-bake/1',
        'name': B.spec.get('name'),
        # keys read by the core's RegionData (godot/world/region_data.gd)
        'id': B.spec.get('name'),
        'cell_m': 0.25,
        'max_step_m': STEP_M,
        'logic': 'masks/logic.png',
        'origin_m': [f.x0, f.z0],
        'size_m': [f.x1 - f.x0, f.z1 - f.z0],
        'datum_m': datum,
        'ppm': PPM,
        'world_bounds_m': [f.x0, f.z0, f.x1, f.z1],
        'projection': 'game px: X = x*20, Y = (z - h)*20; depth D = (z + h)*20, larger is nearer',
        'screen_origin_px': origin,
        'screen_size_px': [Ws, Hs],
        'chunk_px': chunk,
        'chunks': chunks,
        'sun': {'toward_xz': list(map(float, B.toward)),
                'note': 'fixed azimuth from the upper left of the screen; elevation varies with time of day'},
        'encodings': {
            'albedo': 'RGBA8 sRGB, A = terrain coverage',
            'normal': 'RGB8 Godot 2D normal map: R screen right, G screen up, B out of screen',
            'light': 'RGB8: R = sun horizon elevation (deg * 255/90), G = sky visibility 0..1, B = material code (top id, or 32 + face style)',
            'depth': f'RGB8: (R*256 + G) = round(D*2) + {DEPTH_OFFSET}, D = z_px + h_px (world px); B = round((h_m + {H_CODE_OFFSET}) * {H_CODE_SCALE})',
            'masks/logic.png': 'core RegionData mask: one px per 0.25 m cell, R*256 + G = height in cm (datum included), B = core material id (0 void, 1 grass, 2 dirt, 3 stone, 4 stairs, 5 water, 6 deep water, 7 cliff/wall)',
            'masks/height.png': 'world grid 20 px/m: (R*256 + G) = round(h_m*100) + 32768 (datum included; 0 = no ground); B = surface kind (1 level, 2 ramp, 3 stair tread, 4 stair cheek, 5 water, 6 landing)',
            'masks/material.png': 'world grid: R = top material id, G = 255 walkable (cliff lips are 0), B = flags (1 road, 2 stair, 4 water, 8 deep water, 16 cliff lip barrier, 32 cliff foot, 64 ramp)',
            'masks/sun.png': 'world grid: R = sun horizon elevation (deg * 255/90) of the ground, G = sky visibility; for shading actors by their feet',
            'walk_regions.json': 'walkable regions split at steps > step_m, polygons in metres (outer + holes)',
        },
        'top_materials': {k: v for k, v in TOP.items()},
        'face_styles': {k: 32 + v for k, v in FACE.items()},
        'step_m': STEP_M,
    }
    with open(os.path.join(out_dir, 'region.json'), 'w', encoding='utf-8') as fh:
        json.dump(region, fh, ensure_ascii=False, indent=1)
    return region
