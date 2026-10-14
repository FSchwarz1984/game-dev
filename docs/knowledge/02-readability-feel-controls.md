# 02 可读性、手感、目标选取与手机操作

研究日期：2026-10-14。"推论"表示我们自己的建议，不是来源的原话。

## 1. 画面可读性

1. **先定读取层级，先明度后色相。** TF2 的"读取层级"：阵营色 → 职业剪影 → 武器，"胸口高度对比最强"；用轮廓高光而不是黑描边。<https://cdn.steamstatic.com/apps/valve/2008/GDC2008_StylizationWithAPurpose_TF2.pdf> 本项目层级：角色 > 可交互物与威胁 > 地面 > 植被。
2. **角色要免受环境光的伤害。** TF2 把"极亮和极暗"留给边缘和高光，让角色"在困难的光照下也清晰可辨"；角色离开光源时加专门的轮廓光项。<https://www.cs.princeton.edu/courses/archive/fall07/cos597B/papers/mitchell-team-fortress.pdf> 推论：角色在自己的光照层上，带保底亮度和轮廓光；树叶影子对地面全强度、对角色只弱作用；影子运动要慢、低频、对齐像素。
3. **光照从第一天就设计进去，并用来引导视线。** 星之海：所有素材"都要满足动态光照的技术需求"。<https://mobilesyrup.com/2023/09/11/sea-of-stars-level-design-sabotage-studio-thierry-boulanger-interview/> 风来之国（Pixpil）"用光引导玩家的视线"。<https://www.gcores.com/articles/17339>
4. **剪影和小尺寸下的辨识度优先。** Hyper Light Drifter 的 Alx Preston 最在意颜色和剪影，低分辨率下也要好认。<https://automaton-media.com/articles/interviewsjp/20170525-47328/>
5. **调色板要有纪律。** HLD"每个环境用一套鲜明而特定的调色板来突出地标"。<https://www.gameinformer.com/games/hyper_light_drifter/b/pc/archive/2014/03/14/developer-covers-key-aspects-hyper-light-drifter.aspx> 八方旅人早期"分辨率和饱和度做过了头，失去了像素画的魅力"。<https://www.siliconera.com/project-octopath-traveler-developers-answer-project-started-troubles-developing-hd-2d/>
6. **高度要可读。** CrossCode 团队的新作说"3D 有助于透视"。
7. **可交互物要有专属信号，加上运动和声音。** 星露谷的淘金点是"闪烁的光"加掉进水里的声音；镜之边缘用与冷白世界对比的颜色；王国之泪给魔法物件日常形态，让人一眼认出；原神的元素视野把大多数非交互物压暗、只高亮可交互物。反例提醒：Control Resonant 的总监避免"黄色油漆"以保留玩家的自主。
8. **植被成团、留白，用变体藏重复。** Slynyrd：单一草地图块"会单调"；平坦区与纹理区交替，留白"帮助降噪"；"关键团块不要相互接触"；繁复纹理不要挨着繁复纹理，颜色要少。<https://slynyrd.com/blog/2019/8/27/pixelblog-20-top-down-tiles> 推论：植被的明度范围比玩法层窄。

## 2. 反馈与手感

9. **每个输入都立刻在多个通道上得到回应。** "Juice It or Lose It"（2012）<https://www.youtube.com/watch?v=Fy0aCDmgnxg>；Swink 把打磨定义为"动画、声音、特效与输入驱动运动的和谐所造成的物理感"，并警告它是"出了名的时间黑洞"。<https://www.gamedeveloper.com/design/game-feel-the-secret-ingredient> "The Art of Screenshake"（Nijman 2013）。
10. **命中停顿按力度加长，但有上限**（樱井政博）：双方都停；越强停越久，但有上限；被打者在地面左右抖、空中上下抖并衰减；镜头越远抖得越强。<https://sourcegaming.info/2015/11/11/thoughts-on-hitstop-sakurais-famitsu-column-vol-490-1/>
11. **屏幕震动用"创伤值"驱动**（Eiserloh，GDC 2016）：0–1 并衰减，震动量 = 创伤值²，用噪声驱动，位移和角度有上限。<https://www.youtube.com/watch?v=tu-Qe66AvtY>
12. **隐藏状态显示在视线已经在的地方，只在相关时出现。** 旷野之息的体力环只在相关时出现，亮绿色、就在林克旁边；UI 团队的目标是"不出现更好的 UI"；动作提示做成单色剪影，不抢视线；UI 只放左上和右下。<https://www.famitsu.com/news/201709/04141037.html>
13. **法术动词：预览 → 施放 → 可见状态 → 可预测的结果 → 回报。** 静止器把目标染成发光的黄色，用黄色箭头预告方向，用计时条显示冷却。<https://zeldawiki.wiki/wiki/Stasis> 推论：施法前高亮目标，资源条放在施法者身上。

