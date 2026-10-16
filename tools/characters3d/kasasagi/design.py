"""百々かさゝぎ, round 5 (2026-10-16, decision-log G5R3-6..8): the design numbers of the two proposals.

  A  the ChatGPT model sheet (scratchpad gdrive x_v2_84_final/models: turnaround, hair, hat, clothes,
     colours): Q-version about 3 heads, long hair to the knees, a long haori with pointed hems,
     sleeves to the knee, a red ribbon tied round the hat's crown
  B  the v0.2 sprite's front and back (the user liked them; its side view and the other characters
     are not references): a squat body under a very wide hat, the face small and low, bell sleeves,
     hair to the waist as one sheet, a red stripe down the hat

Pick one with C3D_VARIANT=A|B (default below). Everything else reads D[...].

The screen (docs/knowledge/21 §1): 30 native px per metre; upright things are leaned back by
k = tan 27.5 deg, so a point's screen height is y - 0.819 z (z toward the camera): vertical metres are
1:1, depth toward the camera pulls a point down. In effect upright things are seen from
atan(sin 55 deg) = 39.3 deg above. Two consequences shape the head:
  * the face must be a near-vertical plate (a receding chin is pulled up on screen and the face
    shrinks), and
  * a wide hat worn level hides the face; tipped back past 50.7 deg it shows its navy underside (the
    rejected round-4 halo). Tipped back 20-24 deg the white top shows as a flat ellipse over the face,
    as in the v0.2 sprite, and the eyes clear the front brim if the crown stands high above them: a
    big cranium over a small, low face (the baby schema).
"""
import os

VARIANT = os.environ.get('C3D_VARIANT', 'A').upper()

_COMMON = {
    # the face (heights above the chin, metres; 1 native px = 0.0333 m)
    'eye_h': 0.172,            # eye centre: three rows 0.122..0.222, the bangs end on the top row
    'eye_x': 0.083,            # eye centre half spacing: 2 px eyes, 3 px between them
    'face_y': 0.200,           # the face plate's front (distance in front of the head's axis)
    'face_w': 0.182,           # half width of the face at the cheeks (11 px)
    'bang_cut': 0.214,         # the hime cut: just over the eyes' top row (the bangs press on it)
    'mouth_h': 0.062,
    'cheek_h': 0.105,
    'cheek_x': 0.128,
}

_D = {
    'A': dict(_COMMON, **{
        'name': 'A (ChatGPT sheet)',
        'chin_z': 1.20,
        'head_h': 0.52,            # chin to crown
        'cranium_w': 0.232,        # half width at the widest (above the ears)
        'cranium_back': 0.215,
        # hat (sugegasa): radius, cone height, how far the brim plane sits below the crown
        'hat_r': 0.60, 'hat_h': 0.27, 'hat_sink': 0.12,
        'hat_tilt': 22.0, 'hat_tilt_away': 22.0, 'hat_roll': 6.0,
        'hat_band': 'ribbon',      # a red ribbon round the crown, tied, with a tail
        # hair
        'lock_tie_h': -0.17,       # the side locks' ties, height above the chin (chest)
        'lock_end_h': -0.33,
        'back_hair_end': 0.42,     # the long hair's end, height above the ground (knees)
        'back_hair_w': 0.23,
        # body
        'shoulder_w': 0.150, 'shoulder_z': 1.06, 'neck_base': 1.10,
        'obi_z': (0.80, 0.90), 'hip_z': 0.70, 'knee_z': 0.40, 'ankle_z': 0.11,
        'coat_hem': 0.28,          # the haori's lowest points
        'coat_flare': 0.30,        # its half width at the hem
        'sleeve_hem': 0.50, 'sleeve_w': 0.40,    # sleeve bottom height; outer edge from the middle
        'hand_z': 0.64,            # the hand's tip (hanging arm): out of the cuff, over the hanging sleeve
        'trouser_puff': 0.135,
        'foot_len': 0.20,
        'bow': 'front',
        'hem_style': 'points',     # the haori's pointed hems
        'sleeve_slant': 0.10,      # the sleeve's hem lower on the outside (the hanging bag)
    }),
    'B': dict(_COMMON, **{
        'name': 'B (v0.2 sprite)',
        'chin_z': 1.12,
        'head_h': 0.56,
        'cranium_w': 0.245,
        'cranium_back': 0.225,
        'hat_r': 0.69, 'hat_h': 0.24, 'hat_sink': 0.12,
        'hat_tilt': 22.0, 'hat_tilt_away': 22.0, 'hat_roll': 0.0,
        'hat_band': 'stripe',      # a red stripe from the apex down to the front right of the brim
        'lock_tie_h': -0.05,       # just under the chin, as in the sprite
        'lock_end_h': -0.17,
        'back_hair_end': 0.66,     # to the small of her back
        'back_hair_w': 0.215,
        'shoulder_w': 0.150, 'shoulder_z': 0.99, 'neck_base': 1.03,
        'obi_z': (0.74, 0.84), 'hip_z': 0.64, 'knee_z': 0.34, 'ankle_z': 0.10,
        'coat_hem': 0.36,
        'coat_flare': 0.30,
        'sleeve_hem': 0.52, 'sleeve_w': 0.47,
        'hand_z': 0.50,            # the hands just show under the bell sleeves' hems
        'trouser_puff': 0.13,
        'foot_len': 0.19,
        'bow': 'left',
        'hem_style': 'round',
        'sleeve_slant': 0.0,
    }),
}

D = _D[VARIANT]


def get(key):
    return D[key]
