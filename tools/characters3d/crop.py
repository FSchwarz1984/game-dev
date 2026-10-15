"""Crops native lab frames around the character and enlarges them with nearest neighbour.
    python3 -I tools/characters3d/crop.py OUT.png IN.png [IN2.png ...] [--box W H] [--dy N] [--scale S] [--cols N]
The lab's camera keeps her chest at the frame's centre; --dy moves the box (native px, down +)."""
import sys
from PIL import Image


def main():
    a = sys.argv[1:]
    w, h, dy, scale, cols = 96, 96, 4, 4, 0
    files = []
    i = 0
    while i < len(a):
        if a[i] == '--box':
            w, h = int(a[i + 1]), int(a[i + 2])
            i += 3
            continue
        if a[i] == '--dy':
            dy = int(a[i + 1])
            i += 2
            continue
        if a[i] == '--scale':
            scale = int(a[i + 1])
            i += 2
            continue
        if a[i] == '--cols':
            cols = int(a[i + 1])
            i += 2
            continue
        files.append(a[i])
        i += 1
    out, ins = files[0], files[1:]
    tiles = []
    for f in ins:
        im = Image.open(f).convert('RGB')
        cx, cy = im.width // 2, im.height // 2 + dy
        box = (cx - w // 2, cy - h // 2, cx - w // 2 + w, cy - h // 2 + h)
        tiles.append(im.crop(box).resize((w * scale, h * scale), Image.NEAREST))
    cols = cols or len(tiles)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * w * scale + (cols - 1) * 4, rows * h * scale + (rows - 1) * 4), (24, 24, 28))
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % cols) * (w * scale + 4), (k // cols) * (h * scale + 4)))
    sheet.save(out)


main()
