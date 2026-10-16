"""Where the trees, bamboo, shrubs, ferns and boulders stand (generic kinds; the assembly maps
them onto the asset catalog). Poisson-disc sampling per zone with slope, path and pad rules,
clumped by noise so woods have glades and edges have stragglers."""
from __future__ import annotations

import numpy as np

from . import geom, noise


def poisson(rng, bounds, r, accept, k=24, max_pts=20000):
    """Bridson's Poisson-disc sampler over a rectangle; accept(x, z) -> bool filters candidates."""
    x0, z0, x1, z1 = bounds
    cs = r / np.sqrt(2.0)
    gw = int(np.ceil((x1 - x0) / cs)) + 1
    gh = int(np.ceil((z1 - z0) / cs)) + 1
    grid = -np.ones((gh, gw), np.int64)
    pts = []
    active = []
    for _ in range(200):
        p = np.array([rng.uniform(x0, x1), rng.uniform(z0, z1)])
        if accept(p[0], p[1]):
            break
    else:
        return np.zeros((0, 2))
    pts.append(p)
    active.append(0)
    grid[int((p[1] - z0) / cs), int((p[0] - x0) / cs)] = 0
    while active and len(pts) < max_pts:
        i = active[rng.integers(len(active))]
        base = pts[i]
        found = False
        for _ in range(k):
            a = rng.uniform(0, 2 * np.pi)
            rr = rng.uniform(r, 2 * r)
            q = base + rr * np.array([np.cos(a), np.sin(a)])
            if not (x0 <= q[0] < x1 and z0 <= q[1] < z1):
                continue
            gi, gj = int((q[1] - z0) / cs), int((q[0] - x0) / cs)
            ok = True
            for jj in range(max(0, gi - 2), min(gh, gi + 3)):
                for ii in range(max(0, gj - 2), min(gw, gj + 3)):
                    t = grid[jj, ii]
                    if t >= 0 and np.hypot(*(pts[t] - q)) < r:
                        ok = False
                        break
                if not ok:
                    break
            if ok and accept(q[0], q[1]):
                pts.append(q)
                active.append(len(pts) - 1)
                grid[gi, gj] = len(pts) - 1
                found = True
                break
        if not found:
            active.remove(i)
    return np.array(pts)


