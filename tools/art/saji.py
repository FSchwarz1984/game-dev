"""家守さぢ (Saji Yamori) - zashiki-warashi, the companion who rides on Tsuzumi's load.

Reference: assets/reference/illustrations/saji.png. Red messy bob with an ahoge and a teal
headband; big teal eyes; a pale-mint shawl collar with a teal border; a gold bell on a red cord at
the collar (the game's hint bell); plum kimono top with a red collar edge; white sleeves with red
lining; a teal obi with a big bow on her left; a red flared skirt with a cream wavy stripe; white
socks tied with red ribbons; plum boots with red laces.

Model space: 21 columns, centre column 10; row 27 is the outline under her soles. It maps into the
32x40 frame at (MX, MY), so the foot pivot is frame pixel (16, 37). Sitting animations carry a
'seat' anchor (her bottom) to place on Tsuzumi's 'loadTop'.
"""

from __future__ import annotations

from pixart import Palette
from rig import L, Frame, at, shear_h, shear_v, merge

PAL = Palette({
    # hair (vermilion red)
    'H': ('#ff8a62', 'hair', 2), 'R': ('#f0533f', 'hair', 1), 'r': ('#cf3439', 'hair', 0), 'd': ('#9b2434', 'hair', -1), 'D': ('#691a2b', 'hair', -2),
    # skirt: the same red as her hair (as in the illustration); its own letters keep the grids readable
    'K': ('#f0533f', 'skirt', 1), 'k': ('#cf3439', 'skirt', 0), 'j': ('#9b2434', 'skirt', -1), 'J': ('#691a2b', 'skirt', -2),
    # teal (headband, obi, capelet border)
    'Q': ('#4fa8a0', 'teal', 1), 'q': ('#2f7d7a', 'teal', 0), 'c': ('#215a5d', 'teal', -1), 'C': ('#163b42', 'teal', -2),
    # mint shawl collar
    'M': ('#f1f8ea', 'mint', 1), 'm': ('#d2e7d1', 'mint', 0), 'x': ('#a7c7b6', 'mint', -1),
    # plum kimono top and boots
    'P': ('#93437a', 'plum', 1), 'p': ('#702e5e', 'plum', 0), 'u': ('#4e2045', 'plum', -1), 'U': ('#34152f', 'plum', -2),
    # cream sleeves, socks, skirt stripe
    'W': ('#fcf8ef', 'white', 2), 'w': ('#ede5d8', 'white', 0), 'v': ('#cdc2cd', 'white', -1),
    # gold bell
    'Y': ('#ffe58c', 'gold', 2), 'y': ('#e2ae3c', 'gold', 0), 'g': ('#a5702a', 'gold', -1),
    # skin
    's': ('#fde7d8', 'skin', 0), 'z': ('#efbca8', 'skin', -1), 'Z': ('#d4907f', 'skin', -2), 'b': ('#f5a0a2', 'skin', 0),
    # eyes
    'e': ('#2fa094', 'eye', 0), 'E': ('#1b3a3f', 'eye', -2), 'l': ('#ffffff', 'eye', 2),
}, outlines={
    # five line colours: deep red (hair, skirt, plum, gold), deep teal (teal, mint, eyes), soft violet
    # on white cloth, warm brown on skin
    'hair': '#36101c', 'skirt': '#36101c', 'plum': '#36101c', 'gold': '#36101c',
    'teal': '#13282c', 'mint': '#13282c', 'eye': '#13282c', 'white': '#3b3150', 'skin': '#6a3438',
}, default_outline='#36101c', bevel={'hair': 0.8, 'skirt': 0.9, 'white': 1.0, 'skin': 1.1, 'mint': 0.9})

FW, FH = 36, 40
MX, MY = 8, 11
PIVOT = (18, 37)

# =============================================================================================
# FRONT

F_HEAD = L(0, '''
..........oo.........
.........oRdo........
......oooRrooo.......
.....oRRrrrrrdo......
....oRqQqqqqqqco.....
...oRrRrrRrrRrrdo....
...oRrrRrrrrRrrdDo...
..oRrsEEssssEEsrdDo..
..oRrslesssslesrdDo..
..oRrseesssseesrdDo..
..oRrbsssssssbsrddo..
..oRrdzssZZsszdrdDo..
...odDdozzzzzodddDo..
....oooo.ooo.oooo....
''', z=8)

