"""The land around the sample region, for the view from the lookout (W3Vista, godot/world3d/vista3d.gd).

It follows the approved map (docs/design/map.md, map-v2.svg), compressed to the sample's scale, with
the camphor at (0, 0) and the lookout on the spur south-west of it:
  * north: the gully, then the summit ridge with the 「隔」 tower (upper layer);
  * the pass sits in an east-west ridge, so the ground rises east and west of it;
  * west: the ravine of the 裏見之瀑, where the stream falls over a cliff;
  * south-west: the lookout's own ravine runs down into the canyon (吊桥, then 铁桥 further out);
  * south: the lower layer (溜池 with its sluice, the terraces and the water-wheel farm, the
    hot-spring valley), and the old road switchbacking down into the 遠化 mist;
  * the mist rings the whole region; beyond it the plain lies far below, faint, with mountains on
    the horizon.
Inside the sample region the real heights are used, so the near land matches the walkable world.

Writes into godot/world3d/terrain/<name>/:
  vista_mid.png  1 m cells: R*256+G = u16 height, B = forest density, A = water (255)
  vista_mat.png  1 m cells: R = cultivated (terraces, fields), G = road, B = rock, A = mist depth
  vista_far.png  32 m cells: R*256+G = u16 height, B = forest density, A = water
  vista.json     frames, encodings, landmarks, the road, the impostor trees
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from . import geom, noise

MID = {"x0": -640.0, "z0": -560.0, "cell": 1.0, "nx": 1281, "nz": 1281, "hmin": -480.0, "hrange": 960.0}
FAR = {"x0": -16000.0, "z0": -16000.0, "cell": 32.0, "nx": 1001, "nz": 1001, "hmin": -480.0, "hrange": 2400.0}

# the region inside the 遠化 mist (an ellipse around the region's middle, map v2 scaled)
MIST = {"cx": -50.0, "cz": 100.0, "rx": 430.0, "rz": 370.0}

TOWER = (20.0, -248.0)
LOOKOUT = (-23.6, 42.4)
WATERFALL_LIP = (-150.0, -14.0)
POND = (67.0, 217.0)
HOT_SPRING = (250.0, 296.0)
FARM = (48.0, 352.0)
TERRACES = (30.0, 372.0)
SUSPENSION = ((-236.0, 140.0), (-252.0, 176.0))       # 吊桥: across the canyon
IRON_BRIDGE = ((-400.0, 226.0), (-424.0, 268.0))      # 铁桥: further out, the railway's
RAVINE_W = [(-178.0, -330.0), (-166.0, -200.0), (-156.0, -90.0), (-150.0, -14.0), (-154.0, 2.0), (-172.0, 70.0), (-200.0, 128.0), (-236.0, 158.0)]
CANYON = [(-46.0, 114.0), (-70.0, 134.0), (-120.0, 146.0), (-180.0, 150.0), (-244.0, 158.0), (-330.0, 200.0), (-412.0, 247.0), (-560.0, 300.0), (-760.0, 360.0), (-1100.0, 420.0)]
HOT_VALLEY = [(180.0, 230.0), (250.0, 296.0), (330.0, 380.0), (420.0, 470.0)]
ROAD_TAIL = [(4.0, 112.0), (-8.0, 138.0), (18.0, 168.0), (2.0, 196.0), (26.0, 228.0), (8.0, 262.0), (30.0, 298.0), (12.0, 330.0), (24.0, 382.0), (18.0, 430.0), (30.0, 500.0), (24.0, 600.0)]


def _bell(v, c, w):
    return np.exp(-((v - c) / w) ** 2)


def _mist_e(X, Z):
    return np.hypot((X - MIST["cx"]) / MIST["rx"], (Z - MIST["cz"]) / MIST["rz"])


def _carve(h, X, Z, line, depth, half_w, floor_w=0.25):
    """A valley along a polyline: depth (m) and half width (m) per vertex; flat-ish floor."""
    P = np.asarray(line, np.float64)
    d, arc, vals = geom.polyline_field(X, Z, P, np.stack([np.asarray(depth, float), np.asarray(half_w, float)], -1))
    dep, hw = vals[..., 0], vals[..., 1]
    t = np.clip(d / np.maximum(hw, 1e-3), 0.0, 1.0)
    shape = 1.0 - geom.smoothstep(floor_w, 1.0, t)
    return h - dep * shape, d, arc


def land(X, Z, seed):
    """Heights of the land everywhere (m, the camphor's saddle at about 0)."""
    zz = np.arange(-20000.0, 20000.0, 8.0)
    # (the lower layer lies well below the pass: from the lookout it is seen as a land in miniature,
    # with the mist beyond its rim and the plain far below)
    zp = [-20000, -4000, -1500, -700, -380, -255, -150, -96, 0, 112, 160, 210, 270, 340, 420, 480, 600, 900, 1600, 20000]
    hp = [760, 560, 360, 230, 150, 122, 56, 10, 0, -32, -56, -84, -100, -108, -120, -165, -250, -320, -345, -345]
    prof = ndimage.gaussian_filter1d(np.interp(zz, zp, hp), 5)
    h = np.interp(Z, zz, prof)
    # the pass lies in an east-west ridge
    h += np.minimum(np.abs(X) * 0.17, 170.0) * _bell(Z, -40.0, 280.0)
    # the summit crest, highest about the tower
    h += 34.0 * _bell(Z, -255.0, 85.0) * _bell(X, 20.0, 330.0)
    # mountains: north of the summit, and ringing the plain far out
    rc = np.hypot(X - MIST["cx"], (Z - MIST["cz"]) * 0.8)
    north = geom.smoothstep(-380.0, -1100.0, Z)
    ring = geom.smoothstep(4500.0, 11000.0, rc) * (1.0 - north)
    rid = noise.ridged(X / 1500.0, Z / 1500.0, 4, seed + 1)
    h += north * (rid * 480.0 + noise.fbm(X / 600.0, Z / 600.0, 3, seed + 2) * 140.0)
    # (they stand out of the sea of mist on the horizon: peaks well above the lowland)
    h += ring * (noise.ridged(X / 2400.0, Z / 2400.0, 4, seed + 3) * 1300.0 + 380.0)
    # east and west of the region the ridge's flanks fall away toward the plain in spurs
    side = geom.smoothstep(380.0, 900.0, np.abs(X)) * geom.smoothstep(-200.0, 400.0, Z) * (1.0 - ring)
    h += side * (noise.ridged(X / 700.0, Z / 700.0, 3, seed + 4) - 0.35) * 160.0
    # the plain itself: almost flat, a little roll
    plain = geom.smoothstep(700.0, 1500.0, Z) * (1.0 - ring)
    h += plain * (noise.fbm(X / 900.0, Z / 900.0, 2, seed + 5) - 0.5) * 10.0
    # relief everywhere else
    rough = 1.0 - plain * 0.85
    h += rough * ((noise.fbm(X / 140.0, Z / 140.0, 3, seed + 6) - 0.5) * 30.0 + (noise.fbm(X / 38.0, Z / 38.0, 2, seed + 7) - 0.5) * 7.0)
    return h


def mid_features(h, X, Z, seed):
    """The named places of the region on the 1 m grid. Returns h and the masks."""
    water = np.zeros_like(h, bool)
    rock = np.zeros_like(h)
    # the west ravine and the 裏見之瀑: the floor drops 24 m at the lip
    h_r, d_r, arc_r = _carve(h, X, Z, RAVINE_W, [26, 30, 32, 34, 58, 60, 62, 64], [26, 28, 30, 30, 32, 34, 36, 40], 0.12)
    h = h_r
    # the waterfall's cliff: steep rock across the ravine at the lip
    lip = np.asarray(WATERFALL_LIP)
    rock = np.maximum(rock, geom.smoothstep(26.0, 12.0, np.hypot(X - lip[0], Z - lip[1])) * geom.smoothstep(34.0, 10.0, d_r))
    water |= d_r < 1.6
    # the lookout's ravine continues into the canyon
    h, d_c, arc_c = _carve(h, X, Z, CANYON, [6, 18, 40, 62, 74, 80, 84, 86, 86, 86], [16, 22, 30, 38, 44, 48, 52, 56, 60, 66], 0.18)
    water |= d_c < 2.2
    # its walls are bare rock where it is deep (west of the lookout's ravine)
    rock = np.maximum(rock, geom.smoothstep(40.0, 14.0, d_c) * geom.smoothstep(-90.0, -160.0, X))
    # the hot-spring valley
    h, d_h, _ = _carve(h, X, Z, HOT_VALLEY, [8, 22, 26, 30], [26, 34, 40, 46], 0.2)
    water |= (d_h < 1.4) & (np.hypot(X - HOT_SPRING[0], Z - HOT_SPRING[1]) < 90.0)
    # the pond (溜池): a flat basin held by a low dam on its south side
    pe = np.hypot((X - POND[0]) / 26.0, (Z - POND[1]) / 18.0)
    jc = int(np.argmin(np.abs(Z[:, 0] - POND[1])))
    ic = int(np.argmin(np.abs(X[0, :] - POND[0])))
    surf = float(ndimage.gaussian_filter(h, 8.0)[jc, ic]) - 2.5
    basin = geom.smoothstep(1.35, 0.95, pe)
    h = h * (1.0 - basin) + surf * basin
    water |= pe < 1.0
    # the terraces: steps of 1.6 m on the gentle slope by the farm
    te = np.hypot((X - TERRACES[0]) / 80.0, (Z - TERRACES[1]) / 52.0)
    tk = geom.smoothstep(1.05, 0.8, te)
    wob = (noise.fbm(X / 30.0, Z / 30.0, 2, seed + 11) - 0.5) * 2.2
    stepped = np.floor((h + wob) / 1.6) * 1.6 - wob
    h = h * (1.0 - tk) + stepped * tk
    cultivated = tk.copy()
    # fields by the farm and on the gentle ground of the lower layer
    fe = np.hypot((X - FARM[0]) / 120.0, (Z - FARM[1]) / 70.0)
    cultivated = np.maximum(cultivated, geom.smoothstep(1.0, 0.7, fe) * 0.7)
    # the old road: continues the region's road down to the mist
    rp = geom.catmull(np.asarray(ROAD_TAIL), 8)
    d_road, arc_road, _ = geom.polyline_field(X, Z, rp)
    road = geom.smoothstep(2.4, 1.0, d_road)
    hs = ndimage.gaussian_filter(h, 3.0)
    h = h * (1.0 - road) + hs * road
    # forest: everything on slopes that is not rock, field, road or water, with clearings
    gz, gx = np.gradient(h, X[0, 1] - X[0, 0])
    slope = np.degrees(np.arctan(np.hypot(gx, gz)))
    rock = np.maximum(rock, geom.smoothstep(40.0, 52.0, slope))
    clear = noise.fbm(X / 90.0, Z / 90.0, 3, seed + 12)
    forest = geom.smoothstep(0.32, 0.5, clear) * (1.0 - cultivated) * (1.0 - geom.smoothstep(1.0, 3.5, 4.0 - d_road)) * (1.0 - rock * 0.8)
    forest *= ~water
    return h, {"water": water, "rock": rock, "cultivated": cultivated, "road": road, "forest": forest, "slope": slope,
               "road_pts": rp, "d_ravine": d_r, "d_canyon": d_c}


def _u16(h, hmin, hrange):
    q = np.clip(np.round((h - hmin) / hrange * 65535.0), 0, 65535).astype(np.uint32)
    return (q >> 8).astype(np.uint8), (q & 255).astype(np.uint8)


def _u8(a):
    return np.clip(np.round(np.asarray(a, np.float64) * 255.0), 0, 255).astype(np.uint8)


IMPORT_IMAGE = '[remap]\n\nimporter="image"\ntype="Image"\n'


def _save(path, arr, mode):
    Image.fromarray(arr, mode).save(path, optimize=True)
    imp = Path(str(path) + ".import")
    if not imp.exists():
        imp.write_text(IMPORT_IMAGE)


def write(L, out: Path, tmp: Path, local):
    """local: dict(h, x0, z0, cell, nx, nz, placements) of the walkable region."""
    seed = int(L["seed"]) + 700
    # ---- mid grid
    xs = MID["x0"] + np.arange(MID["nx"]) * MID["cell"]
    zs = MID["z0"] + np.arange(MID["nz"]) * MID["cell"]
    X, Z = np.meshgrid(xs, zs)
    h = land(X, Z, seed)
    h, F = mid_features(h, X, Z, seed)
    # the real region inside its bounds, blended over 24 m into the land around it
    lx0, lz0, lc = local["x0"], local["z0"], local["cell"]
    lx1 = lx0 + (local["nx"] - 1) * lc
    lz1 = lz0 + (local["nz"] - 1) * lc
    fi = np.clip((X - lx0) / lc, 0, local["nx"] - 1)
    fj = np.clip((Z - lz0) / lc, 0, local["nz"] - 1)
    hl = ndimage.map_coordinates(local["h"], [fj, fi], order=1, mode="nearest")
    edge = np.minimum.reduce([X - lx0, lx1 - X, Z - lz0, lz1 - Z])
    w = geom.smoothstep(0.0, 24.0, edge)
    # the land around is shifted to meet the region's rim (no step at the seam)
    h = h * (1.0 - w) + hl * w
    inside = edge > 0
    F["forest"] = np.where(inside, 0.0, F["forest"])
    F["water"] = np.where(inside, False, F["water"])
    F["road"] = np.where(inside, 0.0, F["road"])
    F["cultivated"] = np.where(inside, 0.0, F["cultivated"])
    F["rock"] = np.where(inside, 0.0, F["rock"])
    # the view cone of the lookout is meadow and scrub, not woods (its trees are left out below)
    brg = np.degrees(np.arctan2(X - LOOKOUT[0], -(Z - LOOKOUT[1]))) % 360.0
    cone = (brg > 112.0) & (brg < 248.0) & (np.hypot(X - LOOKOUT[0], Z - LOOKOUT[1]) < 420.0)
    F["forest"] = np.where(cone, F["forest"] * 0.25, F["forest"])
    mist = geom.smoothstep(0.92, 1.4, _mist_e(X, Z))
    r, g = _u16(h, MID["hmin"], MID["hrange"])
    _save(out / "vista_mid.png", np.stack([r, g, _u8(F["forest"]), (F["water"] * 255).astype(np.uint8)], -1), "RGBA")
    _save(out / "vista_mat.png", np.stack([_u8(F["cultivated"]), _u8(F["road"]), _u8(F["rock"]), _u8(mist)], -1), "RGBA")

    # ---- far grid
    xf = FAR["x0"] + np.arange(FAR["nx"]) * FAR["cell"]
    zf = FAR["z0"] + np.arange(FAR["nz"]) * FAR["cell"]
    XF, ZF = np.meshgrid(xf, zf)
    hf = land(XF, ZF, seed)
    # the river across the plain, from the canyon's mouth
    river_x = -900.0 + 700.0 * np.sin((ZF - 600.0) / 2300.0) + 260.0 * np.sin((ZF + 200.0) / 640.0)
    river = (np.abs(XF - river_x) < 46.0) & (ZF > 650.0)
    hf = np.where(river, hf - 3.0, hf)
    plain = geom.smoothstep(700.0, 1500.0, ZF)
    forest_far = geom.smoothstep(0.35, 0.55, noise.fbm(XF / 700.0, ZF / 700.0, 3, seed + 21)) * (1.0 - plain * 0.85)
    rf, gf = _u16(hf, FAR["hmin"], FAR["hrange"])
    _save(out / "vista_far.png", np.stack([rf, gf, _u8(forest_far), (river * 255).astype(np.uint8)], -1), "RGBA")

    # ---- impostor trees in the land around the region (inside the mist only)
    rng = np.random.default_rng(seed + 31)
    trees = []
    sp = 8.5
    gxs = np.arange(MID["x0"] + 4, MID["x0"] + MID["nx"] - 4, sp)
    gzs = np.arange(MID["z0"] + 4, MID["z0"] + MID["nz"] - 4, sp)
    for zc in gzs:
        for xc in gxs:
            x = xc + rng.uniform(-sp * 0.45, sp * 0.45)
            z = zc + rng.uniform(-sp * 0.45, sp * 0.45)
            i = int(round((x - MID["x0"]) / MID["cell"]))
            j = int(round((z - MID["z0"]) / MID["cell"]))
            if F["forest"][j, i] < rng.uniform(0.45, 0.8):
                continue
            if _mist_e(np.array(x), np.array(z)) > 1.25:
                continue
            # the lookout's view stays open: no woods in the cone it looks down (south-east to
            # south-west), only a few trees by the farm and along the road
            dx, dz = x - LOOKOUT[0], z - LOOKOUT[1]
            brg = np.degrees(np.arctan2(dx, -dz)) % 360.0
            if 112.0 < brg < 248.0 and np.hypot(dx, dz) < 420.0 and rng.uniform() > 0.06:
                continue
            y = float(h[j, i])
            # what grows where: cedars to the north and in the west ravine, bamboo on the east
            # shoulder, pines on the crests, oaks and maples elsewhere
            if 70.0 < x < 230.0 and -60.0 < z < 120.0:
                kind = 3
            elif z < -120.0 or (F["d_ravine"][j, i] < 70.0):
                kind = 0
            elif F["slope"][j, i] > 26.0 and rng.uniform() < 0.5:
                kind = 1
            else:
                kind = 2 if rng.uniform() < 0.86 else 4
            size = {0: rng.uniform(16, 25), 1: rng.uniform(9, 14), 2: rng.uniform(8, 13), 3: rng.uniform(8, 11), 4: rng.uniform(6, 9)}[kind]
            trees.append([round(float(x), 1), round(y, 2), round(float(z), 1), kind, round(float(size), 1), int(rng.integers(0, 1000))])
    # the farm's houses and the kiln (the kiln is in the region: its marker)
    landmarks = {
        "tower": [TOWER[0], float(land(np.array(TOWER[0]), np.array(TOWER[1]), seed)), TOWER[1]],
        "waterfall_lip": [WATERFALL_LIP[0], 0.0, WATERFALL_LIP[1]],
        "pond": [POND[0], 0.0, POND[1]],
        "hot_spring": [HOT_SPRING[0], 0.0, HOT_SPRING[1]],
        "farm": [FARM[0], 0.0, FARM[1]],
        "suspension_bridge": [list(SUSPENSION[0]), list(SUSPENSION[1])],
        "iron_bridge": [list(IRON_BRIDGE[0]), list(IRON_BRIDGE[1])],
    }

    def hat(x, z):
        i = int(round((x - MID["x0"]) / MID["cell"]))
        j = int(round((z - MID["z0"]) / MID["cell"]))
        return round(float(h[min(max(j, 0), MID["nz"] - 1), min(max(i, 0), MID["nx"] - 1)]), 2)
    for k in ("waterfall_lip", "pond", "hot_spring", "farm"):
        v = landmarks[k]
        v[1] = hat(v[0], v[2])
    landmarks["tower"][1] = hat(TOWER[0], TOWER[1])
    # the waterfall's foot: the lowest floor just downstream of the lip
    foot = (-155.0, 6.0)
    landmarks["waterfall_foot"] = [foot[0], hat(*foot), foot[1]]
    for k in ("suspension_bridge", "iron_bridge"):
        a, b = landmarks[k]
        # deck height: the lower rim of the two ends
        landmarks[k] = [[a[0], hat(a[0], a[1]), a[1]], [b[0], hat(b[0], b[1]), b[1]]]
    houses = []
    for k, (dx, dz, rot) in enumerate([(0, 0, 0.3), (14, 8, -0.2), (-12, 10, 0.5)]):
        x, z = FARM[0] + dx, FARM[1] + dz
        houses.append([x, hat(x, z), z, rot])
    landmarks["houses"] = houses
    info = {
        "format": "tengan-vista/1",
        "mid": {**MID, "file": "vista_mid.png", "mat": "vista_mat.png"},
        "far": {**FAR, "file": "vista_far.png"},
        "mist": MIST,
        "landmarks": landmarks,
        "road": [[round(float(a), 2), round(float(b), 2)] for a, b in F["road_pts"][::2]],
        "trees": trees,
        "kinds": {"0": "cedar", "1": "pine", "2": "broadleaf", "3": "bamboo", "4": "maple"},
    }
    (out / "vista.json").write_text(json.dumps(info, ensure_ascii=False, separators=(",", ":")))
    # preview
    hs_ = np.clip((h - h.min()) / (h.max() - h.min() + 1e-6), 0, 1)
    gz_, gx_ = np.gradient(h)
    shade = np.clip(0.6 + (-gx_ * 0.5 - gz_ * 0.5) * 0.8, 0, 1)
    rgb = np.stack([hs_ * 0.5 + shade * 0.5] * 3, -1)
    rgb[..., 1] += F["forest"] * 0.15
    rgb[F["water"]] = [0.3, 0.5, 0.8]
    rgb[..., 0] += F["road"] * 0.3
    rgb = rgb * (1 - mist[..., None] * 0.5) + mist[..., None] * 0.5
    Image.fromarray((np.clip(rgb, 0, 1)[::2, ::2] * 255).astype(np.uint8)).save(tmp / "vista_mid_preview.png")
    return {"trees": len(trees), "h_mid": [float(h.min()), float(h.max())], "h_far": [float(hf.min()), float(hf.max())]}
