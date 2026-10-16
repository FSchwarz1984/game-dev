"""百々かさゝぎ: assembly of the model, rig and animations (called by tools/characters3d/build.py)."""
import math
import os
import bpy
from mathutils import Vector

from c3d import scene as SC
from kasasagi import model as MD


def all_parts():
    parts = []
    parts += MD.head()
    parts += MD.hair()
    parts += MD.hat()
    from kasasagi import clothes
    parts += clothes.body_parts()
    return parts


def build(static=False):
    parts = all_parts()
    obj, owner = SC.mesh_object('Kasasagi', parts)
    obj.data.color_attributes.active_color = obj.data.color_attributes['Preview']
    built = {'mesh': obj, 'owner': owner, 'parts': parts}
    if not static:
        from kasasagi import rigging
        arm = rigging.build_armature()
        rigging.skin(obj, owner, arm)
        # C3D_NOANIMS=1: the rig without clips (the round-5 shape gate: the static model and the face)
        if os.environ.get('C3D_NOANIMS', '0') != '1':
            from kasasagi import anims
            anims.build_all(arm)
        built['armature'] = arm
    return built


def previews(built, out_dir, pose=None):
    scene = bpy.context.scene
    obj = built['mesh']
    arm = built.get('armature')
    if pose and arm is not None:
        from kasasagi import anims
        anims.apply_pose(arm, pose)
    scene.display.shading.show_backface_culling = os.environ.get('C3D_CULL', '1') == '1'
    views = [('front', 'front', 2.2, (0, 0, 0.95)), ('side', 'side', 2.2, (0, 0, 0.95)),
             ('back', 'back', 2.2, (0, 0, 0.95))]
    for name, view, ortho, centre in views:
        SC.setup_preview(scene, res=(600, 640), ortho=ortho, view=view, centre=centre)
        SC.render(scene, os.path.join(out_dir, name + '.png'))
    # the game's view: the lean applied to a copy, the 55 degree camera; one big, one at native
    # scale (30 px per metre: ortho scale = width px / 30)
    lean = SC.lean_copy(obj)
    lean.data.color_attributes.active_color = lean.data.color_attributes['Preview']
    obj.hide_render = True
    if arm is not None:
        arm.hide_render = True
    for yaw in (0, 45, 90, 180):
        lean.rotation_euler = (0, 0, 0)
        # rotate the source pose instead: re-lean a rotated copy
    SC.setup_preview(scene, res=(600, 640), ortho=2.2, view='game', centre=(0, 0.45, 0.95))
    SC.render(scene, os.path.join(out_dir, 'game.png'))
    SC.setup_preview(scene, res=(80, 85), ortho=80 / 30.0, view='game', centre=(0, 0.45, 0.95), outline=False)
    scene.display.render_aa = 'OFF'
    SC.render(scene, os.path.join(out_dir, 'game_native.png'))
    bpy.data.objects.remove(lean)
    obj.hide_render = False
    # turned copies in the game view
    for yaw in (45, 90, 135, 180):
        obj.rotation_euler = (0, 0, math.radians(yaw))
        bpy.context.view_layer.update()
        lc = SC.lean_copy(obj)
        lc.data.color_attributes.active_color = lc.data.color_attributes['Preview']
        obj.hide_render = True
        SC.setup_preview(scene, res=(600, 640), ortho=2.2, view='game', centre=(0, 0.45, 0.95))
        scene.display.render_aa = '8'
        SC.render(scene, os.path.join(out_dir, 'game_%03d.png' % yaw))
        bpy.data.objects.remove(lc)
        obj.hide_render = False
    obj.rotation_euler = (0, 0, 0)


def pose_sheet(built, out_dir, specs):
    """Front and side Workbench renders of poses 'name@frame' (anims.pose_at), for checking clips."""
    from kasasagi import anims
    scene = bpy.context.scene
    arm = built['armature']
    scene.display.shading.show_backface_culling = False
    for spec in specs:
        name, _, fr = spec.partition('@')
        act = bpy.data.actions.get(name)
        ad = arm.animation_data or arm.animation_data_create()
        if act is not None and name not in ('walk', 'run', 'heavy_walk', 'idle'):
            # a clip at a frame, as exported (key poses and their in-betweens)
            ad.action = act
            if hasattr(ad, 'action_slot') and ad.action_slot is None and len(act.slots):
                ad.action_slot = act.slots[0]
            scene.frame_set(int(fr or 0))
        else:
            ad.action = None
            anims.apply_pose(arm, spec)
        bpy.context.view_layer.update()
        for view in os.environ.get('C3D_POSE_VIEWS', 'front,side').split(','):
            SC.setup_preview(scene, res=(360, 420), ortho=2.3, view=view, centre=(0, 0, 0.95))
            SC.render(scene, os.path.join(out_dir, '%s_%s.png' % (spec.replace('@', '_'), view)))


def to_godot(v):
    return [round(v.x, 5), round(v.z, 5), round(-v.y, 5)]