F_FACE = {
    'open': None,
    'blink': L(7, '''
ssssssss
EEssssEE
ssssssss
''', col=6, z=8.1),
    'talk': L(11, '''
sZZs
sZZs
''', col=8, z=8.1),
    'grin': L(10, '''
.zZZz.
''', col=7, z=8.1),
    'wide': L(7, '''
EE....EE
le....le
eE....eE
''', col=6, z=8.1),
}

F_BODY = L(12, '''
.....oooooooooo......
...ooMMMMmmmmmxoo....
..oWMMMMmmmmmmxxvo...
...oqqqqqqqqqqqco....
....oopPppppppuo.....
....oqqqqqqqQqqqo....
...oKkkkkkkkkqcCQo...
..oKkkkkkkkkkkcqjo...
.oKkkkkkkkkkkkkcqjo..
.oWwwWwwwWwwwWwwwvo..
.oJjjJjjjJjjjJjjjJo..
..ooooooooooooooooo..
''', z=5)

F_ARM_L = L(13, '''
..oo.
.oWwo
oWwwo
oWwKo
ozso.
.oo..
''', col=1, z=6)

F_ARM_R = L(13, '''
.oo..
owvo.
owwvo
oKwvo
.oszo
..oo.
''', col=15, z=6)

F_ARM_R_POINT = L(12, '''
.oo.......
owvoooooo.
owwwwwvKso
owwwwvvozzo
oKvvvo.oo.
.ooooo....
''', col=15, z=6)

F_ARM_R_UP = L(4, '''
...oo.
..oszo
..oszo
..oszo
.oKKvo
.owwvo
owwwvo
owwvvo
owvvo.
owvo..
.oo...
''', col=15, z=6)

F_ARM_L_BELL = L(12, '''
..oooo..
.oWwwwoo
oWwwwwsso
oWwwwKzzo
oWwwvoo..
.oooo....
''', col=1, z=7)

F_ARM_R_WAVE = L(8, '''
....oo.
...oszo
..oszo.
.oKwvo.
owwwvo.
owwvvo.
owvvo..
.ooo...
''', col=15, z=6)

F_ARM_L_WAVE = L(8, '''
.oo....
ozso...
.ozso..
.oWwKo.
.oWwwwo
.oWwwwo
..oWwwo
...ooo.
''', col=0, z=6)

F_LEGS = L(22, '''
.....owWvo.owvvo.....
.....orrro.orrro.....
....oupPpo.ouppuo....
....oUuuUo.oUuuUo....
....ooooo...ooooo....
''', z=2)

# =============================================================================================
# SIDE (facing right)

S_HEAD = L(0, '''
.........oo..........
........oRdo.........
.....oooRrooo........
....oRRrrrrrrdo......
...oRqQqqqqqqqco.....
..oRrrRrrrRrrRrdo....
..oRrrRrrRrrRrrrdo...
..oRrrrRrrrrdrsEEo...
..oRrrRrrrrrdrsleso..
..oRrrrRrrrdrbseeso..
..oDdrrrRrrddssssso..
..oDdddrrrdddzsZzo...
...oDDddddddozzzo....
....oooooooooooo.....
''', z=8)

S_FACE = {
    'open': None,
    'blink': L(7, '''
sss
sEE
sss
''', col=14, z=8.1),
    'talk': L(11, '''
ZZ
''', col=15, z=8.1),
}

S_BODY = L(12, '''
.......ooooooo.......
.....ooMMMmmmxoo.....
....oMMMMmmmmmxxo....
....oxqqqqqqqqqco....
.....oupPpppuuuo.....
....oqqqqqqqqqco.....
...oqcoKkkkkkkkko....
..oocCKkkkkkkkkkkoo..
.oKkjkkkkkkkkkkkkkjo.
.oWwwwWwwwWwwwWwwwvo.
.oJjjjJjjjJjjjJjjjJo.
..ooooooooooooooooo..
''', z=5)

S_LEGS = {
    'stand': L(22, '''
........owwvo........
........orrro........
........opPPpoo......
........oUuuuuo......
........ooooooo......
''', z=2),
    'a': L(22, '''
......owvo.owwvo.....
......orro.orrro.....
.....oppo..opPPpoo...
....oUuuo..oUuuuuo...
....ooooo..ooooooo...
''', z=2),
    'b': L(22, '''
.......owvowwvo......
.......orroorro......
......oppooopPpoo....
......oUuoooUuuuo....
......ooooooooooo....
''', z=2),
}

