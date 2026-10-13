# ツヅラ —遠囃子—（TSUZURA: The Far Festival）

像素风开放世界 · 运输开拓 × 据点经营。第一次开发版本（v0.1）：**序章 + 九十九折峠的第一天**。

> 一只背着家走路的貂妖，在“距离”坏掉的世界里，用脚把远处走回近处。

- 设计文档：[`docs/DESIGN.md`](docs/DESIGN.md)（世界观、主角、核心系统、对旧 demo 的诊断与扬弃、技术美术、路线图、风险）
- 可直接游玩的单文件：[`dist/tsuzura.html`](dist/tsuzura.html)（用 Chrome / Edge / Safari 17+ 打开即可，需要 WebGL2）

## 操作

| 键盘 | 手柄 | 作用 |
|---|---|---|
| WASD / 方向键 | 左摇杆 | 走 |
| Shift | LB / RB | 奔跑（消耗体力，货堆更容易晃） |
| E / F | A | 背起 · 调查 · 把材料献给祠 |
| Q | B | 放下最上面的东西（站在籠丸旁边：放进它的箱子） |
| J | X | **取**：把面前东西的重量吸进尾巴；面前没有东西时，从背上最重的货物里取 |
| K | Y | **予**：把尾巴里的重量交给面前的东西 |
| Esc / P | Start | 暂停与说明 |

触屏：左半屏浮动摇杆，右下角按钮。

## 开发

全部美术（像素精灵、法线、地形纹理）与全部声音（环境、音乐、遠囃子、音效）都在运行时由代码生成，没有任何外部资源文件。

```
index.html          开发入口（逐个加载 src/*.js；需要本地静态服务器，例如 npx serve .）
src/core.js         数学、噪声、色相偏移色带
src/input.js        键盘 / 手柄 / 触屏
src/gl.js           WebGL2 工具
src/pixel.js        程序化像素美术工具：精灵缓冲（颜色/高度/材质/凸起）、法线、描边、图集
src/art_*.js        植物、道具、角色（葛笼、籠丸、对话立绘）
src/shaders.js      2.5D 延迟像素管线的全部着色器
src/render.js       渲染器（阴影图、G-buffer、光照、水、远化幽灵、粒子、bloom、合成）与昼夜表
src/world.js        九十九折峠的地形、水系、材质、植被与道具布置
src/audio.js        全合成音频引擎
src/fx.js           粒子与环境生命
src/entities.js     物件、供品、祠、石灯笼、幽灵、动物、籠丸
src/player.js       葛笼：行走、货堆、重的取予、石化与叶化
src/systems.js      路与近（NEARMAP）、时间天气、交付、存档
src/ui.js           对话、字幕、气泡、HUD、提示、标题
src/story.js        序章、苏醒、首日事件、全部台词
src/vista.js        侧视远景镜头（标题、树顶、眺望岩）
src/main.js         启动、主循环、镜头
tools/build.mjs     打包为单文件：node tools/build.mjs → dist/
```

调试参数（开发用）：`?skip=free&t=9` 直接进入自由探索；`?skip=new&from=vista` 跳到序章远景；`?auto=1` 自动推进对话；`?speed=3` 时间加速。
