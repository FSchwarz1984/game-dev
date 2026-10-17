"""Her height schemes, drawn at the settled lean share 1.0: the game as it is now (57 px at PPM 30, for
reference) and the schemes A (shrink her), B (enlarge the world), C (between). For each, the P3 camera
renders a line-up at her feet on a native 640x360 frame -- a stone lantern, a door in a plastered wall,
her card, four stone steps, a hen, a sitting cat and a 2 m post banded every 0.5 m -- then the same frame
at x3 (a 1080p screen). The world objects are massing, projected exactly; her card is drawn texel for
pixel at the scheme's height (cards do not scale with the projection)."""
from __future__ import annotations

import base64
import io
import math

import numpy as np
from PIL import Image

from . import svg as S
from . import views as V
from .p3 import Cam, SHARE, VIEW_W, VIEW_H, screen_extent
from .svg import Svg, f
from .tables import HER_TOP, her_scheme_px, scheme_ppm

OBJ = [  # name, x, height (m) for the labels; her nearest neighbours are the ones the user named
    ("门（门洞 1.79）", -2.9, 2.13), ("鸡", -1.25, 0.42), ("她", 0.0, HER_TOP), ("猫（坐）", 1.05, 0.32),
    ("石段 4 级", 2.45, 0.64), ("石灯笼", 4.3, 1.52), ("标尺 2 米", 5.7, 2.0)]
X = {name.split("（")[0]: x for name, x, h in OBJ}


def lineup_mesh():
    m = V.Mesh()
    ground = (196, 186, 150)
    m.add([(-60, -30, 0), (60, -30, 0), (60, 60, 0)], ground, 0, None)
    m.add([(-60, -30, 0), (60, 60, 0), (-60, 60, 0)], ground, 0, None)
    k = 10
    # stone lantern
    x = X["石灯笼"]
    V.box(m, x, 0.2, 0, 0.7, 0.7, 0.35, V.COL["stone"], k, base=0.0)
    V.cylinder(m, x, 0.2, 0.35, 0.9, 0.12, V.COL["stone"], k, n=6, base=0.0)
    V.box(m, x, 0.2, 0.9, 0.45, 0.45, 0.32, V.COL["stone"], k, base=0.0)
    V.cone(m, x, 0.2, 1.22, 1.52, 0.5, V.COL["stone"], k, n=6, base=0.0)
    # plastered wall with a doorway (sill 0.34, opening 0.94 x 1.79, lintel 2.13), eave line
    k = 11
    xd = X["门"]
    V.box(m, xd, 0.45, 0, 2.4, 0.25, 2.5, V.COL["wall"], k, base=0.0)
    V.box(m, xd, 0.31, 0.34, 0.94, 0.03, 1.79, (52, 44, 38), 12, base=0.0)
    V.box(m, xd, 0.30, 0.0, 1.1, 0.06, 0.34, V.COL["wood"], 13, base=0.0)
    # four steps going north
    k = 14
    for i in range(4):
        V.box(m, X["石段 4 级"], 0.18 + 0.36 * i + (0.36 * (3 - i)) / 2, 0.0, 1.4, 0.36 * (4 - i), 0.16 * (i + 1) - 0.0,
              V.COL["stone"], k + i, base=None)
    # hen and cat
    x = X["鸡"]
    V.ellipsoid(m, x, 0.0, 0.2, 0.2, 0.12, 0.14, (156, 104, 62), 20, n=8, k_=4, base=0.0)
    V.ellipsoid(m, x + 0.16, 0.0, 0.36, 0.07, 0.06, 0.07, (156, 104, 62), 20, n=6, k_=3, base=0.0)
    V.box(m, x + 0.17, 0.0, 0.42, 0.06, 0.02, 0.05, (200, 40, 36), 20, base=0.0)
    x = X["猫"]
    V.ellipsoid(m, x, 0.0, 0.13, 0.15, 0.12, 0.13, (92, 84, 76), 21, n=8, k_=4, base=0.0)
    V.ellipsoid(m, x, -0.05, 0.27, 0.08, 0.08, 0.07, (92, 84, 76), 21, n=6, k_=3, base=0.0)
    # 2 m post banded every 0.5 m
    for i in range(4):
        col = (40, 36, 34) if i % 2 == 0 else (236, 232, 222)
        V.box(m, X["标尺 2 米"], 0.0, 0.5 * i, 0.1, 0.1, 0.5, col, 30 + i, base=0.0)
    return m


