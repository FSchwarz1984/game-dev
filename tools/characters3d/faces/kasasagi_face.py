"""百々かさゝぎ's face stamps, round 5 (decision-log G5R3-6..8; docs/knowledge/24 §8).

The face is about 11 x 6 native px under thick bangs, drawn like the v0.2 sprite's face the user liked:
two small eyes close under the bangs (2 wide, 3 tall, 3 px apart, low on the head), a soft one-pixel
blush on each cheek, and almost no mouth. No brows ever (the bangs cover them, G5R3-8). Emotion is
carried by the eyes' shape (open, blink, half, ^ ^, > <, wide), tears, the blush, and the body
(anims.py); the mouth is at most one or two dark-pink pixels when she talks. Nothing red, no teeth.

Colours: the ChatGPT sheet's iris (#3d414f dark, #6f7887 iris, #aaafb8 light), not black. Each stamp is
text in an 8 x 8 cell; `pivot` is the cell pixel (x right, y down) that lands on the landmark the game
projects (eyes: the outer column, middle row). Her right eye (the viewer's left) is drawn, column 0
its outer side; her left eye is its mirror image (the highlights stay symmetric, both on the inner
side, as in the sprite). Views: 'f' front, 't' three-quarter, 's' profile (the near eye only).

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
    'Z': (226, 232, 255, 200),    # sleepy 'z' (glow)
}

# eyes mirror without moving the light (both lights on the inner side)
EYE_LIGHT = 'mirror'

# ------------------------------------------------------------------------------------------------
# eyes: her right eye, column 0 its outer side; 3 rows (the top row lies under the bangs' edge)
EYE_PIVOT = (0, 1)
EYES = {
    # (the top row of every eye lies under the bangs: the shape a stamp shows lives in its two lower rows)
    'open': ['KK',               # the sprite's eye: three dark pixels and a glint
             'KW',
             'KK'],
    'blink': ['..',
              '..',
              'kk'],
    'half': ['..',               # sleepy: the lid half down
             'kk',
             'KW'],
    'smug': ['..',               # half-lidded over the glint (mischief)
             'kk',
             'KW'],
    'happy': ['.k.',             # ^ (three wide: its middle on the eye's outer column, see pivots)
              'k.k'],
    'wide': ['KK',               # startled: a white ring round the dark, a row taller
             'SK',
             'SW',
             'KK'],
    'look_in': ['KK',            # glancing toward her nose (the glint moves out)
                'WK',
                'KK'],
    'angry': ['K.',              # the lid slants down to the inner corner
              'K.',
              'KW'],
    'sad': ['.K',                # the inner corner up
            '.K',
            'KW'],
    'teary': ['KK',
              'KW',
              'CC'],
    'cry0': ['k.',               # squeezed shut (>), a tear falling from the inner corner
             '.k',
             'k.',
             '.C',
             '..',
             '..'],
    'cry1': ['k.',
             '.k',
             'k.',
             '..',
             '.c',
             '.C'],
    'shut': ['k.',               # squeezed shut without tears (a wince, a giggle)
             '.k',
             'k.'],
}
# per-stamp pivots where they differ from EYE_PIVOT: the ^ centred over the eye's outer column; the
# squeezed-shut > one row lower, so all three of its rows show under the bangs
EYE_PIVOTS = {'happy': (1, 0), 'cry0': (0, 0), 'cry1': (0, 0), 'shut': (0, 0)}

# columns kept per view (None: all). In profile only the near eye shows, one column wide (its outer,
# dark column: a dark dash under the bangs reads as an eye seen from the side).
VIEW_COLS = {'f': None, 't': None, 's': [0]}

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
MOUTH_VIEW_DROP = {'f': [], 't': [], 's': []}

# ------------------------------------------------------------------------------------------------
# cheeks: one soft pixel always; two warm ones when she blushes
BLUSH_PIVOT = (0, 0)
BLUSH = {'soft': ['B'], 'blush': ['bb']}
MARK_PIVOT = (1, 1)
MARKS = {
    'anger': ['V.V', '.V.', 'V.V'],
    'sweat': ['.D', 'DD', 'D.'],
    'zzz': ['ZZZ', '.Z.', 'ZZZ'],
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
