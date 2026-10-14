#!/usr/bin/env bash
# Installs the official Godot 4.7.2-stable Linux editor and the export templates this project uses,
# after checking every download against the SHA512 published in github.com/godotengine/godot-builds
# (releases/godot-4.7.2-stable.json). Safe to run at the start of every session (the container is
# ephemeral): what is already installed and unchanged is not downloaded again.
#   bash tools/godot/setup-godot.sh
#   TEMPLATES="windows android" bash tools/godot/setup-godot.sh   choose template groups
#   ANDROID_SOURCE=1 ...   also android_source.zip (204 MiB; only for Gradle "custom builds")
# Installs:
#   editor     $GODOT_BIN = $GODOT_HOME/editor/Godot_v4.7.2-stable_linux.x86_64   (146 MiB)
#   templates  ~/.local/share/godot/export_templates/4.7.2.stable/, only:
#     windows  windows_{release,debug}_x86_64.exe + _console.exe wrappers (ANGLE, D3D12 included)
#     android  android_{release,debug}.apk (all four ABIs; the exporter keeps the selected ones)
#     linux    linux_{release,debug}.x86_64
#     always   version.txt, icudt_godot.dat (ICU line-breaking data the exporter puts in the .pck)
# The templates come in one 1222 MiB .tpz; it is verified, the needed members are extracted, and it
# is deleted. Downloads go only to downloads.godotengine.org (which redirects to Godot's release
# storage); the checksums come from a shallow git checkout of godot-builds.
set -euo pipefail
. "$(dirname "$0")/common.sh"

TEMPLATES="${TEMPLATES:-windows android linux}"
EDITOR_ZIP="Godot_v${GODOT_VERSION}-${GODOT_FLAVOR}_linux.x86_64.zip"
TPZ="Godot_v${GODOT_VERSION}-${GODOT_FLAVOR}_export_templates.tpz"
# SHA512 values copied from godot-builds on 2026-10-14. They are cross-checked against a fresh
# checkout below; when GitHub cannot be reached these pinned values are used alone.
declare -A PINNED=(
  ["Godot_v4.7.2-stable_linux.x86_64.zip"]=9aa00f7a605200940bce3027a567b782f49bd8e940dd06ae9e987bd65aee1b1467edd56ed84fcdcbdd44354bf613bdbb4e5d2913e925850368e150c59ed54c65
  ["Godot_v4.7.2-stable_export_templates.tpz"]=ca4d71c4d7b81dfc15d1a98baa07534aa95b03fdda78a0075b06672e1648d2e5f40980c9adc28d23e1b92e732ee7bf3461997aa804af74ec2fcd7a93ccb84079
)
DL="$GODOT_HOME/downloads"
EDIR="$(dirname "$GODOT_BIN")"
mkdir -p "$DL" "$EDIR" "$GODOT_TEMPLATES_DIR"

# --- checksums ------------------------------------------------------------------------------------
BUILDS="$GODOT_HOME/godot-builds"
RELJSON="releases/godot-${GODOT_VERSION}-${GODOT_FLAVOR}.json"
have_json=0
if [ ! -d "$BUILDS/.git" ]; then
  git clone -q --depth 1 --filter=blob:none --no-checkout https://github.com/godotengine/godot-builds "$BUILDS" 2>/dev/null || true
else
  git -C "$BUILDS" fetch -q --depth 1 origin 2>/dev/null && git -C "$BUILDS" reset -q --soft FETCH_HEAD 2>/dev/null || true
fi
if [ -d "$BUILDS/.git" ] && git -C "$BUILDS" checkout -q HEAD -- "$RELJSON" 2>/dev/null; then
  have_json=1
else
  log "godot-builds not reachable; using the pinned SHA512 values only"
fi

# Prints the expected SHA512 of a release file; aborts if godot-builds and the pin disagree.
sha512_for() {
  local name="$1" pinned="${PINNED[$1]:-}" published=""
  if [ "$have_json" = 1 ]; then
    published="$(python3 -I -c 'import json, sys
d = json.load(open(sys.argv[1]))
print(next((f["checksum"] for f in d["files"] if f["filename"] == sys.argv[2]), ""))' "$BUILDS/$RELJSON" "$name")"
  fi
  if [ -n "$published" ] && [ -n "$pinned" ] && [ "$published" != "$pinned" ]; then
    log "SHA512 for $name differs between godot-builds and the pinned value; refusing to continue"
    exit 1
  fi
  local sum="${published:-$pinned}"
  [ -n "$sum" ] || { log "no SHA512 known for $name"; exit 1; }
  echo "$sum"
}

