# 静态立绘的演出：漫符、立绘动作、对话框与文字（2026-10-16，G5R3-13）

用户否了立绘的眨眼和说话动嘴（G5R3-13），要求立绘保持静态，演出改用漫画符号和画面、对话框的动作，"按专业游戏美术参考动态漫画设计去丰富完善"。这一份是设计之前的研究：专业游戏和动态漫画怎么让静态立绘"演"，我们取什么、不取什么。设计提案在 `docs/design/dialogue-staging.md`（草案，待审）。

## 1. 结论先说

1. **静态立绘靠"拍子"演，不靠连续的动。** 每个拍子是一个短促、清楚的强调：一次弹跳、一下横抖、一个漫符弹出、一次闪白。拍子之间立绘静止，字照常读。
   - 逆转裁判的制作人说，早期作品帧数少，"异议あり！"的气泡只有一两种变化，反而得到了"别处得不到的速度感和利落感"；3D 重制时他们刻意打乱节奏、插入停顿来还原这种感觉。这一说法来自转述，原始采访未核实。
   - 动态漫画也是同一个路子：把画格放大成整屏，再加声音和少量动作。维基百科特别指出视觉小说"只偶尔"在画面里做局部动作。
2. **词汇要少而固定。** 星露谷的事件脚本只有几个演出词：
   - `emote`：头顶的小图标，有问号、怒、惊叹、心、睡、伤心、开心、×、"……"、音符、脸红；
   - `jump`：跳，带强度；
   - `shake`：抖，以毫秒计；
   - `screenFlash`：闪白，带强度。
   Ren'Py 的标准转场里，`hpunch`、`vpunch` 是横、竖震屏各四分之一秒，"闪光"是快速变白再回来。一个小而固定的词表，写剧本的人记得住，玩家也学得会。
3. **文字特效用"包住一段字"的标记。** Celeste 的对话文件在台词里直接写 `{~}波浪{/~}`、`{*}抖{/*}`、`{!}冲击{/!}`、`{big}大{/big}`、`{>> 0.5}慢速{>>}`、`{0.5}`（停半秒）；每句开头用 `[角色 左/右 表情]` 换立绘。Undertale 按说话人和情绪，偶尔给字的基线加波浪或抖动，并用打字速度当"嗓音"。我们的剧本标记照这个思路做，用中文写。
4. **漫符的意思和位置是约定俗成的，照约定用**（维基百科"漫画符号"条）：
   - 汗滴在额头或眉边（尴尬、无奈、困惑、慌）；
   - 怒筋是头上部一个空心的十字，多跳几下表示更生气；
   - 竖线阴影在头上或眼下（难堪、疲惫、恐惧）；
   - 红晕是脸颊的斜线；
   - 嘴角的虎牙或猫嘴表示调皮；
   - 头顶的"……"表示无话可说；
   - 人物周围粗黑的线表示气得、吓得发抖；
   - 集中线、速度线强调动作和情绪（Clip Studio 手册）。
   符号贴在约定的位置，不压五官。
5. **可读性和舒适度是硬约束，不是可选项。**
   - XAG 117 的要求：
     - 动的文字对阅读慢的人、对晕动敏感的人都是障碍；
     - 镜头震动应当避免，或者提供关闭选项；
     - 反复的左右、上下晃动，除非是玩法核心，也应当避免。
   - WCAG 2.3.1：任何一秒内闪烁不超过三次，或者闪烁面积和亮度变化低于阈值。
   - 所以我们要有"减少晃动"开关，闪白一句最多一次，抖动只给短短一段字。

## 2. 参考作品各学什么

| 作品 | 做法 | 我们取什么 | 出处 |
|---|---|---|---|
| Celeste | 台词内联标记：波浪、抖、冲击、大字、速度、停顿；每句指定立绘的边和表情 | 标记的写法（包住一段字、数字写秒）；换表情就是主要的"表演" | Everest wiki：Adding Custom Dialogue |
| 星露谷物语 | 事件脚本：`emote`（头顶图标）、`jump`、`shake`（毫秒）、`screenFlash`、`pause` | 小而固定的词表；图标挂在头的上方；节拍用毫秒 | Stardew Valley Wiki：Modding:Event data |
| Ren'Py（视觉小说引擎的通行做法） | `hpunch` / `vpunch` 震屏 0.25 秒；闪光 = 快速变白再回来；`move` 让换了位置的立绘滑过去 | 震屏的时长和强度量级；闪白的形状（快出慢回） | Ren'Py 文档：Transitions |
| Undertale / Deltarune | 按说话人和情绪，给字的基线加波浪或抖；打字速度当嗓音（某些角色的字明显更慢） | 抖字、波浪字只给一小段；打字速度是演出的一部分 | Fonts In Use 对 Undertale 字体的条目；Deltarune Wiki（Voice） |
| 逆转裁判 | 帧数少，靠节奏和停顿；"异议あり！"的气泡、拍桌、震屏、闪白 | 一次重拍（拍桌 = 震 + 闪 + 大字）只给全场最重的一句；平时靠停顿 | 制作人江城元秀的说法（osu! 论坛转述，原始采访未核实）；Dan Floyd 的视频分析 "The Animation of Phoenix Wright"。震屏和闪白的具体参数：观察，未找到出处 |
| 女神异闻录 5 | UI 当"图像娱乐"做，每个菜单是单独的程序；黑红白的斜框为了读得清反复调过 | UI 动势要以可读为前提：我们的对话框本身不变形，只在重拍时整体平移 | Kotaku 转述桥野桂的话；Famitsu 对美术总监须藤正喜的访谈（英文摘要） |
| Hades | 对话里用大幅插画立绘，入场滑入 | 入场滑入（整卡片平移，整像素） | Kotaku：The Art of Hades（立绘部分）；滑入是观察，未找到官方说明 |
| 漫画符号（漫符） | 汗、怒筋、竖线、红晕、虎牙、"……"、速度线、集中线、颤抖线 | 词表和位置约定 | 维基百科：Manga iconography；Clip Studio 手册：Speed lines and Focus lines |
| 动态漫画 | 画格放大成整屏，加声音和少量动作；视觉小说只偶尔做局部动作 | 卡片当"画格"：动作作用在整格上，不扭曲画面 | 维基百科：Motion comic |
| 弹丸论破、火焰纹章、东方 Project、Eastward | 立绘跳动、换表情、头顶表情符号 | 只作印象参考 | 观察，本次没有找到可引用的出处，不作依据 |

