# 11 · 开源资源调研：CC0 美术、像素化与生成模型、Godot 4 插件与着色器、自然地形的画法（2026-10-14）

起因是 F-2（用户："多多参考一下 GitHub 或者 Hugging Face 上面的一些美术资源，比如说植被、地形地图之类的开源的东西去提升优化"）。这篇是调研结果，**不是已批准的决定**；授权政策仍在 `pending.md` 里待提案。

前提：
- **授权**：A-2 选了不在游戏里加第三方署名。所以美术和音频只能直接用 **CC0 或公有领域**；CC BY、BY-SA、NC 和各种自定义许可只能当参考。代码（插件、着色器）可以用 MIT、BSD、Apache-2.0、Unlicense、CC0。MIT、BSD、Apache 要求随游戏附上版权与许可声明，这放在随包的第三方许可文件里，不算游戏内署名。Godot 本身（MIT）和它内置的第三方库本来就要附这个文件。
- **平台**（W-1、W-2）：Windows 用 Forward+，安卓用 Mobile，不再导出网页版。网页导出的体积不再是拒绝插件的理由；只有 Forward+ 能用的东西单独标"仅 Windows"。
- **引擎**（E-1）：容器里的源码是 `godot 4.7.2-stable`（`/home/user/godotengine/godot`），由我们自己编译，所以可以把模块直接编进引擎。

方法：OGA 高级搜索（CC0 + 2D Art，按收藏排序，约 40 个关键词）；itch.io 的 `assets-cc0` 标签页；Kenney；GitHub（搜仓库，用稀疏克隆读 LICENSE 和 plugin.cfg）；Godot 资源库 API；Hugging Face API（模型、数据集、Space）。所有许可都按页面原文或仓库 LICENSE 核对过，日期 2026-10-14。标记：【观察】= 看成品画面得出的判断，没有官方资料；【推断】= 没有实测；【未核实】= 只看到二手说法。

---

## 0. 结论

1. **能直接用的 CC0 像素美术：没有一套达到风来之国的水准，也没有一套和我们的比例、调色、光照对得上。** 在同一像素密度（×3）下并排看（§1.3），CC0 瓦片集普遍高饱和、粗描边、平涂、按格子拼边，这些正是 A-1、R-1 批评的问题。唯一接近的是 pistachio 的 CC0 针叶树：暗绿、低饱和、枝层下垂，高 175–246 px，按 1 米 = 20 px 算是 9–12 米。它可以做中远景的杉、桧，也可以作为我们杉树生成器的造型参考。即使直接用，也要补法线、重新映射调色。
2. **CC0 资源里最有价值的是结构数据，不是成品像素图。** Poly Haven、ambientCG 的照片扫描材质都是 CC0，带高度图和法线。直接缩小只会得到噪点。我做了一个实验：按高度图用分水岭算法分出一块块石头，每块平涂、左上倒角、块与块之间留暗缝，结果读起来就是像素画的崖面和石垣（§1.4）。值得作为我们环境生成器的输入继续试。
3. **Hugging Face：没有能当成品美术用的 CC0 数据集，也没有这样的模型。**
   - **立绘像素化（F-3）**：PixelOE（Apache-2.0）在本机 CPU 上 1–2 秒一张，作为第一步可用，之后仍要按规则清理，再人工修眼睛和线条（§2.2）。
   - **文生图**：本机（4 核 CPU，无 GPU）只跑得动 SD1.5 级别。实测 512² 每张约 65 秒，产出是侧视、高饱和的"伪像素图"，离目标很远（§2.3）。更新的像素 LoRA 底模是 Apache-2.0，许可没问题，但都要 GPU。即使有 GPU，也只适合出概念参考。
4. **Godot 方面建议直接采用的**：
   - Dialogue Manager 4（MIT），只用它的脚本格式和运行时，对话框界面自己做；
   - GdUnit4（MIT），能模拟键盘、鼠标、触摸，符合"真实输入路径"的验证规则；
   - LimboAI（MIT），作为模块编进引擎，管小妖的行为；
   - 一批 CC0 / MIT 着色器：风摆、x-ray 透视孔、亚像素平滑、水面。

   **不解决核心问题的**：SmartShape2D、TileMapDual、Better Terrain。我们的核心问题是像素级的有机边缘和统一的 3/4 透视，这三个只在局部环节有用：编辑器里画形状、运行时可修改的农田和踩出的路。

   **必须自己做的**：太阳阴影与延迟光照合成、遠化、角色光照保护、倒影、地形烘焙。原因之一是 Godot 内置的 2D 阴影是"平面内"遮挡，适合夜里灯笼被墙挡住，不适合 3/4 视角下的太阳（§3.1）。
5. **自然地形的问题出在规则，不出在素材。** R-1 说台阶、道路、崖面"和画面的透视根本就不一样"。按我们的投影（屏幕 = (X, Y − Z)，地面平面和竖直面都是 1:1），台阶、路、崖各有固定画法，以 [15-perspective-rules.md](15-perspective-rules.md) 为准。本篇 §4 只补充外部参考：分层、去网格感、光照。

---

## 1. CC0 / 公有领域像素美术

### 1.1 比例先说清楚

我们是 1 米 = 20 px，角色 34–40 px 高。16 px 的包按 1 格 ≈ 1 米算，是 16 px/m，单看换算和我们差不多，但它们的人物只有 16–24 px（Q 版）。树、房子、台阶都是按这个人物画的：放进我们的画面里，每样东西相对角色都小一号，细节密度也低得多。32 px 的包（LPC 体系）人物约 44–48 px，比例接近我们，但 CC0 的 32 px 包很少，风格也不对。

把 16 px 的包放大也不行：
- 放大 2 倍是整数倍，宪章允许，但放大后每个像素是我们的两倍大，和周围的原生像素混在一起就是混像素；
- 按 1.25 倍去凑比例，是宪章禁止的小数倍缩放。

### 1.2 候选表

契合度 1–5 分，以风来之国为 5 分：同一 3/4 视角、左上光、有机边缘、低饱和自然色、手绘材质。

