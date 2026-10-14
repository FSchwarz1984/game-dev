"""Create (or refresh) the asset bench: a scratch copy of the Godot project's 3D renderer
(godot/render3d), her scale-figure sprite, the project settings (shader globals) and this bench's
driver, plus res://world3d/assets from the repo. Rendering in a copy keeps the main project's
import cache and other agents' files untouched. Usage:
    python3 tools/world3d_assets/bench/make_bench.py <bench_dir>"""
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
GODOT = os.environ.get('GODOT_BIN', '/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64')


def project_text():
    src = open(os.path.join(REPO, 'godot', 'project.godot'), encoding='utf-8').read()
    # drop the game's autoloads, audio and main scene: the bench only needs rendering and globals
    out = []
    skip = False
    for line in src.splitlines():
        if line.startswith('['):
            skip = line.strip() in ('[autoload]', '[audio]')
        if skip:
            continue
        if line.startswith('run/main_scene') or line.startswith('config/icon'):
            continue
        out.append(line)
    s = '\n'.join(out) + '\n'
    s = re.sub(r'config/name="[^"]*"', 'config/name="w3a_bench"', s)
    return s


def copytree(src, dst):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    if os.path.exists(src):
        shutil.copytree(src, dst)


def main(bench, reimport=True):
    os.makedirs(bench, exist_ok=True)
    with open(os.path.join(bench, 'project.godot'), 'w', encoding='utf-8') as f:
        f.write(project_text())
    copytree(os.path.join(REPO, 'godot', 'render3d'), os.path.join(bench, 'render3d'))
    os.makedirs(os.path.join(bench, 'art', 'sprites'), exist_ok=True)
    for fn in ('tsuzumi_plain.png', 'tsuzumi_plain_n.png'):
        for ext in ('', '.import'):
            p = os.path.join(REPO, 'godot', 'art', 'sprites', fn + ext)
            if os.path.exists(p):
                shutil.copy(p, os.path.join(bench, 'art', 'sprites', fn + ext))
    os.makedirs(os.path.join(bench, 'w3a'), exist_ok=True)
    for fn in ('w3a_bench.gd', 'w3a_bench.tscn'):
        shutil.copy(os.path.join(HERE, fn), os.path.join(bench, 'w3a', fn))
    sync_assets(bench)
    if reimport:
        subprocess.run([GODOT, '--headless', '--path', bench, '--import'], capture_output=True, timeout=600)


def sync_assets(bench):
    copytree(os.path.join(REPO, 'godot', 'world3d', 'assets'), os.path.join(bench, 'world3d', 'assets'))


if __name__ == '__main__':
    main(sys.argv[1])
