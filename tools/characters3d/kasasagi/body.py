"""百々かさゝぎ's skeleton points, round 6, in the model sheet's A pose (design.py): shared by the
model, the rig and the animations.

Blender coordinates, metres: Z up, she faces -Y, her left is +X.
"""
import math
from mathutils import Vector

from kasasagi.design import D

# ---- head ----------------------------------------------------------------------------------------
CHIN_Z = D['chin_z']
HEAD_TOP = D['head_top']
HEAD_H = HEAD_TOP - CHIN_Z
HEAD_YC = -D['head_f']          # the head's axis (forward is -Y)
EYE_H = D['eye_h']
EYE_X = D['eye_x']
MOUTH_H = D['mouth_h']
BANG_CUT_H = D['bang_cut']
FACE_W = D['face_w']
FACE_F = D['face_f']

# ---- neck, torso ---------------------------------------------------------------------------------
SHOULDER_Z = D['shoulder_z']
NECK_BASE = Vector((0, 0.012, D['neck_base']))
NECK_TOP = Vector((0, HEAD_YC + 0.02, CHIN_Z + 0.04))
HIPS = Vector((0, 0.0, D['hip_z']))
SPINE = Vector((0, 0.0, 0.80))
CHEST = Vector((0, 0.004, 1.00))
OBI_Z = D['obi_z']

# ---- arms: the A pose (41 deg below level), the elbow nearly straight -------------------------
SW = D['shoulder_w']
CLAV_IN = Vector((0.03, 0.010, SHOULDER_Z + 0.02))
SHOULDER = Vector((SW, 0.012, SHOULDER_Z))
_wx, _wz = D['wrist']
WRIST = Vector((_wx, -0.01, _wz))
ELBOW = SHOULDER.lerp(WRIST, 0.52) + Vector((0, 0.012, 0))
_dir = (WRIST - SHOULDER).normalized()
HAND_TIP = WRIST + _dir * D['hand_len'] + Vector((0, -0.01, -0.02))
ARM_DIR = _dir

# ---- legs ----------------------------------------------------------------------------------------
LX = D['leg_x']
HIP_JOINT = Vector((LX * 0.62, 0.0, D['hip_z'] - 0.04))
KNEE = Vector((LX * 0.92, -0.010, D['knee_z']))
ANKLE = Vector((LX, 0.010, D['ankle_z']))
BALL = Vector((LX, -0.10, 0.03))
TOE = Vector((LX, -(D['foot_len'] * 0.5 + D['foot_f']) + 0.02, 0.025))

# ---- hat -----------------------------------------------------------------------------------------
HAT_R = D['hat_r']
HAT_H = D['hat_h']
# the brim's centre and the hat's frame: tilted back (front up) by hat_tilt, rolled (her left down)
HAT_C = Vector((0.0, -D['hat_centre_f'], D['hat_centre_h']))
_t = math.radians(D['hat_tilt'])
_r = math.radians(D['hat_roll'])


def hat_frame():
    """(centre, up, forward, left): the hat's axes in rest pose."""
    c, s = math.cos(_t), math.sin(_t)
    # tilt back about her left axis: the front edge rises, the axis leans back (+Y)
    up = Vector((0, s, c))
    fwd = Vector((0, -c, s))
    left = Vector((1, 0, 0))
    # roll about the forward axis: her left side down, the axis leans to her left
    cr, sr = math.cos(_r), math.sin(_r)
    up2 = up * cr + left * sr
    left2 = left * cr - up * sr
    return HAT_C.copy(), up2.normalized(), fwd.normalized(), left2.normalized()


# the seat: the crown of the head (the hat bone's head)
HAT_SEAT = Vector((0, HEAD_YC, HEAD_TOP))


def mirror(v):
    return Vector((-v.x, v.y, v.z))
