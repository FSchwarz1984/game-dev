#!/usr/bin/env bash
# Run the vegetation bench once under Xvfb (Mobile renderer, Vulkan/lavapipe) and wait for it.
#   bash tools/flora/bench/run_bench.sh <project_dir> -- --layout=glade --preset=dusk --shot=/tmp/x.png
# The first run imports the project (--import, headless). One Godot process at a time.
set -euo pipefail
PROJ="${1:?project dir}"; shift
[ "${1:-}" = "--" ] && shift
GODOT_BIN="${GODOT_BIN:-/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64}"
DISP="${XVFB_DISPLAY:-:93}"
if [ ! -d "$PROJ/.godot/imported" ] || [ -n "${REIMPORT:-}" ]; then
  timeout 300 "$GODOT_BIN" --headless --path "$PROJ" --import >"$PROJ/import.log" 2>&1 || true
fi
Xvfb "$DISP" -screen 0 1600x900x24 -nolisten tcp >/dev/null 2>&1 &
XPID=$!
trap 'kill $XPID 2>/dev/null || true' EXIT
for _ in $(seq 1 50); do DISPLAY="$DISP" xdpyinfo >/dev/null 2>&1 && break; sleep 0.1; done
DISPLAY="$DISP" timeout "${TIMEOUT:-240}" "$GODOT_BIN" --path "$PROJ" --rendering-method mobile \
  --rendering-driver vulkan --resolution 1440x810 --position 0,0 -- "$@" 2>&1 | grep -v "^$" | tail -n "${TAIL:-25}"
