"""百々かさゝぎ's colours (sRGB albedo), round 5: the ChatGPT colour sheet (Tiangan_v2_kasasagi_colors.png:
main / shadow / highlight per material, sampled from the user's original art). The albedo is the
main colour; shadow and highlight colours are painted only where the design draws them (the jaw's
underside, hair strands, folds), the light does the rest."""
from c3d.surf import hex_to_rgb as H

HAIR = H('#3e344a')
HAIR_DEEP = H('#2a2133')        # between the sheet's strands, the cap's underside (GPT shadow #231a28, a step up)
HAIR_HI = H('#5f5071')          # strand highlights (GPT highlight)
SKIN = H('#fce4d2')
SKIN_DEEP = H('#ecc0ab')        # the jaw's underside, the neck, inside the ears
CREAM = H('#f9efe6')            # the outer kimono (haori)
CREAM_DEEP = H('#dfd5d3')       # its painted folds and inner side
HAT = H('#f7eadc')              # the sugegasa's top (ivory)
HAT_DEEP = H('#ddd1c7')
NAVY_LINING = H('#252c4b')      # the hat's underside, the sleeves' lining
NAVY = H('#33395b')             # the kosode
NAVY_DEEP = H('#232741')
TROUSERS = H('#38344b')         # the lantern trousers (a violet navy)
TROUSERS_DEEP = H('#1e1c2a')
BOOTS = H('#332d3b')
BOOTS_DEEP = H('#22202b')
SOLE = H('#d5c8c0')
# the reds a step deeper than the sheet's mid-tone: a red albedo in full sun, after the frame's grade,
# came out hot pink (#fc4e8b measured); these land near the sheet's crimson on screen
RED = H('#7e2840')              # the sash, the bow, the collar, the hat's band
RED_DEEP = H('#5e1c30')
RED_HI = H('#9b324e')
WHITE = H('#f8efe5')            # obi, hair ties, ankle bands
WHITE_DEEP = H('#d9d1cd')
# the carrying frame (shoiko)
WOOD = H('#8a6a4c')
WOOD_DEEP = H('#6b5039')
ROPE = H('#c9b48e')
STRAW = H('#cdb487')
STRAW_DEEP = H('#b09468')
NAVY_LIGHT = H('#454464')
