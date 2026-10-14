"""Palettes of the pixel dialogue portraits (v3). One character per key, '.' = transparent.

Lower-case keys are the face keys every character shares, so the expression parts (eyes, mouths, tears, blush,
sweat, symbols) mean the same thing on every face; each character maps them to her own colours. Upper-case keys and
digits are the character's hair and costume.

v3 ramps are measured from the owner's illustrations (tools/art/portraits2/derive: luminance bands and Lab k-means of
the reference crop, then evened into hue-shifted steps), so the pixel bust keeps the illustration's colour: Shione's
lavender silver, Tsuzumi's blue-black with a purple sheen under the straw hat, Saji's red bob with the teal band.
"""

# face keys, same meaning for everyone (colours below per character) ---------------------------------------------
#   s t u q   skin light, shade, deep shade, skin line (jaw, nose, closed mouth; warm, never black)
#   b p       blush, blush hatching
#   w v l     eye white, eye white in the lash shadow, glint (eyes, tears)
#   m n y     mouth inside, tongue, teeth
#   c C z     tear / sweat: light, body, edge
#   x X       anger mark, its dark
#   k j       lash ink (also the rim of the symbols), soft line (lower lash, crease)
#   E e i a   iris: dark (top, pupil), mid, light, bright accent

_FACE = {
    'w': '#fbf9f8', 'v': '#dcd4dc', 'l': '#ffffff', 'm': '#5e1d2d', 'n': '#de6f7c', 'y': '#fffaf5',
    'c': '#e9f7ff', 'C': '#a8d9f2', 'z': '#5f9fd0', 'x': '#e23b4e', 'X': '#931f35',
}

PALETTES = {
    'shione': {
        **_FACE,
        's': '#fdeadb', 't': '#f4c9b8', 'u': '#d99a8c', 'q': '#95504f', 'b': '#f5a3a0', 'p': '#e57683',
        'w': '#fbf7f8', 'v': '#ddd1dc',
        # eyes: red iris, the lash in a dark wine
        'k': '#3a0f1c', 'j': '#a8636a', 'E': '#6d1f30', 'e': '#c4505f', 'i': '#e98a8e', 'a': '#f8c0b8',
        # hair: lavender silver, light -> dark, and its outline
        'h': '#f6eef0', 'H': '#e6d6df', 'L': '#d2bfcf', 'M': '#b8a2b8', 'D': '#96809c', 'O': '#6e5a7a', 'K': '#47344f',
        # the crescent horn ornament
        'J': '#b85a68', 'R': '#8e3244', 'r': '#5c1b2a', 'P': '#2e0d18',
        # red: the hair cord and its tails, the two marks under the eye
        '1': '#d4566a', '2': '#a8374b', '3': '#7a2337', '4': '#4a1424',
        # white kimono
        'W': '#fcf8f2', 'V': '#ebe0dc', 'U': '#cbbcc6', 'Y': '#8f7d91',
        # plum under-collar
        '5': '#7e5470', '6': '#5a3550', '7': '#3f2238', '8': '#26101f',
    },
    'tsuzumi': {
        **_FACE,
        's': '#fdeadb', 't': '#f4c9b8', 'u': '#d99a8c', 'q': '#8a4a4c', 'b': '#f5a3a0', 'p': '#e57683',
        'w': '#fbf9fb', 'v': '#d8d6e2',
        # eyes: the owner's grey-blue iris, lash in the hair's ink
        'k': '#1a1220', 'j': '#7a6470', 'E': '#33324a', 'e': '#666b8c', 'i': '#a0a6c0', 'a': '#d6dbea',
        # hair: blue-black with a purple sheen (h is also the see-through brow over the bangs)
        'h': '#7d6a8e', 'H': '#5f4d6c', 'L': '#4a3b55', 'M': '#3a2d44', 'D': '#2b2134', 'O': '#1d1524', 'K': '#120c17',
        # the straw hat (cream) and its red band
        'W': '#f6ecdf', 'V': '#e4d6c6', 'U': '#c7b4a5', 'Y': '#8a7470',
        'R': '#c4425f', 'r': '#8c2b45', 'P': '#4e1426',
        # the hat's navy underside
        '1': '#3d4566', '2': '#2d334c', '3': '#202336', '4': '#13121e',
        # navy kimono
        '5': '#414c78', '6': '#2f3658', '7': '#20243c', '8': '#121322',
    },
    'saji': {
        **_FACE,
        # Saji's skin is warmer and her rosy cheeks are part of her design
        's': '#fde2cf', 't': '#f5c2aa', 'u': '#dc9580', 'q': '#8a3b3a', 'b': '#f59a98', 'p': '#e5707c',
        'w': '#fbf9f7', 'v': '#d9d6dc',
        # eyes: teal iris, lash in a dark red-brown
        'k': '#2a0f15', 'j': '#9a5a52', 'E': '#123e46', 'e': '#227078', 'i': '#4ea6a4', 'a': '#a8e0d6',
        # hair: red, light -> dark, and its outline
        'h': '#f37f66', 'H': '#e3564c', 'L': '#d03c3b', 'M': '#b52e31', 'D': '#8b2229', 'O': '#5f1820', 'K': '#3a0f17',
        # teal headband
        '1': '#4a7f80', '2': '#2f5c63', '3': '#1f3d44', '4': '#12242a',
        # mint cape
        '5': '#eaeedb', '6': '#cfd7c1', '7': '#a8b6a1', '8': '#6c7a6a',
        # plum collar, red collar edge
        'P': '#8e4858', 'Q': '#6a2e3f', 'Z': '#41162a', 'R': '#d83a3a', 'r': '#a5262c',
        # gold bell
        'G': '#ffe08a', 'F': '#e0a840', 'A': '#a06a28', 'B': '#5a3a18',
        # her rosy cheeks, always there (the owner draws them in every illustration); the blush part goes on top
        '9': '#f8c6b6',
        # the same cheeks one step lighter, on her neutral face only (so it does not read as a smile)
        '0': '#fbd5c3',
    },
}


def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
