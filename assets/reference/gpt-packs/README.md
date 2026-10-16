# 用户用 ChatGPT 生成的素材（素材清单第一版、第二版）

用户在第三轮评审答复里给的（G5R3），放在 Google Drive：
<https://drive.google.com/drive/folders/1kE4h9EG5Hww3DF-6HYyN8CFTqi0-cuar>。四个压缩包都不进 git（约 960 MB）；用下面这条命令取回、校验 SHA-256、安全解压：

```sh
bash tools/assets/fetch_gpt_assets.sh <输出目录>          # 两个成品包（约 270 MB）
bash tools/assets/fetch_gpt_assets.sh <输出目录> all      # 再加两个来源包（生成记录、raw、提示词）
```

压缩包是外来数据：每个解压到自己的空目录；来源包里有 .py、.js、.html，**一律不运行**。

## 内容

| 包 | 内容 |
|---|---|
| 第二版成品 `Tiangan_v2_84_final.zip` | 60 张立绘（每人 20 种表情，1024×1536，笠顶到腰，四分之三朝画面右；按用户的意思**不强制露眉**，刘海照原画）；しをね 马尾搭在肩前的平常、微笑两张；建模设定 17 张；概念 5 张 |
| 第一版成品 `Tiangan_supplement_100_finished.zip` | 78 张胸像（每人 26 张，1408×1408，含说话口型三张、眨眼两张）；建模设定 17 张、概念 5 张（和第二版逐字节相同，只有"庄屋的婆婆"一张不同） |
| 两个来源包 | 生成记录、raw、提示词、遮罩、核对脚本（不运行） |

表情（第二版，三人相同）：angry、cry_loud、cry_soft、dazed、determined、laugh、mischievous、neutral、open_smile、pout、sad、serene、serious、shout、shy、skeptical、smile、surprised、thinking、tired。

建模设定（每人）：`turnaround`（正、四分之三、侧、四分之三背、背五视，**Q 版 3–3.5 头身**）、`face_sheet`（12 种表情的头部表）、`hair`、`clothes`、`colors`（主色、暗部、亮部的 sRGB 值）；小鹊另有 `hat`（笠的顶、侧、底）和 `carrying_frame`（背负子三视）。

概念（设计候选，不是已定的人物）：乌鸦、神社结界仙境、茅屋气氛、行商、庄屋的婆婆。

## 用法（G5R3）

- **3D 人物重做（G5R3-6）**：小鹊的 `turnaround`、`face_sheet`、`hair`、`hat`、`clothes`、`colors`、`carrying_frame` 是主要参照。刘海盖住眉（G5R3-8）。
- **立绘（G5R3-9）**：第四版已通过；这些立绘只在逐张比较更好时才换。
- **场景**：茅屋、结界的概念图只作气氛参照，不照搬。
- 授权：用户自己生成并提供给本作使用。
