"""Tsuzumi, action parts (revision 2): arms in the new sleeve style, heads for bow and look-up,
the side bow with its leaning load, lying and sitting poses.

Every sleeve keeps the same language as the walk: a wide pouch hanging from the forearm, a fold,
the indigo lining at the cuff, and the hand coming out of it.
"""

from __future__ import annotations

from rig import L

# =============================================================================================
# FRONT arms. F_*_L is her right arm (viewer's left, lit side); F_*_R her left arm.

F_CHEST_L = L(16, '''
.....ooo.....
....oWWWo....
...oWWwwo....
...oWwwwo....
..oWWwvwo....
..oWwwvwwoo..
..oWwwvwwwiso
.oWWwwvwwwnzo
.oWwwwvwwvooo
.oWwwvwwvVo..
oWWwwvwwvVo..
oWwwvwwvVo...
oWwwvwvVo....
oiiinnNo.....
.ooooooo.....
''', col=0, z=6.5)

F_CHEST_R = L(16, '''
.....ooo.....
....owwwo....
....ovwwvo...
....owwwvo...
....owwvwvo..
..oowwvwwvo..
.osiwwwvwwvo.
.oznwwwvwwvvo
..oowvwwvwwvo
....oVvwwvwwvo
....oVvwwvwwvo
.....oVvwwvwwvo
......oVvwvwvo
.......oNnnnno
........oooooo
''', col=12, z=6.5)

F_OFFER_L = L(16, '''
.....ooo.....
....oWWWo....
...oWWwwo....
...oWwwwo....
..oWWwvwo....
..oWwwvwwo...
..oWwwvwwwo..
.oWWwwvwwwoo.
.oWwwwvwwwino
.oWwwvwwwvnso
oWWwwvwwvVozo
oWwwvwwvVo.o.
oWwwvwvVo....
oiiinnNo.....
.ooooooo.....
''', col=0, z=6.5)

F_OFFER_R = L(16, '''
.....ooo.....
....owwwo....
....ovwwvo...
....owwwvo...
....owwvwvo..
...owwvwwvo..
..owwwvwwvo..
.oowwwvwwvvo.
onivwwwvwwvo.
osnvwwvwwvvo.
ozoVvwwvwwvo.
.o.oVvwwvwwvo
....oVvwvwvvo
.....oNnnnnno
......ooooooo
''', col=13, z=6.5)

F_REACH_L = L(16, '''
.....ooo..
....oWWWo.
...oWWwwo.
...oWwwwo.
..oWWwvwo.
..oWwwvwo.
.oWWwwvwo.
.oWwwwvwo.
oWWwwvwwo.
oWwwvwwwo.
oWwwvwwvo.
oWwvwwvVo.
oiinnnNo..
onnnNNo...
oszooo....
oso.......
.o........
''', col=-1, z=6.5)

F_MOUTH_L = L(9, '''
..oo.oo.oo....
.oFFoDDoffo...
.oFFoDDoffooo.
..oo.oo.oozso.
.........ozzo.
........oszo..
........oszo..
.......oino...
......oWnno...
....ooWwvVo...
...oWWWwvVo...
..oWWwwvvVo...
..oWwwwvVo....
.oWWwwvvVo....
.oWwwwvVo.....
.oWwwvvVo.....
oWWwwvVo......
oWwwvVVo......
oWwvvVo.......
oiinNNo.......
.ooooo........
''', col=0, z=8.6)

F_BEAM_L = L(16, '''
.....ooo....
....oWWWo...
...oWWwwo...
...oWwwwo...
..oWWwvwo...
..oWwwvwwo..
..oWwwvwwo..
.oWWwwvwwo..
.oWwwwvwwwo.
.oWwwvwwwwoo
oWWwwvwwwvio
oWwwvwwwvVso
oWwwvwwvVozo
oiinnnNNo.o.
.oooooooo...
''', col=0, z=6.5)

