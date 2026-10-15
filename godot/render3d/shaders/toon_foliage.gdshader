// Foliage toon material, outline class 2: foliage, silhouette outline only. See toon_foliage_body.gdshaderinc.
shader_type spatial;
render_mode world_vertex_coords, specular_disabled, cull_disabled;
stencil_mode write, compare_always, 2;
#include "res://render3d/shaders/toon_foliage_body.gdshaderinc"