| 资源（作者） | 链接 | 许可（页面原文） | 尺度 | 透视 | 契合 | 结论 |
|---|---|---|---|---|---|---|
| Pixel Pine Tree Assets (10 Pack)（pistachio） | https://opengameart.org/content/pixel-pine-tree-assets-10-pack | "License(s): CC0" | 树高 175–246 px；8 色 + 透明 | 侧视剪影（作者说"为等距优化"，树不受影响） | **3** | 暗绿、层叠下垂枝，接近杉、桧、冷杉；有 3 棵枯松。叶簇偏碎，光向不明确，没有法线。**可直接用作中远景针叶树**（我们补法线、重映射色阶），也可做杉树生成器的轮廓参考 |
| Trees & Bushes（ansimuz） | https://opengameart.org/content/trees-bushes | "License(s): CC0" | 树冠约 70 px | 3/4 顶视 | 2.5 | 暗部厚实，块面分组清楚，但偏饱和。参考：阔叶树冠的分组 |
| Tiny RPG Adventure / Forest（ansimuz，itch） | https://ansimuz.itch.io/tiny-rpg-forest | 元数据 "Creative Commons Zero v1.0 Universal" | 16 px | 3/4 | 2.5 | 棕褐、秋色，用色比多数包克制；网格感明显。参考：克制的土色 |
| TinyRpg Stranger Forest Pack（ansimuz，itch） | https://ansimuz.itch.io/tinyrpg-stranger-forest-pack | 元数据 CC0；"LICENSE FOR THE FREE ASSETS You may use these assets in personal or commercial projects." | 16 px（宣传图约 4.5 倍、非整数放大） | 3/4 | 2 | 薄荷绿、蓝色调的松和小木屋。参考：松枝的层次 |
| [Free Sample] 16x16 Pixel Forest Tileset（inkBubi） | https://opengameart.org/content/free-sample-16x16-pixel-forest-tileset-%E2%80%93-top-down-rpg-style | "License(s): CC0" | 16 px，附 Godot 4.4 TileSet | 3/4 | 2 | 路和水岸的边缘比一般包有机。参考：边缘变体怎么排 |
| RPG Nature Tileset – Seasons（Stealthix，itch） | https://stealthix.itch.io/rpg-nature-tileset | 元数据 CC0；"Attribution is appreciated but not required!" | 32×32 | 3/4 | 2 | 卡通描边、饱和。参考：32 px 尺度下草和路的过渡 |
| Mage City Arcanos（Hyptosis） | https://opengameart.org/content/mage-city-arcanos | "License(s): CC0"；"These are public domain, you don't have to give me credit" | 32 px（RPG Maker XP 体系） | 3/4 | 2 | 石板路纹理密、用色低饱和，但是标准的格子城镇。参考：石材纹理的密度 |
| Ninja Adventure（pixel-boy，itch + GitHub 的 Godot 4 工程） | https://pixel-boy.itch.io/ninja-adventure-asset-pack ・ https://github.com/pixel-boy/NinjaAdventure | 元数据 CC0；"They are released under the Creative Commons Zero (CC0) license… Attribution is not required but appreciated." | 16 px | 3/4 | 1.5 | 内容是日式（村屋、武士、忍者），画风高饱和、粗描边、Q 版。参考：日式村落元素清单。不直接用 |
| Zelda-like tilesets and sprites（ArMM1998） | https://opengameart.org/content/zelda-like-tilesets-and-sprites | "License(s): CC0" | 16 px | 3/4 | 1.5 | 典型 ALttP 结构，只作结构参考 |
| The Field of the Floating Islands（Buch） | https://opengameart.org/content/the-field-of-the-floating-islands | "License(s): CC0" | 16 px | 3/4 | 1.5 | 同上 |
| Tiny Zelder Clone Topdown Pack（wareya） | https://opengameart.org/content/tiny-zelder-clone-topdown-pack | "License(s): CC0"；"Can be used for anything without permission or credit or restriction." | 16 px，Godot 3×3 autotile 布局 | 3/4 | 1 | 参考：崖的 autotile 布局 |
| 16x16 Puny World（Shade） | https://opengameart.org/content/16x16-puny-world-tileset | "License(s): CC0" | 16 px 大地图 | 俯视 | 1 | 不适用 |
| isaiah658's Pixel Pack #1 / #2 | https://opengameart.org/content/isaiah658s-pixel-pack-1 | "License(s): CC0" | 16 px | 3/4 | 1.5 | 高饱和、现代题材 |
| Oriental Roof Tiles（Clint Bellanger） | https://opengameart.org/content/oriental-roof-tiles | "License(s): CC0" | 约 32 px 基准 | 侧立面 | 2.5 | 本瓦的筒瓦行、屋脊、檐口。**参考：我们小屋的屋顶缺的正是这些**（§1.3 图三：我们的屋顶是一块灰色平涂） |
| Japanese buildings – isometric（Jetrel）及 remix | https://opengameart.org/content/japanese-buildings-isometric-strategy-game-mockup | "License(s): CC0" | 小尺寸 | 等距 | 2 | 透视不同。参考：入母屋屋顶的形体 |
| Meditator statues 32x32（Buch）・Buddha statues 16x16（MoikMellah） | https://opengameart.org/content/meditator-statues-32x32 | "License(s): CC0" | 32 / 16 px | 正面 | 1.5 | 参考：地藏、石佛的块面 |
| Flowers（SpiderDave） | https://opengameart.org/content/flowers | "License(s): CC0" | 12×24 小植物，DB32 色板 | 侧视 | 2 | 参考：野草、蕈、藤的小造型；色板要重映射 |
| Farming crops 16x16（josehzz） | https://opengameart.org/content/farming-crops-16x16 | "License(s): CC0" | 16 px，20 种作物各 5 个生长阶段（含稻） | 侧视 | 1.5 | 参考：作物分阶段（稻） |
| [LPC] bamboo, cave rocks…（tapatilorenzo） | https://opengameart.org/content/lpc-bamboo-cave-rocks-misc-objects | "License(s): CC0"（这一条是 CC0，LPC 主体不是） | 32 px | 3/4 | 1.5 | 粗糙 |
| Kenney（Tiny Town、Roguelike/RPG、Foliage Pack 等） | https://kenney.nl/ ・ https://opengameart.org/content/foliage-pack-100x | CC0 | 16 px 或矢量 | 多种 | 1 | 平涂、没有材质。只适合原型 |
| FREE Pixel Art Tree Pack（karsiori，itch） | https://karsiori.itch.io/free-pixel-art-tree-pack | "License info: CC0, you can use this asset pack however you want…" | 小树 | 侧视（平台游戏） | 1.5 | 泡泡状树冠，不适合 |
| Pixel Trees Megapack（Blacis，itch） | https://blacis.itch.io/pixeltrees | "License: CC0"；页面标签含 "AI Generated" | 小 | 侧视 | 1 | 质量低，来源是 AI 生成 |
| OPP2017（Open Pixel Project） | https://opengameart.org/content/opp2017-jungle-and-temple-set | 多重许可，含 CC0："they are in the public domain!" | 32 px，DB32 色板 | 侧视（平台） | 1 | 透视不适用 |
| Japanese style simple backgrounds（Oyasumi） | https://opengameart.org/content/japanese-style-simple-backgrounds | "License(s): CC0" | 1920×1080 | — | 0 | 矢量风格，不是像素 |

