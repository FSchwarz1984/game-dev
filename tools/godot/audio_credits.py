"""Readable credits for the field recordings from godot/audio/SOURCES.json (for the delivery's
licences folder). Usage: python3 -I tools/godot/audio_credits.py godot/audio/SOURCES.json"""
import json
import sys


def main(path):
    data = json.load(open(path, encoding="utf-8"))
    print("Field recordings (CC0 / public domain). Edits are listed per file.\n")
    for name, f in sorted(data.get("files", {}).items()):
        # one source ("source") or several mixed or cut from ("sources": {key: source})
        srcs = [f["source"]] if "source" in f else list(f.get("sources", {}).values())
        print(name)
        for src in srcs:
            print("  title:   " + src.get("title", ""))
            print("  author:  " + src.get("author", ""))
            print("  licence: " + src.get("licence", "") + "  " + src.get("licence_url", ""))
            print("  page:    " + src.get("page", ""))
        for e in f.get("edits", []):
            print("  edit:    " + e)
        print()


if __name__ == "__main__":
    main(sys.argv[1])
