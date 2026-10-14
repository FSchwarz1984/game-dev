"""Bake the ink inside her hat (本来無東西　何処有南北) into a small pixel layer.

The brush font is Yuji Boku (SIL Open Font License 1.1, Google Fonts); it is used only to
draw these ten characters once, so the game needs no font at runtime and the strokes are
snapped to hard pixels like the rest of the pixel art. Output: assets/insets/hat-ink.png,
a 320x180 RGBA layer aligned with the hat insert in src/story/inset.js.

usage: python3 tools/story/hat_ink.py path/to/YujiBoku.ttf
"""
import sys, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 320, 180
CX, CY = W // 2 + 6, H // 2 + 4
COLS = ['本来無東西', '何処有南北']   # read right to left
SIZE, STEP = 27, 26

font = ImageFont.truetype(sys.argv[1], SIZE * 3)
rnd = random.Random(7)
big = Image.new('L', (W * 3, H * 3), 0)
d = ImageDraw.Draw(big)
for ci, col in enumerate(COLS):
    x = CX + 47 - ci * 96
    for k, ch in enumerate(col):
        y = CY - 52 + k * STEP
        # a hand is never quite on the grid
        jx, jy = rnd.uniform(-1.2, 1.2), rnd.uniform(-1, 1)
        glyph = Image.new('L', (SIZE * 4, SIZE * 4), 0)
        ImageDraw.Draw(glyph).text((SIZE * 2, SIZE * 2), ch, font=font, fill=255, anchor='mm')
        glyph = glyph.rotate(rnd.uniform(-3, 3), resample=Image.BICUBIC)
        big.paste(glyph, (int((x + jx) * 3 - SIZE * 2), int((y + jy) * 3 - SIZE * 2)), glyph)
small = big.resize((W, H), Image.BOX)
soak = small.filter(ImageFilter.MaxFilter(3))
out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
px, sp, op = small.load(), soak.load(), out.load()
for y in range(H):
    for x in range(W):
        a = px[x, y]
        if a > 120:
            op[x, y] = (24, 17, 21, 238)          # the stroke
        elif a > 38:
            op[x, y] = (36, 25, 26, 190)          # its thin edge
        elif sp[x, y] > 150:
            op[x, y] = (58, 40, 34, 70)           # ink soaked into the straw beside it
out.save(sys.argv[2] if len(sys.argv) > 2 else 'assets/insets/hat-ink.png')
print('ok')