**只能参考（不是 CC0）**：

| 资源 | 许可原文 | 为什么值得看 |
|---|---|---|
| Pixel Art Top Down – Basic（Cainos） https://cainos.itch.io/pixel-art-top-down-basic | "This asset pack can be used in both free and commercial projects. Credit is not needed but appreciated."（自定义许可） | 32 px 的 3/4 标准构造：台地顶面 + 朝南立面 + 切入立面的台阶，透视始终一致。它恰好是我们要避免的"方块台阶"，但透视的一致性值得学 |
| Tiny Swords（Pixel Frog） https://pixelfrog-assets.itch.io/tiny-swords | "Feel free to use this asset pack in both personal and commercial projects… Crediting is not required"（自定义） | 高台边缘的有机处理：草沿鼓包、崖脚不齐 |
| Mystic Woods（Game Endeavor） | 免费版："You can only use these assets in non-commercial projects." | 16 px，可读性好 |
| Serene Village（LimeZu） | CC BY 4.0 | 16 px 村落 |
| LPC 全系 | CC-BY-SA 3.0 / GPL 3（逐条不同） | 32 px 3/4 体系最完整的风格指南（§4.5） |

Cainos 和 Tiny Swords 都"不需要署名"，和 A-2 不冲突，但它们不是 CC0，通常也不允许把素材本身再分发。如果用户在授权政策里放宽到"免署名的自定义许可"，能多出这两套素材。不过它们离风来之国也很远，价值主要在参考，**我不建议为了它们放宽政策**。

### 1.3 对照图（×3，与 JS 版第一段截图同一像素密度）

我们的截图是 1280×720，渲染器在这个尺寸下取 ×3（`src/gfx/renderer.js`：缩放倍数 = round(√(W·H / (480·270)))），所以素材按原生像素裁出来再放大 3 倍，就和截图是同一密度。图在会话 scratchpad，没有入库；路径前缀 `/tmp/claude-0/-home-user-game-dev/a1b4dbc5-91a8-5ca9-9938-d964a8e56360/scratchpad/previews/`：

| 文件 | 内容 |
|---|---|
| `sheet1_terrain_x3.png` | 地形和瓦片：我们的九十九折（石阶、崖、路）对照 10 套 CC0 瓦片 |
| `sheet2_vegetation_x3.png` | 植被：我们的大楠根部和杉，对照 CC0 的针叶树、阔叶树、草花、作物 |
| `sheet3_props_x3.png` | 日式物件：我们的地藏石和小屋，对照 CC0 的村屋、屋顶瓦、石佛、墓石、木塔 |
| `sheet4_photoscan_material_x3.png` | §1.4 的照片扫描材质实验 |
| `overview1.png`–`overview3.png` | 候选包原图总览（未按比例） |
| `ref_noncc0_structure.png` | Cainos、Tiny Swords 的宣传图（**非 CC0，不要入库**） |

sheet1–4 里只有 CC0 素材和我们自己的截图。其中取自 itch.io 的几格（Ninja Adventure、ansimuz、Stealthix、karsiori）是作者的宣传截图：画面内容是 CC0 素材，但截图本身没有单独声明许可。稳妥起见，如果要入库，先把这几格换成素材原图。

复现用的脚本在同一 scratchpad 的 `scripts/` 下（未入库）：
- `contact.py` 和 `contact_spec*.json`：出对照图；
- `upscale_factor.py`：测宣传图的放大倍数；
- `phpix.py`：§1.4 逐像素版；
- `phseg.py`：§1.4 分水岭版；
- `pixtest.py`：§2.2 立绘像素化；
- `sdtest.py` 和 `sdclean.py`：§2.3。

Python 环境是 `venv/`，装了 CPU 版 torch、pixeloe 0.0.10、scikit-image。

看图得出的结论：
- 我们的画面在细节密度和氛围上已经明显超过所有 CC0 瓦片集。我们的问题在结构：石阶是一条直带，崖顶是一条长直线，阴影边缘硬。换素材解决不了这些。
- 在同一像素密度下，16 px 包的边缘都落在 16 px 网格上，地块读起来就是方块。这正是 A-1 否掉的东西。
- 植被里只有 pistachio 的针叶树在调色和尺度上能放进我们的画面。
- 我们的小屋屋顶明显弱于 Bellanger 那块 2005 年的屋顶瓦：没有瓦垄、屋脊和檐下阴影。这是 R-3 之外另一个该修的地方。

### 1.4 照片扫描材质（CC0）当结构输入：实验

**来源与许可**：
- Poly Haven，https://polyhaven.com/license ："Our assets are all licensed as CC0, which is effectively Public Domain even in jurisdictions that do not support the Public Domain."
- ambientCG，https://ambientcg.com/license ："All ambientCG assets are provided under the Creative Commons CC0 1.0 Universal License."

两家的材质都带真实尺寸、高度图、法线、AO。

**做法**：
- 用了 `japanese_stone_wall`（1.9 m）、`cliff_side`（1.83 m）、`mossy_rock`（3 m）三张 1k 贴图，按 1 米 = 20 px 缩小，一个重复单元只有 37–60 px。
- 第一种做法：逐像素用法线做左上光照，再映射到 6 档色阶。
- 第二种做法：把高度图在 2 倍原生分辨率下做分水岭分割，得到一块块"石头"；每块按它的平均明度取一档底色，左上一圈亮一档，右下一圈暗一档，块间是暗缝，带绿的石块上半部染苔色。

