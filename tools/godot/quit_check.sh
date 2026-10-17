#!/usr/bin/env bash
# Leaving a 3D scene must not crash an exported game (knowledge/16 section 12, 9): engine callbacks
# that land after the scene (or the script languages) are gone crash only the release build, and
# only when one is in flight at that moment, so each case runs several times.
#   bash tools/godot/quit_check.sh <tengan.x86_64 | tengan.exe> <out dir> [runs=3]
# Per run, with real keys (xdotool) on a private Xvfb: menu -> Enter (the home area) -> wait, then
#   esc:   Esc back to the menu; the engine must still be running 20 s later;
#   close: the window's close button (WM_DELETE_WINDOW, quit_check/closewin.c); the engine must
#          exit with code 0 within 40 s.
# Exit code 1 when any run fails. Software rendering: each run takes about a minute and a half.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
BIN="$(realpath "$1")"; OUT="$(realpath -m "$2")"; RUNS="${3:-3}"
mkdir -p "$OUT"
CW="$OUT/closewin"
gcc -O2 -o "$CW" "$HERE/quit_check/closewin.c" -lX11 || { echo "cannot build closewin (gcc, libx11-dev)"; exit 1; }
WINE=/usr/lib/wine/wine64
# the same prefix and overrides as showcase_check.py (dinput8 off: wine 9.0 crashes in Godot's joypad
# init, knowledge/10 section 5.2)
export WINEPREFIX=/home/user/godotengine/wine-prefix WINEDEBUG=-all WINEDLLOVERRIDES="mscoree,mshtml=;dinput8=d;winedbg.exe=d"
fails=0
one() {   # one <case> <run>
	local kind="$1" n="$2" dir="$OUT/$1_$2"
	mkdir -p "$dir"
	export DISPLAY=":$((150 + RANDOM % 40))"
	Xvfb "$DISPLAY" -screen 0 1920x1080x24 -nolisten tcp -noreset >/dev/null 2>&1 &
	local xp=$!
	sleep 2
	"$CW" 0          # the close atoms must exist before the game starts (no window manager here)
	if [[ "$BIN" == *.exe ]]; then
		"$WINE" "$BIN" > "$dir/log.txt" 2>&1 &
	else
		"$BIN" > "$dir/log.txt" 2>&1 &
	fi
	local gp=$!
	sleep 20
	local w
	w=$(xdotool search --onlyvisible --pid $gp 2>/dev/null | tail -1)
	[ -z "$w" ] && w=$(xdotool search --onlyvisible --name "天岸" 2>/dev/null | tail -1)   # (wine: another process)
	xdotool windowactivate --sync "$w" >/dev/null 2>&1; xdotool windowfocus "$w" >/dev/null 2>&1
	xdotool key Return
	sleep 45
	local verdict
	if [ "$kind" = esc ]; then
		xdotool key Escape
		sleep 20
		if kill -0 $gp 2>/dev/null; then verdict="ok: still running after Esc"; else wait $gp; verdict="FAIL: exited with code $? after Esc"; fi
	else
		"$CW" "$w"
		verdict="FAIL: still running 40 s after the close request"
		for _ in $(seq 1 40); do
			if ! kill -0 $gp 2>/dev/null; then
				wait $gp; local code=$?
				if [ $code -eq 0 ]; then verdict="ok: exited with code 0"; else verdict="FAIL: exited with code $code"; fi
				break
			fi
			sleep 1
		done
	fi
	# (the case only counts when the home area had loaded: its GI bake is in the log)
	grep -q "GI baked" "$dir/log.txt" || verdict="FAIL: the home area never loaded ($verdict)"
	kill $gp 2>/dev/null; [[ "$BIN" == *.exe ]] && /usr/lib/wine/wineserver64 -k >/dev/null 2>&1
	kill $xp 2>/dev/null
	echo "$kind $n: $verdict"
	[[ "$verdict" == ok:* ]] || fails=$((fails + 1))
}
for n in $(seq 1 "$RUNS"); do one esc "$n"; one close "$n"; done
echo "failures: $fails"
[ $fails -eq 0 ]
