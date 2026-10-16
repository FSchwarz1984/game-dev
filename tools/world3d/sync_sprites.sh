#!/usr/bin/env bash
# Builds the character sprite sheets for the 3D world's camera with the sprite agent's own tool
# (tools/art/sprite3d, read-only use) and copies them into godot/world3d/sprites/ (lossless,
# no VRAM compression). The sprite pitch matching a leaned billboard under an orthographic camera
# at pitch T is atan(sin T): 39.33 deg for T = 55 (docs/knowledge/21 §7). The sheets are rendered at
# the world's pixels per metre (PixelView3D.PPM, 30: G5R3-24), texel for pixel, never scaled; the
# lookout view draws her and さぢ at the land's scale at her distance (vista3d.gd fig_ppm, 26.66 at
# 360 px high), from a set of its own:
#   bash tools/world3d/sync_sprites.sh [camera_pitch_deg=55] [anims=idle,walk,run] [ppm=30] [subdir]
#   bash tools/world3d/sync_sprites.sh 55 idle 26.66 vista        # -> godot/world3d/sprites/vista/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
T="${1:-55}"
ANIMS="${2:-idle,walk,run}"
PPM="${3:-30}"
SUB="${4:-}"
P="$(python3 -c "import math; print(round(math.degrees(math.atan(math.sin(math.radians($T)))), 2))")"
TMP="$ROOT/tools/world3d/out/sprites_p${P}_ppm$PPM"
mkdir -p "$TMP"
python3 -I "$ROOT/tools/art/sprite3d/build.py" --pitch "$P" --ppm "$PPM" --out "$TMP" --anims "$ANIMS" >/dev/null
DST="$ROOT/godot/world3d/sprites${SUB:+/$SUB}"
mkdir -p "$DST"
for f in "$TMP"/*.png; do
  b="$(basename "$f")"
  cp "$f" "$DST/$b"
  if [ ! -f "$DST/$b.import" ]; then
    printf '[remap]\n\nimporter="texture"\ntype="CompressedTexture2D"\n\n[params]\n\ncompress/mode=0\nmipmaps/generate=false\ndetect_3d/compress_to=0\nprocess/fix_alpha_border=false\n' > "$DST/$b.import"
  fi
done
python3 - "$TMP/characters.json" "$DST/characters.json" "$P" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
d["_sprite_pitch_deg"] = float(sys.argv[3])
json.dump(d, open(sys.argv[2], "w"), ensure_ascii=False)
PY
echo "sprites at pitch $P, $PPM px/m -> $DST"