## 3. 目标选取

14. **永远不要求像素级的朝向。** 动森被批评："角度差一点就拿错东西"，并且"事先看不出角色会去拿哪个"。<https://www.analogstickgaming.com/game-reviews/2020/4/4/animal-crossing-new-horizons>
15. **对候选打分，不取第一个命中。** 推论：在半径和朝向锥内，按距离、与朝向或摇杆方向的夹角、类型优先级（对话 > 拾取 > 道具）打分。Meta 的交互规范用锥形投射，并把射线"弯向最近的有效目标"。<https://developers.meta.com/horizon/design/grab_specs/>
16. **按键之前就显示选中的目标。** 星露谷有"手柄放置格指示器"，工具影响的格子有红框。<https://stardewvalleywiki.com/Options>
17. **加滞回。** Meta 的开始与停止阈值"不同（这叫滞回）"，锥内目标要持续 100 毫秒才成为候选。
18. **宽容，并提供明确的选择。** 蔚蓝的转角修正会"把你往旁边挪一下绕过去"，离墙 2 像素也能蹬墙跳。<https://maddymakesgames.com/articles/celeste_and_forgiveness/index.html> 目标重叠时允许切换；触屏直接点击。

## 4. 手机与触屏

19. **左侧浮动摇杆，右侧直接拖动镜头。** Apple："把摇杆显示在玩家拇指落下的任何地方"，"用直接触摸来平移镜头"。<https://developer.apple.com/design/human-interface-guidelines/game-controls>
20. **尺寸与间距。** Apple：常用控件至少 44×44 pt，次要的至少 28×28 pt。Google：至少 48×48 dp，间隔 8 dp。<https://developer.apple.com/design/human-interface-guidelines/accessibility> · <https://support.google.com/accessibility/android/answer/7101858>
21. **一个情境按钮，配可读的图标。** Apple："把功能合并进单一控件"，隐藏不可用的控件；用符号而不是 A/X/R1；按下时的光"即使手指盖住控件也看得见"，并配声音和触觉。星露谷的单键方案：短按（小于 0.25 秒）用工具，长按执行动作。<https://stardewvalleywiki.com/Mobile_Controls>
22. **让触摸直接作用于世界，并提供替代方案。** Apple 建议"让玩家点物体来选中它"。星露谷手机版点石头或树会自动选工具，点 NPC 会走过去互动；有些精细操作默认方案做不到，所以提供摇杆方案。
23. **自动选取，加手动覆盖。** 激斗峡谷的点击施法"遵循常规优先级"，并有可选的目标锁定过滤。
24. **输入越少越好。** Alto's Odyssey："任何新的触控输入几乎立刻让游戏变得手忙脚乱。"<https://apps.apple.com/cd/mac/story/id1499737138>
25. **拇指可达：常用操作靠近拇指，菜单放上方。** Hoober 后来收回了自己的可达区示意图："人们会点屏幕中央。"要在真机上测。<https://www.uxmatters.com/mt/archives/2013/02/how-do-users-really-hold-mobile-devices.php>

未证实或未找到：原神的交互列表与自动选取、Dave the Diver 的目标选取、旷野之息如何决定作用对象、星露谷/风来之国/八方旅人的描边做法、八方旅人的光照细节；没有找到已上市游戏关于交互目标打分的演讲。
