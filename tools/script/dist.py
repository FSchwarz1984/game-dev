"""Voice distribution of a script draft (knowledge/27 §5): per speaker, the number of lines, their
mean length, the short ones, the stance particles (and, for her, how many go to the empty place
beside her), "您" and the self-reference "人家".

Usage: python3 -I tools/script/dist.py docs/design/script-05-draft.md [--all]
With a v5-style draft only the Chinese performance script ("**中文演出稿**" blocks) is counted;
--all counts every dialogue line in the file (for v4, which has only the Chinese).
"""
import re
import sys
from collections import defaultdict

LINE = re.compile(r"^>\s*([^：（「]+?)(（[^）]*）)?：「(.*)」\s*$")
PUNCT = set("，。、？！…—「」『』（）：；·～〜‧ 　'\"“”‘’")
# stance particles (knowledge/27 §6.1): counted where they close a clause; 吗/呢 in real questions
# are listed apart
STANCE = ["是吧", "啊", "呀", "嘛", "吧", "啦", "哦", "呗", "呢"]
EMPTY = "朝身旁空着的地方"


def chars(s):
    return [c for c in s if c not in PUNCT]


def clause_ends(s):
    # the last word of each clause: text before ， 。 ？ ！ … — or the end
    parts = re.split(r"[，。？！…—]+", s)
    return [p for p in parts if p]


def main(path, all_lines):
    text = open(path, encoding="utf-8").read().splitlines()
    in_cn = all_lines
    stats = defaultdict(lambda: {"n": 0, "chars": 0, "short": 0, "stance": 0, "stance_empty": 0,
                                 "q": 0, "nin": 0, "renjia": 0, "lines": []})
    for raw in text:
        if raw.startswith("**中文演出稿**"):
            in_cn = True
            continue
        if raw.startswith("**日文原稿**") or raw.startswith("## 4.") or raw.startswith("## 13.") or raw.startswith("## 14."):
            in_cn = all_lines and not (raw.startswith("## 13.") or raw.startswith("## 14."))
            if raw.startswith("## 13.") or raw.startswith("## 14.") or raw.startswith("## 4."):
                in_cn = False
                all_lines = False
            continue
        if not in_cn:
            continue
        m = LINE.match(raw)
        if not m:
            continue
        who = m.group(1).strip()
        note = m.group(2) or ""
        line = m.group(3)
        st = stats[who]
        c = chars(line)
        st["n"] += 1
        st["chars"] += len(c)
        if len(c) <= 4:
            st["short"] += 1
        st["nin"] += line.count("您")
        st["renjia"] += line.count("人家")
        if not c or set(c) <= set("啊哇诶嗯哎呀哦"):
            continue                       # a cry or an interjection on its own is not a stance
        for clause in clause_ends(line):
            for p in STANCE:
                if clause.endswith(p):
                    if p in ("呢",) and line.rstrip().endswith("？") and clause == clause_ends(line)[-1]:
                        st["q"] += 1
                    else:
                        st["stance"] += 1
                        if EMPTY in note:
                            st["stance_empty"] += 1
                    break
            if clause.endswith("吗"):
                st["q"] += 1
    print("| 说话的人 | 句数 | 平均字数 | 不超过 4 字 | 表态度的语气词（其中对空位） | 问句的吗／呢 | 您 | 人家 |")
    print("|---|---|---|---|---|---|---|---|")
    for who, st in sorted(stats.items(), key=lambda kv: -kv[1]["n"]):
        mean = st["chars"] / st["n"] if st["n"] else 0
        print(f"| {who} | {st['n']} | {mean:.1f} | {st['short']} | {st['stance']}（{st['stance_empty']}） | {st['q']} | {st['nin']} | {st['renjia']} |")


if __name__ == "__main__":
    main(sys.argv[1], "--all" in sys.argv[2:])
