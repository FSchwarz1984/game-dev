"""百々かさゝぎ's colours (sRGB albedo). Sampled from the user's original art (12 packs, A_01..A_36;
k-means over A_01: cream #f6ece2 / #e4d6d1, navy #3a3b5a / #39344a, hair #322b3d / #282231 /
#544356, red #9e3953) and set one step lighter than the art's mid-tones, because the albedo is what
the world's light multiplies (lit ~1.2x, shade ~0.7x with a cool turn)."""
from c3d.surf import hex_to_rgb as H

SKIN = H('#fbe3d2')
SKIN_DEEP = H('#f1cdbb')        # under the chin, inside the ears: baked as colour, not light
HAIR = H('#2e2539')
HAIR_DEEP = H('#211a2b')        # the underside and the inner layer of the back hair
CREAM = H('#f1e8dc')            # the haori, the hat's top
CREAM_EDGE = H('#ddd0c4')       # hems and the hat's rim edge
HAT = H('#e4d6b8')              # the sugegasa's sedge: a straw cream, warmer than the haori
NAVY = H('#3a3d60')             # kosode, pants, linings, the hat's underside
NAVY_DEEP = H('#25243a')        # jika-tabi (the art's near-black indigo boots)
SOLE = H('#a7a3a8')             # the boots' rubber soles
RED = H('#a63852')              # the sash and its bow, the hat's band
RED_DEEP = H('#8a2c44')
WHITE = H('#f4f0ea')            # obi, ankle bands, sandal thongs, the hair ties' white
STRAW = H('#cdb487')            # sandal soles
STRAW_DEEP = H('#b09468')
WOOD = H('#8a6a4c')             # the carrying frame (shoiko)
WOOD_DEEP = H('#6b5039')
ROPE = H('#c9b48e')
