"""The plan sheets: A site plan, B realm plan (IDs, crown projection, views), C walkability, D screens
and spacing. Each returns (Svg, width, height)."""
from __future__ import annotations

import math

import numpy as np

from . import plan as PL
from . import registry as reg
from . import svg as S
from . import walk as WK
from .p3 import Cam, screen_extent
from .svg import Svg, Frame, f, smooth_path

DATE = "2026-10-17"
STATUS = "设计稿・待用户批准（不进游戏）"


def _common_lines(R, scale_txt):
    return ["比例 %s　单位：米　坐标原点 = 大楠树干中心　h = 0 为峠顶" % scale_txt,
            "数据：docs/design/village/registry.json（%s）" % R["status"].split("，")[0],
            "生成：tools/design/village_plan.py　%s　%s" % (DATE, STATUS)]


def zone_layer(svg, fr, R, labels=True, wash=True):
    svg.layer("zones")
    washes = {"ZN-01": "#e8e0cc", "ZN-02": "#efe3c9", "ZN-03": "#f0dccc", "ZN-04": "#dfe6dd", "ZN-05": "#e9e1d6",
              "ZN-06": "#e1ead2", "ZN-07": "#d7e3cb", "ZN-08": "#efe6cf", "ZN-09": "#efe9cf", "ZN-10": "#dfe3d3"}
    for z in R["zones"]:
        if wash:
            svg.poly(fr.pts(z["poly"]), fill=washes.get(z["id"], "#eee"), fill_opacity=0.55, stroke="none")
    for z in R["zones"]:
        svg.poly(fr.pts(z["poly"]), fill="none", stroke=S.INK3, stroke_width=0.7, stroke_dasharray="6,2,1,2")


def zone_labels(svg, fr, R, offsets=None, cls="zone"):
    svg.layer("zone-labels")
    offsets = offsets or {}
    for z in R["zones"]:
        c = reg.poly_centroid(z["poly"])
        dx, dy = offsets.get(z["id"], (0, 0))
        u, v = fr(c[0] + dx, c[1] + dy)
        svg.text(u, v, "%s %s" % (z["id"], z["name"]), cls=cls, anchor="middle", halo=True)


def sequence_markers(svg, fr, R, size=8.5):
    """The approach as numbered stations (P2: a string of thresholds)."""
    svg.layer("sequence")
    seq = [("1", (44.0, -96.0), "九十九折"), ("2", (40.0, -50.0), "峠顶・道祖神"), ("3", (24.4, -44.4), "东门（道切り绳・雾）"),
           ("4", (21.6, -35.6), "切通：往下、窄、暗"), ("5", (13.0, -32.4), "过溪（石板桥）"), ("6", (10.4, -30.0), "石段下段"),
           ("7", (4.0, -26.6), "踊り場：无缘墓"), ("8", (10.4, -23.0), "石段上段 → 释放"), ("9", (4.5, -17.6), "真路 → 祠"),
           ("10", (5.6, -6.4), "磐座（禁足）")]
    prev = None
    for n, (x, y), lab in seq:
        if not fr.contains(x, y):
            prev = None
            continue
        u, v = fr(x, y)
        if prev:
            svg.line(prev[0], prev[1], u, v, stroke=S.VERMILION, stroke_width=0.8, stroke_dasharray="2,2", opacity=0.7)
        prev = (u, v)
    for n, (x, y), lab in seq:
        if not fr.contains(x, y):
            continue
        u, v = fr(x, y)
        svg.circle(u, v, size, fill=S.PAPER, stroke=S.VERMILION, stroke_width=1.3)
        svg.text(u, v + 3.3, n, cls="red", anchor="middle")
    return seq


