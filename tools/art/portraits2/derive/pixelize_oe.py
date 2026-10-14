"""pixelize_oe.py HI_PNG OUT_PNG SIZE : PixelOE (contrast-aware pixelization, Apache-2.0, knowledge/11) of the tilted
reference crop, composited on the portrait card colour; alpha from an area-resized alpha (> 110 -> opaque).

Run it with a Python that has PixelOE (and torch) installed, e.g. a venv: `VENV/bin/python -I pixelize_oe.py ...`.
derive.py calls it this way; it reads and writes plain PNG files only."""
import sys

import cv2
import numpy as np
from PIL import Image
from pixeloe.pixelize import pixelize

src, dst, size = sys.argv[1], sys.argv[2], int(sys.argv[3])
im = Image.open(src).convert('RGBA')
bg = Image.new('RGBA', im.size, (78, 70, 86, 255))
bg.alpha_composite(im)
bgr = cv2.cvtColor(np.asarray(bg.convert('RGB')), cv2.COLOR_RGB2BGR)
sm = pixelize(bgr, mode='contrast', target_size=size, patch_size=16, thickness=1, colors=None, no_upscale=True)
sm = cv2.cvtColor(sm, cv2.COLOR_BGR2RGB)
a = cv2.resize(np.asarray(im)[..., 3].astype(np.float32), (sm.shape[1], sm.shape[0]), interpolation=cv2.INTER_AREA)
Image.fromarray(np.dstack([sm, np.where(a > 110, 255, 0).astype(np.uint8)]), 'RGBA').save(dst)
print('pixelized', dst, sm.shape)
