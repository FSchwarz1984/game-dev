#!/usr/bin/env bash
# Exports the game (godot/) for Windows, Android and Linux with the official 4.7.2 templates, then
# checks the APK:
#   bash tools/godot/export-game.sh [out_dir] [release|debug]
# Default out_dir: godot/export/ (git-ignored). Uses tools/godot/export.sh per preset (it imports
# first and signs the APK with the shared debug key tools/godot/android/debug.keystore unless the
# GODOT_ANDROID_KEYSTORE_* variables say otherwise). One Godot process at a time.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"
PROJ="$(cd "$HERE/../../godot" && pwd)"
OUT="$(realpath -m "${1:-$PROJ/export}")"
MODE="${2:-release}"
mkdir -p "$OUT/linux" "$OUT/windows" "$OUT/android"
bash "$HERE/export.sh" "$PROJ" Linux "$MODE" "$OUT/linux/tengan.x86_64"
bash "$HERE/export.sh" "$PROJ" Windows "$MODE" "$OUT/windows/tengan.exe"
bash "$HERE/export.sh" "$PROJ" Android "$MODE" "$OUT/android/tengan.apk"
echo "== exports"
for f in "$OUT"/linux/* "$OUT"/windows/* "$OUT"/android/*; do
  [ -f "$f" ] && echo "$(size_of "$f")  $f"
done
echo "== APK"
bash "$HERE/check-apk.sh" "$OUT/android/tengan.apk"
