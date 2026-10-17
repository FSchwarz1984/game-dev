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
        for side, phase in ((1, 0.0), (-1, 0.5)):
            O = offset_polyline(P, side * off)
            t = a0 * L + phase * step
            while t < a1 * L:
                i = int(np.searchsorted(s, t))
                i = min(i, len(O) - 1)
                pts.append(O[i])
                t += step * rng.uniform(0.85, 1.2)
        pts = np.array(pts)
    else:
        pts = _poisson(pl["poly"], can.get("spacing", 6.0), rng)
    trees = []
    for p in pts:
        k = kinds[rng.choice(len(kinds), p=probs)]
        trees.append({"x": float(p[0]), "y": float(p[1]), "kind": k, "h": float(rng.uniform(hlo, hhi)),
                      "crown_r": CROWN_R.get(k, 3.0) * float(rng.uniform(0.85, 1.15)), "trunk_r": TRUNK_R.get(k, 0.3)})
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
