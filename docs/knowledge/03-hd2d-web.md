# 03 HD-2D 的做法与网页（three.js）实现

研究日期：2026-10-14，对应 three.js r186（npm 0.186.x）。

## 1. 开发者怎么做 HD-2D

主要来源：Acquire 在 UNREAL FEST EAST 2018 的演讲（4Gamer 报道 <https://business.4gamer.net/article/1810/18101801/> ；资料 <https://www.docswell.com/s/EpicGamesJapan/KXPWY5-UE4_UFE2018_ACQUIRE_OCTOPATHTRAVELER>）、Unreal Fest Europe 2019 英文资料、Unreal Engine 访谈（八方旅人 1 <https://www.unrealengine.com/en-US/spotlights/octopath-traveler-s-hd-2d-art-style-and-story-make-for-a-jrpg-dream-come-true> ；八方旅人 2 <https://www.unrealengine.com/en-US/developer-interviews/octopath-traveler-ii-builds-a-bigger-bolder-world-in-its-stunning-hd-2d-style>）、Live A Live 在 UNREAL FEST WEST '22 的演讲（<https://gamemakers.jp/article/2023_02_21_30973/>）。

- **引擎与精灵：** 全部用 Unreal Engine。八方旅人 1 的角色是 Paper2D 逐帧动画，每个角色每个职业约 365 张；试过骨骼绑定的精灵，因为看起来像 PS1 早期游戏而放弃。
- **画风的来历：** 第一个 UE4 原型让所有像素都锐利（全景深、像素动画的海、像素特效），测试者说是"上一代"。资料把解决办法称为"思い出補正"（回忆滤镜）：用景深制造空气感和纵深，效果丰富，但不过头。
- **镜头、比例与"箱庭感"：** 原型视场角太广，团队收窄并压扁透视。房屋缩到 FF6 那样的 Q 版比例。地图做成后高前低的梯台，镜头看不到天空。八方旅人 1 和 2 的探索镜头都是固定的。
  - 室内按"二分之一比例"：进门时切换灯光、后期设置和可见物体，镜头距离和角色大小都减半，房间显得更大而精灵在屏幕上的大小不变。
  - Live A Live 用窄长焦视场角的透视，避免边缘畸变。
- **精灵受光并投影：** "在视觉效果之外加一盏点光源，就能把角色的影子投到环境上"（饭塚，八方旅人 1）。
  - 八方旅人 1 的战斗中，增益时关掉太阳（也省性能），改用专门的点光源。
  - 八方旅人 1 的迷宫里："永远在角色正面放一盏聚光灯"，与朝向无关。
  - Live A Live 户外用平行光投影精灵影子，室内用贴花圆影，强度按地图设定。洞窟把精灵压得太暗，于是加了每张地图的精灵亮度和统一的自发光/受光比例。
- **环境材质：** 几乎都派生自一个主材质。
  - "世界坐标 UV"投影让像素纹理不随物体旋转，也藏住接缝。
  - 像素法线贴图、从上方投影的雪和沙、按物体的渐变染色来打破 16×16 图案的单调。
  - 顶点色驱动的风摆、遮罩控制的闪烁自发光、**挡在镜头和玩家之间的物体用屏幕空间圆形挖空**。
  - 资料指出像素纹理里画了左上方的光（"双重光照"，3D 的禁忌），结论是"像素画优先"。
  - 有机物用"2.5D 模型"（像素质感 + 实际光照）。
- **后期（八方旅人 1）：** UE4 自带的调色、泛光、散景景深、镜头光晕、环境立方体贴图、暗角，按地图调。战斗镜头拉近时景深收紧；破防时有色差。镜头光晕阈值很高，只在放置的亮灯或自发光处出现（水面闪光、夕阳）。
- **地形、地标与水：** 自研的块编辑器（100×100 单位的块、坡、高架）加模块化素材；雪地和沙漠用 UE Landscape；河流用样条。地标从灰盒 → 绘制稿 → 像素重建。水在"像素还是写实"之间很难拿捏。<https://www.siliconera.com/project-octopath-traveler-developers-answer-project-started-troubles-developing-hd-2d/>
- **性能事实：** 八方旅人 1 在 Switch 上底座 720p、掌机 1024×576、30 帧。Live A Live 把屏幕百分比降低 7% 省了约 5 毫秒，但像素画明显变差；最后保留 100% 分辨率加 FXAA，并从延迟渲染换成 UE 的移动端前向渲染。

