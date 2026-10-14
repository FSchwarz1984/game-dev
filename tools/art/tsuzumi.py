"""百々つゞみ (Tsuzumi Momo) - hand-pixelled sprite parts and animations.

Reference: assets/reference/illustrations/tsuzumi.png. Extremely wide sugegasa (cream straw top,
indigo underside, a red band over the crown), long straight black-violet hime-cut hair with
white-and-red ties on the side locks, white haori with very wide sleeves (indigo lining) over an
indigo kimono, a red cord bow at the obi with one long red tail, wide indigo trousers gathered by
white ankle wraps, dark split-toe boots. She carries a back-frame (背負子) with a wicker trunk.

Model space: every part is drawn in a 27-column space whose column 13 is her centre line and
whose row 38 is the outline under her soles. It maps into the 48x64 frame at (MX, MY), so the foot
pivot is frame pixel (24, 61). Light comes from the top-left.
"""

from __future__ import annotations

from pixart import Palette, G
from rig import L, Frame, at

# ---------------------------------------------------------------------------------------------
# Palette (colours picked from the illustration, pushed a little for pixel-art saturation)

PAL = Palette({
    # white haori, hat straw, ankle wraps
    'W': ('#fbf7ef', 'white', 2), 'w': ('#ebe3d6', 'white', 0), 'v': ('#cbc0cd', 'white', -1), 'V': ('#9d90aa', 'white', -2),
    # indigo kimono, trousers, hat underside, boots
    'I': ('#5f679f', 'indigo', 1), 'i': ('#42487d', 'indigo', 0), 'n': ('#2f305c', 'indigo', -1), 'N': ('#201e3f', 'indigo', -2),
    # red band, cord, sash, ties
    'R': ('#e3647c', 'red', 1), 'r': ('#c03e5a', 'red', 0), 'd': ('#8c2b45', 'red', -1),
    # hair
    'H': ('#76689e', 'hair', 2), 'j': ('#4d406f', 'hair', 1), 'k': ('#342a4f', 'hair', 0), 'K': ('#231c37', 'hair', -1),
    # skin
    's': ('#fde7d8', 'skin', 0), 'z': ('#efbca8', 'skin', -1), 'Z': ('#d4907f', 'skin', -2), 'b': ('#f5a0a2', 'skin', 0),
    # eyes
    'e': ('#6f84b3', 'eye', 0), 'E': ('#2a2444', 'eye', -2), 'y': ('#ffffff', 'eye', 2),
    # back-frame wood and wicker trunk, straw rope
    'G': ('#b58c5f', 'wood', 1), 'g': ('#8b6443', 'wood', 0), 'u': ('#5e4130', 'wood', -1),
    'T': ('#e1c084', 'wicker', 1), 't': ('#bf9558', 'wicker', 0), 'p': ('#8f6a3c', 'wicker', -1), 'P': ('#644728', 'wicker', -2),
    # dango (eat), lantern paper is a separate prop
    'D': ('#f3d9df', 'food', 1), 'f': ('#9bc46a', 'food', 0), 'F': ('#e6a1b4', 'food', 0),
}, outlines={
    # five line colours: cool near-black (hair, indigo, eyes), soft violet on white cloth and straw,
    # deep red on red cloth, warm brown on skin, dark brown on the wooden frame and wicker
    'hair': '#16122a', 'indigo': '#16122a', 'eye': '#16122a', 'white': '#3b3150',
    'red': '#3e1424', 'food': '#3e1424', 'skin': '#6a3438', 'wood': '#2f1e12', 'wicker': '#2f1e12',
}, default_outline='#16122a', bevel={'hair': 0.7, 'white': 1.0, 'indigo': 0.9, 'skin': 1.1, 'wicker': 0.8, 'wood': 0.6})

FW, FH = 48, 64          # frame size
MX, MY = 11, 23          # model space origin inside the frame
PIVOT = (24, 61)         # foot pivot (frame pixels): centre column, outline row under the soles


# =============================================================================================
# FRONT (facing the camera)

F_HEAD = L(0, '''
.............o.............
...........ooWoo...........
.........ooWWwrvoo.........
.......ooWWwwwrrvvoo.......
.....ooWWwvwwwwrrvvvoo.....
...ooWWWwvwwwwwwrrvvvvoo...
.ooWWWwwvwwwwwwwwrrvvvvvoo.
.onnnnooooooooooooooonNNNo.
..onNoKKKKKKKKKKKKKKKoNNo..
...ookkkkjkkkjkkkjkkkkoo...
....oKkjksEEsssEEskKkKo....
....oKkjksEessseEskKkKo....
....oKkjkbsssssssbkKkKo....
....oKkjkzsssZssszkKkKo....
....oKkjkozssssszokKkKo....
....oKkWwKoooooooKwvkKo....
....oKkrrKKo...oKKrdkKo....
....oKokko.......oKKoKo....
.....o.oo.........oo.o.....
''', z=8)

# Blink and other face swaps for the front head (rows 10-14, cols 9-17).
F_FACE = {
    'open': None,
    'blink': L(10, '''
s..sss..s
sEEsssEEs
''', col=9, z=8.1),
    'happy': L(10, '''
sEssssEss
EsEsssEsE
''', col=8, z=8.1),
    'chew': L(13, '''
sZZs
''', col=12, z=8.1),
    'open_mouth': L(13, '''
sZs
sZs
''', col=12, z=8.1),
    'strain': L(10, '''
sEssssEs
EsEssEsE
''', col=9, z=8.1),
}

F_TORSO = L(16, '''
...ozzzo...
.oWwrzrwvo.
oWWwwrwwwvo
oWwiwniwwvo
oWwiinniwvo
oWwiinnnwvo
oWwwwwrRwvo
odrrrrRrrdo
oWwwwdrdwvo
oWwiiidnwvo
''', col=8, z=5)

F_STRAPS = L(17, '''
.T.......T.
.Tp.....tp.
..Tp...tp..
..tp...tp..
..tp...tp..
''', col=8, z=5.5)

F_ARM_L = L(17, '''
...ooo.
.oWWWWo
oWWWwwo
oWwwwwo
oWwwvwo
oWwwvwo
oWwwvwo
oWwvvwo
oWwvwwo
oiinnno
.ooozso
....oo.
''', col=3, z=6)

F_ARM_R = L(17, '''
.ooo...
owwwwo.
owwwvvo
owwwvvo
owvwvVo
owvwvVo
owvwvVo
owvvvVo
owwvvVo
onnnNNo
oszooo.
.oo....
''', col=17, z=6)

F_SKIRT = L(25, '''
..oWwiinnnwvo..
..oWwiinnnwvo..
..oWwiinnnwvo..
..oWwiinnnwvo..
..oWwwinnwvvo..
.oWwwviinvvvVo.
.oWwvviinnvvVo.
oWwvvoinnnovVVo
ooooooinnnnoooo
.oiiiinnonnnNo.
''', col=6, z=3)

F_LEG_L = L(35, '''
.owWvo.
onnnnno
oNnnnNo
ooooooo
''', col=6, z=2)

F_LEG_R = L(35, '''
.owvvo.
onnnnNo
oNnnnNo
ooooooo
''', col=14, z=2)

F_SASH = L(25, '''
.o..
odo.
ordo
ordo
.odo
.ordo
.ordo
..odo
..ordo
...odo
...oo.
''', col=15, z=7)

F_SASH2 = L(25, '''
.o..
odo.
ordo
ordo
.odo
.odo.
.ordo
.ordo
..odo
..odo
..oo.
''', col=15, z=7)

F_LOAD = L(-10, '''
..o...........o...
.ogo.........ogo..
.ogo.........oguoo
.ogo.........ogoo.
ooooooooooooooooo.
oWWwwwtwwwwwtwwvo.
owwwwwtwwwwwtwvvo.
ovvvvvpvvvvvpvVVo.
oooooooooooooooo..
..oIiiiiiiiiino...
.oIiwiiiiiwiiino..
.oiiiiiwiiiiinNo..
.oiwiiiiiiiwinNo..
''', col=5, z=0)

# =============================================================================================
# SIDE (facing right; mirror for left)

S_HEAD = L(0, '''
.............o.............
...........ooWoo...........
.........ooWrwwvoo.........
.......ooWWrrwwvvvoo.......
.....ooWWWwrrwwwvvvvoo.....
...ooWWWWwwwrrwwwvvvvvoo...
.ooWWWWwwwwwwrrwwwvvvvvvoo.
.onnnooooooooooooooooonnno.
.....oKKKKKKKKKKKKKKKo.....
....oKkkjkkkkkkjkkkkkko....
....oKkkjkkkkKkkjkkkkKo....
....oKkkkjkkKjkssEEsso.....
....oKkkkjkkKjkssEesso.....
....oKkkkkjkKjkbsssssso....
....oKkkkkjkKjkzsssZso.....
....oKkkkkkkKWwozzzzo......
....oKkkkkkkKrrooooo.......
....oKkkkkkKKkko...........
....oKkkkkkKKKKo...........
''', z=8)

