#!/usr/bin/env python3
"""Bake a terrain layout into render chunks, ground masks and previews.

usage:
  python3 tools/terrain/bake.py tools/terrain/layouts/home_saddle.json
  python3 tools/terrain/bake.py LAYOUT --out DIR --chunk 512 --no-previews
  python3 tools/terrain/bake.py LAYOUT --rebuild-atlases --sources DIR_WITH_SCANS

Needs numpy, scipy, scikit-image and Pillow. See tools/terrain/README.md.
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np                       # noqa: E402
from PIL import Image                     # noqa: E402

from tengan_terrain import pipeline, export, preview   # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('layout')
    ap.add_argument('--out', default=None, help='output directory (default tools/terrain/out/<name>)')
    ap.add_argument('--chunk', type=int, default=512)
    ap.add_argument('--sources', default=None, help='directory with the CC0 scans (only to rebuild atlases)')
    ap.add_argument('--rebuild-atlases', action='store_true')
    ap.add_argument('--no-previews', action='store_true')
    ap.add_argument('--godot', nargs='?', const='', default=None,
                    help='also write the Godot-ready region (default godot/world/regions/<name>)')
    a = ap.parse_args()
    t0 = time.time()
    print('bake', a.layout)
    B = pipeline.run(a.layout, sources=a.sources, rebuild_atlases=a.rebuild_atlases)
    out = a.out or os.path.join(HERE, 'out', B.spec.get('name', 'region'))
    region = export.export(B, out, chunk=a.chunk)
    if a.godot is not None:
        root = os.path.normpath(os.path.join(HERE, '..', '..', 'godot'))
        rdir = a.godot or os.path.join(root, 'world', 'regions', B.spec.get('name', 'region'))
        export.export_godot(B, dict(region, label=B.spec.get('label', B.spec.get('name'))), out, rdir, root,
                            os.path.join(HERE, 'godot', 'terrain.gdshader'), extra=B.spec.get('godot', {}))
    if not a.no_previews:
        pdir = os.path.join(out, 'preview')
        os.makedirs(pdir, exist_ok=True)
        Image.fromarray(np.dstack([B.albedo, np.where(B.mask, 255, 0).astype(np.uint8)])).save(os.path.join(pdir, 'albedo.png'), optimize=True)
        for tod in ('morning', 'noon', 'dusk', 'night'):
            img = preview.lit(B.albedo, B.paint.n, B.horizon, B.sky, B.mask, tod, B.toward)
            Image.fromarray(img).save(os.path.join(pdir, f'lit_{tod}.png'), optimize=True)
            Image.fromarray(img).resize((img.shape[1] // 4, img.shape[0] // 4), Image.BOX).save(os.path.join(pdir, f'lit_{tod}_quarter.png'))
    print(f'done in {time.time() - t0:.1f}s -> {out}')


if __name__ == '__main__':
    main()