## 2. 批评与后来的修正

- **模糊：** 八方旅人 PC 版评测："前景以外的一切都泡在厚厚的景深里。"<https://www.rpgsite.net/review/8649-octopath-traveler-pc-review> DQ3 HD-2D 的堀井雄二认为"模糊太强了"，于是减弱；PC 版加了景深开关。<https://blog.playstation.com/2024/11/08/dragon-quest-iii-hd-2d-remake-interview-how-the-classic-rpg-was-revamped-for-its-ps5-debut/>
- **氛围、灰暗与饱和度：** Live A Live 认为八方旅人的强景深、暗角和低饱和不适合自己的热血基调，改用弱景深、几乎不用暗角、舞台式布光。DQ3：加了景深和雾以后"饱和度掉了，不像勇者斗恶龙了"，于是用鲜艳调色、风格化的水、每个城镇一套调色板。<https://square-enix-games.com/news/inside-dragon-quest-iii-hd-2d-remake> 八方旅人 1 加了环境光，避免建筑阴影全黑。
- **精灵与环境不搭：** 八方旅人 2 的开发者说角色"像扁平的纸片"，八方旅人 1 需要"光照上的技巧"。浅野智也：正确的 HD-2D 是先在素材层面风格化，再加写实效果；先做写实素材再缩小，看起来只会像低分辨率。<https://www.4gamer.net/games/553/G055388/20220228038/> DQ3 的背景完全放弃了像素纹理。
- **闪烁：** Live A Live 需要 FXAA；DQ3 有"非常轻微的植被闪烁"。
- **八方旅人 2 的演进：** 地图分辨率更高、精灵更高、动态昼夜，战斗特效中镜头可转约 90°、事件中可转 180°。三角战略的 360° 镜头意味着每张地图要从各个方向都好看，素材量更大。
- Live A Live 光树就设计了约 30 种，因为树占满了野外。

## 3. three.js / WebGL2

- **投影：** 窄视场角的透视相机（约 20–30°）最接近原作，也为景深提供纵深。正交 + 像素对齐（three.js 像素示例）适合低分辨率的"3D 像素画"，不适合 HD-2D。
- **分辨率：** 不要按小数倍放大场景（见 Live A Live）。设备像素比分档封顶；景深、泛光、AO 用半分辨率。
- **受光、投影的精灵：** THREE.Sprite 不受光，也不进阴影 pass（r186 源码）。改用 Mesh 四边形：
  - 圆柱式公告板（只绕竖轴转向镜头）；
  - `alphaTest`（阴影 pass 会自动复用贴图和 alphaTest，得到镂空阴影）；
  - Lambert 材质，法线向上倾，每个区域一个自发光保底；
  - 在 `customDepthMaterial` 的顶点着色器里把四边形转向光源，避免光源侧照时影子缩成一条线。
- **像素稳定：** Nearest 过滤 + mipmap，或基于 fwidth 的抗锯齿最近邻采样（<https://godotshaders.com/shader/sub-pixel-accurate-pixel-sprite-filtering/>），之后 FXAA 或 SMAA。
- **景深：** three.js 的 BokehPass 会用深度材质重绘整个场景再做 41 次全分辨率采样，手机上避免。pmndrs/postprocessing（<https://github.com/pmndrs/postprocessing>）有 DepthOfFieldEffect（默认半分辨率）和 TiltShiftEffect（屏幕空间 Kawase 模糊，不需要深度），并能把多个效果合并成一道 pass、共享深度。three.js 还自带 Horizontal/VerticalTiltShiftShader（每道 9 次采样）。
- **AO：** N8AO（<https://github.com/N8python/n8ao>）半分辨率模式快 2–4 倍；手机上改为烘焙 AO。
- **雾与阴影：** 内置 Fog 几乎免费，保持克制。PCFSoftShadowMap 在 r182 弃用、r186 移除；用 PCFShadowMap 加 `shadow.radius`，或 BasicShadowMap。
- **水、粒子、光束（推论）：** 风格化的水（滚动的像素法线 + 自发光闪点喂给泛光），不用会重绘场景的 Reflector/Water；实例化加法混合粒子，注意过度绘制；手放的加法光束面片，屏幕空间体积光只在桌面上开。
- **示例（新、小、未审查）：** <https://legerdo.github.io/hd2d-diorama/>（r186，26° 视场角，影子面片转向光源，半分辨率散景）、PixelStage（MIT）<https://github.com/YUANYINGLONG-91/pixelstage>、ThreeMaker、Godot SimpleHD2D。没有找到成熟的教程。
- **预算：** PlayCanvas："低端手机大约每帧 100–200 次绘制调用"，按原生像素比渲染会成倍增加填充开销。<https://developer.playcanvas.com/user-manual/optimization/guidelines/> Meta Quest 2（手机级芯片）：少于 100 次绘制调用、少于 75 万三角形。动态分辨率可参考 drei 的 PerformanceMonitor 模式。Square Enix 的开发者说把原生 HD-2D 搬上手机"相当困难"。<https://nintendoeverything.com/octopath-traveler-champions-of-the-continent-devs-on-how-it-came-to-be-when-the-project-started-switch-differences-more/>

