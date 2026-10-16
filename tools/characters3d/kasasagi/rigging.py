"""百々かさゝぎ's skeleton and skin weights, round 6 (the shape gate: the model in the sheet's A pose).

Bones follow one convention so poses are easy to write: every bone's local Z axis points forward
(-Y, the way she faces), so local X is the hinge of a forward bend. The bones the game addresses by
name (character3d.gd, the modifiers) are kept from rounds 4 and 5: root, hips, spine, chest, neck,
head, hat, shoulder_/upper_arm_/forearm_/hand_ L/R, thigh_/shin_/foot_/toe_ L/R.

Round 6, step 1 has no secondary chains yet (hair, locks, sleeves, coat panels, the sash's and the hat
band's tails): they come with the animation (step 2) once the shape is approved. Until then the long
hair and the tails ride the head and the hips rigidly.

Weights come from the parametric tags the model writes (no heat weights: they fail on layered cloth
and hair): each region blends between a few named bones along its own coordinate.
"""
import math
import bpy
from mathutils import Vector

from c3d.surf import smooth, lerp
from kasasagi import body as B
from kasasagi.design import D

FWD = Vector((0, -1, 0))


def M(v, side):
    return Vector((v.x * side, v.y, v.z))


def bone_defs():
    """(name, head, tail, parent) in rest pose."""
    d = []
    d.append(('root', Vector((0, 0, 0)), Vector((0, -0.12, 0)), None))
    d.append(('hips', B.HIPS, B.SPINE, 'root'))
    d.append(('spine', B.SPINE, B.CHEST, 'hips'))
    d.append(('chest', B.CHEST, B.NECK_BASE, 'spine'))
    d.append(('neck', B.NECK_BASE, B.NECK_TOP, 'chest'))
    d.append(('head', B.NECK_TOP, Vector((0, B.HEAD_YC, B.CHIN_Z + B.HEAD_H * 0.6)), 'neck'))
    d.append(('hat', B.HAT_SEAT, B.HAT_SEAT + Vector((0, 0, 0.12)), 'head'))
    for side, sx in ((1, 'L'), (-1, 'R')):
        d.append(('shoulder_' + sx, M(B.CLAV_IN, side), M(B.SHOULDER, side), 'chest'))
        d.append(('upper_arm_' + sx, M(B.SHOULDER, side), M(B.ELBOW, side), 'shoulder_' + sx))
        d.append(('forearm_' + sx, M(B.ELBOW, side), M(B.WRIST, side), 'upper_arm_' + sx))
        d.append(('hand_' + sx, M(B.WRIST, side), M(B.HAND_TIP, side), 'forearm_' + sx))
        d.append(('thigh_' + sx, M(B.HIP_JOINT, side), M(B.KNEE, side), 'hips'))
        d.append(('shin_' + sx, M(B.KNEE, side), M(B.ANKLE, side), 'thigh_' + sx))
        d.append(('foot_' + sx, M(B.ANKLE, side), M(B.BALL, side), 'shin_' + sx))
        d.append(('toe_' + sx, M(B.BALL, side), M(B.TOE, side), 'foot_' + sx))
    return d


