#!/usr/bin/env bash
# Records the vista's prologue timeline (or the title backdrop) with Godot's Movie Maker: every frame
# at a fixed step, written as PNGs, in a real window on Xvfb with Mesa and the Mobile renderer.
#   bash tools/vista/record.sh OUTDIR [WxH window, default 1280x720] [fps, default 30] [record.gd args...]
#   e.g. bash tools/vista/record.sh /tmp/rec 1280x720 30 --shot=prologue --grab=/tmp/rec/native
# Movie Maker writes OUTDIR/f00000000.png ... at the project window size (1280x720); --grab=DIR also
# writes each frame at one pixel per native pixel (record.gd). MOVIE=0 skips Movie Maker (grab only).
set -euo pipefail
. "$(dirname "$0")/../godot/common.sh"
OUT="$1"; RES="${2:-1280x720}"; FPS="${3:-30}"
shift; shift || true; shift || true
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
PROJ="$(cd "$(dirname "$0")/../../godot" && pwd)"
REC="$(cd "$(dirname "$0")" && pwd)/record.gd"
CACHE="$PROJ/.godot/global_script_class_cache.cfg"
if [ ! -f "$CACHE" ] || [ -n "$(find "$PROJ/vista" -name '*.gd' -newer "$CACHE" -print -quit)" ]; then
  "$GODOT_BIN" --headless --path "$PROJ" --import >/dev/null 2>&1 || true
fi
DISP="${XVFB_DISPLAY:-:94}"
W="${RES%x*}"; H="${RES#*x}"
Xvfb "$DISP" -screen 0 "$((W + 256))x$((H + 256))x24" -nolisten tcp >/dev/null 2>&1 &
XPID=$!
trap 'kill $XPID 2>/dev/null || true' EXIT
export DISPLAY="$DISP"
for _ in $(seq 1 50); do xdpyinfo >/dev/null 2>&1 && break; sleep 0.1; done
"$GODOT_BIN" --path "$PROJ" --rendering-method mobile --rendering-driver vulkan --resolution "$RES" --position 0,0 \
  --fixed-fps "$FPS" $([ "${MOVIE:-1}" = 0 ] || echo --write-movie "$OUT/f.png") -s "$REC" -- "$@"
