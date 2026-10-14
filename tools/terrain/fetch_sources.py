#!/usr/bin/env python3
"""Download the CC0 photoscan height maps the rock/stone atlases are derived from.

Only needed to REBUILD the atlases (tools/terrain/data/atlas_*.npz are cached in
the repo). Sources: Poly Haven, "All assets are licensed as CC0"
(https://polyhaven.com/license). Requests use a neutral User-Agent and send no
personal data (project charter, privacy section 4.5).

usage: python3 tools/terrain/fetch_sources.py DEST_DIR
then:  python3 tools/terrain/bake.py LAYOUT --rebuild-atlases --sources DEST_DIR
"""
import json
import os
import sys
import urllib.request

UA = {'User-Agent': 'TenganAssetBuild/1.0'}
SCANS = ['dark_rock_02', 'rock_wall_10', 'dry_river_pebbles']


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def main():
    dest = sys.argv[1] if len(sys.argv) > 1 else 'terrain-sources'
    os.makedirs(dest, exist_ok=True)
    for sid in SCANS:
        out = os.path.join(dest, f'{sid}_disp_1k.png')
        if os.path.exists(out):
            continue
        files = json.loads(get(f'https://api.polyhaven.com/files/{sid}'))
        url = files['Displacement']['1k']['png']['url']
        with open(out, 'wb') as fh:
            fh.write(get(url))
        print('fetched', out)


if __name__ == '__main__':
    main()
