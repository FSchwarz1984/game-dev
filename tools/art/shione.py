"""垣外しをね (Shione Kaito) - the oni grave-keeper, gentle and absurdly strong.

Reference: assets/reference/illustrations/shione.png. Silver-lilac hair with blunt bangs and a
long low ponytail on her right side tied with red cords; one small dark-red crescent horn on her
right; garnet eyes with two red marks on her right cheek; white kimono with a dark plum collar and
wide sleeves edged plum and pink; a red sash bow with long tails; dark plum hakama with a pink
inner layer at the slit; white tabi boots on thick dark soles. She carries a whole log on her
right shoulder.

Asymmetry: horn and ponytail are on HER right, i.e. the viewer's left in the front view and the
viewer's right from the back. The side view faces right and shows her right side (horn near);
mirroring it for left moves the horn to the far side - accepted, as for the other characters.

Model space: 27 columns, centre column 13; row 36 is the outline under her soles. It maps into the
64x48 frame at (MX, MY) = (19, 9), so the foot pivot is frame pixel (32, 45).
"""

from __future__ import annotations

from pixart import Palette
from rig import L, Frame, at, shear_h, shear_v, merge

PAL = Palette({
    # silver-lilac hair
    'H': ('#f6f1f8', 'hair', 2), 'h': ('#ded4e7', 'hair', 1), 'k': ('#c1b3d1', 'hair', 0), 'K': ('#9a8daf', 'hair', -1), 'Q': ('#706485', 'hair', -2),
    # horn
    'c': ('#86313f', 'horn', 1), 'C': ('#56202d', 'horn', -1),
    # skin, eyes, cheek marks
    's': ('#fde7d8', 'skin', 0), 'z': ('#efbca8', 'skin', -1), 'Z': ('#d4907f', 'skin', -2), 'b': ('#f5a0a2', 'skin', 0),
    'e': ('#b8404c', 'eye', 0), 'E': ('#3b1422', 'eye', -2), 'y': ('#ffffff', 'eye', 2),
    # white kimono, tabi
    'W': ('#fcf9f6', 'white', 2), 'w': ('#ede5e3', 'white', 0), 'v': ('#cdbfcc', 'white', -1), 'V': ('#a093a9', 'white', -2),
    # plum hakama, collar, soles
    'P': ('#73526b', 'plum', 1), 'p': ('#563b50', 'plum', 0), 'u': ('#3f2a3b', 'plum', -1), 'U': ('#2a1a27', 'plum', -2),
    # pink inner layer and sleeve lining
    'F': ('#f3cbc8', 'pink', 1), 'f': ('#daa3a7', 'pink', 0), 'g': ('#b47c87', 'pink', -1),
    # red sash and cords
    'R': ('#cc4b5d', 'red', 1), 'r': ('#9e3548', 'red', 0), 'd': ('#6d2333', 'red', -1),
    # log: bark and the cut end
    'T': ('#9b7757', 'bark', 1), 't': ('#735641', 'bark', 0), 'x': ('#4f3a2c', 'bark', -1),
    'n': ('#ecd3a4', 'wood', 1), 'N': ('#cba874', 'wood', 0), 'm': ('#a3805b', 'wood', -1),
}, outlines={
    # five line colours: soft violet (hair, white cloth), plum-black (horn, hakama, sash, eyes),
    # dusky rose on the pink layer, warm brown on skin, dark brown on the log
    'hair': '#3b3150', 'white': '#3b3150', 'horn': '#2a0f1a', 'plum': '#2a0f1a', 'red': '#2a0f1a', 'eye': '#2a0f1a',
    'pink': '#4a2430', 'skin': '#6a3438', 'bark': '#2a1a10', 'wood': '#2a1a10',
}, default_outline='#2a0f1a', bevel={'hair': 0.7, 'white': 1.0, 'plum': 0.9, 'skin': 1.1, 'bark': 1.2, 'wood': 0.6})

FW, FH = 64, 48
MX, MY = 19, 9
PIVOT = (32, 45)

# =============================================================================================
# FRONT

F_HEAD = L(0, '''
...........................
...........................
...........ooooo...........
.........ooHhhhhoo.........
....oo.ooHhhhhhkkkoo.......
...ocCooKHhhhhhkkkkKo......
...oCCoKhhhkkkkkkkkKKo.....
....oCoKhkkkkkkkkkkkKo.....
....oKCkhkkhkkkhkkkhkKo....
....oKkhkhkkhkkhkkhkKKo....
....oKkhsEEsssssEEskkKo....
....oKkhrEesssssEeskKKo....
....oKkhrbsssssssbskKKo....
....oKkKkzssssZsssskKo.....
....oQKKoozsssssszooKKo....
.....oQQo.ooooooo..oKQo....
......oo............oo.....
''', z=8)

