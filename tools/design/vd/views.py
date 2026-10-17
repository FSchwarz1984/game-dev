"""P3 key views: a z-buffered massing render in the game's exact projection (fov 38, pitch 45, the
recommended PPM and lean share; uprights lean back by k * height), with her card drawn texel-for-pixel
at the scheme's size, then an SVG sheet with labels, a plan inset and notes. These are composition
studies (masses, light, what is in and out of the frame), not art."""
from __future__ import annotations

import base64
import io
import math

import numpy as np
from PIL import Image

from . import plan as PL
from . import registry as reg
from . import svg as S
from .p3 import Cam, VIEW_W, VIEW_H, screen_extent
from .svg import Svg, Frame, f

SLUG = {"VW-01": "home", "VW-02": "gate", "VW-03": "camphor", "VW-04": "lookout", "VW-05": "tsuzura",
        "VW-06": "graves", "VW-07": "cutting"}
SS = 2                          # supersample of the native frame for the drawing
LIGHT = np.array([-0.45, -0.35, 0.82])
LIGHT = LIGHT / np.linalg.norm(LIGHT)

COL = {"grass": (181, 185, 143), "moss": (150, 172, 116), "forest": (136, 146, 104), "path_so": (214, 200, 164),
       "path_gyo": (205, 196, 176), "path_shin": (217, 212, 199), "water": (128, 176, 196), "rock": (164, 158, 147),
       "plot": (190, 170, 120), "susuki": (204, 196, 142), "sasa": (104, 120, 76), "yard": (206, 188, 150),
       "trunk": (109, 86, 66), "broad": (138, 161, 106), "cedar": (88, 116, 86), "pine": (106, 134, 96),
       "maple": (152, 176, 108), "camphor": (104, 136, 82), "thatch": (190, 166, 112), "wall": (220, 208, 182),
       "wood": (138, 111, 85), "stone": (190, 183, 168), "fence": (122, 95, 72), "rope": (236, 228, 204),
       "vermilion": (180, 71, 46), "shrine_roof": (120, 112, 100), "sar": (190, 120, 128), "fog": (235, 235, 230),
       "kaki": (150, 166, 112), "kat": (150, 172, 120)}
KIND_COL = {"SUG": "cedar", "AKM": "pine", "MOM": "maple", "KAT": "kat", "KON": "broad", "SII": "broad",
            "トチノキ": "broad", "ヤマザクラ": "broad", "エゴノキ": "broad", "アラカシ": "broad", "SAR": "sar", "KAK": "kaki"}


class Mesh:
    def __init__(self):
        self.tris = []          # (3x3 array, rgb or 3 vertex colours, obj id, lean base or None)
        self.fog = []           # translucent: (3x3 array, rgb, alpha)

    def add(self, P, rgb, oid, base=None):
        self.tris.append((np.asarray(P, dtype=float), rgb, oid, base))

    def quad(self, a, b, c, d, rgb, oid, base=None):
        self.add([a, b, c], rgb, oid, base)
        self.add([a, c, d], rgb, oid, base)


def cylinder(m, x, y, z0, z1, r, rgb, oid, n=8, base=None, top=True):
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        p0 = (x + r * math.cos(a0), y + r * math.sin(a0))
        p1 = (x + r * math.cos(a1), y + r * math.sin(a1))
        m.quad((p0[0], p0[1], z0), (p1[0], p1[1], z0), (p1[0], p1[1], z1), (p0[0], p0[1], z1), rgb, oid, base)
        if top:
            m.add([(x, y, z1), (p0[0], p0[1], z1), (p1[0], p1[1], z1)], rgb, oid, base)


def cone(m, x, y, z0, z1, r, rgb, oid, n=10, base=None):
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        p0 = (x + r * math.cos(a0), y + r * math.sin(a0), z0)
        p1 = (x + r * math.cos(a1), y + r * math.sin(a1), z0)
        m.add([p0, p1, (x, y, z1)], rgb, oid, base)


def ellipsoid(m, x, y, zc, rx, ry, rz, rgb, oid, n=10, k_=6, base=None):
    for i in range(k_):
        t0, t1 = math.pi * i / k_, math.pi * (i + 1) / k_
        for j in range(n):
            a0, a1 = 2 * math.pi * j / n, 2 * math.pi * (j + 1) / n
            def P(t, a):
                return (x + rx * math.sin(t) * math.cos(a), y + ry * math.sin(t) * math.sin(a), zc + rz * math.cos(t))
            m.quad(P(t0, a0), P(t1, a0), P(t1, a1), P(t0, a1), rgb, oid, base)


def box(m, cx, cy, z0, w, d, h, rgb, oid, rot=0.0, base=None, top_rgb=None):
    c, s = math.cos(rot), math.sin(rot)
    def T(u, v):
        return (cx + u * c - v * s, cy + u * s + v * c)
    pts = [T(-w / 2, -d / 2), T(w / 2, -d / 2), T(w / 2, d / 2), T(-w / 2, d / 2)]
    z1 = z0 + h
    for i in range(4):
        a, b = pts[i], pts[(i + 1) % 4]
        m.quad((a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1), rgb, oid, base)
    m.quad((pts[0][0], pts[0][1], z1), (pts[1][0], pts[1][1], z1), (pts[2][0], pts[2][1], z1), (pts[3][0], pts[3][1], z1),
           top_rgb or rgb, oid, base)


def prism(m, poly, z0, z1, rgb, oid, base=None, top_rgb=None):
    P = np.asarray(poly, dtype=float)
    n = len(P)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        m.quad((a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1), rgb, oid, base)
    c = P.mean(axis=0)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        m.add([(c[0], c[1], z1), (a[0], a[1], z1), (b[0], b[1], z1)], top_rgb or rgb, oid, base)


