#!/usr/bin/env bash
# Installs the lean Android SDK this Godot tag needs for building Android export templates and
# exporting APKs, into $ANDROID_HOME (default /home/user/godotengine/android-sdk):
#   cmdline-tools (latest), platform-tools, build-tools;36.1.0, platforms;android-36,
#   ndk;29.0.14206865  (versions from platform/android/java/app/config.gradle of 4.7.2-stable)
#   bash tools/godot/setup-android-sdk.sh
# Accepts the SDK licenses non-interactively (sdkmanager --licenses). Java tools reach the network
# through the proxy settings in JAVA_TOOL_OPTIONS; JDK 21 works (Godot needs >= 17).
# cmdline-tools is pinned to 19.0, the last release with the classic sdkmanager: from 22.0/23.0 on,
# sdkmanager forwards to the new "Android CLI", which downloads ~250 MB more into ~/.android and
# has its own usage-metrics switch (--no-metrics).
# Downloads about 1.05 GB (NDK 747 MiB) from dl.google.com; re-running skips what is installed.
set -euo pipefail
. "$(dirname "$0")/common.sh"

ANDROID_HOME="${ANDROID_HOME:-$GODOT_HOME/android-sdk}"
CMDLINE_ZIP=commandlinetools-linux-13114758_latest.zip       # cmdline-tools 19.0
CMDLINE_SHA1=5fdcc763663eefb86a5b8879697aa6088b041e70          # from repository2-3.xml
PACKAGES=("platform-tools" "build-tools;36.1.0" "platforms;android-36" "ndk;29.0.14206865")

SDKMANAGER="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
if [ ! -x "$SDKMANAGER" ]; then
  tmp="$(mktemp -d)"
  log "downloading $CMDLINE_ZIP"
  curl -fsSL -o "$tmp/$CMDLINE_ZIP" "https://dl.google.com/android/repository/$CMDLINE_ZIP"
  echo "$CMDLINE_SHA1  $tmp/$CMDLINE_ZIP" | sha1sum -c -
  mkdir -p "$ANDROID_HOME/cmdline-tools"
  unzip -q "$tmp/$CMDLINE_ZIP" -d "$tmp"
  rm -rf "$ANDROID_HOME/cmdline-tools/latest"
  mv "$tmp/cmdline-tools" "$ANDROID_HOME/cmdline-tools/latest"
  rm -rf "$tmp"
fi
# `yes` dies of SIGPIPE when sdkmanager stops reading; that is expected.
yes | "$SDKMANAGER" --sdk_root="$ANDROID_HOME" --licenses >/dev/null || true
"$SDKMANAGER" --sdk_root="$ANDROID_HOME" --install "${PACKAGES[@]}"
"$SDKMANAGER" --sdk_root="$ANDROID_HOME" --list_installed
du -sh "$ANDROID_HOME" "$ANDROID_HOME"/* 2>/dev/null