def build_armature():
    arm_data = bpy.data.armatures.new('KasasagiRig')
    arm = bpy.data.objects.new('Armature', arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones
    for name, head, tail, parent in bone_defs():
        b = eb.new(name)
        b.head = head
        b.tail = tail
        along = (tail - head).normalized()
        z = FWD if abs(along.dot(FWD)) < 0.7 else Vector((0, 0, 1))
        b.align_roll(z)
        if parent:
            b.parent = eb[parent]
            b.use_connect = False
        b.use_deform = name != 'root'
    bpy.ops.object.mode_set(mode='OBJECT')
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return arm


# =================================================================================================
# weights

def _norm(w):
    w = {k: v for k, v in w.items() if v > 1e-4}
    s = sum(w.values())
    if s <= 0:
        return {'hips': 1.0}
    w = {k: v / s for k, v in w.items()}
    top = sorted(w.items(), key=lambda kv: -kv[1])[:4]
    s = sum(v for _, v in top)
    return {k: v / s for k, v in top}


def _blend(a, b, t):
    out = {}
    for k, v in a.items():
        out[k] = out.get(k, 0.0) + v * (1 - t)
    for k, v in b.items():
        out[k] = out.get(k, 0.0) + v * t
    return out


def _torso_w(z):
    nb = D['neck_base']
    if z > nb - 0.02:
        return _blend({'chest': 1.0}, {'neck': 1.0}, smooth((z - (nb - 0.01)) / 0.04))
    if z > B.CHEST.z - 0.03:
        return _blend({'spine': 1.0}, {'chest': 1.0}, smooth((z - (B.CHEST.z - 0.03)) / 0.06))
    if z > B.SPINE.z - 0.04:
        return _blend({'hips': 1.0}, {'spine': 1.0}, smooth((z - (B.SPINE.z - 0.04)) / 0.06))
    return {'hips': 1.0}


def _side_of(x):
    return 'L' if x >= 0 else 'R'


def _hang_from_head(z):
    """Hair that hangs from the head and rests on her back: the head above the jaw, the chest below."""
    return _blend({'head': 1.0}, _torso_w(min(z, D['neck_base'] - 0.03)),
                  smooth((B.CHIN_Z + 0.02 - z) / 0.16))


def _arm_t(x):
    """0 at the shoulder joint .. 1 at the wrist, by |x| (the A-posed arm)."""
    return (abs(x) - B.SHOULDER.x) / max(B.WRIST.x - B.SHOULDER.x, 1e-3)


def weights_for(p, tag):
    seg = tag.get('seg', '')
    if seg in ('head', 'hair_cap', 'hair_bang'):
        if seg == 'head' and p.z < B.CHIN_Z + 0.02:
            return _blend({'head': 1.0}, {'neck': 1.0}, smooth((B.CHIN_Z + 0.02 - p.z) / 0.06) * 0.5)
        return {'head': 1.0}
    if seg == 'neck':
        return _blend({'neck': 1.0}, {'head': 1.0}, smooth((p.z - (B.CHIN_Z - 0.02)) / 0.05))
    if seg in ('hat', 'hat_tail'):
        return {'hat': 1.0}
    if seg in ('hair_side', 'hair_back'):
        return _hang_from_head(p.z)
    if seg == 'torso':
        w = _torso_w(p.z)
        if p.z > B.SHOULDER_Z - 0.06 and abs(p.x) > 0.09:
            w = _blend(w, {'shoulder_' + _side_of(p.x): 1.0}, smooth((abs(p.x) - 0.09) / 0.06) * 0.6)
        return w
    if seg == 'coat':
        z = p.z
        w = _torso_w(max(z, B.HIPS.z))
        if z > B.SHOULDER_Z - 0.08 and abs(p.x) > 0.10:
            w = _blend(w, {'shoulder_' + _side_of(p.x): 1.0}, smooth((abs(p.x) - 0.10) / 0.06) * 0.5)
        if z < B.HIPS.z:
            # the skirts: the hips, with a share of the thigh in front
            ang = math.atan2(p.x, -p.y)
            front = smooth((math.cos(ang) - 0.2) / 0.6)
            t = smooth((B.HIPS.z - z) / 0.35)
            w = _blend({'hips': 1.0}, {'thigh_' + _side_of(p.x): 1.0}, front * 0.4 * t)
        return w
    if seg == 'sleeve':
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        t = _arm_t(p.x)
        w = _blend({'shoulder_' + sx: 1.0}, {'upper_arm_' + sx: 1.0}, smooth((t + 0.15) / 0.3))
        return _blend(w, {'forearm_' + sx: 1.0}, smooth((t - 0.40) / 0.30))
    if seg == 'forearm':
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        return {'forearm_' + sx: 1.0}
    if seg == 'hand':
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        u = tag.get('u', 1.0)
        return _blend({'forearm_' + sx: 1.0}, {'hand_' + sx: 1.0}, smooth(u / 0.3))
    if seg in ('obi', 'bow'):
        return _blend({'hips': 1.0}, {'spine': 1.0}, 0.5)
    if seg in ('sashA', 'sashB'):
        return {'hips': 1.0}
    if seg == 'leg':
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        z = tag.get('z', p.z)
        w = _blend({'thigh_' + sx: 1.0}, {'shin_' + sx: 1.0}, smooth((B.KNEE.z + 0.06 - z) / 0.12))
        if z > B.HIPS.z - 0.04:
            w = _blend(w, {'hips': 1.0}, smooth((z - (B.HIPS.z - 0.04)) / 0.08))
        return w
    if seg == 'foot':
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        w = _blend({'shin_' + sx: 1.0}, {'foot_' + sx: 1.0}, smooth((B.ANKLE.z + 0.03 - p.z) / 0.06))
        return _blend(w, {'toe_' + sx: 1.0}, smooth((-p.y + B.BALL.y + 0.02) / 0.05))
    return {'hips': 1.0}


def skin(obj, owner, arm):
    """Vertex groups from the parts' tags; parents the mesh to the armature."""
    names = [b.name for b in arm.data.bones]
    groups = {n: obj.vertex_groups.new(name=n) for n in names if n != 'root'}
    for vi, (part, li) in enumerate(owner):
        p = obj.data.vertices[vi].co
        tag = part.tag[li]
        w = _norm(weights_for(p, tag))
        for bn, val in w.items():
            if bn in groups:
                groups[bn].add([vi], val, 'REPLACE')
    obj.parent = arm
    mod = obj.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm
    return groups
