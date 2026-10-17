#!/usr/bin/env python3
"""Draw the 新手村 v4 design set from docs/design/village/registry.json.

  python3 tools/design/village_plan.py --fonts /path/to/fontdir [--out docs/design/village] [--only plan,views,scale,tables]

Writes (into --out):
  plan_site.svg/.png      图 A 总平面图
  plan_realm.svg/.png     图 B 结界内平面图（元素编号、冠投影、视点）
  plan_walk.svg/.png      图 C 可走与不可走（原因上色、结界封闭检查）
  plan_screens.svg/.png   图 D 屏数与主角间距
  view_0N_*.svg/.png      P3 关键视角（推荐的比例方案下）
  scale_*.png, scale_sheet.svg/.png   她的身高方案对照
  tables.md               比例表、分区面积表、视点检查（设计说明引用它）
Fonts: see vd/fonts.py (OFL, from npm tarballs, SHA-256 checked, not in the repo).
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from vd import registry as reg  # noqa: E402
from vd import terrain as ter  # noqa: E402
from vd import walk as wk  # noqa: E402
from vd.export import svg_to_png  # noqa: E402
from vd.fonts import Fonts  # noqa: E402
from vd.p3 import Cam  # noqa: E402


def keep_out_factory(R):
    def ko(X, Y):
        d = reg.all_road_distance(R, X, Y)
        bad = d < 1.0
        for w in R["water"]:
            if "pts" in w:
                bad |= reg.dist_to_polyline(X, Y, [p[:2] for p in w["pts"]]) < 1.6
        for e in R["elements"]:
            if e["id"] in ("BL-MIN-01", "BL-HOK-01"):
                x, y = e["pos"]
                bad |= (abs(X - x) < 6) & (abs(Y - y) < 5)
        return bad
    return ko


def make_views(R, T, ppm, share):
    out = []
    for vw in R["views"]:
        x, y = vw["her"]
        cam = Cam(ppm=ppm, share=share, her=(x, y, float(T.h(x, y))))
        d = dict(vw)
        d["cam"] = cam
        out.append(d)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True, help="directory holding the Noto Serif SC / Sans SC TTFs")
    ap.add_argument("--out", default=str(reg.REPO / "docs" / "design" / "village"))
    ap.add_argument("--only", default="plan,views,scale,tables")
    ap.add_argument("--scale", type=float, default=2.0, help="PNG device scale")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    only = set(a.only.split(","))
    t0 = time.time()
    R = reg.load()
    fonts = Fonts(a.fonts)
    T = ter.Terrain(R)
    ko = keep_out_factory(R)
    trees = {pl["id"]: reg.scatter_planting(pl, R, ko) for pl in R["plantings"]}
    lowered, removed = reg.p3_south_low(trees, R, T)
    law = dict(lowered=lowered, removed=removed, kept=sum(len(v) for v in trees.values()))
    W = wk.Walk(R, T, trees)
    rc = W.realm_check()
    rec = R["camera"]["recommended"]
    views = make_views(R, T, rec["ppm"], rec["share"])
    print("terrain + walk %.1fs; realm leak cells %d; inside walkable %.0f m2; P3 law: lowered %d, removed %d, kept %d trees" % (
        time.time() - t0, rc["leak_cells"], rc["inside_walkable_m2"], lowered, removed, law["kept"]))

    def emit(name, svg, w, h):
        p = out / (name + ".svg")
        svg.save(p, fonts)
        svg_to_png(p, out / (name + ".png"), w, h, a.scale)
        print("wrote", p.name, "+ png", "(%.1fs)" % (time.time() - t0))

    if "plan" in only:
        from vd import sheets
        svg, w, h = sheets.sheet_site(R, T, trees, views, fonts)
        emit("plan_site", svg, w, h)
        svg, w, h = sheets.sheet_realm(R, T, trees, views, fonts)
        emit("plan_realm", svg, w, h)
        svg, w, h = sheets.sheet_walk(R, T, trees, W, fonts, rc)
        emit("plan_walk", svg, w, h)
        if hasattr(sheets, "sheet_screens"):
            svg, w, h = sheets.sheet_screens(R, T, trees, views, fonts)
            emit("plan_screens", svg, w, h)
    if "views" in only:
        try:
            from vd import views as VV
        except ImportError:
            VV = None
        if VV:
            for vw in views:
                if vw["id"] in ("VW-01", "VW-02", "VW-03", "VW-04", "VW-05", "VW-06", "VW-07"):
                    svg, w, h = VV.sheet_view(R, T, trees, vw, fonts)
                    emit("view_%s" % vw["id"].split("-")[1] + "_" + VV.SLUG.get(vw["id"], ""), svg, w, h)
    if "scale" in only:
        try:
            from vd import lineup as LU
        except ImportError:
            LU = None
        if LU:
            LU.make_all(R, out, fonts, emit)
    if "tables" in only:
        try:
            from vd import tables as TB
        except ImportError:
            TB = None
        if TB:
            (out / "tables.md").write_text(TB.all_tables(R, T, W, rc, views, law), encoding="utf-8")
            print("wrote tables.md")
    print("done %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