F_BEAM_R = L(16, '''
....ooo.....
...owwwo....
...ovwwvo...
...owwwvo...
...owwvwvo..
..owwvwwvo..
..owwvwwvo..
..owwvwwvvo.
.owwwvwwwvo.
oowwwvwwvvo.
oiwwwvwwvvvo
osVwwvwwvvvo
ozoVwvwwvvvo
.o.oNnnnnNNo
....oooooooo
''', col=14, z=6.5)

# Both arms raised overhead (lift, carry overhead): sleeves fall back to the shoulders.
F_UP_L = L(-1, '''
....oo.
...osso
...oszo
...oszo
...oszo
...oszo
...oszo
...oszo
...oszo
...oszo
..oiino
.oWWnno
oWWwwvo
oWwwwvo
oWwwvvo
oWwwvvo
oWwvvVo
.oWvvVo
.oWwvVo
..oWvVo
..oiNNo
...ooo.
''', col=3, z=11)

F_UP_R = L(-1, '''
.oo....
osso...
ozso...
ozso...
ozso...
ozso...
ozso...
ozso...
ozso...
ozso...
onio...
onnWo..
ovwwwo.
ovwwwvo
oVvwwvo
oVvwwvo
oVVvwvo
oVVvwo.
oVvwwo.
oVVwo..
oNNio..
.ooo...
''', col=18, z=11)

# Arms flung out (release): forearms bare, sleeves swinging under the arms.
F_OUT_L = L(9, '''
oo........
osoo......
ozssoo....
.oozzsoo..
...ooiino.
....oWnno.
...oWwwvo.
..oWWwwvo.
..oWwwvVo.
.oWWwvvVo.
.oWwvvVo..
oWwwvVo...
oWwvVo....
oiinNo....
.oooo.....
''', col=-2, z=11)

F_OUT_R = L(9, '''
........oo
......ooso
....oosszo
..ooszzoo.
.oiino....
.onnWo....
.ovwwwo...
.ovwwWWo..
.oVvwwwo..
.oVvvwWWo.
..oVvvwwo.
...oVvwwWo
....oVvwwo
....oNnnio
.....oooo.
''', col=19, z=11)

# =============================================================================================
# SIDE arms (near arm, facing right). Shoulder ~ (11, 17).

S_FWD = L(16, '''
..ooo.............
.oWWWoooooooo.....
oWWWWWWWWwwiooo...
oWwwwwwwwwvnsso...
oWwwwwwwwvvNozo...
oWwwwwwwvvVo.o....
.oWwwwwvvVo.......
.oWwwwwvVo........
..owwwvVo.........
...ooooo..........
''', col=8, z=6.5)

S_CHEST = L(16, '''
..ooo.......
.oWWWo......
oWWWwwo.....
oWwwwwo.....
oWwwwvwo....
oWwwwvwwoo..
oWwwvwwwiso.
oWwwvwwvnzo.
oWwvwwvVoo..
oWwvwvVo....
.oWvwvVo....
.oWwvVo.....
..owvVo.....
...ooo......
''', col=8, z=6.5)

S_OFFER = L(16, '''
..ooo..........
.oWWWo.........
oWWWwwo........
oWwwwwwo.......
oWwwwwwwoo.....
oWwwwwwwwwoo...
oWwwwwwwwwvioo.
oWwwwwwwwvvnsso
.oWwwwwwvvVozzo
.oWwwwwvvVo.oo.
..oWwwvVoo.....
...ooooo.......
''', col=8, z=6.5)

S_UP_HALF = L(9, '''
............oo.
...........osso
..........oszo.
.........oszo..
........oszo...
.......oiio....
..ooo.oWnno....
.oWWWoWwvNo....
oWWWwwWwvVo....
oWwwwwwwvVo....
oWwwwwwvVo.....
oWwwwwvvVo.....
oWwwwvvVo......
oWwwvvVo.......
.oWwvVo........
.oWvVo.........
..ooo..........
''', col=8, z=9)

S_UP = L(-3, '''
.....oo.
....osso
....oszo
....oszo
....oszo
....oszo
....oszo
....oszo
....oszo
....oszo
....oszo
....oszo
....oino
...oWnno
..oWwvNo
.oWwwvVo
oWWwwvVo
oWwwvvVo
oWwwvVo.
oWwvvVo.
oWwvVo..
oWvvVo..
.oWvVo..
.oWVo...
..oo....
''', col=9, z=9)

