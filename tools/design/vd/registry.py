"""Load docs/design/village/registry.json and turn its shapes into geometry: polylines, polygons,
footprints, and the trees a planting scatters (the same scatter gives the drawn trees and their
collision circles, so the picture and the collision come from one source)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]
REGISTRY = REPO / "docs" / "design" / "village" / "registry.json"


def load(path: Path = REGISTRY) -> dict:
    with open(path, encoding="utf-8") as f:
        R = json.load(f)
    R["_index"] = {}
    for key in ("elements", "roads", "water", "plantings", "zones", "views", "sightlines"):
        for it in R.get(key, []):
            R["_index"][it["id"]] = it
    for key in ("pads", "carves", "cliffs", "bumps"):
        for it in R["terrain"].get(key, []):
            R["_index"][it["id"]] = it
    return R


# ---- polylines -------------------------------------------------------------------------------------
def resample(pts, step=0.5):
    """Resample a polyline (list of [x, y, ...]) every `step` metres; extra columns are interpolated."""
    P = np.asarray(pts, dtype=float)
    seg = np.linalg.norm(np.diff(P[:, :2], axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    n = max(2, int(math.ceil(s[-1] / step)) + 1)
    t = np.linspace(0.0, s[-1], n)
    out = np.stack([np.interp(t, s, P[:, c]) for c in range(P.shape[1])], axis=1)
    return out, t


def polyline_length(pts):
    P = np.asarray(pts, dtype=float)
    return float(np.sum(np.linalg.norm(np.diff(P[:, :2], axis=0), axis=1)))


def offset_polyline(P, d):
    """Offset a resampled polyline sideways by d (left of the direction of travel +)."""
    P = np.asarray(P, dtype=float)[:, :2]
    T = np.gradient(P, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
    N = np.stack([-T[:, 1], T[:, 0]], axis=1)
    return P + N * d


def poly_area(poly):
    P = np.asarray(poly, dtype=float)
    x, y = P[:, 0], P[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def poly_centroid(poly):
    P = np.asarray(poly, dtype=float)
    x, y = P[:, 0], P[:, 1]
    a = np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))
    if abs(a) < 1e-9:
        return P.mean(axis=0)
    cx = np.sum((x + np.roll(x, -1)) * (x * np.roll(y, -1) - np.roll(x, -1) * y)) / (3 * a)
    cy = np.sum((y + np.roll(y, -1)) * (x * np.roll(y, -1) - np.roll(x, -1) * y)) / (3 * a)
    return np.array([cx, cy])


def points_in_poly(px, py, poly):
    """Vectorised even-odd test. px, py: arrays of the same shape."""
    P = np.asarray(poly, dtype=float)
    inside = np.zeros(np.shape(px), dtype=bool)
    x0, y0 = P[-1]
    for x1, y1 in P:
        cond = ((y1 > py) != (y0 > py))
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (x0 - x1) * (py - y1) / (y0 - y1) + x1
        inside ^= cond & (px < xint)
        x0, y0 = x1, y1
    return inside


def dist_to_polyline(px, py, pts):
    """Distance from points to a polyline (vectorised over the points, loop over segments)."""
    P = np.asarray(pts, dtype=float)[:, :2]
    d = np.full(np.shape(px), np.inf)
    for (x0, y0), (x1, y1) in zip(P[:-1], P[1:]):
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        if L2 < 1e-12:
            dd = np.hypot(px - x0, py - y0)
        else:
            t = np.clip(((px - x0) * dx + (py - y0) * dy) / L2, 0.0, 1.0)
            dd = np.hypot(px - (x0 + t * dx), py - (y0 + t * dy))
        d = np.minimum(d, dd)
    if len(P) == 1:
        d = np.hypot(px - P[0, 0], py - P[0, 1])
    return d


def signed_side(px, py, pts):
    """For each point, which side of the nearest segment it is on (+1 left, -1 right of travel)."""
    P = np.asarray(pts, dtype=float)[:, :2]
    best = np.full(np.shape(px), np.inf)
    side = np.zeros(np.shape(px))
    for (x0, y0), (x1, y1) in zip(P[:-1], P[1:]):
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        t = np.clip(((px - x0) * dx + (py - y0) * dy) / max(L2, 1e-12), 0.0, 1.0)
        dd = np.hypot(px - (x0 + t * dx), py - (y0 + t * dy))
        cr = dx * (py - y0) - dy * (px - x0)
        m = dd < best
        best = np.where(m, dd, best)
        side = np.where(m, np.sign(cr), side)
    return side, best


# ---- footprints ------------------------------------------------------------------------------------
def footprint_shapes(e):
    """List of ('circle', x, y, r) / ('poly', pts) / ('line', pts, w) for an element's collision."""
    fp = e.get("footprint")
    out = []
    if fp:
        if "circle" in fp:
            x, y, r = fp["circle"]
            out.append(("circle", x, y, r))
        for c in fp.get("circles", []):
            out.append(("circle", c[0], c[1], c[2]))
        if "poly" in fp:
            out.append(("poly", fp["poly"]))
        if "line" in fp:
            out.append(("line", fp["line"]["pts"], fp["line"]["w"]))
        for ln in fp.get("lines", []):
            out.append(("line", ln["pts"], ln["w"]))
        return out
    # fall back on pos + size (a box, rotated by facing)
    if "size" in e and e.get("pos") and e["size"][0] and e["size"][1]:
        w, d = e["size"][0], e["size"][1]
        a = math.radians(e.get("facing", 180) - 180)
        c, s = math.cos(a), math.sin(a)
        x, y = e["pos"]
        pts = []
        for u, v in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)):
            pts.append([x + u * c - v * s, y + u * s + v * c])
        out.append(("poly", pts))
    return out


