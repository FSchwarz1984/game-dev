#!/usr/bin/env python3
# Fetches and prepares the two UI fonts of the Godot project (both SIL OFL 1.1) into godot/art/fonts/:
#   python3 -I tools/godot/fetch_fonts.py <work_dir>
#
# 1. Pixel CJK font: Fusion Pixel Font 12px Proportional (TakWolf, OFL 1.1), simplified-Chinese
#    variant (zh_hans glyph forms; it also covers kana, including ゞ and 々). GitHub release assets are
#    blocked in this container, so it comes from the Fontsource npm package
#    @fontsource/fusion-pixel-12px-proportional-sc (one WOFF2 holding the whole font, 31k glyphs,
#    font version 2024.05.12). Shipped unchanged.
# 2. Vector CJK font: Noto Serif CJK SC Regular (Google/Adobe, OFL 1.1) from a sparse git clone of
#    github.com/notofonts/noto-cjk, subset to ASCII, Latin-1, general punctuation, CJK symbols, kana,
#    full-width forms, every hanzi in GB 2312 and every kanji in JIS X 0208 level 1 (about 9k glyphs),
#    saved as WOFF2. This is the alternative "vector" theme (pending the user's choice).
#
# Downloads go to <work_dir> (untrusted data; this script only reads font tables from it).
# Needs: npm, git, fontTools, and brotli importable under python3 -I (a --user install is not seen in
# isolated mode; here it was installed with: python3 -m pip install --break-system-packages brotli).
import os
import shutil
import subprocess
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "godot", "art", "fonts")
PIXEL_PKG = "@fontsource/fusion-pixel-12px-proportional-sc@5.3.0"
PIXEL_FILE = "package/files/fusion-pixel-12px-proportional-sc-latin-400-normal.woff2"
NOTO_REPO = "https://github.com/notofonts/noto-cjk"
NOTO_COMMIT = "f8d157532fbfaeda587e826d4cd5b21a49186f7c"  # 2024-09-19, the commit used on 2026-10-14


def run(cmd, cwd=None):
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd)


def charset():
    chars = set(chr(c) for c in range(0x20, 0x7F))
    chars |= set(chr(c) for c in range(0xA0, 0x100))
    for lo, hi in ((0x2000, 0x206F), (0x2190, 0x21FF), (0x2460, 0x24FF), (0x25A0, 0x25FF), (0x2600, 0x26FF),
                   (0x3000, 0x303F), (0x3040, 0x309F), (0x30A0, 0x30FF), (0x31F0, 0x31FF), (0xFF00, 0xFFEF)):
        chars |= set(chr(c) for c in range(lo, hi + 1))
    # GB 2312 hanzi: rows 0xB0-0xF7, cells 0xA1-0xFE
    for hi in range(0xB0, 0xF8):
        for lo in range(0xA1, 0xFF):
            try:
                chars.add(bytes([hi, lo]).decode("gb2312"))
            except UnicodeDecodeError:
                pass
    # JIS X 0208 level 1 kanji: Shift_JIS 0x889F-0x9872
    for hi in range(0x88, 0x99):
        for lo in list(range(0x40, 0x7F)) + list(range(0x80, 0xFD)):
            code = (hi << 8) | lo
            if 0x889F <= code <= 0x9872:
                try:
                    chars.add(bytes([hi, lo]).decode("shift_jis"))
                except UnicodeDecodeError:
                    pass
    return "".join(sorted(chars))


def main():
    if len(sys.argv) != 2:
        print(__doc__ if __doc__ else "usage: fetch_fonts.py <work_dir>")
        sys.exit(2)
    work = os.path.abspath(sys.argv[1])
    os.makedirs(work, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    # --- 1. Fusion Pixel (npm tarball)
    pix = os.path.join(work, "fusion-pixel")
    os.makedirs(pix, exist_ok=True)
    run(["npm", "pack", PIXEL_PKG, "--ignore-scripts", "--silent"], cwd=pix)
    tgz = [f for f in os.listdir(pix) if f.endswith(".tgz")][0]
    with tarfile.open(os.path.join(pix, tgz)) as t:
        woff2 = t.extractfile(PIXEL_FILE).read()
        lic = t.extractfile("package/LICENSE").read()
    with open(os.path.join(OUT, "fusion-pixel-12px-proportional-zh_hans.woff2"), "wb") as f:
        f.write(woff2)
    with open(os.path.join(OUT, "OFL-fusion-pixel.txt"), "wb") as f:
        f.write(lic)

    # --- 2. Noto Serif CJK SC (sparse clone, pinned commit), subset to WOFF2
    noto = os.path.join(work, "noto-cjk")
    if not os.path.isdir(noto):
        run(["git", "clone", "--filter=blob:none", "--sparse", "--no-checkout", NOTO_REPO, noto])
    run(["git", "-C", noto, "sparse-checkout", "set", "--no-cone",
         "/Serif/SubsetOTF/SC/NotoSerifSC-Regular.otf", "/Serif/LICENSE"])
    run(["git", "-C", noto, "fetch", "--depth", "1", "--filter=blob:none", "origin", NOTO_COMMIT])
    run(["git", "-C", noto, "checkout", NOTO_COMMIT])
    from fontTools import subset
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    opts.flavor = "woff2"
    font = subset.load_font(os.path.join(noto, "Serif/SubsetOTF/SC/NotoSerifSC-Regular.otf"), opts)
    sub = subset.Subsetter(opts)
    sub.populate(text=charset())
    sub.subset(font)
    subset.save_font(font, os.path.join(OUT, "noto-serif-sc-subset.woff2"), opts)
    shutil.copyfile(os.path.join(noto, "Serif/LICENSE"), os.path.join(OUT, "OFL-noto-serif-cjk.txt"))
    for f in sorted(os.listdir(OUT)):
        print(f, os.path.getsize(os.path.join(OUT, f)))


if __name__ == "__main__":
    main()
