# 備選 B：白天遠化的邊和夜裡一樣寬（未採用，等用戶選）

`vista_common_variantB_wider_edge.gdshaderinc` 是 `godot/render3d/shaders/vista_common.gdshaderinc` 的替換版（2026-10-16，遠景代理，G5R3-37）。

- 邊的寬度在量過的幾條線上都達到夜裡的 0.88 倍以上（向左 1.0、向上 1.9、整條邊 1.06），12:30 的明度、彩度、對比驗收也過。
- 代價：在 k 0.3–0.85 減掉了明暗拉開、抬亮和去霧，所以往東看時雲海裡的暗斑消失（L* 24 → 57），外圈的地比 G5R3-35 定的朦朧。用戶定了暗斑保留（G5R3-38），所以第一版交的是現在主樹裡的版本。
- 要換：用這個文件覆蓋 `godot/render3d/shaders/vista_common.gdshaderinc`，跑 `test_vista`，重出眺望的幀核對。
