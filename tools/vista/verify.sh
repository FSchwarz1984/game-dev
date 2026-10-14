#!/bin/sh
# Rebuilds the vista preview and captures the verification set: stills at 1280x720 and 844x390
# (phone landscape), the rise and the wave as frame sequences with contact sheets, and
# side-by-sides with v0.1.
#   sh tools/vista/verify.sh       -> $SHOT_DIR or .shots/vista/final (git-ignored)
# The v0.1 reference shots (d_title.png, vis_01.png) are read from $VISTA_REF or .shots/ref; the
# side-by-sides are skipped when they are missing.
set -e
cd "$(dirname "$0")/../.."
export SHOT_DIR="${SHOT_DIR:-.shots/vista/final}"
REF="${VISTA_REF:-.shots/ref}"
mkdir -p "$SHOT_DIR"
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
  "rise_seq:$S&rise=0&sky=0&frames=2&seqn=12&seqdt=3&ramp=rise,0,1,0,0.85&ramp=sky,0,1,0.37,0.7" \
  "wave_seq:$S&rise=1&sky=1&wave=0&frames=2&seqn=24&seqdt=0.25&ramp=wave,0,1"
python3 - "$SHOT_DIR" "$REF" <<'PY'
import os, sys
from PIL import Image, ImageDraw
d, ref = sys.argv[1], sys.argv[2]
def sbs(a, b, out, la, lb):
    A = Image.open(a).convert('RGB'); B = Image.open(b).convert('RGB')
    h = max(A.height, B.height); o = Image.new('RGB', (A.width + B.width + 12, h + 28), (16, 16, 20))
    o.paste(A, (0, 28)); o.paste(B, (A.width + 12, 28)); dr = ImageDraw.Draw(o)
    dr.text((8, 8), la, fill=(230, 230, 230)); dr.text((A.width + 20, 8), lb, fill=(230, 230, 230)); o.save(out)
if os.path.exists(ref + '/d_title.png') and os.path.exists(ref + '/vis_01.png'):
    sbs(ref + '/d_title.png', d + '/small_cmp_title.png', d + '/compare_title_v01_vs_new.png', 'v0.1 title (d_title.png)', 'new title (960x540 viewport, native 480x270 x2)')
    sbs(ref + '/vis_01.png', d + '/small_cmp_rise.png', d + '/compare_rise_v01_vs_new.png', 'v0.1 treetop rise (vis_01.png)', 'new south shot, rise 0.5')
else:
    print('v0.1 reference shots not found in', ref, '- side-by-sides skipped')
def sheet(prefix, n, cols, scale, label, out):
    ims = [Image.open('%s/%s-%03d.png' % (d, prefix, i)).convert('RGB') for i in range(n)]
    w, h = ims[0].size; rows = (n + cols - 1) // cols
    o = Image.new('RGB', (cols * (w * scale + 8) - 8, rows * (h * scale + 8) - 8), (16, 16, 20))
    for i, im in enumerate(ims):
        x, y = (i % cols) * (w * scale + 8), (i // cols) * (h * scale + 8)
        o.paste(im.resize((w * scale, h * scale), Image.NEAREST), (x, y))
        ImageDraw.Draw(o).text((x + 6, y + 4), label(i), fill=(235, 235, 235))
    o.save(out)
    return ims
def ramp(u, u0, u1): return min(1, max(0, (u - u0) / (u1 - u0)))
sheet('rise_seq', 12, 3, 2, lambda i: 't=%ds  rise %.2f  sky %.2f' % (i * 3, ramp(i / 11, 0, 0.85), ramp(i / 11, 0.37, 0.7)), d + '/rise_sheet.png')
ims = sheet('wave_seq', 24, 4, 1, lambda i: 'wave %.2f' % (i / 23), d + '/wave_seq_sheet.png')
w, h = ims[0].size
gif = [im.resize((w * 2, h * 2), Image.NEAREST) for im in ims]
gif[0].save(d + '/wave_seq.gif', save_all=True, append_images=gif[1:], duration=120, loop=0)
print('composites written to', d)
PY
