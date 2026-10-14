#!/usr/bin/env bash
# Installs the apt packages the Godot toolchain needs in a fresh container (Ubuntu 24.04):
#   run time of the X11 editor and of exported Linux builds, software rendering under Xvfb
#   (Mesa lavapipe = Vulkan, llvmpipe = OpenGL), input driving and screenshots, and the mingw-w64
#   cross compiler for Windows templates. About 560 MB installed; build-time -dev packages are not
#   needed (Godot loads X11/GL/Vulkan through its own soname wrappers).
#   bash tools/godot/setup-runtime.sh            WINE=1 also installs wine64 (~650 MB) to smoke-test
#                                                Windows builds
set -euo pipefail
PKGS=(
  xvfb xauth libx11-6 libxcursor1 libxinerama1 libxrandr2 libxi6 libxext6 libxrender1 libxkbcommon0
  libgl1 libegl1 libglx-mesa0 libgl1-mesa-dri mesa-vulkan-drivers libvulkan1 vulkan-tools mesa-utils
  xdotool x11-utils x11-apps imagemagick
  gcc-mingw-w64-x86-64-posix g++-mingw-w64-x86-64-posix
  lld pkg-config unzip
)
[ "${WINE:-0}" = 1 ] && PKGS+=(wine64)
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
