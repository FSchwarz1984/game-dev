"""百々かさゝぎ's colours (sRGB albedo), round 5: the ChatGPT colour sheet (Tiangan_v2_kasasagi_colors.png:
main / shadow / highlight per material, sampled from the user's original art). The albedo is the
main colour; shadow and highlight colours are painted only where the design draws them (the jaw's
underside, hair strands, folds), the light does the rest."""
from c3d.surf import hex_to_rgb as H

# Round 6: the darks are set so that they land on the sheet's main colours on screen in the game's
# light and grade at 10:30 (measured: an albedo comes out about 1.6x brighter in the darks, reds
# more saturated: navy #33395b rendered #515b8d, red #7e2840 rendered #d8437b). Targets on screen:
# hair #3e344a, navy #33395b, lining #252c4b, trousers #38344b, boots #332d3b, red #9b324e.
HAIR = H('#27202f')
HAIR_DEEP = H('#1a1520')        # between the sheet's strands, the cap's underside
HAIR_HI = H('#3b3247')          # strand highlights (on screen about the GPT highlight #5f5071)
SKIN = H('#fce4d2')
SKIN_DEEP = H('#ecc0ab')        # the jaw's underside, the neck, inside the ears
CREAM = H('#f9efe6')            # the outer kimono (haori)
CREAM_DEEP = H('#dfd5d3')       # its painted folds and inner side
HAT = H('#f7eadc')              # the sugegasa's top (ivory)
HAT_DEEP = H('#ddd1c7')
NAVY_LINING = H('#171b2f')      # the hat's underside, the sleeves' lining
NAVY = H('#20243a')             # the kosode
NAVY_DEEP = H('#161829')
TROUSERS = H('#23202f')         # the lantern trousers (a violet navy)
TROUSERS_DEEP = H('#14121b')
BOOTS = H('#201c25')
BOOTS_DEEP = H('#15141b')
SOLE = H('#d5c8c0')
RED = H('#5c1d2b')              # the sash, the bow, the collar, the hat's band
RED_DEEP = H('#45151f')
RED_HI = H('#6e2433')
WHITE = H('#f8efe5')            # obi, hair ties, ankle bands
WHITE_DEEP = H('#d9d1cd')
# the carrying frame (shoiko)
WOOD = H('#8a6a4c')
WOOD_DEEP = H('#6b5039')
ROPE = H('#c9b48e')
STRAW = H('#cdb487')
STRAW_DEEP = H('#b09468')
NAVY_LIGHT = H('#454464')