## 3. 由此定下的约束（写设计时照这些）

- **只用整像素平移**：原生 640×360 下以 1 像素为单位，在 1080p 下就是 3 屏幕像素。不旋转、不缩放、不模糊，像素格永远完整；这也是宪章"不做小数倍缩放"的延伸。
- **幅度和时长**：
  - 抖、震：1–3 原生像素，约 0.25 秒（Ren'Py 的量级）。
  - 跳：2 原生像素。
  - 闪白：一句最多一次，0.1–0.2 秒内回落；任何一秒内不超过三次（WCAG 2.3.1）。
- **字永远读得清**：
  - 对话框和正文只在重拍时整体平移一下，平时不动。
  - 抖字只给几个字；打完字后就停，不让一整句一直抖（XAG 117）。
  - 没有更小的像素字号，Fusion Pixel 12px 已是最小，所以低声用变淡，不用缩小。
  - 大字用整数倍（24px），保持像素字形。
- **立绘永远不挡字（F-3）**：卡片的平移幅度要留在卡片和正文之间的 8 像素空隙里。
- **漫符**：
  - 每个拍子最多一个新漫符。
  - 贴在约定的位置：额头、太阳穴、头顶、脸颊，头旁边的卡片底色上；不压五官。
  - 第四版已经画进立绘的符号（惊讶的"！"、大喊的"！！"、生气的怒筋、怀疑的问号、思考的泡泡、嘟嘴的"哼"、疲惫的汗）保持不动；新漫符是独立的小图，风格和它们一致：深色描边、同一套色。
- **"减少晃动"开关**：
  - 关掉一切位移和闪白：滑入、弹、抖、震、抖字、波浪字。
  - 漫符照常出现，但没有动画（直接显示最后一帧）。
  - 大字、变淡、停顿保留：它们不是动作。

## 4. 未核实

- 逆转裁判的震屏、闪白参数，Celeste 换表情时的小弹跳，Hades 的滑入：都是看游戏的印象，没有找到官方说明。
- 江城元秀那段话只见于论坛转述。
- 女神异闻录 5 的采访只读到英文摘要。

## 出处

- Everest（Celeste 模组工具）wiki，Adding Custom Dialogue：<https://github.com/EverestAPI/Resources/wiki/Adding-Custom-Dialogue>
- Stardew Valley Wiki，Modding:Event data：<https://stardewvalleywiki.com/Modding:Event_data>
- Ren'Py 文档，Transitions：<https://www.renpy.org/doc/html/transitions.html>
- Fonts In Use，Undertale dialogue and interfaces：<https://fontsinuse.com/uses/51307/undertale-dialogue-and-interfaces>；Deltarune Wiki，Voice：<https://deltarune.fandom.com/wiki/Voice>
- 逆转裁判：osu! 论坛对江城元秀采访的转述 <https://osu.ppy.sh/community/forums/posts/1835224>；Dan Floyd，The Animation of Phoenix Wright：<https://amara.org/videos/ojQ3BHqKKYoA/info/the-animation-of-phoenix-wright>
- 女神异闻录 5：Kotaku <https://kotaku.com/-metaphor-refantazio-persona-5-menu-ui-hashino-1851667088>；SEGAbits 对 Famitsu 访谈的摘要 <https://segabits.com/?p=54918>
- Hades：Kotaku，The Art of Hades：<https://kotaku.com/the-art-of-hades-1845443438>
- 维基百科，Manga iconography：<https://en.wikipedia.org/wiki/Manga_iconography>；Motion comic：<https://en.wikipedia.org/wiki/Motion_comic>
- Clip Studio Paint 手册，Speed lines and Focus lines：<https://help.clip-studio.com/en-us/manual_en/540_comic/Speed_lines_and_Focus_lines.htm>
- Xbox Accessibility Guideline 117：<https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/117>
- WCAG 2.2，Understanding 2.3.1 Three Flashes or Below Threshold：<https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html>
- 震屏的手感与"创伤值"：见 `02-readability-feel-controls.md` 第 9、11 条（Juice It or Lose It；Nijman；Eiserloh）。