def rasterize_shapes(shapes, X, Y):
    m = np.zeros(X.shape, dtype=bool)
    for sh in shapes:
        if sh[0] == "circle":
            _, x, y, r = sh
            m |= np.hypot(X - x, Y - y) <= r
        elif sh[0] == "poly":
            m |= points_in_poly(X, Y, sh[1])
        elif sh[0] == "line":
            m |= dist_to_polyline(X, Y, sh[1]) <= sh[2] / 2.0
    return m


# ---- planting scatter ---------------------------------------------------------------------------------
def _poisson(poly, spacing, rng, tries=30):
    P = np.asarray(poly, dtype=float)
    x0, y0 = P.min(axis=0)
    x1, y1 = P.max(axis=0)
    cell = spacing / math.sqrt(2)
    gw, gh = int((x1 - x0) / cell) + 1, int((y1 - y0) / cell) + 1
    grid = -np.ones((gh, gw), dtype=int)
    pts = []
    active = []
    # seed
    for _ in range(200):
        p = np.array([rng.uniform(x0, x1), rng.uniform(y0, y1)])
        if points_in_poly(np.array([p[0]]), np.array([p[1]]), P)[0]:
            pts.append(p)
            active.append(0)
            grid[int((p[1] - y0) / cell), int((p[0] - x0) / cell)] = 0
            break
    while active:
        i = active[rng.integers(len(active))]
        found = False
        for _ in range(tries):
            a = rng.uniform(0, 2 * math.pi)
            r = rng.uniform(spacing, 2 * spacing)
            q = pts[i] + r * np.array([math.cos(a), math.sin(a)])
            if not (x0 <= q[0] <= x1 and y0 <= q[1] <= y1):
                continue
            gx, gy = int((q[0] - x0) / cell), int((q[1] - y0) / cell)
            ok = True
            for yy in range(max(0, gy - 2), min(gh, gy + 3)):
                for xx in range(max(0, gx - 2), min(gw, gx + 3)):
                    j = grid[yy, xx]
                    if j >= 0 and np.linalg.norm(pts[j] - q) < spacing:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                continue
            if not points_in_poly(np.array([q[0]]), np.array([q[1]]), P)[0]:
                continue
            pts.append(q)
            active.append(len(pts) - 1)
            grid[gy, gx] = len(pts) - 1
            found = True
            break
        if not found:
            active.remove(i)
    return np.array(pts) if pts else np.zeros((0, 2))


