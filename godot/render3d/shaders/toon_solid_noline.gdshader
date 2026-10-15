// Solid toon material, outline class 5: no outline (ground decals, flat things). See toon_solid_body.gdshaderinc.
shader_type spatial;
render_mode world_vertex_coords, specular_disabled, cull_back;
stencil_mode write, compare_always, 5;
#include "res://render3d/shaders/toon_solid_body.gdshaderinc"