**结果**（`sheet4_photoscan_material_x3.png`）：
- 逐像素版是噪点和迷彩，正是 knowledge/08 §2.2 里"草地是噪声，不是草"的同一个坑。
- 分水岭版像像素画：`cliff_side` 读作层叠的岩板，适合崖面；`japanese_stone_wall` 的源图本身是切石，行太整齐，出来像砖墙，不适合做野面积み。
- 两种都能看出 37 px 的重复。实用时要拿更大范围的源图（2k、4k），或者多张源图随机错位。

**判断**：值得在环境生成器里接着做，用法是把照片扫描当作"石块形状的来源"。块面、倒角、色阶、光照仍然由我们的管线决定，产出的像素图是我们自己的，许可上没有约束。不要把照片直接缩小来用。

---

## 2. Hugging Face：像素生成、像素化模型与数据集

### 2.1 现状（API 查询，按下载量）

| 模型 / 工具 | 许可 | 底模与规模 | 硬件 | 本机（4 核、15 GB、无 GPU） | 评价 |
|---|---|---|---|---|---|
| PixelOE（KohakuBlueleaf/PixelOE，GitHub，PyPI `pixeloe`） | Apache-2.0 | 不是神经网络：对比度感知的轮廓扩张 + 降采样 | CPU | **可行**：0.9–1.7 秒/张（§2.2）。0.0.x 版本也会导入 torch，需要装 CPU 版 torch | 立绘像素化（F-3）的第一步 |
| Pixelization（WuZongWei6，HF 上有多份权重镜像） | "For non-commercial scientific research purposes… Any commercial use of the Dataset and Code is strictly prohibited." | GAN | GPU 或 CPU | — | **排除**（只许非商业） |
| proper-pixel-art（KennethJAllen） ・ unfake.js（jenissimo） | MIT ・ MIT | 规则算法 | CPU | 可行（未跑） | 把 AI 产出的"伪像素图"还原到真实网格；只在用生成模型时需要 |
| nerijs/pixel-art-xl | CreativeML OpenRAIL-M | SDXL LoRA | GPU ≥ 8 GB【推断】 | 不现实（SDXL 在 CPU 上每张以十分钟计）【推断】 | 最常用的像素 LoRA，产出是伪像素 |
| artificialguybr/PixelArtRedmond（SD1.5 版） | 自定义（civitai 式："allowCommercialUse=Rent"，卖图是否允许不清楚） | SD1.5 LoRA，27 MB | CPU 可跑 | **实测**：约 65 秒/张（§2.3） | 质量见 §2.3 |
| latent-consistency/lcm-lora-sdv1-5 | OpenRAIL++ | SD1.5 LoRA | — | 实测（与上一行一起用，6 步） | 加速采样 |
| Limbicnation/pixel-art-lora、adirik/pixel-art-lora-flux.2-klein-4B、svntax-dev/pixel_spritesheet_4walk_small_lora_v1（四向行走图） | Apache-2.0；底模 FLUX.2-klein-4B 也是 Apache-2.0 | 3.9 B 参数的变换器 + 文本编码器 | GPU | 不可行：bf16 权重就要 15 GB 左右【推断】 | 许可干净，有 GPU 时可以出概念图、行走图草稿 |
| tarn59/pixel_art_style_lora_z_image_turbo 等 | Apache-2.0；底模 Z-Image-Turbo（6.2 B）Apache-2.0 | 6 B | GPU | 不可行 | 同上 |
| nerijs/pixel-art-medium-128-v0.1 | CC-BY-NC-4.0 | SD3 Medium | GPU | — | **排除**（只许非商业） |

**数据集**：没有能当游戏美术的。
- `jainr3/diffusiondb-pixelart` 是 CC0，但内容是 AI 生成的伪像素图。
- `bghira/free-to-use-pixelart` 标的是 MIT，但内容是从网上收集的，原作许可不清楚。
- `carlosuperb/lpc-*` 是 CC-BY-SA 3.0（LPC）。
- `Chan-Y/pixelart-308k` 是 CC BY 4.0 的合成图。
- `KhalfounMehdi/gametilenet-sprites-unannotated` 没写许可。

另外，`PeakNav/global-elevation-aster-slippy-tiles-tar-gz`（Apache-2.0 标注）这类高程数据可以给地图 v3 当地形参考（§4.6）。

### 2.2 实测一：立绘像素化（PixelOE 0.0.10，CPU）

- 输入 `assets/portraits/tsuzumi_bust.webp`（512×640），全程在本地处理，没有上传。
- 输出 103×129 和 78×98 两档。用了 `contrast` 和 `k-centroid` 两种降采样模式，有的再量化到 24 色。对照组是面积平均降采样，加或不加 24 色量化。
- 图：`previews/pixelize_tsuzumi_x3.png`。
- 结果：
  - 面积平均会把眼睛、发丝、斗笠边糊掉；
  - PixelOE 的 contrast 模式保住了眼睛、发丝和斗笠的轮廓，但轮廓扩张在头发和袖口上留下白色碎点和断线；
  - k-centroid + 24 色最干净。
- 判断：能完成大约六七成。后面还要三步清理：锁定到项目色板、去掉孤立像素、强制 1 px 轮廓；然后人工修眼睛和嘴。这比从头手画立绘便宜得多，适合 F-3 的流程。

### 2.3 实测二：CPU 上的文生图（SD1.5 fp16 → fp32，LCM-LoRA + PixelArtRedmond，6 步，512²）

- 时间：加载 14 秒；第一张 461 秒（和并行的 git 操作抢 CPU，也是冷启动），之后每张 64–70 秒。峰值内存没有测。
- 提示词写了"3/4 俯视、日本山间神社、石灯笼、苔石阶、橄榄绿、黄昏"。
- 产出是侧视、高饱和、剪贴画式的图：天空蓝，红色"塔"，没有 3/4 视角，没有低饱和。按 4 px 一格还原到 128 px 网格以后，仍然是同样的画面（`previews/sd15_cpu_test.png`）。
- 判断：本机能跑的生成模型，对我们的美术没有用处。

**下载超额**：这一步的下载超出了任务给的约 3 GB 额度。原因是 `SedatAl/pixel-art-LoRa` 仓库的子目录里有 4 个 1.7 GB 的完整检查点，我用 `*.safetensors` 通配下载时一起拉了下来。这些已经删除，但流量已经发生。本次总下载约 9.4 GB。教训：从 HF 下载前先列出完整文件表，只写确切的文件名。

---

## 3. Godot 4 插件与着色器

