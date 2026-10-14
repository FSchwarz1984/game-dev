# 10 · Godot 4 工具链：官方二进制、软件渲染试玩、Windows 与 Android 导出

日期：2026-10-14。来源：Godot 4.7.2-stable 源码（下文注明路径）、godot-docs 的 4.7 分支、本容器（4 CPU、15 GB 内存、Ubuntu 24.04）里的实测。日志、截图在会话 scratchpad，未入库。只读了源码、没有实测的结论标【未验证】；估算标【估】。

## 0. 结论

- 目标平台：Windows 和 Android（只横屏）。**两端都用 Mobile 渲染器**（主管决定，2026-10-14：2D 上 Forward+ 与 Mobile 只差辉光，统一后画面一致）。Web 不再需要（W-1，见 §11）。
- **不自己编译引擎，用官方 4.7.2 二进制。** GitHub 的 release 资源在本容器里是 403，但 `downloads.godotengine.org` 可以下载（它会 302 跳到 Godot 自己的对象存储）。校验用 `github.com/godotengine/godot-builds` 里公布的 SHA512（这个仓库可以 git clone）。`tools/godot/setup-godot.sh` 首次 80 s 装好编辑器和模板，再次运行 1.6 s。
- 官方编辑器在 Xvfb + Mesa 软件渲染下能真正开窗口运行游戏。Forward+、Mobile、Compatibility 三个渲染器都能截图、测 FPS，也能接收真实输入（xdotool 走 XTEST 发键盘、鼠标，鼠标再模拟成触摸）。
- 导出都已产出并检查过：
  - Linux：可执行文件 + .pck。
  - Windows：.exe + .pck，或把 pck 嵌进单个 .exe。在 wine 下能启动并接收输入，但要关掉 dinput8，见 §5.2。
  - Android：APK 为 arm64、横屏、Mobile 渲染器、minSdk 24、已签名。容器里没有 KVM，**APK 没有运行过**，只检查了内容和清单。
- 必须记住的四个坑：
  - 导出版要显示正确的中日文换行，必须带 ICU 数据（`include_text_server_data`）并把断行设为严格（`line_breaking_strictness = Strict`），见 §4。
  - 同一个 Environment 的辉光在 Forward+ 和 Mobile 下长得不一样，Windows 和 Android 会不一致，见 §3.4。
  - 480×270 整数放大在 1280×720 窗口下会留黑边，见 §6。
  - 软件渲染的 FPS 不代表手机，见 §9。

## 1. 版本

| 组件 | 版本 / 位置 |
|---|---|
| Godot | 4.7.2-stable，commit `ed1daf0bf001b61586d9930840f2f1394092c079`，官方构建串 `4.7.2.stable.official.ed1daf0bf` |
| 编辑器 | `/home/user/godotengine/editor/Godot_v4.7.2-stable_linux.x86_64`（139.6 MiB；zip 74.25 MiB） |
| 导出模板 | `~/.local/share/godot/export_templates/4.7.2.stable/`（只解出需要的，共 570 MB） |
| 软件渲染 | Mesa 25.2.8（LLVM 20.1.2）：lavapipe = Vulkan 1.4.318，llvmpipe = OpenGL 4.5 |
| Android SDK | `/home/user/godotengine/android-sdk`：cmdline-tools 19.0、platform-tools 37.0.1、build-tools 36.1.0、platforms;android-36 |
| JDK | 系统自带 OpenJDK 21.0.12（Godot 要求 ≥17，文档推荐 17，"更高版本也支持"） |
| wine（可选） | wine 9.0（Ubuntu 24.04 的 wine64 包） |

Android 版本号以引擎自己的 Gradle 配置为准（`platform/android/java/app/config.gradle`）：compileSdk/targetSdk 36、minSdk 24、buildTools 36.1.0、NDK 29.0.14206865、AGP 8.6.1、Gradle 8.11.1、Java ≥17。godot-docs 4.7 分支的 `tutorials/export/exporting_for_android.rst` 写的还是 build-tools 35.0.1、platform 35、NDK r28b、CMake 3.10.2，比引擎旧，以引擎为准。

