#!/usr/bin/env bash
# The still behind the portrait gallery's demo dialogues (godot/showcase/showcase_gallery.gd BACKDROP): the 3D art
# sample's home area at 9:30 with nobody in it (--nochar, as the showcase delivers it, G5R3-21), graded as the game
# shows it, at native pixels: 652 x 372 = the 640 x 360 page plus 6 px on every side, so the view can shake (震屏)
# without an empty edge. Rendered at x3 (1956 x 1116) on Xvfb with Mesa, then reduced to one pixel per native pixel
# (each 3 x 3 block is one colour; the script checks it). Run it again whenever the home area's look changes.
#   bash tools/godot/capture_backdrop.sh [hours]     -> godot/art/showcase/dialogue_backdrop.png
set -euo pipefail
. "$(dirname "$0")/common.sh"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOURS="${1:-9.5}"
OUT="$ROOT/godot/art/showcase/dialogue_backdrop.png"
TMP="$(mktemp -d)"
DISP="${XVFB_DISPLAY:-:93}"
Xvfb "$DISP" -screen 0 1956x1116x24 -nolisten tcp >/dev/null 2>&1 &
XPID=$!
trap 'kill $XPID 2>/dev/null || true; rm -rf "$TMP"' EXIT
export DISPLAY="$DISP"
for _ in $(seq 1 50); do xdpyinfo >/dev/null 2>&1 && break; sleep 0.1; done
nice -n 19 "$GODOT_BIN" --path "$ROOT/godot" --rendering-method forward_plus --resolution 1956x1116 --position 0,0 \
  res://world3d/sample.tscn -- --nochar --hours="$HOURS" --frames=120 --shot="$TMP/shot.png" > "$TMP/log.txt" 2>&1 || true
[ -f "$TMP/shot_win.png" ] || { tail -20 "$TMP/log.txt"; echo "no capture"; exit 1; }
mkdir -p "$(dirname "$OUT")"
python3 -I - "$TMP/shot_win.png" "$OUT" <<'EOF'
import sys
import numpy as np
from PIL import Image
a = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(np.int16)
S, W, H = 3, 652, 372
best = None
for py in range(S):                 # the sub-pixel camera offset may shift the blocks by whole window pixels
    for px in range(S):
        b = a[py:py + (H - 1) * S, px:px + (W - 1) * S]
        h, w = b.shape[0] // S, b.shape[1] // S
        blocks = b[:h * S, :w * S].reshape(h, S, w, S, 3)
        spread = int(np.abs(blocks - blocks[:, :1, :, :1]).max(axis=(1, 3, 4)).mean() * 1000)
        if best is None or spread < best[0]:
            best = (spread, px, py)
spread, px, py = best
pad = np.pad(a, ((0, S), (0, S), (0, 0)), mode='edge')
img = pad[py + 1:py + 1 + H * S:S, px + 1:px + 1 + W * S:S]
img = img[:H, :W]
if img.shape[:2] != (H, W):
    sys.exit('capture too small: %s' % (img.shape,))
Image.fromarray(img.astype(np.uint8), 'RGB').save(sys.argv[2], optimize=True)
print('backdrop %dx%d (block phase %d,%d; spread %.3f) -> %s' % (W, H, px, py, spread / 1000, sys.argv[2]))
EOF
