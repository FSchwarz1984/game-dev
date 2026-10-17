"""Plans drawn from the registry: the site plan, the realm plan with every element's ID, the
walkability plan and the screens-and-spacing plan. House style in svg.py."""
from __future__ import annotations

import base64
import io
import math

import numpy as np
from PIL import Image
from skimage import measure

from . import registry as reg
from . import svg as S
from .svg import Svg, Frame, f, smooth_path

TREE_FILL = {"SUG": S.CEDAR, "SII": "#7d9a70", "KON": S.BROAD, "MOM": S.MAPLE, "KAT": "#a3b787", "AKM": S.PINE,
             "トチノキ": "#8fa67c", "ヤマザクラ": "#a9b48e", "エゴノキ": "#a7b98f", "アラカシ": "#7f9a74",
             "CAM": "#6f8f5c", "SAR": "#b88a8a", "KAK": "#9fae7a"}


# ---- shared pieces ------------------------------------------------------------------------------------
def defs(svg: Svg):
    svg.defn('<pattern id="moss" width="6" height="6" patternUnits="userSpaceOnUse">'
             '<rect width="6" height="6" fill="%s" opacity="0.55"/><circle cx="1.5" cy="1.5" r="0.7" fill="#7f9a5e"/>'
             '<circle cx="4.5" cy="4" r="0.6" fill="#8aa56a"/></pattern>' % S.MOSS)
    svg.defn('<pattern id="susuki" width="9" height="8" patternUnits="userSpaceOnUse">'
             '<rect width="9" height="8" fill="%s" opacity="0.6"/><path d="M2,7 L2.6,2.5 M2,7 L0.8,3.4 M2,7 L3.6,3.6 '
             'M6.5,6 L7,1.8 M6.5,6 L5.4,2.6" stroke="#9b9466" stroke-width="0.6" fill="none"/></pattern>' % S.SUSUKI)
    svg.defn('<pattern id="sasa" width="4" height="4" patternUnits="userSpaceOnUse">'
             '<rect width="4" height="4" fill="%s" opacity="0.55"/><path d="M1,0 L1,4 M3,0 L3,4" stroke="#4e5f35" '
             'stroke-width="0.7"/></pattern>' % S.BAMBOO)
    svg.defn('<pattern id="shiba" width="7" height="7" patternUnits="userSpaceOnUse">'
             '<rect width="7" height="7" fill="%s" opacity="0.45"/><path d="M1,5 l0.5,-1.6 l0.5,1.6 M4.5,2.5 l0.5,-1.6 '
             'l0.5,1.6" stroke="#9a9a6e" stroke-width="0.5" fill="none"/></pattern>' % S.GRASS)
    svg.defn('<pattern id="plot" width="8" height="5" patternUnits="userSpaceOnUse">'
             '<rect width="8" height="5" fill="%s" opacity="0.7"/><path d="M0,2.5 L8,2.5" stroke="#8f7a4f" stroke-width="0.8"/>'
             '<circle cx="2" cy="1.2" r="0.6" fill="#6f8a4f"/><circle cx="6" cy="3.8" r="0.6" fill="#6f8a4f"/></pattern>' % S.PLOT)
    svg.defn('<pattern id="shin" width="5" height="5" patternUnits="userSpaceOnUse">'
             '<rect width="5" height="5" fill="%s"/><path d="M0,0 L5,0 M0,0 L0,5" stroke="#a79f8e" stroke-width="0.5"/></pattern>' % S.PATH_SHIN)
    svg.defn('<pattern id="gyo" width="6" height="6" patternUnits="userSpaceOnUse">'
             '<rect width="6" height="6" fill="%s"/><circle cx="1.6" cy="1.8" r="0.9" fill="none" stroke="#b4a78c" stroke-width="0.4"/>'
             '<circle cx="4.4" cy="4.4" r="1.1" fill="none" stroke="#b4a78c" stroke-width="0.4"/></pattern>' % S.PATH_GYO)
    svg.defn('<pattern id="rockh" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(35)">'
             '<rect width="4" height="4" fill="%s"/><path d="M0,0 L0,4" stroke="#867f72" stroke-width="0.6"/></pattern>' % S.ROCK)
    svg.defn('<pattern id="thatch" width="3" height="3" patternUnits="userSpaceOnUse">'
             '<rect width="3" height="3" fill="%s"/><path d="M0,3 L3,0" stroke="#a8925f" stroke-width="0.4"/></pattern>' % S.THATCH)
    for cid, col in (("arrow", S.INK), ("arrow-sky", S.SKY), ("arrow-red", S.VERMILION)):
        svg.defn('<marker id="%s" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
                 '<path d="M0,0 L10,5 L0,10 z" fill="%s"/></marker>' % (cid, col))


