#!/usr/bin/env python3
"""Write the vegetation bench (a small Godot project) into a directory:
  python3 tools/flora/bench/make_bench.py <project_dir>
It copies tools/flora/out/godot/flora (run tools/flora/build.py first), bench.gd, a neutral ground
for each layout, the layouts (a row of every species; a glade around the camphor), and the
character placeholder (her front idle frame, for scale)."""
import json
import math
import os
import shutil
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FLORA = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(FLORA))
sys.path.insert(0, FLORA)
from flora.core import Rng, fbm2, hash01, vnoise2  # noqa: E402

PROJECT = '''config_version=5

[application]

config/name="Flora bench"
run/main_scene="res://bench/bench.tscn"
config/features=PackedStringArray("4.7", "Mobile")
run/flush_stdout_on_print=true

[display]

window/size/viewport_width=1440
window/size/viewport_height=810
window/stretch/mode="disabled"

[rendering]

renderer/rendering_method="mobile"
renderer/rendering_method.mobile="mobile"
textures/canvas_textures/default_texture_filter=0

[shader_globals]

player_pos={"type": "vec2", "value": Vector2(-100000, -100000)}
wind_strength={"type": "float", "value": 1.0}
sun_elevation={"type": "float", "value": 47.8}
shadow_strength={"type": "float", "value": 1.0}
'''

TSCN = '''[gd_scene format=3]

[ext_resource type="Script" path="res://bench/bench.gd" id="1"]

[node name="Bench" type="Node"]
script = ExtResource("1")
'''


