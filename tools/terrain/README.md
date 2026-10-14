# tools/terrain — terrain baker

Turns a hand-authored vector layout (JSON) into baked, lit-ready pixel-art ground for the
3/4 oblique view (1 m = 20 px; screen x = x, screen y = z − h), plus the ground masks the
game walks on. The rules it implements are in `docs/knowledge/15-perspective-rules.md`; the
method, formats and known weaknesses are in `docs/knowledge/17-terrain-pipeline.md` (Chinese).

## One command

```sh
python3 tools/terrain/bake.py tools/terrain/layouts/home_saddle.json --godot
```

* Writes the full bake to `tools/terrain/out/<name>/` (git-ignored: chunks, masks, previews).
* `--godot` also writes the Godot-ready region to `godot/world/regions/<name>/` (region.json in
  the core's contract, `logic.png`, `ground.png`, lit `terrain/` chunks, `terrain.gdshader`).
* About 2 minutes on 4 CPUs. Needs `numpy scipy scikit-image pillow` (system python3 has them).
* `--no-previews` skips the four full-size lit previews; `--out DIR`, `--chunk 512`.

## Pipeline

1. **Layout** (`layout.py`): levels (closed splines with organic edges, heights in 0.5 m
   steps, stacked in order), stairs (north–south only, cut into the cliff with stepped cheek
   stones, posts, landing, apron and dressed-stone walls either side), gentle ramps (≤ 1:3,
   checked), water, material patches, roads (polylines), markers.
2. **Tops** (`mat_top.py`): every horizontal surface painted in world space as indexed
   (ramp, tone): grass/lawn/moss/forest floor/dirt road/earth/rock/gravel/scree/stone
   treads/water, then glyph passes (tufts, flowers, pebbles, rock fall at cliff feet).
3. **Projection** (`painter.py`): every world pixel is a top candidate, every southward drop a
   column of face candidates; the winner per screen pixel is the nearest (depth z + h).
   East/west walls get a 1–2 px side strip.
4. **Faces** (`mat_face.py`): cliffs from photoscan-derived rock plates with bedding, earth
   banks with vegetation, dry-stone walls, stair risers and cheeks; sod overhanging every
   vegetated lip; plants at every cliff foot overlapping the face.
5. **Lighting data** (`lighting.py`): per pixel, the elevation of the terrain horizon toward
   the fixed sun azimuth (shadows then lengthen continuously with the sun's elevation) and
   sky visibility (AO).
6. **Export** (`export.py`): 512 px screen chunks (albedo, normal, light, depth), world masks,
   walk polygons, markers, region.json; optional Godot region.

All colours come from short ramps in `palette.py` (CIELAB, low chroma, cool shadows, warm
lights). Time of day is lighting, never repainting.

## Layout format (`tengan-terrain/1`)

```jsonc
{
  "format": "tengan-terrain/1", "name": "home_saddle",
  "bounds": [x0, z0, x1, z1],            // metres, x east, z south
  "seed": 7, "datum_m": 10.0,            // exported heights = layout heights + datum (>= 0)
  "sun": {"toward_xz": [-0.92, 0.38]},   // fixed azimuth toward the sun (screen upper left)
  "levels": [{"id", "height", "shape": [[x, z], ...], "top": "meadow|lawn|moss|forest|dirt|earth|gravel|rock|...",
              "face": "rock|earth|wall|bank", "edge": {"amp", "wave", "rough", "bite"}, "smooth": true, "rect": false}],
  "stairs": [{"id", "x", "z_bottom", "width", "from", "to", "steps", "tread", "cheek", "curb", "wall", "wall_depth"}],
  "ramps":  [{"id", "shape", "from": {"at": [x, z], "height"}, "to": {...}, "face"}],
  "water":  [{"id", "shape", "surface", "depth", "shelf", "wet"}],
  "patches": [{"shape", "top"?, "face"?, "on": [tops]?, "wild"?, "edge"?}],
  "roads":  [{"id", "points", "width", "surface", "wear", "wobble"?}],
  "godot":  {"label", "spawn", "companion", "shots"},     // copied into the Godot region.json
  "markers": [{"id", "kind", "at", "footprint"?, "note"?}]  // trees/buildings/props placed by other generators
}
```

Levels are applied in order (later wins), so draw the low ground first and stack terraces on
top. A stair's `z_bottom` is the cliff foot; the flight climbs north into the upper level.

## Rock atlases (CC0 shape sources)

`data/atlas_*.npz` are small segmentations of Poly Haven photoscan height maps (CC0):
`dark_rock_02` (cliff bedding, rock tops), `rock_wall_10` (dry-stone walls),
`dry_river_pebbles` (scree, gravel, stones in banks). Only plate shapes are used; every pixel
is drawn from our ramps. Rebuild: `python3 tools/terrain/fetch_sources.py DIR` then
`bake.py LAYOUT --rebuild-atlases --sources DIR`.

## Godot side

`godot/terrain.gdshader` and `godot/terrain_chunks.gd` are the reference run-time pieces:
CanvasModulate = ambient, one DirectionalLight2D = sun colour/energy, PointLight2D lanterns
through the normal map; the shader applies the baked horizon so shadows never jump.
