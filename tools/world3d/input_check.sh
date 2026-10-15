#!/usr/bin/env bash
# Real-input check of the 3D art sample (CLAUDE.md §4: verify through the real input path).
# Runs the sample in a real X11 window on Xvfb and drives it with xdotool through XTEST (the X
# server treats it as a physical keyboard), then reads the game's own log of where she is.
#   bash tools/world3d/input_check.sh <out_dir> [WxH]        (CASES=D: only some of the cases)
# A: in the yard, hold D 1.5 s, W 1.0 s, A+S 1.0 s (she walks; さぢ follows).
# B: under the great camphor, west of the trunk: hold W 2.2 s (north under the west limb), then D
#    1.6 s (east along the north side, the limbs over her; her silhouette where they cover her).
# C: the yard at night (21:30): hold D 1.5 s toward the front path and its lanterns.
# D: the lookout: walk S onto the rock and stand still (the view from the lookout comes in
#    through the mist's white), hold D (she turns her head west), hold A (back east and, held
#    against the end, round to the look back home; held until the game's log shows the home
#    bearing), then W 1.2 s (the top-down view comes back, she walks on north).
# Screens: <out>/A_*.png, <out>/B_*.png, <out>/C_*.png (import -window root); logs: <out>/?.log.
# (round 4: the check runs without the VoxelGI bake, the volumetric fog, SSAO and the sun's shadow
# map, --gi=none --vfog=0 --ssao=0 --noshadow: on the software rasteriser the full picture runs at
# about one frame a second (the shadow pass alone is two thirds of it) and the bake blocks for
# 12-27 s, so a held key's press and release land in the same frame and she never moves. With them
# off it runs at about 4 frames a second. The input path (XTEST -> X -> Godot -> the game) is the
# same either way; only what is drawn is lighter.)
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
	DISPLAY="$disp" "$GODOT_BIN" --path "$PROJ" --rendering-method "${METHOD:-forward_plus}" --rendering-driver vulkan \
		--resolution "$RES" --position 0,0 res://world3d/sample.tscn -- --log_pos=2 --gi=none --vfog=0 --ssao=0 --noshadow "$@" > "$OUT/$name.log" 2>&1 &
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
CASES="${CASES:-ABCD}"
if [[ "$CASES" == *A* ]]; then
# ---- A: walking in the yard
run_case A
shot A_0_start
hold 1.5 d; sleep 0.3; shot A_1_after_D
hold 1.0 w; sleep 0.3; shot A_2_after_W
hold 1.0 a s; sleep 0.6; shot A_3_after_AS
finish
fi

if [[ "$CASES" == *B* ]]; then
# ---- B: under the great camphor
run_case B --at=-6.2,-1.0 --hours=8.5
shot B_0_start
hold 2.2 w; sleep 0.3; shot B_1_after_W
hold 1.6 d; sleep 0.3; shot B_2_after_D
finish
fi

if [[ "$CASES" == *C* ]]; then
# ---- C: the yard at night
run_case C --at=-14.2,13.6 --hours=21.5
shot C_0_start
hold 1.5 d; sleep 0.3; shot C_1_after_D
finish
fi
if [[ "$CASES" == *D* ]]; then
# ---- D: the view from the lookout
run_case D --at=-23.4,38.6 --hours=16.5
shot D_0_start
hold 2.5 s
# (standing still she looks out; under software rendering at a few frames a second that can take
# several seconds: wait for the game to say so, then for the white to clear)
for _ in $(seq 1 200); do grep -q "VISTA on" "$OUT/D.log" 2>/dev/null && break; sleep 0.1; done
for _ in $(seq 1 300); do grep -q "VISTA built" "$OUT/D.log" 2>/dev/null && break; sleep 0.1; done
sleep 2.5; shot D_1_looking_out
# (round 4: at about one frame a second in the view, a fixed hold can end before the game has seen
# it; hold the key until the game's own log shows the turn, at most a set time)
hold_until() { # key, max seconds, awk condition on the yaw of the last "vista=true" POS line
	local key="$1" max="$2" cond="$3"
	DISPLAY="$CASE_DISP" xdotool keydown "$key"
	local t0; t0=$(date +%s.%N)
	while :; do
		local y; y=$(grep "vista=true" "$OUT/D.log" | tail -1 | sed -n 's/.*yaw=\([-0-9.]*\).*/\1/p')
		[ -n "$y" ] && awk -v y="$y" "BEGIN{exit !($cond)}" && break
		awk -v a="$t0" -v b="$(date +%s.%N)" -v m="$max" 'BEGIN{exit !(b - a > m)}' && break
		sleep 0.1
	done
	DISPLAY="$CASE_DISP" xdotool keyup "$key"
}
hold_until d 3 "y > 195"; sleep 0.8; shot D_2_after_D
hold_until a 15 "y <= 60.5"; sleep 2.5; shot D_3_after_A_home
hold 1.2 w; sleep 2.5; shot D_4_after_W
finish
fi
for c in A B C; do [ -f "$OUT/$c.log" ] && grep -h "POS" "$OUT/$c.log" | head -60 > "$OUT/${c}_pos.txt"; done
[ -f "$OUT/D.log" ] && grep -h "POS\|VISTA" "$OUT/D.log" > "$OUT/D_pos.txt"
echo done