S_FACE = {
    'open': None,
    'blink': L(11, '''
sss
EEs
''', col=17, z=8.1),
    'happy': L(11, '''
sEs
Ess
''', col=17, z=8.1),
    'chew': L(14, '''
ZZ
''', col=18, z=8.1),
    'open_mouth': L(14, '''
ZZ
''', col=18, z=8.1),
    'strain': L(11, '''
EsE
sEs
''', col=16, z=8.1),
}

S_HAIR = L(19, '''
...oKkkkkkKo
...oKkkjkkKo
...oKkkjkKo.
...oKkjkkKo.
...oKkjkkKo.
...oKkjkKKo.
...oKkjkKo..
...oKkkkKo..
....oKkKo...
....oKKo....
.....oo.....
''', col=1, z=2)

S_HAIR2 = L(19, '''
...oKkkkkkKo
...oKkkjkkKo
...oKkkjkKo.
..oKkkjkKo..
..oKkjkkKo..
..oKkjkKKo..
..oKkjkKo...
.oKkkkKo....
.oKkKKo.....
.oKKo.......
..o.........
''', col=1, z=2)

S_TORSO = L(17, '''
....ozzo..
..oWwrwo..
.oWWwrwvo.
.oWwwiwvo.
.oWwiinvo.
.oWwiinvo.
.oWwiinvo.
.oWwwwRrdo
odrrrrRrdo
.oWwwwdrdo
.oWwiinvo.
''', col=8, z=5)

S_STRAP = L(17, '''
.T....
.Tp...
..tp..
..tp..
''', col=8, z=6.5)

S_ARM = L(17, '''
..ooo..
.oWWWo.
oWWWwwo
oWwwwvo
oWwwwvo
oWwwvvo
oWwvwvo
oWwvwvo
oWwvwvo
oWwvwvo
oinnnNo
.oooszo
....oo.
''', col=9, z=6)

S_SKIRT = L(25, '''
..oWwiiinvo...
..oWwiiinvo...
..oWwiiinvo...
..oWwiiinvvo..
..oWwwiinvvo..
.oWwwviinvvo..
.oWwvvinnvVo..
.oWwvoinnovVo.
.ooooiinnnoooo
''', col=6, z=3)

# Side legs, one grid per walk phase (rows 33-38): trouser bottoms, wraps, boots pointing right.
S_LEGS = {
    'stand': L(33, '''
..oinnnNo..
..oiinnNo..
..owWWvo...
..onnnnnoo.
..oNnnnnnNo
..oooooooo.
''', col=8, z=2),
    'contact_a': L(33, '''
.oinnoinnNo..
oinNo.oinnNo.
owWo...owWWvo
onno...onnnnnoo
oNNo...oNnnnnnNo
oooo...ooooooooo
''', col=5, z=2),
    'down_a': L(33, '''
..oinnoinNo..
.oinNooinnNo.
.owWo.owWWvo.
.onnoonnnnnoo
oNnNooNnnnnnNo
ooooooooooooo.
''', col=5, z=2),
    'pass_a': L(33, '''
...oinninNo..
...oinNinNo..
...owWoWWvo..
...onnonnnnoo
...oNnoNnnnnNo
...ooooooooooo
''', col=5, z=2),
    'contact_b': L(33, '''
.oinnoinnNo..
oinnNo.oiNo..
owWWvo..owWo.
onnnnnoo.onnoo
oNnnnnnNooNnNo
oooooooooooooo
''', col=5, z=2),
    'down_b': L(33, '''
..oinnoinNo..
..oinNooinNo.
..owWWvoowWo.
..onnnnnoonnoo
.oNnnnnnNoNnNo
.ooooooooooooo
''', col=5, z=2),
}

S_LOAD = L(-10, '''
.........o.......
........ogo......
........ogo......
........ogo......
oooooooooogo.....
oWwwwwwwvoguoo...
oWwwwwwvvogo.....
oWvvvvvVVogo.....
ooooooooooogo....
.oIiwiiinogo.....
.oiiiiwinogo.....
.oiwiiiinogo.....
.oiiiwiinogo.....
.oiiiiinnogo.....
.onnnnnNNogo.....
.ooooooooogo.....
oTTTTTTTpogo.....
optpppppPogo.....
ooooooooooogo....
otTtttWtpogo.....
otptttWtpogo.....
opttptWppogo.....
oWWWWWWWwogo.....
otttptWtpogo.....
otptttWtpogo.....
opttptWppogo.....
otttptWtpogo.....
otptttWtpogo.....
oPPPPPWPPogo.....
ooooooooooogoooo.
..........ogggguo
..........ooooooo
''', col=-1, z=1)

# =============================================================================================
# BACK (facing away)

B_HEAD = L(0, '''
.............o.............
...........ooWoo...........
.........ooWWwrvoo.........
.......ooWWwwwrrvvoo.......
.....ooWWwvwwwwrrvvvoo.....
...ooWWWwvwwwwwwrrvvvvoo...
.ooWWWwwvwwwwwwwwrrvvvvvoo.
.ooWWwwwwwwwwwwwwwvvvvvvoo.
..oooowwwwwwwwwwwwwvvoooo..
.....oooooooooooooooo......
.....oKkkjkkkkjkkkKo.......
.....oKkjkkkkjkkkjKo.......
.....oKkjkkkjkkkkjKo.......
.....oKkjkkkjkkkkjKo.......
.....oKkjkkkjkkkkkKo.......
.....oKkjkkkjkkkkkKo.......
.....oKkjkkkjkkkkKKo.......
''', col=1, z=8)

B_HAIR = L(17, '''
.oKkkkkjkkkkkKKo.
.oKkkkkjkkkkkKKo.
.oKkjkkjkkkjkKo..
.oKkjkkkkkkjkKo..
.oKkjkkkkkkjkKo..
.oKkjkkkkkkkKKo..
.oKkkjkkkkkkKKo..
.oKkkjkkkkkKKo...
.ooKKkkkkkkKKo...
..ooKKkkkkKKoo...
....ooKKKKoo.....
......oooo.......
''', col=5, z=9)

B_HAIR2 = L(17, '''
.oKkkkkjkkkkkKKo.
.oKkkkkjkkkkkKKo.
.oKkjkkjkkkjkKo..
.oKkjkkkkkkjkKo..
..oKjkkkkkkjkKo..
..oKjkkkkkkkKKo..
..oKkjkkkkkkKKo..
..oKkjkkkkkKKo...
..ooKkkkkkkKKo...
...ooKKkkkKKoo...
.....ooKKKKoo....
.......oooo......
''', col=5, z=9)

B_TORSO = L(17, '''
.oooooooooo.
oWWwwwwwwvvo
oWwwwwwwwvvo
oWwwwwwwwvvo
oWwwwwwwwvvo
oWwwwwwwwvvo
oWwwwwwwwvvo
oWwwwwwwwvvo
oWwwwwwwwvvo
oWwwwwwwwvvo
''', col=7, z=5)

B_ARM_L = L(17, '''
....oo.
..ooWWo
.oWWWwo
oWWwwwo
oWwwwvo
oWwwwvo
oWwwvvo
oWwwvwo
oWwwvwo
oWwvvwo
oiinnno
.oszooo
..oo...
''', col=2, z=6)

B_ARM_R = L(17, '''
.oo....
owwoo..
owwwvo.
owwvvvo
owwvvVo
owwvvVo
owvvvVo
owvwvVo
owvwvVo
owvvVVo
onnnNNo
ooozso.
...oo..
''', col=18, z=6)

B_SKIRT = L(26, '''
.oWwwwwwwvvvo..
.oWwwwwwwvvvo..
.oWwwwwwwvvvo..
.oWwwwwwwvvvVo.
.oWwwvwwvvvvVo.
.oWwwvwwvvvvVo.
oWwwwvwwvvvvVVo
ooooooooooooooo
.oiiiinonnnnNo.
''', col=6, z=3)

B_LEG_L = L(35, '''
.owWvo.
onnnnno
oNnnnNo
ooooooo
''', col=6, z=2)

B_LEG_R = L(35, '''
.owvvo.
onnnnNo
oNnnnNo
ooooooo
''', col=14, z=2)

B_SASH = L(28, '''
.o.
odo
odo
ordo
.odo
.oo.
''', col=4, z=7)