## 2. 新会话怎么装（容器是临时的）

```sh
bash tools/godot/setup-runtime.sh       # apt：Xvfb、Mesa（lavapipe/llvmpipe）、xdotool、ImageMagick，约 110 MB
bash tools/godot/setup-godot.sh         # 官方编辑器 + 模板，逐个校验 SHA512
bash tools/godot/setup-android-sdk.sh   # 精简 Android SDK，475 MB
```

- `setup-godot.sh` 的做法：
  - 先 `git clone --depth 1 --filter=blob:none` godot-builds，读 `releases/godot-4.7.2-stable.json` 里的 SHA512。脚本里也钉了同样的值：两边不一致就停；GitHub 不通时只用钉住的值。
  - 只从 `downloads.godotengine.org` 下载（只允许 https 跳转）。
  - 模板只有一个 1222 MiB 的 .tpz 有校验值（godot-builds 里单独的 Android APK 只有 perfetto 性能分析版），所以整包下载、校验，再只解出需要的成员，然后删掉 .tpz。
  - 用记录文件判断是否已装好，可以反复运行。
- 实测：
  - 首次 80 s：编辑器 zip 74.25 MiB，.tpz 1221.99 MiB，两个 SHA512 都 OK。
  - 再次运行 1.6 s。
  - 磁盘峰值约 1.9 GB（.tpz + 解出的文件），装完常驻 710 MB。
- `setup-android-sdk.sh` 的做法：
  - 默认只装 platform-tools、build-tools;36.1.0、platforms;android-36。预构建 APK 导出只用到 build-tools 里的 apksigner 和 JDK 的 keytool，不需要 NDK。
  - `FULL=1` 再装 NDK 29.0.14206865（+2.4 GB）和 CMake，这两个只有 Gradle 自定义构建、原生插件、从源码编模板时才需要。
  - 实测：带 NDK 的完整安装 71 s，下载约 1.05 GB；精简版常驻 475 MB；再次运行 6 s。
  - cmdline-tools 钉在 19.0。22.0 以后的 sdkmanager 会转交给新的 "Android CLI"，后者往 `~/.android` 再下 250 MB，并有自己的使用统计开关（`--no-metrics`）；它的设置文件里写的是 `hasOptedIn:false`。
- 可选：
  - `WINE=1 bash tools/godot/setup-runtime.sh` 装 wine64（约 650 MB），用来冒烟测试 Windows 导出。
  - `SOURCE=1` 装 mingw-w64、lld、pkg-config，只有源码构建（后备）才用得到。
- 代理：
  - Java 工具（sdkmanager、Gradle）用的代理和证书已经由环境变量 `JAVA_TOOL_OPTIONS` 配好，不用另外设置。
  - Maven Central 曾返回过一次 429（Too Many Requests），重试即可，`build-templates.sh` 里已经写了重试。

## 3. 软件渲染试玩（Xvfb）

测试项目由 `tools/godot/make-test-project.py` 生成，不是游戏内容。它包含：

- 480×270 视口，`viewport` 拉伸，整数放大，`expand`。
- 带法线贴图的 CanvasTexture 精灵。
- PointLight2D 和 DirectionalLight2D，阴影由 LightOccluder2D 产生。
- TileMapLayer。
- 2D HDR 加辉光（WorldEnvironment 背景设为 Canvas）。
- 中日文 Label，以及禁则统计（见 §4）。
- 键盘和触摸输入、OGG 音效。

`tools/godot/xvfb-playtest.sh <项目或导出物> <输出目录> <渲染器>` 依次完成：

1. 启动 1280×720 的 Xvfb，开窗口运行游戏。
2. 用 xdotool 按住方向键、点击、拖动。
3. 保存引擎自己的视口截图（`get_viewport().get_texture().get_image()`）和整个 X 屏幕截图（`import -window root`）。
4. 汇总 FPS 和输入事件。

