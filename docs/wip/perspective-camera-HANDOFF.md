# 透视相机与移轴景深（G5R3-27/28）：暂停交接

渲染器代理，2026-10-16 14:55。主管叫停（G5R3-32：一次只做一件事；G5R3-33：队列第 ② 件，第一版 Windows 交付后再开）。

## 1. 东西在哪

- **分支** `wip/renderer-perspective-camera`：本地分支，没有推送。检出在 worktree `scratchpad/wt_cam`，基于 9768ab2（道具用树冠图那次提交）。
  - `2236a83` 第一段：透视相机、四组预设、V 键。编译过，也跑过静帧。
  - `d5e3d70` 爬动测量模式：代码写完了，一次都没运行过。
- **补丁** `scratchpad/wt_cam_paused.patch`，等于 `git diff 9768ab2..wip/renderer-perspective-camera`，共 1017 行。
  - 9768ab2 之后主树改过的文件（到 0b7dfe2 为止）和补丁碰的文件没有重叠，所以补丁能直接打上去。
  - 14:55 对 5f2f3ce 跑过 `git apply --check`，通过。
- **主树一个文件都没动。** worktree 里没有未提交的改动。
- 静帧在 `scratchpad/sample3d/r5/`：
  - `cam_t1/`：P2，院子 09:30；
  - `cam1_P2/`：P2，院子 09:30、17:24、21:30，祠前 09:30。拼图是 `sheet4.png`。F1、F3 两张还没出就停了。
- 脚本：
  - `scratchpad/bin/cam1chain.sh`：四组预设各出一套静帧，一次一组，一组约 15 分钟；
  - `scratchpad/bin/r5shots_at.sh`：任意工程目录、固定 30 fps 的全设置静帧；
  - `scratchpad/bin/crawl.py`：分支里也有一份，在 `tools/world3d/metrics/crawl.py`。

## 2. 做到哪一步（第一段：相机本体 + V 键）

**四组预设**（`PixelView3D.PRESETS`）：

| 预设 | 视野 | 俯角 | 后倾份额 | 相机距离 | 说明 |
|---|---|---|---|---|---|
| P2 | 24° | 50° | 0.3 | 约 28.4 m | sample 的默认 |
| P1 | 12° | 55° | 0.6 | 57.4 m | |
| P3 | 38° | 45° | 0 | 17.5 m | |
| ORTHO | — | 55° | 1.0 | — | 旧相机 |

- 相机距离 = (视口高 / 2 / 30) / tan(视野 / 2)，所以焦点平面上永远是 1 米 = 30 像素。
- `PixelView3D` 类本身的默认仍是 ORTHO，工具（asset_preview、feature_test、角色实验室）都不受影响。
- `sample.gd --camera=P2|P1|P3|ortho` 选预设；`--fov=` 调参。

**相机取整**：

- 相机只在焦点平面的像素格上走整格；焦点平面是过 `_cam_target` 的、垂直于视轴的平面。
- 世界格 `w3_ptex` 仍是钉在世界上的正交格（`w3_screen_o`）。焦点平面上它和屏幕逐像素重合；近处的东西放大，远处的缩小。
- 全局量 `w3_cam` = (相机位置, D)。D 为 0 时就是正交。

**着色器**（`pixel_toon.gdshaderinc`）：

- `w3_screen` 算的是一个点在屏幕上真正落在哪；`w3_screen_o` 是世界格。
- `w3_snap` 在真实的屏幕上把锚点取整到像素角。
- 新函数：`w3_depth`、`w3_px_scale`（深度 / D）、`w3_unproject`。
- `w3_card` / `w3_card_uv`：卡片按屏幕整像素排，任何深度都是一像素对一像素，在画面上保持竖直；深度用照常后倾的卡片的深度，所以前后遮挡不变；UV 写成 UV×深度、深度，在片元里除回来，得到屏幕线性的纹素。
  - 用在：精灵（`sprite_char`、`sprite_xray`）、草丛（`world3d/grass_field.gdshader`，场景代理的文件，改了排布和一个 varying）。
- 光点的大小、叶卡片的摆动、实体的风摆，都按 `w3_px_scale` 换成屏幕整像素。

**V 键**（`sample.gd`）：

- `cycle_camera` → `set_camera(i)` → `pv.set_preset(i)` → `_camera_changed()`。
- `_camera_changed()` 调 `env.fit_to_view()`（太阳阴影的最大距离 D + 45、体积雾长度 D + 45）和 `_relean(k)`。
- `_relean(k)`：挂着的道具（`_hung`）、闪光点、乌鸦和猫重新按新后倾放；她和さぢ的胸口点（`walker.lean_k`）也更新。正交下胸口点保留 0.5，旧画面不变。
- showcase 的 HUD 在时刻下面多一行"镜头　P2 中焦 24°"，按键提示加"V 镜头"。

**其它**：落叶和花瓣的起点从写死的 55° 数字改成 `pv.height_at_row()`（在画面上沿外 26 像素），任何相机都从画面外飘进来。

## 3. 验证过的、没验证的

**验证过的**：

- P2 跑过两次静帧（`cam_t1`、`cam1_P2`），0 个着色器错误，0 个脚本错误（`sample.gd` 整个文件都编译了）。
- 四张 P2 静帧看过：透视正常，人物和さぢ的精灵清楚，夜里的灯、黄昏没有坏；祠前大楠的树干透视很强。
- 还没逐张和正交对照、挑过毛病。

**没验证的**：

