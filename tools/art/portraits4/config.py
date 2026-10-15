"""Settings of the v4 dialogue portraits (docs/knowledge/13-pixel-portraits.md section 10).

v4 = the v1 route (every expression converted from its own illustration in the owner's 12 packs, so each keeps
its pose, hands, hair and tilt) at 128 x 128 for the 640 x 360 native canvas, with a sharper pixeliser and a
hand-edit pass on the faces (tears, brows, mouths) where the illustration's expression is too quiet to read.
"""

SIZE = 128                 # native px, square bust (640 x 360 canvas; was 80 at 480 x 270 in v1, 96 in v3)
SUB = 4                    # work supersampling
CARD = (78, 70, 86)        # the card colour behind the bust (dialogue_box.gd CARD_BG)

# Source px between the two eyes of each character's reference image (measured for v1; the packs keep one head
# size per character except the sitting poses 15-18).
REF_EYE_DIST = {'tsuzumi': 64.5, 'shione': 66.0, 'saji': 73.0}

# Framing per character: native px between the eyes, and where the eye midpoint sits in the window (fractions).
# Shione's face sits right of centre so her ponytail (the red cord at the nape and the hair below it) is in frame.
FRAME = {
    'tsuzumi': (28.5, 0.47, 0.44),
    'shione': (26.0, 0.61, 0.47),
    'saji': (28.5, 0.50, 0.47),
}

# expression: (source image, left eye, right eye, mouth centre (source px), mouth state[, options])
# mouth state: 'open' | 'small' | 'closed' | 'hidden' (a hand over the mouth).
# options: {'shift': (dx, dy)} moves the window by native px (composition only; the head moves with it).
# An eye hidden behind a hand is estimated from the visible one and the head's usual eye spacing.
SELECTION = {
    'tsuzumi': {
        'neutral': ('A_35', (532, 209), (593, 237), (555.4, 273.2), 'closed'),
        'smile': ('A_01', (497, 207), (558, 235), (518.6, 265.3), 'closed'),
        'grin': ('A_28', (487, 205), (548, 234), (511.8, 265.5), 'open'),
        'laugh': ('A_22', (496, 201), (553, 238), (512.4, 258.2), 'open'),
        'surprise': ('A_13', (490, 209), (546, 238), (507.7, 271.7), 'open'),
        'shout': ('A_12', (569, 216), (625, 241), (588.7, 277.8), 'open'),
        'sad': ('A_23', (510, 219), (562, 241), (520.0, 269.0), 'closed'),
        'cry': ('A_23', (510, 219), (562, 241), (520.0, 269.0), 'closed'),
        'pout': ('A_04', (495, 208), (562, 234), (510.6, 256.9), 'closed'),
        'angry': ('A_30', (505.7, 231), (563, 251), (527.3, 283.3), 'closed'),
        'doubt': ('A_09', (491, 203), (551, 235), (515.7, 267.5), 'closed'),
        'think': ('A_34', (506, 214), (565, 244), (521.7, 274.4), 'small'),
        'embarrassed': ('A_21', (504.7, 211), (563, 237), (530, 268), 'hidden'),
        'serious': ('A_25', (490, 205), (549, 230), (511.5, 262.5), 'closed'),
        'determined': ('A_10', (531, 197), (587, 226), (550.0, 254.1), 'closed'),
        'tired': ('A_19', (510, 228), (560, 257), (527.6, 282.3), 'small'),
        'calm': ('A_29', (498, 208), (553, 236), (510.9, 264.7), 'closed'),
    },
    'shione': {
        'neutral': ('B_10', (524, 167), (581, 192), (545.0, 222.1), 'closed'),
        'smile': ('B_01', (519, 167), (582, 192), (543.0, 219.3), 'closed'),
        'grin': ('B_02', (537, 154), (601, 181), (560.6, 210.0), 'open'),
        'laugh': ('B_22', (537, 152), (616, 191), (565.3, 214.8), 'open'),
        'surprise': ('B_13', (530, 182), (588, 210), (546.5, 242.1), 'open'),
        'shout': ('B_12', (644, 194), (705, 215), (670.6, 255.4), 'open'),
        'sad': ('B_23', (535, 191), (593, 211), (556.6, 246.6), 'closed'),
        'cry': ('B_23', (535, 191), (593, 211), (556.6, 246.6), 'closed'),
        'pout': ('B_04', (531, 166), (594, 191), (551.9, 214.3), 'closed'),
        'angry': ('B_30', (518.3, 194), (571.7, 205.7), (536, 243.3), 'closed'),
        'doubt': ('B_09', (521, 172), (577, 199), (539.8, 219.5), 'closed'),
        'think': ('B_34', (523, 172), (582, 201), (539.0, 230.8), 'small'),
        'embarrassed': ('B_21', (516.3, 177.5), (590, 196), (545, 225), 'hidden'),
        'serious': ('B_25', (520, 169), (581, 192), (536.9, 215.2), 'closed'),
        'tired': ('B_19', (541, 181), (592, 207), (551.0, 231.8), 'small'),
        'calm': ('B_29', (525, 168), (586, 186), (543.3, 220.7), 'closed'),
        'blank': ('B_35', (543, 186), (607, 205), (569.0, 243.2), 'small'),
    },
    'saji': {
        'neutral': ('C_10', (526, 169), (585, 203), (547.8, 236.6), 'closed'),
        'smile': ('C_01', (495, 184), (559, 218), (523.9, 249.5), 'closed'),
        'grin': ('C_28', (497, 177), (562, 216), (506.3, 234.4), 'open'),
        'laugh': ('C_22', (514, 177), (580, 218), (528.0, 245.6), 'open'),
        'surprise': ('C_13', (524, 188), (587, 220), (548.8, 258.3), 'open'),
        'shout': ('C_12', (602, 196), (668, 224), (625.2, 267.9), 'open'),
        'sad': ('C_23', (525, 213), (578, 243), (538.3, 272.3), 'closed'),
        'cry': ('C_23', (525, 213), (578, 243), (538.3, 272.3), 'closed'),
        'pout': ('C_04', (495, 184), (562, 218), (527.5, 251.9), 'closed'),
        'angry': ('C_30', (607.5, 210), (676, 242.5), (635, 276), 'closed'),
        'doubt': ('C_09', (500, 189), (561, 224), (521.0, 255.4), 'closed'),
        'think': ('C_34', (495, 188), (560, 225), (514.1, 257.1), 'small'),
        'embarrassed': ('C_21', (506.3, 207.3), (580.3, 233.3), (540, 255), 'hidden'),
        'serious': ('C_25', (492, 183), (559, 213), (512.9, 245.2), 'closed'),
        'tired': ('C_19', (506, 205), (561, 242), (522.8, 267.3), 'closed'),
        'calm': ('C_29', (498, 183), (564, 215), (519.6, 245.6), 'closed'),
    },
}

