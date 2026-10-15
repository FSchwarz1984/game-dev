#!/usr/bin/env bash
# Native lab frames -> videos (pixels kept square and whole: nearest-neighbour, integer scales).
#   bash tools/characters3d/video.sh <frames_dir> <out_basename> [crop_w crop_h dy]
# Writes <out>_full_x2.mp4 (the whole 640x360 frame at x2, 1280x720) and <out>_crop_x4.mp4 (a box
# round her at x4), both 30 fps, libx264 crf 12, yuv444p (no chroma blur on 1-pixel lines).
set -euo pipefail
IN="${1:?frames dir}"; OUT="${2:?out base}"; CW="${3:-160}"; CH="${4:-120}"; DY="${5:-0}"
ffmpeg -y -loglevel error -framerate 30 -i "$IN/f%05d.png" -vf "scale=iw*2:ih*2:flags=neighbor" \
  -c:v libx264 -crf 12 -pix_fmt yuv444p "${OUT}_full_x2.mp4"
ffmpeg -y -loglevel error -framerate 30 -i "$IN/f%05d.png" \
  -vf "crop=${CW}:${CH}:(iw-${CW})/2:(ih-${CH})/2+${DY},scale=iw*4:ih*4:flags=neighbor" \
  -c:v libx264 -crf 12 -pix_fmt yuv444p "${OUT}_crop_x4.mp4"
echo "VIDEO ${OUT}_full_x2.mp4 ${OUT}_crop_x4.mp4"