# =============================================================================================
# BACK

B_HEAD = L(0, '''
..........oo.........
.........oRdo........
......oooRrooo.......
.....oRRrrrrrdo......
....oRrRrrrrRrdo.....
...oRrRrrRrrrRrdo....
...oQqqqqqqqqqqcco...
..oRrRrrRrrRrrRrdDo..
..oRrRrrRrrrRrrrdDo..
..oRrRrrrRrrRrrrdDo..
..oRrrRrrrRrrRrrdDo..
..oRrrRrrrrRrrRrdDo..
...odrRrrrrRrrrddo...
....oddddoddddddo....
.....oooo.oooooo.....
''', z=8)

B_BODY = L(12, '''
.....oooooooooo......
...ooMMMmmmmmmxoo....
..oWMMMMmmmmmmmxvo...
...oxxxxxxxxxxxxo....
....oppppppppppuo....
...oQqqqqqqqqqqqco...
..ooQqQoKkkkkkkkoo...
..oKjcqkkkkkkkkkjo...
.oKkkkkkkkkkkkkkkjo..
.oWwwWwwwWwwwWwwwvo..
.oJjjJjjjJjjjJjjjJo..
..ooooooooooooooooo..
''', z=5)

F_LEGS_WALK = {
    'a': L(22, '''
.....owWvo.owvvo.....
.....orrro.orrro.....
....oupPpo.owvvo.....
....oUuuUo.ouppuo....
....ooooo..oUuuUo....
...........ooooo.....
''', z=2),
    'b': L(22, '''
.....owWvo.owvvo.....
.....orrro.orrro.....
.....owWvo.ouppuo....
....oupPpo.oUuuUo....
....oUuuUo..ooooo....
....ooooo............
''', z=2),
    'tuck': L(21, '''
......owvoowvo.......
......orrooorro......
.....ouppooouppo.....
.....oUuUo.oUuUo.....
.....ooooo.ooooo.....
''', z=2),
}

# Sitting: the skirt drapes over her knees, lower legs dangle from the seat edge.
F_SIT_SKIRT = L(17, '''
...oKkkkkkkkkqcCQo...
..oKkkkkkkkkkkcqjjo..
.oKkkkkkkkkkkkkkkjjo.
oKWwwWwwwWwwwWwwwwvjo
oJjjjjJjjjjJjjjjjjjJo
.ooooooooooooooooooo.
''', z=5)

F_SIT_LEGS = [L(20, '''
.....owWo...owvo.....
.....owwo...owvo.....
.....orro...orro.....
.....owWo...owvo.....
....oupPo...oupuo....
....oUuUo...oUuUo....
....ooooo...ooooo....
''', z=6), L(20, '''
.....owWo...owvo.....
.....owwo...owvo.....
.....orro...orro.....
....oupPo...owvo.....
....oUuUo...oupuo....
....ooooo...oUuUo....
............ooooo....
''', z=6), L(20, '''
.....owWo...owvo.....
.....owwo...owvo.....
.....orro...orro.....
.....owWo...oupuo....
....oupPo...oUuUo....
....oUuUo...ooooo....
....ooooo............
''', z=6)]

# =============================================================================================
# SIDE parts (sleeve split out; sitting legs)

S_ARM = L(13, '''
.oo..
oWwo.
oWwvo
oKwvo
.ozso
..oo.
''', col=5, z=6)

S_ARM_POINT = L(12, '''
.oo.......
oWwoooooo.
oWwwwwvKso
oWwwwvvozzo
oKvvvo.oo..
.ooooo.....
''', col=5, z=6)

S_ARM_BELL = L(12, '''
.oo.....
oWwooo..
oWwwwKso
oWwwvozzo
oKvvo.oo.
.oooo....
''', col=5, z=7)

S_ARM_WAVE = L(8, '''
....oo.
...oszo
..oszo.
.oKwvo.
oWwwvo.
oWwvvo.
oWvvo..
.ooo...
''', col=4, z=6)

