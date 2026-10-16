"""Builds the Artifact download page for a packaged art sample (tools/godot/package-showcase.sh).

  python3 -I tools/godot/make_download_page.py <out_dir> [verified.html]

Reads <out_dir>/SHA256SUMS.txt and the parts in <out_dir>/parts/, fills the template
tools/godot/showcase/download.html and writes:
  <out_dir>/download.html   the page (publish it with the Artifact tool, capability downloads)
  <out_dir>/files.json      {published path: source path} for the parts, split into batches that
                            each stay under the 64 MB a single publish may send
The parts are published as parts/partNN.bin next to the page; the page fetches them by those
relative paths, checks each one's size and SHA-256, joins them and offers the zip to save.
verified.html is an HTML fragment for the section "这一版验证到哪里" (what was and was not tested).
"""
import datetime
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BATCH = 60 * 1024 * 1024        # under the 64 MB a single publish may send, leaving room for the page


def main(out, verified=None):
    sums = {}
    for line in open(os.path.join(out, "SHA256SUMS.txt"), encoding="utf-8"):
        h, name = line.split(None, 1)
        sums[name.strip()] = h
    zip_name = "Tengan_ArtSample.zip"
    parts = []
    for name in sorted(n for n in sums if n.startswith("parts/")):
        src = os.path.join(out, name)
        parts.append({"path": name + ".bin", "src": src, "bytes": os.path.getsize(src), "sha256": sums[name]})
    total = os.path.getsize(os.path.join(out, zip_name))
    assert sum(p["bytes"] for p in parts) == total, "parts do not add up to the zip"
    manifest = {"bytes": total, "sha256": sums[zip_name],
                "parts": [{k: p[k] for k in ("path", "bytes", "sha256")} for p in parts]}
    page = open(os.path.join(HERE, "showcase", "download.html"), encoding="utf-8").read()
    if verified:
        frag = open(verified, encoding="utf-8").read().strip()
    else:
        frag = "<p class=\"small\">（待补）</p>"
    page = (page.replace("__MANIFEST__", json.dumps(manifest, ensure_ascii=False))
                .replace("__VERIFIED__", frag)
                .replace("__DATE__", html.escape(datetime.date.today().isoformat())))
    assert "__" not in page.split("<script>")[0].replace("__init__", ""), "unfilled placeholder"
    open(os.path.join(out, "download.html"), "w", encoding="utf-8").write(page)
    batches, cur, size = [], {}, 0
    for p in parts:
        if cur and size + p["bytes"] > BATCH:
            batches.append(cur)
            cur, size = {}, 0
        cur[p["path"]] = p["src"]
        size += p["bytes"]
    if cur:
        batches.append(cur)
    json.dump({"batches": batches}, open(os.path.join(out, "files.json"), "w"), indent=1)
    print("page %s, %d parts, %.1f MB, %d publish batches" % (os.path.join(out, "download.html"),
          len(parts), total / 1048576, len(batches)))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
