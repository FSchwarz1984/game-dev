---
name: playtest-capture
description: Run the game headless in Chromium, drive input frame-synchronously, capture screenshots or timed sequences, and check readability, character flicker, phone layouts and console errors. Use to verify any visual or gameplay change before reporting it to the user.
---

# 无头试玩与截图验证

汇报任何视觉或玩法改动之前，必须亲眼看过截图。v0.1 的很多问题（闪烁、乱码、看不清）都是在用户那里才被发现的。

## 环境

- Playwright 已全局安装：`import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs'`。
- 浏览器在 `/opt/pw-browsers`，不要运行 `playwright install`。
- WebGL 需要这些参数：`--use-angle=swiftshader --enable-unsafe-swiftshader --ignore-gpu-blocklist`；要测声音再加 `--autoplay-policy=no-user-gesture-required`。
- 用 Node 自带的 `http` 起一个静态服务器（每个脚本一个端口），不要依赖外部服务。
- 测试脚本放在会话的 scratchpad 目录，不放进仓库，除非它值得长期保留（那就放 `tools/`）。

## 方法

1. **等待就绪：** 游戏在初始化完成后设置 `window.DONE = true`（新引擎也必须保留这个约定）。
2. **帧同步输入：** swiftshader 很慢（个位数帧率），按毫秒等待会漏帧。给主循环挂一个计数器，按帧等待：
   ```js
   await p.evaluate(() => { window.__fr = 0; const o = APP.tick.bind(APP); APP.tick = dt => { window.__fr++; return o(dt); }; });
   const frames = async n => { const f0 = await p.evaluate(() => __fr); await p.waitForFunction(t => __fr >= t, f0 + n); };
   const press = async code => { await p.keyboard.down(code); await frames(2); await p.keyboard.up(code); await frames(3); };
   ```
3. **调试参数**（新引擎沿用）：`?skip=` 跳到某个场景，`?auto=1` 自动推进对话，`?speed=N` 时间加速，`?t=` 指定时刻，`?frames=N` 限制每帧工作量。
4. **序列截图：** 隔固定间隔截图并打印游戏状态（阶段、对话、玩家状态），把关键帧读出来亲眼看。
5. **闪烁检查：** 角色静止时连续截 8 帧，统计角色包围盒内每帧变化超过阈值的像素比例，并与附近地面对比。注意待机动画、风摆、胶片颗粒都会计入，要做对照实验（逐项关闭）才能下结论。
6. **手机视口：** 至少测 390×844（竖）和 844×390（横）；检查横向溢出（`scrollWidth > clientWidth`）、按钮大小（≥48dp）、文字是否被遮挡。
7. **构建产物也要测：** 单文件和 Artifact 版本（body-only）都要打开测一遍；Artifact 版本必须是纯 ASCII，在没有 charset 的情况下也不能乱码。

## 坑

- 不要同时开三个以上 swiftshader 实例：每个都会被饿到几帧，等待条件会超时。
- 未关闭的对话会挡住输入，测试时用 `?auto=1`。
- `pkill -f chromium` 可能误杀；按脚本名杀进程。
- 测量结论要写清局限，不要把一次截图当成"已验证"。

## 每次汇报前的检查表

- [ ] 控制台没有错误
- [ ] 角色在亮处、暗处、树影下、夜晚都看得清，不闪
- [ ] 当前可交互目标有世界内高亮
- [ ] 手机竖屏和横屏都能操作，无横向溢出
- [ ] 单文件构建和 Artifact 版本都能打开
