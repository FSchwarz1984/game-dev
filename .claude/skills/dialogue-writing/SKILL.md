---
name: dialogue-writing
description: Rules for writing any in-game text for this project — dialogue, barks, item descriptions, cutscene lines, UI copy. Use whenever writing or revising lines so they read like an award-level Japanese light novel and never like AI output.
---

# 台词守则

用户的要求：电影动画式的演出；日式轻小说大奖作品的节奏和幽默感；尽可能避免 AI 味。v0.1 的演出与台词是用户认可的部分，保持那个方向。

## 硬规则

1. **不解释情绪。** 写动作、写具体的东西，让读者自己得出情绪。
2. **不用对仗和排比**，不用"不是……而是……"，不用"这不仅是……更是……"，不用总结式的收尾句。
3. **每个角色有固定的说话指纹：** 自称、句子长短、口头禅、对别人的称呼、什么时候用敬语。指纹写在 `docs/design/characters.md`，写台词前先查。
4. **笑点靠节奏和反差，最后半句落地。** 不靠吐槽式旁白，不靠解释笑点。
5. **每段对话至少有一个只属于这个世界的具体细节：** 地名、物件、民俗、季节、性质（重熱光音生）。
6. **台词要服务于玩法或谜：** 一句台词要么让玩家知道能做什么，要么推进人物，要么留下一个具体的谜。三者都不沾的删掉。
7. **短。** 一个对话框不超过两行；一段对话超过六个来回就要有动作或镜头切换打断。

## 演出

- 镜头、停顿、字幕卡、远景镜头，沿用 v0.1 的电影感。
- 关键场景先写分镜（镜头 → 动作 → 台词 → 停顿），再写台词。

## 自查

写完后逐句检查：有没有一句话能在任何别的游戏里原样出现？有就改到只属于这个世界为止。
