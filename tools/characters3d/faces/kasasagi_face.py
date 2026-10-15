"""百々かさゝぎ's face stamps: pixel art for the screen lattice (see docs/knowledge/24 §8).

The face is about 13 x 10 native pixels, so it is drawn the way sprite faces of that size are drawn
(Eastward, Stardew Valley, Octopath Traveler): eyes 2 x 3 with one highlight pixel, brows one pixel
thick, a mouth of 1-3 pixels (a short dark line; a small arc for a smile; a 2 x 2 dark block for an
open mouth), a pale 2-pixel blush. No big shapes, no bright reds: at native size those read as a
wound (the lead, 2026-10-15). The mischief lives in the half-lidded eyes, the one raised brow and the
one raised corner of the mouth.

Each stamp is drawn here as text in an 8 x 8 cell; `pivot` is the cell pixel (x right, y down) that
lands on the landmark the game projects every frame (eye centre, brow, mouth, cheek). Her right eye
(on the viewer's left when she faces us) is drawn, column 0 its outer side; her left eye is its
mirror, with the highlight kept on the same (screen-left) side: one light for both eyes. Views: 'f'
front, 't' three-quarter, 's' profile (the near eye only, one column).

Colours (sRGB); a glow pixel (eye highlight, tears) is stored with alpha 200 and keeps its light.
"""

PALETTE = {
    'K': (34, 24, 46, 255),       # the eye's dark (lid line, pupil)
    'I': (58, 62, 104, 255),      # iris (a deep navy, a step lighter than the lid)
    'k': (120, 84, 96, 255),      # a soft lower lid
    'W': (255, 255, 255, 200),    # highlight (glow)
    'S': (236, 240, 252, 255),    # white of the eye (surprise only; a cool white, apart from the skin)
    'M': (110, 44, 58, 255),      # mouth (a dark red-brown, never a bright red)
    'B': (246, 188, 186, 255),    # blush (pale)
    'C': (186, 230, 255, 200),    # tear, light (glow)
    'c': (112, 172, 236, 255),    # tear
    'b': (78, 54, 80, 255),       # brow
    'V': (222, 60, 70, 255),      # anger mark
    'D': (200, 236, 255, 200),    # sweat drop (glow)
    'Z': (226, 232, 255, 200),    # a sleepy 'z' (glow)
}

# ------------------------------------------------------------------------------------------------
# eyes: her right eye, 2 wide x 3 tall; column 0 is the outer side; the landmark is the middle row
EYE_PIVOT = (0, 1)
EYES = {
    'open': ['KK',
             'WI',
             'II'],
    'blink': ['..',
              '..',
              'KK'],
    'half': ['..',               # sleepy: the lid half down
             'KK',
             'II'],
    'smug': ['..',               # half-lidded, the pupil and its light under a flat lid (mischief)
             'KK',
             'WI'],
    'happy': ['...',             # ^ (three wide, the arch over the eye's place)
              '.K.',
              'K.K'],
    'wide': ['KK',               # surprise: the white shows round a dot of a pupil
             'SK',
             'SS'],
    'angry': ['K.',              # the lid slants down to the inner corner
              'KK',
              'II'],
    'sad': ['.K',                # the inner corner up, the outer down
            'KK',
            'II'],
    'grin': ['KK',               # smiling eyes: the cheeks push the lower lid up
             'WI',
             '..'],
    'teary': ['KK',
              'WI',
              'CC',
              '.c'],
    'cry0': ['K.',               # squeezed shut (>), a tear running
             '.K',
             'K.',
             'c.',
             'C.',
             'c.'],
    'cry1': ['K.',
             '.K',
             'K.',
             'C.',
             'c.',
             '.c'],
}

# columns kept per view (None: all). In profile only the near eye shows, one column wide.
VIEW_COLS = {'f': None, 't': None, 's': [1]}