def sheet_site(R, T, trees, views, fonts):
    """A 总平面图: the whole registry extent."""
    x0, y0, x1, y1 = R["coords"]["extent"]
    s = 5.0
    W, H = 1480, 1210
    fr = Frame(x0, y0, x1, y1, s, 46, 96)
    svg = Svg(W, H, "新手村 v4 总平面图")
    PL.defs(svg)
    svg.layer("base")
    svg.rect(0, 0, W, H, fill=S.PAPER)
    svg.rect(fr.u0, fr.v0, fr.w, fr.h, fill="#f7f4ec", stroke=S.INK, stroke_width=1.0)
    svg.defn('<clipPath id="mapclip"><rect x="%s" y="%s" width="%s" height="%s"/></clipPath>' % (f(fr.u0), f(fr.v0), f(fr.w), f(fr.h)))
    svg.add('<g clip-path="url(#mapclip)">')
    zone_layer(svg, fr, R, wash=True)
    svg.layer("hill")
    u, v, w, h, uri = PL.hillshade_image(T, fr, alpha=0.42)
    svg.image(u, v, w, h, uri, preserveAspectRatio="none", opacity=0.9)
    PL.draw_contours(svg, fr, T, interval=1.0, major=5.0, labels=True, minor_w=0.3, major_w=0.8)
    PL.draw_plantings(svg, fr, R, trees)
    PL.draw_water(svg, fr, R, T)
    PL.draw_cliffs(svg, fr, R, T)
    PL.draw_roads(svg, fr, R, detail=False)
    PL.draw_camphor(svg, fr, R)
    PL.draw_elements(svg, fr, R, detail=False)
    PL.draw_boundary(svg, fr, R, width=2.0)
    svg.layer("views")
    for vw in views:
        if vw["id"] in ("VW-01", "VW-02", "VW-03", "VW-04", "VW-05"):
            PL.draw_frustum(svg, fr, T, vw["cam"], vw["id"], fill_op=0.10)
    sequence_markers(svg, fr, R, size=7)
    zone_labels(svg, fr, R, cls="zone-s", offsets={"ZN-10": (-22, 10), "ZN-01": (14, -20), "ZN-07": (0, 4),
                                                   "ZN-04": (6, 4), "ZN-05": (-8, -3), "ZN-02": (3, 6), "ZN-03": (9, -1)})
    # landmark labels
    svg.layer("labels")
    for tid, (x, y), lab, dx, dy in [("TR-CAM-01", (0, 0), "大楠", 0, 30), ("BL-MIN-01", (-26, -3.8), "茅屋", 0, -22),
                                     ("RK-CHO-01", (-36.4, -41), "眺望岩", -10, 20), ("SG-MCK-01", (24.4, -42.5), "东门", 30, 4),
                                     ("SG-DOS-01", (36, -46.8), "道祖神", 26, -6), ("WA-FAL-01", (10.1, -45.6), "瀑布", -24, 12),
                                     ("ST-HAS-02", (20.4, -147.6), "石桥", 0, -14), ("SG-MCK-02", (-9, 21.1), "北门", 0, -12),
                                     ("SG-MCK-03", (-48.6, -28), "西南门", -6, -12)]:
        u, v = fr(x, y)
        svg.text(u + dx, v + dy, "%s %s" % (lab, tid), cls="lab-b", anchor="middle", halo=True)
    rd = R["_index"]["RD-KAI-01"]
    for b, (x, y) in rd["bends"].items():
        u, v = fr(x, y)
        svg.text(u + (10 if x > 40 else -10), v + 3, b, cls="lab-s", anchor=("start" if x > 40 else "end"), halo=True)
    svg.add("</g>")
    # frame furniture
    svg.layer("furniture")
    title_lines = _common_lines(R, "1:%d（屏幕 96 dpi 下）" % round(1000 / (s * 0.2646)))
    PL.title_block(svg, 46, 18, fr.w, "新手村 v4　总平面图", "峠旁的隐里：九十九折 → 峠顶 → 东门 → 结界（家・祠・大楠・眺望岩）", [], "图 A")
    px = fr.u0 + fr.w + 34
    py = 104
    svg.text(px, py, "图例", cls="head")
    items = [("head", "分区与边界", None),
             ("fill", "分区（ZN-01…10）", {"fill": "#e1ead2", "stroke": S.INK3, "dash": "6,2,1,2"}),
             ("line", "结界的边（门处断开）", {"stroke": S.VERMILION, "sw": 2.0, "dash": "10,3,2,3"}),
             ("line", "参道的顺序（①…⑩ 一串门槛）", {"stroke": S.VERMILION, "sw": 0.8, "dash": "2,2"}),
             ("fill", "P3 关键视点的地面视野", {"fill": S.SKY, "op": 0.25, "stroke": S.SKY}),
             ("head", "地形与水", None),
             ("line", "等高线 1 米（粗线 5 米）", {"stroke": "#7a6a55", "sw": 0.8}),
             ("cliff", "崖、陡坡（>35°，不可走）", {}),
             ("fill", "溪、泉、瀑布", {"fill": S.WATER, "stroke": S.WATER_EDGE}),
             ("head", "路（真・行・草）", None),
             ("fill", "真：切石延段（只到祠）", {"fill": "url(#shin)", "stroke": S.INK}),
             ("fill", "行：石段、延段、旧街道", {"fill": S.PATH_GYO, "stroke": S.INK2}),
             ("fill", "草：踩出的土路、根の道", {"fill": S.PATH_SO, "stroke": S.INK3, "dash": "2.2,1.6"}),
             ("steps", "石段（箭头朝上）", {}),
             ("head", "植物", None),
             ("tree", "杉、赤松（针叶）", {"kind": "SUG"}),
             ("tree", "杂木、枫、阔叶", {"kind": "KON"}),
             ("fill", "苔庭", {"fill": "url(#moss)"}),
             ("fill", "茅场（芒）", {"fill": "url(#susuki)"}),
             ("fill", "篠竹丛（结界的边，不可走）", {"fill": "url(#sasa)", "stroke": "#4e5f35"}),
             ("fill", "大楠的冠投影（虚线）", {"fill": "#6f8f5c", "op": 0.25, "stroke": "#3f5a33", "dash": "7,3,1.5,3"}),
             ("head", "构筑物", None),
             ("wall", "石垣（短线朝低的一侧）", {}),
             ("fill", "茅屋、祠", {"fill": "url(#thatch)", "stroke": S.INK}),
             ("dot", "地藏（红围嘴）、道祖神", {"fill": "#b8b1a3"}),
             ("dot", "褪色的朱漆灯杆（门槛的朱）", {"fill": S.VERMILION})]
    y = PL.legend(svg, px, py + 10, items)
    y += 14
    svg.text(px, y, "读图", cls="head")
    y += 18
    notes = ["1 九十九折　2 峠顶　3 东门　4 切通　5 过溪",
             "6 石段下段　7 墓台　8 石段上段　9 真路　10 磐座",
             "下・渡・上：门后先往下、过水、再往上（P2）。",
             "P3 相机朝北：往北走的路才会'揭示'（knowledge/29 §7），",
             "所以门后、石段、九十九折都朝北。",
             "大楠在北边，冠投影证明茅屋东头在冠下。",
             "B91…B99：九十九折的九个弯（她数到九十九）。"]
    for ln in notes:
        svg.text(px, y, ln, cls="note-s")
        y += 14
    PL.north_arrow(svg, px + 30, H - 120, 26)
    PL.scale_bar(svg, px + 80, H - 140, s, (0, 10, 20, 40, 60))
    yy = H - 82
    for ln in title_lines:
        svg.text(px, yy, ln, cls="note-s")
        yy += 13
    return svg, W, H