def rock_mass(m, poly, z0, h, rgb, oid, base=None):
    """A rock: the footprint, sides sloping in, a rounded top."""
    P = np.asarray(poly, dtype=float)
    c = P.mean(axis=0)
    mid = c + (P - c) * 0.82
    top = c + (P - c) * 0.45
    n = len(P)
    for i in range(n):
        j = (i + 1) % n
        m.quad((P[i][0], P[i][1], z0 - 0.3), (P[j][0], P[j][1], z0 - 0.3), (mid[j][0], mid[j][1], z0 + h * 0.75),
               (mid[i][0], mid[i][1], z0 + h * 0.75), rgb, oid, base)
        m.quad((mid[i][0], mid[i][1], z0 + h * 0.75), (mid[j][0], mid[j][1], z0 + h * 0.75), (top[j][0], top[j][1], z0 + h),
               (top[i][0], top[i][1], z0 + h), rgb, oid, base)
        m.add([(c[0], c[1], z0 + h * 1.02), (top[i][0], top[i][1], z0 + h), (top[j][0], top[j][1], z0 + h)], rgb, oid, base)


def tube(m, pts, radii, rgb, oid, n=6, base=None):
    P = np.asarray(pts, dtype=float)
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        ax = b - a
        L = np.linalg.norm(ax)
        if L < 1e-6:
            continue
        ax /= L
        up = np.array([0, 0, 1.0]) if abs(ax[2]) < 0.9 else np.array([1.0, 0, 0])
        u = np.cross(ax, up)
        u /= np.linalg.norm(u)
        v = np.cross(ax, u)
        ra, rb = radii[i], radii[i + 1]
        for k in range(n):
            t0, t1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            d0 = u * math.cos(t0) + v * math.sin(t0)
            d1 = u * math.cos(t1) + v * math.sin(t1)
            m.quad(a + d0 * ra, a + d1 * ra, b + d1 * rb, b + d0 * rb, rgb, oid, base)


def hip_roof(m, cx, cy, w, d, z_eave, z_ridge, rgb, oid, base=None):
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2
    r1 = (x0 + d / 2, cy, z_ridge)
    r2 = (x1 - d / 2, cy, z_ridge)
    a, b, c, e = (x0, y0, z_eave), (x1, y0, z_eave), (x1, y1, z_eave), (x0, y1, z_eave)
    m.quad(a, b, r2, r1, rgb, oid, base)          # south slope
    m.quad(c, e, r1, r2, rgb, oid, base)          # north slope
    m.add([e, a, r1], rgb, oid, base)             # west hip
    m.add([b, c, r2], rgb, oid, base)             # east hip


def gable_roof(m, cx, cy, w, d, z_eave, z_ridge, rgb, oid, base=None):
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2
    m.quad((x0, y0, z_eave), (x1, y0, z_eave), (cx, y0, z_ridge), (cx, y0, z_ridge), rgb, oid, base)
    m.quad((x0, y0, z_eave), (cx, y0, z_ridge), (cx, y1, z_ridge), (x0, y1, z_eave), rgb, oid, base)
    m.quad((x1, y0, z_eave), (x1, y1, z_eave), (cx, y1, z_ridge), (cx, y0, z_ridge), rgb, oid, base)


# ---- scene ---------------------------------------------------------------------------------------------
def surface_map(R, T, x0, y0, x1, y1):
    """Ground colour per terrain cell in the window."""
    j0, j1 = int((x0 - T.x0) / T.cell), int((x1 - T.x0) / T.cell) + 1
    i0, i1 = int((y0 - T.y0) / T.cell), int((y1 - T.y0) / T.cell) + 1
    X, Y = T.X[i0:i1, j0:j1], T.Y[i0:i1, j0:j1]
    C = np.zeros(X.shape + (3,), dtype=float)
    C[:] = COL["grass"]
    def paint(mask, key):
        C[mask] = COL[key]
    for pl in R["plantings"]:
        if not pl.get("poly"):
            continue
        m = reg.points_in_poly(X, Y, pl["poly"])
        key = {"KOK": "moss", "SUS": "susuki", "SSA": "sasa", "SHI": "grass"}.get(pl["kind"], "forest")
        paint(m, key)
    for pad in R["terrain"]["pads"]:
        if pad["id"] == "TE-PAD-01":
            paint(reg.points_in_poly(X, Y, pad["poly"]), "yard")
    for e in R["elements"]:
        if e.get("kind") == "HAT" and e.get("poly"):
            paint(reg.points_in_poly(X, Y, e["poly"]), "plot")
    for pl in R["plantings"]:
        if pl.get("kind") == "KOK":
            paint(reg.points_in_poly(X, Y, pl["poly"]), "moss")
    for rd in R["roads"]:
        poly, P, Wd = PL.road_polygon(rd)
        key = {"真": "path_shin", "行": "path_gyo", "草": "path_so"}[rd["grade"]]
        if rd["kind"] == "TOB":
            continue
        paint(reg.points_in_poly(X, Y, poly), key)
    for w in R["water"]:
        if w.get("pts") and len(w["pts"][0]) >= 4:
            P, _ = reg.resample(w["pts"], 0.25)
            d = reg.dist_to_polyline(X, Y, P[:, :2])
            # width per nearest point (approx: max)
            paint(d <= P[:, 3].max() / 2 * 0.9, "water")
    steep = T.slope[i0:i1, j0:j1] > 40
    C[steep] = C[steep] * 0.35 + np.array(COL["rock"]) * 0.65
    return X, Y, T.H[i0:i1, j0:j1], C


