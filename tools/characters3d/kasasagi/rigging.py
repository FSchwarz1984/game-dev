"""百々かさゝぎ's skeleton and skin weights.

Bones follow one convention so poses are easy to write: every bone's local Z axis points forward
(-Y, the way she faces), so local X is the hinge of a forward bend: +X bends the spine forward,
lifts a hanging limb forward (and so bends an elbow), and -X bends a knee; local Y runs along the
bone (twist); local Z leans sideways. Secondary chains (hair, sleeves, the haori's panels, the
sash's tail, the hat's cords) are driven in the game by SpringBoneSimulator3D (characters/rig.json
lists them with their settings).

Weights are computed from the parametric tags the model writes (no automatic heat weights: they
fail on layered cloth and hair): each region blends between a few named bones along its own
coordinate (along a sleeve, down the hair, down the haori).
"""
import math
import bpy
from mathutils import Vector

from c3d.surf import smooth, lerp
from kasasagi import body as B

FWD = Vector((0, -1, 0))


def M(v, side):
    return Vector((v.x * side, v.y, v.z))


def bone_defs():
    """(name, head, tail, parent) in rest pose."""
    d = []
    d.append(('root', Vector((0, 0, 0)), Vector((0, -0.12, 0)), None))
    d.append(('hips', B.HIPS, Vector((0, 0.0, 0.70)), 'root'))
    d.append(('spine', Vector((0, 0.0, 0.70)), Vector((0, 0.004, 0.80)), 'hips'))
    d.append(('chest', Vector((0, 0.004, 0.80)), B.NECK_BASE, 'spine'))
    d.append(('neck', B.NECK_BASE, B.NECK_TOP, 'chest'))
    d.append(('head', B.NECK_TOP, Vector((0, 0.02, 1.36)), 'neck'))
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
        # side lock: from below the jaw, through the tie, to its blunt end
        pts = [Vector((side * 0.205, -0.084, 1.105)), Vector((side * 0.205, -0.088, B.CHIN_Z - 0.055)),
               Vector((side * 0.204, -0.094, 0.93)), Vector((side * 0.198, -0.106, 0.86))]
        par = 'head'
        for k in range(3):
            n = 'lock_%s_%d' % (sx, k)
            d.append((n, pts[k], pts[k + 1], par))
            par = n
        # the tamoto (sleeve bag): two bones down its middle, from under the forearm to its bottom
        s0, s1, s2 = tamoto_chain_points(side)
        d.append(('sleeve_%s_0' % sx, s0, s1, 'forearm_' + sx))
        d.append(('sleeve_%s_1' % sx, s1, s2, 'sleeve_%s_0' % sx))
    # long hair: one chain down each of its three bunches (her right, the middle, her left)
    for i in range(len(HAIR_CHAIN_Z)):
        par = 'head'
        pts = hair_chain_points(i)
        for k in range(len(pts) - 1):
            n = 'hair_%d_%d' % (i, k)
            d.append((n, pts[k], pts[k + 1], par))
            par = n
    # haori panels: front left / right, back left / right, from the hips to the hem
    for key, ang in COAT_PANELS.items():
        pts = coat_chain_points(ang)
        par = 'hips'
        for k in range(len(pts) - 1):
            n = 'coat_%s_%d' % (key, k)
            d.append((n, pts[k], pts[k + 1], par))
            par = n
    # the hat cords' tails under the chin
    knot = Vector((0.0, -0.150, B.CHIN_Z - 0.028))
    d.append(('cord_0', knot, knot + Vector((0, -0.012, -0.05)), 'head'))
    d.append(('cord_1', knot + Vector((0, -0.012, -0.05)), knot + Vector((0, -0.02, -0.095)), 'cord_0'))
    # the sash's two tails from the bow
    from kasasagi.clothes import TAIL_A, TAIL_B
    for key, pts in (('A', TAIL_A), ('B', TAIL_B)):
        par = 'hips'
        for k in range(len(pts) - 1):
            n = 'sash%s_%d' % (key, k)
            d.append((n, pts[k], pts[k + 1], par))
            par = n
    return d


def tamoto_chain_points(side):
    from kasasagi.clothes import tamoto_corners
    top_o, top_i, bot_o, bot_i = tamoto_corners(side)
    top = top_o.lerp(top_i, 0.5)
    bot = bot_o.lerp(bot_i, 0.5)
    return top, top.lerp(bot, 0.5), bot


# the long hair's chains, one per bunch (model.HAIR_BUNCHES: her right, the middle, her left), from
# the nape to the bunch's tip: each bunch swings as one piece, the outer two apart from the middle
HAIR_CHAIN_Z = [(1.03, 0.33), (1.03, 0.64), (1.03, 0.33)]
COAT_PANELS = {'FL': 0.62, 'FR': -0.62, 'BL': 2.2, 'BR': -2.2, 'SL': 1.45, 'SR': -1.45}   # angle from the front, + to her left