def hillshade_image(T, fr: Frame, alpha=0.38):
    """The hillshade inside the frame, as a PNG data URI (warm-tinted, transparent where flat-lit)."""
    hs = T.hillshade(az=225.0, alt=38.0)
    j0 = max(0, int((fr.x0 - T.x0) / T.cell))
    j1 = min(T.X.shape[1], int((fr.x1 - T.x0) / T.cell) + 1)
    i0 = max(0, int((fr.y0 - T.y0) / T.cell))
    i1 = min(T.X.shape[0], int((fr.y1 - T.y0) / T.cell) + 1)
    sub = hs[i0:i1, j0:j1][::-1]
    flat = math.sin(math.radians(38.0))
    dark = np.clip((flat - sub) / flat, 0, 1)
    light = np.clip((sub - flat) / (1 - flat), 0, 1)
    rgba = np.zeros(sub.shape + (4,), dtype=np.uint8)
    rgba[..., 0] = np.where(dark > 0, 70, 255)
    rgba[..., 1] = np.where(dark > 0, 58, 252)
    rgba[..., 2] = np.where(dark > 0, 48, 240)
    rgba[..., 3] = np.clip((dark * 255 * alpha * 1.6 + light * 255 * alpha * 0.5), 0, 255).astype(np.uint8)
    im = Image.fromarray(rgba, "RGBA")
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    x0 = T.x0 + j0 * T.cell - T.cell / 2
    y1 = T.y0 + (i1 - 1) * T.cell + T.cell / 2
    u, v = fr(x0, y1)
    w = (j1 - j0) * T.cell * fr.s
    h = (i1 - i0) * T.cell * fr.s
    return u, v, w, h, "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def contours(T, fr: Frame, interval=1.0, simplify=0.25):
    j0 = max(0, int((fr.x0 - T.x0) / T.cell) - 1)
    j1 = min(T.X.shape[1], int((fr.x1 - T.x0) / T.cell) + 2)
    i0 = max(0, int((fr.y0 - T.y0) / T.cell) - 1)
    i1 = min(T.X.shape[0], int((fr.y1 - T.y0) / T.cell) + 2)
    H = T.H[i0:i1, j0:j1]
    lo = math.floor(H.min() / interval) * interval
    hi = math.ceil(H.max() / interval) * interval
    out = []
    lv = lo
    while lv <= hi + 1e-6:
        for c in measure.find_contours(H, lv):
            if len(c) < 4:
                continue
            xs = T.x0 + (c[:, 1] + j0) * T.cell
            ys = T.y0 + (c[:, 0] + i0) * T.cell
            P = np.stack([xs, ys], axis=1)
            P = _simplify(P, simplify)
            out.append((round(lv, 3), P))
        lv += interval
    return out


def _simplify(P, eps):
    if len(P) < 3:
        return P
    keep = [0]
    def rec(a, b):
        if b <= a + 1:
            return
        A, B = P[a], P[b]
        d = B - A
        L = np.hypot(*d)
        seg = P[a + 1:b]
        if L < 1e-9:
            dist = np.hypot(seg[:, 0] - A[0], seg[:, 1] - A[1])
        else:
            dist = np.abs(d[0] * (seg[:, 1] - A[1]) - d[1] * (seg[:, 0] - A[0])) / L
        k = int(np.argmax(dist))
        if dist[k] > eps:
            rec(a, a + 1 + k)
            keep.append(a + 1 + k)
            rec(a + 1 + k, b)
    rec(0, len(P) - 1)
    keep.append(len(P) - 1)
    keep = sorted(set(keep))
    return P[keep]


def clip_poly_to_frame(P, fr, margin=2.0):
    """Keep only the runs of a polyline that are inside the frame (split where it leaves)."""
    runs, cur = [], []
    for p in P:
        if fr.contains(p[0], p[1], margin):
            cur.append(p)
        else:
            if len(cur) > 1:
                runs.append(np.array(cur))
            cur = []
    if len(cur) > 1:
        runs.append(np.array(cur))
    return runs


def draw_contours(svg: Svg, fr: Frame, T, interval=1.0, major=5.0, labels=True, minor_w=0.35, major_w=0.85):
    svg.layer("contours")
    cs = contours(T, fr, interval)
    lab_spots = []
    for lv, P in cs:
        is_major = abs(lv / major - round(lv / major)) < 1e-6
        for run in clip_poly_to_frame(P, fr):
            pts = fr.pts(run)
            d = smooth_path(pts)
            if is_major:
                svg.path(d, fill="none", stroke="#7a6a55", stroke_width=major_w, opacity=0.75)
            else:
                svg.path(d, fill="none", stroke="#9d8f7b", stroke_width=minor_w, opacity=0.6)
            if labels and is_major and len(run) > 12:
                k = len(run) // 2
                u, v = fr(run[k][0], run[k][1])
                if all(math.hypot(u - a, v - b) > 90 for a, b in lab_spots) and fr.contains(run[k][0], run[k][1], -4):
                    du, dv = np.subtract(fr(*run[min(k + 2, len(run) - 1)]), fr(*run[max(k - 2, 0)]))
                    ang = math.degrees(math.atan2(dv, du))
                    if ang > 90:
                        ang -= 180
                    if ang < -90:
                        ang += 180
                    svg.text(u, v + 2.5, "%+.0f" % lv if lv else "±0", cls="num", anchor="middle", rot=ang, halo=True)
                    lab_spots.append((u, v))


def road_polygon(rd, step=0.3, widths=None):
    P, s = reg.resample([p[:2] for p in rd["pts"]], step)
    n = len(P)
    if rd.get("widths"):
        Pw, sw = reg.resample([list(p[:2]) + [w] for p, w in zip(rd["pts"], rd["widths"])], step)
        W = np.interp(s, sw, Pw[:, 2])
    else:
        W = np.full(n, rd["w"])
    L = reg.offset_polyline(P, 1.0)
    T = (L - P)
    left = P + T * (W[:, None] / 2)
    right = P - T * (W[:, None] / 2)
    return np.concatenate([left, right[::-1]], axis=0), P, W