TRUNK_R = {"SUG": 0.4, "SII": 0.35, "KON": 0.25, "MOM": 0.2, "KAT": 0.35, "AKM": 0.3, "トチノキ": 0.35,
           "ヤマザクラ": 0.25, "エゴノキ": 0.15, "アラカシ": 0.25}
CROWN_R = {"SUG": 2.6, "SII": 4.0, "KON": 3.6, "MOM": 3.2, "KAT": 4.6, "AKM": 3.4, "トチノキ": 4.4,
           "ヤマザクラ": 3.6, "エゴノキ": 2.6, "アラカシ": 3.4}


def scatter_planting(pl, R, keep_out=None):
    """Trees of a planting: list of dicts {x, y, kind, h, crown_r, trunk_r}. Deterministic (seed)."""
    rng = np.random.default_rng(pl.get("seed", 1))
    can = pl["layers"].get("canopy")
    if not can:
        return []
    mix = can["mix"]
    kinds = list(mix.keys())
    probs = np.array([mix[k] for k in kinds], dtype=float)
    probs /= probs.sum()
    hlo, hhi = can.get("height", [10, 15])
    if pl.get("along"):
        road = R["_index"][pl["along"]]
        P, s = resample(road["pts"], 0.5)
        L = s[-1]
        a0, a1 = pl.get("along_range", [0, 1])
        off = road["w"] / 2.0 + can.get("offset", 3.0)
        pts = []
        step = can.get("spacing", 7.0)
        Lft = offset_polyline(P, off)
        Rgt = offset_polyline(P, -off)
        for side, phase in ((1, 0.0), (-1, 0.5)):
            O = Lft if side > 0 else Rgt
            t = a0 * L + phase * step
            while t < a1 * L:
                i = int(np.searchsorted(s, t))
                i = min(i, len(O) - 1)
                if pl.get("side") == "uphill":
                    # keep only the side that lies north of the road here (the uphill side on the south face)
                    other = Rgt[i] if side > 0 else Lft[i]
                    if O[i][1] < other[1] + 1.0:
                        t += step * rng.uniform(0.85, 1.2)
                        continue
                pts.append(O[i])
                t += step * rng.uniform(0.85, 1.2)
        pts = np.array(pts) if pts else np.zeros((0, 2))
    else:
        pts = _poisson(pl["poly"], can.get("spacing", 6.0), rng)
    trees = []
    for p in pts:
        k = kinds[rng.choice(len(kinds), p=probs)]
        h = float(rng.uniform(hlo, hhi))
        cr = min(CROWN_R.get(k, 3.0), 0.42 * h + 0.3) * float(rng.uniform(0.85, 1.15))
        trees.append({"x": float(p[0]), "y": float(p[1]), "kind": k, "h": h, "crown_r": cr,
                      "trunk_r": min(TRUNK_R.get(k, 0.3), 0.03 * h + 0.05)})
    if keep_out is not None and trees:
        X = np.array([t["x"] for t in trees])
        Y = np.array([t["y"] for t in trees])
        ok = ~keep_out(X, Y)
        trees = [t for t, o in zip(trees, ok) if o]
    return trees


def all_road_distance(R, X, Y, skip=()):
    """Distance from points to the nearest road edge (negative inside a road)."""
    d = np.full(np.shape(X), np.inf)
    for rd in R["roads"]:
        if rd["id"] in skip:
            continue
        dd = dist_to_polyline(X, Y, rd["pts"]) - rd["w"] / 2.0
        d = np.minimum(d, dd)
    return d


