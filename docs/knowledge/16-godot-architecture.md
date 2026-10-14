# 16 · Godot 版的架构（P1 地基）

日期：2026-10-14。适用：`godot/` 工程（Godot 4.7.2 官方版，Mobile 渲染器）。本篇说明代码放在哪、各层怎么接、怎么测、怎么导出，以及做的时候引擎在哪里跟设计"打架"。凡是标【未验证】的都没有实测。P1 只有内部测试区域，没有任何内容决定。

## 0. 一句话

纯逻辑（`systems/`）不碰节点，Node 无关、无头可测；画面一律在原生像素里画，舞台按整数倍放大；所有触摸先经过 `InputRouter`，界面层一律不吃输入；剧情是 await 式的导演，跑在游戏时钟上；待用户决定的东西（操作方案、字体、她的身体规则）全是开关，不写死。

## 1. 目录与自动加载

| 目录 | 内容 |
|---|---|
| `core/` | 自动加载（见下）、`proj.gd`（投影与朝向）、`pixel_stage.gd` + `pixel_camera.gd`（像素舞台与镜头）、`linear_to_srgb.gdshader` |
| `systems/` | 纯逻辑：`qualities.gd`（五性、拒绝原因、化学表）、`quality_holder.gd`、`ledger.gd`（账本）、`field.gd` + `field_entity.gd`（她、物体、动词、区域、目标选取）、`targeting.gd`、`mover.gd`（贴墙滑动）、`body_state.gd` + `body_rules.gd` + **`body_rules.tres`（她身体的全部数字）**、`companion.gd`（さぢ跟随）、`crew.gd`（百鬼队排队与搬运） |
| `world/` | `region_data.gd`（遮罩 → 可走、高度、材质）、`world.gd`（区域、Y 排序的物体与角色、导演的舞台接口）、`entity_view.gd`（占位画法）、`regions/test/`（内部测试区域） |
| `actors/` | `actor.gd`（AnimatedSprite2D + 显式动画状态机）、`character_library.gd`（从 `characters.json` 建帧，带法线）、`actor_sprite.gdshader`（身体状态的描边、霜、余烬、变暗） |
| `story/` | `director.gd`（导演）、`story_ui.gd`（打字机、字幕卡、标题、字幕、bark）、`dialogue_box.gd`、`cinema.gd`（遮幅与淡入淡出） |
| `ui/` | `hud.gd`（目标提示、性质键、身体小表、提示、触摸键）、`ui_theme.gd`（像素/矢量字体）、`minimap.gd`（只有接口） |
| `art/` | `fonts/`（两种字体 + OFL + `SOURCES.txt`）、`sprites/`（**占位**精灵图）、`portraits/<角色>/<表情>.png`（像素立绘，knowledge/13） |
| `audio/` | `default_bus_layout.tres`、`ambience/*.ogg`（环境声循环）、`spots/*.ogg`（鸟、鸦）、`SOURCES.json` |
| `tests/` | `run.gd`（无头测试运行器）、`test_case.gd`、`test_*.gd` |

自动加载（顺序有意义）：`Save` → `GameState` → `Audio` → `InputRouter` → `DebugBridge`。

- `GameState`：设置、旗标、当前会话（field、region、director）。命令行可临时覆盖设置（`-- --scheme=obvious --font=vector --body=legacy --touch-ui=on`），覆盖只在这一次运行有效、不存盘；游戏里（或开发键）改的设置才存盘。
- `Save`：`user://saves/<槽>.json`（`-- --save-root=<目录>` 可整体改到别处，试玩机器人用它隔离，绝不改动玩家自己的设置和存档），信封带 `format`；先写 `.tmp`，旧档留作 `.bak`；新版本的档拒读不误读；存储不可用时不崩溃，`available=false`、`last_error` 说明原因，本次会话的存档留在内存。
- `Audio`：总线 Music / Ambience / SFX / Voice；环境声交叉淡入；反馈音（取、予、放、拒绝、回流、点燃、脚步、说话音）暂用合成，保证 0.1 秒内必有声；`duck()` 在对话时压低音乐和环境声。
- `InputRouter`：见第 4 节。
- `DebugBridge`：只在 debug 构建、且命令行要求时启用，给试玩机器人写状态（第 9 节）。