def draw_roads(svg: Svg, fr: Frame, R, detail=True):
    svg.layer("roads")
    order = {"KAI": 0, "MUR": 1, "TSU": 2, "NEM": 3, "TOB": 4, "NOB": 5, "DAN": 6, "KIR": 7}
    for rd in sorted(R["roads"], key=lambda r: order.get(r["kind"], 9)):
        poly, P, W = road_polygon(rd)
        pts = fr.pts(poly)
        if rd["kind"] == "TOB":
            # stepping stones
            Q, s = reg.resample([p[:2] for p in rd["pts"]], 1.25)
            for q in Q:
                u, v = fr(q[0], q[1])
                svg.circle(u, v, max(0.32 * fr.s, 1.2), fill=S.PATH_GYO, stroke=S.INK2, stroke_width=0.5)
            continue
        if rd["grade"] == "真":
            fill, stroke, dash = "url(#shin)", S.INK, None
        elif rd["grade"] == "行":
            fill, stroke, dash = ("url(#gyo)" if detail else S.PATH_GYO), S.INK2, None
        else:
            fill, stroke, dash = S.PATH_SO, S.INK3, "2.2,1.6"
        svg.path(smooth_path(pts, closed=True, tension=0.0), fill=fill, stroke=stroke, stroke_width=0.6,
                 stroke_dasharray=dash, opacity=0.95)
        if rd["kind"] == "DAN" and rd.get("steps"):
            st = rd["steps"]
            (x0, y0), (x1, y1) = rd["pts"][0][:2], rd["pts"][-1][:2]
            L = math.hypot(x1 - x0, y1 - y0)
            ux, uy = (x1 - x0) / L, (y1 - y0) / L
            nx, ny = -uy, ux
            for k in range(st["count"] + 1):
                t = k / st["count"]
                cx, cy = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                a = fr(cx + nx * rd["w"] / 2, cy + ny * rd["w"] / 2)
                b = fr(cx - nx * rd["w"] / 2, cy - ny * rd["w"] / 2)
                svg.line(a[0], a[1], b[0], b[1], stroke=S.INK2, stroke_width=0.5)
            a = fr(x0 + ux * 0.4, y0 + uy * 0.4)
            b = fr(x1 - ux * 0.4, y1 - uy * 0.4)
            svg.line(a[0], a[1], b[0], b[1], stroke=S.INK, stroke_width=0.7, marker_end="url(#arrow)")
        if detail and rd["kind"] == "KAI":
            # kerb stones along both edges, denser at the hairpins
            for side in (1, -1):
                E = reg.offset_polyline(P, side * (rd["w"] / 2 + 0.25))
                for k in range(0, len(E), 6):
                    u, v = fr(E[k][0], E[k][1])
                    svg.circle(u, v, max(0.18 * fr.s, 0.6), fill="#9a9284", stroke="none")


def draw_water(svg: Svg, fr: Frame, R, T):
    svg.layer("water")
    for w in R["water"]:
        if w.get("pts") and len(w["pts"][0]) >= 4:
            P, s = reg.resample(w["pts"], 0.3)
            left = reg.offset_polyline(P, 1.0)
            Tn = left - P[:, :2]
            half = P[:, 3:4] / 2
            Lp = P[:, :2] + Tn * half
            Rp = P[:, :2] - Tn * half
            poly = np.concatenate([Lp, Rp[::-1]], axis=0)
            svg.path(smooth_path(fr.pts(poly), closed=True, tension=0.0), fill=S.WATER, stroke=S.WATER_EDGE,
                     stroke_width=0.6)
            # flow arrows
            Q, sq = reg.resample(w["pts"], 9.0)
            for k in range(1, len(Q) - 1, 2):
                a = fr(Q[k][0], Q[k][1])
                b = fr(Q[k][0] + (Q[k + 1][0] - Q[k][0]) * 0.25, Q[k][1] + (Q[k + 1][1] - Q[k][1]) * 0.25)
                if fr.contains(Q[k][0], Q[k][1]):
                    svg.line(a[0], a[1], b[0], b[1], stroke=S.WATER_EDGE, stroke_width=0.8, marker_end="url(#arrow-sky)")
        elif w.get("pts"):
            # bamboo pipes
            svg.path(smooth_path(fr.pts(w["pts"])), fill="none", stroke="#6f8a4a", stroke_width=1.0,
                     stroke_dasharray="3,1.2")
        if w["id"].startswith("WA-SPR") or w["id"].startswith("WA-BAS"):
            u, v = fr(*w["pos"])
            svg.circle(u, v, 3.2 if w["id"].startswith("WA-SPR") else 2.4, fill=S.WATER, stroke=S.WATER_EDGE, stroke_width=0.8)
            if w["id"].startswith("WA-SPR"):
                for a in range(0, 360, 60):
                    svg.line(u + 3.6 * math.cos(math.radians(a)), v + 3.6 * math.sin(math.radians(a)),
                             u + 5.4 * math.cos(math.radians(a)), v + 5.4 * math.sin(math.radians(a)),
                             stroke=S.WATER_EDGE, stroke_width=0.6)
        if w["id"].startswith("WA-FAL"):
            u, v = fr(*w["pos"])
            for k in range(5):
                svg.line(u - 6 + k * 3, v - 3, u - 6 + k * 3, v + 5, stroke=S.WATER_EDGE, stroke_width=0.9)
            svg.line(u - 8, v - 3, u + 8, v - 3, stroke=S.ROCK_EDGE, stroke_width=1.6)


