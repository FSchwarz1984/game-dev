# 知识库索引

这里是项目的长期记忆：研究得到的原则、失败的教训、用户的参考。写设计、做美术、写代码之前，先读相关的一篇。

| 文件 | 内容 | 什么时候读 |
|---|---|---|
| [01-zelda-guidance-systemic.md](01-zelda-guidance-systemic.md) | 旷野之息/王国之泪：引力、三角形法则、化学引擎、A+B=AB、提示时机、测试方法 | 设计地图、引导、「移」的规则 |
| [02-readability-feel-controls.md](02-readability-feel-controls.md) | 读取层级、角色光照保护、植被、反馈与手感、目标选取、手机操作 | 做画面、交互、UI、手机适配 |
| [03-hd2d-web.md](03-hd2d-web.md) | HD-2D 的真实做法、被批评之处、three.js 实现、性能预算、素材管线 | 写渲染器、做场景和素材 |
| [04-verb-systems-genre-fusion.md](04-verb-systems-genre-fusion.md) | 单一动词系统的模式与坑、类型融合、小岛秀夫原话、差异化风险 | 设计系统、种田、战斗、经营 |
| [05-v0.1-postmortem.md](05-v0.1-postmortem.md) | v0.1 为什么得 0 分，以及值得保留的东西 | 任何时候；尤其在想"直接做"的时候 |
| [06-reference-board.md](06-reference-board.md) | 用户点名的参考作品和各自要学的东西 | 判断方向是否符合用户期待 |
| [07-audio-sources.md](07-audio-sources.md) | 环境声真实录音：来源、授权、处理方法、找不到 CC0 的声音与 CC BY 候选 | 加或换环境声之前；授权问题 |
| [08-2d-pixel-renderer.md](08-2d-pixel-renderer.md) | 2D 像素渲染管线的技术说明与教训（光照、遠化、角色保护、烘焙） | 改渲染器或环境美术之前 |
| [09-segment1-verification.md](09-segment1-verification.md) | 第一段交付前验证抓到的问题：浮层点击、淡入层盖字、测试时钟、3/4 遮挡、竖屏取消（P-3）、字体名 | 做 UI、演出，或写自动试玩之前 |
| [10-godot-toolchain.md](10-godot-toolchain.md) | Godot 4.7.2 工具链：官方编辑器与模板的下载校验（不自己编译）、Xvfb 软件渲染试玩（Forward+/Mobile/Compatibility 实测、真实输入、截图坑）、三渲染器的 2D 差异（辉光）、中日文断行（ICU 数据、严格禁则）、Windows/Android 导出与 APK 检查、每会话安装；W-1（Web）留档 | 装工具、导出、自动试玩、选渲染器之前 |
| [11-open-source-survey.md](11-open-source-survey.md) | 开源资源调研（F-2）：CC0 像素美术逐个评分并与我们的画面 ×3 对照（没有一套达标）；照片扫描材质当岩块形状来源的实验；Hugging Face 的像素化与生成模型（含 CPU 实测）；Godot 4 插件与着色器的许可、版本、取舍；自然地形的参考资料 | 找外部素材、插件或着色器之前；授权政策提案；立绘像素化（F-3） |
| [12-nagarenu-hina-mechanics.md](12-nagarenu-hina-mechanics.md) | 用户原型《流れぬ雛》的全部机制：她带着的性质如何改变她自己（移动、环境、危险、样子、声音），环境元素与四拍教学、恢复与失败、付丧神反应矩阵与头目、引导与 UI、世界结构；对照我们第一段缺什么（R-6） | 设计「移」的身体效果、环境谜题、小妖战斗之前 |
| [13-pixel-portraits.md](13-pixel-portraits.md) | 对话立绘像素化（F-3）：12 包立绘差分的选用，流水线与参数（调色板跟精灵图走），80×80 尺寸，立绘永远不挡字的版式规则，已知不足 | 改立绘或对话框之前；新增表情差分之前 |
| [14-vista-lights.md](14-vista-lights.md) | 远化之夜的升灯（R-8，用户已更正）：目标是 v0.2 开发版 `8196ebf` 的"星火聚向一点"，不是 v0.1，也不是第一段的"排成线"；运动模型、参照截图、验收方法 | 重做序章树顶远景的灯火之前 |
| [15-perspective-rules.md](15-perspective-rules.md) | 3/4 俯视的透视规则：平台加崖、台阶嵌进崖、路贴在平台上、建筑与树、水；交付前检查清单（R-1） | 做任何地形、道路、台阶、建筑、树的素材之前 |
| [16-godot-architecture.md](16-godot-architecture.md) | Godot 版的架构（P1 地基）：目录与自动加载、canvas_items + 自算整数倍填满窗口与像素锁定的平滑镜头、HDR 世界视口、触摸统一路由与两套操作方案、遮罩地面模型（平台、台阶、崖）、数据驱动的身体状态（草案/旧版两套规则）、角色状态机、await 导演与不挡字的对话框、测试与真实输入试玩一条命令、三平台导出、引擎的坑 | 改 `godot/` 里任何代码、加区域或素材、跑测试或试玩、导出之前 |
| [17-terrain-pipeline.md](17-terrain-pipeline.md) | 地形烘焙管线（`tools/terrain`）：矢量布局 → 斜投影像素地面；台阶嵌崖的几何、照片扫描切岩板、CIELAB 色阶（与 v0.1 的色度对照）、地平线贴图让影子连续、Godot 的光照分工、产物格式与核心怎么接、已知不足 | 改地形、做新区域、接地形光照或遮挡之前 |
| [18-vegetation.md](18-vegetation.md) | 植被生成器（`tools/flora`）与产物（`godot/art/flora`）：一条命令重建 64 株 17 类；自然空间建模 + 画面空间压缩、叶簇着色、分面法线；受光（屏幕空间左上略前）与投影（西北太阳、右下）分开；场景结构与 Y 排序、透视孔、整像素风动、随太阳高度连续变化的影子；核心怎么接（`FloraPlant`、`FloraField`）；验证方法、与 JS 和 CC0 的对照、已知不足 | 放置或新增植物、改树的画法、接光照/风/遮挡/阻挡之前 |

新增知识：一篇一个主题，写清来源和日期，未证实的标出来，然后在这张表里登记。