### 3.1 先看 4.7.2 自带什么（查自 `doc/classes/*.xml` 和源码）

- **2D 光照**：
  - `PointLight2D`、`DirectionalLight2D`（`height` 只作用于法线贴图）；
  - `CanvasTexture`（漫反射 + 法线 + 高光）；
  - `LightOccluder2D` 阴影，`shadow_filter` 有 PCF5、PCF13，另有 `shadow_filter_smooth`；
  - `CanvasModulate`。
  - 每个画布项最多 16 盏灯：`MAX_LIGHTS_PER_ITEM = 16`，在 `renderer_canvas_render_rd.h` 和 `rasterizer_canvas_gles3.h` 里都是这个值。一张大的地面烘焙纹理在夜里可能撞上这个上限。解法有三种：把地面切成块；改引擎常量（E-1 允许）；或者像 JS 版一样做全屏延迟光照。
- **2D 阴影的性质**：Light2D 的阴影是从遮挡多边形在平面内投出去的。它适合夜里灯笼被墙、篱笆挡住的情况，**不适合 3/4 视角下的太阳**：太阳的影子应该落在地面上、长度有限、跟着高度走。所以 JS 版的做法（高度场代理的阴影图 + 精灵"转向太阳的卡片"）要在 Godot 里重写，没有插件可替代。
- **HDR 2D 与泛光**：
  - `Viewport.use_hdr_2d` 打开 RGBA16 的 2D 帧缓冲，配合 `WorldEnvironment` 的 Canvas 背景模式做 2D 泛光。宪章要求"泛光只给光源"：让灯笼的自发光大于 1，阈值设在 1 附近。
  - 文档原话：Mobile 渲染器"only supports a lower dynamic range up to 2.0"；不开 HDR 时 2D 是 SDR，阈值要低于 1。
  - 安卓上要实测。
- **2D SDF**：canvas_item 着色器的 fragment 和 light 阶段都有 `texture_sdf`、`texture_sdf_normal`、`sdf_to_screen_uv`。SDF 由 `LightOccluder2D.sdf_collision` 生成，`GPUParticles2D` 的碰撞也用它，覆盖范围和精度用 `rendering/2d/sdf/oversize|scale` 设置。用处：
  - 雨、落叶、萤火虫撞到墙和崖会停下或弹开；
  - 雾贴着崖脚走；
  - 岸边按距离起白沫。
  - 4.7 的 Compatibility 渲染器源码（`drivers/gles3`）里也实现了 2D SDF，所以这不是原生独有的能力；放弃网页版对它没有影响。
- **其他**：`Parallax2D`（远景视差）、`TileMapLayer`、`MultiMeshInstance2D`（大量草丛、叶片实例）、`CanvasGroup`、`BackBufferCopy`、2D 物理插值（`physics/common/physics_interpolation`）、`rendering/2d/snap/snap_2d_transforms_to_pixel`、`noise` 模块（FastNoiseLite）、`NavigationServer2D`。
- **计算着色器**：RenderingDevice 在 Forward+ 和 Mobile 上都有，可以自己写 2D 延迟光照、阴影图、GI；安卓上的性能要实测。

### 3.2 插件、着色器表

★ 是 GitHub 星数，"最近" 是最近一次提交的日期，都是 2026-10-14 查的。"4.7 兼容"如果没有写"实测"，依据都是作者声明或示例工程的 `config/features`，**我没有在 4.7.2 编辑器里跑过任何一个**。

**地形、瓦片、散布**

| 项目 | 许可 | 版本 / Godot | 成熟度 | 建议 | 理由 |
|---|---|---|---|---|---|
| SmartShape2D https://github.com/SirRamEsq/SmartShape2D | MIT（随包声明） | 3.3.2，示例工程 4.5 | 1758★，最近 2026-08-07 | **只作编辑器形状工具** | 用曲线画多边形的填充和沿边纹理，适合在编辑器里勾崖线、岸线、路。但沿曲线贴的像素纹理会被旋转、拉伸，斜边上像素团会碎掉【推断，未实测】。用法：画形状，把多边形交给我们自己的像素烘焙；也可以生成碰撞 |
| TileMapDual https://github.com/pablogila/TileMapDual | MIT | 5.0.3，示例 4.5 | 1278★，最近 2026-09-03 | **运行时可改的地面层再用** | 双网格：每对材质约 15 块瓦片，过渡是圆角。静态地形我们的逐像素烘焙更好；玩家开垦的田、小伙伴踩出的路、建筑地基需要运行时修改，这时可以用（或自己写双网格） |
| Better Terrain https://github.com/Portponky/better-terrain | Unlicense（公有领域，无声明义务） | 示例 4.x | 746★，最近 2026-02-09 | 参考 | 改进 TileMap 的地形匹配规则。我们的地面不走瓦片，用处小 |
| 5-tile dual-grid autotiler https://github.com/laffcat/5-tile-autotiler | MIT | 示例 4.7 | 8★ | 参考 | 双网格加随机变体，项目很小 |
| Gaea 2.0 https://github.com/gaea-godot/gaea | MIT | v2.0.0-beta6，示例 4.7 | 1652★ | 不用 | 程序化生成图。我们的世界是手工设计的，地形由自己的生成器出 |
| Scatter2D https://github.com/alex9978/scatter2d | MIT | 1.4，示例 4.3 | — | 参考，自己写 | 在区域里撒精灵。我们要的是 MultiMeshInstance2D + 泊松盘 + 风摆着色器，自己写不到一天 |
| WaveFunctionCollapse https://github.com/mxgmn/WaveFunctionCollapse | MIT | C# 原型 | 经典 | 不用 | 生成布局，和吸引力法则的手工地图相冲 |

**植被、风、水、倒影、着色器库**