def draw_cliffs(svg: Svg, fr: Frame, R, T):
    svg.layer("cliffs")
    for c in R["terrain"]["cliffs"]:
        P, s = reg.resample(c["pts"], 0.4)
        pts = fr.pts(P)
        svg.path(smooth_path(pts), fill="none", stroke=S.ROCK_EDGE, stroke_width=1.4)
        # hachures toward the drop
        side, _ = reg.signed_side(np.array([P[len(P) // 2, 0]]), np.array([P[len(P) // 2, 1] - 3.0]), P[:, :2])
        sg = side[0] if side[0] != 0 else 1
        Q, _ = reg.resample(c["pts"], 1.1)
        N = reg.offset_polyline(Q, sg * 1.0) - Q[:, :2]
        for k in range(len(Q)):
            ln = 1.6 + (0.9 if k % 2 else 0.0)
            a = fr(Q[k][0], Q[k][1])
            b = fr(Q[k][0] + N[k][0] * ln, Q[k][1] + N[k][1] * ln)
            svg.line(a[0], a[1], b[0], b[1], stroke=S.ROCK_EDGE, stroke_width=0.7)


def tree_symbol(svg: Svg, u, v, r, kind, trunk=None, opacity=0.9):
    col = TREE_FILL.get(kind, S.BROAD)
    if kind in ("SUG", "AKM"):
        n = 12
        pts = []
        for k in range(n * 2):
            a = math.pi * k / n
            rr = r if k % 2 == 0 else r * 0.78
            pts.append((u + rr * math.cos(a), v + rr * math.sin(a)))
        svg.poly(pts, fill=col, stroke="#4c5f45", stroke_width=0.45, opacity=opacity)
    else:
        n = 9
        d = []
        for k in range(n):
            a0 = 2 * math.pi * k / n
            a1 = 2 * math.pi * (k + 1) / n
            p0 = (u + r * math.cos(a0), v + r * math.sin(a0))
            p1 = (u + r * math.cos(a1), v + r * math.sin(a1))
            am = (a0 + a1) / 2
            c = (u + r * 1.18 * math.cos(am), v + r * 1.18 * math.sin(am))
            if k == 0:
                d.append("M%s,%s" % (f(p0[0]), f(p0[1])))
            d.append("Q%s,%s %s,%s" % (f(c[0]), f(c[1]), f(p1[0]), f(p1[1])))
        svg.path(" ".join(d) + " Z", fill=col, stroke="#5a6a4a", stroke_width=0.45, opacity=opacity)
    if trunk:
        svg.circle(u, v, max(trunk, 0.8), fill="#5b4a3a", stroke="none")


def draw_plantings(svg: Svg, fr: Frame, R, trees):
    svg.layer("ground")
    fills = {"KOK": "url(#moss)", "SUS": "url(#susuki)", "SSA": "url(#sasa)", "SHI": "url(#shiba)"}
    for pl in R["plantings"]:
        if pl.get("poly") and pl["kind"] in fills:
            svg.poly(fr.pts(pl["poly"]), fill=fills[pl["kind"]], stroke=("#4e5f35" if pl["kind"] == "SSA" else "none"),
                     stroke_width=0.6, opacity=1.0)
    for e in R["elements"]:
        if e.get("kind") == "HAT" and e.get("poly"):
            svg.poly(fr.pts(e["poly"]), fill="url(#plot)", stroke=S.INK3, stroke_width=0.5)
    svg.layer("trees")
    allt = []
    for pid, ts in trees.items():
        for t in ts:
            allt.append(t)
    allt.sort(key=lambda t: -t["y"])
    for t in allt:
        if not fr.contains(t["x"], t["y"], 6):
            continue
        u, v = fr(t["x"], t["y"])
        tree_symbol(svg, u, v, t["crown_r"] * fr.s, t["kind"], trunk=t["trunk_r"] * fr.s, opacity=0.82)


def draw_camphor(svg: Svg, fr: Frame, R, crown=True):
    e = R["_index"]["TR-CAM-01"]
    svg.layer("camphor")
    if crown:
        pts = fr.pts(e["crown"])
        svg.path(smooth_path(pts, closed=True), fill="#6f8f5c", fill_opacity=0.10, stroke="#3f5a33", stroke_width=1.2,
                 stroke_dasharray="7,3,1.5,3")
        hole = e["crown_hole"]
        u, v = fr(*hole["pos"])
        svg.circle(u, v, hole["r"] * fr.s, fill=S.PAPER, fill_opacity=0.55, stroke="#3f5a33", stroke_width=0.7,
                   stroke_dasharray="2,2")
    for lid in ("TR-CAM-01G", "TR-CAM-01S"):
        L = R["_index"][lid]
        P = np.array([[p[0], p[1]] for p in L["pts"]])
        D = np.array(L["diam"])
        Q, s = reg.resample(np.concatenate([P, D[:, None]], axis=1), 0.3)
        left = reg.offset_polyline(Q, 1.0) - Q[:, :2]
        a = Q[:, :2] + left * Q[:, 2:3] / 2
        b = Q[:, :2] - left * Q[:, 2:3] / 2
        poly = np.concatenate([a, b[::-1]])
        svg.path(smooth_path(fr.pts(poly), closed=True, tension=0.0), fill="#8a6f55",
                 fill_opacity=(0.9 if lid.endswith("G") else 0.55), stroke="#4f3d2c", stroke_width=0.6,
                 stroke_dasharray=(None if lid.endswith("G") else "2,1.5"))
        if lid.endswith("G"):
            # the moss path on top
            svg.path(smooth_path(fr.pts(Q[:, :2])), fill="none", stroke="#b8d18a", stroke_width=max(0.35 * fr.s, 1.2),
                     stroke_linecap="round", opacity=0.95)
    fp = e["footprint"]["poly"]
    svg.path(smooth_path(fr.pts(fp), closed=True, tension=0.4), fill="#6a5340", stroke="#3b2d22", stroke_width=0.9)
    u, v = fr(0, 0)
    svg.circle(u, v, 3.6 * fr.s, fill="#7a6048", stroke="#3b2d22", stroke_width=1.0)
    # the shimenawa round the trunk
    svg.circle(u, v, 3.75 * fr.s, fill="none", stroke="#e6ddc6", stroke_width=1.4)
    svg.circle(u, v, 3.75 * fr.s, fill="none", stroke=S.INK, stroke_width=0.5, stroke_dasharray="1.2,1.6")


def draw_elements(svg: Svg, fr: Frame, R, detail=True):
    svg.layer("elements")
    for e in R["elements"]:
        if e["id"].startswith("TR-CAM") or e["cat"] in ("FX", "AN") or e["kind"] in ("HAT",):
            continue
        cat, kind = e["cat"], e["kind"]
        pos = e.get("pos")
        if pos and not fr.contains(pos[0], pos[1], 4):
            continue
        if cat == "TR":
            if kind == "SUG" and e.get("pts"):           # the fallen cedar
                P = e["pts"]
                a, b = fr(*P[0]), fr(*P[1])
                svg.line(a[0], a[1], b[0], b[1], stroke="#6b5440", stroke_width=max(1.2 * fr.s, 2), stroke_linecap="round")
                Q, _ = reg.resample(P, 1.4)
                for q in Q[1:-1]:
                    u, v = fr(q[0], q[1])
                    tree_symbol(svg, u, v, 0.7 * fr.s, "SUG", opacity=0.95)
                continue
            r = e.get("crown", {}).get("r", 3.0) if isinstance(e.get("crown"), dict) else 3.0
            u, v = fr(*pos)
            kk = {"SAR": "SAR", "KAK": "KAK", "MOM": "MOM", "KAT": "KAT", "AKM": "AKM", "SUG": "SUG"}.get(kind, "KON")
            tree_symbol(svg, u, v, r * fr.s, kk, trunk=e.get("trunk_d", 0.5) / 2 * fr.s, opacity=0.88)
            if kind == "SAR":
                for k in range(7):
                    a = k * 2 * math.pi / 7
                    svg.circle(u + r * 0.55 * fr.s * math.cos(a), v + r * 0.55 * fr.s * math.sin(a), max(0.35 * fr.s, 1.0),
                               fill="#c4566a", stroke="none")
            continue
        if cat == "SH":
            u, v = fr(*pos)
            r = (e["size"][0] / 2) * fr.s
            tree_symbol(svg, u, v, r, "SII", opacity=0.9)
            continue
        if cat == "BL":
            draw_building(svg, fr, e)
            continue
        if cat == "RK":
            shapes = reg.footprint_shapes(e)
            for sh in shapes:
                if sh[0] == "poly":
                    svg.path(smooth_path(fr.pts(sh[1]), closed=True, tension=0.35), fill="url(#rockh)", stroke=S.ROCK_EDGE,
                             stroke_width=0.9)
                elif sh[0] == "circle":
                    u, v = fr(sh[1], sh[2])
                    svg.circle(u, v, sh[3] * fr.s, fill="url(#rockh)", stroke=S.ROCK_EDGE, stroke_width=0.8)
            if not shapes and pos:
                u, v = fr(*pos)
                w = (e.get("size") or [0.6])[0] / 2 * fr.s
                svg.circle(u, v, max(w, 1.4), fill=S.ROCK, stroke=S.ROCK_EDGE, stroke_width=0.6)
            continue
        if cat == "ST" and kind == "GAK":
            if e.get("pts") and kind == "GAK" and e["id"] != "ST-GAK-02":
                draw_wall(svg, fr, e["pts"], e["size"][2])
            elif e["id"] == "ST-GAK-02":
                (x0, y0) = (e["pos"][0] - e["size"][0] / 2, e["pos"][1] - e["size"][1] / 2)
                pts = [(x0, y0), (x0 + e["size"][0], y0), (x0 + e["size"][0], y0 + e["size"][1]), (x0, y0 + e["size"][1])]
                svg.poly(fr.pts(pts), fill="#d9d2c2", stroke=S.INK, stroke_width=1.0)
                st = e["steps"]
                for k in range(st["count"] + 1):
                    yy = st["from"][1] + (st["to"][1] - st["from"][1]) * k / st["count"]
                    a = fr(st["from"][0] - st["w"] / 2, yy)
                    b = fr(st["from"][0] + st["w"] / 2, yy)
                    svg.line(a[0], a[1], b[0], b[1], stroke=S.INK2, stroke_width=0.5)
            continue
        if cat == "ST" and kind == "HAS":
            P = e["pts"]
            a, b = fr(*P[0]), fr(*P[1])
            svg.line(a[0], a[1], b[0], b[1], stroke=S.ROCK_EDGE, stroke_width=e["size"][1] * fr.s + 1.2, stroke_linecap="butt")
            svg.line(a[0], a[1], b[0], b[1], stroke="#cfc8b8", stroke_width=e["size"][1] * fr.s, stroke_linecap="butt")
            continue
        if cat == "SG" and kind == "MZG":
            pts = fr.pts(e["pts"])
            svg.path(smooth_path(pts, tension=0.0), fill="none", stroke="#6c4f3a", stroke_width=max(0.22 * fr.s, 1.6))
            Q, _ = reg.resample(e["pts"], 0.6)
            N = reg.offset_polyline(Q, 0.18) - Q[:, :2]
            for k in range(len(Q)):
                a = fr(Q[k][0] - N[k][0], Q[k][1] - N[k][1])
                b = fr(Q[k][0] + N[k][0], Q[k][1] + N[k][1])
                svg.line(a[0], a[1], b[0], b[1], stroke="#6c4f3a", stroke_width=0.7)
            continue
        if cat == "SG" and kind in ("MCK", "WAR"):
            if kind == "MCK":
                g = next((g for g in R["boundary"]["gates"] if g["id"] == e["id"]), None)
                if g:
                    a, b = fr(*g["between"][0]), fr(*g["between"][1])
                    svg.line(a[0], a[1], b[0], b[1], stroke="#c9b27a", stroke_width=2.2)
                    svg.line(a[0], a[1], b[0], b[1], stroke=S.INK, stroke_width=0.6, stroke_dasharray="1.4,1.4")
            else:
                u, v = fr(*pos)
                svg.rect(u - 3.2, v - 1.6, 6.4, 3.2, rx=1.4, fill="#c9b27a", stroke=S.INK, stroke_width=0.6)
            continue
        if cat == "SG" and kind == "SHM":
            continue
        if cat == "SG" and kind in ("HAK",):
            u, v = fr(*pos)
            s = max(0.42 * fr.s, 2.4)
            svg.rect(u - s / 2, v - s / 2, s, s * 0.8, fill="#b9b2a4", stroke=S.INK, stroke_width=0.6)
            continue
        if cat == "SG" and kind in ("TOU",):
            u, v = fr(*pos)
            svg.circle(u, v, 0.8, fill="#7a6a4a")
            continue
        if cat == "SG" and kind in ("AKA",):
            u, v = fr(*pos)
            svg.circle(u, v, max(0.22 * fr.s, 2.0), fill=S.VERMILION, stroke=S.INK, stroke_width=0.5)
            continue
        if cat == "SG" and kind in ("JIZ", "DOS", "SAI"):
            u, v = fr(*pos)
            r = max((e["size"][0] / 2) * fr.s, 2.0)
            svg.circle(u, v, r, fill="#b8b1a3", stroke=S.INK, stroke_width=0.7)
            if kind == "JIZ":
                svg.circle(u, v + r * 0.2, r * 0.55, fill="#c4473a")
            continue
        if cat == "ST" and kind in ("TOR", "CHO"):
            u, v = fr(*pos)
            r = max(0.32 * fr.s, 1.8)
            svg.rect(u - r, v - r, 2 * r, 2 * r, fill="#c8c1b2", stroke=S.INK, stroke_width=0.6)
            svg.circle(u, v, r * 0.45, fill=S.INK2)
            continue
        if cat == "ST" and kind in ("CHZ", "MIZ", "KUT"):
            shapes = reg.footprint_shapes(e)
            for sh in shapes:
                if sh[0] == "circle":
                    u, v = fr(sh[1], sh[2])
                    svg.circle(u, v, sh[3] * fr.s, fill="#c8c1b2", stroke=S.INK, stroke_width=0.6)
                    if kind == "CHZ":
                        svg.circle(u, v, sh[3] * fr.s * 0.55, fill=S.WATER)
                elif sh[0] == "poly":
                    svg.poly(fr.pts(sh[1]), fill="#c8c1b2", stroke=S.INK, stroke_width=0.6)
                    if kind == "MIZ":
                        P = np.array(sh[1])
                        c = P.mean(axis=0)
                        Pi = c + (P - c) * 0.6
                        svg.poly(fr.pts(Pi), fill=S.WATER, stroke="none")
            if not shapes and pos:
                u, v = fr(*pos)
                svg.rect(u - 2, v - 1.4, 4, 2.8, fill="#c8c1b2", stroke=S.INK, stroke_width=0.6)
            continue
        if cat == "PR":
            shapes = reg.footprint_shapes(e)
            col = "#b6a587" if e.get("collision") == "solid" else "#d1c4a6"
            if e["kind"] == "CHA":
                (x0, y0) = (pos[0] - e["size"][0] / 2, pos[1] - e["size"][1] / 2)
                pts = [(x0, y0), (x0 + e["size"][0], y0), (x0 + e["size"][0], y0 + e["size"][1]), (x0, y0 + e["size"][1])]
                svg.poly(fr.pts(pts), fill="none", stroke=S.INK2, stroke_width=0.8, stroke_dasharray="3,2")
                continue
            if e["kind"] == "MUS":
                (x0, y0) = (pos[0] - e["size"][0] / 2, pos[1] - e["size"][1] / 2)
                svg.rect(*fr(x0, y0 + e["size"][1]), e["size"][0] * fr.s, e["size"][1] * fr.s, fill="#d8c79c",
                         stroke=S.INK3, stroke_width=0.5)
                continue
            for sh in shapes:
                if sh[0] == "circle":
                    u, v = fr(sh[1], sh[2])
                    svg.circle(u, v, max(sh[3] * fr.s, 1.2), fill=col, stroke=S.INK2, stroke_width=0.5)
                elif sh[0] == "poly":
                    svg.poly(fr.pts(sh[1]), fill=col, stroke=S.INK2, stroke_width=0.5)
            if not shapes and pos:
                u, v = fr(*pos)
                svg.circle(u, v, 1.3, fill=col, stroke=S.INK2, stroke_width=0.5)
            continue


def draw_wall(svg: Svg, fr: Frame, pts, height):
    """Retaining wall: a heavy line with short ticks on the low (south) side."""
    P = np.asarray(pts, dtype=float)
    a = fr.pts(P)
    svg.path(smooth_path(a, tension=0.0), fill="none", stroke=S.INK, stroke_width=1.5)
    Q, _ = reg.resample(P, 0.8)
    N = reg.offset_polyline(Q, 1.0) - Q[:, :2]
    # ticks toward the south side
    if np.mean(N[:, 1]) > 0:
        N = -N
    for k in range(len(Q)):
        p0 = fr(Q[k][0], Q[k][1])
        p1 = fr(Q[k][0] + N[k][0] * 0.55, Q[k][1] + N[k][1] * 0.55)
        svg.line(p0[0], p0[1], p1[0], p1[1], stroke=S.INK, stroke_width=0.6)


def draw_building(svg: Svg, fr: Frame, e):
    x, y = e["pos"]
    if e["kind"] == "MIN":
        rw, rd = e["roof"]
        x0, x1, y0, y1 = x - rw / 2, x + rw / 2, y - rd / 2, y + rd / 2
        eng = e.get("engawa")
        if eng:
            svg.poly(fr.pts(eng["poly"]), fill="#c9b08a", stroke=S.INK2, stroke_width=0.5)
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        svg.poly(fr.pts(corners), fill="url(#thatch)", stroke=S.INK, stroke_width=1.1)
        # hip roof lines
        r1 = (x0 + rd / 2, y)
        r2 = (x1 - rd / 2, y)
        for c, r in (((x0, y0), r1), ((x0, y1), r1), ((x1, y0), r2), ((x1, y1), r2)):
            a, b = fr(*c), fr(*r)
            svg.line(a[0], a[1], b[0], b[1], stroke=S.INK2, stroke_width=0.6)
        a, b = fr(*r1), fr(*r2)
        svg.line(a[0], a[1], b[0], b[1], stroke=S.INK, stroke_width=1.6)
        # the walls under the roof (dashed)
        fp = e["footprint"]["poly"]
        svg.poly(fr.pts(fp), fill="none", stroke=S.INK2, stroke_width=0.5, stroke_dasharray="2,1.5")
        d = e["door"]
        a = fr(d["pos"][0] - d["w"] / 2, d["pos"][1])
        b = fr(d["pos"][0] + d["w"] / 2, d["pos"][1])
        svg.line(a[0], a[1], b[0], b[1], stroke=S.VERMILION, stroke_width=1.6)
    else:
        w, dd = e["size"][0], e["size"][1]
        x0, x1, y0, y1 = x - w / 2, x + w / 2, y - dd / 2, y + dd / 2
        svg.poly(fr.pts([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]), fill="#bfa98a", stroke=S.INK, stroke_width=1.0)
        a, b = fr(x, y0), fr(x, y1)
        svg.line(a[0], a[1], b[0], b[1], stroke=S.INK, stroke_width=1.1)
        # the one touch of vermilion on the shrine
        u, v = fr(x, y0)
        svg.rect(u - 3, v - 1.5, 6, 3, fill=S.VERMILION, stroke="none")


def draw_boundary(svg: Svg, fr: Frame, R, width=2.0):
    svg.layer("boundary")
    B = R["boundary"]
    P = np.array(B["poly"] + [B["poly"][0]])
    # cut the gates out
    Q, s = reg.resample(P, 0.3)
    gate_pts = []
    for g in B["gates"]:
        a, b = np.array(g["between"][0]), np.array(g["between"][1])
        gate_pts.append((a, b))
    keep = np.ones(len(Q), dtype=bool)
    for a, b in gate_pts:
        d = reg.dist_to_polyline(Q[:, 0], Q[:, 1], [a, b])
        keep &= d > 1.2
    runs, cur = [], []
    for k in range(len(Q)):
        if keep[k]:
            cur.append(Q[k])
        elif len(cur) > 1:
            runs.append(cur)
            cur = []
    if len(cur) > 1:
        runs.append(cur)
    for run in runs:
        svg.path(smooth_path(fr.pts(run), tension=0.0), fill="none", stroke=S.VERMILION, stroke_width=width,
                 stroke_dasharray="10,3,2,3", opacity=0.85)
    for g in B["gates"]:
        a, b = fr(*g["between"][0]), fr(*g["between"][1])
        for p in (a, b):
            svg.circle(p[0], p[1], 2.6, fill=S.PAPER, stroke=S.VERMILION, stroke_width=1.4)


def frustum_ground(T, cam, step=6):
    """The visible ground of a P3 frame on the terrain: ray-march the frame's border."""
    from .p3 import VIEW_W, VIEW_H
    border = []
    for px in range(0, VIEW_W + 1, step * 4):
        border.append((px, VIEW_H))
    for py in range(VIEW_H, -1, -step):
        border.append((VIEW_W, py))
    for px in range(VIEW_W, -1, -step * 4):
        border.append((px, 0))
    for py in range(0, VIEW_H + 1, step):
        border.append((0, py))
    C = cam.C
    out = []
    for px, py in border:
        d = cam.ray(px, py)
        t, hit = 0.0, None
        dt = 0.25
        while t < 120:
            p = C + d * t
            if not (T.x0 < p[0] < T.x1 and T.y0 < p[1] < T.y1):
                break
            if p[2] <= T.h(p[0], p[1]):
                hit = p
                break
            t += dt
        if hit is not None:
            out.append((hit[0], hit[1]))
    return out


def draw_frustum(svg: Svg, fr: Frame, T, cam, label, color=S.SKY, fill_op=0.08, dash=None, lab=True, width=1.1):
    pts = frustum_ground(T, cam)
    if len(pts) < 3:
        return
    svg.poly(fr.pts(pts), fill=color, fill_opacity=fill_op, stroke=color, stroke_width=width, stroke_dasharray=dash)
    u, v = fr(cam.her[0], cam.her[1])
    svg.circle(u, v, 3.0, fill=color, stroke=S.PAPER, stroke_width=1.0)
    if lab:
        svg.text(u + 5, v - 4, label, cls="lab-b", halo=True, fill=color)


def label_elements(svg: Svg, fr: Frame, R, ids=None, avoid=None, cls="lab", minscale=6.0):
    """Greedy label placement around anchors."""
    svg.layer("labels")
    placed = list(avoid or [])
    items = []
    for e in R["elements"]:
        if ids is not None and e["id"] not in ids:
            continue
        if e["id"].startswith("SG-TOU") or e["id"].startswith("AN-NIW-0") and e["id"] != "AN-NIW-01":
            continue
        pos = e.get("pos")
        if not pos or not fr.contains(pos[0], pos[1], -1):
            continue
        items.append((e["id"], pos))
    for rd in R["roads"]:
        if ids is not None and rd["id"] not in ids:
            continue
        P, s = reg.resample([p[:2] for p in rd["pts"]], 0.5)
        inside = [p for p in P if fr.contains(p[0], p[1], -2)]
        if inside:
            items.append((rd["id"], inside[len(inside) // 2]))
    for w in R["water"]:
        if ids is not None and w["id"] not in ids:
            continue
        if w.get("pos"):
            items.append((w["id"], w["pos"]))
        elif w.get("pts"):
            P = w["pts"]
            k = len(P) // 2
            if fr.contains(P[k][0], P[k][1]):
                items.append((w["id"], P[k][:2]))
    for pl in R["plantings"]:
        if ids is not None and pl["id"] not in ids:
            continue
        if pl.get("poly"):
            c = reg.poly_centroid(pl["poly"])
            if fr.contains(c[0], c[1], -2):
                items.append((pl["id"], c))
    cw = 4.8   # approx width per char at 8.5px
    for tid, pos in items:
        u, v = fr(pos[0], pos[1])
        w = len(tid) * cw + 2
        h = 9
        best = None
        for du, dv in ((6, -5), (6, 9), (-6 - w, -5), (-6 - w, 9), (-w / 2, -9), (-w / 2, 16), (10, 2), (-10 - w, 2),
                       (12, -14), (-12 - w, -14), (12, 18), (-12 - w, 18)):
            box = (u + du, v + dv - h + 2, u + du + w, v + dv + 2)
            if all(box[2] < b[0] or box[0] > b[2] or box[3] < b[1] or box[1] > b[3] for b in placed):
                best = (du, dv, box)
                break
        if best is None:
            du, dv = 6, -5
            box = (u + du, v + dv - h + 2, u + du + w, v + dv + 2)
            best = (du, dv, box)
        du, dv, box = best
        placed.append(box)
        tx, ty = u + du, v + dv
        ax = min(max(u, box[0]), box[2])
        ay = min(max(v, box[1]), box[3])
        if math.hypot(ax - u, ay - v) > 4:
            svg.line(u, v, ax, ay, stroke=S.INK3, stroke_width=0.45)
        svg.text(tx, ty, tid, cls=cls, halo=True)
    return placed


def north_arrow(svg: Svg, u, v, size=26):
    svg.path("M%s,%s L%s,%s L%s,%s L%s,%s Z" % (f(u), f(v - size), f(u + size * 0.32), f(v + size * 0.45), f(u), f(v + size * 0.22),
                                              f(u - size * 0.32), f(v + size * 0.45)), fill=S.INK, stroke="none")
    svg.path("M%s,%s L%s,%s L%s,%s Z" % (f(u), f(v - size), f(u - size * 0.32), f(v + size * 0.45), f(u), f(v + size * 0.22)),
             fill=S.PAPER, stroke=S.INK, stroke_width=0.8)
    svg.text(u, v - size - 5, "N", cls="head", anchor="middle")


def scale_bar(svg: Svg, u, v, s, metres=(0, 5, 10, 20, 40), label=True):
    x_end = metres[-1] * s
    for i in range(len(metres) - 1):
        a = metres[i] * s
        b = metres[i + 1] * s
        svg.rect(u + a, v, b - a, 5, fill=(S.INK if i % 2 == 0 else S.PAPER), stroke=S.INK, stroke_width=0.6)
    for m in metres:
        svg.text(u + m * s, v + 16, "%d" % m, cls="num", anchor="middle")
    if label:
        svg.text(u + x_end + 8, v + 6, "米", cls="num")


def title_block(svg: Svg, u, v, w, title, subtitle, lines, sheet):
    svg.text(u, v + 30, title, cls="title")
    svg.text(u, v + 54, subtitle, cls="title2")
    svg.line(u, v + 64, u + w, v + 64, stroke=S.INK, stroke_width=1.2)
    y = v + 80
    for ln in lines:
        svg.text(u, y, ln, cls="note-s")
        y += 14
    svg.text(u + w, v + 30, sheet, cls="head", anchor="end")
    return y


def legend(svg: Svg, u, v, items, col_w=200):
    """items: list of (kind, label, params)."""
    y = v
    for kind, lab, p in items:
        if kind == "head":
            y += 6
            svg.text(u, y + 10, lab, cls="note-b")
            y += 18
            continue
        a, b = u, u + 34
        cy = y + 6
        if kind == "fill":
            svg.rect(a, y, 34, 12, fill=p.get("fill"), stroke=p.get("stroke", "none"), stroke_width=p.get("sw", 0.6),
                     stroke_dasharray=p.get("dash"), opacity=p.get("op", 1.0))
        elif kind == "line":
            svg.line(a, cy, b, cy, stroke=p.get("stroke", S.INK), stroke_width=p.get("sw", 1.0),
                     stroke_dasharray=p.get("dash"), opacity=p.get("op", 1.0))
        elif kind == "wall":
            svg.line(a, cy - 2, b, cy - 2, stroke=S.INK, stroke_width=1.5)
            for k in range(6):
                svg.line(a + 3 + k * 6, cy - 2, a + 3 + k * 6, cy + 3, stroke=S.INK, stroke_width=0.6)
        elif kind == "tree":
            tree_symbol(svg, a + 17, cy, 6.5, p.get("kind", "KON"), trunk=1.0)
        elif kind == "dot":
            svg.circle(a + 17, cy, p.get("r", 3), fill=p.get("fill"), stroke=p.get("stroke", S.INK), stroke_width=0.6)
        elif kind == "cliff":
            svg.line(a, cy - 3, b, cy - 3, stroke=S.ROCK_EDGE, stroke_width=1.4)
            for k in range(7):
                svg.line(a + 2 + k * 5, cy - 3, a + 2 + k * 5, cy + (3 if k % 2 else 1), stroke=S.ROCK_EDGE, stroke_width=0.7)
        elif kind == "steps":
            svg.rect(a, y, 34, 12, fill=S.PATH_GYO, stroke=S.INK2, stroke_width=0.5)
            for k in range(1, 6):
                svg.line(a + k * 6, y, a + k * 6, y + 12, stroke=S.INK2, stroke_width=0.5)
            svg.line(a + 3, cy, b - 3, cy, stroke=S.INK, stroke_width=0.7, marker_end="url(#arrow)")
        svg.text(b + 8, cy + 3.8, lab, cls="leg")
        y += 18
    return y