def hair_chain_points(i):
    """Five points down bunch i's centre line (model._bunch_centre), behind her back."""
    from kasasagi.model import coat_back_y, HAIR_BUNCHES, _bunch_centre
    cf, hw, n, z_end, x_end = HAIR_BUNCHES[i]
    z0, z1 = HAIR_CHAIN_Z[i]
    pts = []
    for k in range(5):
        z = z0 + (z1 - z0) * k / 4
        x = _bunch_centre(cf, z, x_end, z_end)
        y = coat_back_y(min(max(z, 0.2), 0.982)) * (1 - 0.45 * cf * cf) + 0.06
        pts.append(Vector((x, y, z)))
    return pts


def coat_chain_points(ang):
    from kasasagi.clothes import coat_slice
    pts = []
    for z in (0.66, 0.44, 0.22):
        X, Yd, yc, g = coat_slice(z)
        t = math.pi / 2 - ang          # 0 = her left, pi/2 = front
        pts.append(Vector((X * math.cos(t) * 1.02, yc - Yd * math.sin(t) * 1.02, z)))
    return pts


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
        # bones that point forward (root, feet, toes) take "up" as their Z: forward would be along them
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
    # keep the four strongest
    top = sorted(w.items(), key=lambda kv: -kv[1])[:4]
    s = sum(v for _, v in top)
    return {k: v / s for k, v in top}


def _chain(prefix, n, t):
    """Weights along a chain of n bones for t in [0, 1] (0 = root of bone 0 .. 1 = tip of the last):
    each bone peaks over its own span, neighbours share the joints."""
    w = {}
    x = t * n
    for k in range(n):
        c = k + 0.5
        d = abs(x - c)
        v = max(0.0, 1.0 - d / 0.85)
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
    if z > 0.94:
        return _blend({'chest': 1.0}, {'neck': 1.0}, smooth((z - 0.955) / 0.03))
    if z > 0.80:
        return _blend({'spine': 1.0}, {'chest': 1.0}, smooth((z - 0.78) / 0.06))
    if z > 0.68:
        return _blend({'hips': 1.0}, {'spine': 1.0}, smooth((z - 0.68) / 0.06))
    return {'hips': 1.0}


def _side_of(x):
    return 'L' if x >= 0 else 'R'


