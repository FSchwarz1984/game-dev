---
name: design-proposal
description: Prepare a key design decision for the user's approval before implementing it — characters, story, world, map layout, core mechanics, art direction, title, scope, or anything that changes what the player sees or does. Also use to record the user's answer in the decision log afterwards.
---

# 设计提案与审批

用户明确要求：关键问题要先讨论、经审核允许，不要一个人闷头莽撞（见 `docs/knowledge/05-v0.1-postmortem.md`）。这个技能规定提案怎么写、答复怎么记。

## 先检查

1. 读 `docs/decisions/decision-log.md`。已批准的决定不重新争论；新提案必须与它们一致，冲突时明确指出冲突并请用户裁决。
2. 读 `docs/decisions/pending.md`，避免重复提案。
3. 需要依据时，先查 `docs/knowledge/`；不够再做研究，研究结论写回知识库并附出处。

## 每个决定的写法

- **问题**：一句话说清要决定什么。
- **选项**：2–4 个，彼此真正不同。
- **推荐**：明确选一个，不平均陈列。
- **关键变量**：真正决定选择的那几个因素。
- **代价与风险**：推荐方案的主要代价。
- **什么情况下选别的**。
- **请你决定**：用户可以只回复编号和"同意 / 改成… / 否"。

用户的偏好：正式、直接、该批评就批评；发现用户的想法有结构性问题（范围爆炸、互相矛盾、与已批准决定冲突、与竞品高度重叠）要明说，具体指出问题在哪里。

## 交付形式

- 多个决定一起提交时，做成一个评审页面（Artifact，HTML），每个决定一块，盖"待審"朱印；末尾附编号审批清单。
- 页面链接登记到 `docs/design/README.md`；条目写进 `docs/decisions/pending.md`。
- 单个小决定可以直接在对话里问。

## 收到答复之后

1. 把每条答复按原话（或忠实的概括）写进 `decision-log.md`，注明日期。
2. 从 `pending.md` 删除已决条目；用户提出的新要求如果需要再提案，留在 `pending.md`。
3. 更新 `docs/design/` 里对应文档的状态行（草案 → 已批准）。
4. 提交并推送。

## 不要做

- 不要在用户批准前实施内容层面的决定（角色、剧情、地图、玩法规则、美术方向、名字）。技术实现细节可以自行决定，但要在汇报里说明。
- 不要把"用户给了方向"当成"用户批准了所有细节"。
