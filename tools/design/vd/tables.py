"""Tables for the design note (written to docs/design/village/tables.md): the scale table, the height
schemes, the zone areas in screens, the spacing of the protagonists (tested with the real P3 frame on
the terrain) and what each key view shows."""
from __future__ import annotations

import math

import numpy as np

from . import registry as reg
from .p3 import Cam, SHARES, screen_extent, VIEW_W, VIEW_H

SCREEN_RULE_M2 = 23.0 * 21.0          # the supervisor's rule of thumb for one P3 screen
HER_TOP = 1.52                        # her height with the hat (registry scale CH-KSG)


def her_scheme_px(scheme, share):
    if scheme == "A":
        return Cam(share=share).upright_px(HER_TOP)
    return {"B": 57.0, "C": 48.0}[scheme]


def ppm_for_her(px, share):
    lo, hi = 5.0, 200.0
    for _ in range(70):
        m = (lo + hi) / 2
        if Cam(ppm=m, share=share).upright_px(HER_TOP) < px:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def scheme_rows():
    rows = []
    base = screen_extent(Cam())
    for sch in ("A", "B", "C"):
        for s in SHARES:
            px = her_scheme_px(sch, s)
            ppm = 30.0 if sch == "A" else ppm_for_her(px, s)
            e = screen_extent(Cam(ppm=ppm, share=s))
            rows.append(dict(scheme=sch, share=s, px=px, ppm=ppm, w=e["w_her"], depth=e["depth"], north=e["north"],
                             area=e["area"], dw=base["w_her"] - e["w_her"], dd=base["depth"] - e["depth"],
                             on1080=px * 3))
    return rows, base


def visible_height_at_feet(cam):
    """How tall an upright at her feet can be before it leaves the top of the picture."""
    _, sy_feet, _ = cam.project(np.array([cam.her[0], cam.her[1], cam.her[2]]))
    room = VIEW_H / 2.0 - sy_feet        # px from her feet up to the top edge
    return cam.height_for_px(room), room


def scale_table(R):
    rec = R["camera"]["recommended"]
    rec_cam = Cam(ppm=rec["ppm"], share=rec["share"])
    lines = []
    lines.append("| 编号 | 东西 | 高（米） | 宽（米） | 份额 0 | 份额 0.3 | 份额 0.5 | 份额 1.0 | 宽（像素，东西向） | 精灵（像素） | 推荐方案 C 下（份额 1.0、每米 32） | 备注 |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    cams = [Cam(share=s) for s in SHARES]
    xppm = cams[0].ground_ppm()[0]
    limits = [visible_height_at_feet(c)[0] for c in cams]
    rec_lim = visible_height_at_feet(rec_cam)[0]
    items = [("ch", c) for c in R["scale"]["characters"]] + [("ref", r) for r in R["scale"]["references"]]
    for kind, it in items:
        h = it.get("h_top", it["h"])
        w = it.get("w", 0.0)
        cols = []
        for c, lim in zip(cams, limits):
            if h > lim:
                cols.append("超出画面（只露下面 %.1f 米）" % lim)
            else:
                cols.append("%.0f" % c.upright_px(h))
        wpx = "%.0f" % (w * xppm) if w else "—"
        if kind == "ch":
            sprite = "%.0f" % rec_cam.upright_px(h)
        else:
            sprite = "—"
        recv = ("超出画面" if h > rec_lim else "%.0f" % rec_cam.upright_px(h))
        recw = rec_cam.ground_ppm()[0] * w if w else 0
        note = it.get("note", "")
        hh = ("%.2f" % h) if h < 10 else ("%.1f" % h)
        if kind == "ch" and it.get("h_top") != it.get("h"):
            hh = "%.2f（连%s %.2f）" % (it["h"], it["top"], it["h_top"])
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            it["id"], it["name"], hh, ("%.2f" % w) if w else "—", cols[0], cols[1], cols[2], cols[3], wpx, sprite,
            recv + ("（宽 %.0f）" % recw if recw else ""), note))
    head = []
    head.append("直立物体站在她脚下（焦点的地面）时在屏幕上占几个原生像素：相机 P3（竖直视野 38°、俯角 45°、焦点在她胸口），"
                "现在的相机每米 30 像素；按渲染器给的'她脚下'一列（份额 0 / 0.3 / 0.5 / 1.0 时每米 %.1f / %.1f / %.1f / %.1f 像素），"
                "高的东西按透视逐点投影（不是乘一个常数）。东西向的宽：她脚下每米 %.2f 像素（和份额无关）。" % tuple(
                    [c.upright_ppm_local() for c in cams] + [xppm]))
    head.append("精灵（人物卡片）不随投影缩放，任何深度都是屏幕整像素：'精灵'一列是推荐方案 C 下每个人物该画多少像素"
                "（份额 1.0、相机每米 32；她连笠 1.52 米 = %.0f 像素）。画面上沿离她脚下 %.0f 像素：份额 0 时站在她脚下的东西"
                "高过 %.1f 米就出画，份额 1.0 时 %.1f 米。" % (rec_cam.upright_px(HER_TOP), visible_height_at_feet(cams[0])[1],
                                                       limits[0], limits[3]))
    return "\n\n".join(head) + "\n\n" + "\n".join(lines)