| 项目 | 许可 | 版本 / Godot | 成熟度 | 建议 | 理由 |
|---|---|---|---|---|---|
| godotshaders.com：「2D Pixel perfect wind & sway effect」「2D Wind Sway / Tree & Grass Motion」 https://godotshaders.com/shader/2d-pixel-perfect-wind-sway-effect/ | 页面写明 CC0（站点让作者在 CC0、MIT、GPLv3 里选；**GPL 的不能用**，每个都要单独确认） | Godot 4 语法 | — | **采用（改写）** | 风摆的起点，CC0 不用附声明 |
| godotshaders.com：「Sub-pixel accurate pixel sprite filtering」（mortarroad） https://godotshaders.com/shader/sub-pixel-accurate-pixel-sprite-filtering/ | CC0（页面原文） | 为 3.2 写的，改到 4.x 要小改 | — | **采用** | 像素精灵做亚像素移动、缩放时不闪烁 |
| GDQuest godot-shaders https://github.com/gdquest-demos/godot-shaders | 代码 MIT；**美术是 CC-BY-NC-SA 4.0，不能用** | 正在移植 4.x，示例 4.3 | — | **挑着采用** | 有 `foliage_wind_grass/leaves/trunk`、`water_2D`、`mirror_y`、`outline2D_*`、`dissolve2D`、`shockwave`、**`xray_2d_mask`**（宪章要求"遮挡时挖透视孔"）、`clouds2D`、高斯模糊 |
| dynamic-2d-grass https://github.com/mlaass/dynamic-2d-grass | MIT | 1.0.2，Godot 4.5+ | 10★，2026-04 | 参考，挑着用 | 像素草叶、风、角色推开草、破坏贴花、世界空间的云影。项目很新，适合"草会被她走开"这种可视可感的细节 |
| 2d-pixel-water-shader-godot https://github.com/jess-hammer/2d-pixel-water-shader-godot | MIT | Godot 4.4（mono 工程，着色器本身是 .gdshader） | 126★ | 参考，挑着用 | 像素水面和拖尾 |
| godotshaders 上的「Pixel Water for Godot 4.3」「Water 2D + reflection 4.x」 | 逐个确认 | 4.x | — | 参考 | 用屏幕纹理反射的方案，只反射已经画出的东西，平移镜头时水位会漂（评论里有人报告）。**倒影要自己做**：每个会被倒映的精灵以自己的地面线为轴翻转，画进反射层（SubViewport），再用水面遮罩和波纹扭曲。这样 3/4 视角下才对 |

**光照、阴影、时间**

| 项目 | 许可 | 版本 / Godot | 成熟度 | 建议 | 理由 |
|---|---|---|---|---|---|
| 内置 2D 光照（§3.1） | MIT（引擎） | 4.7.2 | — | **基础** | 法线、点光、灯笼阴影、HDR 泛光都用内置的 |
| Lit https://github.com/shawndeprey/lit | MIT | 1.1.6；"Requires Godot 4.4+ on the Forward+ renderer"（**仅 Windows**） | 47★，2026-06 创建，18 个未关闭问题 | 观望 | 不限灯数，SDF 软阴影，带后处理。太新，安卓（Mobile）不能用；撞到 16 灯上限时再评估 |
| DropShadowCaster2D https://github.com/csocraman/2D-projected-ground-shadow | MIT | 1.0.6 | 26★ | 参考 | 用射线把影子投到地面上，影子会在崖边折下去。我们的太阳阴影要自己做，这个思路可以借鉴 |
| 2D GI（JFA → SDF → 光线步进） https://github.com/samuelbigos/godot_2d_global_illumination | MIT | Godot 3.x 时代 | 214★，最近 2021 | 参考 | 平面内的全局光照，技术说明清楚 |
| Radiance Cascades https://github.com/Sohojoe/radiance-cascades-godot | Apache-2.0（若有 NOTICE 要保留） | 4.3 的移植 | 75★，最近 2024-08 | 以后做技术探针 | 计算着色器，Windows 和安卓都能跑但安卓要实测。效果是夜里灯笼、遠化光点的光往四周渗。平面 GI 和 3/4 的高度光照能否协调，未验证 |
| Normal Map Generator（krosseye） https://github.com/krosseye/godot_normalMap_generator | MIT | 2.1.1，示例 4.4 | — | 可选 | 给手绘或像素化的精灵补法线。我们的生成器本来就输出法线 |
| Laigter https://github.com/azagaya/laigter | GPL-3.0（独立工具，不进游戏，生成的图归我们） | — | 活跃 | 可选 | 同上，是桌面工具 |
| DynamicDayNightCycles https://github.com/eisclimber/DynamicDayNightCycles | MIT | 1.1.0，示例 4.7 | 42★ | 不用 | 我们的 `tod.js` 调色表直接移植更好 |

**镜头、像素**

| 项目 | 许可 | 版本 / Godot | 成熟度 | 建议 | 理由 |
|---|---|---|---|---|---|
| SmoothPixelSubViewportContainer https://github.com/apples/godot-smooth-pixel-subviewport-container | MIT | 0.1.1，4.3 | 21★，最近 2024-12 | **采用这个做法**（代码很短，可以直接用或重写） | 在 480×270 的 SubViewport 里渲染，整数放大时补上亚像素偏移，再加抗锯齿滤镜：镜头移动平滑，像素网格不动 |
| Phantom Camera https://github.com/ramokz/phantom-camera | MIT | 0.11.0.3，Godot 4.4+ | 3603★，活跃 | 试用 | 仿 Cinemachine：按优先级切换镜头并补间、跟随、取景。可以接 `cine.js` 的演出。要验证它和上面亚像素平滑的配合 |

**对话、演出、AI、测试、输入、导入**

