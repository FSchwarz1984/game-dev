"""百々かさゝぎ's proportions and skeleton points (rest pose), derived from design.py; shared by the
model, the rig and the animations.

Blender coordinates, metres: Z up, she faces -Y, her left is +X. On screen (docs/knowledge/21 §1)
a point's height is 30 px per metre of (z_up - 0.819 * forward): see design.py for what that does
to a head under a wide hat.

Rest pose (round 5): she stands with her arms hanging inside the wide sleeves, hands just showing at
the sleeves' hems, as in the v0.2 sprite; every standing animation starts from it.
"""
from mathutils import Vector

from kasasagi.design import D

S = 1.0

# ---- head --------------------------------------------------------------------------------------
CHIN_Z = D['chin_z']
HEAD_H = D['head_h']
HEAD_TOP = CHIN_Z + HEAD_H
HEAD_YC = 0.012                 # the head's axis sits a little behind the body's
EYE_H = D['eye_h']
EYE_X = D['eye_x']
MOUTH_H = D['mouth_h']
BANG_CUT_H = D['bang_cut']
FACE_Y = D['face_y']
FACE_W = D['face_w']

# ---- neck, torso -------------------------------------------------------------------------------
SHOULDER_Z = D['shoulder_z']
NECK_BASE = Vector((0, 0.010, D['neck_base']))
NECK_TOP = Vector((0, 0.018, CHIN_Z + 0.03))
HIPS = Vector((0, 0.0, D['hip_z']))
SPINE = Vector((0, 0.0, D['hip_z'] + 0.5 * (D['obi_z'][0] - D['hip_z']) + 0.04))
CHEST = Vector((0, 0.004, D['obi_z'][1] + 0.05))
OBI_Z = D['obi_z']

# ---- arms: hanging, a little out from her sides, the elbows soft --------------------------------
SW = D['shoulder_w']
CLAV_IN = Vector((0.03, 0.010, SHOULDER_Z - 0.006))
SHOULDER = Vector((SW, 0.012, SHOULDER_Z))
_arm_len = SHOULDER_Z - D['hand_z']
ELBOW = Vector((SW + 0.030, 0.012, SHOULDER_Z - _arm_len * 0.44))
WRIST = Vector((SW + 0.040, -0.020, SHOULDER_Z - _arm_len * 0.86))
HAND_TIP = Vector((SW + 0.040, -0.040, D['hand_z']))

# ---- legs ----------------------------------------------------------------------------------------
HIP_JOINT = Vector((0.072, 0.0, D['hip_z'] - 0.035))
KNEE = Vector((0.078, -0.010, D['knee_z']))
ANKLE = Vector((0.080, 0.012, D['ankle_z']))
BALL = Vector((0.082, -0.075, 0.026))
TOE = Vector((0.083, -(D['foot_len'] - 0.07), 0.022))

# ---- hat -----------------------------------------------------------------------------------------
# the seat: the crown of the head, where the hat rests (the hat bone's head: the game tilts the hat
# about this point)
HAT_SEAT = Vector((0, HEAD_YC, HEAD_TOP))
HAT_R = D['hat_r']
HAT_H = D['hat_h']
HAT_SINK = D['hat_sink']


def mirror(v):
    return Vector((-v.x, v.y, v.z))