## 2. 画面：原生像素、整数放大、填满窗口、平滑镜头

- **拉伸模式用 `canvas_items`，不用 `viewport`**（偏离了"stretch mode viewport"的字面要求，原因如下）。`viewport` 模式把整个窗口在原生分辨率里画完再放大，亚像素的镜头偏移根本无处表达；平滑镜头必须在放大之后再平移。参考实现 apples/godot-smooth-pixel-subviewport-container（MIT，knowledge/11）也是 `canvas_items`。整数倍 + `expand` 照旧。
- **填满窗口、不留黑边**：`PixelStage.fit()` 每次窗口变化时算 `s = floor(min(w/480, h/270))`，把 `content_scale_size` 设成 `(w/s, h/s)`。窗口越大看到的世界越多。1280×720 → 640×360×2；1200×540 → 600×270×2；1920×1080 → 480×270×4；2400×1080 → 600×270×4。奇数尺寸最多留 1 个窗口像素。
- **世界在自己的 SubViewport 里**（原生尺寸 + 四周各 1 像素）：像素对齐（snap transforms/vertices）、最近邻、**2D HDR + 辉光只在这里**（`own_world_3d`，WorldEnvironment 不会碰到 UI 和文字）。它的纹理是线性值，显示时经 `linear_to_srgb.gdshader` 转回 sRGB。实测：屏幕截图与源美术逐像素一致（平均差 0、最大差 0）。
- **镜头**（`PixelCamera`）：整数部分进世界画布，余数（按屏幕像素量化）平移放大后的画面。**跟随她时，只要她在动，镜头就锁在整像素上**：亚像素镜头配上按整像素走的精灵，会让精灵相对屏幕抖动（违反"角色上不做抖动"）。她站定后滞后量以亚像素平滑收回；演出镜头（`shot`/`cam`，带 `speed`：越小越像慢摇臂）全程亚像素。`apply_camera()` 由主循环在移动之后、HUD 投影之前调用，HUD 和世界用同一帧的镜头。
- **画布层**（下 → 上）：世界 < Cinema 5（遮幅、淡入淡出）< HUD 10 < Story 20（对话、字幕卡、标题、字幕）。**淡入淡出永远在文字下面**（knowledge/09 §1）；机器人在黑场上数过字幕卡的亮像素。
- 文字：UI 一律按原生像素排版。像素字体在 12 px 网格上不抗锯齿，放大后每个字体像素正好是 s×s 块（截图放大核对过）；矢量字体在屏幕分辨率上光栅化，任何倍数都清楚。这是 `canvas_items` 顺带的好处。

## 3. 坐标与投影

世界用米：x 向东，z 向南，h 向上。斜投影（knowledge/15）：屏幕 x = 20x，屏幕 y = 20(z − h)。站在地上的东西，节点位置取地面点 `(20x, 20z)` 做 Y 排序，画的时候抬高 20h。

## 4. 输入

- **所有触摸都在 `InputRouter._input` 里路由**，在任何 Control 之前；所有可见层 `mouse_filter = IGNORE`，触摸键只登记命中矩形。新触摸的归属顺序：对话截获（对话打开时任意一点都是"推进"）> 已登记的键（性质键、情境键）> 浮动摇杆（左半屏，仅触摸 UI 开启时）> 点世界（选目标）。这样不可能再出现"浮层吞掉触摸"（P-2 的事故）。
- 鼠标点击经 `emulate_touch_from_mouse` 变成触摸（`device == -1`）；鼠标事件本身不处理，避免一次点击处理两遍。真机触摸（device ≥ 0）出现过一次，`touch_ui=auto` 就打开触摸界面；安卓上默认打开。
- **两套操作方案都做了，由 `GameState.control_scheme` 切换**（待用户决定）：
  - `explicit`（默认，已批准的方案 A，D13）：1–5 取，Shift+1–5 予，L 再按数字是放；触屏点按取、上滑予、下滑放。
  - `obvious`（草案推荐的"按一下做显然的事"）：1–5 做显然的事（`Field.plan()`），Shift+1–5 反过来；触屏点按显然、长按（0.34 秒）反过来。
  - 默认取 A 的理由：它是已批准的决定；草案还没批。切换只是一个设置。
