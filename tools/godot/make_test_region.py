#!/usr/bin/env python3
# Writes the INTERNAL placeholder test region of the Godot project (never shown to the user, P-1):
#   python3 -I tools/godot/make_test_region.py            -> godot/world/regions/test/
# It exercises the ground model, not the art: terraces at 0.5 m steps (0, 0.5, 1.0, 1.5 m),
# vertical cliffs between them, two N-S staircases cut into the cliffs (docs/knowledge/15), a dirt
# path that changes level only on the stairs, a pond with shallow and deep water, a windy patch.
#
# Outputs
#   logic.png   RGB8, one pixel per 0.25 m cell: R*256+G = ground height in centimetres,
#               B = material id (world/region_data.gd MATERIALS). Imported as an Image (lossless).
#   ground.png  crude 3/4 art drawn from the same mask: ground at screen y = 20 (z - h), a
#               south-facing cliff face under every drop, stair treads and risers.
#   region.json size, cell size, art offset, spawn, entities, zones and camera shots.
import json
import math
import os
import random

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "godot", "world", "regions", "test")
PPM = 20
CELL = 0.25
W_M, D_M = 32.0, 24.0
NX, NZ = int(W_M / CELL), int(D_M / CELL)
TOP = 40  # art pixels above world z = 0 (the plateau is 1.5 m = 30 px high)

# material ids (keep in sync with world/region_data.gd)
VOID, GRASS, DIRT, STONE, STAIRS, WATER, DEEP, CLIFF = 0, 1, 2, 3, 4, 5, 6, 7

COLORS = {
    GRASS: (88, 104, 60), DIRT: (122, 100, 72), STONE: (128, 124, 112), STAIRS: (138, 132, 118),
    WATER: (64, 92, 110), DEEP: (42, 64, 82), VOID: (20, 18, 24), CLIFF: (96, 86, 74),
}


def build():
    h = [[0.0] * NX for _ in range(NZ)]
    m = [[GRASS] * NX for _ in range(NZ)]
    for j in range(NZ):
        z = (j + 0.5) * CELL
        for i in range(NX):
            x = (i + 0.5) * CELL
            if z < 8.0:
                h[j][i] = 1.5 if x < 20.0 else 1.0
            elif z < 14.0:
                h[j][i] = 0.5
            # the path: N-S through every level, and a branch east on the middle terrace
            if 9.5 <= x < 11.0 or (11.0 <= x < 15.5 and 10.5 <= z < 12.0):
                m[j][i] = DIRT
            # pond on the lowest level
            ex, ez = (x - 4.5) / 2.6, (z - 18.5) / 2.0
            if ex * ex + ez * ez < 1.0:
                m[j][i] = WATER
                if ex * ex * 4 + ez * ez * 4 < 1.0:
                    m[j][i] = DEEP
            # staircase 1: level 0 -> 0.5 m, cut into the middle terrace (z 13..14)
            if 9.5 <= x < 11.0 and 13.0 <= z < 14.0:
                row = int((14.0 - z) / CELL)  # 0 at the bottom (south) row
                h[j][i] = 0.125 * (row + 1)
                m[j][i] = STAIRS
            # staircase 2: 0.5 m -> 1.5 m, cut into the plateau (z 6..8)
            if 9.5 <= x < 11.0 and 6.0 <= z < 8.0:
                row = int((8.0 - z) / CELL)
                h[j][i] = 0.5 + 0.125 * (row + 1)
                m[j][i] = STAIRS
    return h, m


