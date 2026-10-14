#!/usr/bin/env bash
# Runs a scene of the Godot project in a real X11 window on Xvfb (Mesa lavapipe, Mobile renderer).
#   bash tools/world3d/run3d.sh <res://scene.tscn> <out_dir> [WxH] [-- game args...]
# Logs to <out_dir>/log.txt. Extra args after -- go to the game (OS.get_cmdline_user_args()).
set -uo pipefail
GODOT_BIN="${GODOT_BIN:-/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64}"
PROJ="$(cd "$(dirname "$0")/../../godot" && pwd)"
SCENE="${1:?scene}"; OUT="${2:?out dir}"; RES="${3:-1440x810}"
shift 3 2>/dev/null || shift $#
[ "${1:-}" = "--" ] && shift
mkdir -p "$OUT"
DISP=":$((40 + RANDOM % 50))"
Xvfb "$DISP" -screen 0 "${RES}x24" -nolisten tcp >/dev/null 2>&1 &
XP=$!
trap 'kill $XP 2>/dev/null' EXIT
for _ in $(seq 1 50); do DISPLAY="$DISP" xdpyinfo >/dev/null 2>&1 && break; sleep 0.1; done
DISPLAY="$DISP" timeout "${TIMEOUT:-300}" "$GODOT_BIN" --path "$PROJ" --rendering-method mobile \
  --rendering-driver vulkan --resolution "$RES" --position 0,0 ${GODOT_EXTRA:-} "$SCENE" -- "$@" \
  > "$OUT/log.txt" 2>&1
code=$?
grep -v "ALSA\|alsa\|audio_driver\|All audio drivers\|at: init\|at: initialize\|^$" "$OUT/log.txt" | head -60
exit $code
