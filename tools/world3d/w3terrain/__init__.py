"""Natural terrain generator for the 3D pixel world (docs/knowledge/21-3d-pixel-render.md).

layout JSON (metres, x east, z south, heights relative to the saddle crown)
  -> designed landform (saddle, shoulders, south slope, spur, gully)
  -> erosion on the open slopes (flow accumulation, stream power, hillslope diffusion)
  -> human-made edits (road cut and fill, the hut's yard, the shrine terrace, rice terraces)
  -> material weights (grass, worn path, gravel, rock, moss, leaf litter, bank earth, paddy)
  -> Godot data (godot/world3d/terrain/<name>/)
"""
