#!/usr/bin/env bash
# The smoke playtest of the Godot project, in one command (docs/knowledge/16-godot-architecture.md):
#   bash tools/godot/playtest.sh [out_dir]
# Runs the unit tests, then tools/godot/smoke_bot.py twice with real X input on Xvfb (Mesa software
# Vulkan, Mobile renderer): keyboard at 1280x720, and touch (mouse-emulated) at a phone-landscape
# 1200x540 with the touch UI on. One Godot process at a time. Screenshots and logs go to out_dir
# (default: $TMPDIR/godot-playtest). Exit code 1 when anything failed.
set -uo pipefail
. "$(dirname "$0")/common.sh"
OUT="${1:-${TMPDIR:-/tmp}/godot-playtest}"
mkdir -p "$OUT"
HERE="$(cd "$(dirname "$0")" && pwd)"
fail=0
bash "$HERE/test.sh" || fail=1
GODOT_BIN="$GODOT_BIN" python3 -I "$HERE/smoke_bot.py" --out "$OUT" --size 1280x720 --mode keys --display :93 || fail=1
GODOT_BIN="$GODOT_BIN" python3 -I "$HERE/smoke_bot.py" --out "$OUT" --size 1200x540 --mode touch --display :94 || fail=1
echo "playtest output: $OUT"
[ "$fail" = 0 ] && echo "PLAYTEST PASS" || echo "PLAYTEST FAIL"
exit "$fail"