S_MOUTH = L(9, '''
...........oo..
..........oDDo.
..........oDFo.
..........oFFo.
..........offo.
..........ofDo.
...........osso
..........oszo.
..ooo....oszo..
.oWWWo..oino...
oWWWwwooWnno...
oWwwwwwWwvVo...
oWwwwwwwvVo....
oWwwwwwvVo.....
oWwwwwvvVo.....
oWwwvvvVo......
oWwvvVVo.......
.oWvVVo........
..oooo.........
''', col=8, z=9)

S_BEAM = L(16, '''
..ooo..........
.oWWWo.........
oWWWwwo........
oWwwwwwo.......
oWwwwwwwoo.....
oWwwwwwwwwoo...
.oWwwwwwwwvioo.
..oWwwwwwvvnsso
...oWwwwvvVozzo
....owwvvVo.oo.
.....ooooo.....
''', col=8, z=6.5)

S_GRIP = L(16, '''
..ooo.ooo.
.oWWWoszo.
oWWWwwszo.
oWwwwwioo.
oWwwwvno..
oWwwwvwo..
oWwwvwwvo.
oWwwvwwvo.
oWwvwwwvo.
oWwvwwvVo.
oWvwwwvVo.
.oWwwvvVo.
.oWwvvnNo.
..ooooooo.
''', col=8, z=6.5)

# Sleeve swing for the side walk: forward (the pouch trails back) and back.
S_SLEEVE_FWD = L(16, '''
..ooo.....
.oWWWo....
oWWWwwo...
oWwwwvo...
oWwwwvwo..
oWwwwvwwo.
oWwwvwwwvo
oWwwvwwwvo
.oWwvwwvVo
.oWwvwwvio
..oWvwwnso
..oWwvvozo
...oooo.o.
''', col=8, z=6)

S_SLEEVE_BACK = L(16, '''
..ooo....
.oWWWo...
oWWWwwo..
oWwwwvo..
oWwwwvo..
oWwwwvo..
oWwwvwvo.
oWwwvwvo.
oWwvwwvo.
oWwvwwvVo
oWvwwvvVo
oWvwwvVio
oWvvwvnso
.oooooozo
.......o.
''', col=7, z=6)

# =============================================================================================
# BACK arms. From behind, a raised or flung arm has the same silhouette as from the front.

B_UP_L = F_UP_L
B_UP_R = F_UP_R
B_UP_HALF_L = F_OUT_L
B_UP_HALF_R = F_OUT_R

B_SHOUT_R = L(11, '''
oo........
oszoo.....
.ozsso....
..ooiinoo.
...oWwwWWo
..oWwwwvVo
..owwwvvVo
...owvwvVo
...owvvVo.
....onNNo.
.....ooo..
''', col=16, z=11)

B_SHOUT_L = L(11, '''
........oo
.....ooszo
.....ossoo
..ooniio..
.oWWwwWo..
.oVvwwwWo.
.oVvvwwwo.
.oVvwvwo..
..oVvvwo..
..oNNno...
...ooo....
''', col=1, z=11)

# Sitting on a branch, seen from behind: the coat bunches at the seat, short calves dangle.
B_SIT_SKIRT = L(26, '''
..oWwwwwwwvvvo...
.oWWwwwwwwvvvVo..
oWWwwwwwwwwvvvVo.
ooooooooooooooooo
''', col=5, z=3)

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

# =============================================================================================
# Hats tipped toward or away from the camera.