- 手柄（**暂定、未测**，容器里没有手柄）：左摇杆/十字键移动，A 情境，X 重 Y 熱 B 光 RB 音 LB 生，按住 LT = 反向/予，按住 RT = 放，R3 切换目标，Start 暂停。
- 安卓返回键不退出游戏（`quit_on_go_back=false`），发 `pause`。
- 触摸键按 dp 定尺寸：性质键 ≥ 48 dp、情境键 64 dp（用屏幕 dpi 和整数倍折算成原生像素，最小 28/40 原生像素），五个性质键排在情境键左上约 110° 的弧上，整组推进屏幕内。
- debug 构建的开发键：F6 操作方案、F7 字体、F8 身体规则、F9 触摸 UI、F10 演出检查场景。

## 5. 地面模型与移动

- 区域 = `world/regions/<id>/`：`region.json`（尺寸、格子大小、美术偏移、出生点、物体、区域、镜头位）+ `logic.png` + 美术图。`logic.png` 每像素一格（默认 0.25 米），RGB8：**R×256+G = 地面高度（厘米），B = 材质编号**（`RegionData.MATERIALS`：草、土、石、台阶、浅水、深水、崖……）。用 Godot 的 Image 导入器（无损）读入。
- 规则：一步之内高差 ≤ 0.3 米才能走，所以 0.5 米一级的平台边缘都是崖；台阶是唯一的上下通道，只沿南北走，两侧是墙（上下台阶必须在同一列、沿南北方向）；水和深水由她的身体决定能不能上（轻了能漂过去、冷了能冻着走过去）。
- `Mover.try_move` 是 `field.js tryMove` 的原样移植：碰到圆形物体沿切线滑，碰到墙沿空着的轴滑，斜岸试附近的方向。所以推着墙走会沿墙滑——在台阶上横推会顺着台阶滑上滑下，从台阶头或台阶脚出去，不会翻过侧墙（测试逐帧检查）。
- 测试区域（`tools/godot/make_test_region.py` 生成，**只供内部检查，永不交付**）：0 / 0.5 / 1.0 / 1.5 米四层平台、两段嵌进崖里的台阶、贯穿各层的土路、浅水深水的池塘、一块有风的地方，以及石、梁、旧背负子、石灯笼、注连石、道标和さぢ。

## 6. 「移」与她的身体

- `Ledger`：`total(k) = Σ持有 + air − sourced` 恒定；取、予、放各移动一份，拒绝必带原因（sacred / empty / full / overload / none / far）。
- `Field`：JS 版的完整移植（物体、遠化 `farness`、深远之物推不到也碰不到、区域的进出与挡路台词、目标选取的宽窄锥、情境键、祠前归还），加上：地面高度、地面种类、风区、`check()`（某动词此刻会怎样）、`plan()`（方案 B 的"显然的事"）、`pick()`（点选目标时转身面向它）。
- **她的身体是数据驱动的状态**（`BodyState` + `systems/body_rules.tres`）。每种性质按"本性"分档：0 交出自身、1 本性、2 多带、3 多带两份（继承 2 再覆盖）。每档一组效果，同时作用于移动（速度、加速度、悬浮）、环境（风系数、漂浮、冻水、下沉……）、风险（自燃计时、受伤倍率、完好度）、样子（描边、霜、余烬、变暗且有亮度下限、压扁、发光、脚下色环、声环）、声音（脚步音量、音高、额外的闷响或鼓声）。合并规则写在 `BodyRules.MERGE`。
- 两套规则（`GameState.body_profile`）：`draft` = 草案（**待批准**；本性各 1、容量 1、9 秒回流，之后每 3 秒一份；任何东西每种性质最多比本性多 2）；`legacy` = JS 第一段（本性 重2 熱1 光0 音1 生3、容量 3、无回流、重了 0.7、轻了 1.2 且能过水）。
- **自身份额回流**：默认从账本的 air 取回（air 允许为负，总数严格守恒，按主控的要求）；`regen_from: "source"` 是草案最新的写法（"守恒的唯一例外"，记进 `sourced`，账面仍平）。两种都测过。
- 已经接上的身体效果：速度、漂移加速度、悬浮（影子留在地上）、风区、过水/冻水、自燃 → 掉完好度 → 入水熄灭、受伤倍率与回复的数据、精灵图通道、脚步声。**还没做的**（P4）：深水下沉、蒸汽、冰面持续、踏板、朽桥、点燃草地、小妖的视觉与听觉——数据已在 `body_rules.tres` 里，等环境元素来读。