S_SIT_LEGS = [L(17, '''
...oqcoKkkkkkkkko....
..oocCKkkkkkkkkkkoo..
.oKkjkkkkkkkkkkkkkjo.
.oWwwwWwwwWwwwWwwwoo.
.oJjjjJjjjJjjjJjjoowvo
..oooooooooooooooorro.
................owvo.
................oppoo
................oUuuo
................ooooo
''', z=4), L(17, '''
...oqcoKkkkkkkkko....
..oocCKkkkkkkkkkkoo..
.oKkjkkkkkkkkkkkkkjo.
.oWwwwWwwwWwwwWwwwoo.
.oJjjjJjjjJjjjJjjoowvo
..oooooooooooooooorro.
................owvo..
................oppoo.
.................oUuuo
.................ooooo
''', z=4), L(17, '''
...oqcoKkkkkkkkko....
..oocCKkkkkkkkkkkoo..
.oKkjkkkkkkkkkkkkkjo.
.oWwwwWwwwWwwwWwwwoo.
.oJjjjJjjjJjjjJjjoowvo
..oooooooooooooooorro.
...............owvo..
..............oppoo..
..............oUuuo..
..............ooooo..
''', z=4)]

S_SIT_BODY = L(12, '''
.......ooooooo.......
.....ooMMMmmmxoo.....
....oMMMMmmmmmxxo....
....oWqqqqqyYqqco....
....oWwwopppygpuo....
....oWwwwoPppuuo.....
....oWwwwoqqqqcco....
...ooWwvvoqqqcCo.....
''', z=5)

B_SIT_SKIRT = L(17, '''
..ooQqQoKkkkkkkkoo...
..oKjcqkkkkkkkkkkjo..
.oKkkkkkkkkkkkkkkjjo.
.oWwwWwwwWwwwWwwwwvo.
.oJjjJjjjJjjjJjjjjJo.
..ooooooooooooooooo..
''', z=5)

B_ARM_L = L(13, '''
..oo.
.oWwo
oWwwo
oWwwo
oszo.
.oo..
''', col=1, z=6)

B_ARM_R = L(13, '''
.oo..
owvo.
owwvo
owwvo
.ozso
..oo.
''', col=15, z=6)

B_ARM_R_POINT = L(12, '''
.oo.......
owvoooooo.
owwwwwvKso
owwwwvvozzo
oKvvvo.oo.
.ooooo....
''', col=15, z=6)

# Prone: pinned under a beam (beam drawn by the game across her back), head toward the camera.
# Prone, side view (facing right): lying on her front, head raised, knees on the ground and the
# lower legs kicking up behind her; arms flail in front of her face. The beam is drawn by the game
# across her back (anchor 'beam').
PRONE_BODY = [L(14, '''
.oo...........
oUUo..........
oupo...oo.....
owvo..oUUo....
.orro.oupo....
.owvo.owvo....
..owvoorro....
..oKkkkkkkkoooo
.oKkkkkkkkkkMMo
oKjjjjjjjjjjMxo
oWwwwWwwwwwoxxo
.ooooooooooooo.
''', col=-6, z=4), L(14, '''
.......oo.....
......oUUo....
.oo...oupo....
oUUo..owvo....
oupo..orro....
owvo..owvo....
.orrooowvo....
..oKkkkkkkkoooo
.oKkkkkkkkkkMMo
oKjjjjjjjjjjMxo
oWwwwWwwwwwoxxo
.ooooooooooooo.
''', col=-6, z=4)]

PRONE_ARMS = [L(17, '''
..oo..
.oszo.
oWwso.
oWwoo.
.ooo..
''', col=17, z=9), L(20, '''
.ooooo.
oWwwwszo
.oooooo.
''', col=16, z=9)]

PRONE = None  # kept for reference: front-view prone was unreadable at this size


F_BELL = L(13, '''
.oo.
oYyo
oygo
.oo.
''', col=8, z=7)

S_BELL = L(13, '''
.oo.
oYyo
oygo
.oo.
''', col=13, z=7)

S_ARM = S_ARM.shifted(2)
S_ARM_POINT = S_ARM_POINT.shifted(2)
S_ARM_BELL = S_ARM_BELL.shifted(2)
S_ARM_WAVE = S_ARM_WAVE.shifted(2)
S_SIT_BODY = merge(at(S_BODY))  # same upper body; the sitting skirt replaces the lower rows

# =============================================================================================
# Animations

SEAT = {'front': (10, 22), 'side': (8, 22), 'back': (10, 22)}
HAND = {'front': (17, 17), 'side': (10, 17), 'back': (17, 17)}