def write_logic(h, m):
    img = Image.new("RGB", (NX, NZ))
    px = img.load()
    for j in range(NZ):
        for i in range(NX):
            cm = int(round(h[j][i] * 100))
            px[i, j] = (cm >> 8, cm & 255, m[j][i])
    img.save(os.path.join(OUT, "logic.png"))


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def write_art(h, m):
    rnd = random.Random(5)
    w, ht = int(W_M * PPM), int(D_M * PPM) + TOP
    img = Image.new("RGBA", (w, ht), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cp = int(CELL * PPM)
    for j in range(NZ):  # north to south: later rows cover what they hide
        for i in range(NX):
            hh, mat = h[j][i], m[j][i]
            x0 = i * cp
            y0 = int(round(j * cp - hh * PPM)) + TOP
            base = COLORS[mat]
            for yy in range(cp):
                for xx in range(cp):
                    k = 0.9 + rnd.random() * 0.2
                    if mat == STAIRS and yy == 0:
                        k *= 1.12  # the tread's front edge catches the light
                    img.putpixel((x0 + xx, y0 + yy), shade(base, k) + (255,))
            # south-facing face down to the next lower cell (cliff or stair riser)
            hs = h[j + 1][i] if j + 1 < NZ else 0.0
            if hs < hh - 1e-6:
                face_h = int(round((hh - hs) * PPM))
                top = y0 + cp
                rock = COLORS[STAIRS] if mat == STAIRS else COLORS[CLIFF]
                for yy in range(face_h):
                    t = yy / max(1, face_h - 1)
                    k = 0.78 - 0.25 * t + (0.08 if (yy + i // 3) % 7 == 0 else 0.0)
                    for xx in range(cp):
                        img.putpixel((x0 + xx, top + yy), shade(rock, k * (0.95 + rnd.random() * 0.1)) + (255,))
                if mat != STAIRS:  # grass lip on the cliff top
                    d.line([(x0, top), (x0 + cp - 1, top)], fill=shade(COLORS[GRASS], 1.25) + (255,))
            # east/west drops: a thin dark side edge
            for di in (-1, 1):
                ii = i + di
                if 0 <= ii < NX and h[j][ii] < hh - 0.3:
                    xe = x0 + (cp - 1 if di > 0 else 0)
                    d.line([(xe, y0), (xe, y0 + cp - 1)], fill=shade(COLORS[CLIFF], 0.6) + (255,))
    img.save(os.path.join(OUT, "ground.png"))


REGION = {
    "id": "test",
    "label": "internal test region (placeholder, never shipped as content)",
    "size_m": [W_M, D_M],
    "cell_m": CELL,
    "max_step_m": 0.3,
    "logic": "logic.png",
    "art": "ground.png",
    "art_offset_px": [0, -TOP],
    "spawn": {"x": 10.25, "z": 22.5, "face": "back"},
    "companion": {"id": "saji", "x": 11.6, "z": 22.6},
    "entities": [
        {"id": "rock", "kind": "rock", "name": "石", "x": 13.0, "z": 18.5, "r": 0.45, "solid": True,
         "material": "stone", "q": {"w": 2, "h": 1, "s": 1}, "view": {"shape": "rock", "w": 0.9, "h": 0.7, "color": "#8c8678"}},
        {"id": "beam", "kind": "beam", "name": "梁", "x": 5.5, "z": 11.0, "r": 0.6, "solid": True,
         "material": "wood", "q": {"w": 3}, "view": {"shape": "beam", "w": 2.0, "h": 0.4, "color": "#7a5a3a"}},
        {"id": "frame", "kind": "frame", "name": "旧背負子", "x": 15.0, "z": 11.3, "r": 0.4, "solid": True,
         "q": {"w": 0}, "base": {"w": 2}, "view": {"shape": "frame", "w": 0.7, "h": 1.1, "color": "#8a6a46"}},
        {"id": "lantern", "kind": "lantern", "name": "石灯笼", "x": 6.5, "z": 3.0, "r": 0.35, "solid": True,
         "material": "lantern", "q": {"l": 0, "h": 0, "w": 3}, "view": {"shape": "lantern", "w": 0.6, "h": 1.4, "color": "#9a968a"}},
        {"id": "stone", "kind": "shrine_stone", "name": "注连石", "x": 16.5, "z": 5.5, "r": 0.5, "solid": True,
         "sacred": True, "material": "stone", "q": {"w": 3, "v": 2}, "view": {"shape": "rock", "w": 1.1, "h": 1.0, "color": "#7d7a70", "rope": True}},
        {"id": "sign", "kind": "sign", "name": "道标", "x": 12.4, "z": 21.0, "r": 0.25, "solid": True, "priority": 1,
         "q": {}, "data": {"showQualities": False, "dialogue": "test_sign"}, "view": {"shape": "sign", "w": 0.5, "h": 1.2, "color": "#6e5640"}},
    ],
    "zones": [
        {"id": "wind", "x0": 13.0, "x1": 18.5, "z0": 1.0, "z1": 4.5, "wind": [1.6, 0.0]},
        {"id": "plateau", "x0": 0.0, "x1": 20.0, "z0": 0.0, "z1": 6.0},
    ],
    "shots": {
        "overview": {"x": 16.0, "z": 12.0},
        "stairs": {"x": 10.25, "z": 10.0},
        "plateau": {"x": 10.0, "z": 3.0},
    },
}


def main():
    os.makedirs(OUT, exist_ok=True)
    h, m = build()
    write_logic(h, m)
    write_art(h, m)
    with open(os.path.join(OUT, "region.json"), "w", encoding="utf-8") as f:
        json.dump(REGION, f, ensure_ascii=False, indent=1)
    print("test region written to", OUT)


if __name__ == "__main__":
    main()
