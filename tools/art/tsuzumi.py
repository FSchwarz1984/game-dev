"""百々つゞみ (Tsuzumi Momo) - animations and sheet description (revision 2).

Reference: assets/reference/illustrations/tsuzumi.png. Parts live in tsu_base.py (body, hat, the
back-frame) and tsu_actions.py (action poses). Three sheets:
    load   wearing the back-frame with the wicker box on its shelf
    frame  wearing the old back-frame, empty (day 1); Saji sits on its top rail
    plain  no back-frame
Model space: column 13 is her centre line, row 38 the outline under her soles; it maps into the
56x64 cell at (MX, MY) = (15, 23), so the foot pivot is cell pixel (28, 61). Light: top-left.
The ground line is row 38 in every pose; only the walk's contact frames put the leading foot one
pixel lower in the front and back views (it is nearer the camera).
'<anim>Ride' (front view only): the same frames without the post tips, for when Saji rides.
"""

from __future__ import annotations

from rig import L, Frame, at, merge, shear_h, shear_v, crop_rows
from tsu_base import *  # noqa: F401,F403  (parts and PAL)
import tsu_base as B

FW, FH = 56, 64
MX, MY = 15, 23
PIVOT = (28, 61)

# Anchors in model space (converted to pivot-relative pixels by the build).
LOAD_TOP = {'front': (13, 6), 'side': (5, 6), 'back': (13, 6)}   # top rail: where Saji sits
HOOK = {'front': (4, -1), 'side': (1, -1), 'back': (22, -1)}      # the peg on her right post
HAND_REST = {'front': (7, 30), 'side': (16, 29), 'back': (20, 30)}


def _anchors(view, load, dy=0, hand=None, ldy=None):
    """dy: body offset for the default hand; ldy: offset of the frame (defaults to dy)."""
    ldy = dy if ldy is None else ldy
    a = {'hand': hand if hand is not None else (HAND_REST[view][0], HAND_REST[view][1] + dy)}
    if load:
        a['loadTop'] = (LOAD_TOP[view][0], LOAD_TOP[view][1] + ldy)
        a['hook'] = (HOOK[view][0], HOOK[view][1] + ldy)
    return a


def _face(table, face):
    return table.get(face) if face else None


# ---------------------------------------------------------------------------------------------
# View composers. Every offset is in whole pixels. 'body' moves the torso, sleeves, straps and the
# frame; 'head' moves face and hat; sleeves/hair/sash take their own (lagged) offsets.

def front(load, body=0, head=0, face=None, sl=(0, 0), sr=(0, 0), legs=('plant', 0, 'plant', 0), hem='c',
          sash=0, arm_l=None, arm_r=None, over=(), hem_dy=0):
    ll, lld, rl, rld = legs
    return [
        at(B.F_FRAME, 0, body) if load else None,
        at(B.F_LEG_L[ll], 0, lld), at(B.F_LEG_R[rl], 0, rld),
        at(B.F_HEM[hem], 0, hem_dy), at(B.F_SKIRT, 0, hem_dy),
        at(B.F_TORSO, 0, body),
        at(B.F_STRAPS, 0, body) if load else None,
        at(B.F_SASH2 if sash else B.F_SASH, 0, hem_dy),
        arm_l if arm_l is not None else at(B.F_SLEEVE_L, sl[0], body + sl[1]),
        arm_r if arm_r is not None else at(B.F_SLEEVE_R, sr[0], body + sr[1]),
        at(B.F_FACE_ROWS, 0, head), at(_face(B.F_FACE, face), 0, head) if _face(B.F_FACE, face) else None,
        at(B.HAT_F, 0, head),
        *over,
    ]


def side(load, body=0, head=0, face=None, sleeve=None, lower=None, hair=0, hair_dy=None, arm_over=None, over=()):
    hd = head if hair_dy is None else hair_dy
    return [
        at(B.S_HAIR[hair], 0, hd),
        at(B.S_BOX, 0, body) if load == 'box' else None,
        at(B.S_FRAME, 0, body) if load else None,
        lower if lower is not None else at(B.S_LOWER['stand']),
        at(B.S_SKIRT, 0, max(0, body)),
        at(B.S_TORSO, 0, body),
        None if arm_over is not None else (sleeve if sleeve is not None else at(B.S_SLEEVE[0], 0, body)),
        at(B.S_STRAP, 0, body) if load else None,
        at(B.S_FACE_ROWS, 0, head), at(_face(B.S_FACE, face), 0, head) if _face(B.S_FACE, face) else None,
        at(B.HAT_S, 0, head),
        arm_over,
        *over,
    ]