| 项目 | 许可 | 版本 / Godot | 成熟度 | 建议 | 理由 |
|---|---|---|---|---|---|
| Dialogue Manager 4 https://github.com/nathanhoad/godot_dialogue_manager | MIT | 4.1.0，"for Godot 4.6+" | 3920★，2 个未关闭问题，活跃 | **采用（脚本与运行时）** | 剧本式对话文件：条件、调用游戏函数、翻译。对话框（像素立绘，不挡字，F-3）自己做 |
| Dialogic 2 https://github.com/dialogic-godot/dialogic | MIT | plugin.cfg 写着 "2.0-Alpha-21 WIP (Godot 4.5+)" | 6063★，191 个未关闭问题 | 不用 | 偏视觉小说，仍是 Alpha，比 Dialogue Manager 重 |
| LimboAI https://github.com/limbonaut/limboai | MIT | 1.8.x：GDExtension 支持 4.6+，**模块版对应 Godot 4.7** | 3050★，活跃 | **采用（编成引擎模块）** | 行为树 + 分层状态机，带编辑器和调试器，C++ 性能好，适合大量小妖同时搬运、施工、种田。注意：编成模块后，Windows 和安卓的导出模板都要带它一起编译 |
| Beehave https://github.com/bitbrain/beehave | MIT | 2.9.x | 3299★ | 备选 | 纯 GDScript，简单，大量单位时慢 |
| GdUnit4 https://github.com/godot-gdunit-labs/gdUnit4 | MIT | 7.0.0，示例 4.7 | 1263★，活跃 | **采用** | 单元测试和场景测试，可以模拟鼠标、键盘、**触摸**、自定义输入动作；有命令行工具（`runtest.sh`），可以脱离编辑器跑（CI 用）。符合"真实输入路径"的规则（宪章 §4），但输入是否真的走引擎的输入事件路径，接入时要确认 |
| GUT https://github.com/bitwes/Gut | MIT | 9.6.1 | 2753★ | 备选 | — |
| Virtual-Joystick-Godot https://github.com/MarcoFazioRandom/Virtual-Joystick-Godot | MIT | 示例 4.2 | 989★，最近 2025-01 | 参考或作底子 | 安卓摇杆。我们点选目标、技能键的操作逻辑要从 `src/ui` 移植过来 |
| LDtk Importer https://github.com/heygleeson/godot-ldtk-importer ・ YATI（Tiled）https://github.com/Kiamo2/YATI | MIT ・ MIT | 2.0（4.3，最近 2025-02）・ 2.2.7 | 260★ ・ 293★ | 可选 | 如果地图 v3 想用外部编辑器摆实体、区域、触发器，可以用；地形本身仍走我们的烘焙 |
| Aseprite Wizard https://github.com/viniciusgerevini/godot-aseprite-wizard | MIT | 9.8.0 | 1384★ | 视流程而定 | 只有在用 Aseprite 手绘时才需要（Aseprite 本身是商业许可） |
| Palette Swap Shader（KoBeWi） https://github.com/KoBeWi/Godot-Palette-Swap-Shader | MIT | 1.2 | 115★ | 可选 | 季节、时段的换色变体 |
| Godot-FogOfWar（AntonWedemeier） | **仓库没有许可文件，等于保留所有权利，不能用** | — | 24★ | 排除 | — |
| minimap-lite（godot-forge） | 免费版限制 4 个节点，迷雾是付费功能 | — | 0★ | 排除 | — |

**自己写的**（没有合适插件，或插件得不偿失）：
- **小地图和迷雾**：烘焙好的缩小地图纹理，加一张"已探索"遮罩，按区域的解锁条件打开（F-1）；
- **存档**：FileAccess + 带版本号的 JSON；
- **时段**：移植 `tod.js`；
- **倒影**：见上；
- **太阳阴影与延迟光照合成**；
- **遠化**；
- **角色光照保护**：knowledge/08 §1 的三条不能退化。

### 3.3 只有原生版本才有的提升（可以考虑）

- **仅 Windows（Forward+）**：Lit（作者声明 Mobile 和 Compatibility 都不支持）。
- **Forward+ 和 Mobile 有、网页版（Compatibility）没有：计算着色器（RenderingDevice）。** 自写的延迟光照、阴影图、Radiance Cascades 都靠它。放弃网页版之后，这些才成为选项。
- **与渲染器无关，但网页版时不现实**：
  - 引擎模块（LimboAI）；
  - 更大的纹理和显存预算；
  - 构建时离线烘焙的大量贴图，不再受下载体积限制。
- **不算原生独有**：HDR 2D 和 2D SDF。4.7 的文档和源码里没有看到对 Compatibility 的限制。Mobile 上泛光的动态范围只到 2.0（文档原话），安卓要实测。
- **引擎层**：
  - LimboAI 编成模块；
  - 视需要提高 `MAX_LIGHTS_PER_ITEM`；
  - 把地形烘焙写成 C++（GDExtension 或模块），或者在构建时离线烘焙。JS 版烘焙要 4–5 秒，见 knowledge/08 §4。

---

## 4. 自然地形的画法与参考

### 4.1 透视规则以 knowledge/15 为准（针对 R-1）

台阶、路、崖、建筑的画法已经写在 [15-perspective-rules.md](15-perspective-rules.md)（与本篇同日）。那篇是项目规则，本篇只补充调研中看到的外部佐证和反例，不另立规则：

- **视角不能混**。Slynyrd Pixelblog 3 的原话是 "In most cases graphical projections should not be mixed in the same scene."；LPC 风格指南也写了 "If you're using perspective techniques on your props or tiles, that's wrong"。
  - 等距的房子（Jetrel）、侧视的树和花（karsiori、SpiderDave）、侧视的平台瓦片（OPP）放进我们的斜投影都会错。
  - 例外是树：它近似轴对称，所以等距的针叶树（§1.2 的 pistachio）可以用。
- **反例 Cainos**：东西走向的墙和崖也画成整面朝南的墙，台阶是贴在立面上的矩形。这正是 knowledge/15 §0 说的"东西向竖直面只给 1–3 像素侧边"的反面，也是 A-1 说的"方方正正"。它在透视一致性上值得学，在形状上不能学。
- **正面参考 Tiny Swords**：高台边缘鼓包状的草沿、不齐的崖脚，对应 knowledge/15 §1 的"崖的轮廓必须是有机的"。
- **路不画透视收窄**。CC0 瓦片集里的路全是 16 px 格子上的色带，正好是 knowledge/15 §3 说的"不是贴在地上的色带"的反例。

### 4.2 边缘去网格感

- 静态地形继续用**矢量形状加逐像素烘焙**（JS 版已经是这样）：崖线、岸线、路缘是带噪声的曲线，边界上的抖动只在 1–2 px 内。
- **每条边都要有"打断物"**：草舌、半埋的石头、树根、蕨、落叶。崖顶不允许出现超过若干像素的笔直水平线。我建议上限 24 px，要实测确定。
- 只有运行时会改的地面层才用瓦片（双网格，见 TileMapDual），并且每种过渡至少准备 3–4 个随机变体（boristhebrave：dual grid 只有 16 种情形，其中一种是空，实际 15 块瓦片）。
- Slynyrd Pixelblog 43 的瓦片做法可以借鉴：不满格的纹理去掉底色，好叠层；台地压在崖上时，用三角形的过渡块去接地面；投影要克制，最多一两个面、不超过一格，而且无论墙多高都一样长。

### 4.3 分层（风来之国式的构图）【观察】

