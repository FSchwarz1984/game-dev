"""Overlap check for a script draft (G5R3-12, second blind review of v5).

Two checks:

1. Japanese draft vs the research notes. Every Japanese sentence and quotation in
   docs/knowledge/26 and docs/knowledge/27 is collected (bracketed 「」『』 text with kana,
   blockquote lines with kana, and any other run of Japanese text with kana). Every
   Japanese line of the draft (speech inside 「」 and the stage directions in （）, both
   taken from the "**日文原稿**" blocks) is compared with them. After whitespace and
   punctuation are removed, a shared continuous fragment of N characters or more
   (default 7) is flagged, with the longest shared fragment and where it comes from.

2. Chinese draft vs the fourth draft. Every Chinese line of the draft ("**中文演出稿**"
   blocks) is compared with every line of script-04 (which has only Chinese). Lines that
   are the same after punctuation is removed are counted, with and without the speaker.

Usage:
  python3 -I tools/script/overlap.py DRAFT [--refs K26 K27] [--v4 V4] [--min 7]
                                      [--prev-ja OLD_DRAFT]
Defaults: refs = docs/knowledge/26-human-dialogue-japanese.md and
docs/knowledge/27-japanese-literature-close-reading.md; v4 = docs/design/script-04-draft.md.
--prev-ja also reports which Japanese lines of DRAFT are the same as a Japanese line of
an older draft (for example the fifth draft before it was replaced).
"""
import argparse
import re
import sys
import unicodedata
from collections import defaultdict

KANA = re.compile(r"[ぁ-ゖァ-ヺゝゞヽヾ]")
QUOTE = re.compile(r"[「『]([^「」『』]*)[」』]")
# a run of Japanese-looking text: kana, kanji, iteration marks, the long-vowel mark and
# Japanese punctuation. Chinese text is caught too; only runs with kana are kept.
JRUN = re.compile(r"[ぁ-ゖァ-ヺーゝゞヽヾ一-鿿"
                  r"々〆〇、。！？…—―〜～・「」『』　]+")
SPEECH = re.compile(r"^>\s*([^「：（]+?)(（[^）]*）)?「(.*)$")
CN_LINE = re.compile(r"^>\s*([^：（「]+?)(（[^）]*）)?：「(.*)」\s*$")


def norm(s):
    """Letters and digits only: drops whitespace, punctuation and symbols."""
    return "".join(c for c in s if unicodedata.category(c)[0] in "LN")


def first_quote(s):
    """Text inside the first 「…」 of s (s starts just after the opening bracket)."""
    depth = 1
    out = []
    for c in s:
        if c == "「":
            depth += 1
        elif c == "」":
            depth -= 1
            if depth == 0:
                break
        out.append(c)
    return "".join(out)


def ref_segments(paths):
    segs = []
    for path in paths:
        for no, raw in enumerate(open(path, encoding="utf-8"), 1):
            line = raw.rstrip("\n")
            found = []
            for m in QUOTE.finditer(line):
                if KANA.search(m.group(1)):
                    found.append(m.group(1))
            body = line.lstrip()
            if body.startswith(">") and KANA.search(body):
                found.append(body.lstrip("> "))
            for m in JRUN.finditer(line):
                if KANA.search(m.group(0)):
                    found.append(m.group(0))
            for f in found:
                n = norm(f)
                if n:
                    segs.append((path, no, f.strip(), n))
    return segs


def draft_japanese(path):
    """Japanese speech and stage directions from the **日文原稿** blocks."""
    out = []
    scene = ""
    in_ja = False
    for no, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.rstrip("\n")
        if line.startswith("### "):
            scene = line[4:].strip()
        if line.startswith("**日文原稿**"):
            in_ja = True
            continue
        if line.startswith("**") or line.startswith("## ") or line.startswith("### "):
            in_ja = False      # any other bold heading (场外说明, 中文演出稿) ends the block
            continue
        if not in_ja:
            continue
        s = line.strip()
        m = SPEECH.match(s)
        if m:
            text = first_quote(m.group(3))
            out.append((scene, no, "台词", m.group(1).strip(), text, norm(text)))
            continue
        if s.startswith("（") and s.endswith("）"):
            text = s[1:-1]
            if KANA.search(text):
                out.append((scene, no, "舞台说明", "", text, norm(text)))
    return out