def build_scene(R, T, trees, cam, margin=6.0):
    m = Mesh()
    fp = np.array(PL.frustum_ground(T, cam, step=8))
    if len(fp) < 3:
        fp = np.array([[cam.her[0] - 20, cam.her[1] - 8], [cam.her[0] + 20, cam.her[1] + 25]])
    x0, y0 = fp.min(axis=0) - margin
    x1, y1 = fp.max(axis=0) + margin
    y1 = max(y1, cam.her[1] + 22)
    X, Y, H, C = surface_map(R, T, x0, y0, x1, y1)
    # terrain quads (1 id)
    for i in range(X.shape[0] - 1):
        for j in range(X.shape[1] - 1):
            a = (X[i, j], Y[i, j], H[i, j])
            b = (X[i, j + 1], Y[i, j + 1], H[i, j + 1])
            c = (X[i + 1, j + 1], Y[i + 1, j + 1], H[i + 1, j + 1])
            d = (X[i + 1, j], Y[i + 1, j], H[i + 1, j])
            ca, cb, cc, cd = C[i, j], C[i, j + 1], C[i + 1, j + 1], C[i + 1, j]
            m.add([a, b, c], np.array([ca, cb, cc]), 0, None)
            m.add([a, c, d], np.array([ca, cc, cd]), 0, None)
    win = (x0 - 8, y0 - 8, x1 + 8, y1 + 30)

    def inwin(x, y, pad=0.0):
        return win[0] - pad <= x <= win[2] + pad and win[1] - pad <= y <= win[3] + pad

    oid = [10]
    ids = {}

    def nid(tag):
        oid[0] += 1
        ids[oid[0]] = tag
        return oid[0]

    # planting trees
    for pid, ts in trees.items():
        for t in ts:
            if not inwin(t["x"], t["y"], 6):
                continue
            g = float(T.h(t["x"], t["y"]))
            k = nid(pid)
            col = COL[KIND_COL.get(t["kind"], "broad")]
            h = t["h"]
            cylinder(m, t["x"], t["y"], g - 0.2, g + h * 0.55, t["trunk_r"], COL["trunk"], k, n=6, base=g, top=False)
            if t["kind"] in ("SUG",):
                cone(m, t["x"], t["y"], g + h * 0.3, g + h, t["crown_r"], col, k, n=10, base=g)
            else:
                ellipsoid(m, t["x"], t["y"], g + h * 0.62, t["crown_r"], t["crown_r"], h * 0.33, col, k, n=9, k_=5, base=g)
    # elements
    for e in R["elements"]:
        pos = e.get("pos")
        if pos and not inwin(pos[0], pos[1], 12) and not e["id"].startswith("TR-CAM"):
            continue
        cat, kind = e["cat"], e["kind"]
        g = float(T.h(pos[0], pos[1])) if pos else 0.0
        if e["id"] == "TR-CAM-01":
            k = nid(e["id"])
            g0 = float(T.h(0, 0))
            cylinder(m, 0, 0, g0 - 0.5, g0 + 12.5, 3.6, COL["trunk"], k, n=16, base=g0, top=False)
            for ang in (20, 75, 130, 200, 250, 300):
                a = math.radians(ang)
                bx, by = 4.6 * math.sin(a), 4.6 * math.cos(a)
                cone(m, bx * 0.62, by * 0.62, g0 - 0.3, g0 + 1.5, 1.7, COL["trunk"], k, n=8, base=g0)
            kc = nid("TR-CAM-01.crown")
            ellipsoid(m, -2.0, -4.0, g0 + 20.0, 19.0, 19.0, 9.0, COL["camphor"], kc, n=16, k_=8, base=g0)
            # the rope
            kr = nid("SG-SHM-01")
            cylinder(m, 0, 0, g0 + 1.7, g0 + 1.95, 3.72, COL["rope"], kr, n=24, base=g0, top=False)
            continue
        if kind == "EDA" and e.get("pts") and e["id"] in ("TR-CAM-01G", "TR-CAM-01S"):
            k = nid(e["id"])
            g0 = float(T.h(0, 0))
            tube(m, e["pts"], [d / 2 for d in e["diam"]], COL["trunk"], k, n=7, base=g0)
            if e["id"].endswith("G"):
                top = [(p[0], p[1], p[2] + d / 2 + 0.02) for p, d in zip(e["pts"], e["diam"])]
                tube(m, top, [0.42] * len(top), (150, 190, 96), nid("G-moss"), n=5, base=g0)
            continue
        if cat == "TR":
            k = nid(e["id"])
            h = e.get("height", 6.0)
            if e.get("pts") and kind == "SUG":
                P = e["pts"]
                tube(m, [(P[0][0], P[0][1], g + 0.6), (P[1][0], P[1][1], g + 0.6)], [0.6, 0.45], COL["trunk"], k, n=6, base=g)
                continue
            r = e.get("crown", {}).get("r", 3.0) if isinstance(e.get("crown"), dict) else 3.0
            tr = e.get("trunk_d", 0.4) / 2
            col = COL[KIND_COL.get(kind, "broad")]
            cylinder(m, pos[0], pos[1], g - 0.2, g + h * 0.6, tr, COL["trunk"], k, n=7, base=g, top=False)
            if kind == "SUG":
                cone(m, pos[0], pos[1], g + h * 0.35, g + h, r, col, k, n=10, base=g)
            else:
                ellipsoid(m, pos[0], pos[1], g + h * 0.66, r, r, h * 0.3, col, k, n=10, k_=5, base=g)
                if kind == "SAR":
                    for a in range(0, 360, 45):
                        ellipsoid(m, pos[0] + r * 0.6 * math.cos(math.radians(a)), pos[1] + r * 0.6 * math.sin(math.radians(a)),
                                  g + h * 0.8, 0.6, 0.6, 0.45, (196, 82, 104), k, n=6, k_=3, base=g)
            continue
        if cat == "SH":
            k = nid(e["id"])
            ellipsoid(m, pos[0], pos[1], g + e["size"][2] * 0.5, e["size"][0] / 2, e["size"][1] / 2, e["size"][2] / 2,
                      COL["broad"], k, n=8, k_=4, base=g)
            continue
        if cat == "BL" and kind == "MIN":
            k = nid(e["id"])
            x, y = pos
            gz = e.get("h", g)
            box(m, x, y, gz, e["size"][0], e["size"][1], 2.35, COL["wall"], k, base=gz)
            eng = e["engawa"]
            prism(m, eng["poly"], gz, eng["h"], COL["wood"], k, base=gz)
            hip_roof(m, x, y, e["roof"][0], e["roof"][1], gz + e["eave"], gz + 6.3, COL["thatch"], nid("roof"), base=gz)
            d = e["door"]
            box(m, d["pos"][0], d["pos"][1] - 0.02, gz + d["sill"], d["w"], 0.05, d["h"], (60, 50, 42), nid("door"), base=gz)
            continue
        if cat == "BL" and kind == "HOK":
            k = nid(e["id"])
            x, y = pos
            gz = e.get("h", g)
            box(m, x, y, gz, e["size"][0] * 0.8, e["size"][1] * 0.75, 1.9, (164, 138, 106), k, base=gz)
            gable_roof(m, x, y, e["size"][0] * 1.15, e["size"][1], gz + 1.9, gz + e["size"][2], COL["shrine_roof"], nid("roof"),
                       base=gz)
            box(m, x, y - e["size"][1] * 0.38, gz + 0.6, 0.6, 0.05, 0.9, COL["vermilion"], nid("ver"), base=gz)
            continue
        if kind == "GAK" and e["id"] == "ST-GAK-02":
            k = nid(e["id"])
            box(m, pos[0], pos[1], float(T.h(pos[0], pos[1] - 3)) - 0.2, e["size"][0], e["size"][1], 0.75, COL["stone"], k,
                base=None)
            continue
        if kind == "GAK" and e.get("pts"):
            k = nid(e["id"])
            P, _ = reg.resample(e["pts"], 0.6)
            for a, b in zip(P[:-1], P[1:]):
                ga = float(T.h(a[0], a[1] - 0.8))
                top = float(T.h(a[0], a[1] + 0.8))
                lo, hi = min(ga, top), max(ga, top)
                prism(m, [(a[0], a[1] - 0.3), (b[0], b[1] - 0.3), (b[0], b[1] + 0.3), (a[0], a[1] + 0.3)], lo - 0.2, hi + 0.05,
                      COL["stone"], k, base=None)
            continue
        if cat == "RK":
            k = nid(e["id"])
            shapes = reg.footprint_shapes(e)
            hgt = (e.get("size") or [1, 1, 1.0])[2] or 1.0
            for sh in shapes:
                if sh[0] == "poly":
                    rock_mass(m, sh[1], g, hgt, COL["rock"], k, base=g)
                elif sh[0] == "circle":
                    _, cx, cy, r = sh
                    poly = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 9)[:-1]]
                    rock_mass(m, poly, float(T.h(cx, cy)), hgt, COL["rock"], k, base=float(T.h(cx, cy)))
                elif sh[0] == "line":
                    P, _ = reg.resample(sh[1], 1.2)
                    for p in P:
                        r = sh[2] / 2
                        poly = [(p[0] + r * math.cos(a), p[1] + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 8)[:-1]]
                        rock_mass(m, poly, float(T.h(p[0], p[1])), hgt, COL["rock"], k, base=float(T.h(p[0], p[1])))
            if e["id"] == "RK-IWA-01":
                kr = nid("SG-SHM-02")
                P = np.array(e["footprint"]["poly"])
                c = P.mean(axis=0)
                ring = c + (P - c) * 0.86
                for a, b in zip(ring, np.roll(ring, -1, axis=0)):
                    m.quad((a[0], a[1], g + 0.75), (b[0], b[1], g + 0.75), (b[0], b[1], g + 0.95), (a[0], a[1], g + 0.95),
                           COL["rope"], kr, g)
            continue
        if kind == "MZG":
            k = nid(e["id"])
            P, _ = reg.resample(e["pts"], 0.4)
            for a, b in zip(P[:-1], P[1:]):
                ga = float(T.h(a[0], a[1]))
                prism(m, [(a[0] - 0.06, a[1] - 0.06), (b[0] + 0.06, b[1] - 0.06), (b[0] + 0.06, b[1] + 0.06), (a[0] - 0.06, a[1] + 0.06)],
                      ga, ga + 1.1, COL["fence"], k, base=ga)
            continue
        if kind == "MCK" and e["id"] == "SG-MCK-01":
            k = nid(e["id"])
            g0 = float(T.h(24.4, -42.5))
            tube(m, [(22.6, -42.6, g0 + 4.1), (24.4, -42.5, g0 + 3.6), (26.2, -42.4, g0 + 4.0)], [0.12, 0.12, 0.12], (201, 178, 122), k,
                 n=5, base=g0)
            continue
        if kind == "WAR":
            k = nid(e["id"])
            g0 = float(T.h(*pos))
            box(m, pos[0], pos[1], g0 + 1.9, 0.75, 0.15, 1.6, (201, 178, 122), k, base=g0)
            continue
        if cat == "FX" and kind == "FOG":
            P = np.array(e["poly"])
            gz = float(np.mean([T.h(p[0], p[1]) for p in P]))
            hh = e.get("h", 3.4)
            alpha = 0.55 * e.get("density", 1.0) + 0.25
            tmp = Mesh()
            prism(tmp, P, gz - 0.5, gz + hh, COL["fog"], 0, base=None)
            for Q, rgb, _, _ in tmp.tris:
                m.fog.append((Q, rgb, alpha))
            continue
        if kind in ("HAK",):
            k = nid(e["id"])
            box(m, pos[0], pos[1], g, e["size"][0], e["size"][1], e["size"][2], COL["stone"], k, base=g)
            continue
        if kind in ("TOU", "AKA"):
            k = nid(e["id"])
            col = COL["vermilion"] if kind == "AKA" else (150, 130, 90)
            cylinder(m, pos[0], pos[1], g, g + e["size"][2], 0.06 if kind == "TOU" else 0.12, col, k, n=5, base=g)
            if kind == "AKA":
                box(m, pos[0], pos[1], g + e["size"][2] - 0.55, 0.36, 0.36, 0.45, (236, 224, 196), k, base=g)
            continue
        if kind in ("TOR", "CHO", "JIZ", "DOS", "SAI", "CHZ", "MIZ", "KUT"):
            k = nid(e["id"])
            w = e["size"][0]
            d_ = e["size"][1]
            h = e["size"][2]
            if kind == "TOR":
                box(m, pos[0], pos[1], g, 0.7, 0.7, 0.35, COL["stone"], k, base=g)
                cylinder(m, pos[0], pos[1], g + 0.35, g + 0.9, 0.12, COL["stone"], k, n=6, base=g)
                box(m, pos[0], pos[1], g + 0.9, 0.45, 0.45, 0.32, COL["stone"], k, base=g)
                cone(m, pos[0], pos[1], g + 1.22, g + 1.52, 0.5, COL["stone"], k, n=6, base=g)
            elif kind == "JIZ":
                box(m, pos[0], pos[1], g, w, d_, h * 0.7, COL["stone"], k, base=g)
                box(m, pos[0], pos[1] - 0.05, g + h * 0.45, w * 0.9, d_ * 0.6, h * 0.18, COL["vermilion"], k, base=g)
                ellipsoid(m, pos[0], pos[1], g + h * 0.82, w * 0.35, w * 0.35, h * 0.18, COL["stone"], k, n=6, k_=3, base=g)
            else:
                box(m, pos[0], pos[1], g, w, d_, h, COL["stone"], k, base=g)
            continue
        if cat == "PR":
            k = nid(e["id"])
            sz = e.get("size") or [0.5, 0.5, 0.5]
            if kind == "MON":                       # drying pole: two posts, a bamboo, cloths
                for dx in (-1.8, 1.8):
                    cylinder(m, pos[0] + dx, pos[1], g, g + 2.0, 0.05, (150, 130, 96), k, n=5, base=g)
                tube(m, [(pos[0] - 1.9, pos[1], g + 1.9), (pos[0] + 1.9, pos[1], g + 1.9)], [0.04, 0.04], (170, 160, 110), k, n=4, base=g)
                for dx, c in ((-1.0, (226, 220, 206)), (-0.2, (120, 130, 160)), (0.7, (230, 226, 214))):
                    box(m, pos[0] + dx, pos[1], g + 1.05, 0.6, 0.03, 0.82, c, k, base=g)
            elif kind == "ONO":                     # chopping stump
                cylinder(m, pos[0], pos[1], g, g + 0.5, 0.38, (150, 118, 84), k, n=8, base=g)
            elif kind == "SHO":                     # backpack frame: two uprights and bars
                for dx in (-0.2, 0.2):
                    box(m, pos[0] + dx, pos[1], g, 0.05, 0.05, 1.05, (120, 92, 64), k, base=g)
                for hz in (0.35, 0.75, 1.0):
                    box(m, pos[0], pos[1], g + hz, 0.46, 0.05, 0.04, (120, 92, 64), k, base=g)
            elif kind == "KAG":
                cylinder(m, pos[0], pos[1], g, g + sz[2], 0.26, (196, 176, 120), k, n=8, base=g)
            elif kind == "GOB":
                box(m, pos[0], pos[1], g, 0.55, 0.55, 0.3, (150, 120, 84), k, base=g, top_rgb=(120, 140, 90))
            elif kind == "KKS":
                cylinder(m, pos[0], pos[1], g, g + 1.6, 0.04, (150, 130, 96), k, n=4, base=g)
                box(m, pos[0], pos[1], g + 1.2, 1.1, 0.05, 0.05, (150, 130, 96), k, base=g)
                ellipsoid(m, pos[0], pos[1], g + 1.6, 0.3, 0.3, 0.1, (200, 180, 120), k, n=6, k_=3, base=g)
            elif kind in ("CHA", "MUS", "NEG"):
                pass
            elif kind == "MAK":
                box(m, pos[0], pos[1], g, sz[0], sz[1], sz[2], (156, 120, 80), k, base=g)
            elif e.get("collision") == "solid":
                box(m, pos[0], pos[1], g, sz[0] or 0.5, sz[1] or 0.5, sz[2] or 0.5, (184, 166, 128), k, base=g)
            continue
        if cat == "AN" and e.get("size") and kind in ("NIW", "NEK"):
            k = nid(e["id"])
            gz = e.get("h", g)
            w, d_, h = e["size"]
            if kind == "NIW":                       # a brown hen with a red comb
                ellipsoid(m, pos[0], pos[1], gz + 0.2, 0.2, 0.12, 0.14, (156, 104, 62), k, n=7, k_=4, base=gz)
                ellipsoid(m, pos[0] + 0.16, pos[1], gz + 0.36, 0.07, 0.06, 0.07, (156, 104, 62), k, n=6, k_=3, base=gz)
                box(m, pos[0] + 0.17, pos[1], gz + 0.42, 0.06, 0.02, 0.05, (200, 40, 36), k, base=gz)
            else:                                   # a sitting cat
                ellipsoid(m, pos[0], pos[1], gz + 0.13, 0.15, 0.12, 0.13, (92, 84, 76), k, n=7, k_=4, base=gz)
                ellipsoid(m, pos[0], pos[1] - 0.05, gz + 0.29, 0.08, 0.08, 0.07, (92, 84, 76), k, n=6, k_=3, base=gz)
            continue
    # water surfaces
    for w in R["water"]:
        if w.get("pts") and len(w["pts"][0]) >= 4:
            P, _ = reg.resample(w["pts"], 0.5)
            k = nid(w["id"])
            Lf = reg.offset_polyline(P, 1.0) - P[:, :2]
            for a, b, la, lb in zip(P[:-1], P[1:], Lf[:-1], Lf[1:]):
                if not inwin(a[0], a[1], 4):
                    continue
                ha, hb = a[2] - 0.12, b[2] - 0.12
                m.quad((a[0] + la[0] * a[3] / 2, a[1] + la[1] * a[3] / 2, ha), (a[0] - la[0] * a[3] / 2, a[1] - la[1] * a[3] / 2, ha),
                       (b[0] - lb[0] * b[3] / 2, b[1] - lb[1] * b[3] / 2, hb), (b[0] + lb[0] * b[3] / 2, b[1] + lb[1] * b[3] / 2, hb),
                       COL["water"], k, None)
    return m, ids, (x0, y0, x1, y1)