由远到近：
1. 远景视差：山脊剪影、雾，用 `Parallax2D`；
2. 烘焙地面：含平面图式的路、田、水；
3. 按 y 排序的中层：角色、物件、树干、崖面作为整块场景件；
4. 前景遮挡物：树冠、屋檐、离镜头近的崖顶，单独一层，角色走到后面时淡出，并在角色周围挖透视孔（x-ray 遮罩）；
5. 大气层：光束、薄雾、萤火、落叶粒子；
6. 光照合成：太阳阴影、灯、泛光；
7. 调色。

风来之国的地面和植物几乎看不到棋盘格抖动，靠的是成簇的形状（knowledge/08 §2.1 已有记录）。

### 4.4 像素画的光照：业界说法

- **风来之国**：Chucklefish 的发行公告说画面是"3D lighting and retro-pixel style artwork"，用的是 Pixpil 自研引擎。Game Developer 的访谈（"Road to the IGF: Pixpil's Eastward"，2020）说自研引擎 Gii "built on top of an open source engine called MOAI"，美术用 Aseprite 和 Photoshop，并做了自动化的素材流程工具。是否用了法线贴图、如何用，【未核实】：一篇 2021 年的第三方博客说道具"有专门的纹理通道"参与光照，itch 论坛上有人怀疑。
- **Sea of Stars**（Unity，Sabotage）：2020 年 Kickstarter 时期的报道列出了"fully dynamic lighting of sprites including normal mapping, pixel depth writing and shadow receiving"、体积光、屏幕空间间接光。工作室说所有素材都要满足动态光照的技术要求。这和我们 JS 版的路线（逐像素法线 + 高度 + 延迟光照）是同一类。
- 宪章已经要求：只给光源泛光；角色上不做分档和抖动。

### 4.5 参考资料

- Slynyrd（Raymond Schlitter）Pixelblog：
  - 3「Graphical Projection」https://www.slynyrd.com/blog/2018/3/14/pixelblog-3-graphical-projections-1
  - 20「Top Down Tiles」https://slynyrd.com/blog/2019/8/27/pixelblog-20-top-down-tiles
  - 21「Top Down Objects」https://www.slynyrd.com/blog/2019/9/18/pixelblog-21-top-down-objects
  - 43「Top Down Tiles Part 2」（崖、台地、投影）https://slynyrd.com/blog/2023/3/26/pixelblog-43-top-down-tiles-part-2
  - 只能读来学，不能搬运原图。
- LPC 风格指南 https://lpc.opengameart.org/static/LPC-Style-Guide/build/styleguide.html：32×32 网格，约 60° 的俯视，正交，"If you're using perspective techniques on your props or tiles, that's wrong"。光源方向在官方指南里我没找到原文，TechRadar 转述为"from above, and possibly slightly to the left"【未核实】。
- 自动拼接：boristhebrave「Quarter-Tile Autotiling」https://www.boristhebrave.com/2023/05/31/quarter-tile-autotiling/ （双网格和 1/4 瓦片的取舍）；Red Blob Games 的 autotile 文章 https://www.redblobgames.com/ ；jess::codes 的双网格视频和 TileMapDual 的实现。
- 技术实现参考：GDQuest 着色器库（风、水、x-ray）；samuelbigos 的 2D GI 说明（Jump Flood → 距离场 → 光线步进）。

### 4.6 真实地形当参考（地图 v3）

日本山道、九十九折、梯田、宿场的自然形状，可以拿真实高程数据当草图参考：顺着等高线走的路、台地的宽窄变化。可用的数据：
- SRTM（USGS，公有领域）；
- ASTER GDEM，HF 上有 Apache-2.0 标注的切片集；
- 国土地理院的 DEM，有出典要求；
- OSM（ODbL，要署名）。

只拿来参考形状，不把数据放进游戏。各数据的许可细节这次没有逐条核实。

---

## 5. 建议的下一步（给主管，按收益排序）

1. **地形规则先行（R-1）**：Godot 版的烘焙按 knowledge/15 实现。素材再好，也解决不了透视规则的问题（§1.3）。
2. **照片扫描当岩块形状来源（§1.4）**：在生成器里试 `cliff_side`、`rock_face_03` 这类 CC0 扫描图，用分水岭分块、平涂加倒角，输出反照率、法线、高度，崖面和野面积み都试。对照现在的 Voronoi 石块并排看。
3. **立绘像素化（F-3）**：PixelOE（k-centroid、24 色）→ 锁定项目色板 → 去孤立像素 → 1 px 轮廓 → 人工修脸。离线工具不进游戏，Apache-2.0 没有附加义务。
4. **Godot 基础件**：
   - 采用 Dialogue Manager 4、GdUnit4、LimboAI（模块）；
   - 亚像素平滑的 SubViewport；
   - 着色器：CC0 风摆、GDQuest x-ray、CC0 亚像素滤镜；
   - 内置 HDR 2D 泛光，安卓上实测。
5. **pistachio 针叶树**：先在一个中景里试放，补法线、映射到我们的色阶。不行就只当杉树生成器的造型参考。
6. **授权政策提案**（pending）：建议维持"美术、音频只用 CC0 / 公有领域；代码用 MIT、BSD、Apache、Unlicense、CC0，声明统一放在随包的第三方许可文件"；着色器网站上 GPL 的不用；只许非商业的模型和数据（Pixelization、pixel-art-medium-128）排除。

## 6. 没做到和不确定的地方

- **itch.io 的包没有下载**：免费下载要走"购买"表单，本次权限不允许。评估只基于宣传截图，像素尺度是我从截图里测的（整数倍或约 4.5 倍）。Ninja Adventure 另外稀疏克隆了它 GitHub 上的 Godot 4 工程（只看了部分贴图，没有放进对照图）。
- **插件都没有在 4.7.2 编辑器里跑**：兼容性来自作者声明和示例工程的 `config/features`。SmartShape2D 斜边像素会碎是推断。
- **生成模型**：只实测了 SD1.5 + LoRA，没有测峰值内存。FLUX.2-klein、Z-Image 的 CPU 不可行是按参数量推断的。
- **下载超额**：本次约 9.4 GB，额度约 3 GB，原因见 §2.3。多出来的文件已删除。
- **风来之国的技术细节**：全部是二手说法或【观察】。
- **许可原文**：都是 2026-10-14 的页面内容，以后可能变。真正采用某个素材时，要把当天的许可页存档进 `assets/` 的清单。