B_LOAD = L(-10, '''
..o...........o...
.ogo.........ogo..
.ogo.........oguoo
.ogo.........ogoo.
ooooooooooooooooo.
oWWwwwtwwwwwtwwvo.
owwwwwtwwwwwtwvvo.
ovvvvvpvvvvvpvVVo.
oooooooooooooooo..
..oIiiiiiiiiino...
.oIiwiiiiiwiiino..
.oiiiiiwiiiiinNo..
.oiwiiiiiiiwinNo..
.oiiiiwiiiiiinNo..
.oiiiiiiiwiiinNo..
.oiwiiiiiiiiwnNo..
.onnnnnnnnnnnNNo..
.oooooooooooooo...
.oTTTTTTTTTTTTpo..
.optppppppppppPo..
.oooooooooooooo...
.otTtttWtttpttpo..
.otttptWttptttpo..
.otptttWtpttpppo..
.optttpWptttptpo..
.oWWWWWWWWWWWWwo..
.otttptWttptttpo..
.otptttWtpttpppo..
.optttpWptttptpo..
.otttptWttptttpo..
.otptttWtpttpppo..
.optttpWptttptpo..
.oPPPPPWPPPPPPPo..
.oooooooooooooo...
.ogggggggggggguo..
.oooooooooooooo...
''', col=5, z=10)


# =============================================================================================
# Animations. Each recipe returns a list of Frames for (view, load). Offsets are whole pixels.
# Upper-body bob moves head, torso, arms, straps and the load together; legs stay planted.

LOAD_TOP = {'front': (13, -6), 'side': (3, -6), 'back': (13, -6)}   # where Saji sits (model space)
HOOK = {'front': (21, -7), 'side': (11, -4), 'back': (21, -7)}      # lantern peg tip
HAND_REST = {'front': (8, 28), 'side': (13, 28), 'back': (18, 28)}  # resting hand (front: her right hand)


def _anchors(view, load, dy=0, hand=None, load_dy=None):
    ld = dy if load_dy is None else load_dy
    a = {'hand': hand or (HAND_REST[view][0], HAND_REST[view][1] + dy)}
    if load:
        a['loadTop'] = (LOAD_TOP[view][0], LOAD_TOP[view][1] + ld)
        a['hook'] = (HOOK[view][0], HOOK[view][1] + ld)
    return a


def _front(load, dy=0, face='open', arm_l=None, arm_r=None, legs=(0, 0), skirt=(0, 0), sash=0,
           head_dy=None, over_head=()):
    hd = dy if head_dy is None else head_dy
    face_l = F_FACE.get(face)
    layers = [
        at(F_LOAD, 0, dy) if load else None,
        at(F_LEG_L, 0, legs[0]), at(F_LEG_R, 0, legs[1]),
        at(F_SKIRT, skirt[0], skirt[1]),
        at(F_TORSO, 0, dy),
        at(F_STRAPS, 0, dy) if load else None,
        at(F_SASH2 if sash else F_SASH, skirt[0], skirt[1]),
        arm_l or at(F_ARM_L, 0, dy), arm_r or at(F_ARM_R, 0, dy),
        at(F_HEAD, 0, hd), at(face_l, 0, hd) if face_l else None,
        *over_head,
    ]
    return layers


def _side(load, dy=0, face='open', arm=None, legs='stand', hair=0, head_dy=None, over_head=(), far_arm=None, arm_over=None):
    """arm: the near sleeve under the head; arm_over: a near arm drawn over the head instead
    (raised to the hat, hand at the mouth)."""
    hd = dy if head_dy is None else head_dy
    face_l = S_FACE.get(face)
    return [
        at(S_HAIR2 if hair else S_HAIR, 0, hd),
        at(S_LOAD, 0, dy) if load else None,
        far_arm,
        at(S_LEGS[legs], 0, 0),
        at(S_SKIRT, 0, 0),
        at(S_TORSO, 0, dy),
        None if arm_over else (arm or at(S_ARM, 0, dy)),
        at(S_STRAP, 0, dy) if load else None,
        at(S_HEAD, 0, hd), at(face_l, 0, hd) if face_l else None,
        arm_over,
        *over_head,
    ]


def _back(load, dy=0, arm_l=None, arm_r=None, legs=(0, 0), skirt=(0, 0), hair=0, head_dy=None, sash=0):
    hd = dy if head_dy is None else head_dy
    return [
        at(B_LEG_L, 0, legs[0]), at(B_LEG_R, 0, legs[1]),
        at(B_SKIRT, skirt[0], skirt[1]),
        at(B_SASH, skirt[0] - sash, skirt[1]),
        at(B_TORSO, 0, dy),
        arm_l or at(B_ARM_L, 0, dy), arm_r or at(B_ARM_R, 0, dy),
        at(B_HEAD, 0, hd),
        at(B_HAIR2 if hair else B_HAIR, 0, hd) if not load else None,
        at(B_LOAD, 0, dy) if load else None,
    ]


IDLE_DY = [0, 0, 0, 1, 1, 1, 1, 0]
IDLE_SWAY = [0, 0, 0, 0, 1, 1, 1, 0]


def idle(view, load):
    out = []
    for i, dy in enumerate(IDLE_DY):
        face = 'blink' if i == 6 else 'open'
        if view == 'front':
            ly = _front(load, dy, face, sash=IDLE_SWAY[i])
        elif view == 'side':
            ly = _side(load, dy, face, hair=IDLE_SWAY[i])
        else:
            ly = _back(load, dy, hair=IDLE_SWAY[i], sash=IDLE_SWAY[i])
        out.append(Frame(ly, _anchors(view, load, dy)))
    return out


WALK_BOB = [0, 1, -1, 0, 1, -1]
WALK_FRONT_LEGS = [(-1, 1), (-1, 1), (0, -1), (1, -1), (1, -1), (-1, 0)]
WALK_FRONT_ARMS = [(1, -1), (1, -1), (0, 0), (-1, 1), (-1, 1), (0, 0)]   # extra dy for (left, right) sleeves
WALK_SIDE_LEGS = ['contact_a', 'down_a', 'pass_a', 'contact_b', 'down_b', 'pass_a']
WALK_SIDE_ARM = [1, 1, 0, -1, -1, 0]


def walk(view, load):
    out = []
    for i, dy in enumerate(WALK_BOB):
        if view == 'front':
            al, ar = WALK_FRONT_ARMS[i]
            ly = _front(load, dy, 'open', at(F_ARM_L, 0, dy + al), at(F_ARM_R, 0, dy + ar),
                        legs=WALK_FRONT_LEGS[i], skirt=(0, 0), sash=i % 3 == 2)
        elif view == 'side':
            ly = _side(load, dy, 'open', at(S_ARM, WALK_SIDE_ARM[i], dy), WALK_SIDE_LEGS[i], hair=i % 3 != 0)
        else:
            al, ar = WALK_FRONT_ARMS[i]
            ly = _back(load, dy, at(B_ARM_L, 0, dy + ar), at(B_ARM_R, 0, dy + al),
                       legs=WALK_FRONT_LEGS[i], hair=i % 3 != 0, sash=i % 3 == 2)
        out.append(Frame(ly, _anchors(view, load, dy)))
    return out


# =============================================================================================
# SIDE action parts (facing right). Shoulder at about (12, 18).

S_ARM_FWD = L(17, '''
..ooo.........
.oWWWooooooo..
oWWWWWWWWwwio..
oWwwwwwwwwvnsso
oWwwwwwwwvvNozo
.oWwwwwwvvVo.o.
..oWwwwvvVo....
...owwvvVo.....
....ooooo......
''', col=9, z=6.5)

S_ARM_CHEST = L(17, '''
..ooo....
.oWWWo...
oWWWwwo..
oWwwwwwo.
oWwwwwwio
oWwwwvvnso
oWwwwvvNzo
oWwvwvVoo.
oWwvwvVo..
oWwvvVo...
oinnNNo...
.ooooo....
''', col=9, z=6.5)

S_ARM_OFFER = L(17, '''
..ooo.........
.oWWWo........
oWWWwwoooooo..
oWwwwwwWWwwio.
oWwwwwwwwwvnoo
oWwwwwwwwvvNszo
.oWwwwwwvvVossso
..oWwwwvvVo.ooo.
...owwvvVo......
....ooooo.......
''', col=9, z=6.5)

S_ARM_UP_HALF = L(11, '''
.........oo.
........ossoo
.......oszo..
......oszo...
..ooo.oiio...
.oWWWoWWno...
oWWWwwWwvo...
oWwwwwwwvVo..
oWwwwwwvvVo..
oWwwwwvvVo...
oWwwwvvVo....
oWwvvvVo.....
oWwvvVo......
oinnNo.......
.oooo........
''', col=9, z=6.5)

S_ARM_UP = L(0, '''
.......oo..
......osso.
......oszo.
......oszo.
......oszo.
......oszo.
......oszo.
......oszo.
......oszo.
.....oiino.
.....oWnno.
....oWwvno.
..ooWWwvVo.
.oWWWwwvVo.
oWWWwwwvVo.
oWwwwwwvVo.
oWwwwwvVo..
oWwwwvvVo..
oWwwvvVo...
oWwvvVo....
oWwvVo.....
oinNo......
.ooo.......
''', col=9, z=8.5)

