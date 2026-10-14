"""Tsuzumi, base parts (revision 2): palette, the hat, heads, torsos, sleeves, lower bodies, hair.

Model space: 27 columns with her centre line at column 13 (parts may use negative columns: the hat
is 33 px wide, columns -3..29); row 38 is the outline under her soles. See tsuzumi.py.
"""

from __future__ import annotations

from pixart import Palette
from rig import L

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
    # back-frame wood, wicker box, straw rope
    'G': ('#b58c5f', 'wood', 1), 'g': ('#8b6443', 'wood', 0), 'u': ('#5e4130', 'wood', -1),
    'T': ('#e1c084', 'wicker', 1), 't': ('#bf9558', 'wicker', 0), 'p': ('#8f6a3c', 'wicker', -1), 'P': ('#644728', 'wicker', -2),
    # dango
    'D': ('#f3d9df', 'food', 1), 'f': ('#9bc46a', 'food', 0), 'F': ('#e6a1b4', 'food', 0),
}, outlines={
    # five line colours: cool near-black (hair, indigo, eyes), soft violet on white cloth and straw,
    # deep red on red cloth, warm brown on skin, dark brown on the wooden frame and wicker
    'hair': '#16122a', 'indigo': '#16122a', 'eye': '#16122a', 'white': '#3b3150',
    'red': '#3e1424', 'food': '#3e1424', 'skin': '#6a3438', 'wood': '#2f1e12', 'wicker': '#2f1e12',
}, default_outline='#16122a', bevel={'hair': 0.7, 'white': 1.0, 'indigo': 0.9, 'skin': 1.1, 'wicker': 0.8, 'wood': 0.6})


# =============================================================================================
# The hat: one template for every view (a sugegasa is round, so it has the same outline from any
# side at this camera pitch); only the red band moves. 33 px brim, a flat cone, the brim tips droop
# and show their indigo underside, and a 1 px indigo underside line runs along the front edge.

_HAT = [
    '...............ooo...............',
    '............ooo...ooo............',
    '.........ooo.........ooo.........',
    '.......oo...............oo.......',
    '....ooo...................ooo....',
    '..oo.........................oo..',
    'oo' + '.' * 29 + 'oo',
    'onn' + '.' * 27 + 'nno',
    '.oo' + 'n' * 27 + 'oo.',
    '...' + 'o' * 27 + '...',
]


def _hat_grid(band='right'):
    """Fill the hat outline: lit left slope, shaded right slope, straw ribs, the red band."""
    rows = [list(r) for r in _HAT]
    for y in range(1, 8):
        row = rows[y]
        idx = [x for x, c in enumerate(row) if c == 'o']
        if y == 7:
            left, right = 3, 29
        else:
            left = idx[0]
            while row[left] == 'o':
                left += 1
            right = idx[-1]
            while row[right] == 'o':
                right -= 1
        for x in range(left, right + 1):
            if row[x] != '.':
                continue
            t = (x - left) / max(1, right - left)
            if y == 7:
                c = 'w' if t < 0.72 else 'v'
            elif t < 0.16:
                c = 'W'
            elif t < 0.62:
                c = 'w'
            elif t < 0.93:
                c = 'v'
            else:
                c = 'V'
            row[x] = c
    # straw ribs: two faint radial lines on the lit half
    for (x, y) in [(13, 3), (11, 4), (9, 5), (7, 6), (15, 4), (14, 5), (13, 6), (12, 7)]:
        if rows[y][x] == 'w':
            rows[y][x] = 'v'
    # the red band from the crown down to the brim
    path_r = [(17, 1), (17, 2), (18, 2), (18, 3), (19, 3), (20, 4), (21, 4), (21, 5), (22, 5), (23, 6), (24, 6), (25, 7), (26, 7)]
    path = path_r if band == 'right' else [(32 - x, y) for x, y in path_r]
    for x, y in path:
        if rows[y][x] not in '.o':
            rows[y][x] = 'R' if (y <= 2) else 'r'
    for x, y in path:   # a darker lower edge on the band where it meets the shaded slope
        yy = y + 1
        if yy <= 7 and rows[yy][x] in 'wv' and (x, yy) not in path:
            rows[yy][x] = 'd' if band == 'right' and x > 18 else rows[yy][x]
    return [''.join(r) for r in rows]


