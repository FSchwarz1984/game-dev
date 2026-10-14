#!/usr/bin/env bash
# Builds the Godot editor for Linux x86_64 as a headless tool: project import, --export-release /
# --export-debug, and running scripts (--headless --script). It has no X11/Wayland window, no
# audio, gamepad, D-Bus, fontconfig or screen-reader drivers, so it needs no -dev packages: only
# gcc/g++, pkg-config, python3 + SCons (and lld for the link).
#   bash tools/godot/build-editor.sh          -> $GODOT_OUT/godot-editor (default /home/user/godotengine/out)
#   XZ=1 bash tools/godot/build-editor.sh     also writes godot-editor.xz and prints its size
# Re-running is cheap: the clone is only verified and SCons rebuilds nothing when up to date.
# Measured 2026-10-14 (4 CPUs, 15 GB RAM): see docs/knowledge/10-godot-toolchain.md.
set -euo pipefail
. "$(dirname "$0")/common.sh"

godot_fetch_source
ensure_scons

# production=yes: release defaults (static libstdc++, no debug symbols, stripped binary).
# lto=none:       production would pick GCC full LTO; for a headless export tool its speed does not
#                 matter, and the LTO link of the whole editor needs most of the 15 GB RAM and adds
#                 a long single-threaded link step.
# scu_build=yes:  single-compilation-unit build (8 files per unit), far fewer header re-parses.
# linker=lld:     much faster final link than GNU ld.
# The *=no flags drop drivers a headless tool never uses; with the default use_sowrap=yes they
# would not need -dev packages either, but they would still be compiled and dlopen'ed.
FLAGS=(
  platform=linuxbsd target=editor arch=x86_64
  production=yes lto=none scu_build=yes linker=lld
  x11=no wayland=no
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
