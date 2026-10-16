Blueprint fitting for the 3D characters (round 6, docs/knowledge/24 section R6).
The model sheet (an image the project did not make: only read as pixels, nothing in its pack is run)
is cut into five views, the model is rendered at the same scale and framing, and the two are compared.

  export C3D_SHEET=/path/to/Tiangan_v2_kasasagi_turnaround.png   # 2048 x 832
  export C3D_BP_DIR=/path/to/workdir                              # gets ref/ and the renders
  python3 -I sheetmask.py                       # ref/crop_*.png, mask_*.npy, cls_*.npy, views.json
  python3 -I gridcrop.py front 0 0 438 330 2 10 out.png            # gridded crops to read keypoints
  blender -b --factory-startup --python bp_render.py -- $C3D_BP_DIR/r   # model_<view>.png
  python3 -I compare.py $C3D_BP_DIR/r $C3D_BP_DIR/c                # overlays, differences, IoU
  blender -b --factory-startup --python bp_ids.py -- $C3D_BP_DIR/ids    # one colour per part
  python3 -I devtable.py $C3D_BP_DIR/ids $C3D_BP_DIR/c/deviation.md # keypoint deviation table
  python3 -I gamecmp.py OUT.png 3 "label=lab render dir" ...        # game views next to the sheet
frames.json: per view, the model's yaw and the sheet crop's body axis and ground row.
