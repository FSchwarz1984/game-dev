#!/usr/bin/env bash
# Builds the Windows delivery of the art sample (godot/showcase, G5R3-0): a release export, the
# readme and the licences (engine, third-party, fonts, recordings) in one folder, zipped, then split
# into parts for the Artifact download page (each part a published file, the page joins them).
#   bash tools/godot/package-showcase.sh <out_dir> [part_mb=14]
# Writes <out_dir>/Tengan_ArtSample/ (the folder that goes into the zip), Tengan_ArtSample.zip,
# parts/part00.. and SHA256SUMS.txt (the zip and every part).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"
PROJ="$(cd "$HERE/../../godot" && pwd)"
OUT="$(realpath -m "${1:?out dir}")"
PART_MB="${2:-14}"
STAGE="$OUT/Tengan_ArtSample"
rm -rf "$STAGE" "$OUT/parts" "$OUT/Tengan_ArtSample.zip"
mkdir -p "$STAGE/licenses" "$OUT/parts"
bash "$HERE/export.sh" "$PROJ" Windows release "$STAGE/tengan.exe"
"$GODOT_BIN" --headless -s "$HERE/dump_licenses.gd" -- "$STAGE/licenses" >/dev/null 2>&1
[ -s "$STAGE/licenses/GODOT_LICENSE.txt" ] || { echo "licence dump failed"; exit 1; }
cp "$PROJ"/art/fonts/OFL-*.txt "$STAGE/licenses/"
cp "$PROJ/art/fonts/SOURCES.txt" "$STAGE/licenses/FONT_SOURCES.txt"
python3 -I "$HERE/audio_credits.py" "$PROJ/audio/SOURCES.json" > "$STAGE/licenses/AUDIO_SOURCES.txt"
# the readme: UTF-8 with a BOM and CRLF, so Notepad shows the Chinese right
printf '\xef\xbb\xbf' > "$STAGE/README.txt"
sed 's/$/\r/' "$HERE/showcase/README.txt" >> "$STAGE/README.txt"
rm -f "$STAGE"/*.console.exe
(cd "$OUT" && zip -q -9 -r -X Tengan_ArtSample.zip Tengan_ArtSample)
split -b "${PART_MB}m" -d -a 2 "$OUT/Tengan_ArtSample.zip" "$OUT/parts/part"
(cd "$OUT" && sha256sum Tengan_ArtSample.zip parts/part* > SHA256SUMS.txt)
echo "== $(size_of "$OUT/Tengan_ArtSample.zip")  $OUT/Tengan_ArtSample.zip"
ls -l "$OUT/parts"
