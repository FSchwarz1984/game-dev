#!/usr/bin/env python3
"""Rebuilds a 3D terrain region (docs/knowledge/21-3d-pixel-render.md):
    python3 tools/world3d/build_terrain.py [layout.json]
Writes godot/world3d/terrain/<name>/ and previews in tools/world3d/out/<name>/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from w3terrain import build  # noqa: E402

if __name__ == "__main__":
    layout = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "layouts" / "saddle.json"
    build.build(layout)
    # let Godot (re)import the changed PNGs so the next run sees them
    import os
    import subprocess
    godot = os.environ.get("GODOT_BIN", "/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64")
    proj = Path(__file__).resolve().parents[2] / "godot"
    if os.path.exists(godot) and not os.environ.get("NO_IMPORT"):
        subprocess.run([godot, "--headless", "--path", str(proj), "--import"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
        print("[w3terrain] godot import done")
