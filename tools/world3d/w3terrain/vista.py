"""The land around the sample region, for the view from the lookout (W3Vista, godot/world3d/vista3d.gd).

It follows the approved map (docs/design/map.md, map-v2.svg) and map v3's promise of one far
curiosity in each direction from the lookout (map-v3-natural-draft.md §2), compressed to the
sample's scale, with the camphor at (0, 0) and the lookout on the spur south-west of it:
  * north: the pass falls gently into the cedar basin; beyond it the summit (奥之院, the 「隔」
    tower) rises to the north-west, and the ruined temple's hall stands on the crest of its eastern
    shoulder. Seen from the lookout, looking back, the summit and its tower stand left of the great
    camphor, the temple roof breaks the skyline between them, and the camphor's crown stands against
    the sky (the north mountains are kept low behind it);
  * the pass sits in an east-west ridge, so the ground rises east and west of it;
  * west: the 裏見之瀑's ravine runs down from the north and falls into the canyon by the
    suspension bridge; from the lookout its mist rises out of the canyon;
  * south-west: the lookout's ravine runs down into the canyon (吊桥, then the railway's 铁桥);
  * south: the lower layer (溜池 with its sluice, the terraces and the water-wheel farm, the
    hot-spring valley), and the old road switchbacking down into the 遠化 mist;
  * the mist rings the whole region; beyond it the plain lies far below: fields, a river, villages,
    the railway on a long viaduct, mountains on the horizon (the plain map, villages and railway).
Inside the sample region the real heights are used, so the near land matches the walkable world.
The backdrop is not walkable ground; its layout belongs to the pending map v3 proposal.

Writes into godot/world3d/terrain/<name>/:
  vista_mid.png    1 m cells: R*256+G = u16 height, B = forest density, A = water (255)
  vista_mat.png    1 m cells: R = cultivated (terraces, fields), G = road, B = rock, A = dry-stone wall
  vista_far.png    32 m cells: R*256+G = u16 height, B = forest density, A = water
  vista_plain.png  8 m cells over the plain: R river distance (m), G road distance (0.5 m), B village
                   density, A railway distance (0.5 m) (bilinear: crisp edges at any distance)
  vista.json       frames, encodings, landmarks, the road, the railway, villages' houses, trees
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
PLAIN = {"x0": -6000.0, "z0": 400.0, "cell": 8.0, "nx": 1501, "nz": 1501}

# the region inside the 遠化 mist (an ellipse around the region's middle, map v2 scaled)
MIST = {"cx": -50.0, "cz": 100.0, "rx": 430.0, "rz": 370.0}

SUMMIT = (-74.0, -439.0)                              # 奥之院 and the 「隔」 tower
TEMPLE = (20.6, -426.1)                              # the ruined temple's hall, on the shoulder's crest
LOOKOUT = (-23.6, 42.4)
WATERFALL_LIP = (-206.0, 121.0)                       # 裏見之瀑: the ravine falls into the canyon
WATERFALL_FOOT = (-214.0, 146.0)
POND = (52.0, 288.0)
HOT_SPRING = (250.0, 296.0)
FARM = (48.0, 352.0)
TERRACES = (30.0, 372.0)
SUSPENSION = ((-236.0, 140.0), (-252.0, 176.0))       # 吊桥: across the canyon
IRON_BRIDGE = ((-400.0, 226.0), (-424.0, 268.0))      # 铁桥: further out, the railway's
RAVINE_W = [(-178.0, -330.0), (-166.0, -200.0), (-156.0, -90.0), (-150.0, -14.0), (-160.0, 44.0), (-180.0, 90.0), (-200.0, 114.0), (-206.0, 122.0)]
CANYON = [(-46.0, 114.0), (-70.0, 134.0), (-120.0, 146.0), (-180.0, 150.0), (-244.0, 158.0), (-330.0, 200.0), (-412.0, 247.0), (-560.0, 300.0), (-760.0, 360.0), (-1100.0, 420.0)]
HOT_VALLEY = [(180.0, 230.0), (250.0, 296.0), (330.0, 380.0), (420.0, 470.0)]
ROAD_TAIL = [(4.0, 112.0), (-8.0, 138.0), (18.0, 168.0), (2.0, 196.0), (26.0, 228.0), (8.0, 262.0), (30.0, 298.0), (12.0, 330.0), (24.0, 382.0), (18.0, 430.0), (30.0, 500.0), (24.0, 600.0)]
# the plain: the river from the canyon's mouth, meandering south-east across the view; the railway
# from the 铁桥 down the slope and over the plain on a long viaduct, into the 遠化
RIVER = [(-1100.0, 420.0), (-1250.0, 800.0), (-1150.0, 1250.0), (-700.0, 1650.0), (-150.0, 1900.0), (350.0, 2350.0),
         (520.0, 3000.0), (250.0, 3700.0), (700.0, 4500.0), (1500.0, 5200.0), (1900.0, 6400.0), (1600.0, 7800.0),
         (2400.0, 9500.0), (3200.0, 12500.0)]
RAILWAY = [(-424.0, 268.0), (-470.0, 420.0), (-560.0, 700.0), (-620.0, 1050.0), (-520.0, 1450.0), (-180.0, 1820.0),
           (300.0, 2150.0), (900.0, 2500.0), (1500.0, 3100.0), (2000.0, 4100.0), (2400.0, 5600.0), (2700.0, 7600.0),
           (3000.0, 10500.0)]
RAIL_DECK = [-151.0, -168.0, -205.0, -245.0, -275.0, -296.0, -306.0, -310.0, -312.0, -314.0, -316.0, -318.0, -320.0]


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
    # with the mist beyond its rim and the plain far below; north, the pass falls gently into the
    # cedar basin and the land only climbs again toward the summit)
    # (the lower layer's rim falls to the plain as a long wooded slope, not a wall)
    zp = [-20000, -4000, -2500, -1600, -900, -600, -420, -330, -260, -200, -140, -96, 0, 112, 160, 210, 270, 340, 420, 520,
          650, 900, 1600, 20000]
    hp = [520, 330, 230, 160, 96, 62, 40, 20, -2, -9, -1, 6, 0, -32, -54, -82, -97, -105, -122, -178, -258, -325, -350, -350]
    prof = ndimage.gaussian_filter1d(np.interp(zz, zp, hp), 5)
    h = np.interp(Z, zz, prof)
    # the pass lies in an east-west ridge
    h += np.minimum(np.abs(X) * 0.17, 170.0) * _bell(Z, -40.0, 280.0)
    # the summit to the north-west: a peak with a shoulder falling east (so the camphor's crown,
    # seen from the lookout, stands against the sky right of it)
    rs = np.hypot((X - SUMMIT[0]) / 1.15, Z - SUMMIT[1])
    h += 76.0 * np.exp(-(rs / 150.0) ** 2) + 26.0 * np.exp(-(rs / 320.0) ** 2) * geom.smoothstep(200.0, -100.0, X - SUMMIT[0])
    # mountains: north beyond the summit (low behind the camphor), and ringing the plain far out
    rc = np.hypot(X - MIST["cx"], (Z - MIST["cz"]) * 0.8)
    north = geom.smoothstep(-900.0, -2500.0, Z)
    ring = geom.smoothstep(4500.0, 11000.0, rc) * (1.0 - geom.smoothstep(-300.0, -1200.0, Z))
    rid = noise.ridged(X / 1500.0, Z / 1500.0, 4, seed + 1)
    h += north * (rid * 210.0 + noise.fbm(X / 600.0, Z / 600.0, 3, seed + 2) * 60.0)
    # (they stand out of the plain's white on the horizon: peaks well above the lowland)
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
    # the west ravine of the 裏見之瀑: it runs down from the north and ends high in the canyon's
    # north wall, where the stream falls into the canyon (the waterfall's cliff is bare rock)
    h_r, d_r, arc_r = _carve(h, X, Z, RAVINE_W, [26, 30, 32, 30, 28, 26, 22, 18], [26, 28, 30, 30, 28, 26, 22, 18], 0.12)
    h = h_r
    water |= d_r < 1.6
    # the lookout's ravine continues into the canyon
    h, d_c, arc_c = _carve(h, X, Z, CANYON, [6, 18, 40, 62, 74, 80, 84, 86, 86, 86], [16, 22, 30, 38, 44, 48, 52, 56, 60, 66], 0.18)
    water |= d_c < 2.2
    # its walls are bare rock where it is deep (west of the lookout's ravine)
    rock = np.maximum(rock, geom.smoothstep(40.0, 14.0, d_c) * geom.smoothstep(-90.0, -160.0, X))
    # the plunge pool under the fall and the cliff it falls down
    lip = np.asarray(WATERFALL_LIP)
    foot = np.asarray(WATERFALL_FOOT)
    d_foot = np.hypot(X - foot[0], Z - foot[1])
    h -= 10.0 * geom.smoothstep(22.0, 6.0, d_foot)
    water |= d_foot < 9.0
    rock = np.maximum(rock, geom.smoothstep(34.0, 14.0, np.hypot(X - (lip[0] + foot[0]) * 0.5, Z - (lip[1] + foot[1]) * 0.5)))
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
    # the ruined temple's terrace on the summit's flank (a level pad cut into the slope)
    te_d = np.hypot((X - TEMPLE[0]) / 1.3, Z - TEMPLE[1])
    jt = int(np.argmin(np.abs(Z[:, 0] - TEMPLE[1])))
    it = int(np.argmin(np.abs(X[0, :] - TEMPLE[0])))
    t_h = float(ndimage.gaussian_filter(h, 6.0)[jt, it])
    tk = geom.smoothstep(30.0, 16.0, te_d)
    h = h * (1.0 - tk) + t_h * tk
    # forest: everything on slopes that is not rock, field, road or water, with clearings
    gz, gx = np.gradient(h, X[0, 1] - X[0, 0])
    slope = np.degrees(np.arctan(np.hypot(gx, gz)))
    rock = np.maximum(rock, geom.smoothstep(40.0, 52.0, slope))
    # the temple terrace is held by a dry-stone wall (石垣) where its edge is steep, not bare rock
    masonry = geom.smoothstep(14.0, 18.0, te_d) * geom.smoothstep(34.0, 27.0, te_d) * geom.smoothstep(24.0, 32.0, slope)
    rock = rock * (1.0 - geom.smoothstep(40.0, 30.0, te_d))
    clear = noise.fbm(X / 90.0, Z / 90.0, 3, seed + 12)
    forest = geom.smoothstep(0.32, 0.5, clear) * (1.0 - cultivated) * (1.0 - geom.smoothstep(1.0, 3.5, 4.0 - d_road)) * (1.0 - rock * 0.8)
    forest *= ~water
    forest *= geom.smoothstep(19.0, 27.0, te_d)
    return h, {"water": water, "rock": rock, "cultivated": cultivated, "road": road, "forest": forest, "slope": slope,
               "road_pts": rp, "d_ravine": d_r, "d_canyon": d_c, "temple_h": t_h, "d_temple": te_d, "masonry": masonry}


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


def _line_dist(pts, frame, step=None):
    """Distance (m) from every cell of a frame to a polyline: rasterised samples, nearest by EDT,
    then the exact distance to the nearest sample (error below the sampling step)."""
    c = frame["cell"]
    step = step or c * 0.4
    P, _ = geom.resample_polyline(np.asarray(pts, np.float64), step)
    nx, nz = frame["nx"], frame["nz"]
    ii = np.round((P[:, 0] - frame["x0"]) / c).astype(int)
    jj = np.round((P[:, 1] - frame["z0"]) / c).astype(int)
    ok = (ii >= 0) & (jj >= 0) & (ii < nx) & (jj < nz)
    seed_x = np.full((nz, nx), np.nan)
    seed_z = np.full((nz, nx), np.nan)
    seed_x[jj[ok], ii[ok]] = P[ok, 0]
    seed_z[jj[ok], ii[ok]] = P[ok, 1]
    if not ok.any():
        return np.full((nz, nx), 1e9)
    _, (ij, ii2) = ndimage.distance_transform_edt(np.isnan(seed_x), return_indices=True)
    X = frame["x0"] + np.arange(nx)[None, :] * c
    Z = frame["z0"] + np.arange(nz)[:, None] * c
    return np.hypot(X - seed_x[ij, ii2], Z - seed_z[ij, ii2])


def _poisson(rng, box, r, ok, tries=4000):
    pts = []
    for _ in range(tries):
        p = (rng.uniform(box[0], box[2]), rng.uniform(box[1], box[3]))
        if not ok(*p):
            continue
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > r * r for q in pts):
            pts.append(p)
    return pts


def _plain(out: Path, seed: int, river_pts):
    """The plain below the region: villages and a town on the dry ground between the river's loops,
    roads joining them, the railway's viaduct. Writes vista_plain.png; returns the houses, the
    railway (points with deck and ground heights) and the villages (centre, radius, size)."""
    rng = np.random.default_rng(seed + 51)
    P = PLAIN
    xs = P["x0"] + np.arange(P["nx"]) * P["cell"]
    zs = P["z0"] + np.arange(P["nz"]) * P["cell"]
    d_river = _line_dist(river_pts, P)
    rail_pts = geom.catmull(np.asarray(RAILWAY), 16)
    d_rail = _line_dist(rail_pts, P)

    def river_d(x, z):
        i = int(np.clip(round((x - P["x0"]) / P["cell"]), 0, P["nx"] - 1))
        j = int(np.clip(round((z - P["z0"]) / P["cell"]), 0, P["nz"] - 1))
        return float(d_river[j, i]), float(d_rail[j, i])

    def ground(x, z):
        return float(land(np.array(x), np.array(z), seed))

    # a town where the railway comes near the river, villages spread over the plain (denser near the
    # foot of the mountains), a few hamlets; all on the dry ground
    def dry(x, z, margin):
        dr, dl = river_d(x, z)
        return dr > margin and dl > 70.0 and _mist_e(np.array(x), np.array(z)) > 1.15 and ground(x, z) < -250.0
    villages = [(-260.0, 2160.0, 230.0, 150)]
    for (x, z) in _poisson(rng, (-5200.0, 900.0, 5200.0, 9500.0), 900.0, lambda x, z: dry(x, z, 220.0)):
        if np.hypot(x - villages[0][0], z - villages[0][1]) < 900.0:
            continue
        n = int(rng.integers(10, 34))
        villages.append((x, z, 70.0 + n * 3.2, n))
    for (x, z) in _poisson(rng, (-5200.0, 800.0, 5200.0, 9500.0), 520.0, lambda x, z: dry(x, z, 120.0)):
        if min(np.hypot(x - v[0], z - v[1]) for v in villages) < 520.0:
            continue
        if rng.uniform() < 0.55:
            villages.append((x, z, 40.0, int(rng.integers(3, 8))))
    houses = []
    for vi, (vx, vz, vr, n) in enumerate(villages):
        # houses along one or two streets through the village, gardens between
        ang = rng.uniform(0, np.pi)
        placed = 0
        tries = 0
        while placed < n and tries < n * 30:
            tries += 1
            t = rng.normal(0.0, 0.5)
            side = rng.normal(0.0, 0.32)
            street = 0 if rng.uniform() < 0.65 or n < 12 else 1
            a = ang + street * np.pi * 0.5
            x = vx + np.cos(a) * t * vr - np.sin(a) * side * vr * 0.6
            z = vz + np.sin(a) * t * vr + np.cos(a) * side * vr * 0.6
            dr, dl = river_d(x, z)
            if dr < 48.0 or dl < 30.0:
                continue
            if any((x - q[0]) ** 2 + (z - q[2]) ** 2 < 15.0 ** 2 for q in houses[-60:]):
                continue
            big = rng.uniform() < 0.12
            w = rng.uniform(11.0, 15.0) if big else rng.uniform(7.0, 10.5)
            d = w * rng.uniform(0.6, 0.8)
            houses.append([round(x, 1), round(ground(x, z), 2), round(z, 1), round(float(a + rng.choice([0.0, np.pi * 0.5]) + rng.normal(0, 0.08)), 3),
                           round(w, 1), round(d, 1), round(rng.uniform(4.5, 6.0) if big else rng.uniform(3.6, 4.8), 1),
                           int(rng.integers(0, 3)), int(rng.integers(0, 1000)), vi])
            placed += 1
    # roads: each village to its two nearest, the old road down from the region to the town
    roads = []
    V = np.asarray([(v[0], v[1]) for v in villages])
    for i, v in enumerate(V):
        d = np.hypot(V[:, 0] - v[0], V[:, 1] - v[1])
        for j in np.argsort(d)[1:3]:
            if d[j] < 2600.0:
                a, b = v, V[j]
                mid = (a + b) * 0.5 + rng.normal(0, 1, 2) * d[j] * 0.08
                roads.append(geom.catmull(np.asarray([a, mid, b]), 10))
    old_road = geom.catmull(np.asarray([(24.0, 600.0), (60.0, 900.0), (-40.0, 1300.0), (-150.0, 1700.0), (-260.0, 2160.0)]), 12)
    roads.append(old_road)
    d_road = np.full((P["nz"], P["nx"]), 1e9)
    for rp in roads:
        d_road = np.minimum(d_road, _line_dist(rp, P))
    # street lamps along the roads where they come into a village or the town (lit at night: the
    # strings of light between the villages' windows)
    lamps = []
    for rp in roads:
        pts, _ = geom.resample_polyline(rp, 60.0)
        for q in pts:
            dv = [np.hypot(q[0] - v[0], q[1] - v[1]) - v[2] for v in villages]
            k = int(np.argmin(dv))
            if dv[k] < (420.0 if k == 0 else 200.0) and _mist_e(np.array(q[0]), np.array(q[1])) > 1.15:
                lamps.append([round(float(q[0]), 1), round(ground(float(q[0]), float(q[1])), 2), round(float(q[1]), 1)])
    # the old road from the foot of the pass to the town is lit all the way: at night a string of
    # lights winds across the plain to the town's glow
    pts, _ = geom.resample_polyline(old_road, 45.0)
    for q in pts:
        if _mist_e(np.array(q[0]), np.array(q[1])) > 1.2:
            lamps.append([round(float(q[0]), 1), round(ground(float(q[0]), float(q[1])), 2), round(float(q[1]), 1)])
    # village density: soft blobs around the houses (gardens, hedges, the glow at night)
    dens = np.zeros((P["nz"], P["nx"]))
    for hs in houses:
        i = int(round((hs[0] - P["x0"]) / P["cell"]))
        j = int(round((hs[2] - P["z0"]) / P["cell"]))
        if 0 <= i < P["nx"] and 0 <= j < P["nz"]:
            dens[j, i] += 1.0
    dens = np.clip(ndimage.gaussian_filter(dens, 3.0) * 14.0, 0.0, 1.0)
    img = np.stack([np.clip(np.round(d_river), 0, 255), np.clip(np.round(d_road * 2.0), 0, 255),
                    np.round(dens * 255.0), np.clip(np.round(d_rail * 2.0), 0, 255)], -1).astype(np.uint8)
    _save(out / "vista_plain.png", img, "RGBA")
    # the railway: a point every 20 m with the deck's height and the ground's
    rp, _ = geom.resample_polyline(rail_pts, 20.0)
    seg = np.hypot(*np.diff(np.asarray(RAILWAY), axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    # deck height along the arc of the control polyline (approximately the curve's)
    arc = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(rp, axis=0).T))])
    deck = np.interp(arc / arc[-1] * cum[-1], cum, RAIL_DECK)
    rail = [[round(float(x), 1), round(float(dk), 2), round(float(z), 1), round(ground(float(x), float(z)), 2)] for (x, z), dk in zip(rp, deck)]
    return {"houses": houses, "railway": rail, "lamps": lamps,
            "villages": [[round(v[0], 1), round(v[1], 1), round(v[2], 1), v[3]] for v in villages]}


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
    masonry = np.where(inside, 0.0, F["masonry"])
    r, g = _u16(h, MID["hmin"], MID["hrange"])
    _save(out / "vista_mid.png", np.stack([r, g, _u8(F["forest"]), (F["water"] * 255).astype(np.uint8)], -1), "RGBA")
    _save(out / "vista_mat.png", np.stack([_u8(F["cultivated"]), _u8(F["road"]), _u8(F["rock"]), _u8(masonry)], -1), "RGBA")

    # ---- far grid
    xf = FAR["x0"] + np.arange(FAR["nx"]) * FAR["cell"]
    zf = FAR["z0"] + np.arange(FAR["nz"]) * FAR["cell"]
    XF, ZF = np.meshgrid(xf, zf)
    hf = land(XF, ZF, seed)
    river_pts = geom.catmull(np.asarray(RIVER), 16)
    d_rf, _, _ = geom.polyline_field(XF, ZF, river_pts)
    river = (d_rf < 40.0) & (ZF > 450.0)
    hf = np.where(river, hf - 3.0, hf)
    plain = geom.smoothstep(700.0, 1500.0, ZF)
    forest_far = geom.smoothstep(0.35, 0.55, noise.fbm(XF / 700.0, ZF / 700.0, 3, seed + 21)) * (1.0 - plain * 0.85)
    rf, gf = _u16(hf, FAR["hmin"], FAR["hrange"])
    _save(out / "vista_far.png", np.stack([rf, gf, _u8(forest_far), (river * 255).astype(np.uint8)], -1), "RGBA")

    # ---- the plain: river, roads, villages, the railway (distance fields on 8 m cells)
    plain_info = _plain(out, seed, river_pts)

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
    # the landmarks (the kiln is in the region: its marker)
    landmarks = {
        "waterfall_lip": [WATERFALL_LIP[0], 0.0, WATERFALL_LIP[1]],
        "waterfall_foot": [WATERFALL_FOOT[0], 0.0, WATERFALL_FOOT[1]],
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
    for k in ("waterfall_lip", "waterfall_foot", "pond", "hot_spring", "farm"):
        v = landmarks[k]
        v[1] = hat(v[0], v[2])
    # the tower on the summit's top
    js = int(round((SUMMIT[1] - MID["z0"]) / MID["cell"]))
    i_s = int(round((SUMMIT[0] - MID["x0"]) / MID["cell"]))
    win = h[js - 40:js + 41, i_s - 40:i_s + 41]
    jj, ii = np.unravel_index(int(np.argmax(win)), win.shape)
    tx, tz = SUMMIT[0] + (ii - 40) * MID["cell"], SUMMIT[1] + (jj - 40) * MID["cell"]
    landmarks["tower"] = [round(float(tx), 1), hat(tx, tz), round(float(tz), 1)]
    # the temple's hall faces south, toward the pass and the lookout
    landmarks["temple"] = [TEMPLE[0], round(float(F["temple_h"]), 2), TEMPLE[1], -0.1]
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
        "plain": {**PLAIN, "file": "vista_plain.png"},
        "mist": MIST,
        "plain_houses": plain_info["houses"],
        "plain_lamps": plain_info["lamps"],
        "railway": plain_info["railway"],
        "villages": plain_info["villages"],
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
    mist = geom.smoothstep(0.92, 1.4, _mist_e(X, Z))
    rgb = rgb * (1 - mist[..., None] * 0.5) + mist[..., None] * 0.5
    Image.fromarray((np.clip(rgb, 0, 1)[::2, ::2] * 255).astype(np.uint8)).save(tmp / "vista_mid_preview.png")
    return {"trees": len(trees), "houses": len(plain_info["houses"]), "villages": len(plain_info["villages"]), "h_mid": [float(h.min()), float(h.max())], "h_far": [float(hf.min()), float(hf.max())]}
