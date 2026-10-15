#!/usr/bin/env python3
# Copies the shared art into the Godot project (Godot only loads files under godot/):
#   python3 -I tools/godot/sync_assets.py
# - assets/sprites/*.png -> godot/art/sprites/ (albedo + normal sheets from tools/art/sprite3d/build.py)
#   and their layout assets/sprites/characters.json -> godot/actors/characters.json (the old
#   src/art/characters.data.js is only read when that file is missing). Sheets that the layout no
#   longer names are removed from godot/art/sprites (with their .import files).
# - Dialogue portraits: assets/portraits/pixel/<who>*.png when the pixel portraits exist
#   (docs/knowledge/13-pixel-portraits.md); otherwise a crude placeholder cut from
#   assets/portraits/<who>_bust.webp (internal checking only, never shipped as art).
# - godot/icon.png: a plain placeholder app icon.
# Re-run whenever those sources change. Only reads and writes inside the repository.
# `--sprites-only` copies just the sprite sheets and their layout (tools/art/sprite3d uses it);
# `--portraits-only` copies just the dialogue portraits (tools/art/portraits4 uses it).
import json
import os
import shutil

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GD = os.path.join(ROOT, "godot")
PORTRAIT = (128, 128)  # native px, as the pixel portraits (v4, knowledge/13 §10)


def sprites():
    out = os.path.join(GD, "art", "sprites")
    os.makedirs(out, exist_ok=True)
    src = os.path.join(ROOT, "assets", "sprites")
    layout = os.path.join(src, "characters.json")
    if os.path.isfile(layout):
        data = json.load(open(layout, encoding="utf-8"))
    else:
        js = open(os.path.join(ROOT, "src", "art", "characters.data.js"), encoding="utf-8").read()
        start = js.index("export const CHARACTER_DATA = ") + len("export const CHARACTER_DATA = ")
        data = json.loads(js[start:js.rindex("}") + 1])
    wanted = set()
    for c in data.values():
        for sd in c.get("sheets", {}).values():
            wanted |= {sd["file"] + ".png", sd["file"] + "_n.png"}
    for f in sorted(wanted):
        shutil.copyfile(os.path.join(src, f), os.path.join(out, f))
    for f in sorted(os.listdir(out)):
        base = f[:-len(".import")] if f.endswith(".import") else f
        if base.endswith(".png") and base not in wanted:
            os.remove(os.path.join(out, f))
            print("removed stale", f)
    with open(os.path.join(GD, "actors", "characters.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("sprites:", len(os.listdir(out)), "files; characters:", ", ".join(data))


def portraits():
    """Pixel portraits (128x128 per expression, docs/knowledge/13-pixel-portraits.md §10) when present:
    assets/portraits/pixel/<who>/<expression>.png -> godot/art/portraits/<who>/<expression>.png.
    Portraits that are no longer in the source folder are removed (with their .import files).
    Without them, one crude placeholder per character is cut from <who>_bust.webp (internal only)."""
    out = os.path.join(GD, "art", "portraits")
    os.makedirs(out, exist_ok=True)
    pixel = os.path.join(ROOT, "assets", "portraits", "pixel")
    for who in ("tsuzumi", "saji", "shione"):
        src = os.path.join(pixel, who)
        dst_dir = os.path.join(out, who)
        os.makedirs(dst_dir, exist_ok=True)
        if os.path.isdir(src):
            n = 0
            wanted = {f for f in os.listdir(src) if f.endswith(".png")}
            for f in sorted(wanted):
                shutil.copyfile(os.path.join(src, f), os.path.join(dst_dir, f))
                n += 1
            for f in sorted(os.listdir(dst_dir)):
                base = f[:-len(".import")] if f.endswith(".import") else f
                if base.endswith(".png") and base not in wanted:
                    os.remove(os.path.join(dst_dir, f))
                    print("removed stale portrait", who, f)
            print("portraits", who, n, "expressions <-", os.path.relpath(src, ROOT))
            continue
        im = Image.open(os.path.join(ROOT, "assets", "portraits", who + "_bust.webp")).convert("RGBA")
        w, h = im.size
        cw = int(w * 0.7)
        ch = int(cw * PORTRAIT[1] / PORTRAIT[0])
        x0 = (w - cw) // 2
        im = im.crop((x0, 0, x0 + cw, min(h, ch))).resize(PORTRAIT, Image.LANCZOS)
        rgb = im.convert("RGB").quantize(colors=24, method=Image.Quantize.MEDIANCUT).convert("RGBA")
        rgb.putalpha(im.getchannel("A").point(lambda a: 255 if a > 96 else 0))
        rgb.save(os.path.join(dst_dir, "neutral.png"))
        print("portrait", who, "<- PLACEHOLDER from", who + "_bust.webp")
    man = os.path.join(pixel, "portraits.json")
    if os.path.isfile(man):
        shutil.copyfile(man, os.path.join(out, "portraits.json"))


def icon():
    n = 192
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, n - 8, n - 8), fill=(30, 28, 38, 255))
    d.ellipse((52, 52, n - 52, n - 52), outline=(214, 182, 120, 255), width=10)
    img.save(os.path.join(GD, "icon.png"))


if __name__ == "__main__":
    import sys
    if "--portraits-only" in sys.argv:     # the portrait builder syncs only its own images
        portraits()
    else:
        sprites()
        if "--sprites-only" not in sys.argv:   # the sprite generator syncs only its own sheets
            portraits()
            icon()
