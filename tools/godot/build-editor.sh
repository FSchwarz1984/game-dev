#!/usr/bin/env bash
# Builds the Godot editor for Linux x86_64. It runs headless (import, --export-release/--export-debug,
# --script) and also runs the game in a real X11 window, e.g. under Xvfb with Mesa's software
# Vulkan (lavapipe, Forward+/Mobile renderers) or software GL (llvmpipe, Compatibility renderer)
# for screenshots and playtests (see run-xvfb.sh).
#   bash tools/godot/build-editor.sh          -> $GODOT_OUT/godot-editor (default /home/user/godotengine/out)
#   XZ=1 bash tools/godot/build-editor.sh     also writes godot-editor.xz and prints its size
# Build-time needs: gcc/g++, pkg-config, lld, python3 + SCons. No -dev packages: X11, GL and Vulkan
# are loaded at run time through Godot's soname wrappers (use_sowrap=yes, the default).
# Run-time needs (apt, installed by setup-runtime.sh): libx11-6 libxcursor1 libxinerama1 libxrandr2
# libxi6 libxext6 libxrender1 libgl1 libegl1 libvulkan1, Mesa drivers for software rendering.
# Re-running is cheap: the clone is only verified and SCons rebuilds nothing when up to date.
# Measured 2026-10-14 (4 CPUs, 15 GB RAM): see docs/knowledge/10-godot-toolchain.md.
set -euo pipefail
. "$(dirname "$0")/common.sh"

godot_fetch_source
ensure_scons

# production=yes: release defaults (static libstdc++, no debug symbols, stripped binary).
# lto=none:       production would pick GCC full LTO; the editor is a tool here, and the LTO link of
#                 the whole editor needs most of the 15 GB RAM plus a long single-threaded link.
# scu_build=yes:  single-compilation-unit build (8 files per unit), far fewer header re-parses.
# linker=lld:     much faster final link than GNU ld.
# x11=yes with Vulkan and OpenGL (defaults) for real rendering; Wayland, audio (no sound device in
# the container), D-Bus, speech, fontconfig, udev, SDL joypads and the screen reader stay off.
FLAGS=(
  platform=linuxbsd target=editor arch=x86_64
  production=yes lto=none scu_build=yes linker=lld
  x11=yes wayland=no
  alsa=no pulseaudio=no dbus=no speechd=no fontconfig=no udev=no sdl=no accesskit=no
)

cd "$GODOT_SRC"
log "scons ${FLAGS[*]} -j$JOBS"
start=$(date +%s)
scons "${FLAGS[@]}" -j"$JOBS"
end=$(date +%s)
log "build step took $((end - start)) s"

BIN="$GODOT_SRC/bin/godot.linuxbsd.editor.x86_64"
mkdir -p "$GODOT_OUT"
install -m 755 "$BIN" "$GODOT_BIN"
log "editor: $GODOT_BIN $(size_of "$GODOT_BIN")"
"$GODOT_BIN" --headless --version

if [ "${XZ:-0}" = 1 ]; then
  xz -T"$JOBS" -9 -k -f "$GODOT_BIN"
  log "xz -9: $GODOT_BIN.xz $(size_of "$GODOT_BIN.xz")"
fi