def _crop_upper(layer, last_row):
    from rig import crop_rows
    return crop_rows(layer, layer.row, last_row)


F_UPPER = _crop_upper(F_BODY, 17)
S_UPPER = _crop_upper(S_BODY, 17)
B_UPPER = _crop_upper(B_BODY, 17)


def _lift(layers, lift):
    return [(l, x, y - lift) if l is not None else None for l, x, y in [i if i is not None else (None, 0, 0) for i in layers]]


def _front(dy=0, face=None, arm_l=None, arm_r=None, legs=None, sit=None, head='front', bell=0):
    heads = {'front': F_HEAD, 'side': S_HEAD, 'back': B_HEAD}
    hl = heads[head]
    ly = []
    if sit is None:
        ly += [at(legs or F_LEGS), at(F_BODY, 0, dy)]
    else:
        ly += [at(F_SIT_SKIRT), at(F_UPPER, 0, dy), at(F_SIT_LEGS[sit])]
    ly += [at(F_BELL, bell, dy), arm_l or at(F_ARM_L, 0, dy), arm_r or at(F_ARM_R, 0, dy), at(hl, 0, dy)]
    if head == 'front' and F_FACE.get(face):
        ly.append(at(F_FACE[face], 0, dy))
    return ly


def _side(dy=0, face=None, arm=None, legs='stand', sit=None, head='side', bell=0):
    ly = []
    if sit is None:
        ly += [at(S_LEGS[legs]), at(S_BODY, 0, dy)]
    else:
        ly += [at(S_SIT_LEGS[sit]), at(S_UPPER, 0, dy)]
    hl = {'side': S_HEAD, 'back': S_HEAD_BACKWARD, 'front': F_HEAD}[head]
    ly += [at(S_BELL, bell, dy), arm or at(S_ARM, 0, dy), at(hl, 0, dy)]
    if head == 'side' and S_FACE.get(face):
        ly.append(at(S_FACE[face], 0, dy))
    return ly


def _back(dy=0, arm_l=None, arm_r=None, legs=None, sit=None, head='back', face=None):
    ly = []
    if sit is None:
        ly += [at(legs or F_LEGS), at(B_BODY, 0, dy)]
    else:
        ly += [at(B_SIT_SKIRT), at(B_UPPER, 0, dy)]
    hl = {'back': B_HEAD, 'side': S_HEAD, 'front': F_HEAD}[head]
    ly += [arm_l or at(B_ARM_L, 0, dy), arm_r or at(B_ARM_R, 0, dy), at(hl, 0, dy)]
    if head == 'front' and F_FACE.get(face):
        ly.append(at(F_FACE[face], 0, dy))
    if head == 'side' and S_FACE.get(face):
        ly.append(at(S_FACE[face], 0, dy))
    return ly


S_HEAD_BACKWARD = S_HEAD.flipped(10)


def _a(view, dy=0, hand=None, sit=False, lift=0):
    a = {'hand': hand or (HAND[view][0], HAND[view][1] + dy - lift)}
    if sit:
        a['seat'] = SEAT[view]
    return a


def idle(view, _load=False):
    out = []
    for i, dy in enumerate([0, 0, 1, 1]):
        face = 'blink' if i == 3 else None
        ly = {'front': lambda: _front(dy, face), 'side': lambda: _side(dy, face), 'back': lambda: _back(dy)}[view]()
        out.append(Frame(ly, _a(view, dy)))
    return out


def walk(view, _load=False):
    out = []
    bob = [0, -1, -1, 0, -1, -1]
    legs = ['a', 'a', 'stand', 'b', 'b', 'stand']
    swing = [1, 1, 0, -1, -1, 0]
    for i, dy in enumerate(bob):
        if view == 'front':
            lg = F_LEGS_WALK.get(legs[i], F_LEGS)
            ly = _front(dy, None, at(F_ARM_L, 0, dy + swing[i]), at(F_ARM_R, 0, dy - swing[i]), legs=lg)
        elif view == 'side':
            ly = _side(dy, None, at(S_ARM, swing[i], dy), legs[i] if legs[i] != 'stand' else 'b')
        else:
            lg = F_LEGS_WALK.get(legs[i], F_LEGS)
            ly = _back(dy, at(B_ARM_L, 0, dy - swing[i]), at(B_ARM_R, 0, dy + swing[i]), legs=lg)
        out.append(Frame(ly, _a(view, dy)))
    return out