def p3_law_limit(R, ppm=None, share=None, pitch=45.0, fov=38.0, near_clear=1.2):
    """The P3 planting law (registry rules.p3_south_low) as a function, from the camera's geometry.

    The camera stands Dc = D cos(pitch) south of her and Hc = 0.9 + D sin(pitch) above her feet
    (D = K / PPM); the bottom edge of the picture meets her ground s0 metres south of her. The bottom
    plane of the frame rises southward as a (s - s0), a = Hc / (Dc - s0). An upright whose base is
    s metres south of her and b metres above her ground leans north by k t at height t (k = tan(pitch / 2)
    times the share), so it breaks into the picture as soon as b + t > a (s - k t - s0), i.e. when it is
    taller than (a (s - s0) - b) / (1 + a k). Nearer than s0 the ground itself is in the picture: only
    ground cover <= near_clear. A trunk that would cross that plane behind the camera passes over the
    camera's head and stays above the top of the picture (no limit). The frame's half width at the crossing
    is 320 px times the depth there over K: only things inside it (plus their crown) count.

    Returns limit(s, b, dx, r): the allowed height (m), or None when the thing cannot reach the picture.
    s: south distance of its north edge from her, b: its base above her ground, dx: its east-west offset
    from her, r: its crown radius."""
    from .p3 import Cam, screen_extent, VIEW_W
    ppm = ppm or R["camera"]["recommended"]["ppm"]
    share = R["camera"]["recommended"]["share"] if share is None else share
    cam = Cam(fov=fov, pitch=pitch, ppm=ppm, share=share)
    p = math.radians(pitch)
    Dc = cam.D * math.cos(p)
    Hc = 0.9 + cam.D * math.sin(p)
    s0 = float(screen_extent(cam)["south"])
    a = Hc / (Dc - s0)
    k = cam.k
    K = cam.K

    def limit(s, b, dx, r):
        if s < 0:
            return None                               # north of her: never in front of the camera
        if s <= s0:
            t = 0.0
            lim = near_clear
        else:
            t = (a * (s - s0) - b) / (1.0 + a * k)    # height on the trunk where it meets the bottom plane
            lim = max(near_clear, t)
            t = max(t, 0.0)
        sc = s - k * t                                # where that is, south of her
        if sc >= Dc:
            return None                               # over the camera's head
        zc = b + t                                    # and how high above her ground
        depth = (Dc - sc) * math.cos(p) - (zc - Hc) * math.sin(p)
        half = (VIEW_W / 2.0) * depth / K
        if abs(dx) - r > half + 0.5:
            return None                               # beside the picture
        return lim

    limit.info = dict(Dc=Dc, Hc=Hc, s0=s0, a=a, k=k, reach=Dc + k * Hc, slope=a / (1.0 + a * k))
    return limit


def p3_key_points(R):
    """Where she can stand that the law protects: every road (1 m samples), every pad (2 m grid) and the
    key views."""
    pts = []
    for rd in R["roads"]:
        P, _ = resample([p[:2] for p in rd["pts"]], 1.0)
        pts.append(P[:, :2])
    for pad in R["terrain"]["pads"]:
        poly = np.asarray(pad["poly"])
        x0, y0 = poly.min(axis=0)
        x1, y1 = poly.max(axis=0)
        gx, gy = np.meshgrid(np.arange(x0, x1, 2.0), np.arange(y0, y1, 2.0))
        m = points_in_poly(gx, gy, poly)
        pts.append(np.stack([gx[m], gy[m]], axis=1))
    for v in R["views"]:
        pts.append(np.array([v["her"]]))
    return np.concatenate([p for p in pts if len(p)], axis=0)