S_ARM_MOUTH = L(9, '''
..........oo...
.........oDDo..
.........oDFo..
.........oFFo..
.........ofDo..
.........offo..
..........osso.
.........oszo..
..ooo...oszo...
.oWWWo.oiio....
oWWWwwoWnno....
oWwwwwwwvVo....
oWwwwwwwvVo....
oWwwwwwvVo.....
oWwwwwvvVo.....
oWwwvvvVo......
oWwvvVVo.......
oinnNNo........
.ooooo.........
''', col=9, z=8.5)

S_ARM_BEAM = L(17, '''
..ooo.........
.oWWWo........
oWWWwwo.......
oWwwwwwoo.....
oWwwwwwwwoo...
oWwwwwwwwwioo.
.oWwwwwwvvnsso
..oWwwwvvVozzo
...owwvvVo.oo.
....ooooo.....
''', col=9, z=6.5)

S_ARM_STRAP = L(17, '''
..ooo...
.oWWWoso
oWWWwwzo
oWwwwwwo
oWwwwvwo
oWwwvvwo
oWwvwvvo
oWwvwvVo
oWwvwvVo
oWwvvvVo
oinnnNo.
.ooooo..
''', col=9, z=6.5)

S_LEGS['crouch'] = L(33, '''
...oiiinnnnNo..
..oiiinnnnnnNo.
..owWWvoowWWvo.
.onnnnnoonnnnnoo
.oNnnnnNoNnnnnnNo
.ooooooooooooooo.
''', col=5, z=2)

S_SKIRT_CROUCH = L(27, '''
...oWwiiinvo...
..oWwwiiinvvo..
.oWwwviiinvvvo.
.oWwvviinnnvVo.
oWwvvoiinnnovVo
oooooiiinnnnooo
''', col=5, z=3)

# Bowing upper bodies (head + torso + near arm), hat tipped forward.
S_BOW1 = L(5, '''
.........o...........
.......ooWoo.........
.....ooWWrwvoo.......
...ooWWWrrwwvvoo.....
.ooWWWWwwrrwwvvvoo...
oWWWWwwwwwrrwwvvvvoo.
oWWWwwwwwwwwrwwvvvvvo
.ooWwwwwwwwwwwwvvvvvo
...ooonnnnnnnnnnoooo.
.....oKKKKKKKKKKKo...
....oKkkjkkkkKjkssEo.
....oKkkjkkkKjkssEeo.
....oKkkkjkkKjkbssssso
...oWKkkkjkKWwozsZso.
..oWWWkkkkkKrrooooo..
.oWWWwwKkkKKKo.......
oWWwwwwwKKKwvo.......
oWwwwwwwwwwwvo.......
oWwwwwwwwwRrdo.......
odrrrrrrrRrrdo.......
oWwwwwwwwwdrdo.......
.oWwwwwwiinvo........
''', col=3, z=7)


def _hand(view, col, row):
    return (col, row)


def take(view, load):
    """Reach out, close the hand, pull it to the chest, hold."""
    out = []
    if view == 'side':
        seq = [(S_ARM_FWD, 0, 0, (23, 20)), (S_ARM_FWD, 1, 0, (24, 20)), (S_ARM_CHEST, 0, 0, (18, 22)), (S_ARM_CHEST, 0, 1, (18, 23))]
        for arm, dx, dy, hand in seq:
            out.append(Frame(_side(load, dy, 'open', at(arm, dx, dy), 'stand'), _anchors(view, load, dy, (hand[0] + dx, hand[1] + dy))))
    elif view == 'front':
        seq = [(F_ARM_L_REACH, 0, 0, (4, 29)), (F_ARM_L_REACH, 0, 1, (4, 30)), (F_ARM_L_CHEST, 0, 0, (11, 23)), (F_ARM_L_CHEST, 0, 1, (11, 24))]
        for arm, dx, dy, hand in seq:
            out.append(Frame(_front(load, dy, 'open', arm_l=at(arm, dx, dy)), _anchors(view, load, dy, hand)))
    return out


def give(view, load):
    """Hold it at the chest, push it forward, hold it out, return."""
    out = []
    if view == 'side':
        seq = [(S_ARM_CHEST, 0, 0, (18, 22)), (S_ARM_OFFER, 0, 0, (23, 23)), (S_ARM_OFFER, 1, 0, (24, 23)), (S_ARM_CHEST, 0, 0, (18, 22))]
        for arm, dx, dy, hand in seq:
            out.append(Frame(_side(load, dy, 'open', at(arm, dx, dy), 'stand'), _anchors(view, load, dy, (hand[0] + dx, hand[1] + dy))))
    elif view == 'front':
        seq = [(F_ARM_L_CHEST, F_ARM_R_CHEST, (13, 23)), (F_ARM_L_OFFER, F_ARM_R_OFFER, (13, 27)),
               (F_ARM_L_OFFER, F_ARM_R_OFFER, (13, 27)), (F_ARM_L_CHEST, F_ARM_R_CHEST, (13, 23))]
        for i, (al, ar, hand) in enumerate(seq):
            dy = 1 if i == 2 else 0
            out.append(Frame(_front(load, 0, 'open', arm_l=at(al, 0, dy), arm_r=at(ar, 0, dy)), _anchors(view, load, 0, (hand[0], hand[1] + dy))))
    return out


def push(view, load):
    """Side only: wind up, push the hand forward into the door, lean, hold."""
    out = []
    seq = [(S_ARM_CHEST, 0, 0, 0, (18, 22)), (S_ARM_FWD, 0, 0, 0, (23, 20)), (S_ARM_FWD, 1, 0, 1, (24, 20)), (S_ARM_FWD, 1, 0, 1, (24, 20))]
    for arm, dx, dy, lean, hand in seq:
        ly = _side(load, dy, 'open', at(arm, dx + lean, dy), 'stand', head_dy=dy)
        # lean: head and torso one pixel forward
        ly = [(l, x + (lean if l in (S_HEAD, S_TORSO, S_LOAD, S_STRAP, S_HAIR, S_HAIR2) or l in S_FACE.values() else 0), y) if l is not None else None for l, x, y in [i if i is not None else (None, 0, 0) for i in ly]]
        out.append(Frame(ly, _anchors(view, load, dy, (hand[0] + dx + lean, hand[1] + dy))))
    return out


def reach_up(view, load):
    """Raise a lantern to a hook: arm half up, fully up, up on her toes, hold."""
    out = []
    if view == 'side':
        seq = [(S_ARM_UP_HALF, 0, (20, 11)), (S_ARM_UP, 0, (16, 1)), (S_ARM_UP, -1, (16, 0)), (S_ARM_UP, 0, (16, 1))]
        for arm, dy, hand in seq:
            out.append(Frame(_side(load, dy, 'open', legs='stand', arm_over=at(arm, 0, dy)), _anchors(view, load, dy, (hand[0], hand[1] + dy))))
    elif view == 'back':
        return reach_up_back(load)
    return out


def eat(view, load):
    """Bring a dango to her mouth, bite, chew, lower it."""
    out = []
    if view == 'side':
        seq = [(S_ARM_CHEST, 'open', (18, 22)), (S_ARM_MOUTH, 'open_mouth', (19, 15)), (S_ARM_MOUTH, 'chew', (19, 15)), (S_ARM_CHEST, 'chew', (18, 22))]
        for arm, face, hand in seq:
            if arm is S_ARM_MOUTH:
                ly = _side(load, 0, face, legs='stand', arm_over=at(arm, 0, 0))
            else:
                ly = _side(load, 0, face, at(arm, 0, 0), 'stand')
            out.append(Frame(ly, _anchors(view, load, 0, hand)))
    elif view == 'front':
        seq = [(F_ARM_L_CHEST, 'open', (11, 23)), (F_ARM_L_MOUTH, 'open_mouth', (12, 15)), (F_ARM_L_MOUTH, 'chew', (12, 15)), (F_ARM_L_CHEST, 'chew', (11, 23))]
        for arm, face, hand in seq:
            over = (at(arm, 0, 0),) if arm is F_ARM_L_MOUTH else ()
            out.append(Frame(_front(load, 0, face, arm_l=None if over else at(arm, 0, 0), over_head=over,
                                    ) if not over else _front_with_arm_over(load, face, arm), _anchors(view, load, 0, hand)))
    return out


def _front_with_arm_over(load, face, arm):
    ly = _front(load, 0, face)
    # replace the left sleeve and draw the raised arm over the face
    ly = [i for i in ly if not (i is not None and i[0] is F_ARM_L)]
    return ly + [at(arm, 0, 0)]


