"""Palettes of the hand-drawn dialogue portraits (v2). One character per key, '.' = transparent.

Lower-case keys are the face keys every character shares, so the expression parts (eyes, brows, mouths, tears,
blush, sweat, anger marks) mean the same thing on every face; each character maps them to her own colours.
Upper-case keys and digits are the character's hair and costume.

Ramps come from the in-game sprites and the v1 portraits (tools/art/pixel_portraits.py), so the portraits and the
sprites look like one artist's work. The skin ramp is shared by all three (sprite skin). New steps are marked (*).
"""

# face keys shared by everyone ------------------------------------------------------------------------------------
SKIN = {
    's': '#fde7d8',  # skin light
    't': '#f2c4b0',  # skin shade (*: one step between the sprite's #fde7d8 and #efbca8, for the soft cel shadow)
    'u': '#d99a88',  # skin deep shade (under the bangs, the neck, the far jaw)
    'q': '#7a3a3c',  # skin line: jaw, nose, closed mouth, ear (warm dark, never black)
    'b': '#f7a8a6',  # blush
    'p': '#e57683',  # blush hatching, deep blush (*)
}
FACE = {
    'w': '#faf8fb',  # eye white (*)
    'v': '#d9d3e3',  # eye white in the lash's shadow (*)
    'l': '#ffffff',  # glint (eyes, tears)
    'm': '#5e1d2d',  # mouth inside (*)
    'n': '#de6f7c',  # tongue (*)
    'y': '#fffaf5',  # teeth (*)
    'c': '#e9f7ff',  # tear / sweat light (*)
    'C': '#a8d9f2',  # tear / sweat body (*)
    'z': '#5f9fd0',  # tear / sweat edge (*)
    'x': '#e23b4e',  # anger mark (*)
    'X': '#931f35',  # anger mark dark (*)
}

PALETTES = {
    'tsuzumi': {
        **SKIN, **FACE,
        # eyes: the owner's grey-blue iris (v1 note), lashes in the hair's ink
        'k': '#16122a',  # lash, brow, darkest line
        'j': '#4b3a58',  # soft line: lower lash, crease
        'E': '#2a2444',  # iris dark (top, pupil)
        'e': '#6e7a98',  # iris mid
        'i': '#a7b1c8',  # iris light (bottom)
        'a': '#d2d9e8',  # iris bright accent (*)
        # hair: the v1 portrait ramp (sprite ramp warmed one step)
        'O': '#16122a', 'D': '#241a2e', 'M': '#33263e', 'L': '#4b3a58', 'H': '#6f5c80',
        # straw hat and haori whites; the hat's indigo lining and kimono
        'W': '#fbf7ef', 'V': '#e9e0d3', 'U': '#c9bccb', 'Y': '#9a8ca6',
        'I': '#45508a', 'N': '#2f345e', 'Q': '#1d1f3c',
        # red: hat band, collar, hair ties
        'R': '#c63f5c', 'r': '#8c2b45', 'P': '#3e1424',
    },
    'shione': {
        **SKIN, **FACE,
        'k': '#2a0f1a', 'j': '#7a5470',
        'E': '#6d2333', 'e': '#c84a5c', 'i': '#ec9a96', 'a': '#f8cfc4',
        # hair: warm silver (v1: the sprite's lightness steps at the owner's warm hue)
        'O': '#3b3150', 'D': '#73647c', 'M': '#a08ea1', 'L': '#c6b3c1', 'H': '#e6d8de', 'h': '#f7f0f2',
        # white kimono
        'W': '#fcf9f6', 'V': '#ece3e2', 'U': '#cdbfcc', 'Y': '#9c8a9f',
        # plum: horn, under-collar
        '5': '#86607c', '6': '#5f4058', '7': '#432c40', '8': '#2a0f1a',
        # red: hair cord, ribbon tails, the two marks
        'R': '#cc4b5d', 'r': '#9e3548', 'P': '#6d2333',
    },
    'saji': {
        **SKIN, **FACE,
        'b': '#f59a98',  # Saji's rosy cheeks are part of her design: one step deeper
        'k': '#36101c', 'j': '#8c3a3e',
        'E': '#173c42', 'e': '#2c7a78', 'i': '#4fa8a0', 'a': '#9bdccd',
        # hair: sprite reds, one warm highlight (*)
        'O': '#4a1222', 'D': '#9b2434', 'M': '#cf3439', 'L': '#ef5340', 'H': '#ff8f6c',
        # teal headband and trim
        '1': '#4fa8a0', '2': '#2f7d7a', '3': '#215a5d', '4': '#13282c',
        # mint cape
        '5': '#e6f3df', '6': '#c2dfc4', '7': '#94c0a6',
        # plum collar
        '8': '#702e5e', '9': '#4e2045',
        # gold bell
        'G': '#ffe58c', 'F': '#e2ae3c', 'A': '#a5702a',
        # white sleeves, red under-collar
        'W': '#fcf8ef', 'V': '#e6dccf', 'R': '#d8443c', 'r': '#a52a33',
    },
}

# hair keys used by the cleanliness check (orphan pixels inside hair are allowed only for highlights)
HAIR_KEYS = 'ODMLHh'


def rgb(hexstr):
    h = hexstr.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
