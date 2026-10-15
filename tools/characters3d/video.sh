#!/usr/bin/env bash
# Native lab frames -> videos (pixels kept square and whole: nearest-neighbour, integer scales).
#   bash tools/characters3d/video.sh <frames_dir> <out_basename> [crop_w crop_h dy]
# Writes <out>_1080p.mp4 (the whole 640x360 frame at x3, 1920x1080, as the game shows it on a 1080p
# screen), <out>_1080p_yuv420.mp4 (the same for players without 4:4:4) and <out>_crop_x4.mp4 (a box
# round her at x4). 30 fps, libx264 crf 12; yuv444p keeps 1-pixel lines free of chroma blur.
set -euo pipefail
IN="${1:?frames dir}"; OUT="${2:?out base}"; CW="${3:-160}"; CH="${4:-120}"; DY="${5:-0}"
ffmpeg -y -loglevel error -framerate 30 -i "$IN/f%05d.png" -vf "scale=iw*3:ih*3:flags=neighbor" \
  -c:v libx264 -crf 12 -pix_fmt yuv444p "${OUT}_1080p.mp4"
ffmpeg -y -loglevel error -framerate 30 -i "$IN/f%05d.png" -vf "scale=iw*3:ih*3:flags=neighbor" \
  -c:v libx264 -crf 14 -pix_fmt yuv420p "${OUT}_1080p_yuv420.mp4"
ffmpeg -y -loglevel error -framerate 30 -i "$IN/f%05d.png" \
  -vf "crop=${CW}:${CH}:(iw-${CW})/2:(ih-${CH})/2+${DY},scale=iw*4:ih*4:flags=neighbor" \
  -c:v libx264 -crf 12 -pix_fmt yuv444p "${OUT}_crop_x4.mp4"
echo "VIDEO ${OUT}_1080p.mp4 ${OUT}_1080p_yuv420.mp4 ${OUT}_crop_x4.mp4"