def render(m, cam, ss=SS):
    Wd, Ht = VIEW_W * ss, VIEW_H * ss
    zbuf = np.full((Ht, Wd), np.inf)
    img = np.zeros((Ht, Wd, 3), dtype=float)
    img[:] = (226, 222, 210)
    ibuf = np.zeros((Ht, Wd), dtype=np.int32)
    k = cam.k
    for P, rgb, oid, base in m.tris:
        Q = P.copy()
        if base is not None:
            Q[:, 1] = Q[:, 1] + k * (Q[:, 2] - base)
        sx, sy, d = cam.project(Q)
        if np.any(d <= 0.5):
            continue
        px = (VIEW_W / 2.0 + sx) * ss
        py = (VIEW_H / 2.0 - sy) * ss
        xmin, xmax = int(math.floor(px.min())), int(math.ceil(px.max()))
        ymin, ymax = int(math.floor(py.min())), int(math.ceil(py.max()))
        if xmax < 0 or ymax < 0 or xmin >= Wd or ymin >= Ht:
            continue
        xmin, ymin = max(xmin, 0), max(ymin, 0)
        xmax, ymax = min(xmax, Wd - 1), min(ymax, Ht - 1)
        if xmax < xmin or ymax < ymin:
            continue
        # shading from the world normal
        n = np.cross(P[1] - P[0], P[2] - P[0])
        nn = np.linalg.norm(n)
        if nn < 1e-12:
            continue
        n /= nn
        if n[2] < 0:
            n = -n
        lam = 0.58 + 0.42 * max(0.0, float(n @ LIGHT))
        vcol = np.asarray(rgb, dtype=float)
        xs = np.arange(xmin, xmax + 1) + 0.5
        ys = np.arange(ymin, ymax + 1) + 0.5
        GX, GY = np.meshgrid(xs, ys)
        x0_, y0_, x1_, y1_, x2_, y2_ = px[0], py[0], px[1], py[1], px[2], py[2]
        den = (y1_ - y2_) * (x0_ - x2_) + (x2_ - x1_) * (y0_ - y2_)
        if abs(den) < 1e-9:
            continue
        w0 = ((y1_ - y2_) * (GX - x2_) + (x2_ - x1_) * (GY - y2_)) / den
        w1 = ((y2_ - y0_) * (GX - x2_) + (x0_ - x2_) * (GY - y2_)) / den
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue
        z = w0 * d[0] + w1 * d[1] + w2 * d[2]
        sub = zbuf[ymin:ymax + 1, xmin:xmax + 1]
        upd = inside & (z < sub)
        sub[upd] = z[upd]
        if vcol.ndim == 2:
            col = (w0[upd, None] * vcol[0] + w1[upd, None] * vcol[1] + w2[upd, None] * vcol[2]) * lam
        else:
            col = vcol * lam
        img[ymin:ymax + 1, xmin:xmax + 1][upd] = col
        ibuf[ymin:ymax + 1, xmin:xmax + 1][upd] = oid
    # translucent fog in front of what is drawn
    for P, rgb, alpha in m.fog:
        sx, sy, d = cam.project(P)
        if np.any(d <= 0.5):
            continue
        px = (VIEW_W / 2.0 + sx) * ss
        py = (VIEW_H / 2.0 - sy) * ss
        xmin, xmax = max(int(math.floor(px.min())), 0), min(int(math.ceil(px.max())), Wd - 1)
        ymin, ymax = max(int(math.floor(py.min())), 0), min(int(math.ceil(py.max())), Ht - 1)
        if xmax < xmin or ymax < ymin:
            continue
        GX, GY = np.meshgrid(np.arange(xmin, xmax + 1) + 0.5, np.arange(ymin, ymax + 1) + 0.5)
        x0_, y0_, x1_, y1_, x2_, y2_ = px[0], py[0], px[1], py[1], px[2], py[2]
        den = (y1_ - y2_) * (x0_ - x2_) + (x2_ - x1_) * (y0_ - y2_)
        if abs(den) < 1e-9:
            continue
        w0 = ((y1_ - y2_) * (GX - x2_) + (x2_ - x1_) * (GY - y2_)) / den
        w1 = ((y2_ - y0_) * (GX - x2_) + (x0_ - x2_) * (GY - y2_)) / den
        w2 = 1 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        z = w0 * d[0] + w1 * d[1] + w2 * d[2]
        sub = zbuf[ymin:ymax + 1, xmin:xmax + 1]
        hit = inside & (z < sub)
        blk = img[ymin:ymax + 1, xmin:xmax + 1]
        blk[hit] = blk[hit] * (1 - alpha * 0.5) + np.array(rgb) * alpha * 0.5
    # outlines where the object changes and depth jumps
    edge = np.zeros(ibuf.shape, dtype=bool)
    for dy, dx in ((0, 1), (1, 0)):
        a = ibuf[: Ht - dy, : Wd - dx]
        b = ibuf[dy:, dx:]
        za = zbuf[: Ht - dy, : Wd - dx]
        zb = zbuf[dy:, dx:]
        e = (a != b) & ~((a == 0) & (b == 0))
        edge[: Ht - dy, : Wd - dx] |= e
    img[edge] *= 0.55
    # gentle aerial perspective
    zf = np.where(np.isfinite(zbuf), zbuf, zbuf[np.isfinite(zbuf)].max() if np.isfinite(zbuf).any() else 1)
    t = np.clip((zf - zf.min()) / max(np.ptp(zf), 1e-6), 0, 1)[..., None]
    img = img * (1 - 0.12 * t) + np.array([226, 224, 214]) * 0.12 * t
    return np.clip(img, 0, 255).astype(np.uint8), zbuf, ibuf