# ------------------------------------------------------------------------------------------------
# brows: her right brow, one pixel thick (column 0 its outer end), on the strip of forehead under
# the bangs; an expression gives one name for both, or {'R': name, 'L': name} (one brow raised)
BROW_PIVOT = (0, 0)
BROWS = {
    'normal': ['bb'],
    'angry': ['b.', '.b'],       # inner end down
    'sad': ['.b', 'b.'],         # inner end up
    'up': ['bb'],                # raised a row
    'arch': ['bb'],              # raised two rows (the cocked brow)
    'flat': ['bb'],
    'low': ['bb'],               # lowered a row (the narrowed side)
}
BROW_UP_SHIFT = {'up': 1, 'arch': 2, 'low': -1}

# ------------------------------------------------------------------------------------------------
# mouths: 1-3 pixels; the landmark is column 1, row 0
MOUTH_PIVOT = (1, 0)
MOUTHS = {
    'neutral': ['MM'],
    'smile': ['M.M',             # a small arc
              '.M.'],
    'laugh': ['MM',              # open: a 2 x 2 dark block
              'MM'],
    'grin': ['MMM',              # a wide open smile (D)
             '.M.'],
    'o': ['MM',
          'MM'],
    'frown': ['.M.',
              'M.M'],
    'grit': ['MMM'],
    'wail': ['MM',
             'MM',
             'MM'],
    'smirk': ['..M',             # one corner up (her left)
              'MM.'],
    'pout': ['M',                # pursed and pushed out
             'M'],
    'yawn': ['MM',
             'MM',
             'MM'],
    'talk_a': ['MM',
               'MM'],
    'talk_b': ['MM'],
    'talk_c': ['MMM',
               '.M.'],
}
MOUTH_VIEW_DROP = {'f': [], 't': [], 's': []}

# ------------------------------------------------------------------------------------------------
# cheeks and marks
BLUSH_PIVOT = (0, 0)
BLUSH = {'blush': ['BB']}
MARK_PIVOT = (1, 1)
MARKS = {
    'anger': ['V.V', '.V.', 'V.V'],
    'sweat': ['.D', 'DD', 'D.'],
    'zzz': ['ZZZ', '.Z.', 'ZZZ'],
}

# ------------------------------------------------------------------------------------------------
# expressions: which stamp each feature uses. 'eyes' may be a (name, name) pair of animation
# frames; the game alternates them.
EXPRESSIONS = {
    'neutral':   {'eyes': 'open', 'brows': 'normal', 'mouth': 'neutral'},
    'smile':     {'eyes': 'open', 'brows': 'normal', 'mouth': 'smile'},
    'happy':     {'eyes': 'happy', 'brows': 'up', 'mouth': 'laugh', 'blush': True},
    'grin':      {'eyes': 'grin', 'brows': 'up', 'mouth': 'grin'},
    # 古灵精怪: the half-narrowed eyes, one brow cocked, the smirk's one corner
    'mischief':  {'eyes': 'smug', 'brows': {'R': 'low', 'L': 'arch'}, 'mouth': 'smirk'},
    'cat':       {'eyes': 'grin', 'brows': 'normal', 'mouth': 'smile'},
    # "huh?" (the head tilt): one brow up, the little o
    'curious':   {'eyes': 'open', 'brows': {'R': 'normal', 'L': 'up'}, 'mouth': 'o'},
    'surprised': {'eyes': 'wide', 'brows': 'up', 'mouth': 'o'},
    'angry':     {'eyes': 'angry', 'brows': 'angry', 'mouth': 'grit', 'mark': 'anger'},
    'sad':       {'eyes': 'sad', 'brows': 'sad', 'mouth': 'frown'},
    'teary':     {'eyes': 'teary', 'brows': 'sad', 'mouth': 'frown'},
    'cry':       {'eyes': ('cry0', 'cry1'), 'brows': 'sad', 'mouth': 'wail'},
    'smug':      {'eyes': 'smug', 'brows': 'flat', 'mouth': 'smile'},
    'sleepy':    {'eyes': 'half', 'brows': 'flat', 'mouth': 'yawn', 'mark': 'zzz'},
    'pout':      {'eyes': 'angry', 'brows': 'angry', 'mouth': 'pout', 'blush': True},
    'embarrassed': {'eyes': 'open', 'brows': 'sad', 'mouth': 'frown', 'blush': True, 'mark': 'sweat'},
}
TALK = ['talk_a', 'talk_b', 'talk_c', 'neutral']
