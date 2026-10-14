"""Godot 4 scenes for the exported plants: one .tscn per plant that the game instances as is.

Scene layout (node origin = the plant's foot on the ground, in world px):
  <name> (Node2D, y_sort_enabled)            put it in the y-sorted 'things' node
    ShadowCrown, ShadowTrunk (Sprite2D)      z_index -9, flora_shadow.gdshader (multiply)
    Ground (Sprite2D)                        z_index -8, roots lying on the ground (if any)
    Trunk (Sprite2D)                         sorted at the foot; big trunks also cut an x-ray hole
    Crown (Sprite2D)                         sorted at the crown's southern edge (crown_sort_px),
                                             foliage.gdshader: sway + x-ray hole
For shrubs and herbs the body is the 'Crown' node, sorted at the foot.
"""
import json
import os
import shutil

from .core import SHADOW_DIR, SUN_ELEV_REF, PPM

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'godot_src')


def install_shared(root):
    """Copy the shaders and scripts into <root>/shaders."""
    os.makedirs(os.path.join(root, 'shaders'), exist_ok=True)
    for f in ('foliage.gdshader', 'flora_shadow.gdshader'):
        shutil.copyfile(os.path.join(SRC, f), os.path.join(root, 'shaders', f))


def _color(c):
    return 'Color(%.4f, %.4f, %.4f, 1)' % tuple(v / 255.0 for v in c)


def write_scene(meta, plant_dir, res_dir, res_root='res://flora'):
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

    sh_fol = ext_res('Shader', res_root + '/shaders/foliage.gdshader')
    sh_shd = ext_res('Shader', res_root + '/shaders/flora_shadow.gdshader')
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

    def foliage_mat(layer, occluder, amp, max_off):
        sid = 'm_' + layer
        lines = ['[sub_resource type="ShaderMaterial" id="%s"]' % sid,
                 'shader = ExtResource("%s")' % sh_fol]
        if (layer, 'data') in tex:
            lines.append('shader_parameter/sway_data = ExtResource("%s")' % tex[(layer, 'data')])
        lines += ['shader_parameter/core_color = %s' % _color(meta.get('core_color', [30, 50, 36])),
                  'shader_parameter/sway_amp = %.2f' % amp,
                  'shader_parameter/max_offset = %d' % max_off,
                  'shader_parameter/occluder = %s' % ('true' if occluder else 'false')]
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

    root = ['[node name="%s" type="Node2D"]' % name, 'y_sort_enabled = true',
            'metadata/flora_species = "%s"' % meta.get('species', ''),
            'metadata/flora_kind = "%s"' % meta.get('kind', ''),
            'metadata/flora_layout = "%s"' % meta.get('layout', 'tree')]
    if 'collision' in meta:
        root.append('metadata/flora_collision = PackedVector2Array(%s)' % ', '.join(
            '%.1f, %.1f' % (x, y) for x, y in meta['collision']))
    nodes.append('\n'.join(root))
    if 'shadow' in L:
        sprite('ShadowContact', 'shadow', z=-9, material=shadow_mat(2))
        sprite('ShadowCrown', 'shadow', z=-9, material=shadow_mat(0))
        sprite('ShadowTrunk', 'shadow', z=-9, material=shadow_mat(1))
    if 'ground' in L:
        sprite('Ground', 'ground', z=-8, texture='SubResource("%s")' % canvas_tex('ground'))
    if 'trunk' in L:
        sprite('Trunk', 'trunk', texture='SubResource("%s")' % canvas_tex('trunk'),
               material=foliage_mat('trunk', True, 0.0, 0) if big_trunk else None)
    if 'crown' in L:
        sort = int(meta.get('crown_sort_px', 0))
        amp = float(meta.get('sway_amp', 1.0))
        sprite('Crown', 'crown', pos=(0, sort), texture='SubResource("%s")' % canvas_tex('crown'),
               material=foliage_mat('crown', meta.get('layout') == 'tree', amp, 2 if amp > 1.4 else 1))
    text = '[gd_scene format=3]\n\n' + '\n'.join(ext) + '\n\n' + '\n\n'.join(sub) + '\n\n' + '\n\n'.join(nodes) + '\n'
    path = os.path.join(plant_dir, name + '.tscn')
    with open(path, 'w') as fh:
        fh.write(text)
    return path