def pixel_girl(img, fx, fy, H):
    """Her card at native resolution, H px tall, feet at (fx, fy): straw hat, black hair, white haori,
    a red cord, indigo hakama. Integer pixels; no scaling."""
    a = np.asarray(img).copy()
    H = int(round(H))
    def put(x0, y0, x1, y1, c):
        x0, x1 = int(round(x0)), int(round(x1))
        y0, y1 = int(round(y0)), int(round(y1))
        a[max(y0, 0):max(y1, 0), max(x0, 0):max(x1, 0)] = c
    cx = int(round(fx))
    base = int(round(fy))
    hat_h = max(3, round(H * 0.15))
    head_h = max(3, round(H * 0.2))
    body_h = max(4, round(H * 0.44))
    leg_h = H - hat_h - head_h - body_h
    hat_w = max(5, round(H * 0.46))
    head_w = max(3, round(H * 0.24))
    body_w = max(4, round(H * 0.32))
    y = base - H
    ink = (34, 30, 30)
    # hat (a flat cone): rows widen to the brim
    for r in range(hat_h):
        w = max(1, round(hat_w * (r + 1) / hat_h))
        put(cx - w / 2 - 1, y + r, cx + w / 2 + 1, y + r + 1, ink)
        put(cx - w / 2, y + r, cx + w / 2, y + r + 1, (226, 214, 176))
    y += hat_h
    put(cx - head_w / 2 - 1, y, cx + head_w / 2 + 1, y + head_h, ink)
    put(cx - head_w / 2, y, cx + head_w / 2, y + head_h, (40, 34, 44))
    put(cx - head_w / 2 + 1, y + head_h // 3, cx + head_w / 2 - 1, y + head_h - 1, (232, 200, 170))
    y += head_h
    put(cx - body_w / 2 - 1, y, cx + body_w / 2 + 1, y + body_h, ink)
    put(cx - body_w / 2, y, cx + body_w / 2, y + body_h, (238, 234, 224))
    put(cx - body_w / 2, y + body_h // 2, cx + body_w / 2, y + body_h // 2 + max(1, H // 30), (180, 60, 60))
    y += body_h
    put(cx - body_w * 0.36 - 1, y, cx + body_w * 0.36 + 1, base, ink)
    put(cx - body_w * 0.36, y, cx + body_w * 0.36, base - 1, (52, 56, 84))
    return Image.fromarray(a)


def render_scheme(scheme, share=SHARE):
    px = her_scheme_px(scheme, share)
    ppm = scheme_ppm(scheme, share)
    cam = Cam(ppm=ppm, share=share, her=(0.0, 0.0, 0.0))
    m = lineup_mesh()
    img, zbuf, ibuf = V.render(m, cam, ss=1)
    sx, sy, _ = cam.project(np.array([0.0, 0.0, 0.0]))
    fx, fy = cam.to_pixels(sx, sy)
    im = pixel_girl(Image.fromarray(img), fx, fy, round(px))
    labels = []
    for name, x, h in OBJ:
        if name == "她":
            labels.append((name, fx, fy, h, round(px)))
            continue
        bx, by = cam.to_pixels(*cam.project(np.array([x, 0.0, 0.0]))[:2])
        hp = cam.upright_px(h, at=(x, 0.0), base_h=0.0)
        labels.append((name, bx, by, h, hp))
    return im, cam, px, ppm, labels


SCHEMES = ("now", "A", "B", "C")


def make_all(R, out, fonts, emit):
    row = []
    for sch in SCHEMES:
        im, cam, px, ppm, labels = render_scheme(sch)
        im.save(out / ("scale_%s.png" % sch))
        im.resize((VIEW_W * 3, VIEW_H * 3), Image.NEAREST).save(out / ("scale_%s_x3.png" % sch))
        row.append((sch, SHARE, im, cam, px, ppm, labels))
    svg, w, h = sheet(row)
    emit("scale_sheet", svg, w, h)


NAMES = {"now": "现在（参照）：她 57 像素、世界每米 30", "A": "A　缩她（世界不动）", "B": "B　放大世界（她不动）",
         "C": "C　折中（推荐）"}


def sheet(row):
    fw, fh = VIEW_W, VIEW_H
    gap = 26
    n = len(row)
    W = 40 + n * fw + (n - 1) * gap + 40
    top = 120
    zoom_h = 270
    H = top + (fh + 150 + zoom_h + 40) + 150
    svg = Svg(W, H, "新手村 v4 她的身高方案对照")
    svg.layer("base")
    svg.rect(0, 0, W, H, fill=S.PAPER)
    from . import plan as PL
    PL.title_block(svg, 40, 18, W - 80, "她的身高：三个方案（后倾份额 1.0 下）",
                   "她和石灯笼、门、石段、鸡、猫、2 米标尺并排；上：原生 640 × 360；下：她周围放大 3 倍（1080p 屏幕上的真实大小）",
                   [], "比例方案")
    y0 = top
    for i, (sch, sh, im, cam, px, ppm, labels) in enumerate(row):
        u = 40 + i * (fw + gap)
        b = io.BytesIO()
        im.save(b, "PNG")
        uri = "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
        svg.image(u, y0, fw, fh, uri, preserveAspectRatio="none", style="image-rendering:pixelated")
        svg.rect(u, y0, fw, fh, fill="none", stroke=(S.VERMILION if sch == "C" else S.INK),
                 stroke_width=(2.4 if sch == "C" else 1.0))
        for j, (name, bx, by, hm, hp) in enumerate(labels):
            dy = 0 if j % 2 == 0 else 26
            svg.line(u + bx, y0 + by + 2, u + bx, y0 + by + 14 + dy, stroke=S.INK2, stroke_width=0.5)
            svg.text(u + bx, y0 + by + 24 + dy, name, cls="lab-s", anchor="middle", halo=True)
            if name == "她":
                svg.text(u + bx, y0 + by + 34 + dy, "合 %.2f 米 %d 像素" % (cam.height_for_px(hp), round(hp)), cls="lab-s",
                         anchor="middle", halo=True)
            else:
                svg.text(u + bx, y0 + by + 34 + dy, "%.2f 米 %d 像素" % (hm, round(hp)), cls="lab-s", anchor="middle", halo=True)
        e = screen_extent(cam)
        lines = [NAMES[sch],
                 "她 %d 像素（1080p 上 %d），在世界里合 %.2f 米" % (round(px), round(px) * 3, cam.height_for_px(px)),
                 "相机每米 %.1f 像素（×%.2f）；一屏的地面 %.1f × %.1f 米" % (ppm, ppm / 30.0, e["w_her"], e["depth"])]
        yy = y0 + fh + 20
        for k, ln in enumerate(lines):
            svg.text(u, yy, ln, cls=("note-b" if k == 0 else "note-s"))
            yy += 15
        # x3 crop around her
        crop_w, crop_h = fw // 3, zoom_h // 3
        fx, fy = labels[2][1], labels[2][2]
        cx0 = int(max(0, min(VIEW_W - crop_w, fx - crop_w / 2)))
        cy0 = int(max(0, min(VIEW_H - crop_h, fy - crop_h * 0.72)))
        crop = im.crop((cx0, cy0, cx0 + crop_w, cy0 + crop_h)).resize((crop_w * 3, crop_h * 3), Image.NEAREST)
        b = io.BytesIO()
        crop.save(b, "PNG")
        zu, zv = u, yy + 6
        svg.image(zu, zv, crop_w * 3, crop_h * 3, "data:image/png;base64," + base64.b64encode(b.getvalue()).decode(),
                  preserveAspectRatio="none", style="image-rendering:pixelated")
        svg.rect(zu, zv, crop_w * 3, crop_h * 3, fill="none", stroke=S.INK2, stroke_width=0.8)
        svg.text(zu + 4, zv + crop_h * 3 - 6, "×3（1080p 上一屏的 1/3 宽）", cls="lab-s", halo=True)
    y0 += fh + 150 + zoom_h + 40
    now = row[0][3]
    notes = ["读法：方框里的世界物体按 P3 透视逐点投影（直立物体按份额 1.0 后倾）；她是一张不随投影缩放的卡片，按方案画成整像素高。",
             "现在：她 57 像素、世界每米 30，在她脚下合 %.2f 米——比门洞（1.79 米）还高，是站着的母鸡的 4.5 倍、坐猫的 6 倍：这就是'像个巨人'（G5R3-54）。"
             % now.height_for_px(57),
             "A、B、C 都让她回到连笠 1.52 米（比婆婆矮 7 厘米、比门洞矮 27 厘米，母鸡的 3.6 倍）；差别只在屏幕上她多大、一屏装多少地。",
             "推荐 C：她 48 像素（1080p 上 144；用户喜欢的 0.2 版是 156），相机每米 32（宪章允许的 28–32 的上限），一屏只少 7%。"]
    yy = y0 - 10
    for ln in notes:
        svg.text(40, yy, ln, cls="note-s")
        yy += 16
    return svg, W, H