# the hat convention (godot/characters/hat_tilt_modifier.gd): tipped back, away from the camera, by
# hat_tilt (facing the camera) .. hat_tilt_away (her back to it), so its white top shows as a flat
# ellipse over the face (round 5: past 50.7 deg the camera sees the navy underside; that was the
# rejected round-4 halo at 52 deg); a small roll to the screen's right
from kasasagi.design import D as _D
from kasasagi import body as _B
_VARIANT = 'R6'
HAT_TILT_DEG = _D['hat_tilt']
HAT_TILT_AWAY_DEG = _D['hat_tilt']
HAT_ROLL_DEG = _D['hat_roll']
# in profile her head turns this far toward the camera (godot/characters/head_turn_modifier.gd)
HEAD_TURN_BIAS_DEG = 20.0
# the hat's brim in the hat bone's space (the brim plane below the seat, its radius) and the arm that
# reaches for it (godot/characters/hat_reach_modifier.gd)
HAT_BRIM = {'y': _B.HAT_C.z - _B.HEAD_TOP, 'r': _B.HAT_R, 'arm': ['upper_arm_R', 'forearm_R', 'hand_R'], 'hand_len': 0.062}

HAIR_COLLIDE = ['col_head', 'col_chest', 'col_spine', 'col_hips', 'col_thigh_L', 'col_thigh_R']


def spring_chains():
    """Round 6, step 1 (the shape gate): no secondary chains yet; they come with the animation."""
    return []


def colliders():
    # capsules along each bone's own +Y (Godot axes, bone space): name, bone, radius, height, offset
    hh = _B.HEAD_H
    c = [('col_head', 'head', 0.22, hh * 0.9, (0, hh * 0.40, 0.0)), ('col_chest', 'chest', 0.13, 0.30, (0, 0.04, 0.0)),
         ('col_spine', 'spine', 0.12, 0.26, (0, 0.04, 0.0)), ('col_hips', 'hips', 0.14, 0.30, (0, 0.02, 0.0))]
    for sx in ('L', 'R'):
        c.append(('col_thigh_' + sx, 'thigh_' + sx, 0.10, 0.36, (0, 0.11, 0.0)))
        c.append(('col_shin_' + sx, 'shin_' + sx, 0.09, 0.30, (0, 0.11, 0.0)))
    return [{'name': n, 'bone': b, 'radius': r, 'height': h, 'offset': list(o)} for n, b, r, h, o in c]


def export(built, path):
    import json
    from kasasagi import anims
    SC.export_glb(path, [built['mesh']], built.get('armature'))
    lm = {}
    for name, (p, n) in MD.landmarks().items():
        lm[name] = {'p': to_godot(p), 'n': to_godot(n)}
    clips = {}
    for a in bpy.data.actions:
        clips[a.name] = dict(anims.CLIP_INFO.get(a.name, {}))
        clips[a.name].setdefault('loop', False)
    # the head snap: the face is 10 px wide (round 6), its centre on a pixel edge
    head_snap = {'x': 0.0, 'y': 0.0}
    # her material (godot/characters/shaders/char_toon.gdshader; its defaults are the round-4 look).
    # C3D_DEPTH_SCALE: her own view compensation (char_common.gdshaderinc c3_depth_scale; 1 = none)
    material = {'c3_style': 5, 'key_side': 0.55, 'key_up': 0.30, 'key_neutral': 0.60, 'white_point': 0.66,
                'face_white_point': 0.76, 'face_rim_keep': 0.0, 'face_rim_back': 0.0, 'hair_sheen': 0.0,
                'c3_depth_scale': float(os.environ.get('C3D_DEPTH_SCALE', '1.0'))}
    meta = {'note': 'landmarks: model space, bind pose, Godot axes (x east, y up, z toward the camera)',
            'variant': _VARIANT, 'design': _D['name'],
            'landmarks': lm, 'clips': clips, 'hat_tilt_deg': HAT_TILT_DEG, 'hat_tilt_away_deg': HAT_TILT_AWAY_DEG,
            'hat_roll_deg': HAT_ROLL_DEG, 'head_turn_bias_deg': HEAD_TURN_BIAS_DEG, 'hat_brim': HAT_BRIM,
            'springs': spring_chains(), 'colliders': colliders(), 'head_snap': head_snap, 'material': material,
            # round 6: the hat is worn as the sheet draws it (tipped back 14 deg, a little to her left)
            # and rides the head; no camera-relative tilt (hat_tilt_modifier.gd is not used)
            'hat_mode': 'rigid'}
    with open(os.path.join(os.path.dirname(path), 'rig.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    export_pack(os.path.join(os.path.dirname(os.path.dirname(path)), 'props', 'shoiko.glb'))


def export_pack(path):
    """The carrying frame as its own glTF, in her model space (the game parents it to her chest bone
    with the bone's inverse rest, so at rest it sits exactly where it was modelled)."""
    from kasasagi import shoiko
    os.makedirs(os.path.dirname(path), exist_ok=True)
    obj, owner = SC.mesh_object('Shoiko', [shoiko.shoiko()])
    SC.export_glb(path, [obj], None)
    bpy.data.objects.remove(obj)
