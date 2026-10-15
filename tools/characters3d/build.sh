#!/usr/bin/env bash
# One command rebuilds a 3D character for the game (docs/knowledge/24-3d-characters.md):
#   bash tools/characters3d/build.sh [char] [--static]
#   1. Blender (headless) builds the model, rig, skin weights and animation clips and exports
#      godot/characters/<char>/<char>.glb plus rig.json (face landmarks, chain settings);
#   2. the face stamps compile to godot/characters/<char>/face_atlas.png + face.json;
#   3. Godot imports the changed assets.
# Needs Blender 5.2 (bash tools/characters3d/setup-blender.sh) and the Godot editor
# (tools/godot/setup-godot.sh). Env: BLENDER (default /home/user/blender/blender), GODOT_BIN.
set -euo pipefail
cd "$(dirname "$0")/../.."
CHAR="${1:-kasasagi}"
shift || true
BLENDER="${BLENDER:-/home/user/blender/blender}"
GODOT_BIN="${GODOT_BIN:-/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64}"
STATIC=""
for a in "$@"; do [ "$a" = "--static" ] && STATIC="--static"; done
OUT="godot/characters/$CHAR/$CHAR.glb"
"$BLENDER" -b --factory-startup --python tools/characters3d/build.py -- --char "$CHAR" $STATIC --out "$OUT" \
  2>&1 | grep -E "Traceback|Error|error:|File \"|EXPORTED|WARN" || true
test -f "$OUT"
python3 -I tools/characters3d/faces/make_faces.py "$CHAR"
"$GODOT_BIN" --headless --path godot --import 2>&1 | grep -iE "error|warning" | grep -v "ERR_CANT_OPEN\|daemon" || true
echo "BUILT $CHAR"
