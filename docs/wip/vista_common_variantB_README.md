# 备选 B：白天遠化的边和夜里一样宽（未采用，等用户选）

`vista_common_variantB_wider_edge.gdshaderinc` 是 `godot/render3d/shaders/vista_common.gdshaderinc` 的替换版（2026-10-16，远景代理，G5R3-37）。

- 边的宽度在量过的几条线上都达到夜里的 0.88 倍以上（向左 1.0、向上 1.9、整条边 1.06），12:30 的明度、彩度、对比验收也过。
- 代价：在 k 0.3–0.85 减掉了明暗拉开、抬亮和去雾，所以往东看时云海里的暗斑消失（L* 24 → 57），外圈的地比 G5R3-35 定的朦胧。用户定了暗斑保留（G5R3-38），所以第一版交的是现在主树里的版本。
- 要换：用这个文件覆盖 `godot/render3d/shaders/vista_common.gdshaderinc`，跑 `test_vista`，重出眺望的帧核对。
