#!/usr/bin/env bash
# Fetch the owner's ChatGPT reference art (asset request list v1 and v2) from
# Google Drive, verify SHA-256, and extract safely. The packs are untrusted
# data: each zip lands in its own empty directory, nothing inside is executed
# (the source packs contain .py/.js/.html files; never run them).
#
# usage: bash tools/assets/fetch_gpt_assets.sh <out-dir> [final|all]
#   final (default): the two finished packs (v2 84 finals + v1 100 finals, ~270 MB extracted)
#   all: also the two provenance/source packs (~750 MB more)
# Folder: https://drive.google.com/drive/folders/1kE4h9EG5Hww3DF-6HYyN8CFTqi0-cuar
set -euo pipefail
OUT=${1:?out dir}; WHICH=${2:-final}
HERE=$(cd "$(dirname "$0")" && pwd)
UA="TenganAssetBuild/1.0"
declare -A ID=(
  [v2_84_final]=16UbnJBbMxAnvo5kMybgPimU1uYEO-Mjf
  [v1_supplement_100]=1a-nhMPH9GDEGYwgCuEEQAWkcIYw7kcgx
  [v2_sources_final]=1STz_HJCjezahM5Hw6GxTQooXZszR84j4
  [v1_rule1_sources]=1ovvEBBt8dJuGX_rIzXWUIi-kyjKWg7qI
)
declare -A SUM=(
  [v2_84_final]=6899bba3e3e2b5557622cff6595a271a868923a8dc4114105a0b04d1fc773703
  [v1_supplement_100]=e26fe9dab304331ce64a3ed795572f20ac33aea81bf83c056e973452d3e1cfa1
  [v2_sources_final]=b4260a3beb5a4606d12ef7eacc706b28def6aff16b970dc9e673797c4007bd0a
  [v1_rule1_sources]=4606be1ed38ada799ef630e403b513c7ea105214a6fbf88c9580e1d587a0b787
)
KEYS=(v2_84_final v1_supplement_100)
[ "$WHICH" = all ] && KEYS+=(v2_sources_final v1_rule1_sources)
mkdir -p "$OUT"
for k in "${KEYS[@]}"; do
  zdir="$OUT/zip_$k"; xdir="$OUT/$k"
  if [ -d "$xdir" ] && [ -n "$(ls -A "$xdir")" ]; then echo "$k: already extracted"; continue; fi
  mkdir -p "$zdir"
  if [ ! -f "$zdir/pack.zip" ] || [ "$(sha256sum < "$zdir/pack.zip" | cut -d' ' -f1)" != "${SUM[$k]}" ]; then
    for i in 1 2 3 4 5; do
      curl -sS -L -A "$UA" --max-filesize 600000000 -o "$zdir/pack.zip" \
        "https://drive.usercontent.google.com/download?id=${ID[$k]}&export=download&confirm=t" && break
      sleep $((2**i))
    done
  fi
  got=$(sha256sum < "$zdir/pack.zip" | cut -d' ' -f1)
  [ "$got" = "${SUM[$k]}" ] || { echo "$k: SHA-256 mismatch ($got)"; exit 1; }
  python3 -I "$HERE/safe_unzip.py" "$zdir/pack.zip" "$xdir"
  echo "$k: ok"
done
