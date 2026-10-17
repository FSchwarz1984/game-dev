#!/usr/bin/env bash
# Builds the Windows delivery of the art sample (godot/showcase, G5R3-0): a release export, the
# readme and the licences (engine, third-party, fonts, recordings) in one folder, zipped, then split
# into parts for the Artifact download page (each part a published file, the page joins them).
#   bash tools/godot/package-showcase.sh <out_dir> [part_mb=14] [name=Tengan_ArtSample]
# Writes <out_dir>/<name>/ (the folder that goes into the zip), <name>.zip, parts/part00.. and
# SHA256SUMS.txt (the zip and every part). Later builds take their own name (Tengan_ArtSample_2), so
# the user's copies of different builds do not get mixed up.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/common.sh"
PROJ="$(cd "$HERE/../../godot" && pwd)"
OUT="$(realpath -m "${1:?out dir}")"
PART_MB="${2:-14}"
NAME="${3:-Tengan_ArtSample}"
STAGE="$OUT/$NAME"
rm -rf "$STAGE" "$OUT/parts" "$OUT/$NAME.zip"
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
(cd "$OUT" && zip -q -9 -r -X "$NAME.zip" "$NAME")
split -b "${PART_MB}m" -d -a 2 "$OUT/$NAME.zip" "$OUT/parts/part"
(cd "$OUT" && sha256sum "$NAME.zip" parts/part* > SHA256SUMS.txt)
echo "== $(size_of "$OUT/$NAME.zip")  $OUT/$NAME.zip"
ls -l "$OUT/parts"
