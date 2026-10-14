"""The bake, stage by stage: layout -> world rasters -> top paint (world) ->
projection -> face paint (screen) -> lighting data."""
import time
import numpy as np

from . import layout, painter, mat_top, mat_face, lighting, atlases as atl
from .palette import resolve


class Bake:
    pass


def run(layout_path, sources=None, rebuild_atlases=False, log=print):
    B = Bake()
    t0 = time.time()
    spec = layout.load(layout_path)
    B.spec = spec
    B.atlases = atl.get(sources, rebuild_atlases)
    t = time.time()
    B.world = layout.World(spec).build()
    log(f'  layout       {time.time() - t:5.1f}s  world {B.world.W}x{B.world.H} px')
    for n in B.world.notes:
        log('  note: ' + n)
    t = time.time()
    B.top = mat_top.paint_tops(B.world, B.atlases, seed=B.world.seed)
    log(f'  tops         {time.time() - t:5.1f}s')
    t = time.time()
    B.screen = painter.project(B.world)
    log(f'  projection   {time.time() - t:5.1f}s  screen {B.screen.W}x{B.screen.H} px')
    t = time.time()
    B.paint = mat_face.paint_faces(B.screen, B.world, B.top, B.atlases, seed=B.world.seed)
    log(f'  faces        {time.time() - t:5.1f}s')
    t = time.time()
    toward = spec.get('sun', {}).get('toward_xz', [-0.92, 0.38])
    B.toward = toward
    B.horizon, B.sky = lighting.screen_light(B.screen, B.world, B.paint, toward)
    log(f'  lighting     {time.time() - t:5.1f}s')
    B.albedo = resolve(B.paint.ramp, B.paint.tone)
    B.mask = B.screen.kind != 0
    log(f'  total        {time.time() - t0:5.1f}s')
    return B