NAMES = {'tsuzumi': '百々かさゝぎ', 'shione': '垣外しをね', 'saji': '家守さぢ'}

# Pixeliser settings.
L0_LAMBDA = 0.004          # flattening of the painting before pixelising (0 = off); the face keeps 1/4 of it
OE_THICKNESS = 1           # PixelOE outline expansion
PALETTE_K = 30             # colours measured per character (k-means, Lab, over all her expressions)
CLEAN_MAX = 2              # colour islands up to this many px merge into their most similar neighbour (not in faces)
CROP_MARGIN = 24           # source px kept around the window in the stored crops (room for framing tweaks)

# Canonical eye colours per character, from k-means of the illustration's eye regions (lash, iris dark -> light,
# sclera and its shade, skin, hair over the eyes). Inside each eye the pixelised colours snap to these, so the eyes
# have no muddy in-between tones and look the same in every expression.
EYE_CANON = {
    'tsuzumi': ['#211314', '#443536', '#4f4757', '#7b7385', '#a69fae', '#fbede4', '#cdbfbe', '#f6dac9', '#bd9d8e',
                '#2f2433', '#4a3b55'],
    'shione': ['#311a1d', '#572a30', '#7e3a48', '#b45d66', '#e2928f', '#faeade', '#e3c6bd', '#f9e3d6', '#c79c93',
               '#856b81', '#b8a3b6', '#d9c9d3'],
    'saji': ['#1a100f', '#552925', '#223338', '#3f676b', '#6fa6a2', '#f7ede5', '#c5b4ab', '#f8d5bd', '#d39a86',
             '#d03c3b', '#8b2229'],
}
EYE_REGION = (0.40, 0.30)   # eye ellipse half-axes, as fractions of the native eye distance

# Closed mouths are redrawn as a 1-px stroke along the illustration's mouth line (as in v1): line colour, soft end.
MOUTH = {
    'tsuzumi': ('#8a4a4c', '#c98f86'),
    'shione': ('#95504f', '#d0948c'),
    'saji': ('#8a3b3a', '#cf8c7c'),
}
MOUTH_CAVITY = {'tsuzumi': '#6e2a38', 'shione': '#6e2434', 'saji': '#6e2430'}   # inside of an open mouth, upper part
MOUTH_TONGUE = {'tsuzumi': '#d9707c', 'shione': '#de6f7c', 'saji': '#de6f7c'}   # lower part of an open mouth
MOUTH_PINK = {'tsuzumi': '#e8968f', 'shione': '#e8968f', 'saji': '#ea8f86'}   # the inside of a slightly open mouth
MOUTH_BH = 5.0             # black-hat threshold (L*) of the mouth stroke in the work image
MOUTH_MAX_W = 9            # widest closed mouth, native px
