#!/usr/bin/env bash
# Builds export templates for the native targets and installs them under the official file names
# in $GODOT_OUT/templates (default /home/user/godotengine/out/templates):
#   linux   -> linux_release.x86_64, linux_debug.x86_64          (for running exported builds here)
#   windows -> windows_release_x86_64.exe, windows_debug_x86_64.exe and their _console.exe wrappers
#              (cross-compiled with mingw-w64, posix threads: apt g++-mingw-w64-x86-64-posix)
#   android -> android_release.apk, android_debug.apk, android_source.zip (arm64-v8a only;
#              needs setup-android-sdk.sh first; Gradle downloads into $GODOT_HOME/gradle)
#   bash tools/godot/build-templates.sh <linux|windows|android> [release|debug|both]   (default both)
# Every module stays in: the Advanced text server with ICU, FreeType, all image and audio formats,
# GDScript, and 3D. disable_3d=yes would also remove WorldEnvironment (registered in the 3D section
# of scene/register_scene_types.cpp), which 2D glow, HDR tonemapping and color adjustments need.
# production=yes with lto=none: LTO (production's default on Linux/Windows with GCC) is left for the
# final distribution build; see docs/knowledge/10-godot-toolchain.md for times and sizes.
# Not available here (prebuilt SDKs are GitHub release assets, blocked in this container): ANGLE
# and Direct3D 12 on Windows (angle=no d3d12=no: Vulkan + native OpenGL remain), AccessKit.
set -euo pipefail
. "$(dirname "$0")/common.sh"

PLATFORM="${1:-}"
WHICH="${2:-both}"
case "$WHICH" in release) TARGETS=(release) ;; debug) TARGETS=(debug) ;; both) TARGETS=(debug release) ;;
  *) log "usage: $0 <linux|windows|android> [release|debug|both]"; exit 2 ;; esac

COMMON=(production=yes lto=none scu_build=yes)
case "$PLATFORM" in
  linux) FLAGS=(platform=linuxbsd arch=x86_64 linker=lld wayland=no accesskit=no) ;;
  windows) FLAGS=(platform=windows arch=x86_64 use_mingw=yes d3d12=no angle=no accesskit=no) ;;
  android)
    FLAGS=(platform=android arch=arm64)
    export ANDROID_HOME="${ANDROID_HOME:-$GODOT_HOME/android-sdk}"
    export GRADLE_USER_HOME="${GRADLE_USER_HOME:-$GODOT_HOME/gradle}"
    [ -d "$ANDROID_HOME/ndk" ] || { log "no NDK in $ANDROID_HOME; run setup-android-sdk.sh"; exit 1; }
    ;;
  *) log "usage: $0 <linux|windows|android> [release|debug|both]"; exit 2 ;;
esac

godot_fetch_source
ensure_scons
DEST="$GODOT_OUT/templates"
mkdir -p "$DEST"
cd "$GODOT_SRC"
for t in "${TARGETS[@]}"; do
  log "[$PLATFORM] scons ${FLAGS[*]} ${COMMON[*]} target=template_$t -j$JOBS"
  start=$(date +%s)
  scons "${FLAGS[@]}" "${COMMON[@]}" target="template_$t" -j"$JOBS"
  log "[$PLATFORM] template_$t build step took $(( $(date +%s) - start )) s"
  case "$PLATFORM" in
    linux)
      install -m 755 "bin/godot.linuxbsd.template_$t.x86_64" "$DEST/linux_$t.x86_64"
      log "$DEST/linux_$t.x86_64 $(size_of "$DEST/linux_$t.x86_64")" ;;
    windows)
      install -m 755 "bin/godot.windows.template_$t.x86_64.exe" "$DEST/windows_${t}_x86_64.exe"
      install -m 755 "bin/godot.windows.template_$t.x86_64.console.exe" "$DEST/windows_${t}_x86_64_console.exe"
      log "$DEST/windows_${t}_x86_64.exe $(size_of "$DEST/windows_${t}_x86_64.exe")" ;;
  esac
done

if [ "$PLATFORM" = android ]; then
  # Packs the libgodot_android.so files built above (platform/android/java/lib/libs/<target>/)
  # into the APK templates. Only targets whose .so exists are packaged.
  log "[android] gradlew generateGodotTemplates (JDK: $(java -version 2>&1 | grep -m1 version))"
  # Maven Central sometimes answers 429 Too Many Requests when Gradle fetches many artifacts at
  # once; Gradle keeps what it already downloaded, so a plain retry gets through.
  start=$(date +%s)
  for attempt in 1 2 3; do
    (cd platform/android/java && ./gradlew --no-daemon generateGodotTemplates) && break
    [ "$attempt" = 3 ] && { log "[android] gradle failed 3 times"; exit 1; }
    log "[android] gradle failed (attempt $attempt), retrying in 30 s"
    sleep 30
  done
  log "[android] gradle step took $(( $(date +%s) - start )) s"
  for f in android_debug.apk android_release.apk android_source.zip; do
    if [ -f "bin/$f" ]; then
      install -m 644 "bin/$f" "$DEST/$f"
      log "$DEST/$f $(size_of "$DEST/$f")"
    fi
  done
fi