def place(L, ctx, rng):
    """ctx: callables height(x, z), slope_deg(x, z), path_dist(x, z), pad_dist(x, z),
    water_dist(x, z), in_zone(name, x, z). Returns a list of dicts {kind, x, z, rot, scale, variant}."""
    out = []
    b = L["bounds"]
    M = L["markers"]

    def keep_clear(x, z, clear=2.2):
        return ctx["path_dist"](x, z) > clear and ctx["pad_dist"](x, z) > 1.5 and ctx["water_dist"](x, z) > 1.2

    def far_from_markers(x, z, r):
        for k in ("camphor", "hut", "shrine", "graves", "lookout", "dosojin", "spring", "kiln", "persimmon", "woodpile",
                  "gate_main", "iwakura", "garden", "chozubachi", "jizo"):
            if k not in M:
                continue
            m = M[k]
            rr = 15.0 if k == "camphor" else r
            if np.hypot(x - m[0], z - m[1]) < rr:
                return False
        return True

    # sight lines: in the 3/4 view a tree of height H hides the ground up to about 1.2 H metres
    # north of its foot, so no tall tree stands just south of the places the player looks at
    # (the yard, the shrine, the graves, the lookout, the spring pool). The canopy cut-away only
    # thins what is right around her; it cannot rescue a home hidden behind a pine.
    keep_areas = []
    for pd in L["pads"]:
        if "poly" in pd:
            pp = np.asarray(pd["poly"], np.float64)
            keep_areas.append((float(pp[:, 0].min()), float(pp[:, 0].max()), float(pp[:, 1].max())))
            continue
        c, sz = pd["centre"], pd["size"]
        keep_areas.append((c[0] - sz[0] * 0.5, c[0] + sz[0] * 0.5, c[1] + sz[1] * 0.5))
    keep_areas.append((-10.0, 10.0, 10.8))            # the path in front of the great tree
    sp = M["spring"]
    keep_areas.append((sp[0] - 4.0, sp[0] + 4.0, sp[1] + 2.0))
    dj = M["dosojin"]
    keep_areas.append((dj[0] - 2.5, dj[0] + 2.5, dj[1] + 1.2))     # the dosojin (0.8 m tall: easily lost)
    if "gate_main" in M:
        g = M["gate_main"]
        keep_areas.append((g[0] - 3.5, g[0] + 3.5, g[1] + 1.5))    # the approach: the gate, its steps and the tree
    if "garden" in M:
        g = M["garden"]
        keep_areas.append((g[0] - 3.6, g[0] + 3.6, g[1] + 2.4))
    TREE_H = {"cedar": 18.0, "pine": 11.0, "maple": 7.0, "beech": 9.0, "broadleaf": 8.0, "bamboo": 9.0}

    def clear_view(x, z, kind, r=3.0):
        H = TREE_H.get(kind, 0.0)
        for ax0, ax1, az in keep_areas:
            if ax0 - r - 1.0 <= x <= ax1 + r + 1.0 and az - 0.5 <= z <= az + 1.22 * H:
                return False
        return True

    # the great camphor and the named trees
    out.append({"kind": "camphor", "x": M["camphor"][0], "z": M["camphor"][1], "rot": 0.4, "scale": 1.0, "variant": 0})
    out.append({"kind": "persimmon", "x": M["persimmon"][0], "z": M["persimmon"][1], "rot": 1.1, "scale": 1.0, "variant": 0})
    # the tree she may fell for firewood (marker choppable_tree): a young coppice oak in full leaf
    # (round 5, G5R3-5: the dead stand-in read as "a bare, dead tree" left of the house)
    out.append({"kind": "konara", "x": M["choppable_tree"][0], "z": M["choppable_tree"][1], "rot": 2.0, "scale": 0.58, "variant": 1,
                "role": "choppable"})
    # the old trees the gates' michikiri ropes are tied to (layout gate_trees)
    for gt in L.get("gate_trees", []):
        out.append({"kind": gt["kind"], "x": float(gt["x"]), "z": float(gt["z"]), "rot": float(gt.get("rot", 0.0)),
                    "scale": float(gt.get("scale", 1.0)), "variant": int(gt.get("variant", 0)), "fixed": True})

    # round 5 (G5R3-3, composition plan approved 2026-10-16): inside the barrier everything is planted
    # by hand: masses in four layers with a forest edge, and single specimen trees; the random scatter
    # below keeps out of the barrier
    out.extend(authored(L, ctx, rng))
    sanct = (lambda x, z: ctx["in_zone"]("sanctum", x, z)) if "sanctum" in L["zones"] else (lambda x, z: False)

    # cedars: the far side of the gully and the north-west woods, with glades
    def cedar_ok(x, z):
        if not ctx["in_zone"]("cedar", x, z):
            return False
        if ctx["slope_deg"](x, z) > 38 or not keep_clear(x, z, 2.5) or not clear_view(x, z, "cedar", 2.6):
            return False
        return noise.fbm(np.array(x / 18.0), np.array(z / 18.0), 3, 5) > 0.36
    for p in poisson(rng, (b[0], b[1], b[2], -38.0), 3.4, cedar_ok):
        out.append({"kind": "cedar", "x": float(p[0]), "z": float(p[1]), "rot": float(rng.uniform(0, 6.28)), "scale": float(rng.uniform(0.85, 1.2)), "variant": int(rng.integers(0, 8))})

    # broadleaf trees on the slopes around the home, sparser, never on the saddle's crown
    def broad_ok(x, z):
        if ctx["in_zone"]("cedar", x, z) or ctx["in_zone"]("bamboo", x, z) or ctx["in_zone"]("home", x, z):
            return False
        if ctx["slope_deg"](x, z) > 34 or not keep_clear(x, z, 2.6) or not far_from_markers(x, z, 7.0):
            return False
        if not clear_view(x, z, "broadleaf", 3.4):
            return False
        n = noise.fbm(np.array(x / 22.0), np.array(z / 22.0), 3, 9)
        return n > 0.5 and ctx["height"](x, z) > -26.0
    for p in poisson(rng, (b[0], -36.0, b[2], 104.0), 6.5, broad_ok):
        kind = "maple" if rng.uniform() < 0.3 else ("beech" if rng.uniform() < 0.5 else "broadleaf")
        var = int(rng.integers(0, 8))
        if kind == "maple" and var % 4 == 3:
            var -= 1           # (variant 3 mod 4 is the red accent: in August only where placed on purpose)
        out.append({"kind": kind, "x": float(p[0]), "z": float(p[1]), "rot": float(rng.uniform(0, 6.28)), "scale": float(rng.uniform(0.8, 1.15)), "variant": var})

    # red pines on the spur and the rocky rim above the ravine. Looking back home from the lookout
    # (the view from the lookout, godot/world3d/vista3d.gd: the camera 18.1 m out over the drop,
    # bearing 202 from her, 4 m over her feet) the great camphor, the hut, the shrine and the graves
    # must stand clear: no pine between that camera and them (bearings 6 to 48 degrees, nearer than
    # the camphor). Two pines frame that view instead; the eastern one also frames the view south.
    lk = M["lookout"]
    home_cam = (lk[0] + np.sin(np.radians(202.0)) * 18.11, lk[1] - np.cos(np.radians(202.0)) * 18.11)

    def in_home_view(x, z):
        dx, dz = x - home_cam[0], z - home_cam[1]
        b = np.degrees(np.arctan2(dx, -dz))
        return 6.0 < b < 48.0 and np.hypot(dx, dz) < 64.0

    def pine_ok(x, z):
        sp = np.asarray(L["spur"]["axis"])
        d = min(np.hypot(x - q[0], z - q[1]) for q in sp)
        if d > 7.0 or ctx["slope_deg"](x, z) > 40 or not keep_clear(x, z, 1.6) or not clear_view(x, z, "pine", 5.0):
            return False
        return np.hypot(x - lk[0], z - lk[1]) > 4.0
    # (the corridor is cleared after sampling, with the same random draws, so that everything
    # placed later stays exactly where it was)
    for p in poisson(rng, (-34.0, 8.0, -8.0, 46.0), 5.5, pine_ok)[:7]:
        e = {"kind": "pine", "x": float(p[0]), "z": float(p[1]), "rot": float(rng.uniform(0, 6.28)), "scale": float(rng.uniform(0.8, 1.1)), "variant": int(rng.integers(0, 8))}
        if not in_home_view(e["x"], e["z"]):
            out.append(e)
    frame_pines = [{"kind": "pine", "x": x, "z": z, "rot": r, "scale": sc, "variant": var}
                   for (x, z, r, sc, var) in ((-15.1, 46.3, 2.2, 1.05, 2), (-32.5, 37.5, 4.9, 1.0, 5), (-35.5, 27.5, 0.8, 0.9, 3))
                   if ctx["slope_deg"](x, z) < 42 and keep_clear(x, z, 1.4)]

    # bamboo clumps on the east shoulder
    def bamboo_ok(x, z):
        return ctx["in_zone"]("bamboo", x, z) and ctx["slope_deg"](x, z) < 36 and keep_clear(x, z, 1.8) and clear_view(x, z, "bamboo", 1.6)
    grove = []
    for p in poisson(rng, (30.0, -28.0, 72.0, 18.0), 1.9, bamboo_ok):
        grove.append({"kind": "bamboo", "x": float(p[0]), "z": float(p[1]), "rot": float(rng.uniform(0, 6.28)), "scale": float(rng.uniform(0.85, 1.15)), "variant": int(rng.integers(0, 8))})
    # thinned (art sample round 2: the grove was a wall): clumps at least 2.8 m apart, and glades
    # where the light comes down to the floor. Done after the draws, so the random stream (and every
    # placement after this one) stays as it was.
    kept = []
    for clump in grove:
        if noise.fbm(np.array(clump["x"] / 11.0), np.array(clump["z"] / 11.0), 2, 31) < 0.38:
            continue
        if all(np.hypot(clump["x"] - k["x"], clump["z"] - k["z"]) >= 2.8 for k in kept):
            kept.append(clump)
    out.extend(kept)

    # shrubs along edges (azalea, hydrangea), ferns in the shade, boulders where the ground is rough
    def shrub_ok(x, z):
        if sanct(x, z):
            return False
        pd = ctx["path_dist"](x, z)
        if pd < 1.6 or pd > 7.0 or ctx["pad_dist"](x, z) < 1.0 or ctx["water_dist"](x, z) < 1.0:
            return False
        if ctx["slope_deg"](x, z) > 33 or not far_from_markers(x, z, 4.5):
            return False
        return noise.fbm(np.array(x / 7.0), np.array(z / 7.0), 2, 13) > 0.48
    for p in poisson(rng, (b[0], -40.0, b[2], 100.0), 3.0, shrub_ok):
        kind = "hydrangea" if (p[1] < 10 and rng.uniform() < 0.5) else ("azalea" if rng.uniform() < 0.6 else "shrub")
        out.append({"kind": kind, "x": float(p[0]), "z": float(p[1]), "rot": float(rng.uniform(0, 6.28)), "scale": float(rng.uniform(0.8, 1.2)), "variant": int(rng.integers(0, 8))})

    # the sacred grove between the home and the old road (zones.chinju, chinju_south): camellias,
    # hydrangeas and azaleas close together, a few maples on its southern end; nothing tall where it
    # would hide the approach or the graves
    def belt_ok(x, z):
        if L.get("plantings"):
            return False          # (round 5: the sacred grove is planted by hand, authored())
        inz = ("chinju" in L["zones"] and ctx["in_zone"]("chinju", x, z)) or ("chinju_south" in L["zones"] and ctx["in_zone"]("chinju_south", x, z))
        return inz and ctx["slope_deg"](x, z) < 34 and keep_clear(x, z, 1.3) and far_from_markers(x, z, 2.5)
    for p in poisson(rng, (2.0, -14.0, 16.0, 21.0), 1.55, belt_ok):
        r = rng.uniform()
        kind = "shrub" if r < 0.42 else ("hydrangea" if r < 0.72 else ("azalea" if r < 0.9 else "fern"))
        if p[1] > 15.5 and rng.uniform() < 0.12 and clear_view(float(p[0]), float(p[1]), "maple", 3.0):
            kind = "maple"
        out.append({"kind": kind, "x": float(p[0]), "z": float(p[1]), "rot": float(rng.uniform(0, 6.28)), "scale": float(rng.uniform(0.85, 1.15)), "variant": int(rng.integers(0, 8))})
    # inside the barrier: hydrangeas along the approach and round the shrine's terrace
    def sanct_flowers(x, z):
        if L.get("plantings"):
            return False
        if "oku" not in L["zones"] or not (ctx["in_zone"]("oku", x, z) or ctx["in_zone"]("home", x, z)):
            return False
        pd = ctx["path_dist"](x, z)
        return 0.9 < pd < 2.6 and ctx["pad_dist"](x, z) > 0.6 and ctx["slope_deg"](x, z) < 30 and far_from_markers(x, z, 2.2) and np.hypot(x, z) > 6.0
    for p in poisson(rng, (-28.0, -12.0, 12.0, 22.0), 1.8, sanct_flowers)[:60]:
        out.append({"kind": "hydrangea", "x": float(p[0]), "z": float(p[1]), "rot": float(rng.uniform(0, 6.28)), "scale": float(rng.uniform(0.75, 1.05)), "variant": int(rng.integers(0, 8))})

    def fern_ok(x, z):
        if L.get("plantings") and sanct(x, z):
            return False
        shade = ctx["in_zone"]("cedar", x, z) or ctx["water_dist"](x, z) < 6.0 or np.hypot(x, z) < 13.0
        return shade and keep_clear(x, z, 1.2) and ctx["slope_deg"](x, z) < 40 and far_from_markers(x, z, 2.5)
    for p in poisson(rng, (b[0], -60.0, 40.0, 20.0), 2.2, fern_ok)[:420]:
        out.append({"kind": "fern", "x": float(p[0]), "z": float(p[1]), "rot": float(rng.uniform(0, 6.28)), "scale": float(rng.uniform(0.8, 1.2)), "variant": int(rng.integers(0, 8))})

    def rock_ok(x, z):
        s = ctx["slope_deg"](x, z)
        return 14 < s < 44 and keep_clear(x, z, 1.4) and far_from_markers(x, z, 4.0) and noise.value(np.array(x / 9.0), np.array(z / 9.0), 21) > 0.55
    for p in poisson(rng, (b[0], b[1], b[2], b[3]), 4.5, rock_ok)[:160]:
        out.append({"kind": "boulder", "x": float(p[0]), "z": float(p[1]), "rot": float(rng.uniform(0, 6.28)), "scale": float(rng.uniform(0.5, 1.4)), "variant": int(rng.integers(0, 8))})
    # rock outcrops where the ground is too steep to hold soil (the spur, the ravine head, banks)
    def outcrop_ok(x, z):
        sl = ctx["slope_deg"](x, z)
        return sl > 33.0 and ctx["path_dist"](x, z) > 1.0 and ctx["pad_dist"](x, z) > 0.4 and ctx["water_dist"](x, z) > 0.6
    for p in poisson(rng, (b[0], b[1], b[2], b[3]), 2.3, outcrop_ok)[:700]:
        sl = ctx["slope_deg"](p[0], p[1])
        k = np.clip((sl - 33.0) / 25.0, 0.0, 1.0)
        size = 1.1 + 2.2 * k * rng.uniform(0.6, 1.0)
        out.append({"kind": "outcrop", "x": float(p[0]), "z": float(p[1]), "rot": float(ctx["aspect"](p[0], p[1]) + rng.uniform(-0.5, 0.5)),
                    "sx": float(size * rng.uniform(1.0, 1.5)), "sy": float(size * rng.uniform(0.55, 0.8)), "sz": float(size * rng.uniform(0.7, 1.0)),
                    "sink": 0.42, "variant": int(rng.integers(0, 16))})
    # the face behind the spring: slabs along it
    F = np.asarray(L["spring"]["rock_face"], np.float64)
    from .geom import resample_polyline
    Pf, _ = resample_polyline(F, 2.3)
    for k, q in enumerate(Pf):
        big = k % 2 == 0
        out.append({"kind": "rock_slab", "x": float(q[0] + rng.uniform(-0.3, 0.3)), "z": float(q[1] - (0.9 if big else 0.4)), "rot": float(rng.uniform(-0.5, 0.5)),
                    "sx": float(rng.uniform(1.5, 2.1) if big else rng.uniform(0.9, 1.3)), "sy": float(rng.uniform(1.8, 2.6) if big else rng.uniform(0.9, 1.4)),
                    "sz": float(rng.uniform(1.0, 1.4)), "sink": 0.3, "variant": int(rng.integers(0, 16))})
    # the lookout: its tip is ringed by big rocks below the standing place
    lk = np.asarray(M["lookout"], np.float64)
    for k in range(9):
        a = -np.pi * 0.95 + k * (np.pi * 1.9 / 8.0) + rng.uniform(-0.15, 0.15)
        r = rng.uniform(2.6, 3.6)
        x, z = lk[0] + np.cos(a) * r, lk[1] + np.sin(a) * r * 0.85 + 0.6
        if z < lk[1] - 1.2:
            continue
        sz = rng.uniform(1.8, 2.8)
        out.append({"kind": "outcrop", "x": float(x), "z": float(z), "rot": float(a + np.pi * 0.5), "sx": float(sz * 1.3), "sy": float(sz * 0.9), "sz": float(sz),
                    "sink": 0.55, "variant": int(rng.integers(0, 16))})
    # stepping stones where the old road fords the stream
    for k in range(5):
        out.append({"kind": "boulder", "x": float(-3.4 + k * 0.75 + rng.uniform(-0.1, 0.1)), "z": float(-39.4 + k * 0.05 + rng.uniform(-0.25, 0.25)),
                    "rot": float(rng.uniform(0, 6.28)), "scale": 0.55, "sink": 0.55, "variant": int(rng.integers(0, 16))})
    return out + frame_pines


