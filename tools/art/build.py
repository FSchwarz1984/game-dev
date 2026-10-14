"""Retired (2026-10-14, R-4): the hand-drawn sprite generator that lived here (pixart.py, rig.py,
tsu_base.py, tsu_actions.py, tsuzumi.py, saji.py, shione.py; last in git at 3d24b91)
was replaced by the 3D model generator in tools/art/sprite3d/ (docs/knowledge/20-sprites.md).

This stub only stops an old habit from overwriting the new sheets in assets/sprites/ with the old
ones. Build the characters with:

    python3 -I tools/art/sprite3d/build.py [--preview DIR] [--only NAME]
    python3 -I tools/godot/sync_assets.py --sprites-only
"""

import sys

if __name__ == '__main__':
    sys.exit(__doc__)
