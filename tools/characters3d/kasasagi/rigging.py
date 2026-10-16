"""百々かさゝぎ's skeleton and skin weights (round 5).

Bones follow one convention so poses are easy to write: every bone's local Z axis points forward
(-Y, the way she faces), so local X is the hinge of a forward bend: +X bends the spine forward,
lifts a hanging limb forward (and so bends an elbow), and -X bends a knee; local Y runs along the
bone (twist); local Z leans sideways. Secondary chains (the long hair's three strips, the side locks,
the sleeves' bells, the robe's panels, the sash's tails) are driven in the game by
SpringBoneSimulator3D (rig.json lists them with their settings).

The bones the game addresses by name (character3d.gd, the modifiers) are kept from round 4: root,
hips, spine, chest, neck, head, hat, shoulder_/upper_arm_/forearm_/hand_ L/R, thigh_/shin_/foot_/toe_ L/R.

Weights are computed from the parametric tags the model writes (no heat weights: they fail on layered
cloth and hair): each region blends between a few named bones along its own coordinate.
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


# the long hair's three chains across the sheet (x in [-1, 1]: her right, the middle, her left)
HAIR_CHAIN_X = [-0.62, 0.0, 0.62]
HAIR_CHAIN_N = 4
COAT_PANELS = {'FL': 0.62, 'FR': -0.62, 'BL': 2.2, 'BR': -2.2, 'SL': 1.45, 'SR': -1.45}   # angle from the front, + her left


def hair_chain_points(i):
    """Five points down the sheet along x = HAIR_CHAIN_X[i], from the nape to the end."""
    from kasasagi.model import sheet_point, sheet_frame, SHEET_TOP_H, sheet_bottom_u
    x = HAIR_CHAIN_X[i]
    z_top = B.CHIN_Z + SHEET_TOP_H
    u0 = min(1.0, max(0.0, (z_top - (B.CHIN_Z - 0.03)) / (z_top - D['back_hair_end'])))
    u1 = sheet_bottom_u(x)
    pts = []
    for k in range(HAIR_CHAIN_N + 1):
        u = lerp(u0, u1, k / HAIR_CHAIN_N)
        p = sheet_point(u, x, True)
        pts.append(p + Vector((0, -0.015, 0)))
    return pts


def sleeve_chain_points(side):
    """Down the bell's middle: from the elbow's height to the hem."""
    from kasasagi.clothes import sleeve_frame
    sh, hem, cx, rx, ry = sleeve_frame(side)
    top = Vector((lerp(sh.x, cx, 0.45), 0.004, lerp(sh.z, hem, 0.45)))
    mid = Vector((lerp(sh.x, cx, 0.75), 0.005, lerp(sh.z, hem, 0.75)))
    bot = Vector((cx, 0.006, hem))
    return top, mid, bot


def coat_chain_points(ang):
    from kasasagi.clothes import coat_slice
    hz = D['hip_z']
    hem = D['coat_hem']
    pts = []
    for z in (hz, lerp(hz, hem, 0.5), hem):
        X, Yd, yc, g = coat_slice(z)
        t = math.pi / 2 - ang          # 0 her left, pi/2 front
        pts.append(Vector((X * math.cos(t) * 1.02, yc - Yd * math.sin(t) * 1.02, z)))
    return pts


def bone_defs():
    """(name, head, tail, parent) in rest pose."""
    from kasasagi.model import side_lock_points
    from kasasagi.clothes import sash_paths
    d = []
    d.append(('root', Vector((0, 0, 0)), Vector((0, -0.12, 0)), None))
    d.append(('hips', B.HIPS, B.SPINE, 'root'))
    d.append(('spine', B.SPINE, B.CHEST, 'hips'))
    d.append(('chest', B.CHEST, B.NECK_BASE, 'spine'))
    d.append(('neck', B.NECK_BASE, B.NECK_TOP, 'chest'))
    d.append(('head', B.NECK_TOP, Vector((0, 0.02, B.CHIN_Z + B.HEAD_H * 0.6)), 'neck'))
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
        # side lock: from the cheek, through the tie, to its end
        lp = side_lock_points(side)
        pts = [lp[1], lp[2], lp[4], lp[5]]
        par = 'head'
        for k in range(3):
            n = 'lock_%s_%d' % (sx, k)
            d.append((n, pts[k], pts[k + 1], par))
            par = n
        s0, s1, s2 = sleeve_chain_points(side)
        d.append(('sleeve_%s_0' % sx, s0, s1, 'upper_arm_' + sx))
        d.append(('sleeve_%s_1' % sx, s1, s2, 'sleeve_%s_0' % sx))
    for i in range(len(HAIR_CHAIN_X)):
        par = 'head'
        pts = hair_chain_points(i)
        for k in range(len(pts) - 1):
            n = 'hair_%d_%d' % (i, k)
            d.append((n, pts[k], pts[k + 1], par))
            par = n
    for key, ang in COAT_PANELS.items():
        pts = coat_chain_points(ang)
        par = 'hips'
        for k in range(len(pts) - 1):
            n = 'coat_%s_%d' % (key, k)
            d.append((n, pts[k], pts[k + 1], par))
            par = n
    A, Bp = sash_paths()
    for key, pts in (('A', A), ('B', Bp)):
        par = 'hips'
        for k in range(len(pts) - 1):
            n = 'sash%s_%d' % (key, k)
            d.append((n, pts[k], pts[k + 1], par))
            par = n
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


def _chain(prefix, n, t):
    """Weights along a chain of n bones for t in [0, 1]."""
    w = {}
    x = t * n
    for k in range(n):
        c = k + 0.5
        dd = abs(x - c)
        v = max(0.0, 1.0 - dd / 0.85)
        if v > 0:
            w['%s%d' % (prefix, k)] = v
    if not w:
        w['%s%d' % (prefix, n - 1 if t > 0.5 else 0)] = 1.0
    return w


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
        return _blend({'chest': 1.0}, {'neck': 1.0}, smooth((z - (nb - 0.01)) / 0.03))
    if z > B.CHEST.z - 0.02:
        return _blend({'spine': 1.0}, {'chest': 1.0}, smooth((z - (B.CHEST.z - 0.03)) / 0.06))
    if z > B.SPINE.z - 0.04:
        return _blend({'hips': 1.0}, {'spine': 1.0}, smooth((z - (B.SPINE.z - 0.04)) / 0.06))
    return {'hips': 1.0}


def _side_of(x):
    return 'L' if x >= 0 else 'R'


def weights_for(p, tag):
    seg = tag.get('seg', '')
    if seg in ('head', 'hair_cap', 'hair_bang'):
        if p.z < B.CHIN_Z + 0.02 and seg == 'head':
            return _blend({'head': 1.0}, {'neck': 1.0}, smooth((B.CHIN_Z + 0.02 - p.z) / 0.06) * 0.5)
        return {'head': 1.0}
    if seg == 'neck':
        return _blend({'neck': 1.0}, {'head': 1.0}, smooth((p.z - (B.CHIN_Z - 0.02)) / 0.05))
    if seg == 'hat':
        return {'hat': 1.0}
    if seg == 'hair_side':
        sx = _side_of(p.x)
        z0 = B.CHIN_Z + 0.20
        z1 = B.CHIN_Z + D['lock_end_h']
        if p.z > z0 + 0.02:
            return {'head': 1.0}
        t = (z0 - p.z) / (z0 - z1)
        w = _chain('lock_%s_' % sx, 3, max(0.0, min(1.0, t)))
        return _blend(w, {'head': 1.0}, smooth((p.z - (B.CHIN_Z + 0.10)) / 0.10))
    if seg == 'hair_back':
        x = tag.get('x', 0.0)
        u = tag.get('u', 0.0)
        from kasasagi.model import SHEET_TOP_H
        z_top = B.CHIN_Z + SHEET_TOP_H
        z_nape = B.CHIN_Z - 0.03
        if p.z > z_nape + 0.06:
            return {'head': 1.0}
        t = (z_nape - p.z) / max(z_nape - D['back_hair_end'], 1e-3)
        t = max(0.0, min(1.0, t))
        # three strips across, blended by x
        right = smooth((-x - 0.12) / 0.5)
        left = smooth((x - 0.12) / 0.5)
        mid = max(0.0, 1.0 - right - left)
        tot = right + mid + left
        w = {}
        for i, k in ((0, right), (1, mid), (2, left)):
            if k > 0:
                for bn, v in _chain('hair_%d_' % i, HAIR_CHAIN_N, t).items():
                    w[bn] = w.get(bn, 0.0) + v * k / tot
        return _blend(w, {'head': 1.0}, smooth((p.z - (z_nape - 0.06)) / 0.12))
    if seg in ('torso', 'bow'):
        if seg == 'torso' and p.z > B.SHOULDER_Z - 0.06 and abs(p.x) > 0.08:
            sx = _side_of(p.x)
            return _blend(_torso_w(p.z), {'shoulder_' + sx: 1.0}, smooth((abs(p.x) - 0.08) / 0.05) * 0.5)
        return _torso_w(p.z)
    if seg == 'coat':
        return _coat_w(p, tag)
    if seg == 'sleeve':
        # the panel: its top on the shoulder, the strip round the arm with the arm, the hanging bag on
        # the sleeve chain (it swings on its spring)
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        u = tag.get('u', 0.0)
        s = tag.get('s', 0.5)
        w = _blend({'shoulder_' + sx: 1.0}, {'upper_arm_' + sx: 1.0}, smooth(u / 0.2))
        w = _blend(w, _blend({'upper_arm_' + sx: 1.0}, {'forearm_' + sx: 1.0}, smooth((u - 0.45) / 0.3)),
                   smooth((u - 0.2) / 0.2))
        bag = smooth((u - 0.25) / 0.35) * smooth((s - 0.10) / 0.35)
        w = _blend(w, _chain('sleeve_%s_' % sx, 2, max(0.0, min(1.0, (u - 0.35) / 0.65))), bag)
        if u < 0.08:
            w = _blend(w, {'chest': 1.0}, (0.08 - u) / 0.08 * 0.5)
        return w
    if seg == 'arm':
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        u = tag.get('u', 0.0)
        return _blend({'upper_arm_' + sx: 1.0}, {'forearm_' + sx: 1.0}, smooth((u - 0.40) / 0.2))
    if seg == 'hand':
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        u = tag.get('u', 1.0)
        return _blend({'forearm_' + sx: 1.0}, {'hand_' + sx: 1.0}, smooth(u / 0.3))
    if seg == 'leg':
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        u = tag.get('u', 0.0)
        w = _blend({'thigh_' + sx: 1.0}, {'shin_' + sx: 1.0}, smooth((u - 0.38) / 0.16))
        if u < 0.18:
            w = _blend({'hips': 1.0}, w, smooth(u / 0.18))
        return w
    if seg == 'foot':
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        u = tag.get('u', 0.0)
        w = _blend({'shin_' + sx: 1.0}, {'foot_' + sx: 1.0}, smooth(u / 0.25))
        return _blend(w, {'toe_' + sx: 1.0}, smooth((u - 0.7) / 0.2))
    if seg == 'sash':
        u = tag.get('u', 0.0)
        key = tag.get('chain', 'A')
        n = 4 if key == 'A' else 3
        w = _chain('sash%s_' % key, n, max(0.0, min(1.0, (u - 0.04) / 0.96)))
        return _blend({'hips': 1.0}, w, smooth(u / 0.12))
    return {'hips': 1.0}


def _coat_w(p, tag):
    z = p.z
    hz = D['hip_z']
    hem = D['coat_hem']
    t = (hz - z) / max(hz - hem, 1e-3)
    t = max(0.0, min(1.0, t))
    ang = math.atan2(p.x, -p.y)            # 0 front, + her left, ~pi back
    keys = list(COAT_PANELS.items())
    dists = sorted(((abs((ang - a + math.pi) % (2 * math.pi) - math.pi), k) for k, a in keys))
    (d0, k0), (d1, k1) = dists[0], dists[1]
    share = d0 / max(1e-4, d0 + d1)
    chain = _blend(_chain('coat_%s_' % k0, 2, t), _chain('coat_%s_' % k1, 2, t), share)
    w = _blend({'hips': 1.0}, chain, smooth(t * 1.6) * 0.85)
    front = smooth((math.cos(ang) - 0.2) / 0.6)
    if front > 0:
        w = _blend(w, {'thigh_' + _side_of(p.x): 1.0}, front * 0.35 * smooth(t * 2.0))
    if z > hz - 0.02:
        w = _blend(w, _torso_w(z), smooth((z - (hz - 0.02)) / 0.06))
    return w


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
