"""Animation clips as code: poses are {bone: (rx, ry, rz) degrees in the bone's local axes} (see the
character's rigging.py for the axis convention), plus optional root offsets, keyed on frames.

Two ways to write a clip:
  * key poses with eased in-betweens: Clip.key(frame, pose) ... (Bezier, auto-clamped; looping clips
    use cycle-aware handles so the seam has no hitch);
  * a function of the phase: Clip.sample(fn, step) keys fn(t) every `step` frames (cycles like the
    walk, where every joint is a smooth function of the gait phase).
All clips are pushed to NLA tracks so the glTF exporter writes each as its own animation.
"""
import math
import bpy
from mathutils import Euler, Quaternion, Vector, Matrix

FPS = 30


def q_of(r):
    """(rx, ry, rz[, order]) degrees -> quaternion. The order (default 'XYZ': the forward bend first)
    can be 'ZXY' for a limb raised sideways first, then brought forward."""
    if isinstance(r, Quaternion):
        return r
    order = r[3] if len(r) > 3 else 'XYZ'
    return Euler((math.radians(r[0]), math.radians(r[1]), math.radians(r[2])), order).to_quaternion()


def _is_q(v):
    return isinstance(v, Quaternion)


def add_pose(*poses):
    """Layers poses channel by channel. Euler triples add (fine for the moderate angles of layering);
    where either value is a quaternion (an aimed limb), the later one is applied on top of the earlier
    one in the bone's own turned frame (q_a @ q_b)."""
    out = {}
    for p in poses:
        for k, v in p.items():
            if k.endswith('@loc'):
                o = out.get(k, (0.0, 0.0, 0.0))
                out[k] = (o[0] + v[0], o[1] + v[1], o[2] + v[2])
                continue
            if k not in out:
                out[k] = v
                continue
            o = out[k]
            if _is_q(o) or _is_q(v):
                out[k] = q_of(o) @ q_of(v)
            else:
                order = v[3] if len(v) > 3 else (o[3] if len(o) > 3 else None)
                t = (o[0] + v[0], o[1] + v[1], o[2] + v[2])
                out[k] = t + ((order,) if order else ())
    return out


def scale_pose(p, s):
    out = {}
    for k, v in p.items():
        if _is_q(v):
            out[k] = Quaternion().slerp(v, s)
        else:
            out[k] = (v[0] * s, v[1] * s, v[2] * s) + tuple(v[3:])
    return out


def lerp_pose(a, b, t):
    keys = set(a) | set(b)
    out = {}
    for k in keys:
        va = a.get(k, (0.0, 0.0, 0.0))
        vb = b.get(k, (0.0, 0.0, 0.0))
        if k.endswith('@loc'):
            out[k] = tuple(va[i] + (vb[i] - va[i]) * t for i in range(3))
        elif _is_q(va) or _is_q(vb):
            out[k] = q_of(va).slerp(q_of(vb), t)
        else:
            out[k] = tuple(va[i] + (vb[i] - va[i]) * t for i in range(3)) + tuple(vb[3:] or va[3:])
    return out


def aim(arm, chain, base=None):
    """Quaternion poses that point bones along world directions (armature space, Blender axes: x her
    left, -y forward, z up), the parents first: chain = [(bone, direction, twist_deg), ...]. `base`
    (a pose) is applied to the bones' parents above the chain (e.g. the chest's turn). The result
    keeps each bone's roll as close to its rest roll as the swing allows (shortest arc)."""
    out = {}
    posed = {}

    def posed_rot(bname):
        if bname in posed:
            return posed[bname]
        b = arm.data.bones[bname]
        rest = b.matrix_local.to_3x3()
        if b.parent is None:
            parent_posed = Matrix.Identity(3)
            parent_rest = Matrix.Identity(3)
        else:
            parent_posed = posed_rot(b.parent.name)
            parent_rest = b.parent.matrix_local.to_3x3()
        q = out.get(bname) or (q_of(base[bname]) if base and bname in base and not bname.endswith('@loc') else Quaternion())
        m = parent_posed @ parent_rest.inverted() @ rest @ q.to_matrix()
        posed[bname] = m
        return m

    for bname, direction, twist in chain:
        b = arm.data.bones[bname]
        rest = b.matrix_local.to_3x3()
        if b.parent is None:
            m0 = rest
        else:
            m0 = posed_rot(b.parent.name) @ b.parent.matrix_local.to_3x3().inverted() @ rest
        d_local = (m0.inverted() @ Vector(direction).normalized()).normalized()
        q = Vector((0, 1, 0)).rotation_difference(d_local)
        if twist:
            q = q @ Quaternion(Vector((0, 1, 0)), math.radians(twist))
        out[bname] = q
        posed.pop(bname, None)
    return out


