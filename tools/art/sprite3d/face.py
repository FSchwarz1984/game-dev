"""Face decals: eyes, mouth, blush and marks are hand-placed pixel stamps put on the rendered head
at the projected feature points, chosen by how far the face is turned from the camera. The head
geometry gives the shape; the stamps give the pixels a pixel artist would place (lash, iris,
highlight). The camera-space normal of a feature decides its class:
    front   facing the camera (n.z > 0.80)
    three   turned (0.42 < n.z <= 0.80): the near eye full width, the far eye squeezed
    side    profile (0.18 < n.z <= 0.42): only the near eye, one column
    hidden  otherwise
The stamps are mirrored for the other side so the highlight always sits toward the key light
(top-left)."""

from __future__ import annotations

from model import stamp


def view_class(nz):
    if nz > 0.80:
        return 'front'
    if nz > 0.42:
        return 'three'
    if nz > 0.18:
        return 'side'
    return None


# eye stamps: 'E' lash / dark, 'e' iris, 'q' lower iris (lighter), 'l' highlight, 'w' sclera
EYES = {
    'open': {
        'front': (['EE', 'le', 'eq'], (1.0, 1.0)),
        'three': (['EE', 'le', 'eq'], (1.0, 1.0)),
        'squeeze': (['E', 'e', 'q'], (0.5, 1.0)),
        'side': (['E', 'l', 'e'], (0.5, 1.0)),
    },
    'blink': {
        'front': (['..', 'EE'], (1.0, 1.0)),
        'three': (['..', 'EE'], (1.0, 1.0)),
        'squeeze': (['.', 'E'], (0.5, 1.0)),
        'side': (['.', 'E'], (0.5, 1.0)),
    },
    'happy': {     # ^ ^ closed smile
        'front': (['..', '.E', 'E.'], (1.0, 1.0)),
        'three': (['..', '.E', 'E.'], (1.0, 1.0)),
        'squeeze': (['.', 'E', '.'], (0.5, 1.0)),
        'side': (['.', 'E', '.'], (0.5, 1.0)),
    },
    'shut': {      # > < squeezed (strain, hurt)
        'front': (['E.', '.E', 'E.'], (1.0, 1.0)),
        'three': (['E.', '.E', 'E.'], (1.0, 1.0)),
        'squeeze': (['.', 'E', '.'], (0.5, 1.0)),
        'side': (['E', '.', 'E'], (0.5, 1.0)),
    },
    'down': {      # looking down / sleepy: lid low
        'front': (['..', 'EE', 'eq'], (1.0, 1.0)),
        'three': (['..', 'EE', 'eq'], (1.0, 1.0)),
        'squeeze': (['.', 'E', 'q'], (0.5, 1.0)),
        'side': (['.', 'E', 'e'], (0.5, 1.0)),
    },
    'wide': {
        'front': (['EE', 'le', 'eq'], (1.0, 1.0)),
        'three': (['EE', 'le', 'eq'], (1.0, 1.0)),
        'squeeze': (['E', 'e', 'q'], (0.5, 1.0)),
        'side': (['E', 'l', 'e'], (0.5, 1.0)),
    },
}

MOUTHS = {
    'none': {},
    'closed': {'front': (['m'], (0.5, 0.5)), 'three': (['m'], (0.5, 0.5)), 'side': (['m'], (0.5, 0.5))},
    'open': {'front': (['M'], (0.5, 0.5)), 'three': (['M'], (0.5, 0.5)), 'side': (['M'], (0.5, 0.5))},
    'talk': {'front': (['MM'], (1.0, 0.5)), 'three': (['M'], (0.5, 0.5)), 'side': (['M'], (0.5, 0.5))},
    'shout': {'front': (['MM', 'MM'], (1.0, 0.5)), 'three': (['M', 'M'], (0.5, 0.5)), 'side': (['M', 'M'], (0.5, 0.5))},
    'chew': {'front': (['mm'], (1.0, 0.5)), 'three': (['m'], (0.5, 0.5)), 'side': (['m'], (0.5, 0.5))},
}


def mirror(grid):
    return [row[::-1] for row in grid]


def paint_face(img, px, feats, cmap, expr='open', mouth='closed', blush=True, extra=None, skin_ids=None,
               eye_dx=0.0):
    """feats: name -> (X, Y, depth, normal) with eyeL, eyeR (her left / right), mouth, blushL/R.
    The far eye of a turned face uses the squeezed stamp; the near one the full stamp."""
    eyes = EYES.get(expr, EYES['open'])
    eL, eR = feats.get('eyeL'), feats.get('eyeR')
    classes = {}
    for nm, f in (('eyeL', eL), ('eyeR', eR)):
        if f is None:
            continue
        classes[nm] = view_class(f[3][2])
    both = classes.get('eyeL') and classes.get('eyeR')
    for nm, f in (('eyeL', eL), ('eyeR', eR)):
        if f is None:
            continue
        vc = classes[nm]
        if vc is None:
            continue
        X, Y, d, n = f
        if vc == 'front':
            key = 'front'
        elif vc == 'three':
            key = 'three'
        else:
            # profile: one eye only (the near one); a squeezed far eye when both are visible
            key = 'squeeze' if both else 'side'
        if both and vc != 'front':
            # the eye nearer to the face's silhouette edge is the far one
            other = classes['eyeR' if nm == 'eyeL' else 'eyeL']
            if other == 'front' or (other == 'three' and vc == 'side'):
                key = 'squeeze'
        grid, anchor = eyes[key]
        # highlight toward the top-left: stamps are drawn for an eye on the viewer's right side of
        # the face; mirror for the viewer's left so the iris shading stays consistent
        if f[3][0] < -0.05 and key in ('side', 'squeeze'):
            grid = mirror(grid)
        stamp(img, px, X + eye_dx, Y, grid, cmap, anchor, depth=d)
    m = feats.get('mouth')
    if m is not None and mouth in MOUTHS:
        vc = view_class(m[3][2])
        if vc in MOUTHS[mouth]:
            grid, anchor = MOUTHS[mouth][vc]
            stamp(img, px, m[0], m[1], grid, cmap, anchor, depth=m[2], only_on=skin_ids)
    if blush:
        for nm in ('blushL', 'blushR'):
            b = feats.get(nm)
            if b is None:
                continue
            vc = view_class(b[3][2])
            if vc in ('front', 'three'):
                stamp(img, px, b[0], b[1], ['b'], cmap, (0.5, 0.5), depth=b[2], only_on=skin_ids)
    if extra:
        extra(img, px, feats)
