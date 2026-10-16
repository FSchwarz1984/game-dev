"""Overlap check for a script draft (G5R3-12; second and third blind reviews of v5).

Two checks:

1. Japanese draft vs the research notes. Every Japanese sentence and quotation in
   docs/knowledge/26 and docs/knowledge/27 is collected (bracketed 「」『』 text with kana,
   blockquote lines with kana, and any other run of Japanese text with kana). Every
   Japanese line of the draft (speech inside 「」 and the stage directions in （）, both
   taken from the "**日文原稿**" blocks) is compared with them. After whitespace and
   punctuation are removed, a shared continuous fragment of N characters or more
   (default 7) is flagged, with the longest shared fragment and where it comes from.

   A second pass folds notation before comparing (numeral + counter and a few common
   words written in kanji become kana, 一人 -> ひとり, 一つ -> ひとつ, 今朝 -> けさ ...;
   katakana becomes hiragana), so a reference sentence that comes back in a different
   spelling is caught too. A third pass (--sim, default 0.4) lists draft lines made of
   pieces of one reference sentence: after folding, the shared blocks of 3 characters or
   more add up to at least 4 characters and cover --sim of the shorter side. It catches a
   sentence frame reused with one word swapped, which a long-substring check misses. It is
   a reading list, not a verdict; grammatical endings land there too.

2. Chinese draft vs the fourth draft. Every Chinese line of the draft ("**中文演出稿**"
   blocks) is compared with every line of script-04 (which has only Chinese). Lines that
   are the same after punctuation is removed are counted, with and without the speaker.
   Near-identical lines are counted too: for each new line, the best
   difflib.SequenceMatcher ratio against any fourth-draft line, after punctuation is
   removed; lines with --near <= ratio < 1 are listed (default 0.75).

Usage:
  python3 -I tools/script/overlap.py DRAFT [--refs K26 K27] [--v4 V4] [--min 7]
                                      [--prev-ja OLD_DRAFT] [--sim 0.4] [--near 0.75]
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
from difflib import SequenceMatcher

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


# Notation variants folded to one spelling for the second pass. Longest keys first.
FOLD = [
    ("お一人", "おひとり"), ("一人", "ひとり"), ("二人", "ふたり"),
    ("一つ", "ひとつ"), ("二つ", "ふたつ"), ("三つ", "みっつ"), ("四つ", "よっつ"),
    ("五つ", "いつつ"), ("六つ", "むっつ"), ("七つ", "ななつ"), ("八つ", "やっつ"),
    ("九つ", "ここのつ"), ("一本", "いっぽん"), ("一度", "いちど"), ("一晩", "ひとばん"),
    ("今朝", "けさ"), ("昨夜", "ゆうべ"), ("今年", "ことし"), ("今日", "きょう"),
    ("今夜", "こんや"), ("明日", "あした"), ("何処", "どこ"), ("誰", "だれ"),
    ("下さ", "くださ"), ("頂", "いただ"), ("戴", "いただ"), ("致", "いた"), ("御", "お"),
    ("降り", "おり"), ("下り", "おり"), ("帰", "かえ"), ("戻", "もど"),
    ("食べ", "たべ"), ("食う", "くう"), ("食っ", "くっ"), ("一杯", "いっぱい"),
]


def fold(n):
    """Second-pass spelling: katakana to hiragana, then the FOLD table."""
    n = "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in n)
    for a, b in FOLD:
        n = n.replace(a, b)
    return n


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


def check_japanese(draft, refs, n, key=lambda x: x):
    rkeys = [key(r[3]) for r in refs]
    grams = defaultdict(set)
    for k, rn in enumerate(rkeys):
        for i in range(len(rn) - n + 1):
            grams[rn[i:i + n]].add(k)
    flagged = []
    for item in draft:
        dn = key(item[5])
        hits = set()
        for i in range(len(dn) - n + 1):
            hits |= grams.get(dn[i:i + n], set())
        if not hits:
            continue
        best = ""
        src = None
        for k in hits:
            frag = longest_common(dn, rkeys[k])
            if len(frag) > len(best):
                best, src = frag, refs[k]
        flagged.append((item, best, src))
    return flagged


def similar_japanese(speech, refs, threshold, block=3, shared_min=4):
    """Draft speech lines built from pieces of one reference sentence.

    After folding, the matching blocks of `block` characters or more between a draft line
    and a reference segment (both at least 6 characters) are added up; coverage is that
    sum over the shorter of the two. Lines whose best coverage is >= threshold and share
    at least `shared_min` characters are listed. The list is for reading, not a verdict:
    grammatical endings (〜ません, 〜ました) also land here.
    """
    cands = [(r, fold(r[3])) for r in refs if len(r[3]) >= 6]
    out = []
    for item in speech:
        dn = fold(item[5])
        if len(dn) < 6:
            continue
        best = None
        for r, rn in cands:
            sm = SequenceMatcher(None, dn, rn, autojunk=False)
            shared = sum(b.size for b in sm.get_matching_blocks() if b.size >= block)
            if shared < shared_min:
                continue
            cov = shared / min(len(dn), len(rn))
            if best is None or cov > best[0]:
                best = (cov, shared, r)
        if best and best[0] >= threshold:
            out.append((best[0], best[1], item, best[2]))
    out.sort(key=lambda x: -x[0])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--refs", nargs="+", default=[
        "docs/knowledge/26-human-dialogue-japanese.md",
        "docs/knowledge/27-japanese-literature-close-reading.md"])
    ap.add_argument("--v4", default="docs/design/script-04-draft.md")
    ap.add_argument("--min", type=int, default=7)
    ap.add_argument("--prev-ja", default=None)
    ap.add_argument("--sim", type=float, default=0.4)
    ap.add_argument("--near", type=float, default=0.75)
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

    literal = {f[0][1] for f in flagged}
    folded = check_japanese(draft, refs, a.min, key=fold)
    extra = [f for f in folded if f[0][1] not in literal]
    print(f"\n## 1c. 折算写法后（汉字数词、常用词改假名，片假名改平假名）再比，连续 {a.min} 字以上")
    print(f"标出：台词 {sum(1 for f in folded if f[0][2] == '台词')} 句，舞台说明 "
          f"{sum(1 for f in folded if f[0][2] != '台词')} 条；其中字面比时没标出的 {len(extra)} 条")
    for (scene, no, kind, who, text, _), frag, src in extra:
        where = f"{src[0].split('/')[-1]}:{src[1]}" if src else "?"
        print(f"- [{kind}] l.{no} {scene} {who}「{text}」 共有「{frag}」({len(frag)} 字) ← {where}「{src[2][:40]}」")

    sims = similar_japanese(speech, refs, a.sim)
    print(f"\n## 1d. 拼件相似（折算写法后，和同一条参照共有的 3 字以上片段合计 ≥ 4 字，"
          f"占较短一方的 {a.sim:.0%} 以上；供人读，语法尾巴也会进来）：{len(sims)} 句")
    for cov, shared, (scene, no, kind, who, text, _), src in sims:
        where = f"{src[0].split('/')[-1]}:{src[1]}"
        print(f"- {cov:.2f}（{shared} 字）l.{no} {who}「{text}」 ← {where}「{src[2][:50]}」")

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

    near = []
    for no, who, text, n in new:
        if n in v4_texts:
            continue
        best = max(((SequenceMatcher(None, n, t).ratio(), w, t) for _, w, _, t in v4),
                   key=lambda x: x[0])
        if best[0] >= a.near:
            near.append((best[0], no, who, text, best[1], best[2]))
    print(f"\n## 2b. 很接近的（去掉标点后 difflib.SequenceMatcher ratio，{a.near} ≤ r < 1，"
          f"每句取和第四版最像的一句）：{len(near)} 句")
    for r, no, who, text, w4, t4 in sorted(near, key=lambda x: -x[0]):
        print(f"- {r:.2f} l.{no} {who}：「{text}」 ← 第四版 {w4}「{t4}」")


if __name__ == "__main__":
    main()
