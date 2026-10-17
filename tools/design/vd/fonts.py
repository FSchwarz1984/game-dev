"""Fonts for the drawings: Noto Serif SC (titles, 明朝体 in spirit) and Noto Sans SC (notes), both
SIL Open Font License 1.1. They are NOT in the repository. Get them from npm as tarballs (npm pack or a
plain download; never `npm install`), unpack into an empty directory outside the repo, and pass that
directory with --fonts. Every file is checked against the SHA-256 below before use.

Re-fetch (the same bytes):
  mkdir -p FONTDIR/serif FONTDIR/sans && cd FONTDIR
  curl -sSLo serif.tgz https://registry.npmjs.org/@expo-google-fonts/noto-serif-sc/-/noto-serif-sc-0.4.4.tgz
  curl -sSLo sans.tgz  https://registry.npmjs.org/@expo-google-fonts/noto-sans-sc/-/noto-sans-sc-0.4.4.tgz
  sha256sum serif.tgz sans.tgz        # must match TARBALLS below
  tar -xzf serif.tgz -C serif && tar -xzf sans.tgz -C sans
(the TTFs land in FONTDIR/serif/package/... and FONTDIR/sans/package/...; this module searches the
directory for the file names below.)

The drawings embed a subset (only the glyphs a drawing uses) as WOFF2 in the SVG's @font-face. The
family names in the SVG are neutral ("VD Serif", "VD Sans"); the OFL notice is copied into each SVG.
"""
from __future__ import annotations

import base64
import hashlib
import io
from pathlib import Path

TARBALLS = {
    "serif": {
        "package": "@expo-google-fonts/noto-serif-sc", "version": "0.4.4",
        "url": "https://registry.npmjs.org/@expo-google-fonts/noto-serif-sc/-/noto-serif-sc-0.4.4.tgz",
        "sha256": "38b2ca4e45b33e22ad74c68d1e3b32c584ffe3509293ba1735b5248d66864214",
        "integrity": "sha512-RIPZykLmhdnqjaYuIVNA7btxvd8OwKNK1CSqLiszCOVJAIhkud9cSrOoecYiwU3HetKGaHEZWzD2jbWd43D6mA==",
    },
    "sans": {
        "package": "@expo-google-fonts/noto-sans-sc", "version": "0.4.4",
        "url": "https://registry.npmjs.org/@expo-google-fonts/noto-sans-sc/-/noto-sans-sc-0.4.4.tgz",
        "sha256": "e18cd1a1fbb95d7c25fc133406dfd1b2b25d718835b51ec23d556dc4b11578a8",
        "integrity": "sha512-LF4+p6xdtgUArufW0K+l9/FeDiXrW8FcEkEbOPIUC5ZnPupeFVA6yY9qCZ0sBrdAeLdlusDhv0R7q2x3onXo3w==",
    },
}

# family key -> (file name, sha256 of the TTF, css family, weight)
FILES = {
    "serif400": ("NotoSerifSC_400Regular.ttf", "c358a69de3df5f423a8946a7b03e3126fb6ba116f1130a463455b4e39e1f0742", "VD Serif", 400),
    "serif600": ("NotoSerifSC_600SemiBold.ttf", "5d19e0f438d4a30371f584d34a87c9232dba0a85237db63fe5337fe743487def", "VD Serif", 600),
    "serif700": ("NotoSerifSC_700Bold.ttf", "9c6a2ba736e4b499c84f65ce366bd3625c0401885fd3e585ace50fb738b96ff6", "VD Serif", 700),
    "sans400": ("NotoSansSC_400Regular.ttf", "d45f67f0a7c0ca3f256950777ce6a61cc7ce5f9696d02900cbbaac25f8aa7d16", "VD Sans", 400),
    "sans500": ("NotoSansSC_500Medium.ttf", "b30853d205f3ecdde938b1488c735ee15a2e870d31331b992fdc53971e23ec4a", "VD Sans", 500),
    "sans700": ("NotoSansSC_700Bold.ttf", "9a38ae0ab28cd5a256f9ea8e00dedc688aac17f7915fcb000572990afa956b96", "VD Sans", 700),
}

LICENSE = ("Fonts: Noto Serif SC, (c) 2017-2024 Adobe (http://www.adobe.com/); Noto Sans SC, (c) 2014-2021 Adobe "
           "(http://www.adobe.com/), with Reserved Font Name 'Source'. Both under the SIL Open Font License 1.1 "
           "(https://openfontlicense.org). Subsets are embedded under the neutral family names VD Serif / VD Sans "
           "(no Reserved Font Name used). Source: npm @expo-google-fonts/noto-serif-sc and "
           "@expo-google-fonts/noto-sans-sc 0.4.4.")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Fonts:
    def __init__(self, fontdir):
        self.dir = Path(fontdir)
        self.paths = {}
        for key, (name, digest, fam, wt) in FILES.items():
            hits = list(self.dir.rglob(name))
            if not hits:
                raise SystemExit("font %s not found under %s (see vd/fonts.py for how to fetch it)" % (name, self.dir))
            p = hits[0]
            got = sha256(p)
            if got != digest:
                raise SystemExit("font %s: sha256 %s, expected %s" % (p, got, digest))
            self.paths[key] = p
        self._cache = {}

    def woff2(self, key, text):
        from fontTools import subset
        from fontTools.ttLib import TTFont
        chars = "".join(sorted(set(text) | set(" 0123456789.-–—:/()[]·×%,，。、；：（）「」『』…‘’“”")))
        ck = (key, chars)
        if ck in self._cache:
            return self._cache[ck]
        f = TTFont(self.paths[key])
        opts = subset.Options()
        opts.flavor = "woff2"
        opts.layout_features = ["*"]
        opts.name_IDs = ["*"]
        opts.notdef_outline = True
        opts.hinting = False
        s = subset.Subsetter(opts)
        s.populate(text=chars)
        s.subset(f)
        b = io.BytesIO()
        f.flavor = "woff2"
        f.save(b)
        out = base64.b64encode(b.getvalue()).decode("ascii")
        self._cache[ck] = out
        return out

    def css(self, text_by_key):
        rules = []
        for key, text in text_by_key.items():
            if not text:
                continue
            name, _, fam, wt = FILES[key]
            rules.append('@font-face{font-family:"%s";font-weight:%d;src:url(data:font/woff2;base64,%s) format("woff2");}'
                         % (fam, wt, self.woff2(key, text)))
        return "\n".join(rules)
