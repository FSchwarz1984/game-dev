"""Readable sources of the game's sounds from godot/audio/SOURCES.json (for the delivery's licences folder).
Since G5R3-53 / G5R3-65 every sound and piece of music is synthesized (v0.1's synthesizer rendered offline by
tools/audio/build_sounds.py): there is no recording and no sample to credit. This lists what made each file.
Usage: python3 -I tools/godot/audio_credits.py godot/audio/SOURCES.json"""
import json
import sys
from collections import defaultdict


def main(path):
    data = json.load(open(path, encoding="utf-8"))
    files = data.get("files", {})
    print("Sound and music: all synthesized for this game. No recordings, no instrument samples.")
    print(data.get("_about", ""))
    print()
    by_id = defaultdict(list)
    for name, f in files.items():
        by_id[f.get("id", name)].append((name, f))
    gens = sorted({f.get("generator", "") for f in files.values()})
    print("Generators:")
    for g in gens:
        print("  - " + g)
    print()
    for sid in sorted(by_id):
        rows = by_id[sid]
        seeds = [str(f.get("job", {}).get("seed", f.get("recipe", {}).get("seed", ""))) for _, f in rows]
        print(f"{sid}: {len(rows)} file(s); seeds {', '.join(s for s in seeds if s)}")
        for name, f in rows[:1]:
            print(f"  e.g. {name}  ({f.get('seconds', '')} s)  sha256 {f.get('sha256', '')[:16]}...")


if __name__ == "__main__":
    main(sys.argv[1])