def her_card(img, cam, her_px, ss=SS):
    """Her card: a texel-for-pixel silhouette, feet on her feet, `her_px` native px tall."""
    sx, sy, _ = cam.project(np.array(cam.her))
    fx = (VIEW_W / 2.0 + sx) * ss
    fy = (VIEW_H / 2.0 - sy) * ss
    H = her_px * ss
    im = Image.fromarray(img)
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    hat_w = H * 0.62
    hat_h = H * 0.14
    body_w = H * 0.34
    # body
    d.rectangle([fx - body_w / 2, fy - H * 0.62, fx + body_w / 2, fy - H * 0.06], fill=(240, 236, 226), outline=(40, 34, 30), width=ss)
    d.rectangle([fx - body_w * 0.35, fy - H * 0.06, fx + body_w * 0.35, fy], fill=(44, 46, 70))
    # head and hair
    d.ellipse([fx - H * 0.15, fy - H * 0.84, fx + H * 0.15, fy - H * 0.58], fill=(40, 34, 40), outline=(30, 24, 28))
    # hat
    d.polygon([(fx - hat_w / 2, fy - H * 0.80), (fx + hat_w / 2, fy - H * 0.80), (fx, fy - H)], fill=(238, 230, 206),
              outline=(40, 34, 30))
    d.line([(fx - hat_w / 2, fy - H * 0.80), (fx + hat_w / 2, fy - H * 0.80)], fill=(40, 34, 30), width=ss)
    return np.array(im), (fx / ss, fy / ss)


