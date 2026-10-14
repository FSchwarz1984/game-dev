#!/bin/sh
# Rebuilds the vista preview and captures the verification set (1280x720 and 844x390 phone
# landscape), the wave as a frame sequence, and side-by-sides with v0.1.
#   sh tools/vista/verify.sh            -> $SHOT_DIR or <scratchpad>/shots/vista/final
set -e
cd "$(dirname "$0")/../.."
SCR="${VISTA_SCRATCH:-/tmp/claude-0/-home-user-game-dev/a1b4dbc5-91a8-5ca9-9938-d964a8e56360/scratchpad}"   # where v0.1 reference shots live
export SHOT_DIR="${SHOT_DIR:-$SCR/shots/vista/final}"
node tools/vista/build.mjs
S="shot=south&tod=21"
node tools/vista/shot.mjs \
  "title:shot=title" \
  "south_dusk_pan0:shot=south&tod=17.5&pan=0" \
  "south_dusk_pan50:shot=south&tod=17.5&pan=0.5" \
  "south_dusk_pan100:shot=south&tod=17.5&pan=1" \
  "south_bluehour:shot=south&tod=19" \
  "south_night:$S" \
  "south_rise10:$S&rise=0.1" "south_rise16:$S&rise=0.16" "south_rise50:$S&rise=0.5" "south_rise100:$S&rise=1" \
  "south_sky30:$S&rise=0.6&sky=0.3" "south_sky100:$S&rise=0.8&sky=1" \
  "south_wave20:$S&rise=1&sky=1&wave=0.2" "south_wave60:$S&rise=1&sky=1&wave=0.6" "south_wave95:$S&rise=1&sky=1&wave=0.95" \
  "south_stand:$S&rise=1&sky=1&wave=0.45&stand=1" \
  "tower_on:shot=tower&tower=1&frames=15" "tower_off:shot=tower&tower=0&frames=15" \
  "phone/title:shot=title" "phone/south_dusk:shot=south&tod=17.5" "phone/south_rise50:$S&rise=0.5" \
  "phone/south_sky100:$S&rise=0.8&sky=1" "phone/south_wave60:$S&rise=1&sky=1&wave=0.6" "phone/tower_on:shot=tower&frames=15" \
  "small/cmp_title:shot=title" "small/cmp_rise:$S&rise=0.5" \
  "wave_seq:$S&rise=1&sky=1&wave=0&frames=2&seqn=24&seqdt=0.25&ramp=wave,0,1"
python3 - "$SHOT_DIR" "$SCR/shots" <<'PY'
import sys
from PIL import Image, ImageDraw
d, v01 = sys.argv[1], sys.argv[2]
def sbs(a, b, out, la, lb):
    A = Image.open(a).convert('RGB'); B = Image.open(b).convert('RGB')
    h = max(A.height, B.height); o = Image.new('RGB', (A.width + B.width + 12, h + 28), (16, 16, 20))
    o.paste(A, (0, 28)); o.paste(B, (A.width + 12, 28)); dr = ImageDraw.Draw(o)
    dr.text((8, 8), la, fill=(230, 230, 230)); dr.text((A.width + 20, 8), lb, fill=(230, 230, 230)); o.save(out)
sbs(v01 + '/d_title.png', d + '/small_cmp_title.png', d + '/compare_title_v01_vs_new.png', 'v0.1 title (d_title.png)', 'new title (960x540 viewport, native 480x270 x2)')
sbs(v01 + '/vis_01.png', d + '/small_cmp_rise.png', d + '/compare_rise_v01_vs_new.png', 'v0.1 treetop rise (vis_01.png; the pro_*.png files are gameplay frames)', 'new south shot, rise 0.5')
ims = [Image.open('%s/wave_seq-%03d.png' % (d, i)).convert('RGB') for i in range(24)]
w, h = ims[0].size
sheet = Image.new('RGB', (w * 4, h * 6))
for i, im in enumerate(ims): sheet.paste(im, ((i % 4) * w, (i // 4) * h))
sheet.resize((w * 6, h * 9), Image.NEAREST).save(d + '/wave_seq_sheet.png')
gif = [im.resize((w * 2, h * 2), Image.NEAREST) for im in ims]
gif[0].save(d + '/wave_seq.gif', save_all=True, append_images=gif[1:], duration=120, loop=0)
print('composites written to', d)
PY