def strain(view, load):
    """Without the load: knees bent, both hands under a heavy beam, shaking, a little lift."""
    out = []
    if view == 'side':
        seq = [(0, 'open'), (1, 'strain'), (2, 'strain'), (1, 'strain')]
        for i, (sh, face) in enumerate(seq):
            dy = 3
            shake = [0, 0, 1, 0][i]
            ly = [
                at(S_HAIR, shake, dy),
                at(S_LEGS['crouch'], 0, 0),
                at(S_SKIRT_CROUCH, 0, 0),
                at(S_TORSO, shake, dy),
                at(S_ARM_BEAM, shake, dy - [0, 0, 0, 1][i]),
                at(S_HEAD, shake, dy), at(S_FACE[face], shake, dy) if S_FACE.get(face) else None,
            ]
            out.append(Frame(ly, {'hand': (22 + shake, 24 + dy - [0, 0, 0, 1][i])}))
    elif view == 'front':
        seq = ['open', 'strain', 'strain', 'strain']
        for i, face in enumerate(seq):
            dy = 3
            shake = [0, 0, 1, 0][i]
            lift = [0, 0, 0, 1][i]
            ly = [
                at(F_LEG_L_CROUCH, 0, 0), at(F_LEG_R_CROUCH, 0, 0),
                at(F_SKIRT, 0, 2),
                at(F_TORSO, shake, dy), at(F_SASH, 0, 2),
                at(F_ARM_L_BEAM, shake, dy - lift), at(F_ARM_R_BEAM, shake, dy - lift),
                at(F_HEAD, shake, dy), at(F_FACE[face], shake, dy) if F_FACE.get(face) else None,
            ]
            out.append(Frame(ly, {'hand': (13 + shake, 27 + dy - lift)}))
    return out


def heavy_idle(view, load):
    """Holding extra weight: sunk two pixels, shoulders down, slow heavy breath."""
    out = []
    for i, b in enumerate([2, 2, 3, 3]):
        if view == 'front':
            ly = _front(load, b, 'blink' if i == 3 else 'open', skirt=(0, 1), head_dy=b + 1)
        elif view == 'side':
            ly = _side(load, b, 'open', head_dy=b + 1)
            ly = [(S_SKIRT, 0, 1) if (i2 is not None and i2[0] is S_SKIRT) else i2 for i2 in ly]
        else:
            ly = _back(load, b, skirt=(0, 1), head_dy=b + 1)
        out.append(Frame(ly, _anchors(view, load, b)))
    return out


# =============================================================================================
# FRONT action parts. Her right sleeve is on the viewer's left (F_ARM_L), shoulder ~ (8, 18).

F_ARM_L_CHEST = L(17, '''
...ooo....
.oWWWWo...
oWWWwwo...
oWwwwwo...
oWwwwwwoo.
oWwwwwwiso
oWwwwvvnzo
oWwwvvVoo.
oWwvvVo...
oWvvVo....
oinNo.....
.ooo......
''', col=3, z=6.5)

F_ARM_R_CHEST = L(17, '''
.ooo......
owwwwo....
owwwvvo...
owwwvvo...
oowwwvvo..
osinwvVo..
ozNnvvVo..
.oowvvVo..
...owvVo..
....ovVVo.
.....oNNo.
......ooo.
''', col=14, z=6.5)

F_ARM_L_OFFER = L(17, '''
...ooo.....
.oWWWWo....
oWWWwwo....
oWwwwwwo...
oWwwwwwo...
oWwwwwwwo..
oWwwwwwwoo.
oWwwwwvvino
oWwwwvvVnso
.oWwvvVoozo
..oinNo..o.
...ooo.....
''', col=3, z=6.5)

F_ARM_R_OFFER = L(17, '''
.....ooo...
....owwwwo.
....owwwvvo
...owwwvvVo
...owwwvvVo
..owwwvvvVo
.oowwwvvVVo
oinwvvvVVVo
osnNvvVVVo.
ozoovvVVo..
.o..oNNNo..
.....ooo...
''', col=12, z=6.5)

F_ARM_L_REACH = L(17, '''
...ooo...
.oWWWWo..
oWWWwwo..
oWwwwwo..
oWwwwwwo.
oWwwwwwo.
oWwwwwvo.
oWwwwvvo.
oWwwvvVo.
oWwvvVo..
oinnNo...
oszoo....
oso......
.o.......
''', col=1, z=6.5)

F_ARM_L_MOUTH = L(9, '''
.oo.oo.oo...
oFFoDDoffo..
oFFoDDoffoso
.oo.oo.oozzo
........oso.
.......oszo.
.......oszo.
......oiino.
....ooWWnno.
..ooWWWwvVo.
.oWWWwwwvVo.
oWWwwwwwvVo.
oWwwwwwvvVo.
oWwwwwwvVo..
oWwwwwvvVo..
oWwwwvvVo...
oWwwvvVo....
oWwvvVo.....
oinnNo......
.oooo.......
''', col=2, z=8.5)

F_ARM_L_BEAM = L(17, '''
...ooo....
.oWWWWo...
oWWWwwo...
oWwwwwwo..
oWwwwwwo..
oWwwwwwwo.
oWwwwwwwo.
oWwwwwvvo.
.oWwwvvino
..oWvvVnso
...oinNozo
....ooo.o.
''', col=3, z=6.5)

F_ARM_R_BEAM = L(17, '''
....ooo...
...owwwwo.
...owwwvvo
..owwwvvVo
..owwwvvVo
.owwwvvvVo
.owwwvvvVo
.owwvvvVVo
oinwvvVVo.
osnvvVVo..
ozoNNNo...
.o.ooo....
''', col=14, z=6.5)

F_LEG_L_CROUCH = L(35, '''
.owWvo..
onnnnno.
oNnnnNo.
ooooooo.
''', col=5, z=2)

F_LEG_R_CROUCH = L(35, '''
.owvvo.
onnnnNo
oNnnnNo
ooooooo
''', col=15, z=2)


# =============================================================================================
# Bow. The upper body leans around the hips with a horizontal shear; the head drops forward and
# the hat brim tips with a vertical shear. The load leans with the back.

from rig import shear_h, shear_v, merge, crop_rows

HIP_ROW = 27


def _bow_side(load, k, head_dx, head_dy, tilt, face='blink'):
    upper = merge(at(S_TORSO), at(S_ARM_CHEST if k > 0.5 else S_ARM))
    upper = shear_h(upper, k, HIP_ROW)
    head = merge(at(S_HEAD), at(S_FACE[face]) if S_FACE.get(face) else None)
    head = shear_v(head, tilt, 13)
    hair = shear_h(S_HAIR, k * 0.5, HIP_ROW)
    ly = [
        at(hair, 0, 0),
        at(shear_h(S_LOAD, k, HIP_ROW), 0, 0) if load else None,
        at(S_LEGS['stand']), at(S_SKIRT),
        at(upper),
        at(shear_h(S_STRAP, k, HIP_ROW)) if load else None,
        at(head, head_dx, head_dy),
    ]
    return ly


def bow(view, load):
    """Deep bow: lean in, hold low, come back up (5 frames)."""
    out = []
    if view == 'side':
        steps = [(0.25, 3, 1, 0.12, 'open'), (0.5, 6, 3, 0.26, 'blink'), (0.62, 7, 5, 0.36, 'blink'),
                 (0.62, 7, 5, 0.36, 'blink'), (0.38, 5, 2, 0.2, 'open')]
        for k, hx, hy, tilt, face in steps:
            ly = _bow_side(load, k, hx, hy, tilt, face)
            a = _anchors(view, load, 0)
            if load:
                # the load top leans with the back: shift = k * (HIP_ROW - row)
                for name in ('loadTop', 'hook'):
                    c, r = a[name]
                    a[name] = (c + int(round(k * (HIP_ROW - r))), r)
            out.append(Frame(ly, a))
    elif view == 'back':
        steps = [(1, 1), (3, 3), (4, 5), (4, 5), (2, 2)]
        for body, head in steps:
            ly = _back(load, body, head_dy=head)
            out.append(Frame(ly, _anchors(view, load, body)))
    elif view == 'front':
        steps = [(1, 2, 'open', False), (2, 3, 'blink', True), (3, 4, 'blink', True), (3, 4, 'blink', True), (1, 2, 'open', False)]
        for body, head, face, dish in steps:
            ly = _front(load, body, face, head_dy=head, arm_l=at(F_ARM_L_CHEST, 0, body), arm_r=at(F_ARM_R_CHEST, 0, body))
            if dish:
                ly = [i for i in ly if not (i is not None and (i[0] is F_HEAD or i[0] in F_FACE.values()))]
                ly.append(at(F_HEAD_BOW, 0, head - 2))
            out.append(Frame(ly, _anchors(view, load, body)))
    return out


# =============================================================================================
# BACK action parts. Her right arm is on the viewer's right (shoulder ~ (19, 18)).

B_ARM_R_UP_HALF = L(10, '''
.......oo
......oso
.....oszo
....oiio.
...oWnno.
..owwvNo.
.owwwvVo.
owwwvvVo.
owwwvVVo.
owwvvVo..
owwvVVo..
owvvVo...
onnNNo...
.oooo....
''', col=18, z=11)

