#!/usr/bin/env bash
# Real-input check of the 3D art sample (CLAUDE.md §4: verify through the real input path).
# Runs the sample in a real X11 window on Xvfb and drives it with xdotool through XTEST (the X
# server treats it as a physical keyboard), then reads the game's own log of where she is.
#   bash tools/world3d/input_check.sh <out_dir> [WxH]
# A: in the yard, hold D 1.5 s, W 1.0 s, A+S 1.0 s (she walks; さぢ follows).
# B: under the great camphor, west of the trunk: hold W 2.2 s (north under the west limb), then D
#    1.6 s (east along the north side, the limbs over her; her silhouette where they cover her).
# C: the yard at night (21:30): hold D 1.5 s toward the front path and its lanterns.
# Screens: <out>/A_*.png, <out>/B_*.png, <out>/C_*.png (import -window root); logs: <out>/?.log.
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
		--resolution "$RES" --position 0,0 res://world3d/sample.tscn -- --log_pos=2 "$@" > "$OUT/$name.log" 2>&1 &
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

# ---- B: under the great camphor
run_case B --at=-6.2,-1.0 --hours=8.5
shot B_0_start
hold 2.2 w; sleep 0.3; shot B_1_after_W
hold 1.6 d; sleep 0.3; shot B_2_after_D
finish

# ---- C: the yard at night
run_case C --at=-14.2,13.6 --hours=21.5
shot C_0_start
hold 1.5 d; sleep 0.3; shot C_1_after_D
finish
for c in A B C; do grep -h "POS" "$OUT/$c.log" | head -60 > "$OUT/${c}_pos.txt"; done
echo done
