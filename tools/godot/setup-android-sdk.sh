#!/usr/bin/env bash
# Installs a lean Android SDK for exporting APKs with Godot 4.7.2's prebuilt Android templates
# (setup-godot.sh), into $ANDROID_HOME (default /home/user/godotengine/android-sdk):
#   default   cmdline-tools 19.0, platform-tools, build-tools;36.1.0 (apksigner), platforms;android-36
#             about 480 MB; enough for the standard ("prebuilt APK") export, which signs with
#             apksigner and the JDK's keytool. The NDK is not used by that export.
#   FULL=1    also ndk;29.0.14206865 (+2.4 GB) and cmake;3.10.2.4988404, for Gradle "custom builds",
#             native Android plugins, or building templates from source (build-templates.sh).
#   bash tools/godot/setup-android-sdk.sh            FULL=1 bash tools/godot/setup-android-sdk.sh
# Versions follow the engine's own Gradle config (platform/android/java/app/config.gradle of
# 4.7.2-stable: compileSdk/targetSdk 36, buildTools 36.1.0, ndkVersion 29.0.14206865, Java >= 17).
# The 4.7 docs page (tutorials/export/exporting_for_android.rst) still lists the older build-tools
# 35.0.1, platform 35 and NDK r28b; the engine's values win for Gradle builds.
# JDK: the system JDK 21 works (the docs recommend 17; "higher versions are also supported").
# Accepts the SDK licenses non-interactively. Java tools reach the network through the proxy
# settings in JAVA_TOOL_OPTIONS.
# cmdline-tools is pinned to 19.0, the last release with the classic sdkmanager: from 22.0/23.0 on,
# sdkmanager forwards to the new "Android CLI", which downloads ~250 MB more into ~/.android and
# has its own usage-metrics switch (--no-metrics).
# Re-running only installs what is missing.
set -euo pipefail
. "$(dirname "$0")/common.sh"

CMDLINE_ZIP=commandlinetools-linux-13114758_latest.zip       # cmdline-tools 19.0
CMDLINE_SHA1=5fdcc763663eefb86a5b8879697aa6088b041e70          # from repository2-3.xml
PACKAGES=("platform-tools" "build-tools;36.1.0" "platforms;android-36")
[ "${FULL:-0}" = 1 ] && PACKAGES+=("ndk;29.0.14206865" "cmake;3.10.2.4988404")

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
"$SDKMANAGER" --sdk_root="$ANDROID_HOME" --install "${PACKAGES[@]}" | grep -v "^\[=*" || true
"$SDKMANAGER" --sdk_root="$ANDROID_HOME" --list_installed 2>/dev/null | sed -n '/Installed packages/,$p'
du -sh "$ANDROID_HOME" 2>/dev/null
# Point an existing editor settings file at this SDK and $JAVA_HOME.
godot_editor_settings_android
