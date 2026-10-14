#!/usr/bin/env bash
# Exports a project with the headless editor ($GODOT_BIN, built by build-editor.sh):
#   bash tools/godot/export.sh <project_dir> <preset name> <release|debug> <output file>
#   e.g. export.sh game Windows release /tmp/build/game.exe
#        export.sh game Android debug /tmp/build/game.apk
# The preset's custom_template/* paths must point at templates from build-templates.sh.
# Android signing: $GODOT_ANDROID_KEYSTORE_{DEBUG,RELEASE}_{PATH,USER,PASSWORD} when set, otherwise
# the shared debug key tools/godot/android/debug.keystore (alias androiddebugkey, password
# "android") for both debug and release. A fixed key lets a phone update the app in place across
# sessions; it is fine for sideloaded test builds, not for a store release (use a private key).
set -euo pipefail
. "$(dirname "$0")/common.sh"

PROJ="$(realpath "${1:?project dir}")"
PRESET="${2:?preset name}"
MODE="${3:?release or debug}"
OUTFILE="$(realpath -m "${4:?output file}")"
case "$MODE" in release|debug) ;; *) log "mode must be release or debug"; exit 2 ;; esac

KS="$TOOLS_GODOT/android/debug.keystore"
export GODOT_ANDROID_KEYSTORE_DEBUG_PATH="${GODOT_ANDROID_KEYSTORE_DEBUG_PATH:-$KS}"
export GODOT_ANDROID_KEYSTORE_DEBUG_USER="${GODOT_ANDROID_KEYSTORE_DEBUG_USER:-androiddebugkey}"
export GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD="${GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD:-android}"
export GODOT_ANDROID_KEYSTORE_RELEASE_PATH="${GODOT_ANDROID_KEYSTORE_RELEASE_PATH:-$KS}"
export GODOT_ANDROID_KEYSTORE_RELEASE_USER="${GODOT_ANDROID_KEYSTORE_RELEASE_USER:-androiddebugkey}"
export GODOT_ANDROID_KEYSTORE_RELEASE_PASSWORD="${GODOT_ANDROID_KEYSTORE_RELEASE_PASSWORD:-android}"

mkdir -p "$(dirname "$OUTFILE")"
# Import first: a fresh checkout has no .godot/imported cache, and exporting before the import
# has finished can miss resources.
"$GODOT_BIN" --headless --path "$PROJ" --import
start=$(date +%s)
"$GODOT_BIN" --headless --path "$PROJ" "--export-$MODE" "$PRESET" "$OUTFILE"
log "export took $(( $(date +%s) - start )) s"
ls -la "$(dirname "$OUTFILE")"
