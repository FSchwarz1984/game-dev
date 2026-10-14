#!/usr/bin/env bash
# Runs the Godot project's headless unit tests (godot/tests/test_*.gd through godot/tests/run.gd):
#   bash tools/godot/test.sh                  all tests
#   bash tools/godot/test.sh field            only files whose name contains "field"
# Imports the project first when it has never been imported (a fresh checkout has no .godot/), so
# class_name globals and imported resources (the region masks) resolve. Exit code 1 on failure.
set -euo pipefail
. "$(dirname "$0")/common.sh"
PROJ="$(cd "$(dirname "$0")/../../godot" && pwd)"
if [ ! -f "$PROJ/.godot/global_script_class_cache.cfg" ] || [ "${REIMPORT:-0}" = "1" ]; then
  "$GODOT_BIN" --headless --path "$PROJ" --import >/dev/null 2>&1 || true
fi
ARGS=()
[ -n "${1:-}" ] && ARGS=(-- "--only=$1")
"$GODOT_BIN" --headless --path "$PROJ" -s res://tests/run.gd "${ARGS[@]}"