F_FACE = {
    'open': None,
    'blink': L(10, '''
ss....ss
EE....EE
''', col=9, z=8.1),
    'smile': L(10, '''
sEsssssEs
EsEsssEsE
''', col=8, z=8.1),
}

# the ponytail hangs behind her right shoulder (viewer's left), red cords at the nape and low
F_TAIL = L(10, '''
..oo...
.oKko..
oKkkko.
orrrdo.
.okkKo.
.oKkko.
.okkKo.
.oKkko.
.okkKo.
.oKkko.
.okkKo.
.orrdo.
.okkKo.
.oKkKo.
..oKo..
..oo...
''', col=1, z=2)

F_TORSO = L(13, '''
....ozzzo....
..oWwpzpwvo..
.oWWwwpwwwvo.
.oWwwwpwwwvo.
.oWwwwwpwwvo.
.oWwwwwwpwvo.
.oRrrrrrrrdo.
.oRrrrRRrrdo.
.odrrrrrrddo.
''', col=7, z=5)

F_ARM_L = L(14, '''
...ooo.
.oWWWWo
oWWWwwo
oWwwwwo
oWwwvwo
oWwwvwo
oWwvvwo
oWwvwwo
oWvvwwo
opfffpo
.ozsoo.
..oo...
''', col=3, z=6)

F_ARM_R = L(14, '''
.ooo...
owwwwo.
owwwvvo
owwwvvo
owvwvVo
owvwvVo
owvvvVo
owwvvVo
owwvVVo
opffgpo
.oszo..
..oo...
''', col=17, z=6)

F_HAKAMA = L(21, '''
....oPpppfppuo....
....oPppfFfpuo....
...oPpppfFfppuo...
...oPppfFFfppuo...
...oPppfFFfpppuo..
..oPpppfFFfgppuo..
..oPppffFFfgpppuo.
..oPppfFFFFfgppuo.
.oPpppfFFFFfgpppuo
.oPppffFFFFfgppuuo
.oPppfFFFFFFfgppuo
.oooooooooooooooooo
''', col=4, z=3)

F_SASH = L(22, '''
.oRo.
oRrdo
oRrdo
.ordo
.oRdo
.ordo
.oRdo
.ordo
..odo
..oo.
''', col=14, z=7)

F_FEET = {
    'stand': L(33, '''
......owWvo.owwvo.......
......oUuuo.oUuuo.......
......ooooo.ooooo.......
''', z=2),
    'l': L(33, '''
......owWvo.............
......oUuuo.owwvo.......
......ooooo.oUuuo.......
............ooooo.......
''', z=2),
    'r': L(33, '''
............owwvo.......
......owWvo.oUuuo.......
......oUuuo.ooooo.......
......ooooo.............
''', z=2),
}

# =============================================================================================
# SIDE (facing right: her right side, horn near, ponytail falling down her back)

S_HEAD = L(0, '''
...........................
...........................
.........ooooooo...........
.......ooHhhhhhhoo.........
......oHhhhhhhkkkkoo.......
.....oKhhhhhhkkkkkkko......
....oKhkkkkkkkkkkkkkko.....
...oKkhkkkkkoocoohkkkko....
...oKkkkkkkkocCCokhkkkko...
...oKkkkkkkKoCCokkkkkKo....
...oKkkkkkkKkoohssEEso.....
...oKkkkkkkKkhrssEesso.....
...oKkkkkkkKkhrbsssssso....
...oQKkkkkkKkhkzsssZso.....
....oQKkkkKKkoozzzzzo......
.....oQQKKKKoo.ooooo.......
......ooooooo..............
''', z=8)

S_FACE = {
    'open': None,
    'blink': L(10, '''
sss
EEs
''', col=16, z=8.1),
    'smile': L(10, '''
sEs
Ess
''', col=16, z=8.1),
}

S_TAIL = L(12, '''
..oo..
.oKko.
.orro.
.okKo.
.oKko.
.okKo.
.oKko.
.okKo.
.oKko.
.orro.
.okKo.
.oKKo.
..oo..
''', col=3, z=2)