## 7. 角色

- `Actor`：AnimatedSprite2D + **显式状态机**：LOCOMOTION（每帧按"在走 / 重 / 站"选动画）、SCRIPTED（导演让她走，`idle()` 结束）、ONE_SHOT（播一次，停最后一帧 0.25 秒，自己回去）、HOLD（循环一段时间自己回去）、POSE（保持，直到 `release()`）。导演最后一个场景结束时对所有用过的角色调用 `end_scene()`，场景留下什么都会被收回。她自己的取、予手势一走路就让位。这是 R-4"脚本动作后精灵没切回来"的修法，有单元测试，也在机器人跑的 F10 场景里核对过。
- 帧来自 `actors/characters.json`（由 `src/art/characters.data.js` 转来）；每帧是 CanvasTexture（反照率 + 法线）上的 AtlasTexture。**现在的精灵图是占位**，新的到了只要换 JSON 和图。
- `set_body_look(look)`：身体状态在她身上的接口（着色器参数、悬浮、压扁、点光源、脚下色环、声环）。
- さぢ：`Companion`（JS `followStep` 的移植）：在她身旁偏后、永远在她脚的北侧一步，不挡在镜头和她之间；侧位到不了时沿她走过的路走（≥1.5 米，正南也不压住她的身体）；太远时跳回路上。`Crew`：百鬼队排队与搬运的完整移植（含 4 个原测试）。

## 8. 剧情与界面

- `Director`（`cine.js` 的移植，await 式）：`wait`、`until`、`tween`、`timelapse`、`move`、`face`、`play`、`say`、`card`、`title`、`sub`、`fade`、`letterbox`、`shot` / `cam` / `follow`（带 `speed`、`cut`）、`tod`、`music`、`sfx`。所有等待都挂在游戏时钟上，`tick(dt)` 时在帧内恢复，测试和真游戏一样一帧一帧走（knowledge/09 §2）。
- 对话框按 knowledge/13 §5 的版式：框 468×64，居中贴底；80×80 立绘在 84×84 的卡片里立在框左端（高出 24 像素）；正文从卡片右边 +8 开始；名牌压在框上沿、宽度随名字、永远一行；旁白没有立绘、正文占满整宽。机器人每一行都核对"卡片右边 ≤ 正文左边"。打字机：每秒 30 字（慢速 14），逗号停 0.09 秒、句号停 0.22 秒，隔字一声说话音；按 E / 回车 / 空格 / A 或点屏幕推进，第一下补全、第二下翻页，按住加速。
- 字体（`UiTheme`，`GameState.font_theme` 切换，待用户决定）：`pixel` = Fusion Pixel 12px Proportional（zh_hans 字形，OFL）；`vector` = Noto Serif CJK SC 子集（OFL）。来源、版本、许可写在 `art/fonts/SOURCES.txt`，OFL 原文在旁边。
- HUD：目标提示挂在目标上（名字、遠、性质点、情境键的动作、拒绝原因），快要盖住她时抬到她头顶上方（顶上没地方就放到脚下）；性质键写着此刻按下去会做什么（取 / 予 / 放，或拒绝的简写：满、无、远、×）；身体只在角落里有一个小表，自身份额回流时那一格从下往上填满；提示 `tip()` 必须挂在东西上，没有挂点的直接拒绝——**画面中间永远不出现指路或任务标记（F-1）**；小地图只有接口（`Minimap`：登记区域、解锁、存档），解锁条件待定。

