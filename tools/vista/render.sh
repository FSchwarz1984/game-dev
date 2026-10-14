#!/usr/bin/env bash
# Renders a vista capture plan (tools/vista/capture.gd) in a real window on Xvfb with Mesa software
# rendering and the Mobile renderer (the one both platforms use).
#   bash tools/vista/render.sh plan.json [WxH window, default 960x540] [extra godot args...]
# Example plan: {"out": "/tmp/x", "shots": [{"name": "dusk", "state": {"tod": 19.4, "pan": 1}}]}
set -euo pipefail
. "$(dirname "$0")/../godot/common.sh"
PLAN="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
RES="${2:-960x540}"
shift || true
shift || true
PROJ="$(cd "$(dirname "$0")/../../godot" && pwd)"
CAP="$(cd "$(dirname "$0")" && pwd)/capture.gd"
# new class_name scripts need the global class cache: rescan when a vista script is newer than it
CACHE="$PROJ/.godot/global_script_class_cache.cfg"
if [ ! -f "$CACHE" ] || [ -n "$(find "$PROJ/vista" -name '*.gd' -newer "$CACHE" -print -quit)" ]; then
  "$GODOT_BIN" --headless --path "$PROJ" --import >/dev/null 2>&1 || true
fi
DISP="${XVFB_DISPLAY:-:93}"
W="${RES%x*}"; H="${RES#*x}"
Xvfb "$DISP" -screen 0 "$((W + 256))x$((H + 256))x24" -nolisten tcp >/dev/null 2>&1 &
XPID=$!
trap 'kill $XPID 2>/dev/null || true' EXIT
export DISPLAY="$DISP"
for _ in $(seq 1 50); do xdpyinfo >/dev/null 2>&1 && break; sleep 0.1; done
"$GODOT_BIN" --path "$PROJ" --rendering-method mobile --rendering-driver vulkan --resolution "$RES" --position 0,0 "$@" -s "$CAP" -- --plan="$PLAN"
