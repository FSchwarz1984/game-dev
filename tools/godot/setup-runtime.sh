#!/usr/bin/env bash
# Installs the apt packages the Godot toolchain needs in a fresh container (Ubuntu 24.04):
#   default   run time of the official editor and of exported Linux builds, software rendering
#             under Xvfb (Mesa: lavapipe = Vulkan for Forward+/Mobile, llvmpipe = OpenGL for
#             Compatibility), input driving and screenshots (xdotool, ImageMagick). ~110 MB on top
#             of what the image already has.
#   WINE=1    also wine64 (~650 MB) to smoke-test Windows exports (xvfb-playtest.sh <game.exe>)
#   SOURCE=1  also the compilers for the fallback source builds (build-editor.sh,
#             build-templates.sh): mingw-w64 posix-thread g++ for Windows (~440 MB), lld, pkg-config
#   bash tools/godot/setup-runtime.sh
set -euo pipefail
PKGS=(
  xvfb xauth libx11-6 libxcursor1 libxinerama1 libxrandr2 libxi6 libxext6 libxrender1 libxkbcommon0
  libgl1 libegl1 libglx-mesa0 libgl1-mesa-dri mesa-vulkan-drivers libvulkan1 vulkan-tools mesa-utils
  xdotool x11-utils x11-apps imagemagick unzip
)
[ "${WINE:-0}" = 1 ] && PKGS+=(wine64)
[ "${SOURCE:-0}" = 1 ] && PKGS+=(gcc-mingw-w64-x86-64-posix g++-mingw-w64-x86-64-posix lld pkg-config)
missing=()
for p in "${PKGS[@]}"; do
  dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "install ok installed" || missing+=("$p")
done
if [ ${#missing[@]} -gt 0 ]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -q
  apt-get install -y -q --no-install-recommends "${missing[@]}"
fi
echo "runtime packages ok"
