"""The stone/rock shape atlases, derived from CC0 photoscans (Poly Haven).

Derived atlases are cached as small .npz files in tools/terrain/data/ so a
bake needs no network. To rebuild them, download the listed displacement
maps (fetch_sources.py) and run bake.py with --rebuild-atlases."""
import os
import numpy as np

from . import rocks

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, '..', 'data'))

# name -> (scan id, metres per tile, aspect (x, y), build kwargs)
SPECS = {
    'cliff': ('dark_rock_02', 6.0, (1.4, 0.75), dict(min_dist=4, strata=0.35, strata_px=12, crack=0.3, seed=11)),
    'cliff2': ('rock_face_03', 6.0, (1.3, 0.8), dict(min_dist=3, strata=0.4, strata_px=11, crack=0.4, seed=12)),
    'wall': ('rock_wall_10', 3.2, (1.0, 1.0), dict(min_dist=3, crack=0.9, seed=13)),
    'pebbles': ('dry_river_pebbles', 5.0, (1.0, 1.0), dict(min_dist=2, crack=0.8, seed=14)),
    'rocktop': ('dark_rock_02', 5.0, (1.0, 1.0), dict(min_dist=3, crack=0.45, seed=15)),
}

SOURCES = {
    'dark_rock_02': 'https://polyhaven.com/a/dark_rock_02',
    'rock_face_03': 'https://polyhaven.com/a/rock_face_03',
    'rock_wall_10': 'https://polyhaven.com/a/rock_wall_10',
    'dry_river_pebbles': 'https://polyhaven.com/a/dry_river_pebbles',
}


def get(src_dir=None, rebuild=False):
    out = {}
    os.makedirs(DATA, exist_ok=True)
    for name, (scan, m, asp, kw) in SPECS.items():
        path = os.path.join(DATA, f'atlas_{name}.npz')
        if os.path.exists(path) and not rebuild:
            out[name] = rocks.load_atlas(path)
            continue
        if not src_dir:
            raise FileNotFoundError(f'{path} missing; pass --sources <dir with {scan}_disp_1k.png> to build it')
        a = rocks.build_atlas(os.path.join(src_dir, f'{scan}_disp_1k.png'), m, aspect=asp, **kw)
        rocks.save_atlas(a, path)
        out[name] = a
    return out
