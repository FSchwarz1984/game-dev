#!/usr/bin/env bash
# Runs a Godot project (through the editor binary) or an exported Linux build in a real X11 window
# on Xvfb with Mesa software rendering, drives it with xdotool through XTEST (the X server treats
# these like a physical keyboard and mouse; no synthetic XSendEvent), and captures both the
# engine's own viewport capture and an X screenshot of the screen.
#   bash tools/godot/xvfb-playtest.sh <project_dir|exported_binary|exported .exe> <out_dir> [renderer]
#     renderer: forward_plus (Vulkan, lavapipe) | mobile (Vulkan, lavapipe) |
#               gl_compatibility (OpenGL, llvmpipe)                     default: forward_plus
# Writes <out_dir>/<renderer>/: log.txt (engine stdout), viewport.png (get_viewport().get_texture()
# at frame 120), xscreen.png (ImageMagick `import -window root`), summary.txt.
# Expects the BOOT_OK/FIRST_FRAME/EVT/FPS lines printed by the test project of
# make-test-project.py; with another project only the screenshots and the log are meaningful.
# A Windows .exe runs through wine64 (WINE=1 setup-runtime.sh): its prefix lives in
# $GODOT_HOME/wine-prefix, Vulkan goes through winevulkan to the host's lavapipe.
# Needs apt: xvfb mesa-vulkan-drivers libgl1-mesa-dri xdotool imagemagick (setup-runtime.sh).
set -euo pipefail
. "$(dirname "$0")/common.sh"

TARGET="${1:?project dir or exported binary}"
OUT="${2:?output dir}"
METHOD="${3:-forward_plus}"
case "$METHOD" in forward_plus|mobile) DRIVER=vulkan ;; gl_compatibility) DRIVER=opengl3 ;;
  *) log "renderer must be forward_plus, mobile or gl_compatibility"; exit 2 ;; esac
O="$OUT/$METHOD"
mkdir -p "$O"
rm -f "$O/viewport.png" "$O/xscreen.png"
DISP="${XVFB_DISPLAY:-:97}"
QUIT_SECS="${QUIT_SECS:-30}"
WINDOW_NAME="${WINDOW_NAME:-GodotToolchainTest}"

Xvfb "$DISP" -screen 0 1280x720x24 -nolisten tcp >/dev/null 2>&1 &
XPID=$!
GPID=""
cleanup() {
  # Runs under set -e: every command here must be allowed to fail.
  [ -n "$GPID" ] && kill "$GPID" 2>/dev/null || true
  [ -n "${WINEPREFIX:-}" ] && "${WINESERVER:-/usr/lib/wine/wineserver64}" -k 2>/dev/null || true
  kill "$XPID" 2>/dev/null || true
}
trap cleanup EXIT
export DISPLAY="$DISP"
for _ in $(seq 1 50); do xdpyinfo >/dev/null 2>&1 && break; sleep 0.1; done

SHOT_PATH="$O/viewport.png"
if [ -d "$TARGET" ]; then
  CMD=("$GODOT_BIN" --path "$TARGET")
elif [[ "$TARGET" == *.exe ]]; then
  export WINEPREFIX="${WINEPREFIX:-$GODOT_HOME/wine-prefix}" WINEDEBUG="${WINEDEBUG:--all}"
  # mscoree/mshtml off: no Mono/Gecko install prompts. dinput8 off: under wine 9.0 (Ubuntu 24.04)
  # Godot 4.7.2 crashes with a null read right after loading dinput8.dll (joypad init); without it
  # the game boots. winedbg off: a crash exits instead of hanging in the debugger.
  export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-mscoree,mshtml=;dinput8=d;winedbg.exe=d}"
  WINE="${WINE_BIN:-/usr/lib/wine/wine64}"
  [ -d "$WINEPREFIX" ] || "$WINE" wineboot -i >/dev/null 2>&1
  CMD=("$WINE" "$TARGET")
  SHOT_PATH="Z:$O/viewport.png"  # the game sees Windows paths; Z: maps to /
else
  CMD=("$TARGET")
fi
start=$(date +%s.%N)
"${CMD[@]}" --rendering-method "$METHOD" --rendering-driver "$DRIVER" --resolution 1280x720 \
  --position 0,0 -- --shot="$SHOT_PATH" --quit-secs="$QUIT_SECS" >"$O/log.txt" 2>&1 &
GPID=$!
# Ready when the log shows FIRST_FRAME, or when the window is mapped: release exports buffer
# stdout unless application/run/flush_stdout_on_print is on, so the log can lag far behind.
WID=""
for _ in $(seq 1 600); do
  grep -q FIRST_FRAME "$O/log.txt" && break
  WID="$(xdotool search --onlyvisible --name "$WINDOW_NAME" 2>/dev/null | head -1 || true)"
  [ -n "$WID" ] && break
  kill -0 "$GPID" 2>/dev/null || { log "engine exited before its first frame"; tail -30 "$O/log.txt"; exit 1; }
  sleep 0.2
done
first=$(python3 -c "import time; print(round(time.time() - $start, 1))")
[ -n "$WID" ] || WID="$(xdotool search --sync --onlyvisible --name "$WINDOW_NAME" | head -1)"
xdotool windowfocus --sync "$WID" 2>/dev/null || xdotool windowfocus "$WID"
sleep 3
# Keyboard: hold the right arrow for 1.5 s (the sprite walks at 80 viewport px/s).
xdotool keydown Right; sleep 1.5; xdotool keyup Right
sleep 0.5
# Mouse click at window (300,300): at 1280x720 the 480x270 view is drawn at 2x with a (160,90)
# letterbox offset, so the game sees (70,105). It arrives as an emulated InputEventScreenTouch
# (input_devices/pointing/emulate_touch_from_mouse) and the sprite walks there.
xdotool mousemove 300 300 click 1
sleep 3
# Drag with the button held: emulated InputEventScreenDrag moves the sprite by the drag delta.
xdotool mousemove 600 500 mousedown 1
for x in 620 640 660 680 700; do xdotool mousemove "$x" 500; sleep 0.1; done
xdotool mouseup 1
sleep 1
import -window root "$O/xscreen.png"
wait "$GPID" || true
GPID=""

{
  echo "renderer: $METHOD ($DRIVER) target: $TARGET"
  echo "seconds until ready (process start -> FIRST_FRAME logged or window mapped): $first"
  grep -E "^(BOOT_OK|RENDER|SHOT|FPS_AVG)" "$O/log.txt" || true
  echo "--- input events"
  grep -E "^EVT (key Right|touch|mouse)" "$O/log.txt" || true
  grep -E "^EVT drag" "$O/log.txt" | sed -n '1p;$p' || true
  echo "--- FPS samples"
  grep -E "^FPS " "$O/log.txt" | tr '\n' ' ' | cut -c1-600; echo
  echo "--- errors"
  grep -iE "error|warning" "$O/log.txt" | grep -v "^WRAP" | head -20 || true
} >"$O/summary.txt"
cat "$O/summary.txt"