# Downloads a release file from downloads.godotengine.org and verifies it.
fetch_verified() {
  local name="$1" slug="$2" platform="$3" sum
  sum="$(sha512_for "$name")" || exit 1
  if [ -f "$DL/$name" ] && echo "$sum  $DL/$name" | sha512sum -c --status -; then
    log "$name already downloaded and verified"
    return 0
  fi
  log "downloading $name"
  curl -fL --proto =https --proto-redir =https --retry 3 -sS -A "TenganAssetBuild/1.0" \
    -o "$DL/$name.part" \
    "https://downloads.godotengine.org/?version=${GODOT_VERSION}&flavor=${GODOT_FLAVOR}&slug=${slug}&platform=${platform}"
  if ! echo "$sum  $DL/$name.part" | sha512sum -c --status -; then
    rm -f "$DL/$name.part"
    log "SHA512 mismatch for $name; download discarded"
    exit 1
  fi
  mv "$DL/$name.part" "$DL/$name"
  log "$name: SHA512 OK ($(size_of "$DL/$name"))"
}

# --- editor ---------------------------------------------------------------------------------------
# Assignments (not conditions) so that set -e stops the script when no checksum is known.
EDITOR_SUM="$(sha512_for "$EDITOR_ZIP")"
TPZ_SUM="$(sha512_for "$TPZ")"
ESTAMP="$EDIR/.setup-godot"
if [ -x "$GODOT_BIN" ] && [ -f "$ESTAMP" ] && grep -q "^zip-sha512 $EDITOR_SUM\$" "$ESTAMP" \
  && grep -q "^bin-sha256 $(sha256sum "$GODOT_BIN" | cut -d' ' -f1)\$" "$ESTAMP"; then
  log "editor up to date: $GODOT_BIN"
else
  fetch_verified "$EDITOR_ZIP" "linux.x86_64.zip" "linux.64"
  unzip -o -q "$DL/$EDITOR_ZIP" -d "$EDIR"
  chmod +x "$GODOT_BIN"
  { echo "zip-sha512 $EDITOR_SUM"; echo "bin-sha256 $(sha256sum "$GODOT_BIN" | cut -d' ' -f1)"; } >"$ESTAMP"
  rm -f "$DL/$EDITOR_ZIP"
fi
"$GODOT_BIN" --headless --version

# --- templates ------------------------------------------------------------------------------------
MEMBERS=(version.txt icudt_godot.dat)
for g in $TEMPLATES; do
  case "$g" in
    windows) MEMBERS+=(windows_release_x86_64.exe windows_debug_x86_64.exe
      windows_release_x86_64_console.exe windows_debug_x86_64_console.exe) ;;
    android) MEMBERS+=(android_release.apk android_debug.apk)
      [ "${ANDROID_SOURCE:-0}" = 1 ] && MEMBERS+=(android_source.zip) ;;
    linux) MEMBERS+=(linux_release.x86_64 linux_debug.x86_64) ;;
    *) log "unknown template group: $g (windows, android, linux)"; exit 2 ;;
  esac
done
TSTAMP="$GODOT_TEMPLATES_DIR/.setup-godot"
templates_ok() {
  [ -f "$TSTAMP" ] && grep -q "^tpz-sha512 $TPZ_SUM\$" "$TSTAMP" || return 1
  local m
  for m in "${MEMBERS[@]}"; do
    [ -f "$GODOT_TEMPLATES_DIR/$m" ] && grep -q "^$(sha256sum "$GODOT_TEMPLATES_DIR/$m" | cut -d' ' -f1)  $m\$" "$TSTAMP" || return 1
  done
}
if templates_ok; then
  log "templates up to date in $GODOT_TEMPLATES_DIR"
else
  fetch_verified "$TPZ" "export_templates.tpz" "templates"
  # unzip checks each member's CRC32 while extracting.
  for m in "${MEMBERS[@]}"; do
    unzip -o -j -q "$DL/$TPZ" "templates/$m" -d "$GODOT_TEMPLATES_DIR"
  done
  chmod +x "$GODOT_TEMPLATES_DIR"/*.exe "$GODOT_TEMPLATES_DIR"/linux_* 2>/dev/null || true
  {
    echo "tpz-sha512 $TPZ_SUM"
    (cd "$GODOT_TEMPLATES_DIR" && sha256sum "${MEMBERS[@]}")
  } >"$TSTAMP"
  rm -f "$DL/$TPZ"
fi
log "templates in $GODOT_TEMPLATES_DIR ($(cat "$GODOT_TEMPLATES_DIR/version.txt")):"
(cd "$GODOT_TEMPLATES_DIR" && ls -la "${MEMBERS[@]}" | awk '{printf "  %8.1f MiB  %s\n", $5 / 1048576, $9}')