def hop(view, _load=False):
    """A springy jump: crouch, launch, rise, apex, fall, land (whole sprite moves up)."""
    out = []
    seq = [(0, 2, 'stand', False), (3, -1, 'stand', True), (7, 0, 'tuck', True), (8, 0, 'tuck', True), (4, 0, 'stand', True), (0, 1, 'stand', False)]
    for lift, squash, legs, arms_up in seq:
        if view == 'front':
            lg = F_LEGS_WALK['tuck'] if legs == 'tuck' else F_LEGS
            al = at(F_ARM_L_WAVE, 0, squash) if arms_up else None
            ar = at(F_ARM_R_WAVE, 0, squash) if arms_up else None
            ly = _front(squash, 'grin' if arms_up else None, al, ar, legs=lg)
        elif view == 'side':
            ly = _side(squash, None, at(S_ARM_WAVE, 0, squash) if arms_up else None, 'b' if legs == 'tuck' else 'stand')
        else:
            lg = F_LEGS_WALK['tuck'] if legs == 'tuck' else F_LEGS
            ly = _back(squash, legs=lg)
        out.append(Frame(_lift(ly, lift), _a(view, squash, lift=lift)))
    return out


def float_(view, _load=False):
    """A small float: drifts up and down a few pixels, legs together."""
    out = []
    for lift in [2, 3, 4, 3]:
        if view == 'front':
            ly = _front(0, None, legs=F_LEGS_WALK['tuck'])
        elif view == 'side':
            ly = _side(0, None, legs='b')
        else:
            ly = _back(0, legs=F_LEGS_WALK['tuck'])
        out.append(Frame(_lift(ly, lift), _a(view, 0, lift=lift)))
    return out


SWING = [0, 1, 0, 2]


def sit_load(view, _load=False):
    """Sitting on the load, legs swinging."""
    out = []
    for i, li in enumerate(SWING):
        dy = [0, 0, 1, 0][i]
        face = 'blink' if i == 2 else None
        ly = {'front': lambda: _front(dy, face, sit=li), 'side': lambda: _side(dy, face, sit=li),
              'back': lambda: _back(dy, sit=li)}[view]()
        out.append(Frame(ly, _a(view, dy, sit=True)))
    return out


def sit_talk(view, _load=False):
    """Chattering on the load: mouth flaps, little bounces, a waving hand."""
    out = []
    for i in range(4):
        dy = [0, -1, 0, -1][i]
        face = 'talk' if i % 2 == 0 else 'grin'
        if view == 'front':
            ly = _front(dy, face, arm_r=at(F_ARM_R_WAVE, 0, dy) if i in (1, 2) else None, sit=SWING[i])
        elif view == 'side':
            ly = _side(dy, 'talk' if i % 2 == 0 else None, at(S_ARM_WAVE, 0, dy) if i in (1, 2) else None, sit=SWING[i])
        else:
            ly = _back(dy, arm_r=at(B_ARM_R_POINT, 0, dy - 1) if i in (1, 2) else None, sit=SWING[i])
        out.append(Frame(ly, _a(view, dy, sit=True)))
    return out


def point(view, _load=False, sit=True):
    """Point ahead (3 frames: raise, point, point with a bounce)."""
    out = []
    for i in range(3):
        dy = [0, 0, -1][i]
        si = 0 if sit else None
        if view == 'front':
            arm = at(F_ARM_R_WAVE, 0, dy) if i == 0 else at(F_ARM_R_POINT, 0, dy)
            ly = _front(dy, 'grin' if i else None, arm_r=arm, sit=si)
            hand = (24, 14 + dy) if i else (19, 10 + dy)
        elif view == 'side':
            arm = at(S_ARM_WAVE, 0, dy) if i == 0 else at(S_ARM_POINT, 0, dy)
            ly = _side(dy, None, arm, sit=si)
            hand = (17, 15 + dy) if i else (10, 10 + dy)
        else:
            arm = at(B_ARM_R_POINT, 0, dy)
            ly = _back(dy, arm_r=arm, sit=si)
            hand = (24, 14 + dy)
        out.append(Frame(ly, _a(view, dy, hand=hand, sit=sit)))
    return out


def point_stand(view, _load=False):
    return point(view, _load, sit=False)


