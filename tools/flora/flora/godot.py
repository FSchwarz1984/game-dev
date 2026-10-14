"""Godot 4 scenes for the exported plants: one .tscn per plant that the game instances as is.

Scene layout (docs/knowledge/18-vegetation.md; node origin = the plant's foot on the ground):
  <name> (Node2D, y_sort_enabled, flora_plant.gd)   put it in World.things at Proj.sort_px(x, z)
    ShadowContact, Shadow (Sprite2D)         z_index -9, flora_shadow.gdshader (multiply): contact
                                             shade, cast shadow (crown + trunk, moves with the sun)
    Ground (Sprite2D)                        z_index -8, roots lying on the ground (if any)
    Trunk (Sprite2D)                         sorted at the foot; big trunks also cut an x-ray hole
    Crown (Sprite2D)                         sorted at the crown's southern edge (crown_sort_px),
                                             foliage.gdshader: sway + x-ray hole
For shrubs and herbs the body is the 'Crown' node, sorted at the foot. Every drawn layer uses
foliage.gdshader, so plants take the same light as the terrain (uniform sun_dir).
"""
import math
import os
import shutil

from .core import KZ, PPM, SHADOW_DIR, SUN_ELEV_REF

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'godot_src')
SHARED = {'foliage.gdshader': 'shaders', 'flora_shadow.gdshader': 'shaders',
          'flora_plant.gd': '', 'flora_field.gd': ''}


def install_shared(root):
    """Copy the shaders and scripts into <root> (shaders/ and the root)."""
    for f, sub in SHARED.items():
        d = os.path.join(root, sub)
        os.makedirs(d, exist_ok=True)
        shutil.copyfile(os.path.join(SRC, f), os.path.join(d, f))


def _color(c):
    return 'Color(%.4f, %.4f, %.4f, 1)' % tuple(v / 255.0 for v in c)


def block_circles(meta):
    """Circles (x, z, r in metres from the foot) that stop her: the drawn footprint of the trunk
    (an ellipse on the ground, wide and shallow) covered by a row of circles. Shrubs: one circle
    a little inside the body. Herbs and grasses: none (she walks through)."""
    kind = meta.get('kind')
    if kind == 'herb':
        return []
    if kind == 'shrub':
        r = meta.get('body_radius_m', 0.0)
        return [[0.0, 0.0, round(min(r, 0.7) * 0.7, 2)]] if r else []
    poly = meta.get('collision')
    if poly:
        xs = [p[0] / PPM for p in poly]
        zs = [p[1] / PPM for p in poly]
        rx = (max(xs) - min(xs)) / 2
        rz = max(0.12, (max(zs) - min(zs)) / 2)
        cx = (max(xs) + min(xs)) / 2
        cz = (max(zs) + min(zs)) / 2
    else:
        r = meta.get('trunk_radius_m')
        if not r:
            return []
        rx, rz, cx, cz = r, max(0.12, r * KZ), 0.0, 0.0
    if rx <= 0.6:                 # a thin trunk: one round post (she never sees the difference)
        return [[round(cx, 2), round(cz, 2), round(max(rx * 0.8, rz), 2)]]
    n = max(1, int(math.ceil(rx / rz - 0.5)))
    if n == 1:
        return [[round(cx, 2), round(cz, 2), round(max(rx, rz), 2)]]
    out = []
    for i in range(n):
        x = cx - rx + rz + (2 * (rx - rz)) * i / (n - 1)
        # the ellipse is thinner toward its ends
        k = math.sqrt(max(0.0, 1 - ((x - cx) / rx) ** 2))
        out.append([round(x, 2), round(cz, 2), round(max(0.12, rz * max(k, 0.55)), 2)])
    return out


