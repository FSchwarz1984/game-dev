#!/usr/bin/env bash
# Builds the size-optimized, single-threaded Web export templates (wasm32, no pthreads) with the
# module set in tools/godot/custom.py, and packages them under the names the editor expects.
#   bash tools/godot/build-web-template.sh [release|debug|both]        (default: release)
#   GODOT_TEXT_SERVER=adv bash tools/godot/build-web-template.sh        Advanced text server variant
# Output: $GODOT_OUT/templates/<fb|adv>/web_nothreads_release.zip and web_nothreads_debug.zip
# (each holds godot.js, godot.wasm, godot.audio.worklet.js, godot.audio.position.worklet.js,
# godot.html and the PWA files the exporter skips when PWA is off). Point an export preset at them
# with custom_template/release and custom_template/debug (export-web.sh does this).
# Object files are cached in $GODOT_HOME/scons-cache, so switching the text server or rebuilding
# after a new session with the same cache only recompiles what changed.
set -euo pipefail
. "$(dirname "$0")/common.sh"

WHICH="${1:-release}"
TS="${GODOT_TEXT_SERVER:-fb}"
case "$WHICH" in release) TARGETS=(release) ;; debug) TARGETS=(debug) ;; both) TARGETS=(release debug) ;;
  *) log "usage: $0 [release|debug|both]"; exit 2 ;; esac
case "$TS" in fb|adv) ;; *) log "GODOT_TEXT_SERVER must be fb or adv"; exit 2 ;; esac
export GODOT_TEXT_SERVER="$TS"

godot_fetch_source
ensure_scons
[ -f "$EMSDK_DIR/emsdk_env.sh" ] || bash "$TOOLS_GODOT/install-emsdk.sh"
# shellcheck disable=SC1091
. "$EMSDK_DIR/emsdk_env.sh" >/dev/null 2>&1
emcc --version | head -1 | grep -q " $EM_VERSION " || { log "emcc is not $EM_VERSION; run install-emsdk.sh"; exit 1; }

DEST="$GODOT_OUT/templates/$TS"
mkdir -p "$DEST" "$GODOT_HOME/scons-cache"
cd "$GODOT_SRC"
for t in "${TARGETS[@]}"; do
  # On the command line because platform flags / production would override them in the profile
  # (see the header of custom.py).
  FLAGS=(platform=web target="template_$t" arch=wasm32 production=yes optimize=size_extra lto=full
    profile="$TOOLS_GODOT/custom.py" cache_path="$GODOT_HOME/scons-cache")
  log "[$TS] scons ${FLAGS[*]} -j$JOBS"
  start=$(date +%s)
  scons "${FLAGS[@]}" -j"$JOBS"
  end=$(date +%s)
  log "[$TS] template_$t build step took $((end - start)) s"
  install -m 644 "bin/godot.web.template_$t.wasm32.nothreads.zip" "$DEST/web_nothreads_$t.zip"
  log "[$TS] $DEST/web_nothreads_$t.zip $(size_of "$DEST/web_nothreads_$t.zip")"
  unzip -l "$DEST/web_nothreads_$t.zip" | sed 's/^/    /'
done
