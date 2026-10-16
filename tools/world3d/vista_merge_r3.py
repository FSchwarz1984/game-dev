# The view from the lookout's stand-in atlas for round 5 (decision-log G5R3-1: the vista's trees as
# round 3 drew them): round 3's tree stand-ins (from git, commit 20e91e6) on top, the heroes (the great
# camphor, the hut, the shrine, the graves) of the current bake below.
#   python3 -I tools/world3d/vista_merge_r3.py        (from the repository root)
# Reads godot/world3d/vista/impostors{.json,_a.png,_n.png} (the current bake: build_vista_impostors.sh)
# and the same three files at 20e91e6; writes godot/world3d/vista/impostors_r5{.json,_a.png,_n.png}.
import io
import json
import subprocess

from PIL import Image

R3 = '20e91e6'
D = 'godot/world3d/vista/'
HEROES = ['camphor_great', 'hut', 'shrine', 'graves']


def git_bytes(path):
    return subprocess.run(['git', 'show', R3 + ':' + path], capture_output=True, check=True).stdout


r3 = json.loads(git_bytes(D + 'impostors.json'))
a3 = Image.open(io.BytesIO(git_bytes(D + 'impostors_a.png'))).convert('RGBA')
n3 = Image.open(io.BytesIO(git_bytes(D + 'impostors_n.png'))).convert('RGBA')
cur = json.load(open(D + 'impostors.json'))
a4 = Image.open(D + 'impostors_a.png').convert('RGBA')
n4 = Image.open(D + 'impostors_n.png').convert('RGBA')
rows = a3.size[1]
w = max(a3.size[0], a4.size[0])


def stack(t, b):
    o = Image.new('RGBA', (w, t.size[1] + b.size[1]), (0, 0, 0, 0))
    o.paste(t, (0, 0))
    o.paste(b, (0, t.size[1]))
    return o


stack(a3, a4).save(D + 'impostors_r5_a.png')
stack(n3, n4).save(D + 'impostors_r5_n.png')
frames = [f for f in r3['frames'] if f['asset'] not in HEROES]
for f in cur['frames']:
    if f['asset'] in HEROES:
        g = dict(f)
        rc = list(g['rect'])
        rc[1] += rows
        g['rect'] = rc
        frames.append(g)
json.dump({'format': r3.get('format', 'tengan-impostors/1'), 'page': w, 'pages': 1, 'r3_rows': rows,
           'note': 'round 5: round 3 tree stand-ins (20e91e6) on top, the current heroes below (rows >= r3_rows)',
           'frames': frames}, open(D + 'impostors_r5.json', 'w'))
print('impostors_r5: %d frames, %dx%d' % (len(frames), w, rows + a4.size[1]))
