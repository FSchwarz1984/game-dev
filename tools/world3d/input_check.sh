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
# N: --nochar (G5R3-21, the Windows build without characters), two runs: from the hut door through
#    the gate into the yard and back; then from the top of the spur down onto the lookout rock, where
#    standing still the view comes in; hold D (her head turns west), then S (the top-down view comes
#    back). Steered with held keys from the game's own log of where she is (as a player steers by the
#    screen), at a fixed step. Not in the default set: CASES=N.
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
		--resolution "$RES" --position 0,0 ${GODOT_EXTRA:-} res://world3d/sample.tscn -- --log_pos=2 --gi=none --vfog=0 --ssao=0 --noshadow "$@" > "$OUT/$name.log" 2>&1 &
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
# walk_to <case> <x> <z> [max frames] [arrived within m]: hold the movement keys toward (x, z),
# deciding again each time the game logs a new frame of where she is (keys only, through XTEST); when
# she has not moved for 12 frames (a post, a corner) add a key across the way for 8, the other side
# the next time, as a player does. (Frame-driven: on the software rasteriser with other jobs on the
# machine the game can run at well under a frame a second; run it at a fixed step,
# GODOT_EXTRA="--fixed-fps 5": 0.48 m a frame at her pace, under the 0.5 m cell of the walkable map.)
walk_to() {
	local log="$OUT/$1.log" tx="$2" tz="$3" maxf="${4:-160}" near="${5:-1.0}"
	local held="" f0="" lastf="" sx="" sz="" sf="" side="" sidef=0 flip=0
	local t0; t0=$(date +%s)
	while :; do
		local line f x z want
		line=$(grep "^POS" "$log" | tail -1)
		f=$(sed -n 's/^POS f=\([0-9]*\) .*/\1/p' <<< "$line")
		if [ -z "$f" ] || [ "$f" = "$lastf" ]; then
			(( $(date +%s) - t0 > 1200 )) && { echo "walk_to $tx,$tz: the game stopped logging"; break; }
			sleep 0.1; continue
		fi
		lastf="$f"; [ -z "$f0" ] && f0="$f"
		x=$(sed -n 's/.*her=(\([-0-9.]*\), \([-0-9.]*\)).*/\1/p' <<< "$line")
		z=$(sed -n 's/.*her=(\([-0-9.]*\), \([-0-9.]*\)).*/\2/p' <<< "$line")
		want=$(awk -v x="$x" -v z="$z" -v tx="$tx" -v tz="$tz" -v near="$near" 'BEGIN{dx=tx-x; dz=tz-z; d=sqrt(dx*dx+dz*dz);
			if (d < near) { print "done"; exit } k="";
			if (dx > 0.38*d) k=k" d"; if (dx < -0.38*d) k=k" a"; if (dz > 0.38*d) k=k" s"; if (dz < -0.38*d) k=k" w"; print k}')
		[ "$want" = "done" ] && break
		(( f - f0 > maxf )) && { echo "walk_to $tx,$tz: gave up at $x,$z (frame $f)"; break; }
		if [ -z "$sf" ] || awk -v a="$sx" -v b="$sz" -v x="$x" -v z="$z" 'BEGIN{exit !((x-a)^2+(z-b)^2 > 0.04)}'; then
			sx="$x"; sz="$z"; sf="$f"; (( f > sidef )) && flip=0
		elif (( f - sf > 12 )); then
			# the side toward the target first (her minor axis to it), the other side if that fails too
			local minor; minor=$(awk -v x="$x" -v z="$z" -v tx="$tx" -v tz="$tz" -v w="$want" 'BEGIN{
				if (w ~ /[ad]/) print (tz >= z ? "s w" : "w s"); else print (tx >= x ? "d a" : "a d")}')
			side=$( ((flip)) && echo "${minor#* }" || echo "${minor% *}" )
			flip=$((1 - flip)); sidef=$((f + 8)); sf="$f"
		fi
		(( f > sidef )) && side=""
		[ -n "$side" ] && want="$want $side"
		for k in $held; do [[ " $want " == *" $k "* ]] || DISPLAY="$CASE_DISP" xdotool keyup "$k"; done
		for k in $want; do [[ " $held " == *" $k "* ]] || DISPLAY="$CASE_DISP" xdotool keydown "$k"; done
		held="$want"
	done
	for k in $held; do DISPLAY="$CASE_DISP" xdotool keyup "$k"; done
	grep "^POS" "$log" | tail -1
}
# hold_log <case> <key> <grep pattern> [max s]: hold a key until a line of the game's log (after the
# press) matches, at most max seconds
hold_log() {
	local log="$OUT/$1.log" key="$2" pat="$3" max="${4:-180}"
	local n0; n0=$(wc -l < "$log")
	DISPLAY="$CASE_DISP" xdotool keydown "$key"
	local t0; t0=$(date +%s)
	while :; do
		tail -n +"$((n0 + 1))" "$log" | grep -q -- "$pat" && break
		(( $(date +%s) - t0 > max )) && { echo "hold_log $key: no '$pat' in $max s"; break; }
		sleep 0.1
	done
	DISPLAY="$CASE_DISP" xdotool keyup "$key"
}
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
if [[ "$CASES" == *N* ]]; then
# ---- N: no characters (--nochar), round the home: from the hut door through the gate into the yard
# and back (fixed step: see walk_to)
GODOT_EXTRA="${GODOT_EXTRA:---fixed-fps 5}" run_case N --nochar --hours=12.5
shot N_0_hut_door
walk_to N -18.0 12.6
walk_to N -17.2 11.5 160 0.4
walk_to N -14.8 11.5 160 0.6; shot N_1_through_the_gate
walk_to N -11.0 11.6; shot N_2_yard
walk_to N -11.4 15.0; shot N_3_yard_south
walk_to N -14.8 11.5 160 0.6
walk_to N -17.2 11.5 160 0.6
walk_to N -18.4 13.5
walk_to N -19.6 14.6 160 0.6; shot N_4_back_at_the_door
finish
grep -h "POS\|SCRIPT ERROR\|SHADER ERROR" "$OUT/N.log" > "$OUT/N_pos.txt"
# ---- L: no characters, the lookout: down the spur onto the rock, standing still the view comes in;
# hold D (her head turns west), then S (the top-down view comes back)
GODOT_EXTRA="${GODOT_EXTRA:---fixed-fps 5}" run_case L --nochar --hours=12.5 --at=-21.4,30.6
shot L_0_top_of_the_spur
walk_to L -21.8 34.0
walk_to L -22.6 38.2
walk_to L -23.5 41.9 160 0.6; shot L_1_on_the_rock
# (standing still she looks out: wait for the game to say so, then for the white to clear)
for _ in $(seq 1 1200); do grep -q "VISTA on" "$OUT/L.log" 2>/dev/null && break; sleep 0.1; done
for _ in $(seq 1 3000); do grep -q "VISTA built" "$OUT/L.log" 2>/dev/null && break; sleep 0.1; done
n0=$(grep -c "vista=true" "$OUT/L.log"); for _ in $(seq 1 1200); do (( $(grep -c "vista=true" "$OUT/L.log") > n0 + 10 )) && break; sleep 0.1; done
shot L_2_looking_out
hold_log L d "vista=true.*yaw=2[0-9][0-9]"; sleep 2; shot L_3_after_D
hold_log L s "vista=false"; n0=$(grep -c "^POS" "$OUT/L.log"); for _ in $(seq 1 1200); do (( $(grep -c "^POS" "$OUT/L.log") > n0 + 10 )) && break; sleep 0.1; done
shot L_4_after_S
finish
grep -h "POS\|VISTA\|AUDIO\|SCRIPT ERROR\|SHADER ERROR" "$OUT/L.log" > "$OUT/L_pos.txt"
fi
for c in A B C; do [ -f "$OUT/$c.log" ] && grep -h "POS" "$OUT/$c.log" | head -60 > "$OUT/${c}_pos.txt"; done
[ -f "$OUT/D.log" ] && grep -h "POS\|VISTA" "$OUT/D.log" > "$OUT/D_pos.txt"
echo done
