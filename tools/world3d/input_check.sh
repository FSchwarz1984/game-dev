#!/usr/bin/env bash
# Real-input check of the 3D art sample (CLAUDE.md §4: verify through the real input path).
# Runs the sample in a real X11 window on Xvfb and drives it with xdotool through XTEST (the X
# server treats it as a physical keyboard), then reads the game's own log of where she is.
#   bash tools/world3d/input_check.sh <out_dir> [WxH]
# A: in the yard, hold D 1.5 s, W 1.0 s, A+S 1.0 s (she walks; さぢ follows).
# B: on the lookout, stand still (the view from the lookout dissolves in), hold D 1.2 s (she turns
#    her head east), press S (the top-down view comes back).
# Screens: <out>/A_*.png, <out>/B_*.png (import -window root); logs: <out>/A.log, <out>/B.log.
set -uo pipefail
GODOT_BIN="${GODOT_BIN:-/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64}"
PROJ="$(cd "$(dirname "$0")/../../godot" && pwd)"
OUT="${1:?out dir}"; RES="${2:-1280x720}"
mkdir -p "$OUT"

run_case() {
	local name="$1"; shift
	local disp=":$((60 + RANDOM % 30))"
	Xvfb "$disp" -screen 0 "${RES}x24" -nolisten tcp >/dev/null 2>&1 &
	local xp=$!
	for _ in $(seq 1 50); do DISPLAY="$disp" xdpyinfo >/dev/null 2>&1 && break; sleep 0.1; done
	DISPLAY="$disp" "$GODOT_BIN" --path "$PROJ" --rendering-method mobile --rendering-driver vulkan \
		--resolution "$RES" --position 0,0 res://world3d/sample.tscn -- --log_pos "$@" > "$OUT/$name.log" 2>&1 &
	local gp=$!
	# wait for the window and for the world to be built (the log says so)
	for _ in $(seq 1 600); do grep -q "GRASS tufts" "$OUT/$name.log" 2>/dev/null && break; sleep 0.1; done
	sleep 9
	local wid
	wid=$(DISPLAY="$disp" xdotool search --onlyvisible --class "Godot" 2>/dev/null | tail -1)
	[ -z "$wid" ] && wid=$(DISPLAY="$disp" xdotool search --onlyvisible --name "." 2>/dev/null | tail -1)
	DISPLAY="$disp" xdotool windowfocus "$wid" 2>/dev/null
	echo "$disp $wid"
	CASE_DISP="$disp"; CASE_XP=$xp; CASE_GP=$gp
}

shot() { DISPLAY="$CASE_DISP" import -window root "$OUT/$1.png"; echo "MARK $1 $(date +%s.%N)" >> "$OUT/marks.txt"; }
hold() { local t="$1"; shift; DISPLAY="$CASE_DISP" xdotool keydown "$@"; sleep "$t"; DISPLAY="$CASE_DISP" xdotool keyup "$@"; }
finish() { kill "$CASE_GP" 2>/dev/null; sleep 0.5; kill "$CASE_XP" 2>/dev/null; }

: > "$OUT/marks.txt"
# ---- A: walking in the yard
run_case A
shot A_0_start
hold 1.5 d; sleep 0.3; shot A_1_after_D
hold 1.0 w; sleep 0.3; shot A_2_after_W
hold 1.0 a s; sleep 0.6; shot A_3_after_AS
finish

# ---- B: the lookout
run_case B --at=-23.4,41.7 --hours=17.8
sleep 2.5; shot B_0_looking_out
hold 1.2 d; sleep 1.2; shot B_1_after_D
hold 0.2 s; sleep 1.5; shot B_2_after_S
finish
grep -h "POS\|VISTA" "$OUT/A.log" | head -40 > "$OUT/A_pos.txt"
grep -h "POS\|VISTA" "$OUT/B.log" | head -60 > "$OUT/B_pos.txt"
echo done
