#!/usr/bin/env bash
# W-1 (2026-10-14): the web target was dropped (native Windows + Android instead). Kept for
# reference only; this script was run once and installed Emscripten 4.0.11 without problems.
# Installs and activates the Emscripten SDK version this Godot tag is built with in CI
# (EM_VERSION in common.sh) into $EMSDK_DIR (default /home/user/godotengine/emsdk).
#   bash tools/godot/web/install-emsdk.sh
# Then, in a shell that builds web templates:  source "$EMSDK_DIR/emsdk_env.sh"
# (build-web-template.sh does this itself). Downloads come from storage.googleapis.com
# (about 300 MB); re-running with the version already installed only re-activates it.
set -euo pipefail
. "$(dirname "$0")/../common.sh"

if [ ! -d "$EMSDK_DIR/.git" ]; then
  mkdir -p "$(dirname "$EMSDK_DIR")"
  git clone --depth 1 https://github.com/emscripten-core/emsdk "$EMSDK_DIR"
fi
cd "$EMSDK_DIR"
./emsdk install "$EM_VERSION"
./emsdk activate "$EM_VERSION"
# shellcheck disable=SC1091
. ./emsdk_env.sh >/dev/null 2>&1
emcc --version | head -1
