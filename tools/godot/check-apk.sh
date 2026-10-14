#!/usr/bin/env bash
# Prints what matters in an exported APK: size, ABIs, minSdk/targetSdk, orientation, Vulkan
# features, the Godot renderer metadata, the largest entries, and the signing certificate.
#   bash tools/godot/check-apk.sh <file.apk>
# Uses aapt2 and apksigner from build-tools 36.1.0 (setup-android-sdk.sh).
set -euo pipefail
. "$(dirname "$0")/common.sh"
APK="${1:?apk}"
BT="$ANDROID_HOME/build-tools/36.1.0"
echo "== size: $(size_of "$APK")"
echo "== badging"
"$BT/aapt2" dump badging "$APK" 2>/dev/null | grep -E "^(package|sdkVersion|targetSdkVersion|application-label:|native-code|uses-feature|uses-permission|launchable-activity)" || true
echo "== manifest (orientation 11 = userLandscape, 6 = sensorLandscape, 0 = landscape)"
"$BT/aapt2" dump xmltree --file AndroidManifest.xml "$APK" 2>/dev/null \
  | grep -E -A1 "screenOrientation|vulkan|rendering.method|minSdkVersion|targetSdkVersion|E: (uses-feature|meta-data|activity)" \
  | grep -E "screenOrientation|vulkan|rendering|SdkVersion|android:name|android:value|android:required|android:version" | sed 's/^ */  /' | head -40
echo "== largest entries"
unzip -lv "$APK" | sort -k1 -n -r | head -12
echo "== signature"
"$BT/apksigner" verify --print-certs "$APK" 2>&1 | grep -v "^WARNING: META-INF" | head -6
