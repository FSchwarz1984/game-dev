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
    parts.append(MD.hat(float(os.environ.get('C3D_HAT_TILT', '0')), float(os.environ.get('C3D_HAT_ROLL', '0'))))
    from kasasagi import clothes
    parts += clothes.body_parts()
    return parts


def build(static=False):
    parts = all_parts()
    obj, owner = SC.mesh_object('Kasasagi', parts)
    obj.data.color_attributes.active_color = obj.data.color_attributes['Preview']
    built = {'mesh': obj, 'owner': owner, 'parts': parts}
    if not static:
        from kasasagi import rigging, anims
        arm = rigging.build_armature()
        rigging.skin(obj, owner, arm)
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


# the hat convention (godot/characters/hat_tilt_modifier.gd): the top leans away from the camera by
# HAT_TILT_DEG while she faces it (the navy underside frames her face, as in the art), easing to
# HAT_TILT_AWAY_DEG as she turns her back, and to the screen's right by HAT_ROLL_DEG
HAT_TILT_DEG = 52.0
HAT_TILT_AWAY_DEG = 24.0
HAT_ROLL_DEG = 12.0
# in profile her head turns this far toward the camera (godot/characters/head_turn_modifier.gd)
HEAD_TURN_BIAS_DEG = 20.0

# secondary motion (SpringBoneSimulator3D in the game; VRM-style verlet: stiffness pulls back to the
# animated pose, drag damps, gravity in m/s^2-ish units of the solver)
HAIR_COLLIDE = ['col_head', 'col_chest', 'col_spine', 'col_hips', 'col_thigh_L', 'col_thigh_R']


def spring_chains():
    out = []
    for i in range(5):
        out.append({'name': 'hair_%d' % i, 'root': 'hair_%d_0' % i, 'end': 'hair_%d_3' % i, 'stiffness': 1.6,
                    'drag': 0.55, 'gravity': 0.4, 'radius': 0.035, 'tip': 0.06, 'collide': HAIR_COLLIDE,
                    'wind': 0.25})
    for sx in ('L', 'R'):
        out.append({'name': 'lock_' + sx, 'root': 'lock_%s_0' % sx, 'end': 'lock_%s_2' % sx, 'stiffness': 2.0,
                    'drag': 0.55, 'gravity': 0.3, 'radius': 0.02, 'tip': 0.03, 'collide': ['col_chest', 'col_head'],
                    'wind': 0.15})
        out.append({'name': 'sleeve_' + sx, 'root': 'sleeve_%s_0' % sx, 'end': 'sleeve_%s_1' % sx, 'stiffness': 2.4,
                    'drag': 0.5, 'gravity': 0.15, 'radius': 0.04, 'tip': 0.05,
                    'collide': ['col_chest', 'col_spine', 'col_hips', 'col_thigh_' + sx], 'wind': 0.2})
    for key in ('FL', 'FR', 'BL', 'BR', 'SL', 'SR'):
        out.append({'name': 'coat_' + key, 'root': 'coat_%s_0' % key, 'end': 'coat_%s_1' % key, 'stiffness': 2.2,
                    'drag': 0.55, 'gravity': 0.3, 'radius': 0.035, 'tip': 0.03,
                    'collide': ['col_thigh_L', 'col_thigh_R', 'col_shin_L', 'col_shin_R'], 'wind': 0.12})
    # the sash's tails: the freest things on her (the art always has them flying)
    # stiff enough to keep their out-flung shape standing still (the lead: one of her three big shapes),
    # free enough to stream behind her when she moves
    out.append({'name': 'sashA', 'root': 'sashA_0', 'end': 'sashA_3', 'stiffness': 1.5, 'drag': 0.34,
                'gravity': 0.30, 'radius': 0.02, 'tip': 0.04,
                'collide': ['col_hips', 'col_thigh_L', 'col_thigh_R', 'col_shin_L', 'col_shin_R'], 'wind': 0.35})
    out.append({'name': 'sashB', 'root': 'sashB_0', 'end': 'sashB_3', 'stiffness': 1.3, 'drag': 0.34,
                'gravity': 0.30, 'radius': 0.02, 'tip': 0.04,
                'collide': ['col_hips', 'col_thigh_L', 'col_thigh_R'], 'wind': 0.40})
    return out


def colliders():
    # capsules along each bone's own +Y (Godot axes, bone space): name, bone, radius, height, offset
    c = [('col_head', 'head', 0.21, 0.42, (0, 0.21, 0.0)), ('col_chest', 'chest', 0.125, 0.30, (0, 0.07, 0.0)),
         ('col_spine', 'spine', 0.115, 0.26, (0, 0.05, 0.0)), ('col_hips', 'hips', 0.13, 0.30, (0, 0.02, 0.0))]
    for sx in ('L', 'R'):
        c.append(('col_thigh_' + sx, 'thigh_' + sx, 0.095, 0.40, (0, 0.125, 0.0)))
        c.append(('col_shin_' + sx, 'shin_' + sx, 0.08, 0.32, (0, 0.13, 0.0)))
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
    meta = {'note': 'landmarks: model space, bind pose, Godot axes (x east, y up, z toward the camera)',
            'landmarks': lm, 'clips': clips, 'hat_tilt_deg': HAT_TILT_DEG, 'hat_tilt_away_deg': HAT_TILT_AWAY_DEG,
            'hat_roll_deg': HAT_ROLL_DEG, 'head_turn_bias_deg': HEAD_TURN_BIAS_DEG,
            'springs': spring_chains(), 'colliders': colliders()}
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