def schemes_table():
    rows, base = scheme_rows()
    out = []
    out.append("现在：相机每米 30 像素，她 57 像素（1080p 上 171 像素），她脚下的地面一屏宽 %.1f 米、深 %.1f 米（往南 5.9、往北 %.1f），"
               "面积 %.0f 平方米（规则里按 23 × 21 = 483 平方米算一屏）。她连笠按 1.52 米。" % (base["w_her"], base["depth"], base["north"], base["area"]))
    out.append("")
    out.append("| 方案 | 份额 | 她（原生像素） | 1080p 上 | 相机每米像素 | 放大 | 一屏宽 × 深（米） | 比现在少 | 一屏面积 |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    names = {"A": "A 缩她（世界不动）", "B": "B 放大世界（她不动）", "C": "C 折中（她 48、世界略放大）"}
    for r in rows:
        out.append("| %s | %.1f | %.0f | %.0f | %.1f | ×%.2f | %.1f × %.1f | 宽少 %.1f、深少 %.1f | %.0f 平方米（%.0f%%） |" % (
            names[r["scheme"]], r["share"], r["px"], r["on1080"], r["ppm"], r["ppm"] / 30.0, r["w"], r["depth"],
            r["dw"], r["dd"], r["area"], 100 * r["area"] / base["area"]))
    return "\n".join(out)


def zone_table(R, T, W, rc):
    rec = R["camera"]["recommended"]
    e_rec = screen_extent(Cam(ppm=rec["ppm"], share=rec["share"]))
    out = ["| 分区 | 名称 | 面积（平方米） | 其中可走 | 折成屏数（按 483） | 推荐方案下的屏数（按 %.0f） | 主角 |" % e_rec["area"],
           "|---|---|---|---|---|---|---|"]
    tot = 0.0
    for z in R["zones"]:
        a = reg.poly_area(z["poly"])
        m = reg.points_in_poly(T.X, T.Y, z["poly"])
        walk = float((m & W.ok).sum() * T.cell * T.cell)
        tot += a if z["id"] != "ZN-01" and z["id"] != "ZN-02" else 0
        out.append("| %s | %s | %.0f | %.0f | %.1f | %.1f | %s |" % (z["id"], z["name"], a, walk, a / SCREEN_RULE_M2,
                                                                     a / e_rec["area"], z.get("protagonist") or "—"))
    realm = reg.poly_area(R["boundary"]["poly"])
    B = np.array(R["boundary"]["poly"])
    out.append("")
    out.append("结界（BD-01）面积 %.0f 平方米，外接框东西 %.0f 米 × 南北 %.0f 米；可走并连成一片的 %.0f 平方米。按 483 折 %.1f 屏，"
               "推荐方案下 %.1f 屏。" % (realm, B[:, 0].max() - B[:, 0].min(), B[:, 1].max() - B[:, 1].min(),
                                     rc["inside_walkable_m2"], realm / SCREEN_RULE_M2, realm / e_rec["area"]))
    return "\n".join(out)


PROTAGONISTS = [("TR-CAM-01", "大楠", "VW-03"), ("BL-MIN-01", "茅屋", "VW-01"), ("SG-MCK-01", "东门", "VW-02"),
                ("RK-CHO-01", "眺望岩", "VW-04")]


def protagonist_shape(R, pid):
    e = R["_index"][pid]
    if pid == "TR-CAM-01":
        return np.array(e["footprint"]["poly"])
    if pid == "SG-MCK-01":
        a, b = R["boundary"]["gates"][0]["between"]
        return np.array([a, b, [b[0], b[1] - 0.4], [a[0], a[1] - 0.4]])
    if pid == "BL-MIN-01":
        x, y = e["pos"]
        rw, rd = e["roof"]
        return np.array([[x - rw / 2, y - rd / 2], [x + rw / 2, y - rd / 2], [x + rw / 2, y + rd / 2], [x - rw / 2, y + rd / 2]])
    return np.array(e["footprint"]["poly"])


def spacing_table(R, T, views):
    from .plan import frustum_ground
    vmap = {v["id"]: v for v in views}
    out = ["| 主角 A | 主角 B | 中心距（米） | 最近边距（米） | 站在 A 的关键视点，B 进不进画面 | 站在 B 的关键视点，A 进不进画面 |",
           "|---|---|---|---|---|---|"]
    shapes = {p: protagonist_shape(R, p) for p, _, _ in PROTAGONISTS}
    frusta = {}
    for pid, name, vid in PROTAGONISTS:
        cam = vmap[vid]["cam"]
        frusta[pid] = np.array(frustum_ground(T, cam, step=4))
    for i in range(len(PROTAGONISTS)):
        for j in range(i + 1, len(PROTAGONISTS)):
            a, an, av = PROTAGONISTS[i]
            b, bn, bv = PROTAGONISTS[j]
            A, B = shapes[a], shapes[b]
            cd = float(np.hypot(*(A.mean(axis=0) - B.mean(axis=0))))
            # nearest edge distance (sampled)
            def dense(P):
                Q = np.concatenate([P, P[:1]])
                pts, _ = reg.resample(Q, 0.25)
                return pts[:, :2]
            dA, dB = dense(A), dense(B)
            d = np.min(np.hypot(dA[:, None, 0] - dB[None, :, 0], dA[:, None, 1] - dB[None, :, 1]))
            inA = reg.points_in_poly(dB[:, 0], dB[:, 1], frusta[a]).any()
            inB = reg.points_in_poly(dA[:, 0], dA[:, 1], frusta[b]).any()
            out.append("| %s %s | %s %s | %.1f | %.1f | %s | %s |" % (a, an, b, bn, cd, d, "进（✗）" if inA else "不进（✓）",
                                                                  "进（✗）" if inB else "不进（✓）"))
    return "\n".join(out)


def view_table(R, T, views):
    """For each key view: which of its must-see elements are inside the 640x360 picture (anchor and a point
    up the element) and not hidden by terrain; which must-hide elements are out."""
    out = ["| 视点 | 她站在 | 要看见的（在画面里） | 要藏住的（不在画面里） | 画面里的地面（往北 / 往南） |", "|---|---|---|---|---|"]
    for vw in views:
        cam = vw["cam"]
        def inside(eid):
            e = R["_index"].get(eid)
            if e is None:
                return None
            pts = []
            if e.get("kind") == "EDA" and e.get("pts"):
                bx, by = R["_index"][e["parent"]]["pos"]
                base = float(T.h(bx, by))
                for p in e["pts"]:
                    pts.append((p[0], p[1], p[2], p[2] - base))
            elif eid == "TR-CAM-01" or e.get("parent") == "TR-CAM-01" and not e.get("pts"):
                # the trunk's face toward the camera, from the ground up to the rope and beyond
                h0 = float(T.h(0.0, -3.6))
                for t in (0.5, 2.4, 4.0, 6.0):
                    pts.append((0.0, -3.7, h0 + t, t))
                    pts.append((-2.6, -2.6, h0 + t, t))
                    pts.append((2.6, -2.6, h0 + t, t))
            elif e.get("pos"):
                x, y = e["pos"]
                h0 = float(T.h(x, y))
                hgt = 1.0
                if isinstance(e.get("size"), list) and e["size"][2]:
                    hgt = min(e["size"][2], 3.0)
                if e.get("height"):
                    hgt = min(e["height"], 4.0)
                for t in (0.0, hgt * 0.5, hgt):
                    pts.append((x, y, h0 + t, t))
            elif e.get("pts"):
                base = None
                if e.get("parent"):
                    px_, py_ = R["_index"][e["parent"]]["pos"]
                    base = float(T.h(px_, py_))
                for p in e["pts"]:
                    x, y = p[0], p[1]
                    h0 = float(T.h(x, y))
                    if len(p) >= 3 and base is not None:
                        pts.append((x, y, p[2], p[2] - base))
                    else:
                        pts.append((x, y, h0, 0.0))
            elif e.get("poly"):
                for p in e["poly"]:
                    pts.append((p[0], p[1], float(T.h(p[0], p[1])), 0.0))
            for x, y, h, t in pts:
                sx, sy, d = cam.project(np.array([x, y, h]), lean_t=t)
                px, py = cam.to_pixels(sx, sy)
                if 0 <= px <= VIEW_W and 0 <= py <= VIEW_H and d > 0:
                    # terrain occlusion along the ray
                    C = cam.C
                    P = np.array([x, y, h + 0.2])
                    v = P - C
                    L = np.linalg.norm(v)
                    blocked = False
                    for k in np.linspace(0.05, 0.95, 40):
                        q = C + v * k
                        if q[2] < float(T.h(q[0], q[1])) - 0.05:
                            blocked = True
                            break
                    if not blocked:
                        return True
            return False
        see = ["%s%s" % (s, "" if inside(s) else "（✗不在）") for s in vw["see"]]
        hide = ["%s%s" % (s, "（✗进了画面）" if inside(s) else "") for s in vw["hide"]]
        e = screen_extent(cam)
        out.append("| %s %s | (%.1f, %.1f) | %s | %s | %.1f / %.1f 米 |" % (vw["id"], vw["name"], vw["her"][0], vw["her"][1],
                                                                       "、".join(see), "、".join(hide) or "—", e["north"], e["south"]))
    return "\n".join(out)


def all_tables(R, T, W, rc, views):
    parts = ["# 新手村 v4：生成的表（tools/design/village_plan.py 写的，不要手改）", "",
             "## 1. 比例表", "", scale_table(R), "",
             "## 2. 她的身高方案（她连笠 1.52 米）", "", schemes_table(), "",
             "## 3. 分区面积与屏数", "", zone_table(R, T, W, rc), "",
             "## 4. 主角之间的间距（推荐方案 C 下的 P3 画面，按地形求出的可见地面）", "", spacing_table(R, T, views), "",
             "## 5. 关键视点检查（推荐方案 C 下）", "", view_table(R, T, views), ""]
    return "\n".join(parts)
