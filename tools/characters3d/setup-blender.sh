#!/usr/bin/env bash
# Installs the official Blender 5.2 (Linux x64) used to build the 3D characters
# (tools/characters3d/, docs/knowledge/24-3d-characters.md), outside the repository.
#   bash tools/characters3d/setup-blender.sh            install (or check) the pinned version
#   BLENDER_HOME=/some/dir bash tools/characters3d/setup-blender.sh
# Result: $BLENDER_HOME/blender-<ver>-linux-x64/blender, and a stable link $BLENDER_HOME/blender.
# The download comes only from download.blender.org; it is checked against the SHA256 published in
# the same directory (blender-<ver>.sha256) AND the value pinned below; a mismatch stops the script.
# Requests carry a neutral User-Agent and nothing else (CLAUDE.md section 4.5). Safe to rerun: an
# installed, unchanged copy is not downloaded again (about 1 s).
set -euo pipefail

BLENDER_VERSION="${BLENDER_VERSION:-5.2.2}"
BLENDER_SERIES="${BLENDER_VERSION%.*}"                       # 5.2
BLENDER_HOME="${BLENDER_HOME:-/home/user/blender}"
UA="TenganAssetBuild/1.0"
BASE="https://download.blender.org/release/Blender${BLENDER_SERIES}"
TARBALL="blender-${BLENDER_VERSION}-linux-x64.tar.xz"
# Copied from $BASE/blender-5.2.2.sha256 on 2026-10-15.
declare -A PINNED=(
  ["blender-5.2.2-linux-x64.tar.xz"]=84098912789dc450e95697c4184fb8a90acbe5111c2ba4aede3fecb57806a168
)

log() { printf '[setup-blender] %s\n' "$*" >&2; }

DEST="$BLENDER_HOME/blender-${BLENDER_VERSION}-linux-x64"
STAMP="$DEST/.setup-blender"
if [ -x "$DEST/blender" ] && [ -f "$STAMP" ] && grep -q "$TARBALL" "$STAMP"; then
  ln -sfn "$DEST/blender" "$BLENDER_HOME/blender"
  log "already installed: $DEST ($("$DEST/blender" --version 2>/dev/null | head -1))"
  exit 0
fi

mkdir -p "$BLENDER_HOME/downloads"
DL="$BLENDER_HOME/downloads"

published="$(curl -fsS -A "$UA" "$BASE/blender-${BLENDER_VERSION}.sha256" | awk -v f="$TARBALL" '$2 == f { print $1 }')"
pinned="${PINNED[$TARBALL]:-}"
if [ -z "$published" ] && [ -z "$pinned" ]; then
  log "no checksum for $TARBALL (not published, not pinned); refusing to continue"
  exit 1
fi
if [ -n "$published" ] && [ -n "$pinned" ] && [ "$published" != "$pinned" ]; then
  log "published SHA256 differs from the pinned value; refusing to continue"
  exit 1
fi
want="${published:-$pinned}"

if [ ! -f "$DL/$TARBALL" ] || [ "$(sha256sum "$DL/$TARBALL" | cut -d' ' -f1)" != "$want" ]; then
  log "downloading $TARBALL (about 370 MiB)"
  curl -fL -A "$UA" --retry 3 -o "$DL/$TARBALL.part" "$BASE/$TARBALL"
  mv "$DL/$TARBALL.part" "$DL/$TARBALL"
fi
got="$(sha256sum "$DL/$TARBALL" | cut -d' ' -f1)"
if [ "$got" != "$want" ]; then
  log "SHA256 mismatch for $TARBALL: got $got, want $want"
  rm -f "$DL/$TARBALL"
  exit 1
fi
log "SHA256 ok ($got)"

rm -rf "$DEST.tmp"
mkdir -p "$DEST.tmp"
tar -xJf "$DL/$TARBALL" -C "$DEST.tmp" --strip-components=1
rm -rf "$DEST"
mv "$DEST.tmp" "$DEST"
printf '%s %s\n' "$TARBALL" "$got" > "$STAMP"
ln -sfn "$DEST/blender" "$BLENDER_HOME/blender"
# the tarball is only needed to reinstall; keep the disk free
rm -f "$DL/$TARBALL"
log "installed: $DEST ($("$DEST/blender" --version 2>/dev/null | head -1))"