def p3_tree_limit(x, y, h, crown_r, g, Kp, hk, kd, limit, ry=None):
    """Lowest allowed height for a tree (or any upright) at (x, y) on ground g over all key points near it,
    and the key point that sets it (index), or (None, None). crown_r: its half width east-west; ry: its
    half depth north-south (default crown_r)."""
    ry = crown_r if ry is None else ry
    reach = limit.info["reach"] + 4.0
    idx = kd.query_ball_point([x, y + reach / 2], r=math.hypot(20.0, reach / 2) + 1.0)
    best, at = None, None
    for i in idx:
        if Kp[i, 1] - y < 0:
            continue                                  # the tree is north of this point
        s_ = Kp[i, 1] - y - ry                        # south distance of the crown's north edge
        lim = limit(max(s_, 0.0), g - hk[i], Kp[i, 0] - x, crown_r)
        if lim is None:
            continue
        if best is None or lim < best:
            best, at = lim, i
    return best, at


def p3_south_low(trees_by_planting, R, T, near_clear=1.2, ppm=None, share=None, pitch=45.0, fov=38.0):
    """Apply the P3 planting law (p3_law_limit) to the scattered trees: a tree that would break into the
    picture from any key point is lowered to fit, or removed when that leaves less than 1.6 m. Trees north
    of every key point are untouched. Returns the count of trees lowered or removed."""
    from scipy.spatial import cKDTree
    limit = p3_law_limit(R, ppm, share, pitch, fov, near_clear)
    Kp = p3_key_points(R)
    kd = cKDTree(Kp)
    hk = T.h(Kp[:, 0], Kp[:, 1])
    changed = 0
    for pid in list(trees_by_planting.keys()):
        keep = []
        for t in trees_by_planting[pid]:
            g = float(T.h(t["x"], t["y"]))
            lim, _ = p3_tree_limit(t["x"], t["y"], t["h"], t["crown_r"], g, Kp, hk, kd, limit)
            if lim is not None and t["h"] > lim:
                changed += 1
                if lim < 1.6:
                    continue
                t["h"] = lim
                t["crown_r"] = min(t["crown_r"], 0.42 * t["h"] + 0.3)
                t["trunk_r"] = min(t["trunk_r"], 0.03 * t["h"] + 0.05)
                t["low"] = True
            keep.append(t)
        trees_by_planting[pid] = keep
    return changed


def p3_check_elements(R, T, near_clear=1.2):
    """The same law for the hand-placed trees and the buildings (they are not lowered automatically):
    rows (id, name, height, allowed, key point x, y) for each that breaks it somewhere."""
    from scipy.spatial import cKDTree
    limit = p3_law_limit(R, near_clear=near_clear)
    Kp = p3_key_points(R)
    kd = cKDTree(Kp)
    hk = T.h(Kp[:, 0], Kp[:, 1])
    rows = []
    for e in R["elements"]:
        if "pos" not in e:
            continue
        cat = e["id"].split("-")[0]
        x, y = e["pos"][:2]
        if cat == "TR" and e.get("height"):
            h = float(e["height"])
            cr = e.get("crown")
            if isinstance(cr, dict):
                rx = ry = float(cr.get("r", 2.0))
            elif isinstance(cr, list):
                P = np.asarray(cr, dtype=float)
                rx = float(np.abs(P[:, 0] - x).max())
                ry = float(np.abs(P[:, 1] - y).max())
            else:
                rx = ry = float(e.get("trunk_d", 0.6)) / 2.0
            g = float(T.h(x, y))
        elif cat == "BL" and e.get("size"):
            sx, sy, sz = e["size"][:3]
            h = float(sz)
            rx, ry = sx / 2.0, sy / 2.0
            g = float(e["h"]) if e.get("h") is not None else float(T.h(x, y))
        else:
            continue
        if h <= near_clear:
            continue
        lim, at = p3_tree_limit(x, y, h, rx, g, Kp, hk, kd, limit, ry=ry)
        if lim is not None and h > lim + 0.05:
            rows.append((e["id"], e.get("name", ""), h, lim, float(Kp[at, 0]), float(Kp[at, 1])))
    return rows
