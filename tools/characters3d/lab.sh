#!/usr/bin/env bash
# Runs the character lab (godot/characters/dev/char_lab.tscn) in a real X11 window on Xvfb (Mesa
# lavapipe), Forward+, fixed 30 fps clock (captures are frame-exact, not real time).
#   bash tools/characters3d/lab.sh <out_dir> [WxH] [-- lab args...]
# e.g. bash tools/characters3d/lab.sh /tmp/x 1920x1080 -- --shots=/tmp/x:0,10.5;45,10.5
# Log: <out_dir>/log.txt. See docs/knowledge/24-3d-characters.md §verify for the options.
set -uo pipefail
GODOT_BIN="${GODOT_BIN:-/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64}"
PROJ="$(cd "$(dirname "$0")/../../godot" && pwd)"
OUT="${1:?out dir}"; RES="${2:-1920x1080}"
shift 2 2>/dev/null || shift $#
[ "${1:-}" = "--" ] && shift
mkdir -p "$OUT"
DISP=":$((100 + RANDOM % 100))"
Xvfb "$DISP" -screen 0 "${RES}x24" -nolisten tcp >/dev/null 2>&1 &
XP=$!
trap 'kill $XP 2>/dev/null' EXIT
for _ in $(seq 1 50); do DISPLAY="$DISP" xdpyinfo >/dev/null 2>&1 && break; sleep 0.1; done
DISPLAY="$DISP" timeout "${TIMEOUT:-600}" "$GODOT_BIN" --path "$PROJ" --rendering-method forward_plus \
  --rendering-driver vulkan --resolution "$RES" --position 0,0 --fixed-fps 30 ${GODOT_EXTRA:-} \
  res://characters/dev/char_lab.tscn -- "$@" > "$OUT/log.txt" 2>&1
code=$?
grep -v "ALSA\|alsa\|audio_driver\|All audio drivers\|at: init\|at: initialize\|^$" "$OUT/log.txt" | head -60
exit $code
