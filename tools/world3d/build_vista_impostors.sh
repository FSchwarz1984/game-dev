#!/usr/bin/env bash
# Builds the impostors of the view from the lookout (docs/knowledge/21 §10):
#   bash tools/world3d/build_vista_impostors.sh
# 1. bakes the trees (8 directions, 8 degrees down) and, from the camera of the look back home, the
#    great camphor, the hut, the shrine and the graves (render3d/dev/impostor_bake.tscn, Xvfb);
# 2. packs them into levels of detail (tools/world3d/vista_impostors.py) in godot/world3d/vista/;
# 3. imports them. About half a minute. Rebuild after the assets or the layout change.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GODOT_BIN="${GODOT_BIN:-/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64}"
TMP="$ROOT/tools/world3d/out/impostor_bake"
rm -rf "$TMP"
mkdir -p "$TMP/trees" "$TMP/heroes"
bash "$ROOT/tools/world3d/run3d.sh" res://render3d/dev/impostor_bake.tscn "$TMP/trees" 1280x720 -- --out="$TMP/trees" \
	--assets=sugi_a,sugi_d,pine_a,pine_c,konara_a,konara_c,buna_a,maple_a,maple_red_a,take_c,kaki_a --angles=8 --elev=8 >/dev/null
# the look back home: the camera stands HOME_CAM_H over her feet, behind her (vista3d.gd), at the
# distance where a sprite pixel is a screen pixel (270 px tall: 18.55 m; 240 px: 16.49 m)
VIEWS=$(python3 - "$ROOT" << 'EOF'
import json, math, sys
root = sys.argv[1]
t = json.load(open(root + "/godot/world3d/terrain/saddle/terrain.json"))
M = t["markers"]
cat = json.load(open(root + "/godot/world3d/assets/catalog.json"))["assets"]
HOME_BEARING, HOME_CAM_H, D = 22.0, 4.0, 135.0 / math.tan(math.radians(20.0)) / 20.0
lk = M["lookout"]
r = math.sqrt(D * D - HOME_CAM_H ** 2)
b = math.radians(HOME_BEARING + 180.0)
cam = (lk["x"] + math.sin(b) * r, lk["y"] + HOME_CAM_H, lk["z"] - math.cos(b) * r)
out = []
for name, mk, yaw, mid in (("camphor_great", "camphor", 0.0, 12.0), ("hut", "hut", 0.0, 3.0), ("shrine", "shrine", 0.0, 1.5),
                           ("graves", "graves", -2.0, 0.8)):
    m = M[mk]
    dx, dz = cam[0] - m["x"], cam[2] - m["z"]
    ang = (math.degrees(math.atan2(dx, dz)) - yaw) % 360.0
    el = math.degrees(math.atan2(cam[1] - (m["y"] + mid), math.hypot(dx, dz)))
    out.append("%s:%.1f:%.1f" % (name, ang, el))
print(",".join(out))
EOF
)
bash "$ROOT/tools/world3d/run3d.sh" res://render3d/dev/impostor_bake.tscn "$TMP/heroes" 1280x720 -- --out="$TMP/heroes" \
	--views="$VIEWS" >/dev/null
# levels: the woods from 7.1 px/m down; the pines and maples that stand near the lookout from 14.1;
# the heroes at the scale they are seen at from the look back (for 270 and 240 px tall views)
L="7.071/5/3.536/2.5/1.768/1.25/0.884/0.625/0.442"
python3 "$ROOT/tools/world3d/vista_impostors.py" "$TMP/trees" "$TMP/heroes" "$ROOT/godot/world3d/vista" \
	--ppm=7.071,5,3.536,2.5,1.768,1.25,0.884,0.625,0.442 \
	--hero=pine_a:14.142/10/$L,pine_c:14.142/10/$L,maple_red_a:14.142/10/$L,maple_a:10/$L,camphor_great:5.59/5.1,hut:7.54/7.0,shrine:6.33/5.8,graves:6.57/6.1
"$GODOT_BIN" --headless --path "$ROOT/godot" --import >/dev/null 2>&1 || true
echo "views: $VIEWS"