class Clip:
    def __init__(self, arm, name, frames, loop=False):
        self.arm = arm
        self.name = name
        self.frames = frames
        self.loop = loop
        self.action = bpy.data.actions.new(name)
        self.keys = []
        ad = arm.animation_data or arm.animation_data_create()
        ad.action = self.action

    def _world_to_local(self, bone_name, d):
        b = self.arm.data.bones[bone_name]
        return b.matrix_local.to_3x3().inverted() @ Vector(d)

    def key(self, frame, pose, interp='BEZIER'):
        """pose: {bone: (rx, ry, rz)}; '<bone>@loc': (x, y, z) world-axis offset of that bone."""
        arm = self.arm
        for pb in arm.pose.bones:
            pb.rotation_quaternion = Quaternion()
            pb.location = Vector()
        touched = set()
        for k, v in pose.items():
            if k.endswith('@loc'):
                bn = k[:-4]
                arm.pose.bones[bn].location = self._world_to_local(bn, v)
                touched.add((bn, 'location'))
            else:
                if k not in arm.pose.bones:
                    continue
                arm.pose.bones[k].rotation_quaternion = q_of(v)
        for pb in arm.pose.bones:
            pb.keyframe_insert('rotation_quaternion', frame=frame, group=pb.name)
            if pb.name in ('root', 'hips') or (pb.name, 'location') in touched:
                pb.keyframe_insert('location', frame=frame, group=pb.name)
        self.keys.append((frame, interp))

    def sample(self, fn, step=1):
        """fn(t in [0, 1)) -> pose; keyed every `step` frames, the last key closes the loop."""
        f = 0
        while f <= self.frames:
            t = (f % self.frames) / self.frames if self.loop else f / self.frames
            self.key(f, fn(t), interp='BEZIER')
            f += step

    def finish(self):
        fcs = _fcurves(self.action)
        for fc in fcs:
            if self.loop:
                m = fc.modifiers.new('CYCLES')
            for kp in fc.keyframe_points:
                kp.interpolation = 'BEZIER'
                kp.handle_left_type = 'AUTO_CLAMPED' if not self.loop else 'AUTO'
                kp.handle_right_type = 'AUTO_CLAMPED' if not self.loop else 'AUTO'
            fc.update()
        ad = self.arm.animation_data
        track = ad.nla_tracks.new()
        track.name = self.name
        strip = track.strips.new(self.name, 0, self.action)
        strip.action_frame_end = self.frames
        track.mute = True
        ad.action = None
        return self


def _fcurves(action):
    """F-curves of an action (Blender 4.4+ slotted actions keep them in layers / strips / channelbags)."""
    out = []
    if hasattr(action, 'layers') and len(action.layers):
        for layer in action.layers:
            for strip in layer.strips:
                for cb in getattr(strip, 'channelbags', []):
                    out += list(cb.fcurves)
    if not out and hasattr(action, 'fcurves'):
        out = list(action.fcurves)
    return out


def apply_pose(arm, pose):
    for pb in arm.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = Vector()
    for k, v in pose.items():
        if k.endswith('@loc'):
            bn = k[:-4]
            b = arm.data.bones[bn]
            arm.pose.bones[bn].location = b.matrix_local.to_3x3().inverted() @ Vector(v)
        elif k in arm.pose.bones:
            arm.pose.bones[k].rotation_quaternion = q_of(v)
    bpy.context.view_layer.update()