CANOPY_R = {"camphor": 13.0, "cedar": 2.6, "furusugi": 1.8, "maple": 3.4, "beech": 3.6, "broadleaf": 3.4, "pine": 3.0,
            "persimmon": 3.2, "choppable": 1.6, "bamboo": 1.6}


# ------------------------------------------------------------------------------------------------
# authored plantings (round 5)
LAYER_DEFAULTS = {
    # layer: spacing (m), where in the mass (inset from its edge, m; negative: outside it), scale range
    "canopy": (4.2, (1.6, 99.0), (0.85, 1.15)),
    "sub": (2.3, (0.5, 99.0), (0.8, 1.15)),
    "shrub": (1.35, (0.0, 1.9), (0.75, 1.1)),       # the mantle (マント群落): dense along the edge
    "ground": (1.15, (0.3, 99.0), (0.8, 1.2)),
    "sode": (0.9, (-1.1, 0.1), (0.75, 1.1)),          # the sleeve (ソデ群落): tall herbs just outside
}
CROWN_R = 14.0      # the great camphor's crown: no other canopy tree under it


def authored(L, ctx, rng):
    """Masses ("plantings": polygon, layers {name: {kinds: {kind: weight}, spacing, inset, scale}}) and
    specimens ("specimens": exact kinds or asset names at exact places). A kind may be a placement
    kind (cedar, broadleaf, shrub, hydrangea, ...) or an asset name (tsubaki_a, maple_a, ...)."""
    out = []
    specs = L.get("specimens", [])
    for sp in specs:
        out.append({"kind": sp["kind"], "x": float(sp["x"]), "z": float(sp["z"]), "rot": float(sp.get("rot", rng.uniform(0, 6.28))),
                    "scale": float(sp.get("scale", 1.0)), "variant": int(sp.get("variant", 0)), "fixed": True,
                    **({"role": sp["role"]} if "role" in sp else {}),
                    # (a set stone: how deep it sits, its own extents; rocks.gd reads them)
                    **{k: float(sp[k]) for k in ("sink", "sx", "sy", "sz") if k in sp}})
    keep_out = [(float(sp["x"]), float(sp["z"]), float(sp.get("clear", 1.4))) for sp in specs]
    for g in L.get("plantings", []):
        poly = np.asarray(g["poly"], np.float64)
        R = np.random.default_rng(int(g.get("seed", 0)) + 9100 + len(g["id"]) * 31)
        bx0, bz0 = poly.min(axis=0) - 1.5
        bx1, bz1 = poly.max(axis=0) + 1.5
        placed = []

        def sdf_at(x, z):
            return float(geom.polygon_sdf(np.array([[x]]), np.array([[z]]), poly)[0, 0])
        for lname, spec in g["layers"].items():
            sp_d, inset_d, sc_d = LAYER_DEFAULTS[lname]
            spacing = float(spec.get("spacing", sp_d))
            ins = spec.get("inset", inset_d)
            scl = spec.get("scale", sc_d)
            kinds = spec["kinds"]
            names = list(kinds)
            w = np.array([kinds[k] for k in names], np.float64)
            w /= w.sum()

            def ok(x, z, ins=ins, lname=lname, spacing=spacing):
                d = -sdf_at(x, z)                     # depth inside the mass (m)
                if not (ins[0] <= d <= ins[1]):
                    return False
                if lname == "canopy" and np.hypot(x, z) < CROWN_R:
                    return False
                if ctx["path_dist"](x, z) < (0.9 if lname in ("ground", "sode") else 1.3):
                    return False
                if ctx["water_dist"](x, z) < 0.8 or ctx["slope_deg"](x, z) > 42 or ctx["pad_dist"](x, z) < 0.5:
                    return False
                for (cx, cz, cr) in keep_out:
                    if np.hypot(x - cx, z - cz) < cr:
                        return False
                # nothing tall right on top of a smaller plant already there
                for (px, pz, pr) in placed:
                    if np.hypot(x - px, z - pz) < min(pr, spacing) * 0.7:
                        return False
                return True
            pts = poisson(R, (bx0, bz0, bx1, bz1), spacing, ok)
            for q in pts:
                k = names[int(R.choice(len(names), p=w))]
                var = int(R.integers(0, 8))
                if k == "maple" and var % 4 == 3:
                    var -= 1
                out.append({"kind": k, "x": float(q[0]), "z": float(q[1]), "rot": float(R.uniform(0, 6.28)),
                            "scale": float(R.uniform(scl[0], scl[1])), "variant": var, "planted": g["id"]})
                placed.append((float(q[0]), float(q[1]), spacing))
        # hedges: a clipped evergreen line along a polyline (生垣)
    for hd in L.get("hedges", []):
        pts = np.asarray(hd["pts"], np.float64)
        step = float(hd.get("step", 0.85))
        P, s = geom.resample_polyline(pts, step)
        align = bool(hd.get("align", False))
        for i in range(len(P) - (1 if align else 0)):
            if align:
                # a segment of clipped hedge centred between two samples, its length along the line
                q = (P[i] + P[i + 1]) * 0.5
                d = P[i + 1] - P[i]
                rot = float(np.arctan2(-d[1], d[0]))
            else:
                q = P[i]
                rot = float(rng.uniform(0, 6.28))
            out.append({"kind": hd.get("kind", "shrub"), "x": float(q[0]), "z": float(q[1]), "rot": rot,
                        "scale": float(hd.get("scale", 0.9)), "variant": int(rng.integers(0, 8)), "planted": "hedge"})
    return out
