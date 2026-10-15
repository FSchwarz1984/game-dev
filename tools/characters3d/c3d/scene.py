"""Blender side of the builder: Parts -> mesh objects with the attributes the Godot shader reads,
custom normals, preview renders, glTF export."""
import math
import bpy
from mathutils import Vector, Matrix


def reset_scene(fps=30):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.fps = fps
    s.unit_settings.system = 'METRIC'
    return s


def merge(parts):
    verts, faces, cols, uv0, uv1, nrm, owner = [], [], [], [], [], {}, []
    for part in parts:
        base = len(verts)
        verts += [tuple(p) for p in part.v]
        faces += [tuple(i + base for i in f) for f in part.f]
        cols += part.col
        uv0 += part.uv
        uv1 += [tuple(a) for a in part.aux]
        for k, n in part.nrm.items():
            nrm[k + base] = n
        owner += [(part, i) for i in range(len(part.v))]
    return verts, faces, cols, uv0, uv1, nrm, owner


def mesh_object(name, parts, collection=None):
    """One mesh object from parts. Colour attribute 'Color' (FLOAT, point domain) holds the sRGB albedo
    as plain numbers (exported unchanged as COLOR_0; the Godot shader decodes sRGB itself) and
    'Preview' (BYTE) the same colours for Blender's own preview renders. UV maps: 'UVMap' (TEXCOORD_0)
    and 'Aux' (TEXCOORD_1). glTF flips V (v -> 1 - v) on export, so V is stored flipped here and
    Godot reads the intended value."""
    verts, faces, cols, uv0, uv1, nrm, owner = merge(parts)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ca = me.color_attributes.new('Color', 'FLOAT_COLOR', 'POINT')
    for i, c in enumerate(cols):
        ca.data[i].color = c
    pa = me.color_attributes.new('Preview', 'BYTE_COLOR', 'POINT')
    for i, c in enumerate(cols):
        pa.data[i].color_srgb = c
    me.color_attributes.active_color = ca
    for lname, data in (('UVMap', uv0), ('Aux', uv1)):
        layer = me.uv_layers.new(name=lname)
        for poly in me.polygons:
            for li in poly.loop_indices:
                vi = me.loops[li].vertex_index
                u, v = data[vi]
                layer.data[li].uv = (u, 1.0 - v)
    me.uv_layers.active_index = 0
    for poly in me.polygons:
        poly.use_smooth = True
    me.update()
    if nrm:
        vn = [Vector(v.normal) for v in me.vertices]
        for k, n in nrm.items():
            vn[k] = Vector(n).normalized()
        me.normals_split_custom_set_from_vertices([tuple(n) for n in vn])
    obj = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(obj)
    obj['owner_count'] = len(owner)
    return obj, owner


# ------------------------------------------------------------------------------------------------
# previews (Workbench): front orthographic, and the game's view (lean + 55 degree pitch)

LEAN_K = math.tan(math.radians(55.0) / 2.0)


def lean_copy(obj, k=LEAN_K):
    """A copy of the evaluated object (armature deformation included) with the game's lean applied:
    every point moves north (+Y here) by k times its height."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    me.transform(obj.matrix_world)
    shear = Matrix.Identity(4)
    shear[1][2] = k
    me.transform(shear)
    cp = bpy.data.objects.new(obj.name + '_lean', me)
    bpy.context.scene.collection.objects.link(cp)
    return cp


def setup_preview(scene, res=(480, 640), ortho=2.4, view='game', centre=(0, 0, 0.85), outline=True):
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    sh = scene.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'VERTEX'
    sh.show_object_outline = outline
    sh.object_outline_color = (0.05, 0.04, 0.06)
    sh.show_cavity = False
    sh.background_type = 'VIEWPORT'
    sh.background_color = (0.62, 0.66, 0.58)
    scene.display.render_aa = '8'
    cam = bpy.data.objects.get('PreviewCam')
    if cam is None:
        cam = bpy.data.objects.new('PreviewCam', bpy.data.cameras.new('PreviewCam'))
        scene.collection.objects.link(cam)
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = ortho
    c = Vector(centre)
    if view == 'game':
        pitch = math.radians(55.0)
        d = Vector((0, math.cos(pitch), -math.sin(pitch)))     # looking north and down
        cam.location = c - d * 20
        cam.rotation_euler = (math.radians(90.0 - 55.0), 0, 0)
    elif view == 'front':
        cam.location = c + Vector((0, -20, 0))
        cam.rotation_euler = (math.radians(90), 0, 0)
    elif view == 'side':
        cam.location = c + Vector((20, 0, 0))
        cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    elif view == 'back':
        cam.location = c + Vector((0, 20, 0))
        cam.rotation_euler = (math.radians(90), 0, math.radians(180))
    elif view == 'game_back':
        # the game's camera with her back to it (she faces north, away from the camera)
        pitch = math.radians(55.0)
        d = Vector((0, -math.cos(pitch), -math.sin(pitch)))
        cam.location = c - d * 20
        cam.rotation_euler = (math.radians(90.0 - 55.0), 0, math.radians(180))
    cam.data.clip_start = 0.1
    cam.data.clip_end = 100
    scene.camera = cam
    return cam


def render(scene, path):
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def export_glb(path, objects, armature=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    if armature is not None:
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, export_yup=True,
        export_texcoords=True, export_normals=True, export_tangents=False,
        export_vertex_color='NAME', export_vertex_color_name='Color', export_all_vertex_colors=False,
        export_materials='PLACEHOLDER', export_animations=True, export_animation_mode='ACTIONS',
        export_force_sampling=True, export_frame_step=1, export_optimize_animation_size=False,
        export_anim_single_armature=True, export_reset_pose_bones=True, export_rest_position_armature=True,
        export_skins=True, export_influence_nb=4, export_morph=True, export_morph_normal=False,
        export_def_bones=False, export_leaf_bone=False, export_apply=False, export_cameras=False,
        export_lights=False, export_extras=False)