S_TAIL2 = L(12, '''
..oo..
.oKko.
.orro.
.okKo.
.oKko.
okKo..
oKko..
okKo..
oKko..
orro..
okKo..
oKKo..
.oo...
''', col=3, z=2)

S_TORSO = L(13, '''
....ozzo...
...oWwpwo..
..oWWwpwvo.
..oWwwwpvo.
..oWwwwwpo.
..oWwwwwvo.
..oRrrrRrdo
.oRrrrrRRrdo
..odrrrrrdo.
''', col=7, z=5)

S_ARM = L(14, '''
..ooo..
.oWWWo.
oWWWwwo
oWwwwvo
oWwwwvo
oWwwvvo
oWwvwvo
oWwvwvo
oWvvwvo
opffgpo
.oooszo
....oo.
''', col=9, z=6)

S_HAKAMA = L(21, '''
....oPppppuo......
....oPpppppuo.....
...oPppppfppuo....
...oPpppfFfpuo....
...oPpppfFfppuo...
..oPppppfFfppuo...
..oPpppfFFfgppuo..
..oPpppfFFfgppuo..
.oPppppfFFfgpppuo.
.oPpppfFFFfgpppuo.
.oPpppfFFFFfgppuo.
.ooooooooooooooooo
''', col=4, z=3)

S_FEET = {
    'stand': L(33, '''
........owWwvoo.........
........oUuuuuUo........
........oooooooo........
''', z=2),
    'a': L(33, '''
.....owWvo...owWwvoo....
.....oUuuo...oUuuuuUo...
.....ooooo...oooooooo...
''', z=2),
    'b': L(33, '''
.......owWvoowWwvoo.....
.......oUuuooUuuuuUo....
.......oooooooooooo.....
''', z=2),
}

# =============================================================================================
# BACK (horn and ponytail on the viewer's right)

B_HEAD = L(0, '''
...........................
...........................
..........ooooo............
........ooHhhhhoo..........
.......oHhhhhhhkkkoo.oo....
......oKhhhkkkkkkkKoocCo...
.....oKhkkkhkkkkhkKKoCCo...
.....oKhkkkhkkkkhkkKoCo....
....oKkhkkkhkkkkhkkCKo.....
....oKkhkkkhkkkkhkkKKo.....
....oKkhkkkkhkkkkhkKKo.....
....oKkhkkkkhkkkkhkKKo.....
....oKkkhkkkhkkkkhkKKo.....
....oQKkhkkkhkkkhkKKQo.....
.....oQKKkkkkkkkKKQQo......
......ooQQQQQQQQQoo........
........ooooooooo..........
''', z=8)

B_TAIL = L(12, '''
..oo...
.oKko..
.orrro.
.okkKo.
.oKkko.
.okkKo.
.oKkko.
.okkKo.
.oKkko.
.okkKo.
.orrdo.
.okkKo.
.oKkKo.
..oKo..
..oo...
''', col=17, z=9)

B_TORSO = L(13, '''
..ooooooooo..
.oWWwwwwwvvo.
.oWwwwwwwwvo.
.oWwwwwwwwvo.
.oWwwwwwwwvo.
.oWwwwwwwwvo.
.oRrrrrrrrdo.
.oRrRRRrrrdo.
.odrrrrrrddo.
''', col=7, z=5)

B_ARM_L = L(14, '''
...ooo.
.oWWWWo
oWWWwwo
oWwwwwo
oWwwvwo
oWwwvwo
oWwvvwo
oWwvwwo
oWvvwwo
opfffpo
.ozsoo.
..oo...
''', col=3, z=6)

B_ARM_R = L(14, '''
.ooo...
owwwwo.
owwwvvo
owwwvvo
owvwvVo
owvwvVo
owvvvVo
owwvvVo
owwvVVo
opffgpo
.oszo..
..oo...
''', col=17, z=6)

B_HAKAMA = L(21, '''
....oPppppppuo....
....oPppppppuo....
...oPpppppppppo...
...oPppppppppuo...
...oPpppppppppuo..
..oPppppppppppuo..
..oPpppppppppppuo.
..oPpppppppppppuo.
.oPppppppppppppuo.
.oPppppppppppppuuo
.oPpppppppppppppuo
.oooooooooooooooooo
''', col=4, z=3)

B_BOW = L(20, '''
..oo..oo..
.oRrooRro.
.oRrRRrdo.
..ordRdo..
...oRdo...
..ordrdo..
..odo.odo.
...o...o..
''', col=8, z=7)