B_ARM_R_UP = L(-1, '''
..oo...
.osso..
.oszo..
.oszo..
.oszo..
.oszo..
.oszo..
.oszo..
.oszo..
.oszo..
.oino..
oWnnNo.
owwvVo.
owwvVo.
owwvVo.
owvvVo.
owvVo..
owvVo..
owvVo..
owvVo..
owvVo..
onNNo..
.ooo...
''', col=18, z=11)

B_ARM_L_UP = L(-1, '''
...oo..
..osso.
..oszo.
..oszo.
..oszo.
..oszo.
..oszo.
..oszo.
..oszo.
..oszo.
..oino.
.oWWno.
.oWwwvo
.oWwwvo
.oWwwvo
.oWwvvo
..oWwvo
..oWwvo
..oWwvo
..oWwvo
..oWwvo
..oinNo
...ooo.
''', col=2, z=11)

B_ARM_L_UP_HALF = L(10, '''
oo.......
oso......
ozso.....
.oiio....
.onnWo...
.oNvwwo..
.oVvwwwo.
.oVvvwwwo
.oVVvwwwo
..oVvwwWo
..oVVvwWo
...oVvwWo
...oNNnno
....oooo.
''', col=0, z=11)

B_ARM_R_SHOUT = L(11, '''
.oo.......
oszo......
.oszo.....
..oinoo...
..oWwnNo..
.ooWwwvNo.
oWWwwvvVo.
owwwvvVVo.
.owwvvVo..
.owvvVVo..
..ovVVo...
..onNNo...
...ooo....
''', col=16, z=11)

B_ARM_L_SHOUT = L(11, '''
.......oo.
......ozso
.....ozso.
...ooino..
..oNnwWo..
.oNvwwWoo.
.oVvvwwWWo
.oVVvvwwwo
..oVvvwwo.
..oVVvvwo.
...oVVvo..
...oNNno..
....ooo...
''', col=1, z=11)

B_SIT_SKIRT = L(26, '''
..oWwwwwwwvvvo...
.oWWwwwwwwvvvVo..
oWWwwwwwwwwvvvVo.
ooooooooooooooooo
''', col=5, z=3)

# Lower legs hanging from the branch, seen from behind: no thighs (they point away), so the legs
# are short; the swinging leg rises a pixel as it swings forward (away from the camera).
B_SIT_LEGS = [L(29, '''
...oiinno.onnnNo..
...owWWvo.owvvvo..
...onnnno.onnnNo..
...ooooo..ooooo...
''', col=4, z=2), L(29, '''
...oiinno.onnnNo..
...owWWvo.owvvvo..
...onnnno.onnnNo..
...ooooo..oNnnNo..
..........ooooo...
''', col=4, z=2), L(29, '''
...oiinno.onnnNo..
...owWWvo.owvvvo..
...onnnno.onnnNo..
...oNnnNo.ooooo...
...ooooo..........
''', col=4, z=2)]


def _back_top(load, dy=0, arm_l=None, arm_r=None, legs=(0, 0), skirt=(0, 0), head_dy=None, top=()):
    """Back view with arms drawn after the load (raised arms beside the tower)."""
    hd = dy if head_dy is None else head_dy
    return [
        at(B_LEG_L, 0, legs[0]), at(B_LEG_R, 0, legs[1]),
        at(B_SKIRT, skirt[0], skirt[1]),
        at(B_SASH, skirt[0], skirt[1]),
        at(B_TORSO, 0, dy),
        arm_l if arm_l and not load else None, arm_r if arm_r and not load else None,
        at(B_HEAD, 0, hd),
        at(B_HAIR, 0, hd) if not load else None,
        at(B_LOAD, 0, dy) if load else None,
        arm_l if arm_l and load else None, arm_r if arm_r and load else None,
        *top,
    ]


def reach_up_back(load):
    out = []
    seq = [(B_ARM_R_UP_HALF, 0, (25, 11)), (B_ARM_R_UP, 0, (21, 0)), (B_ARM_R_UP, -1, (21, -1)), (B_ARM_R_UP, 0, (21, 0))]
    for arm, dy, hand in seq:
        ly = _back_top(load, dy, arm_l=at(B_ARM_L, 0, dy), arm_r=at(arm, 0, dy))
        out.append(Frame(ly, _anchors('back', load, dy, hand)))
    return out


def climb(view, load):
    """Back view: hand over hand, knees lifting in turn (4 frames)."""
    out = []
    seq = [
        (at(B_ARM_L_UP, 0, 0), at(B_ARM_R_UP_HALF, 0, 2), (-3, 0), 0, (3, 1)),
        (at(B_ARM_L_UP, 0, 1), at(B_ARM_R_UP_HALF, 0, 1), (-2, 0), -1, (3, 2)),
        (at(B_ARM_L_UP_HALF, 0, 2), at(B_ARM_R_UP, 0, 0), (0, -3), 0, (22, 1)),
        (at(B_ARM_L_UP_HALF, 0, 1), at(B_ARM_R_UP, 0, 1), (0, -2), -1, (22, 2)),
    ]
    for al, ar, legs, dy, hand in seq:
        ly = _back_top(load, dy, arm_l=al, arm_r=ar, legs=legs)
        out.append(Frame(ly, _anchors('back', load, dy, hand)))
    return out


def shout(view, load):
    """Back view: hands cupped at her mouth, elbows out; leans in on the shout (3 frames)."""
    out = []
    seq = [(1, 0), (0, -1), (0, -1)]
    for i, (dy, hd) in enumerate(seq):
        ly = _back_top(load, dy, arm_l=at(B_ARM_L_SHOUT, 0, dy), arm_r=at(B_ARM_R_SHOUT, 0, dy), head_dy=hd)
        out.append(Frame(ly, _anchors('back', load, dy, (13, 13))))
    return out


def sit_branch(view, load):
    """Back view: sitting on a branch (seat anchor at the hips), legs swinging (4 frames)."""
    out = []
    order = [0, 1, 0, 2]
    for i, li in enumerate(order):
        dy = 0
        ly = [
            at(B_SIT_LEGS[li], 0, 0),
            at(B_SIT_SKIRT, 0, 0),
            at(B_TORSO, 0, dy),
            at(B_ARM_L, 0, dy), at(B_ARM_R, 0, dy),
            at(B_HEAD, 0, dy),
            at(B_HAIR, 0, dy) if not load else None,
            at(B_LOAD, 0, dy) if load else None,
        ]
        a = _anchors('back', load, dy)
        a['seat'] = (13, 29)
        out.append(Frame(ly, a))
    return out


# =============================================================================================
# Asleep on her back with the hat over her face, then sitting up (no load). Head to the left,
# feet to the right (this is a side-view animation: mirror for the other direction).

ASLEEP = [L(27, '''
............o..............................
..........ooWoo............................
........ooWWwrvoo..........................
......ooWWwwwrrvvoo........ooo.............
....ooWWwvwwwwrrvvvooooooooWWWoooooo....oo.
..ooWWWwvwwwwwwrrvvvvoWWWWwWwwwwwwWo..oNNo.
ooWWWwwvwwwwwwwwrrvvvvowwwwwwwvwwwwooonnno.
okkKKooooooooooooooooKoiiwrRrdiiwwwvvoonnNo
okKKKkkKKoozzzo..owwwoiiiwdrdniiwvvvvvownno
.ooKKkkKoowwwwwoowWwwwonnnnddnnnnnvvVoowno.
...oooooowwwwwwwwwwwwwoozsoooonnnnooooooo..
.......oooooooooooooooo.oo....ooooo........
''', col=-8, z=4), L(27, '''
............o..............................
..........ooWoo............................
........ooWWwrvoo..........................
......ooWWwwwrrvvoo........................
....ooWWwvwwwwrrvvvooooooooooooooooo....oo.
..ooWWWwvwwwwwwrrvvvvoWWWWwWwwwwwwWo..oNNo.
ooWWWwwvwwwwwwwwrrvvvvowwwwwwwvwwwwooonnno.
okkKKooooooooooooooooKoiiwrRrdiiwwwvvoonnNo
okKKKkkKKoozzzo..owwwoiiiwdrdniiwvvvvvownno
.ooKKkkKoowwwwwoowWwwwonnnnddnnnnnvvVoowno.
...oooooowwwwwwwwwwwwwoozsoooonnnnooooooo..
.......oooooooooooooooo.oo....ooooo........
''', col=-8, z=4)]

