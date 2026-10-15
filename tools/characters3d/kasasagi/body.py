"""百々かさゝぎ's proportions and skeleton (rest pose), shared by the model, the rig and the animations.

Blender coordinates, metres: Z up, she faces -Y, her left is +X. The game draws 30 native px per
metre and leans upright things back (docs/knowledge/21 §1), so on screen a vertical metre is 30 px
and depth toward the camera adds 0.819 px per px (the head's depth makes it look taller than it is
tall). Targets on screen (native px): hat top to soles about 57-60 px, head (crown to chin) about
19-21 px with the face (eye top to chin) about 9 px, eyes 4 x 5 px.
"""
from mathutils import Vector

S = 1.0                     # global scale knob (kept 1: the numbers below are the design)

# ---- head (the chibi head: about 3 heads to the crown) -----------------------------------------
CHIN_Z = 1.06               # bottom of the chin
HEAD_H = 0.50               # chin to crown
HEAD_TOP = CHIN_Z + HEAD_H
# face landmarks in head space (h = height above the chin, y = front surface); the stamps of the
# face (eyes, brows, mouth) are drawn at these points, projected on screen every frame
EYE_H = 0.190               # eye centre height above the chin
EYE_X = 0.100               # eye centre half spacing (3 px either side of the face's centre line)
MOUTH_H = 0.075
BROW_H = 0.305              # on the strip of forehead under the bangs (brows carry the expressions)
BANG_CUT_H = 0.420          # the hime cut: bangs end here, a strip of forehead above the brows

# ---- neck, torso -------------------------------------------------------------------------------
NECK_BASE = Vector((0, 0.012, 0.965))
NECK_TOP = Vector((0, 0.020, 1.075))
HIPS = Vector((0, 0.0, 0.62))
SPINE = Vector((0, 0.0, 0.725))
CHEST = Vector((0, 0.004, 0.845))
SHOULDER_Z = 0.948

# ---- arms (rest = the art's resting pose, A_01: elbows out at her sides, forearms across the front,
# hands meeting below the obi; the wide sleeves hang from the forearms as two flags facing front) ---
CLAV_IN = Vector((0.03, 0.012, 0.945))
SHOULDER = Vector((0.125, 0.014, 0.950))
ELBOW = Vector((0.200, 0.012, 0.800))
WRIST = Vector((0.098, -0.090, 0.684))
HAND_TIP = Vector((0.052, -0.120, 0.656))

# ---- legs ----------------------------------------------------------------------------------------
HIP_JOINT = Vector((0.068, 0.0, 0.615))
KNEE = Vector((0.072, -0.012, 0.365))
ANKLE = Vector((0.074, 0.010, 0.098))
BALL = Vector((0.076, -0.070, 0.026))
TOE = Vector((0.077, -0.112, 0.022))

# ---- hat -----------------------------------------------------------------------------------------
HAT_SEAT = Vector((0, 0.020, 1.565))   # the crown, where the head ring sits (the hat bone's head:
                                       # the game tilts the hat about this point)
HAT_R = 0.50
HAT_H = 0.185


def mirror(v):
    return Vector((-v.x, v.y, v.z))
