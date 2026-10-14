#!/usr/bin/env bash
# Renders one 3D asset through the 3D pixel renderer at four times of day (docs/knowledge/21 §2.5).
#   bash tools/world3d/preview_asset.sh res://world3d/assets/<kind>/<name>/<name>.tscn <out_dir> [window WxH] [extra game args]
# Writes <out_dir>/<name>_<hour>.png (native pixels) and _x3.png. Window 1440x810 shows 480x270
# native; use a taller window for tall trees (1000x1000 -> 500x500 native).
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ASSET="${1-}"; OUT="${2:?output dir}"; RES="${3:-1440x810}"
shift 3 2>/dev/null || shift $#
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
TIMEOUT="${TIMEOUT:-120}" bash "$HERE/run3d.sh" res://render3d/dev/asset_preview.tscn "$OUT" "$RES" -- --asset="$ASSET" --out="$OUT" "$@"
