"""Builds one terrain region from its layout: heights, materials, water, walkability, placements.

    python3 tools/world3d/build_terrain.py [tools/world3d/layouts/saddle.json]
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
from scipy import ndimage

from . import edits, export, geom, landform, materials, noise, pixelart, placement

ROOT = Path(__file__).resolve().parents[3]


def log(*a):
    print("[w3terrain]", *a, flush=True)


def build(layout_path: Path, out_godot: Path | None = None, out_tmp: Path | None = None):
    t0 = time.time()
    L = json.loads(Path(layout_path).read_text())
    name = L["name"]
    out_godot = out_godot or ROOT / "godot" / "world3d" / "terrain" / name
    out_tmp = out_tmp or ROOT / "tools" / "world3d" / "out" / name
    out_godot.mkdir(parents=True, exist_ok=True)
    out_tmp.mkdir(parents=True, exist_ok=True)
    x0, z0, x1, z1 = L["bounds"]
    cell = float(L["cell"])
    nx = int(round((x1 - x0) / cell)) + 1
    nz = int(round((z1 - z0) / cell)) + 1
    xs = x0 + np.arange(nx) * cell
    zs = z0 + np.arange(nz) * cell
    X, Z = np.meshgrid(xs, zs)
    rng = np.random.default_rng(int(L["seed"]))
    M = L["markers"]

    # ---------------- landform
    h, zr, hr = landform.base(L, X, Z)
    h = landform.spur_and_ravine(L, X, Z, h)
    home = np.hypot(X, Z * 1.15)
    protect = geom.smoothstep(L["erosion"]["protect_radius_home"], L["erosion"]["protect_radius_home"] * 0.55, home)
    # never erode the spur crest or the gully floor into nonsense
    sd, _, _ = geom.polyline_field(X, Z, np.asarray(L["spur"]["axis"]))
    protect = np.maximum(protect, geom.smoothstep(6.0, 2.0, sd))
    log("landform", f"{time.time() - t0:.1f}s", "range", float(h.min()), float(h.max()))
    h = landform.erode(L, X, Z, h, cell, protect)
    log("eroded", f"{time.time() - t0:.1f}s")

    # ---------------- human-made edits
    # terraces first (they are older than the road that winds past them)
    h, paddy, paddy_lvl = edits.terraces(h, X, Z, L["terraces"], int(L["seed"]) + 3)
    # the road: profile from the land, grade-limited, then cut and fill
    R = L["road"]
    rpts = geom.catmull(np.asarray(R["points"], np.float64), 10)
    RP, rs, rprof = edits.road_profile(h, x0, z0, cell, rpts, R["max_grade"], window=6.0)
    h_before_road = h.copy()
    h, road_d, road_arc, road_h = edits.cut_corridor(h, X, Z, RP, rprof, R["width"], R["bank"], bank_slope=0.95, wobble_seed=int(L["seed"]) + 5)
    # pads (yard, shrine terrace, graves bench, lookout top)
    pad_sdf = {}
    for p in L["pads"]:
        h, sdf = edits.apply_pad(h, X, Z, p, int(L["seed"]) + 9)
        pad_sdf[p["id"]] = sdf
    # footpaths after the pads so they meet them
    path_fields = []
    for P in L["paths"]:
        pts = geom.catmull(np.asarray(P["points"], np.float64), 8)
        h, d, arc = edits.flatten_path(h, X, Z, pts, P["width"], cell=cell)
        path_fields.append((P, pts, d))
    step_info = []
    for st in L["steps"]:
        h, hh = edits.apply_steps(h, X, Z, st)
        step_info.append({**st, "h_from": hh[0], "h_to": hh[1]})
    h, stream_d, stream_surf, SP, sfloor = edits.carve_stream(h, X, Z, L["stream"], cell)
    h, pool_e, pool_surf = edits.spring_pool(h, X, Z, L["spring"], int(L["seed"]) + 13)
    h, kiln_d = edits.kiln(h, X, Z, L["kiln"])
    # re-lay the road surface (later edits may have nudged it) and smooth seams lightly
    road_core = road_d <= R["width"] * 0.5
    hs = ndimage.gaussian_filter(h, 0.6)
    h = np.where(road_core, h, hs * 0.35 + h * 0.65)
    log("edits", f"{time.time() - t0:.1f}s")

    # ---------------- water: pool, stream, paddies (surface height + kind + flow)
    water_h = np.full(h.shape, -1000.0)
    water_k = np.zeros(h.shape, np.uint8)
    flow = np.zeros(h.shape + (2,))
    pool_in = pool_e < 1.15
    water_h = np.where(pool_in, pool_surf, water_h)
    water_k = np.where(pool_in, 1, water_k)
    # stream surface along its line, a little wider than the bed so the banks hide the edge
    sd2, sarc, ssurf = geom.polyline_field(X, Z, SP, sfloor - 0.12)
    in_stream = (sd2 < L["stream"]["width"] * 0.5 + 0.2) & (~pool_in) & (h < ssurf - 0.02)
    in_stream = ndimage.binary_dilation(in_stream, iterations=1) & (sd2 < L["stream"]["width"] * 0.5 + 0.8) & (~pool_in)
    water_h = np.where(in_stream, ssurf, water_h)
    water_k = np.where(in_stream, 2, water_k)
    # flow direction: along the stream's tangent at the nearest point
    gzs, gxs = np.gradient(sarc)
    nrm = np.hypot(gxs, gzs) + 1e-9
    flow[..., 0] = np.where(in_stream, gxs / nrm, 0.0)
    flow[..., 1] = np.where(in_stream, gzs / nrm, 0.0)
    # paddies: water a few centimetres above the flat
    pad_h = ndimage.grey_closing(np.where(paddy > 0.5, h, -1000.0), size=3)
    pk = paddy > 0.5
    water_h = np.where(pk & (water_k == 0), h + 0.05, water_h)
    water_k = np.where(pk & (water_k == 0), 3, water_k)

    # ---------------- walkability (props add their footprints at runtime)
    gz_, gx_ = np.gradient(h, cell)
    slope = np.degrees(np.arctan(np.hypot(gx_, gz_)))
    walk = (slope <= 35.0)
    deep = (water_k == 1) | ((water_k == 2) & (water_h - h > 0.28))
    walk &= ~deep
    walk |= road_core
    for p in L["pads"]:
        walk |= pad_sdf[p["id"]] < -0.2
    walk = ndimage.binary_opening(walk, iterations=1)
    log("water & walk", f"{time.time() - t0:.1f}s", "walkable", f"{walk.mean() * 100:.1f}%")

    # ---------------- placements (trees, bamboo, shrubs, ferns, boulders)
    def grid_lookup(arr):
        def f(x, z):
            i = int(round((x - x0) / cell))
            j = int(round((z - z0) / cell))
            i = min(max(i, 0), nx - 1)
            j = min(max(j, 0), nz - 1)
            return float(arr[j, i])
        return f
    path_all = road_d - R["width"] * 0.5
    for P, pts, d in path_fields:
        path_all = np.minimum(path_all, d - P["width"] * 0.5)
    pad_all = np.minimum.reduce([pad_sdf[k] for k in pad_sdf])
    water_dist = ndimage.distance_transform_edt(water_k == 0) * cell
    zones = {k: geom.polygon_sdf(X, Z, v) < 0 for k, v in L["zones"].items()}
    ctx = {
        "height": grid_lookup(h), "slope_deg": grid_lookup(slope), "path_dist": grid_lookup(path_all),
        "pad_dist": grid_lookup(pad_all), "water_dist": grid_lookup(water_dist),
        "in_zone": lambda name, x, z: bool(grid_lookup(zones[name])(x, z)),
        "aspect": grid_lookup(np.arctan2(-gx_, -gz_)),      # yaw facing downhill
    }
    plc = placement.place(L, ctx, rng)
    for p in plc:
        p["y"] = ctx["height"](p["x"], p["z"])
    log("placements", len(plc), f"{time.time() - t0:.1f}s")

    # ---------------- materials on the splat grid
    cs = float(L["splat_cell"])
    sx = x0 + np.arange(int(round((x1 - x0) / cs)) + 1) * cs
    sz = z0 + np.arange(int(round((z1 - z0) / cs)) + 1) * cs
    Xs, Zs = np.meshgrid(sx, sz)
    fi = (Xs - x0) / cell
    fj = (Zs - z0) / cell

    def up(arr, order=1):
        return ndimage.map_coordinates(arr.astype(np.float64), [fj, fi], order=order, mode="nearest")
    Hs = up(h)
    F = {}
    F["road_d"] = up(road_d)
    F["road_hw"] = R["width"] * 0.5
    F["road_bank"] = geom.smoothstep(R["width"] * 0.5 + R["bank"] + 2.0, R["width"] * 0.5 + 0.2, up(road_d)) * geom.smoothstep(0.25, 0.6, up(np.abs(h - h_before_road)))
    F["road_wear"] = geom.smoothstep(R["width"] * 0.42, 0.0, up(road_d))
    # outer side of the road's bends (gravel thrown out by feet and rain)
    F["road_outer"] = geom.smoothstep(0.5, 1.3, up(road_d) - R["width"] * 0.25)
    F["paths"] = [(up(d), P["width"] * 0.5) for P, pts, d in path_fields]
    pw = np.zeros_like(Hs)
    for d, hw in F["paths"]:
        pw = np.maximum(pw, geom.smoothstep(hw * 0.9, 0.0, d))
    F["path_wear"] = pw
    F["yard_sdf"] = up(pad_sdf["hut_yard"])
    F["shrine_sdf_k"] = geom.smoothstep(0.4, -0.2, up(pad_sdf["shrine_terrace"]))
    F["graves_k"] = geom.smoothstep(1.2, -0.5, up(pad_sdf["graves_bench"]))
    F["lookout_top"] = geom.smoothstep(0.8, -0.5, up(pad_sdf["lookout_top"]))
    dsj = np.asarray(M["dosojin"])
    F["dosojin_k"] = geom.smoothstep(2.4, 1.2, np.hypot(Xs - dsj[0], Zs - dsj[1]) + (noise.fbm(Xs / 1.3, Zs / 1.3, 2, 4) - 0.5) * 1.2)
    F["spur_rock"] = geom.smoothstep(9.0, 3.0, up(sd))
    F["spring_face"] = geom.smoothstep(0.5, 0.0, up(np.abs(geom.polyline_field(X, Z, geom.catmull(np.asarray(L["spring"]["rock_face"]), 6))[0] - 1.1)) - 0.2) * geom.smoothstep(20.0, 30.0, up(slope))
    F["stream_bed"] = geom.smoothstep(L["stream"]["width"] * 0.5 + 0.4, L["stream"]["width"] * 0.5 - 0.3, up(stream_d))
    F["water_d"] = up(water_dist)
    F["water_core"] = geom.smoothstep(0.3, -0.2, up(water_dist) - 0.0) * up((water_k == 1).astype(float))
    F["cedar"] = up(zones["cedar"].astype(float))
    F["paddy"] = up(paddy, order=0)
    F["terrace_bank"] = up(((paddy < 0.5) & (geom.polygon_sdf(X, Z, L["terraces"]["poly"]) < -1.0)).astype(float)) * geom.smoothstep(12.0, 25.0, up(slope))
    F["camphor_roots"] = geom.smoothstep(9.0, 3.0, np.hypot(Xs - M["camphor"][0], Zs - M["camphor"][1]))
    F["trunk_k"] = geom.smoothstep(4.0, 1.5, np.hypot(Xs - M["camphor"][0], Zs - M["camphor"][1]))
    canopy = np.zeros_like(Hs)
    kind = np.zeros_like(Hs)
    for p in plc:
        r = placement.CANOPY_R.get(p["kind"], 0.0) * p.get("scale", 1.0)
        if r <= 0:
            continue
        # canopy footprint, offset a little downslope/south where crowns lean over
        cx, cz = p["x"], p["z"]
        i0 = int((cx - r - 1 - x0) / cs); i1 = int((cx + r + 1 - x0) / cs) + 1
        j0 = int((cz - r - 1 - z0) / cs); j1 = int((cz + r + 1 - z0) / cs) + 1
        i0, j0 = max(i0, 0), max(j0, 0)
        i1, j1 = min(i1, Hs.shape[1]), min(j1, Hs.shape[0])
        if i1 <= i0 or j1 <= j0:
            continue
        sub_x = Xs[j0:j1, i0:i1]
        sub_z = Zs[j0:j1, i0:i1]
        d = np.hypot(sub_x - cx, sub_z - cz) / r
        k = geom.smoothstep(1.15, 0.45, d) * (1.4 if p["kind"] == "camphor" else 1.0)
        canopy[j0:j1, i0:i1] = np.maximum(canopy[j0:j1, i0:i1], k)
        lk = {"cedar": 0.5, "pine": 0.5, "bamboo": 1.0}.get(p["kind"], 0.0)
        kind[j0:j1, i0:i1] = np.where(k > 0.3, lk, kind[j0:j1, i0:i1])
    F["canopy"] = np.clip(canopy, 0, 1)
    F["litter_kind"] = kind
    mats = materials.compute(L, F, Xs, Zs, Hs, cs, plc)
    log("materials", f"{time.time() - t0:.1f}s")

    # ---------------- stonework: retaining walls along the walled sides of pads (their real edges)
    from skimage import measure
    walls = []
    gzs_all = {}
    for p in L["pads"]:
        sides = p.get("wall", [])
        if not sides:
            continue
        sdf = pad_sdf[p["id"]]
        gzs, gxs = np.gradient(sdf)
        for c in measure.find_contours(sdf, 0.0):
            if len(c) < 6:
                continue
            pts = np.stack([x0 + c[:, 1] * cell, z0 + c[:, 0] * cell], -1)
            P, _ = geom.resample_polyline(pts, 0.4)
            rows = []
            for q in P:
                i_ = min(max(int(round((q[0] - x0) / cell)), 0), nx - 1)
                j_ = min(max(int(round((q[1] - z0) / cell)), 0), nz - 1)
                n_ = np.array([gxs[j_, i_], gzs[j_, i_]])
                n_ /= (np.linalg.norm(n_) + 1e-9)
                outside = float(edits.sample_point(h, X, Z, q + n_ * 1.0))
                pad_h = float(p["height"])
                rows.append((q, n_, pad_h, outside))
            # keep only where there is a real step; split into runs
            run = []
            def flush(run):
                if len(run) >= 3:
                    walls.append({"pad": p["id"],
                                  "points": [[round(float(r[0][0]), 3), round(float(r[0][1]), 3)] for r in run],
                                  "normals": [[round(float(r[1][0]), 3), round(float(r[1][1]), 3)] for r in run],
                                  "top": [round(max(r[2], r[3]), 3) for r in run],
                                  "bottom": [round(min(r[2], r[3]), 3) for r in run],
                                  "cut": [bool(r[3] > r[2]) for r in run]})
            for r in rows:
                if abs(r[3] - r[2]) > 0.28:
                    run.append(r)
                else:
                    flush(run)
                    run = []
            flush(run)

    # ---------------- shared pixel art (palette + glyph atlas)
    table = pixelart.write(out_godot.parent / "common")
    (out_godot.parent / "common" / "glyphs.json").write_text(json.dumps(table, indent=1))

    # ---------------- export
    info = export.write(L, out_godot, out_tmp, dict(
        h=h, X=X, Z=Z, x0=x0, z0=z0, cell=cell, nx=nx, nz=nz, walk=walk, water_h=water_h, water_k=water_k,
        flow=flow, mats=mats, cs=cs, Hs=Hs, placements=plc, road=(RP, rprof), paths=path_fields, walls=walls,
        steps=step_info, pool_surf=pool_surf, stream=(SP, sfloor), slope=slope))
    log("done", f"{time.time() - t0:.1f}s", info)
    return info