def weights_for(p, tag):
    seg = tag.get('seg', '')
    if seg in ('head', 'hair_cap', 'hair_bang'):
        if p.z < B.CHIN_Z + 0.03 and seg == 'head':
            return _blend({'head': 1.0}, {'neck': 1.0}, smooth((B.CHIN_Z + 0.03 - p.z) / 0.06) * 0.5)
        return {'head': 1.0}
    if seg == 'neck':
        return _blend({'neck': 1.0}, {'head': 1.0}, smooth((p.z - 1.04) / 0.05)) if p.z > 1.0 else \
            _blend({'chest': 1.0}, {'neck': 1.0}, smooth((p.z - 0.95) / 0.05))
    if seg == 'hat':
        return {'hat': 1.0}
    if seg == 'hair_side':
        sx = _side_of(p.x)
        if p.z > 1.12:
            return {'head': 1.0}
        t = (1.105 - p.z) / (1.105 - 0.86)
        w = _chain('lock_%s_' % sx, 3, max(0.0, min(1.0, t)))
        return _blend(w, {'head': 1.0}, smooth((p.z - 1.06) / 0.06))
    if seg == 'hair_back':
        f = tag.get('x', 0.0)
        if p.z > 1.12:
            return {'head': 1.0}

        def on_chain(i):
            z0, z1 = HAIR_CHAIN_Z[i]
            return _chain('hair_%d_' % i, 4, max(0.0, min(1.0, (z0 - p.z) / (z0 - z1))))
        bunch = tag.get('bunch', -1)
        if bunch >= 0:
            # a bunch's clumps hang on its own chain only: the bunches part when they swing
            w = on_chain(bunch)
        else:
            # the dark inner layer (behind the head and shoulders) shares the chains by its place
            right = smooth((-f - 0.15) / 0.45)
            left = smooth((f - 0.15) / 0.45)
            mid = max(0.0, 1.0 - right - left)
            tot = right + mid + left
            w = {}
            for i, k in ((0, right), (1, mid), (2, left)):
                if k > 0:
                    for bn, v in on_chain(i).items():
                        w[bn] = w.get(bn, 0.0) + v * k / tot
        return _blend(w, {'head': 1.0}, smooth((p.z - 0.99) / 0.12))
    if seg in ('torso', 'bow'):
        if seg == 'torso' and p.z > 0.90 and abs(p.x) > 0.09:
            sx = _side_of(p.x)
            return _blend(_torso_w(p.z), {'shoulder_' + sx: 1.0}, smooth((abs(p.x) - 0.09) / 0.05) * 0.5)
        return _torso_w(p.z)
    if seg in ('coat', 'coat_band'):
        return _coat_w(p, tag)
    if seg == 'sleeve':
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        u = tag.get('u', 0.0)
        u_el = 0.50
        w = _blend({'shoulder_' + sx: 1.0}, {'upper_arm_' + sx: 1.0}, smooth(u / 0.14))
        w = _blend(w, {'forearm_' + sx: 1.0}, smooth((u - (u_el - 0.08)) / 0.16))
        # where the sleeve meets the body, keep it on the chest
        if u < 0.08:
            w = _blend(w, {'chest': 1.0}, (0.08 - u) / 0.08 * 0.6)
        return w
    if seg == 'tamoto':
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        u = tag.get('u', 0.0)
        x = tag.get('x', 0.5)
        # the top hangs from the forearm (the outer corner from the elbow), the rest from the chain
        arm = _blend({'forearm_' + sx: 1.0}, {'upper_arm_' + sx: 1.0}, smooth((x - 0.75) / 0.25) * 0.5)
        ch = _chain('sleeve_%s_' % sx, 2, max(0.0, min(1.0, u)))
        return _blend(arm, ch, smooth(u / 0.35))
    if seg == 'hand':
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        u = tag.get('u', 1.0)
        return _blend({'forearm_' + sx: 1.0}, {'hand_' + sx: 1.0}, smooth(u / 0.3))
    if seg == 'leg':
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        u = tag.get('u', 0.0)
        u_knee = 0.47
        w = _blend({'thigh_' + sx: 1.0}, {'shin_' + sx: 1.0}, smooth((u - (u_knee - 0.07)) / 0.14))
        if u < 0.18:
            w = _blend({'hips': 1.0}, w, smooth(u / 0.18))
        return w
    if seg == 'foot':
        sx = 'L' if tag.get('side', 1) > 0 else 'R'
        u = tag.get('u', 0.0)
        w = _blend({'shin_' + sx: 1.0}, {'foot_' + sx: 1.0}, smooth(u / 0.25))
        return _blend(w, {'toe_' + sx: 1.0}, smooth((u - 0.7) / 0.2))
    if seg == 'cord':
        u = tag.get('u', 0.0)
        return _blend({'head': 1.0}, _chain('cord_', 2, u), smooth(u / 0.3))
    if seg == 'sash':
        u = tag.get('u', 0.0)
        key = tag.get('chain', 'A')
        n = 4
        w = _chain('sash%s_' % key, n, max(0.0, min(1.0, (u - 0.04) / 0.96)))
        return _blend({'hips': 1.0}, w, smooth(u / 0.12))
    return {'hips': 1.0}


def _coat_w(p, tag):
    z = p.z
    if z > 0.70:
        w = _torso_w(z)
        if z > 0.90 and abs(p.x) > 0.10:
            w = _blend(w, {'shoulder_' + _side_of(p.x): 1.0}, smooth((abs(p.x) - 0.10) / 0.05) * 0.6)
        return w
    # below the obi: the hips carry the cloth, the panels' chains swing it, the thighs push the front
    t = (0.66 - z) / (0.66 - 0.22)
    t = max(0.0, min(1.0, t))
    ang = math.atan2(p.x, -p.y)            # 0 front, + her left, ~pi back
    keys = list(COAT_PANELS.items())
    # nearest two panels by angle
    dists = sorted(((abs((ang - a + math.pi) % (2 * math.pi) - math.pi), k) for k, a in keys))
    (d0, k0), (d1, k1) = dists[0], dists[1]
    share = d0 / max(1e-4, d0 + d1)
    chain = _blend(_chain('coat_%s_' % k0, 2, t), _chain('coat_%s_' % k1, 2, t), share)
    w = _blend({'hips': 1.0}, chain, smooth(t * 1.6) * 0.85)
    # the front panels also follow her thighs a little (her knees must not poke through)
    front = smooth((math.cos(ang) - 0.2) / 0.6)
    if front > 0:
        sx = _side_of(p.x)
        w = _blend(w, {'thigh_' + sx: 1.0}, front * 0.35 * smooth(t * 2.0))
    if z > 0.62:
        w = _blend(w, _torso_w(z), smooth((z - 0.62) / 0.08))
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