### 3.1 结果（1280×720 窗口，480×270 视口 ×2）

| 运行方式 | 渲染器 / 驱动 | 就绪时间 | 平均 FPS |
|---|---|---|---|
| 编辑器直接跑项目 | Forward+ / Vulkan（lavapipe） | 0.9 s（着色器缓存冷时 2.3 s） | 35.7–37.0 |
| 同上 | Mobile / Vulkan（lavapipe） | 0.7–1.0 s | 47.0–63.8 |
| 同上 | Compatibility / OpenGL 4.5（llvmpipe） | 0.5–1.1 s | 57.5–60.7 |
| 导出的 Linux release | Forward+ | 0.7 s | 38.9–44.0 |
| 导出的 Windows release（wine） | Compatibility / Forward+ | 2.0 / 2.9 s | 54.3 / 45.4 |

FPS 是关掉垂直同步、去掉前 3 s 后的平均值。测量时容器里另有一个进程（别的代理）一直占着约 1 个核，两次测量之间相差可达 25%，所以只看量级。Compatibility 会报一条 "Could not set V-Sync mode"，无害。容器没有声卡，音频自动退回 dummy 驱动；OGG 的播放调用没有报错，但**没有听到声音**。

### 3.2 真实输入路径（XTEST）

xdotool 不带 `--window` 时走 XTEST 扩展：X 服务器把它当作物理键盘、鼠标，和 XSendEvent 发的合成事件不同。三个渲染器、导出的 Linux 版、wine 下的 Windows 版结果都一样（wine 下窗口是 1280×698，坐标略有偏移）：

- 按住 → 键 1.5 s，精灵右移 121 px（预期 80 px/s × 1.5 s = 120）。
- 窗口坐标 (300,300) 点一下：开启 `input_devices/pointing/emulate_touch_from_mouse` 后，游戏收到 `InputEventScreenTouch`，位置 (70,105)，然后走到该点。
- 按住左键拖动，每次移动 20 窗口像素：游戏收到 `InputEventScreenDrag`，rel = 10（×2 放大），精灵跟着移动 40 px。
- 同时也会收到普通的鼠标事件。手机上的真实触摸**没有**测过（见 §9）。

### 3.3 截图的两个坑

- 开启 2D HDR 时，Forward+ 和 Mobile 的 `get_viewport().get_texture().get_image()` 拿到的是**线性**值（半浮点）。直接存 PNG 会偏暗：实测 (8.8, 14.5, 4.6)，屏幕上是 sRGB (53.5, 67.8, 38.0)。要逐像素 `Color.linear_to_srgb()`；`Image.linear_to_srgb()` 只接受 8 位数据，暗部会出色阶。Compatibility 返回的本来就是 sRGB，不能再转。修正后，三个渲染器的截图和 X 屏幕截图平均值相差都不超过 0.6/255。
- release 导出版的 stdout 在重定向到文件时是块缓冲（`application/run/flush_stdout_on_print` 默认关，只有 `.debug` 默认开）。自动化测试要么在项目里打开它，要么像脚本那样以"窗口出现"为准。

### 3.4 2D 功能在三个渲染器下的差异

- **Forward+ 和 Mobile**：法线贴图光照、点光和平行光的阴影、TileMap、文字完全一致，屏幕截图平均差 < 1/255。差别只在辉光（下一条）。
- **辉光**：三个渲染器都有，但样子不同。
  - 单独测试：一个 HDR ×8 的光点，辉光强度 2，bloom 0.5。光点周围一圈的平均亮度：Forward+ 195.9（大而暖的光晕），Mobile 167.5（核更紧，外晕更淡、偏黄绿，背景更暗），Compatibility 106.5（很小的光晕）。没有 HDR 的同样光点周围是 43–54。
  - 正式场景里，光点被 CanvasModulate 压到亮度约 1.4，只比阈值 1.0 高一点：**只有 Mobile 出光晕，Forward+ 和 Compatibility 都没有**。
  - 结论：Windows（Forward+）和 Android（Mobile）用同一个 Environment 会不一致。要么按渲染器分别调辉光参数（运行时看 `RenderingServer.get_current_rendering_method()` 选 Environment），要么两个平台都用 Mobile 渲染器（桌面也支持）。这是会改变画面的决定，按协议要提案。