def frame_png(R, T, trees, vw):
    cam = vw["cam"]
    m, ids, win = build_scene(R, T, trees, cam)
    img, zbuf, ibuf = render(m, cam)
    rec = R["camera"]["recommended"]
    img, feet = her_card(img, cam, rec["her_px"])
    im = Image.fromarray(img)
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return b.getvalue(), feet, ids, ibuf


def label_points(R, T, vw):
    """Screen positions (native px) for the view's named elements: a point a little up the thing."""
    cam = vw["cam"]
    out = []
    for eid in vw["see"] + vw.get("hide", []):
        e = R["_index"].get(eid)
        if not e:
            continue
        cand = []
        if e.get("kind") == "EDA" and e.get("pts"):
            base = float(T.h(0, 0))
            for p in e["pts"]:
                cand.append((p[0], p[1], p[2], p[2] - base))
        elif eid in ("TR-CAM-01", "SG-SHM-01"):
            g0 = float(T.h(0, 0))
            hh = 1.8 if eid == "SG-SHM-01" else 3.5
            cand.append((0.0, -3.7, g0 + hh, hh))
            cand.append((-1.5, -3.4, g0 + hh, hh))
        elif e.get("pos"):
            x, y = e["pos"]
            g = float(T.h(x, y))
            hgt = 1.0
            if isinstance(e.get("size"), list) and e["size"][2]:
                hgt = e["size"][2]
            if e.get("height"):
                hgt = e["height"] * 0.5
            hgt = min(hgt, 4.0)
            cand.append((x, y, (e.get("h") or g) + hgt * 0.7, hgt * 0.7))
        elif e.get("pts"):
            for p in e["pts"]:
                cand.append((p[0], p[1], float(T.h(p[0], p[1])) + 0.3, 0.3))
        elif e.get("poly"):
            c = reg.poly_centroid(e["poly"])
            cand.append((c[0], c[1], float(T.h(c[0], c[1])) + 0.5, 0.5))
        best = None
        for x, y, h, t in cand:
            sx, sy, d = cam.project(np.array([x, y, h]), lean_t=t)
            px, py = cam.to_pixels(sx, sy)
            if 4 <= px <= VIEW_W - 4 and 4 <= py <= VIEW_H - 4:
                best = (px, py)
                break
        out.append((eid, best, eid in vw.get("hide", [])))
    return out