def back(load, body=0, head=0, sl=(0, 0), sr=(0, 0), legs=('plant', 0, 'plant', 0), hem='c', hair=0, hair_dy=None,
         arm_l=None, arm_r=None, top=(), hem_dy=0):
    ll, lld, rl, rld = legs
    hd = head if hair_dy is None else hair_dy
    return [
        at(B.F_LEG_L[ll], 0, lld), at(B.F_LEG_R[rl], 0, rld),
        at(B.B_HEM[hem], 0, hem_dy), at(B.B_SKIRT, 0, hem_dy), at(B.B_SASH, 0, hem_dy),
        at(B.B_TORSO, 0, body),
        arm_l if arm_l is not None else at(B.B_SLEEVE_L, sl[0], body + sl[1]),
        arm_r if arm_r is not None else at(B.B_SLEEVE_R, sr[0], body + sr[1]),
        at(B.B_HAIR_ROWS, 0, head), at(B.B_HAIR[hair], 0, hd),
        at(B.HAT_B, 0, head),
        at(B.B_FRAME, 0, body) if load else None,
        at(B.B_BOX, 0, body) if load == 'box' else None,
        *top,
    ]


# ---------------------------------------------------------------------------------------------
# Idle: the hat stays still; chest and shoulders breathe one pixel; hair tips and sash sway.

BREATH = [0, 0, 0, -1, -1, -1, 0, 0]
SWAY = [0, 0, 0, 0, 1, 1, 1, 0]     # one frame behind the breath


def idle(view, load):
    out = []
    for i, b in enumerate(BREATH):
        face = 'blink' if i == 6 else None
        if view == 'front':
            ly = front(load, body=b, face=face, sash=SWAY[i])
        elif view == 'side':
            ly = side(load, body=b, face=face, hair=SWAY[i] * 2, hair_dy=0)
        else:
            ly = back(load, body=b, hair=SWAY[i] * 2, hair_dy=0)
        out.append(Frame(ly, _anchors(view, load, b)))
    return out


# ---------------------------------------------------------------------------------------------
# Walk: 8 frames - contact, down, passing, up for each leg; 1 px bob; hair, sleeves and the sash
# tail follow the body one frame late.

BOB = [0, 1, 0, -1, 0, 1, 0, -1]
LAG = [BOB[(i - 1) % 8] for i in range(8)]
# front legs: (left part, dy, right part, dy) - the forward foot sits a pixel lower
F_LEGS_WALK = [('long', 0, 'tuck', -1), ('plant', 0, 'tuck', -2), ('plant', 0, 'plant', -1), ('tuck', 0, 'plant', 0),
               ('tuck', -1, 'long', 0), ('tuck', -2, 'plant', 0), ('plant', -1, 'plant', 0), ('plant', 0, 'tuck', 0)]
F_HEM_WALK = ['l', 'l', 'c', 'r', 'r', 'r', 'c', 'l']
HEM_LAG = [F_HEM_WALK[(i - 1) % 8] for i in range(8)]
# back legs: the trailing foot comes toward the camera (lower), the leading one goes away
B_LEGS_WALK = [('tuck', -1, 'long', 0), ('tuck', -2, 'plant', 0), ('plant', -1, 'plant', 0), ('plant', 0, 'tuck', 0),
               ('long', 0, 'tuck', -1), ('plant', 0, 'tuck', -2), ('plant', 0, 'plant', -1), ('tuck', 0, 'plant', 0)]
SIDE_HAIR = [1, 1, 2, 2, 1, 1, 2, 2]
SLEEVE_SWING = [-1, -1, 0, 1, 1, 1, 0, -1]   # near sleeve, side view (back when the near leg leads)