- **Compatibility（OpenGL）**：灯光衰减和颜色明显不同（灯下那片光更亮、更暖、更大），截图平均差约 10/255，有 1.4 万个像素差超过 24。HDR 截图返回 sRGB。**Android 设备不支持 Vulkan 时，Godot 会自动退回 Compatibility**（`rendering/rendering_device/fallback_to_opengl3` 默认开），画面会变成这样。
- `disable_3d=yes` 会连 `WorldEnvironment` 一起去掉：它在 `scene/register_scene_types.cpp` 的 `_3D_DISABLED` 段里注册。2D 辉光、色调映射、调色都靠它，所以 2D 游戏也**不能**关 3D。

## 4. 中日文文字

- 官方构建默认使用 Advanced 文本服务器（ICU / HarfBuzz / Graphite）。Noto Sans JP 子集字体能正确显示 ゞ、々。简体字（这、们、说）不在 JP 子集里，要把 SC 子集设为 `FontFile.fallbacks`，实测有效。共用的汉字会用日文字形（Han unification）：中文段落要换成 SC 字体，或用支持 `locl` 的 Pan-CJK 字体再设置 `language`（只有 Advanced 文本服务器支持）。
- **导出版要带 ICU 数据才能正确断行**：
  - 编辑器把数据编进了程序里，模板没有（`modules/text_server_adv/SCsub` 里模板用的是 `icudata_stub`）。
  - 打开 `internationalization/locale/include_text_server_data`（加入 ja/zh 翻译也会自动打开，见 `editor/export/editor_export_platform.cpp`）后，导出会从模板目录取 `icudt_godot.dat`，pck 增加 4.6 MiB（APK 里压缩后 2.8 MB）。日志里会打印 "Using text server data from export templates"。
  - 实测导出版和编辑器的断行结果完全相同。
- **禁则要设成严格**：`internationalization/locale/line_breaking_strictness = 3`（Strict）。测试样本是一段日文（含 ゝゞヽヾ々っゃゅょ），在 31 种宽度（60–240 px）下各断一次：
  - 默认（Auto/Normal）：小假名可以出现在行首，比如「所でニ｜ャーニャー」，31 次全部违规。
  - Strict + WORD：0 次违规；只有一段 9 个字连在一起不能断，在 60–90 px 这么窄时会超出边框。
  - Strict + WORD_SMART：超出边框的地方改成强行断开，所以那几处违规。150 px 时每一行都正确（「…所で｜ニャーニャー…」「「百々つゞみ」「家守さ｜ぢ」…」）。
  - ARBITRARY 不看规则，63 处行首违规、12 处行尾违规，不要用。
  - 对话框宽度正常时，Strict + WORD_SMART 就够了。
- 文字是在 480×270 里渲染再整数放大的，12 px 的中日文能读，但颗粒感强。要不要改成高分辨率 UI 层（SubViewport）或换像素字体，是以后的美术决定。

## 5. 导出（官方模板，`tools/godot/export.sh`）

`export.sh <项目> <预设名> <release|debug> <输出文件>` 先 `--import`，再 `--export-*`。耗时：导入 5 s，Linux 5 s，Windows 6–8 s，Android 12–14 s。

### 5.1 Linux
`GodotToolchainTest.x86_64` 70.1 MiB（就是模板本身）+ `.pck` 4.75 MiB（其中 ICU 数据 4.6 MiB）。在 Xvfb 下用真实输入跑通（§3.1）。