# =============================================================================================
# The log (a whole cedar trunk) on her right shoulder.

LOG_FRONT = L(5, '''
...ooooooo...
..oTTTTttxo..
.oTnnnnNNmxo.
oTnNNNNNNNmxo
oTnNmmmmmNmxo
oTnNmNNNmNmxo
oTnNmNmNmNmxo
oTnNmNNNmNmxo
oTnNmmmmmNmxo
oTnNNNNNNNmxo
.oTmmmmmmmxo.
..oxxxxxxxo..
...ooooooo...
''', col=-2, z=10)

LOG_SIDE = L(5, '''
..oooooooooooooooooooooooooooooooooooooooooooooooooooo....
.oTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTnno...
otTTttTTTTttTTTTTtTTTTTTttTTTTTtTTTTTTTttTTTTTtTTTTTnNNmo..
ottttttxtttttttttttttxttttttttttttttxtttttttttttttttnNmNmo.
otttxttttttttxttttttttttttxtttttttttttttttxtttttttttnNmNmo.
oxttttttttxttttttttttxtttttttttxtttttttttttttxttttttnNNmo..
.oxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxnmmo...
..oooooooooooooooooooooooooooooooooooooooooooooooooooooo....
''', col=-17, z=10)

LOG_BACK = L(5, '''
..ooooooo....
.oxTTTTTTo...
oxtTTTTTTTo..
oxtttTTTTTo..
oxttttTTTTTo.
oxtttttTTTTo.
oxttttttTTTo.
oxtxttttTTTo.
oxtttttttTTo.
oxttttttttTo.
.oxtttttttto.
..oxxxxxxxo..
...ooooooo...
''', col=17, z=10)

# Arms holding the log: her right hand steadies it on the shoulder.
F_ARM_L_LOG = L(12, '''
.oo....
ozsoo..
ozsWWoo
.oWWwwo
oWWwwwo
oWwwwvo
oWwwvvo
oWwvwvo
oWwvvwo
oWvvwwo
opfffpo
.oooo..
''', col=3, z=11)

S_ARM_LOG = L(9, '''
......oo.
.....ozso
....ozso.
..oooWWo.
.oWWwwwo.
oWWWwwvo.
oWwwwwvo.
oWwwwvvo.
oWwwvvVo.
oWwvvVo..
oWvvVo...
opfgpo...
.oooo....
''', col=8, z=11)

B_ARM_R_LOG = L(12, '''
....oo.
..ooszo
.oowWso
oWwwwvo
oWwwwvo
owwwvvo
owwvvVo
owvvvVo
owvvVVo
owvvVVo
opffgpo
..oooo.
''', col=17, z=11)


# =============================================================================================
# Animations

F, S, B = 'front', 'side', 'back'
HAND = {'front': (5, 24), 'side': (14, 25), 'back': (21, 24)}


def _front(dy=0, face=None, arm_l=None, arm_r=None, feet='stand', tail_dx=0, log=False):
    return [
        at(F_TAIL, tail_dx, dy),
        at(F_FEET[feet]), at(F_HAKAMA), at(F_TORSO, 0, dy), at(F_SASH),
        arm_l or (at(F_ARM_L_LOG, 0, dy) if log else at(F_ARM_L, 0, dy)), arm_r or at(F_ARM_R, 0, dy),
        at(F_HEAD, 0, dy), at(F_FACE[face], 0, dy) if F_FACE.get(face) else None,
        at(LOG_FRONT, 0, dy) if log else None,
    ]


def _side(dy=0, face=None, arm=None, feet='stand', tail=0, log=False):
    return [
        at(S_TAIL2 if tail else S_TAIL, 0, dy),
        at(S_FEET[feet]), at(S_HAKAMA), at(S_TORSO, 0, dy),
        at(S_HEAD, 0, dy), at(S_FACE[face], 0, dy) if S_FACE.get(face) else None,
        at(LOG_SIDE, 0, dy) if log else None,
        arm or (at(S_ARM_LOG, 0, dy) if log else at(S_ARM, 0, dy)),
    ]


def _back(dy=0, arm_l=None, arm_r=None, feet='stand', tail_dx=0, log=False):
    return [
        at(F_FEET[feet]), at(B_HAKAMA), at(B_TORSO, 0, dy),
        arm_l or at(B_ARM_L, 0, dy), arm_r or (at(B_ARM_R_LOG, 0, dy) if log else at(B_ARM_R, 0, dy)),
        at(B_HEAD, 0, dy), at(B_TAIL, tail_dx, dy),
        at(LOG_BACK, 0, dy) if log else None,
    ]