NOTES = {
    "VW-01": ["主角：茅屋（BL-MIN-01）。大屋顶占画面上部，檐下一条深暗（P12，陰翳礼讃）。",
              "画面右缘：G 枝从大楠那边落到院子边，'像一道长满苔的坡'（剧本第 4 场）——",
              "走过去就能上树，不用提示（宪章：不用镜头指路）。",
              "院子朝南敞开，柿子在左下角当框（P13）。屋后是屋敷林，再后面是岩带。",
              "往北一屏之外才是大楠的根：两个主角不同屏（表 4）。"],
    "VW-02": ["主角：东门（两棵老杉 + 道切り绳 + 大草鞋 + 雾）。门是画面上沿的一个框。",
              "门外的路宽（2.8 米），门内收成 1.2–1.6 米；过了门路向左弯下去，",
              "土坎和杉根挡住里面：从门口看不见结界里的任何东西（P1、P3）。",
              "大楠、祠、茅屋都不在画面里（表 5 检查）。雾只认盆灯（已定）。"],
    "VW-03": ["主角：大楠。P3 的画面在她脚下只到约 6 米高：树冠永远在画面外，",
              "大楠靠树干（7.2 米宽，约占画面三分之一）、根、注连绳的亮线和树影读出来。",
              "右边：祠的屋顶，背后瑞垣里的磐座（禁足地只围它）。脚前：烂柯的棋盘。",
              "注连绳改挂在离地 1.8 米：挂 2.4 米时离树 5 米以内才看得见。"],
    "VW-04": ["主角：眺望岩。往南走在 P3 里是'盲'的（只看得见脚下往南 5.5 米），",
              "所以崖口和两棵赤松是从画面下沿突然出现的：惊喜，不是指路。",
              "坐下以后进入已定的眺望模式（竖直视野 40°，只看南面的平原，G5R3-16、49）。",
              "芒在她身边齐腰到齐肩：风吹成浪（P8、P9）。"],
    "VW-05": ["主角：路本身（节奏）。九十九折的一段往西爬：弯口外侧一尊红围嘴的地藏，",
              "上一段路的路缘石在画面上沿露出来——下一个目标总看得见，但不是同一个（宪章：引导）。",
              "P3 看不见大楠的树冠和北边山顶「隔」塔的红光：剧本第 1 场的这两样要靠",
              "演出镜头或光（红光映在云和雾上），见设计说明第 9 节。"],
    "VW-06": ["补充视点：墓台。九座墓朝南一列，灯杆在前；墓后石垣上是百日红的一团红，",
              "大楠的南枝从头顶伸过来（剧本第 3 场'大楠の枝の下に小さな墓が九つ'）。",
              "苔庭被 1.44 米的石垣挡住：再上九级才整个出现（P3、P4）。"],
    "VW-07": ["补充视点：切通。窄、暗、往下；两侧土坎和杉根，左前方露出溪和连香树的干。",
              "门后的路换性格（P18）：宽度、材质、坡度、光一起换。"],
}