### 5.2 Windows
- release：`.exe` 104.1 MiB + `.pck` 4.75 MiB。
- `binary_format/embed_pck=true` 时只有一个 108.8 MiB 的 `.exe`。
- debug：`.exe` 98.3 MiB + `.console.exe` 控制台包装 + `.pck`。
- `application/modify_resources=true`（图标、版本信息）在 Linux 上直接生效，不需要 rcedit。
- 官方 Windows 模板包含 ANGLE 和 Direct3D 12。自己用 mingw 编译做不到，因为这两个 SDK 是 GitHub release 资源，被拦。
- wine 9.0 下的冒烟测试：
  - 默认设置下，`dinput8.dll` 刚加载就空指针崩溃（手柄初始化），两个渲染器都一样。
  - `WINEDLLOVERRIDES` 加上 `dinput8=d` 之后能启动、渲染、接收输入，Forward+ 走 winevulkan 到 lavapipe，FPS 见 §3.1。
  - 这很可能是旧版 wine 的问题。**真实 Windows 机器上还没有验证**，第一次交付前必须在用户的电脑上跑一次。

### 5.3 Android
- 预设：不用 Gradle 构建、只要 arm64-v8a、横屏、immersive。项目设置：`display/window/handheld/orientation=4`（Sensor Landscape）、`rendering_method.mobile="mobile"`。
- 导出前提：
  - 项目必须打开 `rendering/textures/vram_compression/import_etc2_astc`，即使全部是无损贴图，否则报错。
  - 要设置项目图标，否则报 "No project icon"（不致命）。
- 签名：
  - 默认用仓库里的 `tools/godot/android/debug.keystore`（别名 androiddebugkey，密码 android；按 Android 惯例这不是秘密）。
  - 通过 `GODOT_ANDROID_KEYSTORE_{DEBUG,RELEASE}_{PATH,USER,PASSWORD}` 环境变量指定（官方文档列出的变量）。
  - 固定一把调试密钥，是为了每个临时会话导出的 APK 都能在手机上覆盖安装：换了签名就得先卸载，存档会丢。正式发布要另建私钥，不进仓库，并做好备份。
- 编辑器第一次启动时，会把 SDK 路径写进 `~/.config/godot/editor_settings-4.7.tres`：有 `ANDROID_HOME` 就用它，否则写默认的 `~/Android/Sdk`。如果编辑器在 SDK 装好之前跑过一次，之后的导出会失败，所以 `export.sh` 每次都先修正这个路径。
- release APK 的检查结果（`tools/godot/check-apk.sh`，用 aapt2 和 apksigner）：
  - 大小 28.26 MiB；debug 版 29.81 MiB（加图标之前测的）。
  - 包名 `org.tengan.toolchaintest`，minSdk 24，targetSdk/compileSdk 36。
  - native-code 只有 `arm64-v8a`。官方模板里有 4 种 ABI，导出时只保留了选中的。
  - `screenOrientation=11`（userLandscape）。
  - `<meta-data org.godotengine.rendering.method = "mobile">`。
  - 有 `android.hardware.vulkan.level` 和 `vulkan.version 1.1` 两个 feature，都是 required=false：因为允许退回 OpenGL，没有 Vulkan 的手机也能装。
  - 最大的条目：`libgodot_android.so` 71.1 MB（压缩后 24.0 MB），classes.dex 5.1 MB，`assets/icudt_godot.dat` 4.8 MB。
  - 证书是 `CN=Android Debug`，SHA-256 `6ebfceb3…978306`。另有一个 `.idsig` 文件（v4 签名，安装时不需要）。
- 没有 KVM（没有 `/dev/kvm`，CPU 也没有 vmx/svm），模拟器跑不了。**APK 只验证了结构，没有在任何设备上运行过。**

## 6. 画面比例：480×270 整数放大

