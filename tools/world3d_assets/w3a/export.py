"""Intermediate output for the Godot packager (tools/world3d_assets/godot/package.gd).

Layout (docs/knowledge/21 section 2): every asset lives in godot/world3d/assets/<category>/<name>/
with <name>.tscn, its meshes (.res) and textures (PNG + a hand-written .import: lossless, no
mipmaps, detect_3d off), and one entry in godot/world3d/assets/catalog.json.

The generators write into a stage folder: PNG + .import files directly, meshes as binary blobs;
the packager builds .res meshes, .tres materials and .tscn scenes next to them.

Blob layout (little endian), per surface, in this order:
  positions float32 (n, 3) · normals float32 (n, 3) · uv float32 (n, 2) · [uv2 float32 (n, 2)]
  · [colour float32 (n, 4)] · [custom0 float32 (n, 4)] · [custom1 float32 (n, 4)] · indices int32 (t, 3)
Triangles are written in Godot's winding (clockwise front faces): our builders make
counter-clockwise outward triangles, so every triangle is flipped here once.
"""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np
from PIL import Image

from .mesh import MeshData

RES_ROOT = 'res://world3d/assets/'
SHADERS = 'res://render3d/shaders/'

_UID_CHARS = 'abcdefghijklmnopqrstuvwxy012345678'


def uid_for(path):
    """A stable Godot uid text for a resource path (so rebuilds give identical files)."""
    h = int.from_bytes(hashlib.sha1(path.encode('utf-8')).digest()[:8], 'little') & 0x7FFFFFFFFFFFFFFF
    s = ''
    while True:
        s = _UID_CHARS[h % 34] + s
        h //= 34
        if h == 0:
            break
    return 'uid://' + s


IMPORT_TEMPLATE = """[remap]

importer="texture"
type="CompressedTexture2D"
uid="{uid}"

[deps]

source_file="{src}"

[params]

compress/mode=0
compress/high_quality=false
compress/lossy_quality=0.7
compress/uastc_level=0
compress/rdo_quality_loss=0.0
compress/hdr_compression=1
compress/normal_map=0
compress/channel_pack=0
mipmaps/generate=false
mipmaps/limit=-1
roughness/mode=0
roughness/src_normal=""
process/channel_remap/red=0
process/channel_remap/green=1
process/channel_remap/blue=2
process/channel_remap/alpha=3
process/fix_alpha_border=true
process/premult_alpha=false
process/normal_map_invert_y=false
process/hdr_as_srgb=false
process/hdr_clamp_exposure=false
process/size_limit=0
detect_3d/compress_to=0
"""


class Asset:
    def __init__(self, out, name, category):
        self.out = out
        self.name = name
        self.category = category
        self.rel = f'{category}/{name}'
        self.dir = os.path.join(out.stage, category, name)
        os.makedirs(self.dir, exist_ok=True)
        self.res = RES_ROOT + self.rel + '/'
        self.catalog = {}
        out.assets.append(self)

    def texture(self, key, rgba):
        """Writes <name>_<key>.png (+ .import). Returns its res:// path."""
        rgba = np.clip(np.round(np.asarray(rgba, np.float64)), 0, 255).astype(np.uint8)
        fn = f'{self.name}_{key}.png'
        mode = 'RGBA' if rgba.shape[2] == 4 else 'RGB'
        Image.fromarray(rgba, mode).save(os.path.join(self.dir, fn), optimize=True)
        res = self.res + fn
        with open(os.path.join(self.dir, fn + '.import'), 'w') as f:
            f.write(IMPORT_TEMPLATE.format(uid=uid_for(res), src=res))
        assert rgba.shape[0] <= 256 and rgba.shape[1] <= 256, f'{fn}: textures must be <= 256x256 (contract 2.3)'
        return res

    def material(self, key, shader, params=None, textures=None, render_priority=0):
        """shader: file name in res://render3d/shaders (e.g. 'toon_solid.gdshader')."""
        mname = f'{self.name}_{key}'
        self.out.manifest['materials'][self.res + mname + '.tres'] = {
            'shader': SHADERS + shader, 'params': params or {}, 'textures': textures or {},
            'render_priority': render_priority}
        return self.res + mname + '.tres'

    def mesh(self, key, surfaces, custom_aabb=None):
        """surfaces: list of (material res path, MeshData). Returns the mesh res path."""
        mname = f'{self.name}_{key}'
        blob = []
        desc = []
        off = 0
        lo = np.full(3, np.inf)
        hi = np.full(3, -np.inf)
        tris = 0
        for mat, md in surfaces:
            a = md.arrays() if isinstance(md, MeshData) else md
            if a is None:
                continue
            n = len(a['p'])
            idx = a['idx'][:, [0, 2, 1]].astype(np.int32)
            parts = [a['p'].astype(np.float32), a['n'].astype(np.float32), a['uv'].astype(np.float32)]
            d = {'material': mat, 'vertices': n, 'triangles': int(len(idx)), 'offset': off,
                 'uv2': 'uv2' in a, 'color': 'col' in a, 'custom0': 'cus' in a, 'custom1': 'cus1' in a}
            for k in ('uv2', 'col', 'cus', 'cus1'):
                if k in a:
                    parts.append(a[k].astype(np.float32))
            parts.append(idx)
            for p in parts:
                b = np.ascontiguousarray(p).tobytes()
                blob.append(b)
                off += len(b)
            desc.append(d)
            tris += len(idx)
            lo = np.minimum(lo, a['p'].min(0))
            hi = np.maximum(hi, a['p'].max(0))
        path = os.path.join(self.out.blobs, f'{self.category}__{mname}.bin')
        with open(path, 'wb') as f:
            for b in blob:
                f.write(b)
        entry = {'bin': os.path.abspath(path), 'surfaces': desc, 'aabb': [lo.tolist(), (hi - lo).tolist()]}
        if custom_aabb is not None:
            entry['custom_aabb'] = custom_aabb
        self.out.manifest['meshes'][self.res + mname + '.res'] = entry
        self.out.tri_count[self.name] = self.out.tri_count.get(self.name, 0) + tris
        return self.res + mname + '.res'

    def scene(self, nodes, meta=None, script=None, key=None):
        """nodes: list of dicts {name, type: 'mesh'|'marker'|'node', mesh (res path), pos, rot (deg),
        scale, parent, cast_shadow ('on'|'off'|'double'|'only'), visible, meta, material_override}."""
        fn = f'{self.name}.tscn' if key is None else f'{self.name}_{key}.tscn'
        self.out.manifest['scenes'].append({'path': self.res + fn, 'nodes': nodes, 'meta': meta or {},
                                            'script': script})
        return self.res + fn


class Out:
    def __init__(self, root):
        self.root = root
        self.stage = os.path.join(root, 'stage')
        self.blobs = os.path.join(root, 'blobs')
        for d in (self.stage, self.blobs):
            os.makedirs(d, exist_ok=True)
        self.assets = []
        self.tri_count = {}
        self.manifest = {'meshes': {}, 'materials': {}, 'scenes': []}

    def asset(self, name, category):
        return Asset(self, name, category)

    def write(self):
        self.manifest['assets'] = [{'name': a.name, 'category': a.category, 'rel': a.rel, 'catalog': a.catalog}
                                   for a in self.assets]
        with open(os.path.join(self.root, 'manifest.json'), 'w') as f:
            json.dump(self.manifest, f, indent=1)
