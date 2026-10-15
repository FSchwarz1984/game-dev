# 设计文档索引

每个文件顶部有状态行：**草案**（待审批）或**已批准**（日期）。实施只能依据已批准的内容。

## 评审页面

| 日期 | 关口 | 链接 | 状态 |
|---|---|---|---|
| 2026-10-14 | G0 方向评审 | <https://claude.ai/artifact/QRVQFsHfKNPYrzGwnwVRkt> | 已批准（答复见 decision-log.md） |
| 2026-10-14 | G1 角色与故事 + G2 新手区地图 | <https://claude.ai/artifact/1u2fAfNyZTDjVUj3RfRKr3> | 已答复：G2 通过；G1 部分通过（见 decision-log.md） |
| 2026-10-14 | G1 第二轮：宇宙观、主角真身、シオン、名字、作品名 | <https://claude.ai/artifact/3cvHsMaeU9aTw9gb26Lj8D> | 已答复：宇宙观"还行但要更复杂"；真身、名字、作品名被否决（见 decision-log.md） |
| 2026-10-14 | G1 第三轮：世界观三选一、真身、名字、作品名（按类型） | <https://claude.ai/artifact/WhsgJ2hB6q27ftCNVDXhc7> | 已答复：全部否决，改为采用第二轮（见 decision-log.md G1R3） |
| 2026-10-14 | G3 可玩灰盒（技术预览） | <https://claude.ai/artifact/Q2VsSTbbjBM6nMqUMbJqJJ> | 已撤回（P-1：只交付成品），不再更新 |
| 2026-10-14 | G5 第一段成品：标题、序章「送魂夜」、第一天早上 | <https://claude.ai/artifact/We1nnVFD9GUdcWUT78uKaa> | 已交付，用户已答复（E-1 迁移 Godot、R-1…R-8、F-1…F-3） |
| 2026-10-14 | G5 开工前评审：身体材质、「移」的规则、操作、地图、小地图、美术标杆、立绘、字体、剧本语气、授权（十个决定） | <https://claude.ai/artifact/QcemFFSjDfjdyJR93yCtUw> | 已答复（decision-log G5R-1…10）：菅笠、地图迷雾、样章、像素字、授权通过；名字、「移」、操作、地图、立绘、剧本要重做 |
| 2026-10-15 | G5 第二轮评审：美术样章（3D 场景按像素画渲染）、第三版立绘、精灵图（R-4）、远景灯火（R-8）、主角的名、「移」v2、操作 v2、地图 v3、剧本第三版、两件小事（十个决定） | <https://claude.ai/artifact/PD8KPonn2V7QhQPPEtr9Gm> | 已答复（decision-log G5R2-1…11）：路线继续但大改；名 A、「移」v2、操作、地图通过；立绘、人物模型、剧本要重做 |
| 2026-10-15 | 立绘与 3D 人物模型的素材清单（给用户用 ChatGPT 生成；含可复制的提示词） | <https://claude.ai/artifact/1oFkdMqddgN7Y3CmxSAGvX> | 等用户发回素材 |

## 文档

| 文件 | 内容 | 状态 |
|---|---|---|
| [title.md](title.md) | 作品名 | 四轮被否决，仍未定 |
| [characters.md](characters.md) | 三位角色：姓名、表面与隐藏身份、派蒙位、说话指纹、登场节拍 | 设定已采用（第二轮）；人名第四版微调待确认 |
| [story.md](story.md)（[cosmology.svg](cosmology.svg)） | 宇宙观 v3「天岸」、序章、新手区剧情、谜线、季节与章节 | 宇宙观 v3 已采用 |
| [systems.md](systems.md) | 「移」与五性、百鬼队、城镇建设、作物、杀或平息、一天、操作 | 已批准 |
| [map.md](map.md)（[map-v2.svg](map-v2.svg)） | 新手区地图 v2 | 已批准 |
| [scope-g5.md](scope-g5.md) | G5 垂直切片的范围 | 已批准 |
| [g3-graybox.md](g3-graybox.md) | G3 可玩灰盒：站点、操作、要验证什么 | 技术预览（不是设计决定） |
| [godot-plan.md](godot-plan.md) | Godot 迁移计划：架构、阶段 P0–P6、八个问题的修法 | 执行中（迁移是用户的决定 E-1） |
| [body-effects-draft.md](body-effects-draft.md) | 「移」的身体效果：菅笠之身、三档、容量与回流、操作 | 已答复：菅笠通过；三档和容量被否（G5R-1、G5R-2） |
| [map-v3-draft.md](map-v3-draft.md) | 地图 v3（= v2 + F-1，平台加崖）与小地图解锁 | 已否（G5R-4、G5R-5），留作对照 |
| [script-02-draft.md](script-02-draft.md) | 开场剧本第二版 | 已否（G5R-9），留作反例 |
| [name-protagonist-draft.md](name-protagonist-draft.md) | 主角的名：百々かさゝぎ / あやゐ / かさね | 已批准 A（G5R2-5） |
| [yi-v2-draft.md](yi-v2-draft.md) | 「移」v2：以效果为中心，没有数字；梁与背负子的教学 | 先照此做（G5R2-6），技术美术稳定后再推敲 |
| [controls-v2-draft.md](controls-v2-draft.md) | 操作 v2：先指后做，鼠标、手柄、触屏的精确指向 | 已批准（G5R2-7）；触屏随安卓一起放弃 |
| [map-v3-natural-draft.md](map-v3-natural-draft.md) | 地图 v3（自然地形）：好奇点三层、不靠镜头的引导、迷雾小地图 | 基本通过（G5R2-8）；加：自然地爬上大楠、神社一带的结界（G5R2-1） |
| [script-03-draft.md](script-03-draft.md) | 开场剧本第三版（含场景事实表、症状结构、盲审对照） | 仍有 AI 味、缺幽默（G5R2-9），要写第四版 |
| [script-04-draft.md](script-04-draft.md) | 开场剧本第四版：七十岁的婆婆、乌鸦和收音机、谈钱三次而第三次翻过来、追乌鸦爬树 | 草案，盲审中，进下一轮评审页 |
| [realm-and-climb-draft.md](realm-and-climb-draft.md) | 结界怎么进（推荐提灯）、烂柯先做成看得见的东西、序章追乌鸦爬上大楠 | 草案，进下一轮评审页 |