def sheet_realm(R, T, trees, views, fonts):
    """B 结界内平面图: the realm at a larger scale, every element with its ID."""
    x0, y0, x1, y1 = -54.0, -50.0, 32.0, 30.0
    s = 13.0
    fr = Frame(x0, y0, x1, y1, s, 40, 100)
    W, H = int(fr.u0 + fr.w + 470), int(fr.v0 + fr.h + 40)
    svg = Svg(W, H, "新手村 v4 结界内平面图")
    PL.defs(svg)
    svg.layer("base")
    svg.rect(0, 0, W, H, fill=S.PAPER)
    svg.rect(fr.u0, fr.v0, fr.w, fr.h, fill="#f7f4ec", stroke=S.INK, stroke_width=1.0)
    svg.defn('<clipPath id="mapclipB"><rect x="%s" y="%s" width="%s" height="%s"/></clipPath>' % (f(fr.u0), f(fr.v0), f(fr.w), f(fr.h)))
    svg.add('<g clip-path="url(#mapclipB)">')
    zone_layer(svg, fr, R, wash=True)
    svg.layer("hill")
    u, v, w, h, uri = PL.hillshade_image(T, fr, alpha=0.36)
    svg.image(u, v, w, h, uri, preserveAspectRatio="none", opacity=0.9)
    PL.draw_contours(svg, fr, T, interval=0.5, major=2.5, labels=True, minor_w=0.3, major_w=0.75)
    PL.draw_plantings(svg, fr, R, trees)
    PL.draw_water(svg, fr, R, T)
    PL.draw_cliffs(svg, fr, R, T)
    PL.draw_roads(svg, fr, R, detail=True)
    PL.draw_elements(svg, fr, R, detail=True)
    PL.draw_camphor(svg, fr, R)
    PL.draw_boundary(svg, fr, R, width=2.4)
    svg.layer("axes")
    # the one straight axis
    a, b = fr(4.5, -22.0), fr(4.5, -3.0)
    svg.line(a[0], a[1], b[0], b[1], stroke=S.VERMILION, stroke_width=0.8, stroke_dasharray="12,3,2,3")
    svg.text(b[0] + 4, b[1] - 2, "轴（SL-04）", cls="red")
    # sightlines
    for sl in R["sightlines"]:
        if sl["id"] in ("SL-01", "SL-03"):
            a, b = fr(*sl["from"]), fr(*sl["to"])
            svg.line(a[0], a[1], b[0], b[1], stroke=S.SKY, stroke_width=1.0, stroke_dasharray="4,2",
                     marker_end="url(#arrow-sky)")
            svg.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 4, "%s %s" % (sl["id"], sl["name"]), cls="lab-s",
                     anchor="middle", halo=True, fill=S.SKY)
    svg.layer("views")
    for vw in views:
        if fr.contains(vw["her"][0], vw["her"][1]):
            PL.draw_frustum(svg, fr, T, vw["cam"], vw["id"], fill_op=0.05, dash="5,2", width=0.9)
    sequence_markers(svg, fr, R, size=9)
    zone_labels(svg, fr, R, cls="zone", offsets={"ZN-10": (-30, 14), "ZN-07": (-6, 5), "ZN-06": (-6, -2), "ZN-05": (-2, -3.2),
                                                 "ZN-04": (5, 6), "ZN-08": (2, 6.5), "ZN-09": (6, 3), "ZN-03": (2, -6)})
    ids = None
    placed = PL.label_elements(svg, fr, R, ids=ids, cls="lab")
    svg.add("</g>")
    svg.layer("furniture")
    PL.title_block(svg, 40, 18, fr.w, "新手村 v4　结界内平面图（元素编号）", "家一带・神社结界・眺望岩：每个元素的编号见 registry.json", [], "图 B")
    px = fr.u0 + fr.w + 30
    py = 108
    svg.text(px, py, "图例", cls="head")
    items = [("line", "大楠冠的投影（树高 30 米，冠约 41 × 41 米）", {"stroke": "#3f5a33", "sw": 1.2, "dash": "7,3,1.5,3"}),
             ("fill", "冠的缺口'天窗'：正午光落在祠前", {"fill": S.PAPER, "stroke": "#3f5a33", "dash": "2,2"}),
             ("fill", "G 枝（可爬：顶面亮苔）", {"fill": "#8a6f55", "stroke": "#4f3d2c"}),
             ("fill", "南枝（头顶上方，不挡路）", {"fill": "#8a6f55", "op": 0.55, "stroke": "#4f3d2c", "dash": "2,1.5"}),
             ("line", "注连绳（白圈）", {"stroke": "#e6ddc6", "sw": 2.0}),
             ("line", "瑞垣（只围磐座）", {"stroke": "#6c4f3a", "sw": 2.0}),
             ("line", "道切り绳（门）", {"stroke": "#c9b27a", "sw": 2.2}),
             ("fill", "岩（磐座、眺望岩，同一种花岗岩）", {"fill": "url(#rockh)", "stroke": S.ROCK_EDGE}),
             ("wall", "石垣", {}),
             ("fill", "菜地", {"fill": "url(#plot)", "stroke": S.INK3}),
             ("line", "筧（竹水管）", {"stroke": "#6f8a4a", "sw": 1.0, "dash": "3,1.2"}),
             ("line", "视线、额缘（SL-*）", {"stroke": S.SKY, "sw": 1.0, "dash": "4,2"}),
             ("fill", "P3 视点的地面视野（VW-*）", {"fill": S.SKY, "op": 0.15, "stroke": S.SKY, "dash": "5,2"}),
             ("line", "唯一的直轴：手水 → 祠 → 磐座", {"stroke": S.VERMILION, "sw": 0.8, "dash": "12,3,2,3"})]
    y = PL.legend(svg, px, py + 10, items)
    y += 10
    svg.text(px, y, "冠投影与茅屋（用户要求的证明）", cls="head")
    y += 18
    cam = R["_index"]["TR-CAM-01"]
    xs = [p[0] for p in cam["crown"]]
    ys = [p[1] for p in cam["crown"]]
    house = R["_index"]["BL-MIN-01"]
    hx0 = house["pos"][0] - house["roof"][0] / 2
    hx1 = house["pos"][0] + house["roof"][0] / 2
    hy0 = house["pos"][1] - house["roof"][1] / 2
    hy1 = house["pos"][1] + house["roof"][1] / 2
    # fraction of the roof under the crown
    gx, gy = np.meshgrid(np.linspace(hx0, hx1, 60), np.linspace(hy0, hy1, 40))
    under = reg.points_in_poly(gx, gy, cam["crown"]).mean()
    lines = ["干径 %.1f 米（干围 %.1f 米），树高 %.0f 米。" % (cam["trunk_d"], cam["girth"], cam["height"]),
             "冠：东西 %.0f 米（%.1f … %.1f），南北 %.0f 米（%.1f … %.1f）。" % (max(xs) - min(xs), min(xs), max(xs), max(ys) - min(ys), min(ys), max(ys)),
             "茅屋屋顶 %.1f × %.1f 米，%.0f%% 在冠下（东头）。" % (house["roof"][0], house["roof"][1], under * 100),
             "树干中心到茅屋东檐 %.1f 米，到屋中心 %.1f 米：" % (math.hypot(hx1, house["pos"][1]), math.hypot(*house["pos"])),
             "比 P3 一屏的宽（约 22 米）还远，所以两个主角不同屏，",
             "冠却罩着家（'罩在德库树下的家'）。",
             "参照：蒲生のクス 干围 22.72 米、高 30.9 米；",
             "长太の大楠 冠东西 30 米、南北 35 米（干径 2.6 米）。",
             "同等干径的冠幅没有找到一手资料：冠幅是设计值。"]
    for ln in lines:
        svg.text(px, y, ln, cls="note-s")
        y += 14
    y += 8
    svg.text(px, y, "编号的写法", cls="head")
    y += 18
    for ln in ["类别-种类-序号：TR-CAM-01 = 树・樟・1 号（大楠）。",
               "部件加字母：TR-CAM-01G = 大楠的 G 枝。",
               "TR 树 PL 种植 RK 岩 ST 石作 BL 建筑 SG 神事民俗",
               "PR 道具 WA 水 RD 路 TE 地形 AN 动物 FX 效果",
               "ZN 分区 VW 视点 SL 视线。全部字段见 registry.json。"]:
        svg.text(px, y, ln, cls="note-s")
        y += 14
    PL.north_arrow(svg, px + 30, H - 110, 24)
    PL.scale_bar(svg, px + 80, H - 128, s, (0, 5, 10, 20))
    yy = H - 74
    for ln in _common_lines(R, "1:%d" % round(1000 / (s * 0.2646))):
        svg.text(px, yy, ln, cls="note-s")
        yy += 13
    return svg, W, H


