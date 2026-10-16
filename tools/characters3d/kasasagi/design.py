"""百々かさゝぎ, round 6 (2026-10-16, decision-log G5R3-17): the model is built to the ChatGPT model
sheet as a blueprint (scratchpad gdrive x_v2_84_final/models: Tiangan_v2_kasasagi_turnaround.png, with
the hat, clothes, hair, colours and face sheets for detail). Rounds 4 and 5 were tuned by eye; this one
takes every number from the sheet.

Blueprint frame. The turnaround is 2048 x 832; its five views are cut by tools in the scratchpad
(chars6/tools/sheetmask.py). Per view, local pixels (u right, v down) from the figure's bounding box:
    front    box x 45..482,   y 100..760: ground (sole) v = 660, body axis u = 218 (the face, the
             collar's V; the feet are drawn 11 px left of it)
    side     box x 844..1195, y 102..759: ground v = 657, axis u = 192 (the shin); she faces left,
             so we see her left side
    back     box x 1575..2002, y 99..761: ground v = 662, axis u = 205
The scale: the figure, sole to hat apex, is 660 px; she is 1.90 m tall to the apex (30 native px per
metre: about 57 px on screen), so one sheet pixel is S = 1.90 / 660 m. Heights are h = (ground - v) S,
her left x = (u - axis) S in the front view (her left is on the viewer's right), forward
f = (axis - u) S in the side view.

Where the views disagree, the front view wins, then the side (the lead's rule): the hat is 431 px
across in the front view but 350 px in the side view; it is built 1.24 m across (the front).
The back view is drawn mirrored for the asymmetric details (the hat's tail and the sash's long tail
hang on her left in the front, three-quarter and side views and on her right in the back view): they
are built on her left.

Coordinates (Blender): metres, Z up, she faces -Y, her left is +X.
"""
import math

S = 1.90 / 660.0                 # metres per sheet pixel


def hf(v, ground=660):
    """Height of a sheet row (front view by default)."""
    return (ground - v) * S


def xf(u, axis=218):
    """Her-left x of a front-view column."""
    return (u - axis) * S


def fs(u, axis=192):
    """Forward distance of a side-view column (she faces left)."""
    return (axis - u) * S


