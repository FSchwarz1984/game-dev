"""Render bench shots through the renderer's PixelView3D (Xvfb + Mobile renderer + lavapipe) and
compose verification sheets.

    from shots import Bench, sheet
    b = Bench('/scratch/bench')            # creates/refreshes the bench project (copy of render3d)
    b.shot('a.png', items=[{'scene': 'res://world3d/assets/trees/x/x.tscn'}], focus=[0, 1, 0], hour=12.5)
    b.run()                                 # one Godot run per native canvas size
    sheet([('a.png', 'noon')], 'sheet.png', scale=3)

The native canvas is the window size divided by the integer scale (PixelView3D.fit): 1440x810 ->
480x270 (x3); 900x800 -> 900x800 (x1) for overviews of big assets.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import defaultdict

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_bench  # noqa: E402

GODOT = os.environ.get('GODOT_BIN', '/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64')
DISPLAY = os.environ.get('W3A_DISPLAY', ':57')
HOURS = {'morning': 7.5, 'noon': 12.5, 'dusk': 17.6, 'night': 22.0}


class Bench:
    def __init__(self, bench_dir, refresh=True, pitch=55.0):
        self.dir = bench_dir
        self.pitch = pitch
        if refresh:
            make_bench.main(bench_dir)
        self.shots = defaultdict(list)

    def shot(self, out, items, focus=(0, 1, 0), hour='noon', window=(1440, 810), fig=None, cut_px=0.0,
             ground=True, ground_tint=(0.42, 0.47, 0.30), wind=1.0, rain=0.0, frames=6, clock=3.0, shadows=True,
             canvas=None):
        h = HOURS.get(hour, hour) if isinstance(hour, str) else hour
        s = {'out': os.path.abspath(out), 'items': items, 'focus': list(focus), 'hour': float(h),
             'fig': list(fig) if fig is not None else None, 'cut_px': cut_px, 'ground': ground,
             'ground_tint': list(ground_tint), 'wind': wind, 'rain': rain, 'frames': frames, 'clock': clock,
             'shadows': shadows, 'canvas': list(canvas) if canvas is not None else None}
        if canvas is not None:
            window = (960, 540)
        self.shots[tuple(window)].append(s)

    def run(self, timeout=900):
        _ensure_xvfb()
        env = dict(os.environ, DISPLAY=DISPLAY)
        for window, shots in self.shots.items():
            job = os.path.join(self.dir, 'job_%dx%d.json' % window)
            with open(job, 'w') as f:
                json.dump({'pitch': self.pitch, 'shots': shots}, f)
            t0 = time.time()
            r = subprocess.run([GODOT, '--path', self.dir, '--rendering-method', 'forward_plus', '--rendering-driver', 'vulkan',
                                '--resolution', '%dx%d' % window, '--position', '0,0', 'res://w3a/w3a_bench.tscn',
                                '--', f'--job={job}'], capture_output=True, text=True, timeout=timeout, env=env)
            log = r.stdout + r.stderr
            with open(os.path.join(self.dir, 'bench_%dx%d.log' % window), 'w') as f:
                f.write(log)
            bad = [l for l in log.splitlines() if ('ERROR' in l or 'SCRIPT ERROR' in l) and 'ALSA' not in l
                   and 'audio' not in l.lower() and 'status < 0' not in l]
            for s in shots:
                if s.get('canvas') is not None:
                    grade_raw(s['out'])
            missing = [s['out'] for s in shots if not os.path.exists(s['out'])]
            if bad or missing:
                print('bench problems (%dx%d):' % window)
                for l in bad[:30]:
                    print('  ', l)
                for m in missing:
                    print('   missing', m)
            print(f'bench {window[0]}x{window[1]}: {len(shots)} shots in {time.time() - t0:.1f} s')
        self.shots = defaultdict(list)


def grade_raw(out):
    """Apply the renderer's composite grading (render3d/shaders/composite.gdshader, without the
    vignette) to <out>_raw.png -> <out>.png, using the parameters the bench saved."""
    import numpy as np
    base = os.path.splitext(out)[0]
    if not os.path.exists(base + '_raw.png'):
        return
    g = json.load(open(base + '_grade.json'))
    c = np.asarray(Image.open(base + '_raw.png').convert('RGB'), np.float64) / 255.0
    l = c @ np.array([0.299, 0.587, 0.114])
    c = l[..., None] + (c - l[..., None]) * g['saturation']
    lift = np.array(g['lift']); gain = np.array(g['gain'])
    c = lift + c * (gain - lift)
    l2 = c @ np.array([0.299, 0.587, 0.114])
    sm = lambda a, b, x: np.clip((x - a) / (b - a), 0, 1) ** 2 * (3 - 2 * np.clip((x - a) / (b - a), 0, 1))
    c = c + np.array(g['shadow_tone']) * (1 - sm(0.0, 0.5, l2))[..., None] + np.array(g['high_tone']) * sm(0.45, 1.0, l2)[..., None]
    Image.fromarray(np.clip(np.round(c * 255), 0, 255).astype(np.uint8)).save(out)


def _ensure_xvfb():
    try:
        subprocess.run(['xdpyinfo', '-display', DISPLAY], capture_output=True, timeout=5, check=True)
        return
    except Exception:
        pass
    subprocess.Popen(['Xvfb', DISPLAY, '-screen', '0', '2400x1600x24', '-nolisten', 'tcp'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(50):
        try:
            subprocess.run(['xdpyinfo', '-display', DISPLAY], capture_output=True, timeout=5, check=True)
            return
        except Exception:
            time.sleep(0.1)


def upscale(img, k):
    return img.resize((img.width * k, img.height * k), Image.NEAREST)


def sheet(cells, out, scale=1, cols=None, label_h=14, bg=(40, 38, 44), title=None):
    """cells: list of (path or Image, label). Images are scaled by `scale` (nearest)."""
    ims = []
    for c, lab in cells:
        im = Image.open(c).convert('RGB') if isinstance(c, str) else c.convert('RGB')
        ims.append((upscale(im, scale) if scale != 1 else im, lab))
    cols = cols or len(ims)
    rows = (len(ims) + cols - 1) // cols
    cw = max(i.width for i, _ in ims)
    ch = max(i.height for i, _ in ims) + label_h
    th = 18 if title else 0
    W = cols * cw + (cols + 1) * 4
    H = rows * ch + (rows + 1) * 4 + th
    S = Image.new('RGB', (W, H), bg)
    d = ImageDraw.Draw(S)
    if title:
        d.text((6, 3), title, fill=(230, 226, 214))
    for k, (im, lab) in enumerate(ims):
        r, c = divmod(k, cols)
        x = 4 + c * (cw + 4)
        y = th + 4 + r * (ch + 4)
        S.paste(im, (x, y + label_h))
        d.text((x + 2, y + 1), lab, fill=(220, 216, 200))
    S.save(out)
    return out