1. **V 键运行时的切换**：`_camera_changed`、`_relean`、`_lean_walkers` 这一串，以及 showcase HUD。`showcase_hud.gd` 这次没加载过。
2. P1、P3、正交三组的画面。
3. **正交一组和 9768ab2 是否逐像素相同。** 应当相同：正交走的全是旧路径，`w3_card` 在正交下就是旧的后倾卡片，`v_uvd` 等于 UV。验法：两边都用 `--seed=1`，固定 30 fps，参数相同，原生和窗口图都应是 0 像素不同。
4. **爬动测量**（`d5e3d70`），没跑过。
   - `post_body` 的 `w3_dbg` 输出没编译过。
   - `_save_depth` 读视口浮点图（`use_hdr_2d`），格式是不是 RGBAH 没确认，日志里有 `DEPTH … format=`。
   - 用法：`--crawl=dir:x,z,h;...`，然后 `python3 tools/world3d/metrics/crawl.py <dir>/c00_… <D>`。D 在日志 `DEPTH … D=` 里。
5. **阴影**：透视下是一张 4096 的 `SHADOW_ORTHOGONAL`，覆盖视锥 0.5 m 到 D + 45。纹素密度和移动时阴影边的爬动都还没量。

## 4. 下一步

**第一段收尾**，做完报主管，先看静帧：

1. `bash scratchpad/bin/cam1chain.sh` 出四组预设 ×（院子晨、昏、夜，祠前，F1、F3），做对照页。
2. 正交和 9768ab2 的逐像素对照（见第 3 节第 3 条）。
3. 用 Xvfb + xdotool 在 showcase 里按 V 切四组，确认 HUD 和切换后的阴影、雾、挂件；按 CLAUDE.md，要走真实输入。
4. 先确认爬动测量能编译，再量四组 × 东、上各一步，按近景、焦点带、远景分别计数。

**第二段：景深 + B 键**（关 / 轻 / 强，默认轻）。设计草案：

- **为什么不用自带的。** Godot 自带的 CameraAttributesPractical 在所有东西画完以后对整张图做，没法按模板把人物和可交互物排除在外。所以计划在描边后处理（`post_body`）里自己做：1、2、5 类（实体、叶、地被）做按深度的散景采集；3 类（人物，`char_post`）和 4 类（目标）不虚。主管说过"先试自带的"，可以出一张自带景深的对照图说明为什么不用。
- **CoC**（单位：原生像素）= r_max × smoothstep(b, b + ramp, |d − D|)。
  - 轻：r_max 2，b 2.5 m，ramp 6 m；
  - 强：r_max 3.5，b 1.5 m，ramp 5 m。
  - 参数放进一个全局量 `w3_dof`（x = 0 表示关）。
- **采集**：整数偏移、圆盘内全取，强档 37 个点。
  - 近处的样本覆盖得到我时，按自己的 CoC 盖过来，前景的边是软的；
  - 同深度或更远的样本，按 min(我的 CoC, 它的 CoC) 计；
  - 盘的边缘权重用 clamp(r + 0.5 − 距离)，不要硬台阶；
  - 亮样本（亮度 > 0.9）加权，灯成小光斑，要克制。
- **虚化区里的线**：描边和折痕随 CoC 淡掉，否则虚的画面上会留一像素的硬线。
- **坑**：posts 读的 `screen_tex` 是描边和雾之前的图；粒子、光束、x-ray 在 posts 之后画，不会被虚。粒子可以按深度另外淡化。

**第三段**：每组 × 白天、黄昏、夜，用 xdotool 走家一圈；F1–F5 新旧对照；每组 × 每档景深的爬动数；knowledge/21 写透视的规则（本节和第 5 节的要点）。

## 5. 坑

1. **阴影距离。** 正交下 Godot 不理 `directional_shadow_max_distance`（knowledge/21 §6.2），透视下理。所以切换后必须调 `W3Env.fit_to_view()`，sample 的 `set_camera` 里已经调了。
2. **面向相机位置的卡片不能用。** 我最早让精灵面向相机的位置，结果在画面边上被剪成斜的：P2 偏 8 m 时约 17°。已改为 `w3_card`。只在世界正交格上取整的卡片，离开焦点平面就落在半像素上、按非整数缩放、会闪。
3. **直立物体在画面边上往外歪。** 竖线收向画面下方的天底，按各自的后倾算：P1 在画面边约 6°，P2 约 15–19°，P3 约 31°。精灵和草丛靠 `w3_card` 保持竖直，树和房子照真实透视歪。这是给用户比较三组时要说明的主要差别。
4. **GDScript 里手算后倾的地方**：`sample.gd _hung`（挂件及其点灯的变体）、`dressing.glints`、`dressing_life._place`（乌鸦、猫）、`walker.lean_k`（胸口点，管剖切孔的位置）、`atmosphere._above_view`。以后再加"手放在倾斜物体上的东西"，都要用 `pv.lean_k()`，并在 `_relean` 里登记。
5. **3D 人物的后倾。** `Character3D.set_view(ppm, pitch)` 的 `view_numbers.w` 仍是 tan(p/2)，没有乘预设的后倾份额。人物代理的文件我没动；3D 模型回来时要让它接收 lean，否则头部取整会和着色器对不上。
6. **合回主树之前**要先看主树后来有没有改 `sample.gd`、`pixel_toon`、`grass_field`、`atmosphere`、`walker`、`showcase_hud`。`grass_field` 是场景代理的文件，要告诉它。
7. **机器。** 一次只开一个 Godot。负载 10 左右时，一组 6 张全设置静帧约 15 分钟，单张从启动算约 4.5 分钟。

## 6. 不属于相机、但我这边还没做完的

- `scratchpad/sample3d/final5/progress.md` 的第 5–10 节还没写：
  - 树荫天光和光斑、道具用树冠图；
  - 眺望和遠化的交接；
  - Windows 外壳（手柄、`set_quality`）；
  - 音频；
  - 改动清单；
  - 问题。
- 写这几节的材料在 `coord/to_lead.md` 和 `final5/progress/` 里。