D = {
    'name': 'round6',
    # ---- the hat (front: apex (220, 2), brim tips (2, 92) and (432, 125), the brim's raised front
    # edge crossing the centre at v 70; side: front tip (5, 62), back tip (~355, 165), apex (255, 5);
    # hat sheet: height / diameter 0.26, a ring of red band round the crown at 0.34 of the radius)
    'hat_r': 431 / 2 * S,                     # 0.620
    'hat_h': 0.318,                            # cone height (apex above the brim's plane)
    'hat_centre_h': hf(110),                   # 1.583: the brim's centre (front: v 70 front edge,
                                               # v 150 back edge behind the head)
    'hat_centre_f': 0.02,                      # forward of the body axis (side: tips at +0.52 / -0.47)
    'hat_tilt': 14.0,                          # deg, the front raised (front view 10.7, side 16.6)
    'hat_roll': 4.4,                           # deg, her left side down (front: tips 33 px apart)
    'hat_crown': 0.36,                         # the crown knob: the cone steepens above this fraction
                                               # of the radius (hat sheet side view)
    'hat_ring_r': 0.44,                        # the red ring round the crown, fraction of the radius (front
                                               # view: v 25..45, mid-way down the visible cone; the hat
                                               # sheet draws it at 0.34)
    'hat_band_w': 0.100,                       # the band's width (front: 15-20 px seen nearly edge-on)
    'hat_strap_angle': 58.0,                   # deg: the strap the front view shows, down the cone's
                                               # front-left to the brim at x 0.48
    'hat_straps': [float(a) for a in __import__('os').environ.get('C3D_HAT_STRAPS', '58,155').split(',') if a],
    'hat_tail_angle': 155.0,                   # deg round the brim from her front toward her left: where
                                               # the band crosses the brim and hangs (three-quarter and
                                               # side views: behind her, on her left)
    'hat_tail_end': 1.00,                      # height of the tail's end (side: v 300; three-quarter v 390)
    'hat_tail_w': 0.095,
    # ---- the head (front: bangs cut v 150, eyes v 155..188 at u 182 / 248, face 160..277 wide at
    # v 195, chin v 232, mouth v 207; side: nose f 0.25, chin f 0.18 at h 1.229)
    'chin_z': hf(232),                         # 1.232
    'head_top': 1.77,                          # hidden under the hat (the face sheet: 3.1 eye-to-chin
                                               # lengths from the chin to the crown)
    'face_w': 117 / 2 * S,                     # 0.168: half width at the cheeks
    'face_f': 0.215,                           # the face's front (cheeks) forward of the head axis
    'head_f': 0.02,                            # the head's axis, forward of the body axis (side: the
                                               # ear at f 0, the nose at 0.25)
    'cranium_w': 0.235,                        # half width of the skull (under the hair)
    'cranium_back': 0.235,                     # back of the skull behind the head axis
    'eye_h': hf(172),                          # 1.405: eye centre
    'eye_top': hf(155),                        # 1.454
    'eye_x': 33 * S,                           # 0.095: half the distance between the eye centres
    'eye_w': 38 * S,                           # 0.109
    'eye_hgt': 33 * S,                         # 0.095
    'bang_cut': hf(150),                       # 1.468
    'mouth_h': hf(207),                        # 1.304
    'ear_h': hf(198),
    # ---- hair (front outline: +-0.32 just under the brim, +-0.28 at the chin, +-0.30 at the
    # shoulders, +-0.34 at h 1.04 and on down behind the sleeves to v 470; back view: 200 px wide at
    # v 150, 105 px at v 450, the end at v 490; side: the back of the hair f -0.40)
    'hair_out_w': [(1.62, 0.300), (1.47, 0.318), (1.25, 0.278), (1.10, 0.300), (1.00, 0.330),
                   (0.80, 0.300), (0.62, 0.230), (0.50, 0.170)],
    'back_hair_end': hf(490, 662) + 0.055,     # 0.550: the sheet's end (v 490, h 0.495) less the
                                               # point the mantle's middle hangs below its edge
    'lock_x': 0.196,                           # the side locks' centres (front: u 130..170, 268..308)
    'lock_w': 40 * S,                          # 0.115
    'lock_tie_h': hf(237),                     # 1.218: the white-red-white tie (v 222..252)
    'lock_end_h': hf(330),                     # 0.950
    # ---- body (front: neck v 232..250, kosode shoulders u 160..280 at v 262, collar V to v 300,
    # obi v 323..357 and u 148..290, red band v 330..347)
    'neck_base': hf(250),                      # 1.180
    'shoulder_z': hf(268),                     # 1.128: the shoulder joint
    'shoulder_w': 0.150,                       # the shoulder joint's x
    'shoulder_top_w': 60 * S,                  # 0.173: the kosode's shoulder point
    'collar_v': hf(300),                       # 1.036
    'obi_z': (hf(357), hf(323)),               # 0.872 .. 0.970
    'obi_w': 71 * S,                           # 0.204: half width in front
    'obi_d': 0.150,                            # half depth (side view)
    'band_z': (hf(347), hf(330)),              # the red band over the obi
    'bow_x': 25 * S,                           # 0.072: the knot, a little to her left
    'bow_z': hf(345),                          # 0.907
    'bow_w': 37 * S,                           # loop half width
    'bow_h': 40 * S,
    'tail_short_end': (xf(272), hf(410)),      # (x, h)
    'tail_long_end': (xf(385), hf(615)),
    'tail_w': 0.130,                           # front: 32 px seen at an angle; side: 40-60 px
    'hip_z': 0.66,
    # ---- the arms, in the sheet's A pose (front: shoulder joint ~(165, 285), wrist ~(65, 370), hand
    # centre (42, 392): 41 deg below level)
    'arm_angle': 41.0,
    'wrist': (0.470, 0.840),                   # (|x|, h): at the cuff's top (sheet: the hand leaves the
                                               # cuff at (60, 365), the fingertips at (20, 405))
    'hand_len': 0.14,
    # ---- sleeves (front: the cuff from (50, 355) down to the lowest point (78, 480); side: the bag
    # 0.26 m front to back, lowest at h 0.486)
    'sleeve_bottom': hf(480),                  # 0.518
    'sleeve_depth': 0.130,                     # half, front to back
    # ---- the outer coat (front: the hem's outer corners (90, 582) and (330, 558), the opening's hems at
    # v 520..545, 0.79 m wide at the hem; side: front f +0.34, back -0.23, hem 0.30 front, 0.265 back)
    'coat_hem': 0.225,                         # the lowest corner
    'coat_hem_mid': hf(530),                   # 0.374: the front panels' hems by the opening
    # ---- legs (front: trouser cuffs v 572, legs 80 px wide at v 540, wraps v 578..600, tabi v 600..658,
    # feet at u 152 / 262, 65 px wide; side: toe f +0.23, heel -0.07)
    'leg_x': 0.158,
    'knee_z': 0.36,
    'cuff_z': hf(572),                         # 0.253
    'trouser_r': 40 * S,                       # 0.115: the widest half width of a leg
    'wrap_z': (hf(600), hf(578)),              # 0.173 .. 0.236
    'ankle_z': 0.13,
    'foot_len': 103 * S,                       # 0.297
    'foot_w': 0.200,                           # front: 65 px (0.187) for the tabi, the sole a little wider
    'foot_f': 0.08,                            # the foot's centre forward of the leg
}