def sheet_walk(R, T, trees, W_, fonts, rc):
    """C 可走与不可走: every unwalkable cell coloured by its cause; the realm check."""
    import base64
    import io
    from PIL import Image
    x0, y0, x1, y1 = -54.0, -50.0, 32.0, 30.0
    s = 11.0
    fr = Frame(x0, y0, x1, y1, s, 40, 100)
    W, H = int(fr.u0 + fr.w + 470), int(fr.v0 + fr.h + 40)
    svg = Svg(W, H, "新手村 v4 可走与不可走")
    PL.defs(svg)
    svg.layer("base")
    svg.rect(0, 0, W, H, fill=S.PAPER)
    svg.rect(fr.u0, fr.v0, fr.w, fr.h, fill="#f7f4ec", stroke=S.INK, stroke_width=1.0)
    svg.defn('<clipPath id="mapclipC"><rect x="%s" y="%s" width="%s" height="%s"/></clipPath>' % (f(fr.u0), f(fr.v0), f(fr.w), f(fr.h)))
    svg.add('<g clip-path="url(#mapclipC)">')
    # raster of causes
    j0 = int((x0 - T.x0) / T.cell)
    j1 = int((x1 - T.x0) / T.cell) + 1
    i0 = int((y0 - T.y0) / T.cell)
    i1 = int((y1 - T.y0) / T.cell) + 1
    C = W_.cause[i0:i1, j0:j1][::-1]
    comp = rc["comp"][i0:i1, j0:j1][::-1]
    rgba = np.zeros(C.shape + (4,), dtype=np.uint8)
    def hexrgb(h):
        return tuple(int(h[k:k + 2], 16) for k in (1, 3, 5))
    for c, col in WK.CAUSE_COLORS.items():
        m = C == c
        r, g, b = hexrgb(col)
        rgba[m] = (r, g, b, 120)
    m = (C == WK.OK) & comp
    rgba[m] = (236, 228, 205, 255)
    m = (C == WK.OK) & ~comp
    rgba[m] = (246, 243, 236, 255)
    wm = W_.walk_mask[i0:i1, j0:j1][::-1] & (C == WK.OK)
    rgba[wm] = (214, 196, 150, 255)
    im = Image.fromarray(rgba, "RGBA").resize((C.shape[1] * 2, C.shape[0] * 2), Image.NEAREST)
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    u, v = fr(x0 - T.cell / 2, y1 + T.cell / 2)
    svg.image(u, v, C.shape[1] * T.cell * s, C.shape[0] * T.cell * s,
              "data:image/png;base64," + base64.b64encode(b.getvalue()).decode(), preserveAspectRatio="none",
              style="image-rendering:pixelated")
    PL.draw_contours(svg, fr, T, interval=1.0, major=5.0, labels=False, minor_w=0.25, major_w=0.6)
    svg.layer("overlays")
    # the climb surface of the G limb
    L = R["_index"]["TR-CAM-01G"]
    svg.path(smooth_path(fr.pts([p[:2] for p in L["pts"]])), fill="none", stroke="#5f9a2a", stroke_width=5.0,
             stroke_linecap="round", opacity=0.9)
    a = fr(*L["pts"][-1][:2])
    svg.text(a[0] - 6, a[1] + 16, "G 枝：从落地的一头走上去（climb）", cls="lab-b", anchor="end", halo=True, fill="#3f6a1a")
    PL.draw_boundary(svg, fr, R, width=2.2)
    if rc["leak_cells"]:
        for x, y in rc["leak_pts"][::4]:
            u, v = fr(x, y)
            svg.circle(u, v, 2, fill="#ff00aa")
    for g in R["boundary"]["gates"]:
        (ax, ay), (bx, by) = g["between"]
        u, v = fr((ax + bx) / 2, (ay + by) / 2)
        svg.text(u, v - 10, "%s %s" % (g["name"], g["id"]), cls="lab-b", anchor="middle", halo=True, fill=S.VERMILION)
    svg.add("</g>")
    svg.layer("furniture")
    PL.title_block(svg, 40, 18, fr.w, "新手村 v4　可走与不可走", "碰撞和画面来自同一份数据：每一块不能走的地方都有看得见的原因", [], "图 C")
    px = fr.u0 + fr.w + 30
    py = 108
    svg.text(px, py, "图例（不可走的原因）", cls="head")
    items = []
    for c in (WK.SLOPE, WK.WATER, WK.THICKET, WK.WALL, WK.SOLID, WK.TREE, WK.BUILDING):
        items.append(("fill", WK.CAUSE_NAMES[c], {"fill": WK.CAUSE_COLORS[c], "op": 0.5}))
    items += [("head", "可走", None),
              ("fill", "结界里连成一片的可走地面", {"fill": "#ece4cd", "stroke": S.INK3}),
              ("fill", "人修的可走面：石段、桥、缘侧、台", {"fill": "#d6c496", "stroke": S.INK3}),
              ("fill", "结界外（或孤立）的可走地面", {"fill": "#f6f3ec", "stroke": S.INK3}),
              ("line", "可爬：G 枝（顶面亮苔）", {"stroke": "#5f9a2a", "sw": 5.0}),
              ("line", "结界的边（门处断开）", {"stroke": S.VERMILION, "sw": 2.0, "dash": "10,3,2,3"})]
    y = PL.legend(svg, px, py + 10, items)
    y += 12
    svg.text(px, y, "检查（脚本自动做）", cls="head")
    y += 18
    area = rc["inside_walkable_m2"]
    lines = ["把三个门关上，从院子开始往外漫：",
             "结界里连成一片的可走地面 %.0f 平方米；" % area,
             "漫出结界边 1.5 米以外的格子：%d 个。" % rc["leak_cells"],
             ("→ 结界的每一段边都由看得见的东西封住（崖、陡坡、" if rc["leak_cells"] == 0 else "→ 有漏洞（洋红点）：那里需要空气墙，要改布局。"),
             ("篠竹丛、溪谷、石垣），不需要空气墙（G5R3-48）。" if rc["leak_cells"] == 0 else ""),
             "坡度上限 35°；溪面宽于 0.8 米不可走；",
             "树干、岩、垣、屋按 registry 的 footprint 实心。",
             "G5R3-48 点名的三处穿模，数据里都有了面：",
             "G 枝（climb）、茅屋前的沓脱石和缘侧（walk）、",
             "过溪的石板桥（walk）。北面原来的小桥取消（水改道）。"]
    for ln in lines:
        if ln:
            svg.text(px, y, ln, cls="note-s")
            y += 14
    PL.north_arrow(svg, px + 30, H - 110, 24)
    PL.scale_bar(svg, px + 80, H - 128, s, (0, 5, 10, 20))
    yy = H - 74
    for ln in _common_lines(R, "1:%d" % round(1000 / (s * 0.2646))):
        svg.text(px, yy, ln, cls="note-s")
        yy += 13
    return svg, W, H
