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
# C3D_PROJ: build into another project view (default: the repository's godot/); C3D_VARIANT picks the
# design (tools/characters3d/kasasagi/design.py); C3D_NOANIMS=1 builds the rig without clips
PROJ="${C3D_PROJ:-godot}"
OUT="$PROJ/characters/$CHAR/$CHAR.glb"
mkdir -p "$PROJ/characters/$CHAR"
# The repository's godot/characters/ holds the models the game uses (kasasagi there is round 4); the
# generator in tools/characters3d/kasasagi/ is the rejected round 6 (G5R3-20, docs/knowledge/24), so
# replacing a model the game already has needs C3D_MAIN=1. Build into a project view (C3D_PROJ) instead.
GAME_DIR="$(pwd -P)/godot/characters/$CHAR"
DEST_DIR="$(cd "$PROJ/characters/$CHAR" && pwd -P)"
if [ "$DEST_DIR" = "$GAME_DIR" ] && [ -f "$GAME_DIR/$CHAR.glb" ] && [ "${C3D_MAIN:-0}" != "1" ]; then
  echo "build.sh: not replacing the game's model in godot/characters/$CHAR (set C3D_PROJ=<project view>, or C3D_MAIN=1 to replace it)" >&2
  exit 2
fi
"$BLENDER" -b --factory-startup --python tools/characters3d/build.py -- --char "$CHAR" $STATIC --out "$OUT" \
  2>&1 | grep -E "Traceback|Error|error:|File \"|EXPORTED|WARN" || true
test -f "$OUT"
python3 -I tools/characters3d/faces/make_faces.py "$CHAR" --out "$PROJ/characters/$CHAR"
"$GODOT_BIN" --headless --path "$PROJ" --import 2>&1 | grep -iE "error|warning" | grep -v "ERR_CANT_OPEN\|daemon" || true
echo "BUILT $CHAR -> $PROJ (variant ${C3D_VARIANT:-default})"