# Propped on her elbows: the hat still tipped over her eyes.
SITUP_PROP = L(22, '''
.............o.............
...........ooWoo...........
.........ooWWwrvoo.........
.......ooWWwwwrrvvoo.......
.....ooWWwvwwwwrrvvvoo.....
...ooWWWwvwwwwwwrrvvvvoo...
.ooWWWwwvwwwwwwwwrrvvvvvoo.
.onnnnooooooooooooooonnnno.
..oKkoKKKKKKKKKKKKKKKkKo...
..oKkkkkzsssZssoKkkkkkKo.....oo.
..oKKkkkozzzzzoooWWwwwwoooooonNo
...oKKkkooWwrwwoWwwwwwwwwwwvoonno
....oKkkowwwrRrdoiiiiinnnnnnvonNo
....oKkWWoWwdrdoiiiiinnnnnnnnoono
...oWWwwWoWwwwwoiiinnnnnnnnnnnoo.
..oWWwwwwoooooooooooooooooooooo..
..oooooooo.......................
''', col=-2, z=5)

# Sitting on the ground facing right, legs out along the ground.
S_SIT_LEGS = L(32, '''
.oWWwwwwwwwwwwvo..oo.
oWwwwiiiinnnnnnoonNo.
oWwwiiiinnnnnnnnoNno.
oWwvvinnnnnnnnnNowWo.
.oooooooooooooooonnoo
.................ooo.
''', col=4, z=3)


def asleep(view, load):
    """Side view only (mirror for the other way): two breathing frames, slow."""
    return [Frame([at(ASLEEP[i])], {'hand': (14, 39)}) for i in (0, 1)]


def _sit_ground(face='open', hat_tilt=0.0, arm=None):
    head = S_HEAD if not hat_tilt else shear_v(merge(at(S_HEAD), at(S_FACE[face]) if S_FACE.get(face) else None), hat_tilt, 13)
    dy = 8
    return [
        at(S_HAIR, 0, dy - 4),
        at(S_SIT_LEGS),
        at(S_TORSO, 0, dy), at(arm or S_ARM, 0, dy - 1),
        at(head, 0, dy) if hat_tilt else at(S_HEAD, 0, dy),
        at(S_FACE[face], 0, dy) if (S_FACE.get(face) and not hat_tilt) else None,
    ]


def sit_up(view, load):
    """Side view: lying, propped on elbows, sitting with the hat over her eyes, hat pushed back."""
    return [
        Frame([at(ASLEEP[0])], {'hand': (14, 39)}),
        Frame([at(SITUP_PROP)], {'hand': (8, 37)}),
        Frame(_sit_ground('blink', 0.18), {'hand': (13, 36), 'seat': (12, 38)}),
        Frame(_sit_ground('open'), {'hand': (13, 36), 'seat': (12, 38)}),
    ]


def sit(view, load):
    """Side view: sitting on the ground (cutscenes), breathing and a blink."""
    out = []
    for i in range(4):
        ly = _sit_ground('blink' if i == 3 else 'open')
        if i in (1, 2):
            ly = [(l, x, y + 1) if (l is not None and l not in (S_SIT_LEGS,)) and l is not S_HAIR else (l, x, y) if l is not None else None
                  for l, x, y in [i2 if i2 is not None else (None, 0, 0) for i2 in ly]]
        out.append(Frame(ly, {'hand': (13, 36), 'seat': (12, 38)}))
    return out


# =============================================================================================
# Shouldering the frame: crouch with her back to the standing load, slip the straps on, rise.

def shoulder(view, load):
    out = []
    if view == 'side':
        # (load dx, load dy, body dy, legs, arm)
        seq = [(-5, 14, 3, 'crouch', S_ARM), (-1, 12, 3, 'crouch', S_ARM_STRAP), (0, 5, 1, 'stand', S_ARM_STRAP), (0, 0, 0, 'stand', S_ARM)]
        for ldx, ldy, dy, legs, arm in seq:
            ly = [
                at(S_HAIR, 0, dy),
                at(S_LOAD, ldx, ldy),
                at(S_LEGS[legs]),
                at(S_SKIRT_CROUCH) if legs == 'crouch' else at(S_SKIRT),
                at(S_TORSO, 0, dy),
                at(arm, 0, dy),
                at(S_STRAP, 0, dy) if ldy < 13 else None,
                at(S_HEAD, 0, dy),
            ]
            a = {'hand': (14, 18 + dy), 'loadTop': (LOAD_TOP['side'][0] + ldx, LOAD_TOP['side'][1] + ldy),
                 'hook': (HOOK['side'][0] + ldx, HOOK['side'][1] + ldy)}
            out.append(Frame(ly, a))
    elif view == 'front':
        seq = [(14, 3), (12, 3), (5, 1), (0, 0)]
        for ldy, dy in seq:
            legs = (0, 0)
            ly = [
                at(F_LOAD, 0, ldy),
                at(F_LEG_L_CROUCH if dy > 1 else F_LEG_L), at(F_LEG_R_CROUCH if dy > 1 else F_LEG_R),
                at(F_SKIRT, 0, min(dy, 2)),
                at(F_TORSO, 0, dy), at(F_STRAPS, 0, dy) if ldy < 13 else None,
                at(F_SASH, 0, min(dy, 2)),
                at(F_ARM_L_CHEST if 0 < ldy < 13 else F_ARM_L, 0, dy), at(F_ARM_R_CHEST if 0 < ldy < 13 else F_ARM_R, 0, dy),
                at(F_HEAD, 0, dy),
            ]
            a = {'hand': (11, 23 + dy), 'loadTop': (LOAD_TOP['front'][0], LOAD_TOP['front'][1] + ldy),
                 'hook': (HOOK['front'][0], HOOK['front'][1] + ldy)}
            out.append(Frame(ly, a))
    return out





# Front bow, deep frames: the head tips toward the camera, so the hat shows its top as a broad
# dish (apex near the middle, the red band running to her left) and the face disappears under it.
F_HEAD_BOW = L(5, '''
.......ooooooooooooo.......
....oooWWWWwwwwwwvvvooo....
..ooWWWWwwwwwwwwwwvvvvvoo..
.oWWWwwwwwwwwrwwwwwvvvvvvo.
oWWWwwwwwwwwrRwwwwwwvvvvvvo
oWWwwwwwwwwwoRrwwwwwwvvvvVo
oWwwwwwwwwwwwrRrwwwwwvvvvVo
.oWwwwwwwwwwwwrRrwwwwvvvVo.
..ooWwwwwwwwwwwwrRrwvvvoo..
....ooonnnnnnnnnnnnnooo....
......oKKkkkkkkkkkKKo......
.......oKKkKKKkKKKKo.......
........oooooooooo.........
''', z=8.5)


# =============================================================================================
# From the first brief: release (放: both arms flung out), hurt, look up, lift and carry overhead.

# Front head tipped back: the hat's indigo underside opens up like the illustration; she looks up.
F_HEAD_UP = L(1, '''
.......ooooooooooooo.......
....oooWWwwwwwwwwwvvooo....
..ooWWwwnnnnnnnnnnnvvvvoo..
.oWWwnnnNNNNNNNNNNNnnvvvvo.
oWwnnNNNnnnnnnnnnnNNNnnvvo.
oWnnNnnnnnnnnnnnnnnnNnnnvo.
onnNnnnoKKKKKKKKKoonnNnnvo.
.onnnnoKkkkjkkkjkkKonnnno..
..ooooKkkkkkkkkkkkkKoooo...
....oKkjksEEsssEEskKkKo....
....oKkjkseesssseskKkKo....
....oKkjkbsssssssbkKkKo....
....oKkjkzsssZssszkKkKo....
....oKkjkozssssszokKkKo....
....oKkWwKoooooooKwvkKo....
....oKkrrKKo...oKKrdkKo....
....oKokko.......oKKoKo....
.....o.oo.........oo.o.....
''', z=8)

F_ARM_L_UP = B_ARM_L_UP
F_ARM_R_UP = B_ARM_R_UP
F_ARM_L_OUT = B_ARM_L_UP_HALF
F_ARM_R_OUT = B_ARM_R_UP_HALF


def release(view, load):
    """Fling both arms out (3 frames: gather, fling, hold)."""
    out = []
    if view == 'front':
        seq = [(at(F_ARM_L_CHEST, 0, 1), at(F_ARM_R_CHEST, 0, 1), 1, 'blink'),
               (at(F_ARM_L_OUT, 0, -1), at(F_ARM_R_OUT, 0, -1), -1, 'open'),
               (at(F_ARM_L_OUT, 0, 0), at(F_ARM_R_OUT, 0, 0), 0, 'open')]
        for al, ar, dy, face in seq:
            ly = _front(load, dy, face, arm_l=None, arm_r=None)
            ly = [i for i in ly if not (i is not None and i[0] in (F_ARM_L, F_ARM_R))] + [al, ar]
            out.append(Frame(ly, _anchors(view, load, dy, (13, 22 + dy))))
    elif view == 'side':
        seq = [(at(S_ARM_CHEST, 0, 1), 1, 'blink', False), (at(S_ARM_UP_HALF, 0, -1), -1, 'open', True), (at(S_ARM_UP_HALF, 0, 0), 0, 'open', True)]
        for arm, dy, face, over in seq:
            ly = _side(load, dy, face, arm_over=arm) if over else _side(load, dy, face, arm)
            out.append(Frame(ly, _anchors(view, load, dy, (20, 11 + dy))))
    else:
        seq = [(at(B_ARM_L, 1, 1), at(B_ARM_R, -1, 1), 1), (at(B_ARM_L_UP_HALF, 0, -1), at(B_ARM_R_UP_HALF, 0, -1), -1),
               (at(B_ARM_L_UP_HALF, 0, 0), at(B_ARM_R_UP_HALF, 0, 0), 0)]
        for al, ar, dy in seq:
            out.append(Frame(_back_top(load, dy, arm_l=al, arm_r=ar), _anchors(view, load, dy, (13, 22 + dy))))
    return out