def _anchors(view, dy, log=False):
    a = {'hand': (HAND[view][0], HAND[view][1] + dy)}
    if log:
        a['log'] = {'front': (5, 11), 'side': (13, 9), 'back': (21, 11)}[view]
        a['log'] = (a['log'][0], a['log'][1] + dy)
    return a


def idle(view, _=False, log=False):
    out = []
    for i, dy in enumerate([0, 0, 1, 1]):
        face = 'blink' if i == 3 else None
        ly = {'front': lambda: _front(dy, face, log=log), 'side': lambda: _side(dy, face, log=log, tail=i >= 2),
              'back': lambda: _back(dy, log=log)}[view]()
        out.append(Frame(ly, _anchors(view, dy, log)))
    return out


def walk(view, _=False, log=False):
    out = []
    bob = [0, 1, 0, 0, 1, 0]
    feet_f = ['l', 'l', 'stand', 'r', 'r', 'stand']
    feet_s = ['a', 'a', 'b', 'a', 'a', 'b']
    for i, dy in enumerate(bob):
        if view == 'front':
            sw = [1, 1, 0, -1, -1, 0][i]
            ly = _front(dy, None, None if log else at(F_ARM_L, 0, dy + sw), at(F_ARM_R, 0, dy - sw), feet_f[i], tail_dx=0, log=log)
        elif view == 'side':
            sw = [1, 1, 0, -1, -1, 0][i]
            ly = _side(dy, None, None if log else at(S_ARM, sw, dy), feet_s[i], tail=i % 3 != 0, log=log)
        else:
            sw = [1, 1, 0, -1, -1, 0][i]
            ly = _back(dy, at(B_ARM_L, 0, dy - sw), None if log else at(B_ARM_R, 0, dy + sw), feet_f[i], log=log)
        out.append(Frame(ly, _anchors(view, dy, log)))
    return out


def carry_idle(view, _=False):
    return idle(view, log=True)


def carry_walk(view, _=False):
    return walk(view, log=True)


def bow(view, _=False):
    """A slow, polite bow (5 frames)."""
    out = []
    if view == 'side':
        hip = 23
        for k, hx, hy, tilt, face in [(0.2, 2, 1, 0.1, None), (0.45, 5, 3, 0.22, 'blink'), (0.65, 7, 5, 0.32, 'blink'),
                                      (0.65, 7, 5, 0.32, 'blink'), (0.3, 3, 2, 0.15, None)]:
            upper = shear_h(merge(at(S_TORSO), at(S_ARM)), k, hip)
            head = shear_v(merge(at(S_HEAD), at(S_FACE[face]) if S_FACE.get(face) else None), tilt, 13)
            tail = shear_h(S_TAIL, k, hip)
            ly = [at(tail), at(S_FEET['stand']), at(S_HAKAMA), at(upper), at(head, hx, hy)]
            out.append(Frame(ly, _anchors(view, 0)))
    else:
        for body, head, face in [(1, 2, None), (2, 4, 'blink'), (3, 5, 'blink'), (3, 5, 'blink'), (1, 2, None)]:
            if view == 'front':
                ly = [at(F_TAIL, 0, body), at(F_FEET['stand']), at(F_HAKAMA), at(F_TORSO, 0, body), at(F_SASH),
                      at(F_ARM_L, 1, body), at(F_ARM_R, -1, body), at(F_HEAD, 0, head),
                      at(F_FACE[face], 0, head) if F_FACE.get(face) else None]
            else:
                ly = [at(F_FEET['stand']), at(B_HAKAMA), at(B_TORSO, 0, body), at(B_ARM_L, 1, body),
                      at(B_ARM_R, -1, body), at(B_HEAD, 0, head), at(B_TAIL, 0, head)]
            out.append(Frame(ly, _anchors(view, body)))
    return out


NAME = 'shione'
FRAME = (FW, FH)
ORIGIN = (MX, MY)

ANIMS = {
    'idle':      (idle,       (F, S, B), 4,  True,  ('main',)),
    'walk':      (walk,       (F, S, B), 9,  True,  ('main',)),
    'carryIdle': (carry_idle, (F, S, B), 3,  True,  ('main',)),
    'carryWalk': (carry_walk, (F, S, B), 8,  True,  ('main',)),
    'bow':       (bow,        (F, S, B), 5,  False, ('main',)),
}
SHEETS = {'main': False}
