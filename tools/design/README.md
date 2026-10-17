# tools/design：新手村 v4 的设计图纸生成器

从 `docs/design/village/registry.json`（美术资源总档，唯一的数据源）生成全部设计图纸和表。设计阶段的工具：不碰 `godot/`，不进游戏。

## 怎么跑

```bash
python3 tools/design/village_plan.py --fonts /path/to/fontdir            # 全部
python3 tools/design/village_plan.py --fonts /path/to/fontdir --only plan  # 只出平面（plan / views / scale / tables 任选）
```

依赖：Python 3（numpy、scipy、scikit-image、Pillow、fontTools、brotli），以及预装的无头 Chromium（Playwright 的 `chromium_headless_shell`，路径自动找；也可以用环境变量 `VD_CHROME` 指定）。一次全跑约 2 分钟，单线程，不会占满 CPU。结果是确定的：所有随机都有固定的 seed。

## 输出（`docs/design/village/`）

| 文件 | 内容 |
|---|---|
| `plan_site.svg/.png` | 图 A 总平面图：分区、结界的边、参道顺序①–⑩、等高线、水系、崖、路（真行草）、植物、关键视点的地面视野，右下是参道纵断面 |
| `plan_realm.svg/.png` | 图 B 结界内平面图：每个元素的编号、大楠冠的投影（证明茅屋东头在冠下）、轴、视线 |
| `plan_walk.svg/.png` | 图 C 可走与不可走：每块不可走的格子按原因上色；把三个门关上从院子漫出去，检查结界的边有没有漏洞（空气墙） |
| `plan_screens.svg/.png` | 图 D 屏数与主角间距：分区面积折成 P3 屏数，四个主角各自的关键视点画面 |
| `view_0N_*.svg/.png` | P3 关键视角（推荐的比例方案下）：体块渲染 + 标注 + 平面上的视野 + 构图说明 |
| `scale_sheet.svg/.png`，`scale_{now,A,B,C}.png`（原生 640×360）和 `_x3.png`（×3） | 她的身高：现在（参照）和三个方案，后倾份额 1.0 下 |
| `tables.md` | 比例表、方案表、分区面积表、主角间距、视点检查、她会走到哪些东西背后（设计说明引用它；不要手改） |

PNG 不进 git（.gitignore），随时可以重新生成；交付评审页时由主管 `git add -f` 挑选。

## 代码

| 模块 | 做什么 |
|---|---|
| `vd/p3.py` | P3 相机（PixelView3D 的透视预设）：投影、后倾、她脚下的像素比例、可见地面。后倾份额默认 1.0（渲染器 2026-10-17 定的）。和渲染器的 `upright_scale.py` 对过数（份额 0 / 0.3 / 0.5 / 1.0 时她脚下每米 19.75 / 22.39 / 24.14 / 28.53 像素；份额 1.0 时画面上沿 21.0、下沿 32.2） |
| `vd/registry.py` | 读总档；折线、多边形、碰撞形状；成片种植的撒树（seed 固定）；P3 种植律 `p3_south_low`（带后倾）；手放的东西在哪些地方挡住她 `occlusion_by_elements` |
| `vd/terrain.py` | 高度场：控制点薄板样条 + 平台（石垣处是陡边）+ 刻槽（切通、溪床、路基；切通靠镜头的南坎可以放缓）+ 崖（落差、两端收尾、回落）+ 隆起 |
| `vd/walk.py` | 可走性：坡 > 35°、水面、篠竹丛、实心物件、石垣瑞垣；石段、桥、缘侧、台是可走面；结界的封闭检查 |
| `vd/plan.py`、`vd/sheets.py` | 平面图的画法和图 A–D 的版式 |
| `vd/views.py` | 关键视角的体块渲染（Z 缓冲，原生 640×360 的 2 倍），她是一张按方案像素画的卡片 |
| `vd/lineup.py` | 身高方案的并排对照（同一个渲染器、同一个相机） |
| `vd/tables.py` | 表（含关键视点和全部路上"她被不被地形挡住"的检查） |
| `vd/fonts.py`、`vd/svg.py`、`vd/export.py` | 字体子集化与嵌入、SVG、SVG 转 PNG |

**碰撞和画面从同一份数据来**：每个元素的 `collision` / `footprint` 定碰撞；平面图上的符号、图 C 的不可走格子、关键视角里的体块都从同一条记录画出来。成片种植的树由 `seed` 撒出，树干的碰撞圆和图上的树是同一次撒的结果；P3 种植律对它们的压低也在同一处执行。以后重建地图时，Godot 的组装读同一份 `registry.json`。

