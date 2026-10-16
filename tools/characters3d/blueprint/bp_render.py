"""Blender: build the static model and render it at the blueprint's scale, one orthographic eye-level
view per turnaround view, framed exactly like the sheet's crop (same size, ground row and axis).
Flat vertex colours (the model's albedo), transparent background, no anti-aliasing.
blender -b --factory-startup --python bp_render.py -- OUTDIR"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bpy
from mathutils import Vector
from c3d import scene as SC
from kasasagi.design import S

C6 = os.environ.get('C3D_BP_DIR', os.path.expanduser('~/c3d_blueprint'))   # work dir: ref/ (the cut sheet), renders
out = sys.argv[sys.argv.index('--') + 1]
os.makedirs(out, exist_ok=True)
info = json.load(open(C6 + '/ref/views.json'))
frames = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frames.json')))
SC.reset_scene(fps=30)
from kasasagi import build as KB
built = KB.build(static=True)
obj = built['mesh']
# the blueprint compares colours as the sheet paints them: the darks the palette pre-compensates for
# the game's light (palette.py, round 6) are shown here as their on-screen targets
from kasasagi import palette as P
from c3d.surf import hex_to_rgb as HX
DISPLAY = [(P.HAIR, HX('#3e344a')), (P.HAIR_DEEP, HX('#2a2133')), (P.HAIR_HI, HX('#5f5071')),
           (P.NAVY_LINING, HX('#252c4b')), (P.NAVY, HX('#33395b')), (P.NAVY_DEEP, HX('#232741')),
           (P.TROUSERS, HX('#38344b')), (P.TROUSERS_DEEP, HX('#1e1c2a')), (P.BOOTS, HX('#332d3b')),
           (P.BOOTS_DEEP, HX('#22202b')), (P.RED, HX('#9b324e')), (P.RED_DEEP, HX('#75253d')),
           (P.RED_HI, HX('#ae3754'))]
pa = obj.data.color_attributes['Preview']
for d in pa.data:
    c = tuple(d.color_srgb)
    for src, dst in DISPLAY:
        if sum(abs(c[i] - src[i]) for i in range(3)) < 0.012:
            d.color_srgb = dst
            break
scene = bpy.context.scene
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
sh = scene.display.shading
sh.light = 'FLAT'
sh.color_type = 'VERTEX'
sh.show_object_outline = False
sh.show_cavity = False
sh.show_backface_culling = False
scene.display.render_aa = 'OFF'
scene.view_settings.view_transform = 'Standard'
cam = bpy.data.objects.new('BPCam', bpy.data.cameras.new('BPCam'))
scene.collection.objects.link(cam)
cam.data.type = 'ORTHO'
cam.data.sensor_fit = 'HORIZONTAL'
cam.data.clip_start = 0.1
cam.data.clip_end = 100
scene.camera = cam
for v, fr in frames.items():
    W = info[v]['x1'] - info[v]['x0'] + 1
    H = info[v]['y1'] - info[v]['y0'] + 1
    scene.render.resolution_x, scene.render.resolution_y = W, H
    cam.data.ortho_scale = W * S
    xc = (W / 2.0 - fr['axis']) * S
    zc = (fr['ground'] - H / 2.0) * S
    cam.location = (xc, -20.0, zc)
    cam.rotation_euler = (math.radians(90), 0, 0)
    obj.rotation_euler = (0, 0, math.radians(fr['yaw']))
    bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(out, 'model_%s.png' % v)
    bpy.ops.render.render(write_still=True)
obj.rotation_euler = (0, 0, 0)
print('BP DONE')