def cn_lines(path, only_cn_blocks):
    out = []
    in_cn = not only_cn_blocks
    for no, raw in enumerate(open(path, encoding="utf-8"), 1):
        line = raw.rstrip("\n")
        if only_cn_blocks:
            if line.startswith("**中文演出稿**"):
                in_cn = True
                continue
            if line.startswith("**日文原稿**") or line.startswith("## ") or line.startswith("### "):
                in_cn = False
                continue
        else:
            if line.startswith("## 13."):
                break
        if not in_cn:
            continue
        m = CN_LINE.match(line.strip())
        if m:
            out.append((no, m.group(1).strip(), m.group(3), norm(m.group(3))))
    return out


def longest_common(a, b):
    best = 0
    best_end = 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                v = prev[j - 1] + 1
                cur[j] = v
                if v > best:
                    best = v
                    best_end = i
        prev = cur
    return a[best_end - best:best_end]


def check_japanese(draft, refs, n):
    grams = defaultdict(set)
    for k, (_, _, _, rn) in enumerate(refs):
        for i in range(len(rn) - n + 1):
            grams[rn[i:i + n]].add(k)
    flagged = []
    for item in draft:
        dn = item[5]
        hits = set()
        for i in range(len(dn) - n + 1):
            hits |= grams.get(dn[i:i + n], set())
        if not hits:
            continue
        best = ""
        src = None
        for k in hits:
            frag = longest_common(dn, refs[k][3])
            if len(frag) > len(best):
                best, src = frag, refs[k]
        flagged.append((item, best, src))
    return flagged


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--refs", nargs="+", default=[
        "docs/knowledge/26-human-dialogue-japanese.md",
        "docs/knowledge/27-japanese-literature-close-reading.md"])
    ap.add_argument("--v4", default="docs/design/script-04-draft.md")
    ap.add_argument("--min", type=int, default=7)
    ap.add_argument("--prev-ja", default=None)
    a = ap.parse_args()

    refs = ref_segments(a.refs)
    draft = draft_japanese(a.draft)
    speech = [d for d in draft if d[2] == "台词"]
    print(f"## 1. 日文稿 vs knowledge/26、27（连续 {a.min} 字以上，去掉空白和标点）")
    print(f"参照片段 {len(refs)} 条；日文稿台词 {len(speech)} 句，舞台说明 {len(draft) - len(speech)} 条")
    flagged = check_japanese(draft, refs, a.min)
    fs = [f for f in flagged if f[0][2] == "台词"]
    fd = [f for f in flagged if f[0][2] != "台词"]
    print(f"标出：台词 {len(fs)} 句，舞台说明 {len(fd)} 条")
    for (scene, no, kind, who, text, _), frag, src in flagged:
        where = f"{src[0].split('/')[-1]}:{src[1]}" if src else "?"
        print(f"- [{kind}] l.{no} {scene} {who}「{text}」 共有「{frag}」({len(frag)} 字) ← {where}「{src[2][:40]}」")

    if a.prev_ja:
        prev = draft_japanese(a.prev_ja)
        pset = {d[5] for d in prev if d[2] == "台词"}
        same = [d for d in speech if d[5] in pset]
        print(f"\n## 1b. 日文稿台词和 {a.prev_ja} 的日文台词相同（去掉标点）：{len(same)} / {len(speech)}")
        for d in same:
            print(f"- l.{d[1]} {d[3]}「{d[4]}」")

    v4 = cn_lines(a.v4, only_cn_blocks=False)
    new = cn_lines(a.draft, only_cn_blocks=True)
    v4_pairs = {(w, t) for _, w, _, t in v4}
    v4_texts = {t for _, _, _, t in v4}
    same_pair = [x for x in new if (x[1], x[3]) in v4_pairs]
    same_text = [x for x in new if x[3] in v4_texts]
    print(f"\n## 2. 中文演出稿 vs 第四版（去掉标点后一字不差）")
    print(f"第四版 {len(v4)} 句；新稿 {len(new)} 句")
    print(f"说话人和字都相同：{len(same_pair)} 句；只看字（不管谁说）：{len(same_text)} 句")
    for no, who, text, _ in same_text:
        mark = "" if (who, norm(text)) in v4_pairs else "（第四版是别人说的）"
        print(f"- l.{no} {who}：「{text}」{mark}")


if __name__ == "__main__":
    main()
