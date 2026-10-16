"""百々かさゝぎ's face stamps, round 6 (the model sheet's face: big grey eyes under hime bangs that hide
the brows, decision-log G5R3-8; docs/knowledge/24 §0).

At the game's scale (30 px per metre) the sheet's face is 10 px wide and its eyes 3 x 3 px each, laid
out [skin][eye eye eye][gap gap][eye eye eye][skin] (tools/characters3d/kasasagi/model.py, landmarks).
The bangs end on the eyes' top row. An eye: a dark top (lash and pupil), a glint, the grey iris
underneath (the sheet's iris is light at the bottom). Emotion is carried by the eyes' shape (open,
blink, half, ^ ^, > <, wide), tears, the blush and the body; the mouth is at most one or two
dark-pink pixels. Nothing red, no teeth.

Colours: the ChatGPT sheet's iris (#3d414f dark, #6f7887 iris, #aaafb8 light). Each stamp is text in an
8 x 8 cell; `pivot` is the cell pixel (x right, y down) that lands on the landmark the game projects
(eyes: the outer column, middle row). Her right eye (the viewer's left) is drawn, column 0 its outer
side; her left eye is its mirror image. Views: 'f' front, 't' three-quarter, 's' profile.

A glow pixel (the eye's light, tears) is stored with alpha 200 and keeps its light at night.
"""

PALETTE = {
    'K': (54, 57, 71, 255),       # the eye's dark: the sheet's iris shadow #3d414f as it lands on screen
                                  # (the face's light and the grade lift a stamp by about 6 levels)
    'k': (46, 46, 60, 255),       # a closed eye's line (a step deeper than K, so a 1 px line reads)
    'I': (111, 120, 135, 255),    # iris (#6f7887)
    'W': (118, 138, 180, 255),    # the eye's light: a blue-grey glint in the dark (the v0.2 sprite's is a
                                  # mid blue #6f84b3; a white pixel read as a stare, a near-skin one
                                  # left only a thin dark line)
    'S': (250, 248, 246, 255),    # the white of a startled eye
    'M': (176, 92, 104, 255),     # mouth: a dark pink, never red
    'm': (222, 150, 146, 255),    # a soft mouth (a pale pink dot)
    'B': (246, 168, 160, 255),    # blush, soft (always on)
    'b': (238, 132, 138, 255),    # blush, warm (happy, shy, pouting)
    'C': (176, 214, 250, 200),    # tear, light (glow): a clear blue, not white
    'c': (128, 172, 230, 255),    # tear
    'V': (214, 64, 78, 255),      # anger mark
    'D': (200, 236, 255, 200),    # sweat drop (glow)
    'Z': (132, 160, 226, 200),    # sleepy 'z' (glow): a mid blue (a near-white z vanished on the ivory hat)
}

# eyes mirror without moving the light (both lights on the inner side)
EYE_LIGHT = 'mirror'

# ------------------------------------------------------------------------------------------------
# eyes: her right eye, column 0 its outer side; 3 rows (the top row lies under the bangs' edge)
EYE_PIVOT = (0, 1)
EYES = {
    'open': ['KKK',              # the lash and the pupil
             'KWI',              # the glint, the iris
             'IIK'],             # the iris light at the bottom, the outer corner closed
    'blink': ['...',
              'kkk',
              '...'],
    'half': ['...',              # sleepy: the lid half down
             'kkk',
             'IWK'],
    'smug': ['...',              # half-lidded over the glint (mischief)
             'kkk',
             'KWI'],
    'happy': ['.k.',             # ^
              'k.k',
              '...'],
    'wide': ['KKK',              # startled: round, the glint small, the white showing below
             'KWK',
             'SKS'],
    'look_in': ['KKK',           # glancing toward her nose (the glint moves out)
                'IWK',
                'KII'],
    'angry': ['K..',             # the lid slants down to the inner corner
              'KK.',
              'KWI'],
    'sad': ['..K',               # the inner corner up
            '.KK',
            'KWI'],
    'teary': ['KKK',
              'KWI',
              'CCC'],
    'cry0': ['k..',              # squeezed shut (>), a tear falling from the inner corner
             '.k.',
             'k..',
             '..C',
             '...',
             '...'],
    'cry1': ['k..',
             '.k.',
             'k..',
             '...',
             '..c',
             '..C'],
    'shut': ['k..',              # squeezed shut without tears (a wince, a giggle)
             '.k.',
             'k..'],
}
# per-stamp pivots where they differ from EYE_PIVOT
EYE_PIVOTS = {}

