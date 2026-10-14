#!/usr/bin/env python3
"""Build every plant: sprites (albedo + normal per layer), sway data, shadows, meta.json and a
Godot scene per plant, plus catalog.json. One command rebuilds what the game uses:

  python3 tools/flora/build.py                 everything into godot/art/flora (res://art/flora)
  python3 tools/flora/build.py --only cedar    one species (others are kept)
  python3 tools/flora/build.py --out DIR --res res://art/flora    somewhere else (bench, sheets)

Output (docs/knowledge/18-vegetation.md):
  flora_plant.gd, flora_field.gd   scene root script (placement, lift) and the shared run-time state
  shaders/                         foliage.gdshader, flora_shadow.gdshader
  plants/<species>/<name>/         PNGs, meta.json, <name>.tscn
  catalog.json                     every plant: species, kind, scene, layers, sort offset, blockers
A full build removes plants and files that are no longer made (Godot's .import files of the
files it keeps stay). Deterministic: the same seeds give the same pixels.
"""
import argparse
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flora import godot, render  # noqa: E402
from flora.species import bamboo_shrubs as BS  # noqa: E402
from flora.species import broadleaf as BL  # noqa: E402
from flora.species import camphor as CA  # noqa: E402
from flora.species import conifer as CO  # noqa: E402
from flora.species import herbs as HB  # noqa: E402

# species -> list of (name, builder). Several variants each, so no two neighbours match.
CATALOG = {
    'camphor': [('camphor_a', lambda: CA.camphor('camphor_a', 1)), ('camphor_b', lambda: CA.camphor('camphor_b', 7))],
    'cedar': [('cedar_%d' % i, (lambda i=i: CO.cedar('cedar_%d' % i, 10 + i, thin=0.35 if i == 4 else 0.0)))
              for i in range(1, 6)],
    'red_pine': [('red_pine_%d' % i, (lambda i=i: CO.red_pine('red_pine_%d' % i, 20 + i))) for i in range(1, 6)],
    'maple_green': [('maple_green_%d' % i, (lambda i=i: BL.maple('maple_green_%d' % i, 30 + i, 'green'))) for i in range(1, 4)],
    'maple_turn': [('maple_turn_%d' % i, (lambda i=i: BL.maple('maple_turn_%d' % i, 40 + i, 'turn'))) for i in range(1, 4)],
    'maple_red': [('maple_red_%d' % i, (lambda i=i: BL.maple('maple_red_%d' % i, 50 + i, 'red'))) for i in range(1, 3)],
    'beech': [('beech_%d' % i, (lambda i=i: BL.beech('beech_%d' % i, 60 + i, moss_forest=i <= 3))) for i in range(1, 5)],
    'persimmon': [('persimmon_%d' % i, (lambda i=i: BL.persimmon('persimmon_%d' % i, 70 + i))) for i in range(1, 4)],
    'bamboo': [('bamboo_%d' % i, (lambda i=i: BS.bamboo('bamboo_%d' % i, 80 + i))) for i in range(1, 4)],
    'hydrangea': [('hydrangea_%d' % i, (lambda i=i: BS.hydrangea('hydrangea_%d' % i, 90 + i))) for i in range(1, 5)],
    'azalea': [('azalea_%d' % i, (lambda i=i: BS.azalea('azalea_%d' % i, 100 + i))) for i in range(1, 5)],
    'shrub': [('shrub_%d' % i, (lambda i=i: BS.shrub('shrub_%d' % i, 110 + i))) for i in range(1, 5)],
    'susuki': [('susuki_%d' % i, (lambda i=i: HB.susuki('susuki_%d' % i, 120 + i))) for i in range(1, 6)],
    'fern': [('fern_%d' % i, (lambda i=i: HB.fern('fern_%d' % i, 130 + i))) for i in range(1, 6)],
    'higanbana': [('higanbana_%d' % i, (lambda i=i: HB.higanbana('higanbana_%d' % i, 140 + i))) for i in range(1, 5)],
    'tsuyukusa': [('tsuyukusa_%d' % i, (lambda i=i: HB.tsuyukusa('tsuyukusa_%d' % i, 150 + i))) for i in range(1, 5)],
    'ominaeshi': [('ominaeshi_%d' % i, (lambda i=i: HB.ominaeshi('ominaeshi_%d' % i, 160 + i))) for i in range(1, 5)],
}


REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_OUT = os.path.join(REPO, 'godot', 'art', 'flora')
DEFAULT_RES = 'res://art/flora'


def _prune(pdir, keep_files):
    """Remove files of a plant folder that this build did not write (and their .import files)."""
    for f in os.listdir(pdir):
        base = f[:-len('.import')] if f.endswith('.import') else f
        if base not in keep_files:
            os.remove(os.path.join(pdir, f))


def build(only=None, out=None, res=None, keep=None):
    root = out or DEFAULT_OUT
    res_root = res or DEFAULT_RES
    os.makedirs(root, exist_ok=True)
    godot.install_shared(root)
    cat_path = os.path.join(root, 'catalog.json')
    catalog = {}
    if os.path.exists(cat_path) and only:
        with open(cat_path) as fh:
            catalog = json.load(fh)
    built = []
    for species, items in CATALOG.items():
        if only and species not in only:
            continue
        for name, fn in items:
            t0 = time.time()
            p = fn()
            render.render(p)
            pdir = os.path.join(root, 'plants', species, name)
            meta = render.export(p, pdir)
            res_dir = '%s/plants/%s/%s' % (res_root, species, name)
            _, blocks = godot.write_scene(meta, pdir, res_dir, res_root)
            files = {'meta.json', name + '.tscn'}
            for f in meta['layers'].values():
                files |= {f[k] for k in ('albedo', 'normal', 'data') if k in f}
            _prune(pdir, files)
            catalog[name] = dict(species=species, kind=meta['kind'], layout=meta.get('layout'),
                                 scene=res_dir + '/' + name + '.tscn', layers=meta['layers'],
                                 crown_sort_px=meta.get('crown_sort_px', 0),
                                 crown_height_m=meta.get('crown_height_m'), block=blocks,
                                 collision=meta.get('collision'))
            built.append((name, round(time.time() - t0, 2)))
            if keep is not None:
                keep[name] = p
            print('built %-16s %5.2fs' % (name, time.time() - t0), flush=True)
    if not only:
        # plants no longer in the catalogue
        names = {n for items in CATALOG.values() for n, _ in items}
        pr = os.path.join(root, 'plants')
        for sp in sorted(os.listdir(pr)):
            for n in sorted(os.listdir(os.path.join(pr, sp))):
                if n not in names or sp not in CATALOG:
                    shutil.rmtree(os.path.join(pr, sp, n))
            if not os.listdir(os.path.join(pr, sp)):
                os.rmdir(os.path.join(pr, sp))
    with open(cat_path, 'w') as fh:
        json.dump(catalog, fh, indent=1, sort_keys=True)
    return built


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--only', default='', help='species, comma separated (default: all)')
    ap.add_argument('--out', default=None, help='output folder (default: godot/art/flora)')
    ap.add_argument('--res', default=None, help='res:// path of that folder (default: res://art/flora)')
    a = ap.parse_args()
    only = set(x for x in a.only.split(',') if x) or None
    t = time.time()
    built = build(only, a.out, a.res)
    print('%d plants in %.1fs' % (len(built), time.time() - t))
