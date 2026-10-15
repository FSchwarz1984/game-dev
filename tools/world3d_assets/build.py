#!/usr/bin/env python3
"""Build the 3D assets of the summit home (trees, plants, buildings, props) in one command:

    python3 tools/world3d_assets/build.py                    # everything
    python3 tools/world3d_assets/build.py --only camphor      # some generators (others keep their files)
    python3 tools/world3d_assets/build.py --no-godot          # intermediates only (tools/world3d_assets/out)

Steps: the Python generators (w3a/) write PNG textures with hand-written .import files (lossless,
no mipmaps, detect_3d off: docs/knowledge/21 section 2.3) and binary mesh blobs into out/stage and
out/blobs, plus out/manifest.json; a scratch Godot project (out/pack: the renderer's shaders and the
project's shader globals) imports the textures and runs godot/package.gd, which writes .res meshes,
.tres materials (the renderer's toon_solid / toon_foliage shaders) and .tscn scenes; ids are made
stable; the result replaces godot/world3d/assets/ (res://world3d/assets), with catalog.json.
Deterministic: the same code gives byte-identical files.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'bench'))

from w3a.export import Out  # noqa: E402
import make_bench  # noqa: E402

GODOT = os.environ.get('GODOT_BIN', '/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64')
ASSETS = os.environ.get('W3A_ASSETS', os.path.join(REPO, 'godot', 'world3d', 'assets'))   # override for experiments

# generator modules; each build(out) adds its assets
GENERATORS = [
    'w3a.species.camphor',
    'w3a.species.sugi',
    'w3a.species.pine',
    'w3a.species.maple',
    'w3a.species.kaki',
    'w3a.species.plants',
    'w3a.species.broadleaf',
    'w3a.props.lights',
    'w3a.props.graves',
    'w3a.props.dosojin',
    'w3a.props.shrine',
    'w3a.props.dressing',
    'w3a.props.minka',
    'w3a.props.yard',
    'w3a.props.sacred',
]

# assets of earlier rounds that no longer exist (removed from the catalog and the assets folder on
# every build): the round-3 hut became the house 'hut' of minka.py; fixed-position props renamed
RETIRED = ['minka', 'fence_bamboo', 'signpost', 'waymark', 'basket_tall', 'basket_flat', 'straw_sheaves', 'straw_heap']


def run_generators(only, out_dir):
    if os.path.exists(out_dir):
        for sub in ('stage', 'blobs'):
            shutil.rmtree(os.path.join(out_dir, sub), ignore_errors=True)
    out = Out(out_dir)
    stats = {}
    for modname in GENERATORS:
        short = modname.split('.')[-1]
        if only and short not in only:
            continue
        t0 = time.time()
        mod = importlib.import_module(modname)
        st = mod.build(out)
        stats[short] = {'seconds': round(time.time() - t0, 1), **(st or {})}
        print(f'  {short}: {stats[short]}', flush=True)
    out.write()
    return out, stats


def write_catalog(out, dst_root, only):
    path = os.path.join(dst_root, 'catalog.json')
    cat = {'version': 1, 'assets': {}}
    if only and os.path.exists(path):
        cat = json.load(open(path))
    for a in out.assets:
        if a.catalog:
            e = dict(a.catalog)
            e.setdefault('category', a.category)
            e.setdefault('scene', f'res://world3d/assets/{a.rel}/{a.name}.tscn')
            cat['assets'][a.name] = e
        for vname, ve in a.entries.items():
            e = dict(ve)
            e.setdefault('category', a.category)
            cat['assets'][vname] = e
    for r in RETIRED:
        cat['assets'].pop(r, None)
    cat['assets'] = dict(sorted(cat['assets'].items()))
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cat, f, indent=1, ensure_ascii=False)
        f.write('\n')


def pack(out, out_dir, only):
    proj = os.path.join(out_dir, 'pack')
    os.makedirs(proj, exist_ok=True)
    with open(os.path.join(proj, 'project.godot'), 'w', encoding='utf-8') as f:
        f.write(make_bench.project_text().replace('w3a_bench', 'w3a_pack'))
    make_bench.copytree(os.path.join(REPO, 'godot', 'render3d'), os.path.join(proj, 'render3d'))
    dst = os.path.join(proj, 'world3d', 'assets')
    if os.path.exists(dst):
        shutil.rmtree(dst)
    if only and os.path.exists(ASSETS):
        shutil.copytree(ASSETS, dst)
        for r in RETIRED:
            for cat_dir in os.listdir(dst):
                d = os.path.join(dst, cat_dir, r)
                if os.path.isdir(d):
                    shutil.rmtree(d)
    os.makedirs(dst, exist_ok=True)
    for a in out.assets:
        d = os.path.join(dst, a.category, a.name)
        if os.path.exists(d):
            shutil.rmtree(d)
        shutil.copytree(os.path.join(out.stage, a.category, a.name), d)
    write_catalog(out, dst, only)
    t0 = time.time()
    r = subprocess.run([GODOT, '--headless', '--path', proj, '--import'], capture_output=True, text=True, timeout=1800)
    imp_log = r.stdout + r.stderr
    cmd = [GODOT, '--headless', '--path', proj, '--script', os.path.join(HERE, 'godot', 'package.gd'), '--',
           os.path.join(out_dir, 'manifest.json')]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    log = imp_log + '\n----\n' + r.stdout + r.stderr
    with open(os.path.join(out_dir, 'pack.log'), 'w') as f:
        f.write(log)
    errs = [l for l in log.splitlines() if ('ERROR' in l or 'SCRIPT ERROR' in l or 'failed' in l)
            and 'ALSA' not in l and 'audio' not in l.lower() and 'status < 0' not in l]
    for l in log.splitlines():
        if l.startswith('packed:'):
            print('  ' + l + f' ({time.time() - t0:.1f} s)')
    if errs:
        print('  Godot reported problems (see out/pack.log):')
        for l in errs[:20]:
            print('   ', l)
    normalise_text_resources(dst)
    if os.path.exists(ASSETS):
        shutil.rmtree(ASSETS)
    shutil.copytree(dst, ASSETS)
    return not errs


def normalise_text_resources(root):
    """Godot writes random ids into .tscn/.tres files (ext_resource ids, node unique_id). Make
    them sequential / path-derived so a rebuild without changes gives identical files."""
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if not fn.endswith(('.tscn', '.tres')):
                continue
            p = os.path.join(dp, fn)
            s = open(p, encoding='utf-8').read()
            ids = re.findall(r'\[(?:ext|sub)_resource [^\]]*id="([^"]+)"', s)
            mapping = {old: f'{k + 1}' for k, old in enumerate(ids)}

            def rep_id(m):
                return m.group(0).replace(f'id="{m.group(1)}"', f'id="{mapping[m.group(1)]}"')
            s = re.sub(r'\[(?:ext|sub)_resource [^\]]*id="([^"]+)"[^\]]*\]', rep_id, s)
            s = re.sub(r'(ExtResource|SubResource)\("([^"]+)"\)', lambda m: f'{m.group(1)}("{mapping.get(m.group(2), m.group(2))}")', s)

            def rep_uid(m):
                h = zlib.crc32(((m.group(2) or '') + '/' + m.group(1)).encode()) & 0x7FFFFFFF
                return m.group(0).replace('unique_id=' + m.group(3), 'unique_id=' + str(h))
            s = re.sub(r'\[node name="([^"]+)"[^\]]*?(?:parent="([^"]*)")?[^\]]*unique_id=(\d+)', rep_uid, s)
            open(p, 'w', encoding='utf-8').write(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='', help='comma-separated generator names')
    ap.add_argument('--no-godot', action='store_true')
    ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    a = ap.parse_args()
    only = [s for s in a.only.split(',') if s]
    t0 = time.time()
    print('generating...', flush=True)
    out, stats = run_generators(only, a.out)
    stats['_triangles'] = out.tri_count
    with open(os.path.join(a.out, 'stats.json'), 'w') as f:
        json.dump(stats, f, indent=1)
    print('  triangles per asset:', out.tri_count)
    if not a.no_godot:
        print('packing in Godot...', flush=True)
        ok = pack(out, a.out, only)
        if not ok:
            sys.exit(1)
    print(f'done in {time.time() - t0:.1f} s')


if __name__ == '__main__':
    main()