## 9. 测试与试玩（一条命令）

```sh
bash tools/godot/test.sh            # 单元测试（无头）：61 个，含 JS 测试的移植
bash tools/godot/playtest.sh [out]  # 单元测试 + 两轮真实输入试玩（1280×720 键盘；1200×540 触摸）
```

- 测试运行器 `tests/run.gd`：`godot --headless --path godot -s res://tests/run.gd [-- --only=名字]`。GDScript 没有异常，所以注册了一个 `Logger`：测试期间引擎或脚本打出的任何错误都会让该测试失败。运行器先安排退出，再做清理，不会挂住；600 秒总超时。
- 移植了 JS 的 qualities（6）、targeting（5）、field-logic（10，含导演）、crew（4）。没移植的：`seg1-flow`（第一段的内容流程，P5 重写剧本后重做）、`field` / `sim` / `nav` / `build-farm`（停用的灰盒和不在本次范围的模块）。新增：地面模型、台阶侧墙、她的身体、回流两种记账、上限、操作方案 B、角色状态机、镜头、さぢ跟随、存档。
- 试玩机器人 `tools/godot/smoke_bot.py`：Xvfb 开真窗口（Mesa 软件 Vulkan，Mobile 渲染器），xdotool 走 XTEST 发真实按键、鼠标（=触摸）。游戏只**报告**状态（`--bot-state` 每两帧原子写一次 JSON：她、目标、物体的窗口坐标、触摸键矩形、对话、账本、声音、角色状态），机器人像玩家一样"看"坐标再按，结果从状态里核对。它不调用任何游戏函数。截图两种：X 屏幕截图（玩家看到的），以及经 `--bot-cmd` 的引擎截图（根视口不是 HDR，不需要转换；若以后根视口开 HDR，`DebugBridge` 会逐像素转 sRGB，见 knowledge/10 §3.3）。
- 每轮都用 `--save-root` 把存档放进输出目录，开始前清空。
- 键盘一轮：走过三层平台、两段台阶（高度 0 → 0.5 → 1.5 米），确认 1.0 米的崖挡住她；面向石灯笼选中，1 取「重」（她变重、变慢、有声音，再取被拒且说明原因），下台阶到旧背负子，Shift+1 予（背负子变近，账本守恒）；E 打开道标的旁白、E 推进；和さぢ对话三行，每行核对立绘不挡字；F10 演出场景（黑场上的字幕卡、白场上的标题，场景后所有角色回到 LOCOMOTION）；F7 换矢量字体看对话。
- 触摸一轮（触摸 UI 开）：浮动摇杆走同样的路线，点选石灯笼，点「重」键取，上滑予，点情境键开对话，点屏幕推进；切到方案 B 后长按「重」交出自身（她悬浮），等它约 9 秒后自己回来。
- 导出的 Linux debug 包也用 `--binary` 跑过同一轮键盘试玩。

## 10. 导出

```sh
bash tools/godot/export-game.sh [out] [release|debug]   # Windows、Android、Linux，最后检查 APK
```

预设在 `godot/export_presets.cfg`：Linux（x86_64，exe + pck）、Windows（x86_64，exe + pck，改写版本信息）、Android（只 arm64-v8a，不用 Gradle，沉浸式，签名用 `tools/godot/android/debug.keystore`）。`include_filter` 带上 `*.json` 和字体许可文本，`tests/` 不进包。

## 11. 素材同步脚本（都在 `tools/godot/`）

| 脚本 | 作用 |
|---|---|
| `fetch_fonts.py <工作目录>` | 从 Fontsource 的 npm 包取 Fusion Pixel（GitHub release 在容器里被拦），从 noto-cjk 稀疏克隆取 Noto Serif SC 并子集化 |
| `build_audio.py` | 把 `assets/audio` 的 CC0 / 公有领域录音转成精确长度的 OGG 循环（MP3 的编码延迟会让接缝错位）和单发叫声，并写 `SOURCES.json` |
| `sync_assets.py` | 复制精灵图、转 `characters.json`、复制像素立绘（没有时才做粗糙占位）、生成占位图标 |
| `make_test_region.py` | 生成内部测试区域的遮罩、粗糙美术与 `region.json` |