def write_scene(meta, plant_dir, res_dir, res_root='res://art/flora'):
    """meta: render.export() result. plant_dir: where the PNGs are; res_dir: their res:// path."""
    name = meta['name']
    L = meta['layers']
    ext = []
    sub = []
    nodes = []

    def ext_res(kind, path):
        rid = '%d_%s' % (len(ext) + 1, os.path.basename(path).split('.')[0])
        ext.append('[ext_resource type="%s" path="%s" id="%s"]' % (kind, path, rid))
        return rid

    scr = ext_res('Script', res_root + '/flora_plant.gd')
    sh_fol = ext_res('Shader', res_root + '/shaders/foliage.gdshader')
    sh_shd = ext_res('Shader', res_root + '/shaders/flora_shadow.gdshader') if 'shadow' in L else None
    tex = {}
    for layer, f in L.items():
        for key in ('albedo', 'normal', 'data'):
            if key in f:
                tex[(layer, key)] = ext_res('Texture2D', res_dir + '/' + f[key])

    def canvas_tex(layer):
        sid = 'ct_' + layer
        lines = ['[sub_resource type="CanvasTexture" id="%s"]' % sid,
                 'diffuse_texture = ExtResource("%s")' % tex[(layer, 'albedo')]]
        if (layer, 'normal') in tex:
            lines.append('normal_texture = ExtResource("%s")' % tex[(layer, 'normal')])
        lines.append('texture_filter = 1')
        sub.append('\n'.join(lines))
        return sid

    big_trunk = meta.get('trunk_occluder', False)
    crown_h = meta.get('crown_height_m', [0, 0])
    h_mid_px = (sum(crown_h) / 2.0) * PPM if crown_h else 0.0
    ref = meta.get('sun_ref', {}).get('elevation_deg', SUN_ELEV_REF)
    sd = meta.get('sun_ref', {}).get('shadow_dir_xz', list(SHADOW_DIR))

    def shadow_mat(ch):
        sid = 'm_shadow%d' % ch
        sub.append('\n'.join([
            '[sub_resource type="ShaderMaterial" id="%s"]' % sid,
            'shader = ExtResource("%s")' % sh_shd,
            'shader_parameter/channel = %d' % ch,
            'shader_parameter/ref_elevation = %.2f' % ref,
            'shader_parameter/shadow_dir = Vector2(%.4f, %.4f)' % (sd[0], sd[1]),
            'shader_parameter/crown_height_px = %.1f' % h_mid_px,
        ]))
        return sid

    def lit_mat(layer, occluder=False, amp=0.0, max_off=0):
        sid = 'm_' + layer
        lines = ['[sub_resource type="ShaderMaterial" id="%s"]' % sid,
                 'shader = ExtResource("%s")' % sh_fol]
        if (layer, 'data') in tex:
            lines.append('shader_parameter/sway_data = ExtResource("%s")' % tex[(layer, 'data')])
            lines += ['shader_parameter/core_color = %s' % _color(meta.get('core_color', [30, 50, 36])),
                      'shader_parameter/sway_amp = %.2f' % amp,
                      'shader_parameter/max_offset = %d' % max_off]
        else:
            lines.append('shader_parameter/has_sway_data = false')
        lines.append('shader_parameter/occluder = %s' % ('true' if occluder else 'false'))
        sub.append('\n'.join(lines))
        return sid

    def sprite(node, layer, z=None, pos=(0, 0), material=None, texture=None):
        f = L[layer]
        lines = ['[node name="%s" type="Sprite2D" parent="."]' % node]
        if z is not None:
            lines.append('z_index = %d' % z)
        if pos != (0, 0):
            lines.append('position = Vector2(%d, %d)' % pos)
        lines.append('texture = %s' % (texture or 'ExtResource("%s")' % tex[(layer, 'albedo')]))
        lines.append('centered = false')
        lines.append('offset = Vector2(%d, %d)' % (f['offset'][0] - pos[0], f['offset'][1] - pos[1]))
        if material:
            lines.append('material = SubResource("%s")' % material)
        nodes.append('\n'.join(lines))

    blocks = block_circles(meta)
    root = ['[node name="%s" type="Node2D"]' % name, 'y_sort_enabled = true',
            'script = ExtResource("%s")' % scr,
            'metadata/flora_species = "%s"' % meta.get('species', ''),
            'metadata/flora_kind = "%s"' % meta.get('kind', ''),
            'metadata/flora_layout = "%s"' % meta.get('layout', 'tree'),
            'metadata/flora_crown_sort_px = %d' % int(meta.get('crown_sort_px', 0)),
            'metadata/flora_block = [%s]' % ', '.join('[%.2f, %.2f, %.2f]' % tuple(c) for c in blocks)]
    if 'collision' in meta:
        root.append('metadata/flora_collision = PackedVector2Array(%s)' % ', '.join(
            '%.1f, %.1f' % (x, y) for x, y in meta['collision']))
    nodes.append('\n'.join(root))
    if 'shadow' in L:
        sprite('ShadowContact', 'shadow', z=-9, material=shadow_mat(2))
        sprite('Shadow', 'shadow', z=-9, material=shadow_mat(0))
    if 'ground' in L:
        sprite('Ground', 'ground', z=-8, texture='SubResource("%s")' % canvas_tex('ground'),
               material=lit_mat('ground'))
    if 'trunk' in L:
        sprite('Trunk', 'trunk', texture='SubResource("%s")' % canvas_tex('trunk'),
               material=lit_mat('trunk', occluder=big_trunk))
    if 'crown' in L:
        sort = int(meta.get('crown_sort_px', 0))
        amp = float(meta.get('sway_amp', 1.0))
        sprite('Crown', 'crown', pos=(0, sort), texture='SubResource("%s")' % canvas_tex('crown'),
               material=lit_mat('crown', meta.get('layout') == 'tree', amp, 2 if amp > 1.4 else 1))
    text = '[gd_scene format=3]\n\n' + '\n'.join(ext) + '\n\n' + '\n\n'.join(sub) + '\n\n' + '\n\n'.join(nodes) + '\n'
    path = os.path.join(plant_dir, name + '.tscn')
    with open(path, 'w') as fh:
        fh.write(text)
    return path, blocks