def walk(view, load):
    out = []
    for i, b in enumerate(BOB):
        lag = LAG[i]
        if view == 'front':
            sw = SLEEVE_SWING[(i - 1) % 8]
            ly = front(load, body=b, head=b, sl=(0, lag - b + (1 if sw < 0 else 0)), sr=(0, lag - b + (1 if sw > 0 else 0)),
                       legs=F_LEGS_WALK[i], hem=HEM_LAG[i], sash=(i // 2) % 2)
        elif view == 'side':
            sw = SLEEVE_SWING[(i - 1) % 8]
            sleeve = at(B.S_SLEEVE[0], sw, lag)
            ly = side(load, body=b, head=b, sleeve=sleeve, lower=at(B.S_WALK[i]), hair=SIDE_HAIR[(i - 1) % 8], hair_dy=lag)
        else:
            sw = SLEEVE_SWING[(i - 1) % 8]
            ly = back(load, body=b, head=b, sl=(0, lag - b + (1 if sw > 0 else 0)), sr=(0, lag - b + (1 if sw < 0 else 0)),
                      legs=B_LEGS_WALK[i], hem=HEM_LAG[i], hair=[1, 1, 0, 2, 2, 2, 0, 1][i], hair_dy=lag)
        out.append(Frame(ly, _anchors(view, load, b)))
    return out


def heavy_idle(view, load):
    """Holding extra weight: sunk, shoulders down, a slow heavy breath; the hat sinks with her."""
    out = []
    for i, b in enumerate([2, 2, 3, 3]):
        face = 'blink' if i == 3 else None
        if view == 'front':
            ly = front(load, body=b, head=b, face=face, hem_dy=1, legs=('plant', 0, 'plant', 0))
        elif view == 'side':
            ly = side(load, body=b, head=b, face=face, hair_dy=b)
        else:
            ly = back(load, body=b, head=b, hem_dy=1, hair_dy=b)
        out.append(Frame(ly, _anchors(view, load, b)))
    return out





# =============================================================================================
# Actions (parts in tsu_actions.py)

import tsu_actions as A


def _drop(ly, *parts):
    return [i for i in ly if not (i is not None and i[0] in parts)]


def take(view, load):
    """Reach out, close the hand, pull it to the chest, hold."""
    out = []
    if view == 'front':
        seq = [(A.F_REACH_L, 0, (2, 31)), (A.F_REACH_L, 1, (2, 32)), (A.F_CHEST_L, 0, (11, 22)), (A.F_CHEST_L, 1, (11, 23))]
        for arm, dy, hand in seq:
            out.append(Frame(front(load, body=0, arm_l=at(arm, 0, dy)), _anchors(view, load, 0, hand)))
    elif view == 'side':
        seq = [(A.S_FWD, 0, (24, 21)), (A.S_FWD, 1, (25, 21)), (A.S_CHEST, 0, (18, 23)), (A.S_CHEST, 0, (18, 23))]
        for arm, dx, hand in seq:
            out.append(Frame(side(load, sleeve=at(arm, dx, 0)), _anchors(view, load, 0, (hand[0], hand[1]))))
    return out


def give(view, load):
    """Hold it at the chest, offer it forward, hold it out, return."""
    out = []
    if view == 'front':
        seq = [(A.F_CHEST_L, A.F_CHEST_R, 0, (13, 22)), (A.F_OFFER_L, A.F_OFFER_R, 0, (13, 26)),
               (A.F_OFFER_L, A.F_OFFER_R, 1, (13, 27)), (A.F_CHEST_L, A.F_CHEST_R, 0, (13, 22))]
        for al, ar, dy, hand in seq:
            out.append(Frame(front(load, arm_l=at(al, 0, dy), arm_r=at(ar, 0, dy)), _anchors(view, load, 0, hand)))
    elif view == 'side':
        seq = [(A.S_CHEST, 0, (18, 23)), (A.S_OFFER, 0, (23, 24)), (A.S_OFFER, 1, (24, 24)), (A.S_CHEST, 0, (18, 23))]
        for arm, dx, hand in seq:
            out.append(Frame(side(load, sleeve=at(arm, dx, 0)), _anchors(view, load, 0, hand)))
    return out


def push(view, load):
    """Side: wind up, push the hand into the door, lean in, hold (the hand passes through)."""
    out = []
    seq = [(A.S_CHEST, 0, 0, (18, 23)), (A.S_FWD, 0, 0, (24, 19)), (A.S_FWD, 1, 1, (25, 19)), (A.S_FWD, 1, 1, (25, 19))]
    for arm, dx, lean, hand in seq:
        ly = side(load, sleeve=at(arm, dx + lean, 0))
        moved = (B.S_TORSO, B.S_FACE_ROWS, B.HAT_S, B.S_STRAP, B.S_FRAME, B.S_BOX) + tuple(B.S_HAIR)
        ly = [(l, x + (lean if l in moved else 0), y) if l is not None else None for l, x, y in [i if i is not None else (None, 0, 0) for i in ly]]
        a = _anchors(view, load, 0, (hand[0] + lean, hand[1]))
        if load:
            a['loadTop'] = (a['loadTop'][0] + lean, a['loadTop'][1]); a['hook'] = (a['hook'][0] + lean, a['hook'][1])
        out.append(Frame(ly, a))
    return out


def reach_up(view, load):
    """Raise a lantern to a hook: arm half up, fully up, up on her toes, hold."""
    out = []
    if view == 'side':
        seq = [(A.S_UP_HALF, 0, (21, 9)), (A.S_UP, 0, (14, -3)), (A.S_UP, -1, (14, -4)), (A.S_UP, 0, (14, -3))]
        for arm, dy, hand in seq:
            out.append(Frame(side(load, body=dy, head=dy, arm_over=at(arm, 0, dy)), _anchors(view, load, dy, hand)))
    elif view == 'back':
        seq = [(A.B_UP_HALF_R, 0, (26, 9)), (A.B_UP_R, 0, (21, -3)), (A.B_UP_R, -1, (21, -4)), (A.B_UP_R, 0, (21, -3))]
        for arm, dy, hand in seq:
            out.append(Frame(back(load, body=dy, head=dy, arm_r=None, top=(at(arm, 0, dy),)) if False else
                             back(load, body=dy, head=dy, arm_r=at(B.B_SLEEVE_R, 0, 99), top=(at(arm, 0, dy),)),
                             _anchors(view, load, dy, hand)))
    return out


def eat(view, load):
    """Bring a dango to her mouth, bite, chew, lower it."""
    out = []
    if view == 'front':
        seq = [(A.F_CHEST_L, None, (11, 22)), (A.F_MOUTH_L, 'open_mouth', (12, 13)), (A.F_MOUTH_L, 'chew', (12, 13)), (A.F_CHEST_L, 'chew', (11, 22))]
        for arm, face, hand in seq:
            if arm is A.F_MOUTH_L:
                ly = front(load, face=face, arm_l=at(B.F_SLEEVE_L, 0, 99), over=(at(arm),))
            else:
                ly = front(load, face=face, arm_l=at(arm))
            out.append(Frame(ly, _anchors(view, load, 0, hand)))
    elif view == 'side':
        seq = [(A.S_CHEST, None, (18, 23)), (A.S_MOUTH, 'open_mouth', (19, 15)), (A.S_MOUTH, 'chew', (19, 15)), (A.S_CHEST, 'chew', (18, 23))]
        for arm, face, hand in seq:
            if arm is A.S_MOUTH:
                ly = side(load, face=face, arm_over=at(arm))
            else:
                ly = side(load, face=face, sleeve=at(arm))
            out.append(Frame(ly, _anchors(view, load, 0, hand)))
    return out


def climb(view, load):
    """Back view: hand over hand, knees lifting in turn (4 frames)."""
    out = []
    seq = [(A.B_UP_L, 0, A.B_UP_HALF_R, 2, ('plant', -3, 'plant', 0), 0, (5, -3)),
           (A.B_UP_L, 1, A.B_UP_HALF_R, 1, ('plant', -2, 'plant', 0), -1, (5, -2)),
           (A.B_UP_HALF_L, 2, A.B_UP_R, 0, ('plant', 0, 'plant', -3), 0, (21, -3)),
           (A.B_UP_HALF_L, 1, A.B_UP_R, 1, ('plant', 0, 'plant', -2), -1, (21, -2))]
    for al, ady, ar, ardy, legs, b, hand in seq:
        ly = back(load, body=b, head=b, legs=legs, arm_l=at(B.B_SLEEVE_L, 0, 99), arm_r=at(B.B_SLEEVE_R, 0, 99),
                  top=(at(al, 0, ady + b), at(ar, 0, ardy + b)))
        out.append(Frame(ly, _anchors('back', load, b, hand)))
    return out


def shout(view, load):
    """Back view: hands cupped at her mouth, elbows out; she leans into the shout (3 frames)."""
    out = []
    for i, (b, h) in enumerate([(1, 1), (0, -1), (0, -1)]):
        ly = back(load, body=b, head=h, arm_l=at(B.B_SLEEVE_L, 0, 99), arm_r=at(B.B_SLEEVE_R, 0, 99),
                  top=(at(A.B_SHOUT_L, 0, b), at(A.B_SHOUT_R, 0, b)))
        out.append(Frame(ly, _anchors('back', load, b, (13, 12))))
    return out


def sit_branch(view, load):
    """Back view: sitting on a branch (anchor 'seat' at her hips), calves swinging (4 frames)."""
    out = []
    for i, li in enumerate([0, 1, 0, 2]):
        b = [0, 0, -1, 0][i]
        ly = [
            at(A.B_SIT_LEGS[li]), at(A.B_SIT_SKIRT),
            at(B.B_TORSO, 0, b), at(B.B_SLEEVE_L, 0, b), at(B.B_SLEEVE_R, 0, b),
            at(B.B_HAIR_ROWS), at(B.B_HAIR[[0, 1, 0, 2][i]], 0, 0), at(B.HAT_B),
            at(B.B_FRAME, 0, b) if load else None, at(B.B_BOX, 0, b) if load == 'box' else None,
        ]
        a = _anchors('back', load, b)
        a['seat'] = (13, 29)
        out.append(Frame(ly, a))
    return out


HIP = 27


def bow(view, load):
    """A deep bow: lean in, hold, come back up (5 frames)."""
    out = []
    if view == 'side':
        # clean lean ratios (1/3, 1/2) give regular 3- and 2-row steps; the hat tips with them
        steps = [(1 / 3, 1 / 4, 2, 1, None), (1 / 2, 1 / 3, 4, 3, 'blink'), (1 / 2, 1 / 2, 5, 4, 'blink'),
                 (1 / 2, 1 / 2, 5, 4, 'blink'), (1 / 3, 1 / 4, 2, 1, None)]
        for k, tilt, hx, hy, face in steps:
            upper = shear_h(merge(at(B.S_TORSO), at(A.S_CHEST if k >= 0.5 else B.S_SLEEVE[0])), k, HIP)
            head = merge(at(B.S_FACE_ROWS), at(_face(B.S_FACE, face)) if _face(B.S_FACE, face) else None, at(B.HAT_S))
            head = shear_v(head, tilt, 13)
            hair = shear_h(B.S_HAIR[0], k / 2, HIP)
            ly = [at(hair),
                  at(shear_h(B.S_BOX, k, HIP)) if load == 'box' else None,
                  at(shear_h(B.S_FRAME, k, HIP)) if load else None,
                  at(B.S_LOWER['stand']), at(B.S_SKIRT), at(upper),
                  at(shear_h(B.S_STRAP, k, HIP)) if load else None,
                  at(head, hx, hy)]
            a = _anchors(view, load, 0)
            if load:
                for n in ('loadTop', 'hook'):
                    c, r = a[n]
                    a[n] = (c + int(k * (HIP - r)), r)
            out.append(Frame(ly, a))
    elif view == 'front':
        for b, h, dish in [(1, 1, False), (2, 3, True), (3, 4, True), (3, 4, True), (1, 1, False)]:
            ly = front(load, body=b, head=h, face='blink' if dish else None,
                       arm_l=at(A.F_CHEST_L, 0, b), arm_r=at(A.F_CHEST_R, 0, b))
            if dish:
                ly = _drop(ly, B.HAT_F, B.F_FACE_ROWS, *[f for f in B.F_FACE.values() if f]) + [at(A.F_HAT_DISH, 0, h - 1)]
            out.append(Frame(ly, _anchors(view, load, b)))
    else:
        for b, h, dish in [(1, 1, False), (2, 3, True), (3, 4, True), (3, 4, True), (1, 1, False)]:
            ly = back(load, body=b, head=h, hair_dy=h)
            if dish:
                ly = _drop(ly, B.HAT_B)
                ly.insert(len(ly) - (2 if load == 'box' else 1 if load else 0), at(A.F_HAT_DISH, 0, h - 1))
            out.append(Frame(ly, _anchors(view, load, b)))
    return out


def strain(view, load):
    """Knees bent, both hands under a heavy beam, shaking, a little lift (no back-frame)."""
    out = []
    for i in range(4):
        shake, lift = [0, 0, 1, 0][i], [0, 0, 0, 1][i]
        face = None if i == 0 else 'strain'
        b = 3
        if view == 'front':
            ly = [at(A.F_LEG_CROUCH_L), at(A.F_LEG_CROUCH_R), at(B.F_HEM['c'], 0, 2), at(B.F_SKIRT, 0, 2),
                  at(B.F_TORSO, shake, b), at(B.F_SASH, 0, 2),
                  at(A.F_BEAM_L, shake, b - lift), at(A.F_BEAM_R, shake, b - lift),
                  at(B.F_FACE_ROWS, shake, b), at(_face(B.F_FACE, face), shake, b) if face else None, at(B.HAT_F, shake, b)]
            hand = (13 + shake, 29 + b - lift)
        else:
            ly = [at(B.S_HAIR[0], shake, b), at(A.S_CROUCH), at(B.S_SKIRT, 0, 3), at(B.S_TORSO, shake, b),
                  at(A.S_BEAM, shake, b - lift),
                  at(B.S_FACE_ROWS, shake, b), at(_face(B.S_FACE, face), shake, b) if face else None, at(B.HAT_S, shake, b)]
            hand = (23 + shake, 24 + b - lift)
        out.append(Frame(ly, {'hand': hand}))
    return out


def release(view, load):
    """Fling both arms out (放): gather, fling, hold."""
    out = []
    if view == 'front':
        seq = [(A.F_CHEST_L, A.F_CHEST_R, 1, 'blink'), (A.F_OUT_L, A.F_OUT_R, -1, None), (A.F_OUT_L, A.F_OUT_R, 0, None)]
        for al, ar, b, face in seq:
            ly = front(load, body=b, face=face, arm_l=at(al, 0, b), arm_r=at(ar, 0, b))
            out.append(Frame(ly, _anchors(view, load, b, (13, 22 + b))))
    elif view == 'side':
        for arm, b, over in [(A.S_CHEST, 1, False), (A.S_UP_HALF, -1, True), (A.S_UP_HALF, 0, True)]:
            ly = side(load, body=b, arm_over=at(arm, 0, b)) if over else side(load, body=b, sleeve=at(arm, 0, b))
            out.append(Frame(ly, _anchors(view, load, b, (21, 9 + b))))
    else:
        for al, ar, b in [(None, None, 1), (A.B_UP_HALF_L, A.B_UP_HALF_R, -1), (A.B_UP_HALF_L, A.B_UP_HALF_R, 0)]:
            if al is None:
                ly = back(load, body=b, sl=(1, 0), sr=(-1, 0))
            else:
                ly = back(load, body=b, arm_l=at(B.B_SLEEVE_L, 0, 99), arm_r=at(B.B_SLEEVE_R, 0, 99), top=(at(al, 0, b), at(ar, 0, b)))
            out.append(Frame(ly, _anchors(view, load, b, (13, 22 + b))))
    return out


def hurt(view, load):
    """Flinch: knocked back a pixel, eyes squeezed, arms up; then recover (2 frames)."""
    out = []
    for i, (dx, b) in enumerate([(-1, 1), (0, 0)]):
        face = 'strain' if i == 0 else 'blink'
        if view == 'front':
            ly = front(load, body=b, head=b, face=face, arm_l=at(A.F_CHEST_L, dx, b), arm_r=at(A.F_CHEST_R, dx, b))
        elif view == 'side':
            ly = side(load, body=b, head=b, face=face, sleeve=at(A.S_CHEST, dx, b))
        else:
            ly = back(load, body=b, head=b, sl=(1, 0), sr=(-1, 0))
        keep = set(B.F_LEG_L.values()) | set(B.F_LEG_R.values()) | {B.S_LOWER['stand']}
        ly = [(l, x + (dx if l not in keep else 0), y) if l is not None else None for l, x, y in [j if j is not None else (None, 0, 0) for j in ly]]
        out.append(Frame(ly, _anchors(view, load, b)))
    return out


def look_up(view, load):
    """Tips her head back to look up (cutscenes): 2 breathing frames."""
    out = []
    for b in (0, -1):
        if view == 'front':
            ly = _drop(front(load, body=b), B.HAT_F, B.F_FACE_ROWS) + [at(A.F_FACE_UP), at(A.F_HAT_UP)]
        elif view == 'side':
            head = shear_v(merge(at(B.S_FACE_ROWS), at(B.HAT_S)), -1 / 5, 13)
            ly = _drop(side(load, body=b), B.S_FACE_ROWS, B.HAT_S) + [at(head, 0, 1)]
        else:
            ly = back(load, body=b, head=1, hair_dy=1)
        out.append(Frame(ly, _anchors(view, load, b)))
    return out


def lift(view, load):
    """Lift something overhead: crouch and grab, bring it up, hold it high (3 frames)."""
    out = []
    if view == 'front':
        seq = [('crouch', A.F_BEAM_L, A.F_BEAM_R, 3, (13, 32)), ('stand', A.F_CHEST_L, A.F_CHEST_R, 0, (13, 22)),
               ('stand', A.F_UP_L, A.F_UP_R, 0, (13, -3))]
        for legs, al, ar, b, hand in seq:
            if al is A.F_UP_L:   # raised arms go in front of the brim; the sleeves slide down to the elbows
                ly = front(load, body=b, head=b, arm_l=at(B.F_SLEEVE_L, 0, 99), arm_r=at(B.F_SLEEVE_R, 0, 99),
                           over=(at(al, 0, b), at(ar, 0, b)))
                out.append(Frame(ly, _anchors(view, load, b, hand)))
                continue
            ly = front(load, body=b, head=b, face='strain' if legs == 'crouch' else None, hem_dy=2 if legs == 'crouch' else 0,
                       arm_l=at(al, 0, b), arm_r=at(ar, 0, b))
            if legs == 'crouch':
                ly = _drop(ly, *B.F_LEG_L.values(), *B.F_LEG_R.values()) + [at(A.F_LEG_CROUCH_L), at(A.F_LEG_CROUCH_R)]
                ly = [ly[-2], ly[-1]] + ly[:-2]
            out.append(Frame(ly, _anchors(view, load, b, hand)))
    elif view == 'side':
        for kind, arm, b, hand in [('crouch', A.S_BEAM, 3, (23, 27)), ('stand', A.S_CHEST, 0, (18, 23)), ('stand', A.S_UP, 0, (14, -3))]:
            if kind == 'crouch':
                ly = side(load, body=b, head=b, face='strain', lower=at(A.S_CROUCH), sleeve=at(arm, 0, b))
            elif arm is A.S_UP:
                ly = side(load, arm_over=at(arm))
            else:
                ly = side(load, sleeve=at(arm))
            out.append(Frame(ly, _anchors(view, load, b, hand)))
    else:
        for al, ar, b, hand in [(None, None, 2, (13, 32)), (A.B_UP_HALF_L, A.B_UP_HALF_R, 0, (13, 9)), (A.B_UP_L, A.B_UP_R, 0, (13, -3))]:
            if al is None:
                ly = back(load, body=b, head=b, hem_dy=1, sl=(1, 0), sr=(-1, 0))
            else:
                ly = back(load, arm_l=at(B.B_SLEEVE_L, 0, 99), arm_r=at(B.B_SLEEVE_R, 0, 99), top=(at(al), at(ar)))
            out.append(Frame(ly, _anchors(view, load, b, hand)))
    return out


def carry_overhead(view, load):
    """Walk holding something overhead (8 frames; the object is a prop at 'hand')."""
    out = []
    for i, b in enumerate(BOB):
        if view == 'front':
            ly = front(load, body=b, head=b, legs=F_LEGS_WALK[i], hem=HEM_LAG[i], sash=(i // 2) % 2,
                       arm_l=at(B.F_SLEEVE_L, 0, 99), arm_r=at(B.F_SLEEVE_R, 0, 99), over=(at(A.F_UP_L, 0, b), at(A.F_UP_R, 0, b)))
            hand = (13, -3 + b)
        elif view == 'side':
            ly = side(load, body=b, head=b, lower=at(B.S_WALK[i]), hair=SIDE_HAIR[(i - 1) % 8], hair_dy=LAG[i], arm_over=at(A.S_UP, 0, b))
            hand = (14, -3 + b)
        else:
            ly = back(load, body=b, head=b, legs=B_LEGS_WALK[i], hem=HEM_LAG[i], hair_dy=LAG[i],
                      arm_l=at(B.B_SLEEVE_L, 0, 99), arm_r=at(B.B_SLEEVE_R, 0, 99), top=(at(A.B_UP_L, 0, b), at(A.B_UP_R, 0, b)))
            hand = (13, -3 + b)
        out.append(Frame(ly, _anchors(view, load, b, hand)))
    return out


def shoulder(view, load):
    """Putting the back-frame on: crouch with her back to it, slip the straps on, rise (4 frames)."""
    out = []
    if view == 'side':
        for ldx, ldy, b, crouch, grip in [(-4, 10, 3, True, False), (-1, 9, 3, True, True), (0, 4, 1, False, True), (0, 0, 0, False, False)]:
            ly = [
                at(B.S_HAIR[0], 0, b),
                at(B.S_BOX, ldx, ldy) if load == 'box' else None,
                at(B.S_FRAME, ldx, ldy),
                at(A.S_CROUCH) if crouch else at(B.S_LOWER['stand']),
                at(B.S_SKIRT, 0, 3 if crouch else 0),
                at(B.S_TORSO, 0, b),
                at(A.S_GRIP if grip else B.S_SLEEVE[0], 0, b),
                at(B.S_STRAP, 0, b) if ldy < 10 else None,
                at(B.S_FACE_ROWS, 0, b), at(B.HAT_S, 0, b),
            ]
            out.append(Frame(ly, {'hand': (16, 18 + b), 'loadTop': (LOAD_TOP['side'][0] + ldx, LOAD_TOP['side'][1] + ldy),
                                  'hook': (HOOK['side'][0] + ldx, HOOK['side'][1] + ldy)}))
    elif view == 'front':
        for ldy, b, crouch in [(10, 3, True), (9, 3, True), (4, 1, False), (0, 0, False)]:
            ly = front(load, body=b, head=b, hem_dy=2 if crouch else 0,
                       arm_l=at(A.F_CHEST_L, 0, b) if 0 < ldy < 10 else None, arm_r=at(A.F_CHEST_R, 0, b) if 0 < ldy < 10 else None)
            ly = _drop(ly, B.F_FRAME, B.F_STRAPS)
            ly = [at(B.F_FRAME, 0, ldy)] + ly + ([at(B.F_STRAPS, 0, b)] if ldy < 10 else [])
            if crouch:
                ly = _drop(ly, *B.F_LEG_L.values(), *B.F_LEG_R.values()) + [at(A.F_LEG_CROUCH_L), at(A.F_LEG_CROUCH_R)]
                ly = [ly[0], ly[-2], ly[-1]] + ly[1:-2]
            out.append(Frame(ly, {'hand': (11, 22 + b), 'loadTop': (LOAD_TOP['front'][0], LOAD_TOP['front'][1] + ldy),
                                  'hook': (HOOK['front'][0], HOOK['front'][1] + ldy)}))
    return out


def asleep(view, load):
    """Side view (mirror for the other way): on her back with the hat over her face, breathing."""
    out = []
    for i in (0, 1):
        ly = [at(A.ASLEEP_BODY[i]), at(B.HAT_F, -9, 26)]
        out.append(Frame(ly, {'hand': (26, 34)}))
    return out


def _sit_ground(face=None, tilt=0.0, arm=None):
    b = 8
    head = merge(at(B.S_FACE_ROWS), at(_face(B.S_FACE, face)) if _face(B.S_FACE, face) else None, at(B.HAT_S))
    if tilt:
        head = shear_v(head, tilt, 13)
    return [at(B.S_HAIR[0], 0, b - 4), at(A.S_SIT_LEGS), at(B.S_TORSO, 0, b), at(arm or B.S_SLEEVE[0], 0, b - 1), at(head, 0, b)]


def sit_up(view, load):
    """Side: lying, propped on her elbows, sitting with the hat over her eyes, hat back in place."""
    return [
        Frame([at(A.ASLEEP_BODY[0]), at(B.HAT_F, -9, 26)], {'hand': (26, 34)}),
        Frame([at(A.ASLEEP_BODY[0], 0, 0), at(shear_v(B.HAT_S, 1 / 4, 13), -6, 21)], {'hand': (14, 35)}),
        Frame(_sit_ground('blink', 1 / 4), {'hand': (16, 36), 'seat': (12, 38)}),
        Frame(_sit_ground(), {'hand': (16, 36), 'seat': (12, 38)}),
    ]


def sit(view, load):
    """Side: sitting on the ground (cutscenes); breathing and a blink."""
    out = []
    for i in range(4):
        ly = _sit_ground('blink' if i == 3 else None)
        if i in (1, 2):
            ly = [(l, x, y + 1) if (l is not None and l is not A.S_SIT_LEGS) else (l, x, y) for l, x, y in ly]
        out.append(Frame(ly, {'hand': (16, 36), 'seat': (12, 38)}))
    return out


def _ride(fn):
    """The same animation for when Saji rides on the frame: in the front view the post tips are
    left out (Saji sits between them, wider than the gap, and would otherwise be striped by them)."""
    def ride(view, load):
        return [Frame(_drop(f.layers, B.F_FRAME), f.anchors) for f in fn(view, load)]
    ride.__name__ = fn.__name__ + '_ride'
    return ride


# =============================================================================================
# Sheet description for tools/art/build.py

NAME = 'tsuzumi'
FRAME = (FW, FH)
ORIGIN = (MX, MY)
F, S, Bk = 'front', 'side', 'back'
ALL = ('load', 'frame', 'plain')

# name: (recipe, views, fps, loop, sheets)
ANIMS = {
    'idle':          (idle,           (F, S, Bk), 4,   True,  ALL),
    'walk':          (walk,           (F, S, Bk), 10,  True,  ALL),
    'heavyIdle':     (heavy_idle,     (F, S, Bk), 3,   True,  ALL),
    'take':          (take,           (F, S),     8,   False, ALL),
    'give':          (give,           (F, S),     8,   False, ALL),
    'shoulder':      (shoulder,       (F, S),     5,   False, ('load', 'frame')),
    'push':          (push,           (S,),       8,   False, ALL),
    'reachUp':       (reach_up,       (S, Bk),    6,   False, ALL),
    'eat':           (eat,            (F, S),     4,   False, ALL),
    'bow':           (bow,            (F, S, Bk), 5,   False, ALL),
    'climb':         (climb,          (Bk,),      6,   True,  ALL),
    'shout':         (shout,          (Bk,),      6,   False, ALL),
    'sitBranch':     (sit_branch,     (Bk,),      3,   True,  ALL),
    'release':       (release,        (F, S, Bk), 8,   False, ALL),
    'hurt':          (hurt,           (F, S, Bk), 6,   False, ALL),
    'lookUp':        (look_up,        (F, S, Bk), 2,   True,  ALL),
    'lift':          (lift,           (F, S, Bk), 5,   False, ALL),
    'carryOverhead': (carry_overhead, (F, S, Bk), 10,  True,  ALL),
    'strain':        (strain,         (F, S),     8,   True,  ('plain',)),
    'asleep':        (asleep,         (S,),       1.5, True,  ('plain',)),
    'sitUp':         (sit_up,         (S,),       4,   False, ('plain',)),
    'sit':           (sit,            (S,),       3,   True,  ('plain',)),
    # front view while Saji rides (characters.js frameAt(..., { rider: true }) picks these)
    'idleRide':      (_ride(idle),       (F,),    4,   True,  ('load', 'frame')),
    'walkRide':      (_ride(walk),       (F,),    10,  True,  ('load', 'frame')),
    'heavyIdleRide': (_ride(heavy_idle), (F,),    3,   True,  ('load', 'frame')),
    'takeRide':      (_ride(take),       (F,),    8,   False, ('load', 'frame')),
    'giveRide':      (_ride(give),       (F,),    8,   False, ('load', 'frame')),
}

SHEETS = {'load': 'box', 'frame': 'frame', 'plain': None}

# Draw order for Saji riding on the frame: 'behind' = draw Saji first (Tsuzumi's hat covers her
# legs), 'over' = draw Saji after Tsuzumi.
RIDER = {'front': 'behind', 'side': 'behind', 'back': 'over'}