## 12. 引擎跟设计"打架"的地方（踩过的坑）

1. **`viewport` 拉伸做不了平滑镜头**：见第 2 节，改用 `canvas_items` + 自己算整数倍和画布尺寸。内置的"整数倍 + expand"在 1280×720 下会留黑边（knowledge/10 §6），所以画布尺寸要自己跟着窗口改。
2. **HDR 的 SubViewport 纹理是线性的**：直接显示会偏暗，显示时要转 sRGB；辉光要放在世界视口自己的 World3D 里，否则会作用到文字。
3. **着色器里不能把 `TEXTURE` 当参数传给函数**（`custom_samplers` 报错），只能就地采样。
4. **GDScript 的 lambda 按值捕获局部变量**：在 lambda 里改计数器不会留到下一次调用，要放进字典或数组。
5. **协程调用规则**：协程作为语句调用只是警告（忘了 await 时照样跑到第一个 await 就返回）；把返回值拿来用却不 await 是编译错误。`await callable.call()` 可以等到协程结束。
6. **测试里打出的引擎错误不会让测试失败**：GDScript 没有异常，要用 4.5+ 的 `Logger`（`OS.add_logger`）收集。预期的失败路径要避免打错误：`JSON.parse_string` 失败会打错误，用 `JSON.new().parse()`；`make_dir_recursive_absolute` 失败会打错误，先检查路径上有没有同名文件。
7. **`-s` 模式会加载自动加载，但运行器脚本在它们注册之前编译**：运行器直接引用的类里如果写了自动加载的名字，会编译失败，然后运行器挂住不退出。所以 `UiTheme` 不依赖 `GameState`，运行器按路径加载、先安排退出再清理。
8. 安卓的返回键默认直接退出游戏（`quit_on_go_back`），已关掉。

## 13. 桩、没做的和没验证的

- 桩：小地图（只有接口）、暂停菜单、存档内容（系统有，游戏还不存进度）、音乐（等 P5 把 JS 合成音离线渲染成 OGG）、世界流式加载（只按 id 加载一个区域）、闪避 / 派遣 / 召回（只发动作）、时间（`tod` 只是画布调色）。
- 没验证：手柄（没有设备）；Windows 包只导出没运行（容器里没装 wine；knowledge/10 说 wine 下要关 dinput8）；APK 没在真机上跑（没有 KVM），触摸、dpi 换算、横屏、沉浸、存档路径、音频延迟都要真机看；软件渲染的帧率（30–42）不代表手机；声音只确认了"播放了"（状态里有记录），没有人耳听过（容器没有声卡）。
- 美术全是占位：测试区域、物体画法、精灵图（新精灵图由别的代理做）。性质效果在她身上的样子只是接口和最小表现，强度要在 P4 和美术一起调。


## 13. 整数倍的取法（主管决定，2026-10-14）

- 原先：`s = floor(min(w/480, h/270))`。1280×720 时 s = 2、画布 640×360，世界和文字都比用户在 JS 版里认可的取景（427×240，×3）小三分之一；远景代理也指出，升灯的"倒漏斗"在这个尺寸下只占屏幕的三分之二。
- 现在：`s = round(h/270)`，画布宽小于 400 时再减一，画布 = 窗口 / s。原生高度在各种屏幕上都靠近 270（240–300）：1280×720 → 426×240，1366×768 → 455×256，1920×1080 → 480×270，2560×1440 → 512×288，1200×540 → 600×270，1600×720 → 533×240，2400×1080 → 600×270。
- 对话框宽度随画布：`min(468, 画布宽 − 12)`；426 宽时正文一栏约 26 个字。
- 验证：`bash tools/godot/playtest.sh` 两项都过（1280×720 键盘 → 426×240 ×3；1200×540 触屏 → 600×270 ×2），对话框截图里立绘不挡字。