`viewport` 拉伸 + `integer` + `expand` 的实际表现：expand 只调整宽高比，不会把整数倍放大后剩下的像素填满。只有 1280×720 一行是实测（触摸坐标的 (160,90) 偏移和截图都证实了黑边），其余各行按同一规则推算【未验证】。

| 窗口 | 倍数 | 结果 |
|---|---|---|
| 1280×720 | ×2 | 画面 960×540，四周黑边（左右 160、上下 90） |
| 1920×1080 | ×4 | 正好填满 |
| 2560×1440 | ×5 | 2400×1350 + 黑边 |
| 20:9 手机，如 2400×1080 | ×4 | 视口自动扩成约 600×270，正好填满 |

想消掉黑边又不用小数倍：窗口大小变化时自己算 `scale = floor(min(w/480, h/270))`，再把 `get_tree().root.content_scale_size` 设成 `(w/scale, h/scale)`，让镜头多看一点世界【未验证】。这会改变玩家看到的范围，按协议要先提案。

## 7. 入库什么，每个会话重做什么

- **入库**：`tools/godot/` 里的脚本，以及调试密钥 `tools/godot/android/debug.keystore`（2.6 KB）。
- **不入库任何引擎二进制**。每个新会话跑 §2 的三个脚本：
  - 官方编辑器 + 模板 80 s（下载 1.3 GB，常驻 710 MB）。
  - 精简 Android SDK：首次约半分钟【估】，下载约 305 MiB（cmdline-tools 172.7、build-tools 61.2、platform 62.8、platform-tools 8.6）。
  - apt 约 20 s。
  - 合计约 2.5 分钟。要是嫌麻烦，可以写成 SessionStart hook（由主控决定）。
- 对照：官方编辑器 139.6 MiB，`xz -9` 后 61.5 MiB（用时 153 s；官方 zip 是 74.25 MiB），仍超过 GitHub 50 MB 的警告线；模板每个平台都在 70–120 MiB，进 git 会让历史越来越大，还会碰到单文件 100 MB 的上限。从官方站下载加校验，比提交二进制或每次编译都划算。

## 8. 源码构建（后备，默认不用）

只有将来要修改引擎时才用。以下只是记录，**都没有跑完过**：

- `build-editor.sh`：X11 + Vulkan + GL，其他驱动全关，`use_sowrap` 不需要任何 -dev 包，`production=yes lto=none scu_build=yes linker=lld`。实测进度：x11=no 那次 11.5 分钟编了 850 个单元后停下；x11=yes 那次 20.3 分钟时 SCU 单元编到 133/250 后停下（因为改用官方二进制）。整个编辑器按此推算约 40–50 分钟【估】。
- `build-templates.sh`：Linux、Windows（mingw，没有 ANGLE 和 D3D12）、Android arm64（要 `FULL=1` 的 NDK，以及 Gradle 8.11.1；Gradle 在 JDK 21 上配置成功，但没有正式构建）。**从未运行**，是未验证的草稿。
- 源码在 `/home/user/godotengine/godot`（浅克隆 17 s，438 MB），只用来查代码，可以删。

## 9. 风险与没验证的部分

1. **软件渲染的 FPS 不能用来估手机性能。** lavapipe/llvmpipe 是 CPU 光栅化，测到的是"这个场景在 4 核 CPU 上软件渲染的速度"，只能说明功能正常、画面正确、没有严重的 CPU 瓶颈。手机 GPU 的填充率、带宽、驱动 bug，以及 Mobile 渲染器的真实帧率都看不出来。另外，Godot 在没有 Vulkan 的手机上会退回 OpenGL，画面会变（§3.4）。需要知道用户手机的型号，并在真机上测：`adb install -r`，或从下载页安装。
2. 辉光在 Forward+ 和 Mobile 下样子不同（§3.4），两个平台的画面可能不一致。
3. Windows 版只在 wine 里跑过，而且要绕开 dinput8 的崩溃，**还没有在真实 Windows 上跑过**；手柄初始化在真机上是否正常也不知道。
4. APK 没有运行过：触摸、横屏切换、沉浸模式、存档路径、音频延迟都要真机验证。
5. 下载依赖 `downloads.godotengine.org` 和它跳转的存储地址；校验依赖 GitHub 上的 godot-builds（脚本里钉了一份校验值做后备）。如果官方改了网址，脚本会失败，并给出明确的报错。
6. 源码构建后备从没跑完（§8）。
7. 容器的磁盘和 CPU 被多个代理共用：可用空间在 17–23 GB 之间波动，FPS 也受其他进程影响。