def hat(band='right', row=0, z=8.5):
    return L(row, '\n'.join(_hat_grid(band)), col=-3, z=z)


HAT_F = hat('right')
HAT_S = hat('left')
HAT_B = hat('right')

# =============================================================================================
# FRONT

F_FACE_ROWS = L(10, '''
....oKkKKkKKkKKkKKkKkKo....
....oKkjksEEsssEEskKkKo....
....oKkjksEessseEskKkKo....
....oKkjkbsssZsssbkKkKo....
....oKkjkozssssszokKkKo....
....oKkWwKoooooooKwvkKo....
....oKkrrKKo...oKKrdkKo....
....oKokko.......oKKoKo....
.....o.oo.........oo.o.....
''', z=8)

F_FACE = {
    'open': None,
    'blink': L(11, '''
s..sss..s
sEEsssEEs
''', col=9, z=8.1),
    'happy': L(11, '''
sEssssEss
EsEsssEsE
''', col=8, z=8.1),
    'chew': L(13, '''
sZZs
''', col=12, z=8.1),
    'open_mouth': L(13, '''
sZs
''', col=12, z=8.1),
    'strain': L(11, '''
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

# Straw-rope shoulder straps of the back-frame (pasted only onto cloth pixels).
F_STRAPS = L(17, '''
.T.......T.
.Tp.....tp.
..Tp...tp..
..tp...tp..
..tp...tp..
''', col=8, z=5.5, only='Wwvirn')

# Sleeves: trapezoids flaring from the shoulder to mid-thigh, one fold, indigo lining at the opening.
F_SLEEVE_L = L(16, '''
.....ooo..
....oWWWo.
...oWWwwo.
...oWwwwo.
..oWWwvwo.
..oWwwvwo.
..oWwwvwo.
.oWWwwvwo.
.oWwwvwwo.
.oWwwvwwo.
oWWwwvwwo.
oWwwvwwwo.
oWwwvwwwo.
oiiinnnno.
onnnnNzso.
.oooooooo.
''', col=0, z=6)

F_SLEEVE_R = L(16, '''
..ooo.....
.owwwo....
.owwvvo...
.owwwvo...
.owwwvvo..
.owvwwvo..
.owvwwvo..
.owvwwvvo.
.owwvwwvo.
.owwvwwvo.
.owwvwwvvo
.owwwvwwvo
.owwwvwwvo
.onnnnNNNo
.oszNNNNNo
..ooooooo.
''', col=17, z=6)

F_SKIRT = L(25, '''
..oWwiinnnwvo..
..oWwiinnnwvo..
..oWwiinnnwvo..
..oWwiinnnwvo..
..oWwwinnwvvo..
.oWwwviinvvvVo.
''', col=6, z=3)

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

# Lower body, front: the coat hem (sways with the stride) over two poseable legs. Each leg is the
# baggy trouser below the hem, the white wrap and the boot; 'long' is the forward leg (fuller,
# reaches a pixel lower), 'tuck' the trailing leg with its heel up.
F_HEM = {
    'c': L(31, '''
..oWwvviinnvvVo..
.oWwvvoinnnovVVo.
.oooooiiinnnooooo
''', col=4, z=3),
    'l': L(31, '''
..oWwvviinnvvVo..
.oWwvvoiinnovVVo.
ooooooiiinnnoooo.
''', col=4, z=3),
    'r': L(31, '''
..oWwvviinnvvVo..
.oWwvvoinnnnvVVo.
.ooooiiinnnoooooo
''', col=4, z=3),
}

F_LEG_L = {
    'plant': L(33, '''
.oiiiiio.
.oiiiiino
..owWWvo.
.onnnnno.
.oNnnnNo.
.ooooooo.
''', col=5, z=2),
    'long': L(33, '''
.oiiiiio.
oiiiiiino
.oiiiiino
..owWWvo.
.onnnnno.
.oNnnnNo.
.ooooooo.
''', col=5, z=2),
    'tuck': L(33, '''
..oiiio..
..oiiino.
..owWvo..
..onnno..
..ooooo..
''', col=5, z=2),
}

F_LEG_R = {
    'plant': L(33, '''
.oinnnno.
oinnnnNo.
.owvvo...
.onnnnNo.
.oNnnnNo.
.oooooooo
''', col=13, z=2),
    'long': L(33, '''
.oinnnno.
oinnnnnNo
.oinnnnNo
..owvvo..
.onnnnnNo
.oNnnnnNo
.ooooooo.
''', col=13, z=2),
    'tuck': L(33, '''
..oinno..
.oinnnNo.
..owvvo..
..onnNo..
..ooooo..
''', col=13, z=2),
}

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

# =============================================================================================
# SIDE (facing right)

S_FACE_ROWS = L(10, '''
....oKKKKKKKKKKKKKKko......
....oKkkjkkkkkKkkjkKo......
....oKkkkjkkKjkssEEso......
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
    'blink': L(12, '''
sss
EEs
''', col=17, z=8.1),
    'happy': L(12, '''
sEs
Ess
''', col=17, z=8.1),
    'chew': L(15, '''
ZZ
''', col=18, z=8.1),
    'open_mouth': L(15, '''
ZZ
''', col=18, z=8.1),
    'strain': L(12, '''
EsE
sEs
''', col=16, z=8.1),
}

S_HAIR = [L(19, '''
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
''', col=1, z=2), L(19, '''
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
''', col=1, z=2), L(19, '''
...oKkkkkkKo
...oKkkjkkKo
...oKkkjkKo.
...oKkjkkKo.
..oKkkjkKo..
..oKkjkKKo..
..oKkjkKo...
..oKkkKo....
..oKkKo.....
..oKKo......
...o........
''', col=1, z=2)]

S_TORSO = L(16, '''
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

S_STRAP = L(16, '''
.T....
.Tp...
..tp..
..tp..
..tp..
...p..
''', col=8, z=6.5, only='WwvirnR')

S_SLEEVE = [L(16, '''
..ooo....
.oWWWo...
oWWWwwo..
oWwwwvo..
oWwwwvo..
oWwwwvwo.
oWwwvwwvo
oWwwvwwvo
oWwvwwwvo
oWwvwwvVo
oWvwwwvVo
oWvwwvvVo
.oWwwvinso
.oWwvvnozo
..ooooo.o.
''', col=8, z=6)]

S_SKIRT = L(25, '''
..oWwiiinvo...
..oWwiiinvo...
..oWwiiinvo...
..oWwiiinvvo..
..oWwwiinvvo..
.oWwwviinvvo..
''', col=6, z=3)

S_LOWER = {
    'stand': L(31, '''
..oWwvviinnvVo..
..oWwvoinnovVo..
..ooooiiinnoooo.
....oiiinnnNo...
....owWWvoo.....
....onnnnnooo...
....oNnnnnnnNo..
....oooooooooo..
''', col=4, z=2),
}

# =============================================================================================
# BACK

B_HAIR_ROWS = L(10, '''
.....oKkkjkkkkjkkkKo.......
.....oKkjkkkkjkkkjKo.......
.....oKkjkkkjkkkkjKo.......
.....oKkjkkkjkkkkjKo.......
.....oKkjkkkjkkkkkKo.......
.....oKkjkkkjkkkkkKo.......
.....oKkjkkkjkkkkKKo.......
''', z=8)

B_HAIR = [L(17, '''
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
''', col=5, z=9), L(17, '''
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
''', col=5, z=9), L(17, '''
.oKkkkkjkkkkkKKo.
.oKkkkkjkkkkkKKo.
.oKkjkkjkkkjkKo..
.oKkjkkkkkkjkKo..
.oKkjkkkkkkjkKo..
.oKkjkkkkkkkKKo..
oKkkjkkkkkkKKo...
oKkkjkkkkkKKo....
ooKKkkkkkkKKo....
.ooKKkkkkKKoo....
...ooKKKKoo......
.....oooo........
''', col=5, z=9)]

B_TORSO = L(16, '''
..oooooooo..
.oWwwwwwwvo.
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

B_SLEEVE_L = L(16, '''
.....ooo..
....oWWWo.
...oWWwwo.
...oWwwwo.
..oWWwvwo.
..oWwwvwo.
..oWwwvwo.
.oWWwwvwo.
.oWwwvwwo.
.oWwwvwwo.
oWWwwvwwo.
oWwwvwwwo.
oWwwvwwwo.
oiiinnnno.
onnnnNzso.
.oooooooo.
''', col=0, z=6)

B_SLEEVE_R = L(16, '''
..ooo.....
.owwwo....
.owwvvo...
.owwwvo...
.owwwvvo..
.owvwwvo..
.owvwwvo..
.owvwwvvo.
.owwvwwvo.
.owwvwwvo.
.owwvwwvvo
.owwwvwwvo
.owwwvwwvo
.onnnnNNNo
.oszNNNNNo
..ooooooo.
''', col=17, z=6)

B_SKIRT = L(26, '''
.oWwwwwwwvvvo..
.oWwwwwwwvvvo..
.oWwwwwwwvvvo..
.oWwwwwwwvvvVo.
.oWwwvwwvvvvVo.
''', col=6, z=3)

B_SASH = L(28, '''
.o.
odo
odo
ordo
.odo
.oo.
''', col=4, z=7)

# Back hem variants (the haori's back is closed; the legs below reuse the front leg parts).
B_HEM = {
    'c': L(31, '''
..oWwwvwwvvvvVo..
.oWwwwvwwvvvvVVo.
.ooooooooooooooo.
''', col=4, z=3),
    'l': L(31, '''
..oWwwvwwvvvvVo..
.oWwwwvwwvvvvVVo.
oooooooooooooooo.
''', col=4, z=3),
    'r': L(31, '''
..oWwwvwwvvvvVo..
.oWwwwvwwvvvvVVo.
.oooooooooooooooo
''', col=4, z=3),
}

# Side walk, one lower body per frame (rows 30-38). A = near leg (lit), B = far leg (darker).
# 0 contact A fwd, 1 down, 2 passing, 3 up, 4 contact B fwd, 5 down, 6 passing, 7 up.
S_WALK = [L(29, '''
...oWwvviinnvVo.....
..oWwvvviinnnvVo....
..oWwvvoiinnnovVo...
..oooooiiiinnnoooo..
...oNnnnoooiiinnNo..
..oNnnoo..oiiinnNo..
..ovvo....owWWvoo...
.oNNo....onnnnnooo..
.ooo.....oNnnnnnnNo.
.........oooooooooo.
''', col=2, z=2), L(29, '''
...oWwvviinnvVo.....
...oWwvviinnnvVo....
..oWwvvoiinnnovVo...
..ooooooiiinnnooo...
...ooNnnoiiinnNo....
..oNnnooooiinnNo....
.oNvvo...owWWvo.....
.oNNo...onnnnnooo...
..oo....oNnnnnnnNo..
........oooooooooo..
''', col=2, z=2), L(29, '''
...oWwvviinnvVo.....
...oWwvviinnvVo.....
...oWwvoiinnovVo....
...ooooiiinnnoooo...
.....oiiinnNNo......
.....oiinnNnno......
.....owWWvovvo......
.....onnnnnNNoo.....
.....oNnnnnnnoNo....
.....oooooooooo.....
''', col=2, z=2), L(29, '''
...oWwvviinnvVo.....
...oWwvviinnnvVo....
...oWwvoiinnnovVo...
...ooooiiinnnNnooo..
.....oiiinoonnNNo...
.....oiinno.oNnnNo..
....owWWvo..ovvoo...
...onnnnoo..oNNNoo..
...oNnnnnNo.oooooo..
...oooooooo.........
''', col=2, z=2), L(29, '''
...oWwvviinnvVo.....
..oWwvvviinnnvVo....
..oWwvvoiinnnovVo...
..oooooiiiinnnoooo..
...oiiinoooNNnnNo...
..oiinoo..oNnnnNo...
..owWo....ovvvoo....
.onnno...oNNNNNoo...
.oooo....oNNNNNNNo..
.........ooooooooo..
''', col=2, z=2), L(29, '''
...oWwvviinnvVo.....
...oWwvviinnnvVo....
..oWwvvoiinnnovVo...
..ooooooiiinnnooo...
...ooiinnoNNnnNo....
..oiinnoooNnnNo.....
.owWWo...ovvvo......
.onnno..oNNNNNoo....
..ooo...oNNNNNNNo...
........ooooooooo...
''', col=2, z=2), L(29, '''
...oWwvviinnvVo.....
...oWwvviinnvVo.....
...oWwvoiinnovVo....
...ooooiiinnnoooo...
.....oiiinNNNo......
.....oiinoNnno......
.....owWWvvvo.......
.....onnnnNNNoo.....
.....oNnnnnNNNNo....
.....ooooooooooo....
''', col=2, z=2), L(29, '''
...oWwvviinnvVo.....
...oWwvviinnnvVo....
...oWwvoiinnnovVo...
...ooooiiinnnoooo...
.....oNNnoiiinNo....
.....oNnnooiinnNo...
....ovvvo..owWWvo...
...oNNNNo..onnnnoo..
...oNNNNNo.oNnnnNo..
...ooooooo.oooooo...
''', col=2, z=2)]

# =============================================================================================
# The back-frame (背負子): two posts against her back with three rails and a shelf; the wicker box
# sits on the shelf and leans on the frame. Post tips stand ~7 px above the brim; the top rail
# (row 7) is where Saji sits (anchor loadTop). A peg on her right post holds a lantern (hook).

B_FRAME = L(-4, '''
..oo..........oo...
.oGgo........oggo..
.oGgo........oggoo.
.oGgo........ogguuo
.oGgo........oggoo.
.oGgo........oggo..
.oGgo........oggo..
.oGgo........oggo..
.oGgo........oggo..
.oGgo........oggo..
.oGgooooooooooggo..
.oGgGGGGGgggggggo..
.oGgooooooooooggo..
.oGgo........oggo..
.oGgo........oggo..
.oGgo........oggo..
.oGgo........oggo..
.oGgo........oggo..
.oGgo........oggo..
.oGgooooooooooggo..
.oGgGGGgggggguggo..
.oGgooooooooooggo..
.oGgo........oggo..
.oGgo........oggo..
.oGgo........oggo..
.oGgo........oggo..
.oGgo........oggo..
.oGgo........oggo..
.oGgooooooooooggo..
oGGgGGGGgggggguugo.
oooooooooooooooooo.
.ouuo........ouuo..
..oo..........oo...
''', col=4, z=10)

B_BOX = L(8, '''
..ooooooooooo..
.oTTTTTTTTTTpo.
.otTttttttttPo.
.oPPPPPPPPPPPo.
.otTtpttWttptpo
.optttpWtpttPpo
.otptttWtttpPpo
.otTtptWtpttPpo
.oWWWWWWWWWWwwo
.optttpWtpttPpo
.otptttWtttpPpo
.otTtptWtpttPpo
.optttpWtpttPpo
.otptttWtttpPpo
.oPPPPPWPPPPPPo
..oooooooooooo.
''', col=6, z=11)

F_FRAME = L(-4, '''
..oo..........oo..
.oGgo........oggo.
ooGgo........oggo.
uuGgo........oggo.
ooGgo........oggo.
.oGgo........oggo.
''', col=4, z=0)

S_FRAME = L(-4, '''
.....oo.
....oGgo
...ooGgo
..ouuGgo
...ooGgo
....oGgo
....oGgo
....oGgo
....oGgo
....oGgo
...ooGgo
...ouGgo
...ooGgo
....oGgo
....oGgo
....oGgo
....oGgo
....oGgo
....oGgo
...ooGgo
...ouGgo
...ooGgo
....oGgo
....oGgo
....oGgo
....oGgo
....oGgo
....oGgo
oooooGgo
oGGGgGgo
oooooGgo
....ouuo
.....oo.
''', col=-1, z=1)

S_BOX = L(8, '''
.oooooooo.
oTTTTTTpo.
otTttttPo.
oPPPPPPPo.
otTtpWtpo.
optttWpPo.
otpttWtPo.
otTtpWtPo.
oWWWWWWwo.
optttWpPo.
otpttWtPo.
otTtpWtPo.
optttWpPo.
otpttWtPo.
oPPPPWPPo.
.ooooooo..
''', col=-4, z=0.5)

# Side strap: from the frame over her shoulder and down her chest (pasted onto cloth only).
S_STRAP = L(16, '''
.Tt...
.tTp..
..tp..
..tp..
..tp..
...p..
...p..
''', col=8, z=6.5, only='WwvirnR')