## 4. 素材管线（一个开发者 + AI）

- **工具：** Crocotile 3D（图块贴图套件，导出 glTF）、Blockbench（免费、网页可用，导出 glTF/OBJ）。MagicaVoxel 是体素风，需确认许可。
- **套件策略（与八方旅人一致）：** 网格图块 + 模块化部件；独特地标走"灰盒 → 绘制稿 → 像素重建"。固定纹理密度（建议每米 16 像素）。
- **避免重复：** 按物体的渐变染色、从上方投影的材质、更密的图块变体和颜色、每个区域一套调色板、灯光与旗帜（DQ3）、梯台地形；树要多设计几种（Live A Live 约 30 种）；推论：90° 旋转与镜像、贴花、预制团块、每屏一个地标。让 AI 写工具和着色器，但像素要手工清理（八方旅人 1 逐帧修坏像素）。
- **许可：** Kenney：CC0（<https://kenney.nl/support>）。KayKit：CC0。Screaming Brain Studios Tiny Texture Pack 3：CC0 平铺纹理（<https://opengameart.org/node/148379>）。Poly Haven、ambientCG：CC0 但写实（不适合直接缩小使用）。Quaternius 现在用自己的 QAL v1.0，不是 CC0。

## 5. 推荐的渲染配方

1. **阴影 pass：** 一盏平行光，正交视锥收紧；精灵和动态道具投影；手机上静态阴影预烘焙。
2. **主前向 pass：** HalfFloat 渲染目标带深度纹理。像素纹理（Nearest + mip）、世界坐标 UV、顶点色 AO 与染色、内置 Fog、上面描述的精灵四边形。
3. **AO：** 只在桌面。
4. **景深：** 宽对焦带，并提供开关。
5. **泛光：** mip 链泛光，阈值约 1（HDR），只作用于自发光、火光和闪点。
6. **最后一道合并 pass：** LUT 调色、色调映射（检查不把饱和度洗掉）、轻暗角、只在受击时的色差，然后 FXAA 或 SMAA。UI 在后期链之外渲染。

| | 桌面 | 中端手机 |
|---|---|---|
| 像素比 | ≤2 | 1–1.5，分档 |
| 绘制调用 | ≤500 | ≤100 |
| 三角形 | ≤100 万 | ≤25 万 |
| 阴影 | 2048²，PCF 半径 2 | 1024²，Basic，只给精灵 |
| AO | N8AO 半分辨率 | 烘焙 |
| 景深 | 散景 CoC，半分辨率 | TiltShiftEffect，半分辨率 |
| 泛光 | 8 级 mip | 4–5 级或关闭 |
| 抗锯齿 | MSAA 4× 或 SMAA | FXAA |
| 灯光 | ≤8 盏不投影 | ≤3 盏不投影 |
| 全屏 pass | 约 5–6 道 | ≤3 道 |
| 目标 | 60 帧 | 60，退回 30 |

表中数值是起点估计，锚定在上面引用的预算上；要在真机上用 `renderer.info` 测量。

## 未证实 / 缺口

没有任何作品公开过视场角或俯角（从 20–30° 开始试）；不确定精灵是否用法线贴图（只确认环境用了像素法线）；没有开发者说明光束怎么做；没有找到 HD-2D 的 CEDEC 演讲或 80.lv 拆解。
