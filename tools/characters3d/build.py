"""Builds a 3D character for the game: model, rig, skin weights, animations, glTF.

    blender -b --factory-startup --python tools/characters3d/build.py -- [options]
      --char kasasagi            which character (tools/characters3d/<char>/)
      --out PATH.glb             write the glTF (default godot/characters/<char>/<char>.glb)
      --preview DIR              Workbench previews (front, side, back, game view) into DIR
      --pose NAME[@frame]        pose the previews with an animation clip at a frame
      --static                   model only (no rig): quick shape previews
Run from the repository root (tools/characters3d/build.sh does that). See docs/knowledge/24.
"""
import os
import sys
import importlib

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bpy  # noqa: E402
from c3d import scene as SC  # noqa: E402


def parse(argv):
    opts = {'char': 'kasasagi', 'out': None, 'preview': None, 'pose': None, 'static': False, 'poses': None}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--static':
            opts['static'] = True
        elif a.startswith('--') and i + 1 < len(argv):
            opts[a[2:]] = argv[i + 1]
            i += 1
        i += 1
    return opts


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    o = parse(argv)
    char = importlib.import_module(o['char'] + '.build')
    scene = SC.reset_scene(fps=30)
    built = char.build(static=o['static'])
    if o['preview']:
        os.makedirs(o['preview'], exist_ok=True)
        char.previews(built, o['preview'], pose=o['pose'])
    if o.get('poses'):
        d, _, specs = o['poses'].partition(':')
        os.makedirs(d, exist_ok=True)
        char.pose_sheet(built, d, specs.split(','))
    if not o['static'] or o['out']:
        out = o['out'] or os.path.join(os.getcwd(), 'godot', 'characters', o['char'], o['char'] + '.glb')
        # the repository's godot/characters/ holds the models the game uses (kasasagi there is round 4;
        # this generator is the rejected round 6, G5R3-20): replacing one needs C3D_MAIN=1 (build.sh
        # checks the same before it starts Blender)
        game = os.path.realpath(os.path.join(HERE, '..', '..', 'godot', 'characters')) + os.sep
        if (os.path.realpath(out).startswith(game) and os.path.exists(out)
                and os.environ.get('C3D_MAIN', '0') != '1'):
            print("NOT EXPORTED: %s is the game's model (pass --out elsewhere, or set C3D_MAIN=1)" % out)
            return
        os.makedirs(os.path.dirname(out), exist_ok=True)
        char.export(built, out)
        print('EXPORTED', out)


main()