# columns kept per view (None: all). In profile only the near eye shows, one column wide (its outer,
# dark column: a dark dash under the bangs reads as an eye seen from the side).
VIEW_COLS = {'f': None, 't': None, 's': [0, 1]}

# placement (character3d.gd). The facing (cos of the angle between a landmark's normal and the
# camera) where a stamp turns from front to three-quarter to side.
VIEW_CUTS = [0.80, 0.25, 0.10]
# both eyes (and both blush pixels) at the height of the one nearer the camera
LEVEL_PAIRS = 'near'

# ------------------------------------------------------------------------------------------------
# no brows (G5R3-8): the bangs cover them
BROW_PIVOT = (0, 0)
BROWS = {}
BROW_UP_SHIFT = {}

# ------------------------------------------------------------------------------------------------
# mouths: 0-2 pixels; the landmark is column 0, row 0
MOUTH_PIVOT = (0, 0)
MOUTHS = {
    'soft': ['m'],               # a pale dot (a content face)
    'o': ['M'],                  # surprise: a dark-pink dot
    'open': ['M',                # talking, open: 1 x 2
             'M'],
    'line': ['M'],
    'pout': ['m'],
    'wail': ['M',                # crying: open, 1 x 2
             'M'],
    'smirk': ['.m'],             # one corner up: a pale dot off-centre (her left)
}
# the landmark is the chin's lowest row: a two-row mouth grows up from it (pivot on its lower pixel),
# or its second pixel fell on the neck below the face
MOUTH_PIVOTS = {'open': (0, 1), 'wail': (0, 1)}
MOUTH_VIEW_DROP = {'f': [], 't': [], 's': []}

# ------------------------------------------------------------------------------------------------
# cheeks: one soft pixel always; two warm ones when she blushes
BLUSH_PIVOT = (0, 0)
BLUSH = {'soft': ['B'], 'blush': ['bb']}
MARK_PIVOT = (1, 1)
MARKS = {
    'anger': ['.V.V.',           # the four bent corners of the anger vein
              'VV.VV',
              '.....',
              'VV.VV',
              '.V.V.'],
    'sweat': ['.D', 'DD', 'D.'],
    'zzz': ['ZZZZ',              # a 3 x 3 z read as an I
            '..Z.',
            '.Z..',
            'ZZZZ'],
}

# ------------------------------------------------------------------------------------------------
# expressions: which stamp each feature uses. 'eyes' may be a (name, name) pair of animation frames
# (the game alternates them at 6 Hz); 'cheeks' a blush stamp ('soft' by default, '' none); 'mouth' ''
# for none (most of the time).
EXPRESSIONS = {
    'neutral':   {'eyes': 'open', 'mouth': ''},
    'smile':     {'eyes': 'open', 'mouth': 'soft'},
    'happy':     {'eyes': 'happy', 'mouth': 'soft', 'cheeks': 'blush'},
    'grin':      {'eyes': 'happy', 'mouth': 'smirk', 'cheeks': 'blush'},
    # 坏笑 / 古灵精怪: half-lidded eyes over a sly one-sided dot of a smile
    'mischief':  {'eyes': 'smug', 'mouth': 'smirk'},
    'cat':       {'eyes': 'happy', 'mouth': ''},
    'curious':   {'eyes': 'open', 'mouth': 'o'},
    'surprised': {'eyes': 'wide', 'mouth': 'o', 'cheeks': ''},
    'angry':     {'eyes': 'angry', 'mouth': 'line', 'mark': 'anger', 'cheeks': 'blush'},
    'sad':       {'eyes': 'sad', 'mouth': ''},
    'teary':     {'eyes': 'teary', 'mouth': ''},
    'cry':       {'eyes': ('cry0', 'cry1'), 'mouth': 'wail', 'cheeks': 'blush'},
    'smug':      {'eyes': 'smug', 'mouth': 'soft'},
    'sleepy':    {'eyes': 'half', 'mouth': '', 'mark': 'zzz'},
    'pout':      {'eyes': 'angry', 'mouth': 'pout', 'cheeks': 'blush'},
    'embarrassed': {'eyes': 'look_in', 'mouth': '', 'cheeks': 'blush', 'mark': 'sweat'},
    'blink':     {'eyes': 'blink', 'mouth': ''},
}
TALK = ['open', 'line', 'open', '']