def ground(W, H, seed, clearing=None):
    """A neutral late-summer ground: muted grass in broad, low-contrast patches with small tufts;
    optional packed-earth clearing (cx, cy, rx, ry in px). Deliberately quiet: it is a stage for
    the plants, not terrain art (that is the terrain agent's)."""
    rng = Rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    g1 = np.array([88, 103, 66], float)
    g2 = np.array([91, 106, 67], float)
    g0 = np.array([85, 100, 65], float)
    n = fbm2(xx / 60.0, yy / 60.0, 3, seed)
    img = np.where((n > 0.60)[..., None], g2, np.where((n < 0.38)[..., None], g0, g1))
    # tufts: tiny, tops lit, scattered on a jittered grid
    for gy in range(0, H, 7):
        for gx in range(0, W, 9):
            if hash01(gx, gy, seed) < 0.55:
                continue
            x = gx + int(hash01(gx, gy, seed + 1) * 8)
            y = gy + int(hash01(gx, gy, seed + 2) * 6)
            if x >= W - 2 or y >= H - 1 or y < 2:
                continue
            base = img[y, x].copy()
            img[y, x] = base * 0.93
            img[y - 1, x] = base * 1.05
            if hash01(gx, gy, seed + 3) < 0.4:
                img[y - 2, x] = base * 1.07
    if clearing is not None:
        cx, cy, rx, ry = clearing
        d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
        d += (vnoise2(xx / 14.0, yy / 14.0, seed + 9) - 0.5) * 0.25
        soil = np.array([106, 96, 74], float)
        soil2 = np.array([101, 92, 71], float)
        moss = np.array([86, 98, 62], float)
        s_n = vnoise2(xx / 16.0, yy / 16.0, seed + 11)
        s_col = np.where((s_n > 0.62)[..., None], soil2, soil)
        s_col = np.where((vnoise2(xx / 30.0, yy / 30.0, seed + 12) > 0.70)[..., None], moss, s_col)
        a = np.clip((1.0 - d) * 4.0, 0, 1)
        a = np.where(a > 0.5, 1.0, np.where((a > 0.2) & (hash01(xx.astype(np.int64) // 2, yy.astype(np.int64) // 2, seed) < a), 1.0, 0.0))
        img = img * (1 - a[..., None]) + s_col * a[..., None]
    out = np.zeros((H, W, 4), np.uint8)
    out[..., :3] = np.clip(img, 0, 255)
    out[..., 3] = 255
    return out


def load_catalog(root):
    with open(os.path.join(root, 'catalog.json')) as fh:
        return json.load(fh)


def row_layout(cat):
    """Every species in a row on neutral ground, small plants in a second row in front."""
    order = ['camphor_a', 'cedar_1', 'cedar_4', 'red_pine_1', 'red_pine_3', 'beech_1', 'persimmon_1', 'maple_green_1',
             'maple_turn_1', 'maple_red_1', 'bamboo_1']
    small = ['hydrangea_1', 'azalea_1', 'shrub_1', 'susuki_1', 'susuki_2', 'fern_1', 'fern_2', 'higanbana_1',
             'tsuyukusa_1', 'ominaeshi_1', 'hydrangea_2', 'azalea_2']
    plants = []
    x = 60
    y_back = 560
    for n in order:
        c = cat[n]
        w = c['layers'].get('crown', c['layers'].get('trunk'))['size'][0]
        off = c['layers'].get('crown', c['layers'].get('trunk'))['offset'][0]
        x += -off + 8
        plants.append({'scene': c['scene'], 'x': x, 'y': y_back})
        x += w + off + 8
    width = x + 40
    x = 80
    for n in small:
        c = cat[n]
        w = c['layers']['crown']['size'][0]
        off = c['layers']['crown']['offset'][0]
        x += -off + 26
        plants.append({'scene': c['scene'], 'x': x, 'y': y_back + 90})
        x += w + off + 26
    return {'ground': 'res://bench/ground_row.png', 'bounds': [0, 0, int(width), 700], 'plants': plants,
            'player': [width // 2, y_back + 60]}


def glade_layout(cat, seed=5):
    """The shrine clearing under the great camphor: the clearing south of the trunk, shrubs and
    herbs at its edges, maples and a persimmon on the sides, cedars and pines behind, bamboo east,
    beech in the moss corner. Plants are grouped with breathing space between groups."""
    rng = Rng(seed)
    W, H = 1500, 1000
    cx, cy = 760, 470                         # camphor foot
    plants = [{'scene': cat['camphor_a']['scene'], 'x': cx, 'y': cy}]

    def put(name, x, y):
        plants.append({'scene': cat[name]['scene'], 'x': int(x), 'y': int(y)})

    # background: cedars along the north edge, staggered, with gaps
    for i, x in enumerate([90, 170, 250, 1240, 1320, 1410]):
        put('cedar_%d' % (1 + i % 5), x + rng.range(-10, 10), 250 + (i % 2) * 40 + rng.range(-10, 10))
    for i, x in enumerate([340, 1160]):
        put('cedar_%d' % (3 + i), x, 200)
    # pines on the east rise, maples framing the clearing
    put('red_pine_2', 1230, 560)
    put('red_pine_4', 1360, 640)
    put('maple_turn_1', 360, 640)
    put('maple_green_2', 250, 720)
    put('maple_red_1', 1120, 820)
    put('persimmon_1', 300, 470)              # by the hut, west
    put('bamboo_2', 1430, 420)
    put('bamboo_3', 1460, 520)
    put('beech_1', 120, 560)
    put('beech_2', 140, 850)
    # shrubs: hydrangea by the hut path, azaleas clipped along the clearing's edge
    for (n, x, y) in [('hydrangea_1', 470, 600), ('hydrangea_3', 520, 640), ('azalea_1', 980, 640),
                      ('azalea_3', 1030, 670), ('shrub_2', 1080, 700), ('shrub_1', 430, 760),
                      ('azalea_2', 610, 820), ('hydrangea_2', 900, 860)]:
        put(n, x, y)
    # herbs: ferns in the shade by the roots, susuki on the sunny south edge, flowers in drifts
    for (n, x, y) in [('fern_1', 680, 520), ('fern_2', 860, 520), ('fern_3', 640, 560), ('fern_4', 900, 560),
                      ('fern_5', 560, 520)]:
        put(n, x, y)
    for i in range(7):
        put('susuki_%d' % (1 + i % 5), 640 + i * 38 + rng.range(-8, 8), 900 + rng.range(-12, 12))
    for i in range(5):
        put('ominaeshi_%d' % (1 + i % 4), 520 + i * 18 + rng.range(-4, 4), 880 + rng.range(-8, 8))
    for i in range(4):
        put('tsuyukusa_%d' % (1 + i % 4), 820 + i * 22, 600 + rng.range(-6, 6))
    for i in range(6):
        put('higanbana_%d' % (1 + i % 4), 1000 + i * 14 + rng.range(-3, 3), 760 + rng.range(-8, 8))
    lanterns = [[cx - 60, cy + 110], [cx + 70, cy + 120], [330, 540]]
    return {'ground': 'res://bench/ground_glade.png', 'bounds': [0, 0, W, H], 'plants': plants,
            'player': [cx + 10, cy + 150], 'lanterns': lanterns, 'clearing': [cx, cy + 150, 300, 170]}


def main(proj):
    os.makedirs(os.path.join(proj, 'bench', 'layouts'), exist_ok=True)
    os.makedirs(os.path.join(proj, 'bench', 'char'), exist_ok=True)
    with open(os.path.join(proj, 'project.godot'), 'w') as fh:
        fh.write(PROJECT)
    with open(os.path.join(proj, 'bench', 'bench.tscn'), 'w') as fh:
        fh.write(TSCN)
    for f in ('bench.gd', 'linear_to_srgb.gdshader'):
        shutil.copyfile(os.path.join(HERE, f), os.path.join(proj, 'bench', f))
    src = os.path.join(FLORA, 'out', 'godot', 'flora')
    dst = os.path.join(proj, 'flora')
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    cat = load_catalog(src)
    row = row_layout(cat)
    glade = glade_layout(cat)
    for name, L in (('row', row), ('glade', glade)):
        with open(os.path.join(proj, 'bench', 'layouts', name + '.json'), 'w') as fh:
            json.dump(L, fh, indent=1)
        b = L['bounds']
        Image.fromarray(ground(b[2], b[3], 3 if name == 'row' else 4, L.get('clearing')), 'RGBA').save(
            os.path.join(proj, 'bench', 'ground_%s.png' % name))
    # her front idle frame (56x64, feet at (28, 61)) and its normal map, for scale
    for suf in ('', '_n'):
        im = Image.open(os.path.join(REPO, 'assets', 'sprites', 'tsuzumi_plain%s.png' % suf))
        im.crop((0, 0, 56, 64)).save(os.path.join(proj, 'bench', 'char', 'tsuzumi%s.png' % suf))
    fs = np.zeros((5, 15, 4), np.uint8)
    yy, xx = np.mgrid[0:5, 0:15]
    m = ((xx - 7) / 7.5) ** 2 + ((yy - 2) / 2.5) ** 2 < 1
    fs[m] = (20, 22, 34, 255)
    Image.fromarray(fs, 'RGBA').save(os.path.join(proj, 'bench', 'char', 'foot_shadow.png'))
    print('bench written to', proj)


if __name__ == '__main__':
    main(sys.argv[1])