## 10. 脚本索引（`tools/godot/`）

| 文件 | 用途 |
|---|---|
| `common.sh` | 公共设置：版本、路径、`GODOT_BIN`，以及修正编辑器设置里 Android 路径的函数 |
| `setup-runtime.sh` | apt 依赖（`WINE=1`、`SOURCE=1` 为可选项） |
| `setup-godot.sh` | 官方编辑器 + 模板，SHA512 校验，可反复运行 |
| `setup-android-sdk.sh` | 精简 Android SDK（`FULL=1` 加 NDK 和 CMake） |
| `make-test-project.py` | 生成测试项目（不是游戏内容） |
| `xvfb-playtest.sh` | Xvfb + 软件渲染 + XTEST 输入 + 两种截图；`.exe` 走 wine |
| `export.sh` | 无界面导出；处理 Android 签名和 SDK 路径 |
| `check-apk.sh` | 检查 APK 的大小、ABI、SDK 级别、方向、渲染器和签名 |
| `android/debug.keystore` | 固定的调试签名 |
| `build-editor.sh`、`build-templates.sh` | 源码构建（后备，默认不用） |
| `web/` | W-1：不再需要的 Web 方向草稿 |

## 11. W-1：Web 方向已做的工作（现在不需要）

2026-10-14 改为原生 Windows + Android 交付后，Web 导出不再需要。已做的部分留作参考；**以下关于 CSP 的结论只来自读源码，没有实测**。

- 装过 emsdk 4.0.11（本 tag 的 CI `.github/workflows/web_builds.yml` 钉的版本；`platform/web/detect.py` 要求 ≥4.0.0，closure compiler 要求 ≥4.0.11）。安装用了 56 s，占 1.7 GB，为腾磁盘已经删掉；`tools/godot/web/install-emsdk.sh` 一分钟可以重装。
- `tools/godot/web/build-web-template.sh` 和 `custom.py` **从没构建过**，是草稿。其中 `disable_3d=yes` 会去掉 WorldEnvironment（§3.4），重新启用前必须改。
- 读源码得到的要点【未验证】：
  - wasm 用 `fetch()` 取回，再交给 `WebAssembly.instantiateStreaming`（`platform/web/js/engine/config.js`）。CSP 必须允许 `script-src 'wasm-unsafe-eval'`（或 `'unsafe-eval'`）。这个 Promise 没有 catch：被拦时页面会停在进度条上，用户看不到任何报错。
  - `.wasm` 和 `.pck` 都用相对 URL 的 `fetch()` 取回，受 `connect-src` 管。两个 AudioWorklet 模块用 `audioWorklet.addModule(相对 URL)` 加载，受 `script-src` 管。
  - `threads=no` 时不需要 SharedArrayBuffer 和 COOP/COEP；只有开启 PWA 才注册 service worker；IndexedDB 不可用时会被捕获，只打印一条提示。
  - `Engine.preloadFile()` 接受 ArrayBuffer，所以 .pck 可以分片下载后拼接；.wasm 只能靠包装 `fetch` 来分片。
  - Fallback 文本服务器只在空白处（包括 U+200B）断行；Noto Sans CJK 子集里没有 U+200B 字形。
  - `brotli=no` 会连内置默认字体（OpenSans，存成 WOFF2）一起去掉。
- 参照：官方 4.7.2 的 `web_nothreads_release.zip` 压缩后 9.77 MiB。