def sheet_view(R, T, trees, vw, fonts):
    png, feet, ids, ibuf = frame_png(R, T, trees, vw)
    cam = vw["cam"]
    W, H = 1960, 1010
    svg = Svg(W, H, "新手村 v4 关键视角 %s %s" % (vw["id"], vw["name"]))
    PL.defs(svg)
    svg.layer("base")
    svg.rect(0, 0, W, H, fill=S.PAPER)
    PL.title_block(svg, 40, 18, W - 80, "%s　%s" % (vw["id"], vw["name"]), vw["purpose"], [], "P3 关键视角")
    fu, fv = 40, 112
    fw, fh = VIEW_W * SS, VIEW_H * SS
    svg.image(fu, fv, fw, fh, "data:image/png;base64," + base64.b64encode(png).decode(), preserveAspectRatio="none")
    svg.rect(fu, fv, fw, fh, fill="none", stroke=S.INK, stroke_width=1.6)
    # thirds
    for k in (1, 2):
        svg.line(fu + fw * k / 3, fv, fu + fw * k / 3, fv + fh, stroke="#ffffff", stroke_width=0.6, opacity=0.45,
                 stroke_dasharray="6,6")
        svg.line(fu, fv + fh * k / 3, fu + fw, fv + fh * k / 3, stroke="#ffffff", stroke_width=0.6, opacity=0.45,
                 stroke_dasharray="6,6")
    # labels
    svg.layer("labels")
    placed = []
    for eid, pt, hidden in label_points(R, T, vw):
        if pt is None:
            continue
        u, v = fu + pt[0] * SS, fv + pt[1] * SS
        txt = eid + ("（应藏住）" if hidden else "")
        w = len(txt) * 6.2 + 8
        cand = [(14, -14), (14, 18), (-14 - w, -14), (-14 - w, 18), (20, -30), (-20 - w, -30), (20, 34), (-20 - w, 34)]
        for du, dv in cand:
            box = (u + du, v + dv - 12, u + du + w, v + dv + 3)
            if box[0] < fu or box[2] > fu + fw or box[1] < fv or box[3] > fv + fh:
                continue
            if all(box[2] < b[0] or box[0] > b[2] or box[3] < b[1] or box[1] > b[3] for b in placed):
                break
        placed.append(box)
        svg.line(u, v, box[0] if du > 0 else box[2], v + dv - 4, stroke=S.INK, stroke_width=0.8)
        svg.circle(u, v, 2.2, fill=(S.VERMILION if hidden else S.INK))
        svg.text(box[0] + 4, v + dv, txt, cls="lab-b", halo="#f3efe6")
    # her
    hu, hv = fu + feet[0] * SS, fv + feet[1] * SS
    rec = R["camera"]["recommended"]
    svg.text(hu + 14, hv + 4, "她（%d 像素）" % rec["her_px"], cls="lab-b", halo="#f3efe6", fill=S.VERMILION)
    # frame caption
    e = screen_extent(cam)
    svg.text(fu, fv + fh + 22, "原生 640 × 360（图上放大 2 倍）　相机：竖直视野 38°、俯角 45°、每米 %.0f 像素、后倾份额 %.1f（推荐方案 C）"
             % (cam.ppm, cam.share), cls="note-s")
    svg.text(fu, fv + fh + 38, "她站在 (%.1f, %.1f)，地面高 %.2f 米。画面里的地面：往北 %.1f 米、往南 %.1f 米，她那一行宽 %.1f 米。"
             "体块示意（不是美术）：树冠、屋顶、岩都是简化的体块，光从西南上方来。" % (vw["her"][0], vw["her"][1], cam.her[2],
                                                                    e["north"], e["south"], e["w_her"]), cls="note-s")
    # right panel: plan inset + notes
    px0 = fu + fw + 40
    pw = W - px0 - 40
    x_c, y_c = vw["her"]
    span = 46.0
    s = pw / span
    fr = Frame(x_c - span / 2, y_c - 10, x_c + span / 2, y_c - 10 + 300 / s, s, px0, fv)
    svg.defn('<clipPath id="inset"><rect x="%s" y="%s" width="%s" height="%s"/></clipPath>' % (f(fr.u0), f(fr.v0), f(fr.w), f(fr.h)))
    svg.auto_clip = "url(#inset)"
    svg.layer("inset-bg")
    svg.rect(fr.u0, fr.v0, fr.w, fr.h, fill="#f7f4ec")
    svg.layer("inset-hill")
    u, v, w, h, uri = PL.hillshade_image(T, fr, alpha=0.35)
    svg.image(u, v, w, h, uri, preserveAspectRatio="none")
    PL.draw_contours(svg, fr, T, interval=1.0, major=5.0, labels=False)
    PL.draw_plantings(svg, fr, R, trees)
    PL.draw_water(svg, fr, R, T)
    PL.draw_cliffs(svg, fr, R, T)
    PL.draw_roads(svg, fr, R, detail=False)
    PL.draw_elements(svg, fr, R)
    PL.draw_camphor(svg, fr, R)
    PL.draw_boundary(svg, fr, R, width=1.6)
    svg.layer("inset-frustum")
    PL.draw_frustum(svg, fr, T, cam, "", fill_op=0.16, lab=False, width=1.4)
    svg.auto_clip = None
    svg.layer("furniture")
    svg.rect(fr.u0, fr.v0, fr.w, fr.h, fill="none", stroke=S.INK, stroke_width=1.0)
    PL.north_arrow(svg, fr.u0 + fr.w - 20, fr.v0 + 34, 14)
    PL.scale_bar(svg, fr.u0 + 10, fr.v0 + fr.h - 22, s, (0, 5, 10), label=True)
    y = fr.v0 + fr.h + 26
    svg.text(px0, y, "平面上的视野（蓝）", cls="note-b")
    y += 26
    svg.text(px0, y, "构图", cls="head")
    y += 20
    for ln in NOTES.get(vw["id"], []):
        svg.text(px0, y, ln, cls="note-s")
        y += 15
    y += 8
    svg.text(px0, y, "要看见的 / 要藏住的", cls="head")
    y += 20
    labs = label_points(R, T, vw)
    for eid, pt, hidden in labs:
        ok = (pt is not None) != hidden
        name = R["_index"][eid].get("name", "") if eid in R["_index"] else ""
        svg.text(px0, y, "%s %s %s" % ("✓" if ok else "✗", eid, name), cls="note-s", fill=(S.INK if ok else S.VERMILION))
        y += 14
    return svg, W, H