## 字体（SIL OFL 1.1，不进仓库）

标题用 Noto Serif SC（明朝体一类），注记用 Noto Sans SC。只在生成时子集化成 WOFF2、以 data URI 嵌进 SVG 的 `@font-face`，字体族名改成中性的 `VD Serif` / `VD Sans`（Noto Sans SC 的许可里有保留字体名 'Source'，子集不用这个名字）。每个 SVG 的开头有一行注释写明版权和许可。

来源（npm tarball；只下载、解包，不执行里面的任何东西，不 `npm install`）：

| 包 | 版本 | tarball | SHA-256 | npm integrity |
|---|---|---|---|---|
| `@expo-google-fonts/noto-serif-sc` | 0.4.4 | https://registry.npmjs.org/@expo-google-fonts/noto-serif-sc/-/noto-serif-sc-0.4.4.tgz | `38b2ca4e45b33e22ad74c68d1e3b32c584ffe3509293ba1735b5248d66864214` | `sha512-RIPZykLmhdnqjaYuIVNA7btxvd8OwKNK1CSqLiszCOVJAIhkud9cSrOoecYiwU3HetKGaHEZWzD2jbWd43D6mA==` |
| `@expo-google-fonts/noto-sans-sc` | 0.4.4 | https://registry.npmjs.org/@expo-google-fonts/noto-sans-sc/-/noto-sans-sc-0.4.4.tgz | `e18cd1a1fbb95d7c25fc133406dfd1b2b25d718835b51ec23d556dc4b11578a8` | `sha512-LF4+p6xdtgUArufW0K+l9/FeDiXrW8FcEkEbOPIUC5ZnPupeFVA6yY9qCZ0sBrdAeLdlusDhv0R7q2x3onXo3w==` |

用到的 TTF 和它们的 SHA-256（`vd/fonts.py` 每次运行都会校验，不符就停下）：

| 文件 | SHA-256 |
|---|---|
| `NotoSerifSC_400Regular.ttf` | `c358a69de3df5f423a8946a7b03e3126fb6ba116f1130a463455b4e39e1f0742` |
| `NotoSerifSC_600SemiBold.ttf` | `5d19e0f438d4a30371f584d34a87c9232dba0a85237db63fe5337fe743487def` |
| `NotoSerifSC_700Bold.ttf` | `9c6a2ba736e4b499c84f65ce366bd3625c0401885fd3e585ace50fb738b96ff6` |
| `NotoSansSC_400Regular.ttf` | `d45f67f0a7c0ca3f256950777ce6a61cc7ce5f9696d02900cbbaac25f8aa7d16` |
| `NotoSansSC_500Medium.ttf` | `b30853d205f3ecdde938b1488c735ee15a2e870d31331b992fdc53971e23ec4a` |
| `NotoSansSC_700Bold.ttf` | `9a38ae0ab28cd5a256f9ea8e00dedc688aac17f7915fcb000572990afa956b96` |

重新取到同一批文件（在仓库外的一个新的空目录里做；中性的 User-Agent，不带任何个人信息）：

```bash
mkdir -p /tmp/vdfonts/serif /tmp/vdfonts/sans && cd /tmp/vdfonts
curl -sSL -A "TenganAssetBuild/1.0" -o serif.tgz https://registry.npmjs.org/@expo-google-fonts/noto-serif-sc/-/noto-serif-sc-0.4.4.tgz
curl -sSL -A "TenganAssetBuild/1.0" -o sans.tgz  https://registry.npmjs.org/@expo-google-fonts/noto-sans-sc/-/noto-sans-sc-0.4.4.tgz
echo "38b2ca4e45b33e22ad74c68d1e3b32c584ffe3509293ba1735b5248d66864214  serif.tgz" | sha256sum -c
echo "e18cd1a1fbb95d7c25fc133406dfd1b2b25d718835b51ec23d556dc4b11578a8  sans.tgz"  | sha256sum -c
tar -xzf serif.tgz -C serif && tar -xzf sans.tgz -C sans
cd - && python3 tools/design/village_plan.py --fonts /tmp/vdfonts     # 回到仓库根目录再跑
```

许可证全文在包里的 `package/LICENSE_FONT`（SIL Open Font License 1.1）。