def bell(view, _load=False, sit=True):
    """Ring the bell at her collar: grab it, shake left, shake right, let go."""
    out = []
    shakes = [0, -1, 1, 0]
    for i, b in enumerate(shakes):
        si = SWING[i] if sit else None
        if view == 'front':
            arm = at(F_ARM_L_BELL, b, 0) if i < 3 else None
            ly = _front(0, 'grin' if i in (1, 2) else None, arm_l=arm, sit=si, bell=b)
            hand = (9 + b, 15)
        elif view == 'side':
            arm = at(S_ARM_BELL, b, 0) if i < 3 else None
            ly = _side(0, None, arm, sit=si, bell=b)
            hand = (14 + b, 15)
        else:
            ly = _back([0, 0, 1, 0][i], arm_l=at(B_ARM_L, 1, -1) if i in (1, 2) else None, arm_r=at(B_ARM_R, -1, -1) if i in (1, 2) else None, sit=si)
            hand = (10, 15)
        out.append(Frame(ly, _a(view, 0, hand=hand, sit=sit)))
    return out


def bell_stand(view, _load=False):
    return bell(view, _load, sit=False)


def look_back(view, _load=False):
    """While riding: turns to look behind her (3 frames)."""
    out = []
    if view == 'front':
        heads = ['front', 'side', 'side']
        for i, h in enumerate(heads):
            out.append(Frame(_front(0, 'blink' if i == 2 else None, sit=0, head=h), _a(view, 0, sit=True)))
    elif view == 'side':
        heads = ['side', 'back', 'back']
        for i, h in enumerate(heads):
            out.append(Frame(_side(0, None, sit=0, head=h), _a(view, 0, sit=True)))
    else:
        heads = ['back', 'side', 'front']
        for i, h in enumerate(heads):
            out.append(Frame(_back(0, sit=0, head=h, face='grin' if i == 2 else None), _a(view, 0, sit=True)))
    return out


def _prone(i, arm, dx=0, head_dy=0):
    head = merge(at(S_HEAD), at(S_FACE['talk']) if i % 2 else None)
    return [at(PRONE_BODY[i % 2], dx, 0), at(head, 7 + dx, 12 + head_dy), at(PRONE_ARMS[arm], dx, 0)]


def pinned(view, _load=False):
    """Side view: prone under a beam (the beam is a separate prop laid over 'beam'): legs kick in
    turn, arms flail, mouth going."""
    out = []
    for i in range(4):
        out.append(Frame(_prone(i, i % 2), {'hand': (22, 18 + 3 * (i % 2)), 'beam': (3, 21)}))
    return out


def crawl(view, _load=False):
    """Side view: dragging herself out from under it, elbow over elbow (the sprite stays put; move it
    forward by about 2 px per frame)."""
    out = []
    for i in range(4):
        out.append(Frame(_prone(i, (i + 1) % 2, dx=[-1, 0, 0, 1][i], head_dy=[0, -1, 0, -1][i]),
                         {'hand': (21 + [0, 1, 1, 2][i], 18 + 3 * ((i + 1) % 2))}))
    return out


NAME = 'saji'
FRAME = (FW, FH)
ORIGIN = (MX, MY)
F, S, B = 'front', 'side', 'back'

ANIMS = {
    'idle':       (idle,        (F, S, B), 4,  True,  ('main',)),
    'walk':       (walk,        (F, S, B), 10, True,  ('main',)),
    'hop':        (hop,         (F, S, B), 10, False, ('main',)),
    'float':      (float_,      (F, S, B), 5,  True,  ('main',)),
    'pointStand': (point_stand, (F, S, B), 6,  False, ('main',)),
    'bellStand':  (bell_stand,  (F, S, B), 8,  False, ('main',)),
    'sit':        (sit_load,    (F, S, B), 5,  True,  ('main',)),
    'sitTalk':    (sit_talk,    (F, S, B), 8,  True,  ('main',)),
    'sitPoint':   (point,       (F, S, B), 6,  False, ('main',)),
    'sitBell':    (bell,        (F, S, B), 8,  False, ('main',)),
    'lookBack':   (look_back,   (F, S, B), 5,  False, ('main',)),
    'pinned':     (pinned,      (S,),      8,  True,  ('main',)),
    'crawl':      (crawl,       (S,),      6,  True,  ('main',)),
}
SHEETS = {'main': False}