# Bowing toward the camera: the crown faces us as a broad dish, the band running to the brim.
F_HAT_DISH = L(4, '''
.........ooooooooooooooo.........
.....ooooWWWWwwwwwwwwvvvoooo.....
...ooWWWWwwwwwwwwwwwwwwvvvvvoo...
..oWWWwwwwwwwwwwRwwwwwwwwvvvvvo..
.oWWWwwwwwwwwwwwRrwwwwwwwwvvvvvo.
oWWWwwwwwwwwwwwwoRrwwwwwwwwvvvvVo
oWWwwwwwwwwwwwwwwrRrwwwwwwwvvvvVo
.oWwwwwwwwwwwwwwwwrRrwwwwwvvvvVo.
..ooWwwwwwwwwwwwwwwwrRrwwvvvvoo..
....oooWwwwwwwwwwwwwwwrRrvvooo...
.......ooonnnnnnnnnnnnnnnooo.....
..........ooKKkkkkkkkKKoo........
............oooooooooooo.........
''', col=-3, z=8.5)

# Looking up: the hat tips back and its indigo underside opens up, as in the illustration.
F_HAT_UP = L(0, '''
.........ooooooooooooooo.........
.....ooooWWWWwwwwwwwwvvvoooo.....
...ooWWwwwnnnnnnnnnnnnnnwvvvoo...
..oWWwnnnNNNNNNNNNNNNNNNnnnvvvo..
.oWwnnNNNnnnnnnnnnnnnnnnNNNnnvvo.
oWwnNNnnnnnnnnnnnnnnnnnnnnnNNnvVo
onnNnnnnoKKKKKKKKKKKKKKKonnnNnnvo
.ooonnnoKkkkjkkkkkkjkkkkKonnnoo..
....ooKkkkkkkkkkkkkkkkkkkkKoo....
''', col=-3, z=8.5)

F_FACE_UP = L(9, '''
....oKkKkkKkkkkkKkkKkKo....
....oKkjksEEsssEEskKkKo....
....oKkjkseesssseskKkKo....
....oKkjkbsssZsssbkKkKo....
....oKkjkozssssszokKkKo....
....oKkWwKoooooooKwvkKo....
....oKkrrKKo...oKKrdkKo....
....oKokko.......oKKoKo....
.....o.oo.........oo.o.....
''', z=8)

# =============================================================================================
# Crouches (strain, lift, shouldering the frame)

F_LEG_CROUCH_L = L(33, '''
.oiiiiio.
oiiiiiino
.owWWvoo.
onnnnnno.
oNnnnnNo.
oooooooo.
''', col=4, z=2)

F_LEG_CROUCH_R = L(33, '''
.oinnnno.
oinnnnnNo
.oowvvo..
.onnnnnNo
.oNnnnnNo
.oooooooo
''', col=14, z=2)

S_CROUCH = L(29, '''
...oWwvviinnvVo.....
..oWwvvviinnnvVo....
..oWwvvoiinnnovVo...
.oooooooiiinnnoooo..
.oNnnnoooiiiinnnNo..
.oNnnnnnooiiiinnnNo.
..ovvvoo..owWWvooo..
..oNNNNo..onnnnnooo.
..oNNNNNo.oNnnnnnnNo
..oooooooooooooooooo
''', col=1, z=2)

# Lying on her back: the body that shows to the right of the hat (the hat covers head and chest).
ASLEEP_BODY = [L(30, '''
....................oo..
...................oNNo.
ooooooooooooooo....onno.
oWWWwwwwwwwwwwwooooowWo.
owwwwiiiwrRrdiiinnnnwWoo
owwwiiiiiwdrdiiinnnnownNo
ovvvviiiiiiiiinnnnnNooNNo
oVVvvvvvvvvvvvvoooooooooo
ooooooooooooooo.........
''', col=13, z=4), L(30, '''
....................oo..
...................oNNo.
...................onno.
oooooooooooooooooooowWo.
oWWWwwwiiiwrRrdiinnnwWoo
owwwiiiiiiwdrdiiinnnownNo
ovvvviiiiiiiiinnnnnNooNNo
oVVvvvvvvvvvvvvoooooooooo
ooooooooooooooo.........
''', col=13, z=4)]

# Sitting on the ground facing right, legs out along the ground.
S_SIT_LEGS = L(33, '''
.oWWwwwwwwwwwwvo..oo.
oWwwwiiiinnnnnnoonNo.
oWwwiiiinnnnnnnnoNno.
oWwvvinnnnnnnnnNowWo.
.oooooooooooooooonnoo
.................ooo.
''', col=4, z=3)
