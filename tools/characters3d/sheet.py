"""Contact sheet of images (python3 -I tools/characters3d/sheet.py OUT.png IN1.png IN2.png ... [--scale N]
[--cols N] [--label]): pastes them in a grid; --scale enlarges with nearest neighbour (native pixels)."""
import sys
from PIL import Image, ImageDraw


def main():
    args = sys.argv[1:]
    scale, cols, label = 1, 0, False
    files = []
    i = 0
    while i < len(args):
        if args[i] == '--scale':
            scale = int(args[i + 1])
            i += 2
            continue
        if args[i] == '--cols':
            cols = int(args[i + 1])
            i += 2
            continue
        if args[i] == '--label':
            label = True
            i += 1
            continue
        files.append(args[i])
        i += 1
    out, ins = files[0], files[1:]
    ims = [Image.open(f).convert('RGB') for f in ins]
    ims = [im.resize((im.width * scale, im.height * scale), Image.NEAREST) for im in ims]
    cols = cols or len(ims)
    rows = (len(ims) + cols - 1) // cols
    w = max(im.width for im in ims)
    h = max(im.height for im in ims) + (14 if label else 0)
    sheet = Image.new('RGB', (cols * w + (cols - 1) * 4, rows * h + (rows - 1) * 4), (40, 40, 46))
    d = ImageDraw.Draw(sheet)
    for k, im in enumerate(ims):
        x = (k % cols) * (w + 4)
        y = (k // cols) * (h + 4)
        sheet.paste(im, (x, y))
        if label:
            name = ins[k].rsplit('/', 1)[-1].rsplit('.', 1)[0]
            d.text((x + 3, y + im.height + 1), name, fill=(230, 230, 230))
    sheet.save(out)


main()
