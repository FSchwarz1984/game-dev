#!/usr/bin/env bash
# Records the art sample's route (hut -> yard -> round the great camphor -> the old road, さぢ
# following; sample.gd _make_route) with Godot's Movie Maker, pixel for pixel, and encodes it.
#   bash tools/world3d/record.sh <out_dir> [WxH] [-- extra game args]
# Movie Maker writes frames at the project's window size override (1280x720 in project.godot) and
# resizes the window's image to it with a BILINEAR filter when the window differs: a 1920x1080
# recording came out 1280x720 and smeared. So this runs the project through a view of it whose
# override is WxH (tools/world3d/out/proj_WxH: a copy of project.godot, everything else symlinked)
# in a WxH window: frames are the window as shown, every native pixel an exact square.
# Output: <out_dir>/frames/f########.png, <out_dir>/route_WxH.mp4, <out_dir>/log.txt.
set -uo pipefail
GODOT_BIN="${GODOT_BIN:-/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64}"
SRC="$(cd "$(dirname "$0")/../../godot" && pwd)"
OUT="${1:?out dir}"; RES="${2:-1920x1080}"
shift 2 2>/dev/null || shift $#
[ "${1:-}" = "--" ] && shift
W="${RES%x*}"; H="${RES#*x}"
VIEW="$(cd "$(dirname "$0")" && pwd)/out/proj_${RES}"
rm -rf "$VIEW"; mkdir -p "$VIEW" "$OUT/frames"
for e in $(ls -A "$SRC"); do
	[ "$e" = "project.godot" ] && continue
	ln -s "$SRC/$e" "$VIEW/$e"
done
sed -e "s/^window\/size\/window_width_override=.*/window\/size\/window_width_override=$W/" \
	-e "s/^window\/size\/window_height_override=.*/window\/size\/window_height_override=$H/" \
	"$SRC/project.godot" > "$VIEW/project.godot"
rm -f "$OUT"/frames/f*.png "$OUT"/frames/f.wav
DISP=""
for n in $(seq 60 99); do [ -e "/tmp/.X$n-lock" ] || { DISP=":$n"; break; }; done
Xvfb "$DISP" -screen 0 "${RES}x24" -nolisten tcp >/dev/null 2>&1 &
XP=$!
trap 'kill $XP 2>/dev/null' EXIT
for _ in $(seq 1 50); do DISPLAY="$DISP" xdpyinfo >/dev/null 2>&1 && break; sleep 0.1; done
DISPLAY="$DISP" timeout "${TIMEOUT:-5400}" "$GODOT_BIN" --path "$VIEW" --rendering-method mobile \
	--rendering-driver vulkan --resolution "$RES" --position 0,0 \
	--write-movie "$OUT/frames/f.png" --fixed-fps 30 res://world3d/sample.tscn -- \
	--route=walk --route_quit --route_log "${@:---hours=16.6}" > "$OUT/log.txt" 2>&1
# the first frame is drawn before the shadow map and the camera have settled (a flash of flat light):
# the recording starts two frames in
for k in 0 1; do rm -f "$OUT/frames/$(printf 'f%08d.png' $k)"; done
n=$(ls "$OUT"/frames/f*.png 2>/dev/null | wc -l)
echo "frames: $n ($(awk "BEGIN{printf \"%.1f\", $n/30}") s)"
ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 2 -i "$OUT/frames/f%08d.png" -c:v libx264 -crf 14 \
	-preset slow -pix_fmt yuv420p -movflags +faststart "$OUT/route_${RES}.mp4" && echo "$OUT/route_${RES}.mp4"
