"""Blender: the blueprint views of the model with every part in its own flat ID colour (for measuring
keypoints exactly on the model). Writes ids_<view>.png and ids.json (part -> colour).
blender -b --factory-startup --python bp_ids.py -- OUTDIR"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import bpy
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
owner = built['owner']
names = sorted(set(p.name for p, _ in owner))
ids = {}
for k, n in enumerate(names):
    # well-separated colours: k -> (r, g, b) on a 6-level cube
    ids[n] = (40 + 40 * (k % 5), 40 + 40 * ((k // 5) % 5), 60 + 60 * (k // 25))
assert len(set(ids.values())) == len(ids)
pa = obj.data.color_attributes['Preview']
for vi, (part, li) in enumerate(owner):
    c = ids[part.name]
    pa.data[vi].color_srgb = (c[0] / 255, c[1] / 255, c[2] / 255, 1.0)
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
PAD = 200                       # a wider frame than the sheet's crop: nothing of the model is clipped
for v, fr in frames.items():
    W = info[v]['x1'] - info[v]['x0'] + 1 + 2 * PAD
    H = info[v]['y1'] - info[v]['y0'] + 1 + PAD
    scene.render.resolution_x, scene.render.resolution_y = W, H
    cam.data.ortho_scale = W * S
    xc = (W / 2.0 - (fr['axis'] + PAD)) * S
    zc = (fr['ground'] + PAD - H / 2.0) * S
    cam.location = (xc, -20.0, zc)
    cam.rotation_euler = (math.radians(90), 0, 0)
    obj.rotation_euler = (0, 0, math.radians(fr['yaw']))
    bpy.context.view_layer.update()
    scene.render.filepath = os.path.join(out, 'ids_%s.png' % v)
    bpy.ops.render.render(write_still=True)
json.dump({'ids': ids, 'pad': PAD}, open(os.path.join(out, 'ids.json'), 'w'), indent=1)
print('IDS DONE')