def hurt(view, load):
    """Flinch: knocked back a pixel, eyes squeezed, arms up; then recover (2 frames)."""
    out = []
    for i, (dx, dy) in enumerate([(-1, 1), (0, 0)]):
        if view == 'front':
            ly = _front(load, dy, 'strain' if i == 0 else 'blink', arm_l=at(F_ARM_L_CHEST, 0, dy), arm_r=at(F_ARM_R_CHEST, 0, dy))
        elif view == 'side':
            ly = _side(load, dy, 'strain' if i == 0 else 'blink', at(S_ARM_CHEST, 0, dy))
        else:
            ly = _back(load, dy, arm_l=at(B_ARM_L, 1, dy), arm_r=at(B_ARM_R, -1, dy))
        # knock the whole upper body back (toward screen-left in the side view)
        ly = [(l, x + (dx if l not in (F_LEG_L, F_LEG_R, B_LEG_L, B_LEG_R) and l not in S_LEGS.values() else 0), y)
              if l is not None else None for l, x, y in [j if j is not None else (None, 0, 0) for j in ly]]
        out.append(Frame(ly, _anchors(view, load, dy)))
    return out


def look_up(view, load):
    """Tips her head back to look up (cutscenes): 2 breathing frames."""
    out = []
    for i, dy in enumerate([0, 1]):
        if view == 'front':
            ly = _front(load, dy, 'open')
            ly = [j for j in ly if not (j is not None and (j[0] is F_HEAD or j[0] in F_FACE.values()))]
            ly.append(at(F_HEAD_UP, 0, dy))
        elif view == 'side':
            head = shear_v(S_HEAD, -0.22, 13)
            ly = _side(load, dy, None, head_dy=dy)
            ly = [(head, 1, dy) if (j is not None and j[0] is S_HEAD) else j for j in ly]
        else:
            ly = _back(load, dy, head_dy=dy + 1)
        out.append(Frame(ly, _anchors(view, load, dy)))
    return out


def lift(view, load):
    """Lift something overhead: crouch and grab, bring it up, hold it high (3 frames)."""
    out = []
    if view == 'front':
        seq = [('crouch', at(F_ARM_L_BEAM, 0, 3), at(F_ARM_R_BEAM, 0, 3), 3, (13, 30)),
               ('stand', at(F_ARM_L_CHEST, 0, 0), at(F_ARM_R_CHEST, 0, 0), 0, (13, 22)),
               ('stand', at(F_ARM_L_UP, 0, 0), at(F_ARM_R_UP, 0, 0), 0, (13, -2))]
        for legs, al, ar, dy, hand in seq:
            ly = _front(load, dy, 'strain' if legs == 'crouch' else 'open', skirt=(0, min(dy, 2)))
            if legs == 'crouch':
                ly = [(F_LEG_L_CROUCH, 0, 0) if (j is not None and j[0] is F_LEG_L) else (F_LEG_R_CROUCH, 0, 0) if (j is not None and j[0] is F_LEG_R) else j for j in ly]
            ly = [j for j in ly if not (j is not None and j[0] in (F_ARM_L, F_ARM_R))] + [al, ar]
            out.append(Frame(ly, _anchors(view, load, dy, hand)))
    elif view == 'side':
        seq = [('crouch', at(S_ARM_BEAM, 0, 3), 3, (22, 27), False), ('stand', at(S_ARM_CHEST, 0, 0), 0, (18, 22), False),
               ('stand', at(S_ARM_UP, 0, 0), 0, (16, 1), True)]
        for legs, arm, dy, hand, over in seq:
            if legs == 'crouch':
                ly = [at(S_HAIR, 0, dy), at(S_LOAD, 0, dy) if load else None, at(S_LEGS['crouch']), at(S_SKIRT_CROUCH),
                      at(S_TORSO, 0, dy), arm, at(S_STRAP, 0, dy) if load else None, at(S_HEAD, 0, dy), at(S_FACE['strain'], 0, dy)]
            else:
                ly = _side(load, dy, 'open', arm_over=arm) if over else _side(load, dy, 'open', arm)
            out.append(Frame(ly, _anchors(view, load, dy, hand)))
    else:
        seq = [(at(B_ARM_L, 1, 2), at(B_ARM_R, -1, 2), 2, (13, 30)), (at(B_ARM_L_UP_HALF, 0, 0), at(B_ARM_R_UP_HALF, 0, 0), 0, (13, 10)),
               (at(B_ARM_L_UP, 0, 0), at(B_ARM_R_UP, 0, 0), 0, (13, -2))]
        for al, ar, dy, hand in seq:
            out.append(Frame(_back_top(load, dy, arm_l=al, arm_r=ar, skirt=(0, min(dy, 1))), _anchors(view, load, dy, hand)))
    return out


def carry_overhead(view, load):
    """Walk with something held overhead (6 frames; the object is a prop at 'hand')."""
    out = []
    for i, dy in enumerate(WALK_BOB):
        if view == 'front':
            ly = _front(load, dy, 'open', legs=WALK_FRONT_LEGS[i], sash=i % 3 == 2)
            ly = [j for j in ly if not (j is not None and j[0] in (F_ARM_L, F_ARM_R))] + [at(F_ARM_L_UP, 0, dy), at(F_ARM_R_UP, 0, dy)]
            hand = (13, -2 + dy)
        elif view == 'side':
            ly = _side(load, dy, 'open', legs=WALK_SIDE_LEGS[i], hair=i % 3 != 0, arm_over=at(S_ARM_UP, 0, dy))
            hand = (16, 1 + dy)
        else:
            ly = _back_top(load, dy, arm_l=at(B_ARM_L_UP, 0, dy), arm_r=at(B_ARM_R_UP, 0, dy), legs=WALK_FRONT_LEGS[i])
            hand = (13, -2 + dy)
        out.append(Frame(ly, _anchors(view, load, dy, hand)))
    return out


# =============================================================================================
# Sheet description for tools/art/build.py

NAME = 'tsuzumi'
FRAME = (FW, FH)
ORIGIN = (MX, MY)

F, S, B = 'front', 'side', 'back'

# name: (recipe, views, fps, loop, sheets)
ANIMS = {
    'idle':       (idle,       (F, S, B), 4,   True,  ('load', 'plain')),
    'walk':       (walk,       (F, S, B), 10,  True,  ('load', 'plain')),
    'heavyIdle':  (heavy_idle, (F, S, B), 3,   True,  ('load', 'plain')),
    'take':       (take,       (F, S),    8,   False, ('load', 'plain')),
    'give':       (give,       (F, S),    8,   False, ('load', 'plain')),
    'push':       (push,       (S,),      8,   False, ('load', 'plain')),
    'reachUp':    (reach_up,   (S, B),    6,   False, ('load', 'plain')),
    'eat':        (eat,        (F, S),    4,   False, ('load', 'plain')),
    'bow':        (bow,        (F, S, B), 5,   False, ('load', 'plain')),
    'climb':      (climb,      (B,),      6,   True,  ('load', 'plain')),
    'shout':      (shout,      (B,),      6,   False, ('load', 'plain')),
    'sitBranch':  (sit_branch, (B,),      3,   True,  ('load', 'plain')),
    'shoulder':   (shoulder,   (F, S),    5,   False, ('load',)),
    'strain':     (strain,     (F, S),    8,   True,  ('plain',)),
    'asleep':     (asleep,     (S,),      1.5, True,  ('plain',)),
    'sitUp':      (sit_up,     (S,),      4,   False, ('plain',)),
    'sit':        (sit,        (S,),      3,   True,  ('plain',)),
    'release':    (release,        (F, S, B), 8, False, ('load', 'plain')),
    'hurt':       (hurt,           (F, S, B), 6, False, ('load', 'plain')),
    'lookUp':     (look_up,        (F, S, B), 2, True,  ('load', 'plain')),
    'lift':       (lift,           (F, S, B), 5, False, ('load', 'plain')),
    'carryOverhead': (carry_overhead, (F, S, B), 9, True, ('load', 'plain')),
}

SHEETS = {'load': True, 'plain': False}   # sheet name -> draw the back-frame load
