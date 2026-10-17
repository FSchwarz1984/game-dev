# 立绘补充素材清单（最终版）

> 状态：**最终版**（2026-10-17）。回应 G5R3-51 和 G5R3-60："要補的素材，你最好能夠最終確定到底有哪些，給我一個最終的版本"。这份清单交出去以后不再出第二版：某一张不合格，只重做那一张，清单本身不变（第 9 节）。
>
> - **给 ChatGPT 的正式说明（G5R3-64）**：`docs/design/portrait-gpt-brief.md`，导出为 `Tengan_Portraits_GPT_Brief.pdf`（英文正文，第一页中文给用户）。条目、参考图、做法和这份清单一样；**提示词和补救句以 brief 为准**：每条提示词补了一段"Sizes"（五官改多少），补救句多了三条。下面的提示词已和 brief 逐字同步；这份中文清单留作内部记录。
> - **一共 20 项**：GP-01…GP-16 是三个女孩的，一定要做；GP-17…GP-20 是婆婆的，**已定要做**（G5R3-65，C.1 选 A）：GP-17 先单独交回，用户看过、满意了再做 GP-18…20。新增的五张（GP-02…05、GP-11）已定（G5R3-66）。
> - 每一项为什么要做、用在剧本的哪几句，来自逐句排表情的 `docs/design/portrait-faces-seg1.md`（下文"A 表"）。
> - 参考图在 `portrait_refs/` 文件夹里，文件名以编号开头（主管会把这个文件夹发给你）。

## 0. 怎么用（先看这一段）

> G5R3-64 以后，用户按 brief 第一页的办法做：在 ChatGPT 里上传 PDF 和这一项的参考图，说"按这份文档做 GP-xx"，不再复制提示词。下面是原来的操作说明，留作记录。

1. **一项一个新对话。** 每一项在 ChatGPT 里新开一个对话，不要在上一张的结果上接着改：一路改下去会越改越偏。
2. **上传这一项的参考图**：`GP-xx_ref_a.png`；GP-17 要两张，`ref_a` 和 `ref_b`。参考图就是你原来那 12 包里的原画，原始分辨率，没有改过。
3. **复制这一项的提示词**（英文，第 6、7 节每项下面的整段），粘贴发送。提示词也单独存成了 `GP-xx_prompt.txt`，打开就能复制。如果你的 ChatGPT 有"选择区域再编辑"的笔刷，可以先把她整张脸涂上（从刘海下沿到下巴，连两颊），再发提示词；没有就直接发。
4. **检查**：先用第 4 节的通用条目，再看这一项自己的条目。最要紧的是"翻页检查"（G4）和"缩小检查"（G10）。
5. **不合格就在同一个对话里补救**：第 5 节有现成的英文句子。最多改三次；三次都不行，新开对话从头再来一次；还不行就跳过，交回时注明哪一项、哪里不行。
6. **顺序**：先做 GP-01…GP-16。婆婆已定要做（G5R3-65 选 A）：先做 GP-17、单独交回，我们转成游戏里的像素立绘给你看过，你满意了再做 GP-18…20（第 7 节）。
7. **交回**：文件名和方式见第 8 节。

## 1. 总表

| 编号 | 人物 | 表情 | 类型 | 用在第一段的几句（A 表） | 参考图 |
|---|---|---|---|---|---|
| GP-01 | 小鹊 | 认真 serious | 重做（盲测：平常、认真、坚定同一张脸） | 10 句 | `GP-01_ref_a.png` = A_35 |
| GP-02 | 小鹊 | 避开视线 evasive | 新增 | 6 句 | `GP-02_ref_a.png` = A_35 |
| GP-03 | 小鹊 | 低落 downcast | 新增 | 3 句 | `GP-03_ref_a.png` = A_35 |
| GP-04 | 小鹊 | 茫然 blank | 新增 | 4 句 | `GP-04_ref_a.png` = A_35 |
| GP-05 | 小鹊 | 得意 smug | 新增 | 3 句 | `GP-05_ref_a.png` = A_35 |
| GP-06 | 小鹊 | 喊（呼喊） shout | 重做（你点名） | 1 句 | `GP-06_ref_a.png` = A_12 |
| GP-07 | 小鹊 | 鼓腮 pout | 重做（你点名） | 这一段不用 | `GP-07_ref_a.png` = A_04 |
| GP-08 | 小鹊 | 思考 think | 重做（你点名） | 这一段不用 | `GP-08_ref_a.png` = A_34 |
| GP-09 | さぢ | 鼓腮 pout | 重做（你点名） | 2 句 | `GP-09_ref_a.png` = C_04 |
| GP-10 | さぢ | 喊 shout | 重做（你点名） | 4 句 | `GP-10_ref_a.png` = C_12 |
| GP-11 | さぢ | 得意 smug | 新增 | 2 句 | `GP-11_ref_a.png` = C_04 |
| GP-12 | しをね | 鼓腮 pout | 重做（你点名） | 这一段她不说话 | `GP-12_ref_a.png` = B_04 |
| GP-13 | しをね | 喊 shout | 重做（你点名） | 同上 | `GP-13_ref_a.png` = B_12 |
| GP-14 | しをね | 开怀 grin | 重做（你点名） | 同上 | `GP-14_ref_a.png` = B_02 |
| GP-15 | しをね | 认真 serious | 重做（你点名） | 同上 | `GP-15_ref_a.png` = B_25 |
| GP-16 | しをね | 茫然 blank | 重做（你点名） | 同上 | `GP-16_ref_a.png` = B_35 |
| GP-17 | 婆婆 | 设定，兼平常脸 neutral | 新增（G5R3-65 已定） | 10 句 | `GP-17_ref_a.png` = B_01、`GP-17_ref_b.png` = C_01（只作画风参考） |
| GP-18 | 婆婆 | 笑 smile | 新增（G5R3-65 已定） | 2 句 | 你通过的 GP-17 |
| GP-19 | 婆婆 | 怀念 wistful | 新增（G5R3-65 已定） | 4 句 | 你通过的 GP-17 |
| GP-20 | 婆婆 | 板脸 stern | 新增（G5R3-65 已定） | 5 句 | 你通过的 GP-17 |

"A_35"等是你原来 12 包里的编号（A＝小鹊，B＝しをね，C＝さぢ）。`portrait_refs/_overview_*.png` 把每一项的原画（游戏裁的那一块）和现在的第四版并排放在一起；`portrait_refs/_now/` 是要重做的那几张现在的样子（×3）。这两样只给你看，不用发给 ChatGPT。

## 2. 做法：在原画上只改脸（推荐）

两种做法：

- **编辑**：把原画传给 ChatGPT，只改脸，姿势、衣服、头发、笠、构图都不动。
- **新画**：照着参考图重新画一张。

| 比较的地方 | 编辑（只改脸） | 新画 |
|---|---|---|
| 脸和头的透视是否协调（你批评喊的嘴"和脸的透视不協調"） | 整张脸由 ChatGPT 一次画出来，自然跟着头的角度。第四版的问题是我们只在一张不喊的脸上补了一张大嘴；只要它不是"只换嘴"，就不会再出现。提示词里写明整张脸一起重画、张嘴时下巴跟着往下，合格条目 G5 专门查这一条 | 全身一起画，最协调；但头的角度和第四版其他表情不一样 |
| 换表情时姿势一不一致 | 和第四版用同一张原画：姿势、手、笠、头发都一样，换到这张脸时人不跳。配色也是同一套，转换时用原来的调色板，其余各张一个像素都不变 | 每张的姿势、头的倾斜、发型细节都会变。上次两包新画的素材：小鹊的比例变成熟（眼到下巴 1.26 个眼距，原画 1.05–1.15；眼到腰带约 7 个眼距，原画 3.7），しをね的头在框里变大（knowledge/13 §10.10）；第二包的头被摆正到 15° 以内（4.3）。所以只有さぢ从里面挑了三张 |
| 画风会不会漂 | 线条和上色沿用原画。ChatGPT 的编辑仍然会整张重算，旁边可能有细微变化，所以要翻页检查（G4）；我们收图后还可以只取新图的脸，贴回原画上（第 9 节） | 漂得最多：上次第一包里小鹊的脸更窄、头发更平，第二包整体偏成熟 |
| 表情够不够强 | 原画的表情本来就淡，ChatGPT 可能改得太轻。用缩小检查（G10）把关，不够就用补救句"再夸张一倍" | 容易画出强表情 |

**推荐：三个女孩的 16 项全部用编辑。** 婆婆没有原画，她的设定（GP-17）只能新画，她的三张表情再在你通过的设定上编辑。

小鹊的 GP-01…05 都用同一张原画 A_35，也就是第四版"平常"那一张。加上平常，这六种安静的表情在第一段占了她出立绘的 54 句里的 51 句；用同一张原画，换脸时只有脸在变。

**关于现在的 ChatGPT**（2026-10 查的）：

- 现在是 ChatGPT Images 2.5（2026-09-08 发布）。报道说它"在只改画面一部分时更可靠，不会动画面里的其他细节"，多轮修改时"前面改过的地方更容易保持一致"（IT Brief）。
- OpenAI 的帮助页说：可以用选择工具圈出要改的部分；圈选不精确，改动会溢出；在提示词里写明要改哪里更准。这两页对本机返回 403，没能直接读到，内容来自搜索引擎对它们的摘要。
- 所以编辑之后一定要翻页检查。

## 3. 提示词为什么用英文

- **依据：** Qwen-Image-Bench（arXiv 2605.28091，2026）用 1,000 条中英对照的提示词测了 18 个图像模型。GPT Image 2（ChatGPT Images 2.0 用的模型）各项得分如下：

  | 指标 | 中文提示词 | 英文提示词 |
  |---|---|---|
  | 总分 | 64.7 | 65.2 |
  | 照提示词办事（Alignment） | 65.85 | 65.78 |
  | 画面质量 | 58.65 | 59.09 |
  | 美感 | 67.53 | 68.48 |

  照提示词办事几乎一样，质量和美感英文略高。上一代 GPT Image 1.5，论文明说英文提示词更听话。2.5 没有按语言的对比数据。
- **选英文的理由：**
  1. 我们要的说法，英文在图像生成里是通行的术语，一个词一个意思："three-quarter view"、"half-lidded eyes"、"puffed cheeks"、"real alpha channel"、"cel shading"。中文的"漫符""赛璐璐"在中英混杂的语境里容易被理解偏。
  2. 质量和美感那一点点差距。
  3. 上两版清单都是中文提示词，结果比例漂了。没有证据说是语言造成的，但也没有理由留在中文。
- **如实说：** 语言的差别很小。真正决定成败的是"编辑而不是新画"和第 4 节的检查。
- 你不用读英文：每一项的提示词上面有中文说明，说的是同一件事。ChatGPT 用中文回你也没关系。

## 4. 合格标准

### 4.1 每一张都查（GP-17 另有自己的标准，见第 7 节）

- **G1** 一张图、一个人、一个表情；不要拼图、多格、九宫格。
- **G2** PNG；画布和参考图一样大（1024×1536 竖图）。ChatGPT 给的是更大的 2:3 竖图也可以（比如 1365×2048），比例必须是 2:3。
- **G3** 透明是真的透明：
  - 在文件资源管理器里看缩略图，人物外面是纯色（跟着资源管理器的底色走），不是灰白相间的格子。
  - 格子是画上去的假透明，不合格。
  - 两次都给不出真透明，用第 5 节的"绿底"那一句，见 4.4。
- **G4 翻页检查（最要紧）。** 新图和参考图放在同一个文件夹，用"照片"打开，按左右方向键来回切换。
  - 笠、头发（含刘海和发梢）、角、发箍、发绳、衣服、手、身体的位置和大小都不动；
  - 两只眼睛的位置不跳；
  - 只有脸在变。
- **G5 整张脸是一起画的。** 眼、眼睑、嘴、脸颊、下巴是同一个表情。张大嘴的，下巴跟着往下，嘴的中线跟着头歪的方向，不像后来贴上去的（G5R3-51）。
- **G6 没有任何漫画符号和文字**：汗滴、怒筋、"！""？"、思考泡泡、哼气的白气、红晕斜线、闪光、音符、"……"、对话框、文字、水印、签名。这些由游戏叠加（G5R3-13）。腮红只能是柔和的粉色，不画斜线。
- **G7 没有泪，眼里和脸上没有水光。** 这份清单里没有一张要泪。上次半透明的泪缩小以后变成灰斑，那批因此不合格（knowledge/13 §10.10）。以后哪一张要泪，泪要画成不透明的实色形状，不能是半透明的水光；游戏这边的泪本来就是这样补的。
- **G8 设定不走样**，对照 4.2 逐项看。
- **G9 比例不变**，对照 4.3。编辑出来的图，翻页检查（G4）过了，这一条就过了。
- **G10 缩小检查。**
  - 在"画图"里把新图和参考图都缩小：调整大小 → 百分比，小鹊 45，しをね和さぢ 40（婆婆 45）。
  - 这时两眼相距约 25–32 像素（随头转的角度变）、脸约 60 像素宽，和游戏里 128×128 的立绘框里一样大。游戏还要再转成像素，所以这一步看着刚刚读得出的，到游戏里会更弱：要一眼就看得出。
  - 并排看：这张的表情一眼看得出，和参考图明显不同。
  - 小鹊的 GP-01…05 还要彼此分得开（4.2 末尾的表）。
  - 看不出来就是太轻。
- **G11 画风和参考图一样**：线条和上色的方式不变；不能变成厚涂、写实、3D 渲染或像素画。

### 4.2 设定要点（G8）

**小鹊（百々かさゝぎ，原画包 A）**

- 白色的宽檐菅笠，笠面斜着一条红带，笠的底面是深蓝色。
- 黑里带紫的长直发；厚厚的齐刘海**盖住眉毛，不能露眉**（G5R3-8）。
- 胸前两束头发，各用白、红、白三道发绳扎着。
- 灰紫色的眼睛。
- 深蓝的和服，领口是外白内红的 V 字。

**さぢ（家守さぢ，原画包 C）**

- 蓬乱的红色短发，头顶翘起一撮。
- 青绿色的发箍；青绿色的眼睛；脸颊天生带一点红。
- 薄荷绿的披肩领，边是深青绿色；领口一只金色的铃；深红的衣领。

**しをね（垣外しをね，原画包 B）**

- 偏暖的银紫色头发，齐刘海，发梢外翘。
- 头的画面左侧一只深红色的月牙形角，只有这一只。
- 红色的眼睛。
- **右眼下**，也就是画面左边那只眼睛下面，有两道短短的红色竖痕（G5R2-10）。
- 低马尾在后颈用红绳扎成一个大结，从画面左侧看得见。
- 白衣，深红的衣领。

**小鹊六张安静的脸（现有的平常 + GP-01…05），彼此怎么分**（G10 用；每张一个在小图里看得见的硬特征）：

| 表情 | 眼睑 | 眼珠 | 嘴 |
|---|---|---|---|
| 平常（现有，A_35 原样） | 正常张开 | 看向右边（说话的对象） | 小、平 |
| 认真 GP-01 | 上眼睑压平压低、下眼睑上提，眼睛明显变窄 | 平视右边 | 一条更长的直线 |
| 避开视线 GP-02 | 正常或略低 | **移到眼眶左侧**，躲开对方 | 抿紧 |
| 低落 GP-03 | **上眼睑重重垂下** | 往下看 | 嘴角微微往下 |
| 茫然 GP-04 | **比平常睁得大**，眼白多一点 | 小一点、失焦 | **微微张开一道缝** |
| 得意 GP-05 | 半垂，下眼睑往上推，像在笑 | 斜看右边 | **画面右边那个嘴角微微上扬** |

### 4.3 比例（G9；数字从你那 12 包原画量的）

我们在 1024×1536 的全身原画上量：两眼取瞳孔中心，下巴取下巴尖，腰带取正中的上缘。

| | 小鹊（A） | しをね（B） | さぢ（C） | 上次不合格的 ChatGPT 素材 |
|---|---|---|---|---|
| 两眼间距（随头转的角度变） | 57–72 像素 | 55–76 像素 | 61–78 像素 | — |
| 眼到下巴 ÷ 两眼间距（闭嘴） | 1.05–1.15 | 1.0–1.15 | 1.05–1.2 | 第二包：小鹊 1.26、しをね 1.23 |
| 眼到腰带上缘 ÷ 两眼间距 | 3.7 | 3.3（袴的上缘） | 3.7 | 第二包小鹊约 7 |
| 全身约几个头高 | 6.7 | 6.9 | 6.2 | — |
| 头歪的角度（两眼连线） | 19–33° | 12–27° | 19–34° | 第二包按上次清单的要求摆正到 15° 以内（抽量小鹊的平常：约 14°） |

- 大张嘴的（喊）：眼到下巴可以长到 1.35 个眼距，下巴本来就该往下。
- 编辑的图不用量，翻页检查过了就行。
- 这张表给两种情况用：一是 ChatGPT 没听话、把全身重画了；二是给婆婆的设定作画风上的参考（第 7 节）。

### 4.4 背景

- **要透明的 PNG。** 提示词里只要透明，不给第二个选择。上次写了"透明底，或者纯浅灰"，ChatGPT 多数给了灰底。
- **做不到时的退路：纯绿 #00FF00。** 要它整片一个颜色，不要渐变、不要地面的影子，人物身上不要反出绿光。第 5 节有现成的句子。
- **为什么是纯绿。** 我们量了第四版三人各自用到的全部颜色（57–61 种），每一种和候选底色的色差（CIELAB ΔE）取最小值：

  | 候选底色 | 和三人颜色的最小色差 |
  |---|---|
  | 纯绿 | 103–117 |
  | 纯蓝 | 115–119 |
  | 洋红 | 89–92 |
  | 浅灰 #E6E6E6 | 只有 6–8 |
  | 白 | 0 |

  - 浅灰、白和小鹊的笠、しをね的白衣和银发几乎一样，抠图后留下浅色毛边，上次就是这样。
  - 纯蓝也远，但小鹊的深蓝和服和笠底贴着边，蓝色的毛边会读成衣服的颜色。
  - さぢ的薄荷绿披肩和青绿发箍，比纯绿暗得多、灰得多，抠得开。
  - 婆婆的衣服如果定成绿色，她的退路改用洋红 #FF00FF。

### 4.5 尺寸和取景

- **编辑的 19 项（GP-01…16、18…20）**：和参考图一样，全身、1024×1536、人在画布里的位置和大小不变。不要你裁成胸像，也不要 ChatGPT 裁：游戏这边按第四版的取景，从全身图上以两眼为准裁出 128×128 的胸像，每个人所有表情的取景都一样（knowledge/13 §10.2）。
- **GP-17**：全身、1024×1536、四分之三侧身朝画面右边，头的大小和三个女孩的原画差不多（两眼相距约 60–75 像素）。

## 5. 补救用的句子（复制到同一个对话里；以 brief 的 A7 为准）

| 毛病 | 发这一句 |
|---|---|
| 表情太轻（G10 没过） | `The expression is too weak. Make it about twice as strong. Keep everything except the face exactly the same.` |
| 某一处改得不够（眼睑、眼珠、嘴、脸颊） | `Make the change to the [eyelids / irises / mouth / cheek] bigger: [the size from the item's Target]. Keep everything else exactly the same.` |
| 动了脸以外的地方（G4 没过） | `You changed other parts (the hat / hair / clothes / hands / size or position). Start again from the original image I attached and change only the face.` |
| 嘴像贴上去的（G5 没过） | `The mouth looks pasted on. Redraw the whole face — eyes, eyelids, cheeks, mouth and jaw — as one expression that follows the tilt of her head.` |
| 画了符号、腮红斜线、泪或水光（G6、G7 没过） | `Remove the sweat drop / blush lines / tears / wet shine / symbol. Change nothing else.` |
| 不是真透明（G3 没过） | `The background must be truly transparent (a real PNG alpha channel, not a checkerboard pattern). Give me the same image again with a transparent background and nothing else changed.` |
| 两次都不透明，改用绿底 | `Give me the same image again, but fill the whole background with one flat pure green colour, #00FF00 (RGB 0, 255, 0): no gradient, no ground shadow, no green light reflected on her, and a clean edge around her hair. Change nothing else.` |
| 小鹊露出了眉毛 | `Her eyebrows must stay hidden under her bangs, as in the original. Keep the bangs exactly as in the original.` |
| しをね的红痕跑了位置 | `The two short red marks must stay under her right eye — the eye on the left side of the image — exactly as in the original.` |
| 眼睛空了、灰了或发光 | `Keep her normal iris colour and the white highlights in her eyes. The eyes must look alive.` |
| 脸变老、变长或脸型变了（G9 没过） | `Keep her face shape and proportions exactly as in the original: the same head size, eye size and distance from the eyes to the chin.` |
| 风格变了（G11 没过） | `Keep the drawing style of the original exactly: the same clean anime line art and soft cel shading, the same line weight and colours.` |

## 6. 三个女孩：GP-01…GP-16（一定要做）

### GP-01　小鹊 · 认真（serious）　重做

- **用在**（10 句）：0-04 看出绑绳少绕一圈、0-28 "这个，您要送到哪儿？"、1-06 碎石路的嘱咐、3-05 和 7-02 "那是拿桃付过的。"、10-05 报梁的分量、10-20 "婆婆呢？"、11-05 "这是我的背负子。"、11-06 "你下去。"、11-10 挑さぢ屁股上的土（10-05、11-10 是 G5R3-68 改过的句子）。都是说本行、认真盯着、收紧的时候。
- **为什么重做**：平常（A_35）、认真（A_25）、坚定（A_10）三张原画几乎同一张脸，三轮盲测都互相认错（knowledge/13 §10.5、§10.10）。现在改用 A_35 只改脸，让它和平常分得开；坚定不再单独使用（`portrait-faces-seg1.md` B.4）。
- **参考图**：`GP-01_ref_a.png`（A_35，第四版"平常"的原画）。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 缩到 45% 并排看，眼睛比参考图明显窄，上眼睑是平的，嘴是一条直线。
  - 不能像生气：眼睛的内角不往下斜。
  - 不能像困：眼皮不耷拉。
- **中文说明**（不用复制）：专注、认真，像手艺人在估一件货。上眼睑压平、压低一点，下眼睑抬一点，眼睛变窄但还睁着，看得见虹膜和高光，平视右边；嘴闭成一条更长的直线。不生气、不困、不难过，不笑，不脸红。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, the wide straw hat with its red band, her long black-purple hair, the thick straight bangs, the two front locks with their white-and-red hair ties, the clothes, the small lantern in her hand, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face. Her eyebrows are hidden under her bangs: keep them hidden and show the expression with the eyes, eyelids and mouth.

New expression — focused and serious, the look of a craftswoman sizing up a load: upper eyelids lowered a little and drawn straight and flat across the top of the irises, lower eyelids raised slightly, so the eyes are clearly narrower than in the original but still open, with the irises and their highlights visible; a steady gaze straight ahead toward the right. Mouth closed in a firm, straight line, a little longer than now. Not angry, not sleepy, not sad; no smile, no blush.

Sizes, compared with the original: each eye about 70% as tall as now, the upper eyelid covering roughly the top quarter of the iris; the mouth line about one and a half times as long as now, perfectly straight and clearly dark.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-02　小鹊 · 避开视线（evasive）　新增

- **用在**（6 句）：0-07 "个子矮，货放得稳。"、2-01 "我可没吃。只是换一换。"、3-06 "我可什么也……"、9-03 "反正，那个也不是活计。"、11-02 "没晃。"、12-02 "下来的时候，稍有闪失。"。没人问先否认，替自己开脱，被戳穿还嘴硬。在笑话里配汗，在第 9 场的伤心里不配，同一张脸用在两种地方。
- **为什么新增**：这是剧本里她最常见的习惯（剧本 1.2 节），现有的脸里没有"躲"：害羞是双手捂脸，太大；平常读不出躲。
- **参考图**：`GP-02_ref_a.png`（A_35）。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 缩到 45%，一眼看得出眼珠在眼眶的左边（参考图是看右边）。
  - 脸是平静的：不害羞、不难过、不害怕。
  - 不脸红。
- **中文说明**：一本正经地躲开对方的眼睛（她在否认或找理由）。两只眼珠都移到眼眶的最左边，明显躲开右边说话的人，虹膜右边露出眼白；眼皮略低；嘴闭着，小，抿紧，嘴角不上不下。脸其余部分平静，不害羞、不难过、不害怕，不脸红。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, the wide straw hat with its red band, her long black-purple hair, the thick straight bangs, the two front locks with their white-and-red hair ties, the clothes, the small lantern in her hand, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face. Her eyebrows are hidden under her bangs: keep them hidden and show the expression with the eyes, eyelids and mouth.

New expression — avoiding someone's eyes while keeping a perfectly straight face (she is denying something, or making an excuse): both irises moved to the far LEFT side of her eyes, clearly looking away from the person on the right, with white showing on the right side of each iris; eyelids slightly lowered; mouth closed, small and pressed tight, the corners neither up nor down. The rest of the face stays calm: she is not shy, not sad and not scared. No blush.

Sizes, compared with the original: each iris pushed all the way into the left corner of its eye, with a clear strip of white on its right side about a third as wide as the iris; the upper eyelids covering a little of the top of the irises; the mouth a little shorter than now.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-03　小鹊 · 低落（downcast）　新增

- **用在**（3 句）：6-02 树顶看着鼓槌"从山上绕一圈……"、9-01 "婆婆家这时候，该做午饭了。"、9-02 "三十年，一回也没误过……"。
- **为什么新增**：现有的"难过"是含泪的；她这一段不哭，话里也不说难过，难过只能在脸上（"不解释情绪"）。要一张垂眼、不带泪的。
- **参考图**：`GP-03_ref_a.png`（A_35）。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 缩到 45%，眼皮明显垂下、往下看。
  - 没有泪、没有水光。
  - 和"认真"分得开：认真是平视、眼皮平；低落是往下看、眼皮重。
- **中文说明**：自己憋着的安静的难过。上眼睑重重垂下，眼睛半闭，往右下方看；虹膜一部分藏在眼皮下，睫毛弯成往下的弧；嘴小、闭着，嘴角微微往下。平静，不哭：没有泪、没有水光、不脸红。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, the wide straw hat with its red band, her long black-purple hair, the thick straight bangs, the two front locks with their white-and-red hair ties, the clothes, the small lantern in her hand, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face. Her eyebrows are hidden under her bangs: keep them hidden and show the expression with the eyes, eyelids and mouth.

New expression — quiet sadness she keeps to herself: upper eyelids lowered heavily so the eyes are half closed, looking down toward the lower right; the irises partly hidden under the lids, the lashes forming a soft downward curve; mouth small and closed, the corners turned slightly down. Calm, not crying: no tears, no wet shine, no blush.

Sizes, compared with the original: each eye about half as tall as now, the upper eyelid covering about half of the iris, the lower edge of the iris resting on the lower eyelid; keep a small white highlight in each iris so the eyes still look alive; the corners of the mouth just visibly lower than its middle.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-04　小鹊 · 茫然（blank）　新增

- **用在**（4 句）：7-01 醒来"都快午时了。"、8-01 "昨天才给门槽抹的蜡。"、8-03 "说是不让叫。"、10-13 第一次「移」之后"吃是没吃。先替它收着。"。大事当前说小事，脸上是还没回过神。
- **为什么新增**：用户说过主角看到世界出了大事"竟然没有任何一点反应"（R-5）。这几句话是小事，反应要在脸上。现有的"惊讶"是一下子的，茫然是停住的。
- **参考图**：`GP-04_ref_a.png`（A_35）。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 缩到 45%，眼睛比参考图睁得大，嘴微微张着一道缝。
  - 眼睛照常有颜色、有高光，不能空、不能灰、不能发光。用户说过しをね那张褪色的"茫然""詭異"（G5R3-51）。
  - 不能像惊讶：嘴只是一道缝，不是圆的"o"。
- **中文说明**：还没明白发生了什么、愣住了。眼睛比原画睁得大，虹膜四周露出一点眼白；虹膜略小，直直看着前方、失焦，像看穿了东西；嘴唇微微分开一道缝；脸是松的。眼睛照常的颜色和高光都留着，要看得出是活的。不哭、不出汗。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, the wide straw hat with its red band, her long black-purple hair, the thick straight bangs, the two front locks with their white-and-red hair ties, the clothes, the small lantern in her hand, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face. Her eyebrows are hidden under her bangs: keep them hidden and show the expression with the eyes, eyelids and mouth.

New expression — stunned, not yet understanding what has happened: eyes opened wider than in the original, with a little white visible around the irises; the irises slightly smaller, looking straight ahead without focus, as if seeing through things; lips slightly parted with a small gap (not a round open mouth); the face otherwise slack. Keep her normal eye colour and the highlights: the eyes must still look alive, not empty, not grey, not glowing. No tears, no sweat.

Sizes, compared with the original: each eye about a fifth taller than now, with a thin line of white showing above or below the iris; the irises about 10 to 15 percent smaller; the lips parted by a thin dark gap that stays clearly visible when the picture is small.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-05　小鹊 · 得意（smug）　新增

- **用在**（3 句）：0-17 "九十九折，我闭着眼也下得去。"（夸口）、11-16 "先拿这个，当定钱。"、12-09 "它拿团子付过了。"。只在她占了上风的那一刻露一点。
- **为什么新增**：她"一本正经地使坏"（characters.md 三人的喜剧分工），用户要"古灵精怪"。夸口那条线（第 0 场夸口、第 6 场摔下来、第 12 场"稍有闪失"）要在第一拍有一张得意的脸，后两拍才有落点。
- **参考图**：`GP-05_ref_a.png`（A_35）。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 缩到 45%，读得出"得意、心里有数"，不是平常，也不是开心的笑。
  - 画面右边那个嘴角上扬看得见。
  - 不眨眼、不露牙、不脸红。
- **中文说明**：小小的、不声不响的得意（她刚一本正经地说了句聪明话）。眼皮半垂，下眼睑往上推一点，眼睛像一个平静的、心里有数的半笑，斜看右边；画面右边那个嘴角微微上扬，闭着嘴的一点坏笑。要淡、要干：不是大笑，不眨眼，不露牙，不脸红。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, the wide straw hat with its red band, her long black-purple hair, the thick straight bangs, the two front locks with their white-and-red hair ties, the clothes, the small lantern in her hand, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face. Her eyebrows are hidden under her bangs: keep them hidden and show the expression with the eyes, eyelids and mouth.

New expression — a tiny, quiet, pleased-with-herself look (she has just said something clever with a perfectly straight face): eyelids half lowered and the lower eyelids pushed up a little, so the eyes look like a calm, knowing half-smile, glancing toward the right; the corner of her mouth on the right side of the image raised slightly in a small, closed-mouth smirk. Subtle and dry: not a big smile, no wink, no teeth, no blush.

Sizes, compared with the original: the upper eyelids covering about a third of each iris and the lower eyelids pushed up into a slight upward curve, so the eyes are a little more than half as tall as now; the mouth line about a third longer than now, with only its end on the right side of the image lifted.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-06　小鹊 · 喊（呼喊，shout）　重做

- **用在**（1 句）：6-05 "婆婆——！"。白潮从平原扑上来时，她朝山下的庄屋喊，是第一段里她唯一一次放开嗓子。
- **为什么重做**：
  - 你说："我不知道那个嘴巴是不是你之后画上去的，我感觉从人物面部透视的角度来说，有一点不太协调怪怪的"（G5R3-51）。确实是：原画 A_12 是"快步焦急"的小张嘴，第四版在上面补了一张大嘴，眼睛和脸还是原来的。
  - 第五轮盲测，三位测试者都把三个人的喊读成惊讶。
- **参考图**：`GP-06_ref_a.png`（A_12，第四版"喊"的原画；姿势不变）。
- **做法**：编辑，整张脸一起重画。
- **这一张自己的条目**：
  - G5 要特别看：嘴张得很大，下巴跟着往下（脸变长一点），嘴的中线跟着头的倾斜。
  - 缩到 45%，读得出是在喊，不是惊讶：嘴是大张的、看得见牙，不是小圆"o"。
  - 是焦急，不是生气：内眼角的上眼皮往上提。
- **中文说明**：拼尽全力朝山下远处的人喊，焦急、惊慌，不是生气。嘴张得很大，下巴往下，脸长了一点，看得见上排牙和舌头，口腔是暗的；眼睛睁大，虹膜变小；上眼睑靠鼻子那一头往上提（担心）；整张脸绷紧。一整张喊的脸，张开的嘴跟着头的角度和倾斜。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, the wide straw hat with its red band, her long black-purple hair, the thick straight bangs, the two front locks with their white-and-red hair ties, the clothes, the hands, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face. Her eyebrows are hidden under her bangs: keep them hidden and show the expression with the eyes, eyelids and mouth.

New expression — calling out with all her voice to someone far away below the mountain; desperate and alarmed, not angry: mouth opened very wide, the jaw dropped so the face becomes a little longer, the upper teeth and the tongue visible, the inside of the mouth dark; eyes wide open with smaller irises; the inner ends of the upper eyelids lifted with worry; the whole face tense. Draw it as one shouting face, so the open mouth follows the angle and tilt of her head.

Sizes, compared with the original: the open mouth more than twice as tall as now and about a third wider; the chin lowered by about half the height of her iris, so the face becomes visibly longer; the irises about 15 percent smaller. The original has a faint little sweat drop on her cheek: leave it out.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-07　小鹊 · 鼓腮（pout）　重做

- **用在**：第一段没有。你点名重做（G5R3-51），以后的剧本会用到。
- **为什么重做**：
  - 你说："三個人的鼓腮，首先我不太能看出来小鵲和其他人差不多的氣鼓鼓的樣子，而且三個人嘴巴邊上那個白色氣泡做得非常意義不明。"
  - 原画 A_04 的"3"字小嘴在 128 像素里丢了，第四版改成波浪嘴、加了白气。新的一张要靠鼓起来的脸颊改变脸的轮廓，不靠嘴边的符号。
- **参考图**：`GP-07_ref_a.png`（A_04，叉腰的姿势不变）。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 缩到 45%，脸的外轮廓（画面右边那一侧的脸颊）明显鼓出去。
  - 嘴边没有任何白气或符号。
  - 腮红只能是粉色，不画斜线。
- **中文说明**：赌气。两颊鼓满了气，画面右边那一侧脸颊的轮廓明显往外鼓，近处的脸颊变圆；嘴噘成一个小小的、抿着的嘟嘴；眼睛斜看一边，上眼皮压低一点（不高兴）；脸颊上淡淡的粉红（只有颜色）。嘴边不要白气，不要任何符号。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, the wide straw hat with its red band, her long black-purple hair, the thick straight bangs, the two front locks with their white-and-red hair ties, the clothes, the pose with her hands on her hips, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face. Her eyebrows are hidden under her bangs: keep them hidden and show the expression with the eyes, eyelids and mouth.

New expression — sulking: both cheeks puffed full of air, so the outline of her far cheek (the right side of her face in the image) clearly bulges outward and the near cheek looks round; lips pushed together into a small, pursed pout; eyes looking sideways with the upper eyelids lowered a little, grumpy; a soft pink blush on the cheeks (colour only). No puff of air and no symbol near the mouth.

Sizes, compared with the original: the outline of her far cheek pushed out by about a third of an iris width; the pursed mouth smaller than now (about two thirds of its width); the upper eyelids covering about a quarter of each iris; the irises glancing toward the left side of the image.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-08　小鹊 · 思考（think）　重做

- **用在**：第一段没有。你点名重做（G5R3-51："小鵲的思考也怪怪的"）。
- **为什么重做**：原画 A_34（拿着折起来的地图辨路）的脸和平常几乎一样，第四版只是在头旁边加了一个思考泡泡，脸本身读不出在想事情。
- **参考图**：`GP-08_ref_a.png`（A_34，拿地图的姿势不变）。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 缩到 45%，不靠泡泡也读得出在想事情：眼珠往左上看，嘴歪向一边。
  - 没有思考泡泡、没有问号。
- **中文说明**：在使劲想一件事。虹膜转向左上方，像在回想；离我们近的那只眼睛略眯；嘴闭着、往一边歪一点，抿成一条有点歪的线，一个"嗯……"的样子。没有思考泡泡，没有问号。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, the wide straw hat with its red band, her long black-purple hair, the thick straight bangs, the two front locks with their white-and-red hair ties, the clothes, the hands and the folded map, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face. Her eyebrows are hidden under her bangs: keep them hidden and show the expression with the eyes, eyelids and mouth.

New expression — thinking hard about something: irises turned up and to the left, as if trying to recall something; the eye nearer to us slightly narrowed; mouth closed and pulled a little to one side, lips pressed into a slightly crooked line, a puzzled "hmm". No thought bubble, no question mark.

Sizes, compared with the original: the irises raised so that about a third of each is hidden under the upper eyelid, with white showing below them; the near eye (on the left side of the image) a little narrower than the far one; the mouth line about as long as now, moved slightly toward the left side of the image and tilted.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-09　さぢ · 鼓腮（pout）　重做

- **用在**（2 句）：10-06 "你那么懂分量，想想办法嘛！"、11-08 "不要！这是我家嘛！"。
- **为什么重做**：
  - 你点名三个人的鼓腮（G5R3-51），说嘴边的白色气泡意义不明。
  - 原画 C_04 的"3"字嘴在 128 像素里丢了。
  - 第一包 ChatGPT 素材里有一张鼓腮（saji_puffed_cheeks），不拿来顶替：knowledge/13 §10.10 记的是新素材的嘟嘴不加符号读不出；我又看了它转成 128 像素的样子，脸颊几乎没有鼓出轮廓。
- **参考图**：`GP-09_ref_a.png`（C_04，叉腰的姿势不变）。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 缩到 40%，两边脸颊鼓出脸的轮廓，一眼是"气鼓鼓"。
  - 发箍、铃、天生的红脸蛋都在。
  - 嘴边没有白气。
- **中文说明**：小孩子赌气。两颊像仓鼠一样使劲鼓起来，脸两边的轮廓明显鼓出去；嘴噘成一个小圆；眉毛往鼻子那边压下来，斜着眼瞪人；脸颊粉红（只有颜色）。是生闷气、耍赖，不是哭。嘴边不要白气，不要任何符号。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, her messy red bob with the single upright tuft, the teal headband, her naturally rosy cheeks, the mint-green cape collar with its dark teal edge, the golden bell at her collar, the clothes, the pose with her hands on her hips, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, eyebrows, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face.

New expression — a childish sulk: cheeks puffed out hard like a hamster's, so the outline of her face visibly bulges on both sides; lips pushed into a small round pout; eyebrows angled down toward her nose; eyes glaring sideways; a pink blush on the cheeks (colour only). Cross and stubborn, not crying. No puff of air and no symbol near the mouth.

Sizes, compared with the original: the outline of her face pushed out on the far side by about a third of an iris width, and the near cheek rounder; the pout a small round shape about a third as wide as an iris; the eyebrows angled down more steeply than now; the irises toward the right corners of her eyes, glaring at the person on the right.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-10　さぢ · 喊（shout）　重做

- **用在**（4 句）：10-08 "给你福气！福气！给好多！……"、10-10 "那、那团子大人！……"、10-24 "等等！团子大人我还没给你呢！"、10-25 "去了也没用！人家跑了一整晚，连门都没摸着！"。
- **为什么重做**：你点名三个人的喊，嘴和脸的透视不协调（G5R3-51）；盲测读成惊讶。原画 C_12 是焦急的小张嘴。
- **参考图**：`GP-10_ref_a.png`（C_12，姿势不变）。
- **做法**：编辑，整张脸一起重画。
- **这一张自己的条目**：
  - G5 要特别看：嘴大张、看得见牙和舌头，下巴跟着往下。
  - 缩到 40%，读得出在喊，不是惊讶。
  - 没有泪。
- **中文说明**：拼命大声喊，一个急得快哭的小姑娘在喊住要走的人。嘴大张，下巴往下，看得见上排牙和舌头；眉毛扬起、往中间挤；眼睛睁大；脸涨红。不哭：没有泪。一整张喊的脸，张开的嘴跟着头的角度。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, her messy red bob with the single upright tuft, the teal headband, her naturally rosy cheeks, the mint-green cape collar with its dark teal edge, the golden bell at her collar, the clothes, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, eyebrows, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face.

New expression — yelling as loudly as she can, a desperate and upset little girl calling after someone who is leaving: mouth wide open, the jaw dropped, the upper teeth and the tongue visible; eyebrows raised and pulled together; eyes wide; the face flushed. Not crying: no tears. Draw it as one shouting face, so the open mouth follows the angle of her head.

Sizes, compared with the original: the open mouth about one and a half times as wide and twice as tall as now, roughly as tall as it is wide; the chin lowered by about half the height of her iris; the eyebrows raised higher than now; the irises about 10 percent smaller. The original has a faint little sweat drop on her cheek: leave it out.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-11　さぢ · 得意（smug）　新增

- **用在**（2 句）：11-04 "定了。从今天起，这儿是我家！"、11-13 "还有你，背东西的！在我家底下走，房租拿来！"。
- **为什么新增**：宣布所有权是她的招牌（characters.md；knowledge/23 §6.2）。现有的"开怀"读成单纯的高兴，"坏笑"有眨眼，读成开玩笑，都不是小房东的神气。和鼓腮（GP-09）用同一张原画，第 11 场两种脸来回换时人不跳。
- **参考图**：`GP-11_ref_a.png`（C_04，叉腰的姿势不变）。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 缩到 40%，读得出神气、得意，和"坏笑"（眨眼、虎牙）分得开。
  - 不眨眼，不露虎牙。
- **中文说明**：神气、霸道，一个小房东在宣布"这是我家"。眼睛半闭，一副了不起、心满意足的样子；眉毛扬起；闭着嘴的一个大大的得意笑；脸颊因为得意有点红。不眨眼，不露虎牙，不生气。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, her messy red bob with the single upright tuft, the teal headband, her naturally rosy cheeks, the mint-green cape collar with its dark teal edge, the golden bell at her collar, the clothes, the pose with her hands on her hips, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, eyebrows, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face.

New expression — proud and bossy, a little landlady announcing that this is HER house: eyes half closed with a superior, satisfied look; eyebrows raised; a big, self-satisfied, closed-mouth grin; cheeks a little flushed with pride. No wink, no fang, not angry.

Sizes, compared with the original: the upper eyelids covering a third to a half of each iris, drawn flat; the eyebrows raised in a relaxed curve; the closed-mouth grin about three times as wide as the original mouth, curving up at both ends.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-12　しをね · 鼓腮（pout）　重做

- **用在**：第一段她不说话。你点名重做（三个人的鼓腮，G5R3-51）。
- **为什么重做**：同 GP-07：嘴边的白气意义不明，脸颊没鼓。她温柔守礼（characters.md），鼓腮要轻、要有教养，但缩小后仍要读得出。
- **参考图**：`GP-12_ref_a.png`（B_04，姿势不变）。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 缩到 40%，画面右边那一侧脸颊的轮廓鼓出来一点，读得出"不高兴"。
  - 右眼下的两道红痕原样在原处；只有一只角。
  - 嘴边没有白气。
- **中文说明**：温和、有教养的小小赌气（她是个安静、极有礼貌的姑娘）。脸颊轻轻鼓起，画面右边那一侧脸颊的轮廓鼓出来一点；嘴抿成小小的嘟嘴；眼睛看向一边，上眼皮稍低；淡淡的粉红（只有颜色）。有点不乐意，不是生气。嘴边不要白气，不要任何符号。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, her silver-lavender hair with straight bangs, the single dark-red crescent horn, the low ponytail and its big red cord, the two short vertical red marks under her right eye (the eye on the LEFT side of the image), the white kimono with the dark-red collar, the hands, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, eyebrows, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face.

New expression — a gentle, ladylike sulk (she is a calm, very polite girl): cheeks softly puffed, so the outline of her far cheek (the right side of her face in the image) bulges a little; lips pressed into a small pout; eyes looking away to the side with the upper eyelids slightly lowered; a faint pink blush (colour only). Mildly miffed, not angry. No puff of air and no symbol near the mouth.

Sizes, compared with the original: the outline of her far cheek pushed out by about a quarter of an iris width; the pout about half as wide as the original wavy mouth; the upper eyelids covering about a fifth of each iris; the irises glancing toward the left side of the image.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-13　しをね · 喊（shout）　重做

- **用在**：第一段她不说话。你点名重做（三个人的喊，G5R3-51）。
- **为什么重做**：补上去的嘴和脸的透视不协调，盲测读成惊讶。她很少大声说话，喊的场合多半是提醒别人危险，所以画成急着提醒，不画成凶。
- **参考图**：`GP-13_ref_a.png`（B_12，姿势不变）。
- **做法**：编辑，整张脸一起重画。
- **这一张自己的条目**：
  - G5 要特别看：嘴大张，下巴跟着往下，嘴跟着头的倾斜。
  - 缩到 40%，读得出在喊。
  - 红痕、角原样在。
- **中文说明**：急着出声提醒别人（她很少提高声音）。嘴张大，下巴往下，看得见上排牙；眉毛扬起、往中间挤（担心）；眼睛睁大。是急，不是凶，也不哭。一整张喊的脸，张开的嘴跟着头的角度。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, her silver-lavender hair with straight bangs, the single dark-red crescent horn, the low ponytail and its big red cord, the two short vertical red marks under her right eye (the eye on the LEFT side of the image), the white kimono with the dark-red collar, the hands, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, eyebrows, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face.

New expression — calling out urgently to warn someone (she rarely raises her voice): mouth open wide, the jaw dropped, the upper teeth visible; eyebrows raised and drawn together with worry; eyes wide. Urgent, not angry, not crying. Draw it as one shouting face, so the open mouth follows the angle of her head.

Sizes, compared with the original: the open mouth about a third wider and more than twice as tall as now; the chin lowered by about a third of the height of her iris; the eyebrows raised and drawn together; the irises slightly smaller.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-14　しをね · 开怀（grin）　重做

- **用在**：第一段她不说话。你点名重做（"垣外的開懷……也是"，G5R3-51）。
- **为什么重做**：原画 B_02 是睁着眼的圆张口，第一轮盲测读成喊；第四版把它改成一条细细的嘴角上扬的线，不自然。新的一张靠"笑弯的眼睛"读成高兴。
- **参考图**：`GP-14_ref_a.png`（B_02，挥手的姿势不变）。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 缩到 40%，眼睛是笑弯的，一眼读成"高兴"，不读成喊或惊讶。
  - 嘴不是一条细线。
  - 红痕、角原样在。
- **中文说明**：温暖、高兴的张口笑，像和朋友一起笑。眼睛笑成温柔的月牙（还微微睁着，看得见高光），下眼睑被脸颊推上去；脸颊抬起、淡淡的红；嘴张开成柔和的大笑，嘴角明显往上，露出一点上排牙。自然、温柔：嘴不是一条尖细的线，也不是喊的圆嘴。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, her silver-lavender hair with straight bangs, the single dark-red crescent horn, the low ponytail and its big red cord, the two short vertical red marks under her right eye (the eye on the LEFT side of the image), the white kimono with the dark-red collar, the waving hand, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, eyebrows, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face.

New expression — a warm, happy, open smile, like laughing with a friend: eyes curved into gentle crescents (still a little open, highlights visible), the lower eyelids pushed up by the cheeks; cheeks lifted with a soft blush; mouth open in a soft, wide smile with the corners clearly turned up and a little of the upper teeth showing. Natural and gentle: not a thin, sharp line of a mouth, and not a round shouting mouth.

Sizes, compared with the original: each eye about half as tall as now and curved like an upturned crescent, with part of the iris and its highlight still showing; the open mouth about as wide as now but only about two thirds as tall, with a flat upper edge showing a band of upper teeth and the corners clearly turned up. The original has faint pink hatching lines on her far cheek: leave them out and keep the blush as soft colour only.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-15　しをね · 认真（serious）　重做

- **用在**：第一段她不说话。你点名重做（"垣外的……認真也是"，G5R3-51）。
- **为什么重做**：第四版在原画 B_25 上压了眼睑、画了眉，看起来不自然。新的一张是温和而坚定的认真，像请对方停一下、听她说。抬手的姿势保留。
- **参考图**：`GP-15_ref_a.png`（B_25，抬手示意的姿势不变）。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 缩到 40%，读得出认真、平稳，和她的平常（B_10）分得开：眼皮更平，嘴是一条直线。
  - 不凶、不冷、不难过。
  - 抬起的手原样在。
- **中文说明**：平静而认真，温和地坚持，像在请人停下来听她说。眼神稳，直视右边听话的人；上眼睑略低、平直；眉毛平（透过薄刘海看得见）；嘴闭成一条直线。不生气、不难过、不冷淡。抬起的手原样保留。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, her silver-lavender hair with straight bangs, the single dark-red crescent horn, the low ponytail and its big red cord, the two short vertical red marks under her right eye (the eye on the LEFT side of the image), the white kimono with the dark-red collar, her raised hand, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, eyebrows, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face.

New expression — calm and serious, gently firm, as if asking someone to stop and listen: eyes steady and looking straight at the listener on the right, upper eyelids slightly lowered and straight; eyebrows level (they show through her thin bangs); mouth closed in a straight line. Not angry, not sad, not cold.

Sizes, compared with the original: the upper eyelids covering about a quarter of each iris, drawn straight; the lower eyelids slightly raised; the mouth line about as long as now, perfectly straight.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

### GP-16　しをね · 茫然（blank）　重做

- **用在**：第一段她不说话。这是她见到小鹊时说"我好像见过您"、自己也吓了一跳的那一刻要用的脸（characters.md）。你点名重做："垣外的茫然有點詭異，不夠自然"（G5R3-51）。
- **为什么重做**：第四版把她的虹膜褪成了灰色、去掉了高光，看起来像没有魂，诡异。新的一张是自然的出神：像一段模糊的记忆刚浮上来，人一下子走了神。
- **参考图**：`GP-16_ref_a.png`（B_35，提灯的姿势不变）。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 眼睛是正常的红色、有高光，不灰、不空、不发光。
  - 缩到 40%，读得出"走神了"，和她的平常分得开：视线不在对方身上，嘴微张。
  - 一点也不吓人。
- **中文说明**：自然地出神，像一段模糊的记忆刚浮上来，她一下子迷在里面。眼睛正常张开或略大，视线失焦，越过看的人飘到远处；眉毛中间略微扬起；嘴唇微微分开。虹膜照常是红色，高光都在，不要空、淡、灰、发光或空洞，一点都不诡异。

```text
Edit the attached image (my own character illustration). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, her silver-lavender hair with straight bangs, the single dark-red crescent horn, the low ponytail and its big red cord, the two short vertical red marks under her right eye (the eye on the LEFT side of the image), the white kimono with the dark-red collar, the hands and the lantern, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, eyebrows, gaze, mouth, cheeks and jaw — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face.

New expression — a natural, absent look, as if a faint memory has just surfaced and she has lost herself in it for a moment: eyes open normally or slightly wider, the gaze unfocused, drifting past the viewer into the distance; eyebrows raised a little in the middle; lips slightly parted. Keep her normal red iris colour and the eye highlights. Do NOT make the eyes empty, pale, grey, glowing or hollow. Nothing eerie.

Sizes, compared with the original: the eyes the same height as now or up to a tenth taller; the irises shifted very slightly upward, both looking the same way, into the distance; the inner ends of the eyebrows slightly raised; the lips parted by a thin dark gap. The original has a few short pink-red strokes on her far cheek (below the eye on the right side of the image): leave them out. Her only markings are the two red marks under the eye on the left side of the image.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original: clean anime line art and soft cel shading. Not painterly, not realistic, not 3D, not pixel art.
```

## 7. 婆婆：GP-17…GP-20（已定要做，G5R3-65）

- 用户答 C.1 选 A（G5R3-65，`portrait-faces-seg1.md` C.1）：四项都做；外观的四项默认值先照画，用户看了再说。
- **顺序**：先做 GP-17。建议你先只把它交回：我们转成游戏里 128 像素的立绘、放进对话框给你看，你对设定和像素效果都满意了，再做 GP-18…20。三张表情都是在 GP-17 上编辑的，GP-17 不对，后面三张都要重来。
- **剧本里写了的**（第 0 场事实表和台词）：
  - 七十上下；庄屋当家的母亲。
  - 膝盖不好：坐在后门里的木台阶上，撑着膝盖、"哎哟哟"一声才站起来。
  - 手指头不大听使唤。
  - 头发以前是黑的，现在不是了（"刻这道那年，我头发还是黑的"）。
  - 这些年在缩，现在比小鹊高一点（"早晚跟你一般高"）。
  - 眼镜一早被屋里的小的藏了，看什么都眯着眼。
  - 用袖口擦鼓槌：穿的是有袖子的和服。
  - 从台词读得出的性格：先喂吃的，请求只说一半，拿膝盖和年纪自嘲，好意不上脸（script-04 的人物表；第五版 1.2 节）。提示词里写成"gruff, practical and dry-humoured, warm underneath"。
- **剧本里没写、提示词里先填了默认值的**（G5R3-65：先按默认画；以后要改，就改提示词里"Appearance"那一句）：
  1. 发型：白发在脑后挽一个小髻。
  2. 衣服：洗旧了的藍染木棉单衣，小花纹，袖子是普通的。
  3. 一条深色的前挂け（围裙）。
  4. 不拄拐杖，不戴首饰。
- **刻意不画的**：
  - 眼镜：第 0 场被藏了，以后要戴眼镜的立绘是以后的内容。
  - 某一地的乡土服饰：剧本 7.3 节说村子的地域还没定，等那件事定了再说。

### GP-17　婆婆 · 设定，兼平常脸（neutral）　新画

- **用在**：平常的 10 句（0-01、0-03、0-05、0-11、0-13、0-20、0-22、0-29、0-31、0-32）。
- **参考图**：
  - `GP-17_ref_a.png`（B_01，しをね）和 `GP-17_ref_b.png`（C_01，さぢ），只作画风参考：线条、上色、细节的密度、人在画布里的大小。
  - 用两个不同的人，是为了让 ChatGPT 明白这是"画风"，不是要照着画某一个人。
  - 你手上第二版素材包里有一张"庄屋的婆婆"概念图（`concepts/Tiangan_v2_village_matron_concept.png`），**不附**：它带拐杖、笑着睁眼，和剧本里的她不一样，附上它 ChatGPT 会照着画。
- **做法**：新画（她没有原画）。
- **GP-17 自己的合格标准**（代替 4.1）：
  1. 一眼看得出七十岁上下：白发、眼角和嘴边的皱纹、背有点驼。
  2. 眯着眼（不戴眼镜）；嘴是一条有点不高兴的线。
  3. 和两张参考图并排，像同一个画师画的：线条粗细、上色方式、细节密度一致。
  4. 不像参考图里的任何一个女孩：不带角、发箍、红绳、她们的衣服。
  5. 全身一个人，四分之三侧身，朝画面右边；双手空着、不挡脸。
  6. 1024×1536 竖图，真透明（G3）；没有文字、色卡、多视图、背景、地面的影子；没有漫画符号（G6）。
  7. 头的大小和参考图里的女孩差不多：两眼相距约 60–75 像素；全身约 6–7 个头高（4.3），背驼一点会矮一些。
  8. 缩到 45%（G10）还认得出是个眯着眼的老太太。
- **中文说明**：
  - 照两张参考图的画风，画同一个故事里的一个新人物：一个七十岁上下的山村老太太，村里头一户种田人家（庄屋）当家人的母亲。
  - 头发老了变白（三十年前还是黑的）；膝盖不好，手指有点僵，人越缩越矮，站着有点驼背。
  - 脾气粗、实在、嘴上不饶人，心里疼人。
  - 今天眼镜被藏了，看什么都眯着眼，眼角有细纹。
  - 外观按上面四项默认值。
  - 一个人，全身，站着，四分之三侧身朝画面右边，头朝右，手放松、空着；平常的表情：眯着眼，嘴抿成一条有点不高兴的线。
  - 画布 1024×1536，透明底；人和参考图里的女孩一样比例，头在画面里差不多大。
  - 不要文字、标签、色卡、别的视图、背景、地面的影子，不要漫画符号。

```text
Create a full-body illustration of a NEW character for the same story, drawn in exactly the same style as the two attached images: the same clean anime line art, soft cel shading, line weight, colouring and level of detail. She is a different person: do not copy the girls' faces, hair, horns, headbands, cords or clothes.

Who she is: an old woman of about seventy in a Japanese mountain village, the mother of the head of the village's leading farming household. Her hair has turned white with age (thirty years ago it was still black). She has bad knees and slightly stiff fingers, and she has been shrinking with age: she stands a little stooped. She is gruff, practical and dry-humoured, warm underneath. Her glasses have been hidden today, so she squints at everything: her eyes are narrowed into a squint, with fine wrinkles around them.

Appearance: white hair pulled back into a small bun; a plain, faded indigo cotton summer kimono with a small pattern and ordinary sleeves; a dark apron (maekake) over it; work-worn hands; no glasses, no walking stick, no jewellery.

Pose and framing: one figure, full body, standing, in a three-quarter view facing the RIGHT side of the image like the girls in the attached images, her head turned toward the right, arms relaxed and hands empty, nothing in front of her face. Expression: her ordinary look, the squint and the mouth set in a slightly grumpy line. She must read as elderly at a glance: white hair, wrinkles, a slight stoop.

Proportions and colours: her head about the same size as the girls' heads, and the same kind of anime face as theirs, only old (not realistic); the squint drawn as narrowed, curved eyelids with a little of the dark iris still showing, so that other expressions can be made from this picture later; the kimono a soft, greyish faded indigo, clearly lighter and greyer than deep navy; the apron dark charcoal; the hair white with cool grey shading.

Canvas: 1024 x 1536 (portrait). Draw her at the same scale as the girls in the attached images, so that her head is about the same size on the canvas (the distance between her eyes about 60 to 75 pixels).

Output rules:
- One PNG with a transparent background: a real alpha channel, not a painted checkerboard.
- No text, no labels, no colour swatches, no extra views, no background scenery, no ground shadow.
- No manga symbols: no sweat drops, anger marks, exclamation or question marks, blush lines or sparkles.
```

### GP-18　婆婆 · 笑（smile）　编辑 GP-17

- **用在**（2 句）：0-06 "孙子们早就高过你这道了。"、0-08 "我啊，越缩越矮。早晚跟你一般高。"。
- **参考图**：你通过的 GP-17（就是你交回的那张）。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 翻页检查（G4）：对照 GP-17，只有脸在变。
  - 缩到 45%，读得出是在打趣地笑；眼睛笑成缝，有笑纹。
- **中文说明**：干巴巴的、打趣人的老太太笑（她刚拿别人、也拿自己开了个玩笑）。眼睛挤成弯弯的缝，眼角深深的笑纹；脸颊被推上去；嘴是闭着的、有点歪的笑，或者微微张开。暖，带一点坏。不脸红。

```text
Edit the attached image (my own character design of an old village woman). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, her hair, her clothes and apron, her hands, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. She has no glasses: keep it that way. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, eyebrows, mouth, cheeks, jaw and the wrinkles — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face.

New expression — a dry, teasing grandmother's grin (she has just made a joke at someone else's expense, and at her own): eyes squeezed into curved slits with deep laugh lines at the corners; cheeks pushed up; mouth in a crooked, closed-mouth grin, or slightly open. Warm and a little mischievous. No blush.

Sizes, compared with the original: the eyes almost closed into curved slits; the laugh lines at the corners of the eyes clearly drawn; the corners of the mouth turned up enough to see when the picture is small.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original.
```

### GP-19　婆婆 · 怀念（wistful）　编辑 GP-17

- **用在**（4 句）：0-09 "刻这道那年，我头发还是黑的。"、0-10 "可惜了那面鼓。"、0-12 "顶上还差一个人。"、0-19 "我知道一个。"。
- **参考图**：你通过的 GP-17。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 翻页检查（G4）。
  - 缩到 45%，读得出在想从前的事：垂着眼看近处。
  - 没有泪、没有水光。
- **中文说明**：安静的、只属于她自己的怀念。眼皮垂下，看着身前近处的一样东西（木柱上一道旧刻痕）；眯着的眼放松了；嘴放松，带一丝很淡的、有点伤感的笑。没有泪，没有水光。

```text
Edit the attached image (my own character design of an old village woman). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, her hair, her clothes and apron, her hands, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. She has no glasses: keep it that way. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, eyebrows, mouth, cheeks, jaw and the wrinkles — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face.

New expression — quiet, private nostalgia: eyelids lowered, looking down at something close in front of her (an old mark carved into a wooden post); the squint softened; the mouth relaxed, with the faintest sad smile. No tears, no wet shine.

Sizes, compared with the original: the upper eyelids lowered further, so that she is clearly looking down; the mouth softer and relaxed, the faint smile small but visible.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original.
```

### GP-20　婆婆 · 板脸（stern）　编辑 GP-17

- **用在**（5 句）：0-15 "十。小笠，这盏别算进去。"、0-16 "这是回来用的……"、0-18 "说这话的先摔。"、0-24 "把眼镜还我。"、0-26 "变？它敢。"。
- **参考图**：你通过的 GP-17。
- **做法**：编辑，只改脸。
- **这一张自己的条目**：
  - 翻页检查（G4）。
  - 缩到 45%，读得出在训人：眉头压下、眯眼瞪着、嘴角往下。
  - 是长辈训孩子的板脸，不是恨、不是真的发火。
- **中文说明**：板着脸训人。眉头往中间、往下压；眼睛眯成严厉的一条缝；嘴抿着往下撇，像在冲一个淘气的孩子甩一句话。严厉里带着疼：不是真生气，不是恨。

```text
Edit the attached image (my own character design of an old village woman). Change ONLY her facial expression.

Keep exactly as in the original: the angle and tilt of her head, her hair, her clothes and apron, her hands, the pose, the body and its proportions, the size and position of the figure on the canvas, the line art and colouring style, every colour. She has no glasses: keep it that way. If I flip between the original and your result, only the face should change.

Redraw the whole face — eyes, eyelids, eyebrows, mouth, cheeks, jaw and the wrinkles — as ONE expression that fits the angle of her head. Do not paste new eyes or a new mouth onto the old face.

New expression — gruff and scolding: eyebrows drawn together and down; eyes narrowed into a hard squint; mouth pressed into a frown with the corners turned down, as if snapping a short order at a naughty child. Stern but fond: not truly angry, not hateful.

Sizes, compared with the original: the eyebrows clearly lowered and pulled together; the eyes narrowed to a hard squint; the corners of the mouth turned down clearly enough to see when the picture is small.

Output rules:
- One PNG, the same canvas size and shape as the original (1024 x 1536, portrait).
- Transparent background: a real alpha channel, not a painted checkerboard.
- No text, no speech bubbles and no manga symbols: no sweat drops, anger marks, exclamation or question marks, thought bubbles, puffs of air, blush lines, sparkles or music notes.
- No tears and no wet shine on the eyes or cheeks.
- The expression must read at a glance even when the picture is shown small (her face about 60 pixels wide).
- Same drawing style as the original.
```

## 8. 交回

### 8.1 文件名

一项一张，PNG，ChatGPT 下载下来的原图，不要缩放、不要裁、不要另存成 JPG。

| 编号 | 文件名 |
|---|---|
| GP-01 | `GP-01_tsuzumi_serious.png` |
| GP-02 | `GP-02_tsuzumi_evasive.png` |
| GP-03 | `GP-03_tsuzumi_downcast.png` |
| GP-04 | `GP-04_tsuzumi_blank.png` |
| GP-05 | `GP-05_tsuzumi_smug.png` |
| GP-06 | `GP-06_tsuzumi_shout.png` |
| GP-07 | `GP-07_tsuzumi_pout.png` |
| GP-08 | `GP-08_tsuzumi_think.png` |
| GP-09 | `GP-09_saji_pout.png` |
| GP-10 | `GP-10_saji_shout.png` |
| GP-11 | `GP-11_saji_smug.png` |
| GP-12 | `GP-12_shione_pout.png` |
| GP-13 | `GP-13_shione_shout.png` |
| GP-14 | `GP-14_shione_grin.png` |
| GP-15 | `GP-15_shione_serious.png` |
| GP-16 | `GP-16_shione_blank.png` |
| GP-17 | `GP-17_granny_neutral.png` |
| GP-18 | `GP-18_granny_smile.png` |
| GP-19 | `GP-19_granny_wistful.png` |
| GP-20 | `GP-20_granny_stern.png` |

（小鹊的文件名用 tsuzumi，和游戏里的 id 一致。）

- **用了绿底退路的**：文件名末尾加 `_green`，例如 `GP-03_tsuzumi_downcast_green.png`。
- **一项有两张都满意的**：多交一张，末尾加 `_b`，例如 `GP-06_tsuzumi_shout_b.png`。最多两张，我们一起转、一起盲测，挑好的那张。
- **跳过的项**：交回时说一句是哪一项、哪里不行。

### 8.2 怎么交

- 全部打成一个 zip，在 Claude 的对话里直接上传；或者放进上次那个 Google Drive 文件夹，告诉我们文件名。
- 可以分批：先交 GP-01…GP-16；婆婆的 GP-17 单独先交，你看过、满意了再做、再交 GP-18…20（第 7 节）。

## 9. 我们收到以后怎么验收

1. **文件**：查 PNG、2:3、真透明（绿底的用色键抠：去掉绿，再把边上的绿色压回去）、一张一个人。
2. **对位**：
   - 把新图和参考图按脸以外的部分（笠、头发、衣服）配准。位移超过 2 像素、缩放差超过 2% 的，按 G4 退回那一项。
   - 脸以外有细微变化的，转换前把新图的脸按一块遮罩贴回原画上，只换脸。这一步是我们做，不用你做。
3. **比例**：量两眼间距、眼到下巴，落在 4.3 的范围里。
4. **转像素**：
   - 用第四版的管线，同一套取景，用这个人原来的调色板（`palette: False`），所以她其余各张一个像素都不变。
   - 不再往图里画白气、"！！"这类符号（G5R3-51、G5R3-13）。
   - 只在转换丢掉了细线（睫毛、嘴线、眼里的高光）时补回来，记在 `tools/art/portraits4/edits/`。
5. **盲测**：
   - 三位从没见过这些图的独立测试者，各自新开一个进程，只给打乱、去名的立绘，从表情词表里选。
   - 所有立绘混在一起测，包括新增的避开视线、低落、茫然、得意。
   - 及格线：每张新图至少 2/3 的人读对；喊不再被读成惊讶；小鹊的六张安静的脸（平常、认真、避开视线、低落、茫然、得意）彼此不混。
6. **和第四版并排给你看**：新旧放在一起，用游戏里的对话框、×3。重做的那 11 张由你逐张决定换不换：G5R3-9 说的，只在更好的时候才换。
7. **某一张不过**：只重做那一张，用同一个提示词，加一句它没过的原因（第 5 节的句子），清单本身不变。

## 10. 这份清单为什么是完整的

**覆盖了哪些来源的需求：**

1. **你点名的**（G5R3-51）：三个人的鼓腮（GP-07、09、12）、三个人的喊（GP-06、10、13）、しをね的开怀（GP-14）、认真（GP-15）、茫然（GP-16）、小鹊的思考（GP-08）。十张全在，不管这一段用不用。
2. **盲测一直错的**（knowledge/13 §10.5、§10.10）：
   - 小鹊的平常、认真、坚定同一张脸：重做认真（GP-01），坚定不再单独使用（`portrait-faces-seg1.md` B.4）。
   - 喊被读成惊讶：在第 1 条里一起重做。
   - 生气用的是"警惕"的原画：不重做，因为你夸过它（G5R3-9），第四版三轮盲测都读对；理由在 `portrait-faces-seg1.md` B.2。
3. **剧本要的**：第五版 121 句逐句排了表情（`portrait-faces-seg1.md` A 表）。小鹊、さぢ用到的每一个表情，不是现有的留用图，就是这份清单里的一项（B.1）。
   - 新增的五张：GP-02…05、GP-11。
   - 中文稿接下来重写（G5R3-55），场次、事件、情绪走向不变；重写只能用这里定下的表情，所以重写不会产生新的需求。
4. **婆婆**：C.1 已定 A（G5R3-65），GP-17…20 都做。
5. **行商、乌鸦、收音机**：推荐不出立绘（C.2）。
6. **しをね**：这一段她不说话，只有点名的五张。

**什么情况下会出现新的需求**（那是新内容的新清单，不是这一份的第二版）：

- 以后的剧本：新手区后面几段、第一章；しをね在废寺登场的台词。要用到现在 53 张加上这 20 张里都没有的表情时。
- 新人物：难民、庄屋的其他人；行商如果成了常来的商人。
- 婆婆戴眼镜的样子：只在以后有她戴眼镜的场景时。
- 村子的地域定下来以后（剧本 7.3 节），如果要让婆婆穿那个地方的衣服：那是新的设定决定，GP-17 照新的设定重画。
- 你在实机里对某一张提出新的意见。
- 3D 人物要的设定图（三视图等）：那是人物攻关的事，不是对话立绘（G5R3-20）。

## 11. 自查（交出前逐条核过）

- [x] A 表 121 句，每一句都有表情或"不出立绘"（小鹊 59、さぢ 32、婆婆 21 两种情况、行商 4、乌鸦 3、收音机 2），和剧本 1.4 节的统计一致；脚本从中文演出稿逐句抽出，再和日文原稿逐场对齐，每场句数相同。
- [x] B 里每个用到的表情都有来处：现有的留用图，或 GP-xx。
- [x] 现有 53 张逐张归类：留用 13、重做 11、合并 1、用不到保留 28。
- [x] 编号 GP-01…GP-20 连续、不重复。每一项都有：人物、表情、用途、重做的原因或新增的理由、参考图、做法、提示词、这一项自己的合格条目。
- [x] 参考图文件都在 `portrait_refs/` 里，文件名以编号开头。
  - GP-01…16 各一张 `_ref_a`；GP-17 两张（`_ref_a`、`_ref_b`），全部是 1024×1536 的原图；
  - GP-18…20 用你交回的 GP-17，没有我们这边的文件；
  - 原画的 SHA-256 和原包 manifest 里记的一致（抽查了 A_35、A_12、A_04、A_34）。
- [x] 用户点名的十张都在（第 10 节第 1 条）。
- [x] 盲测的问题都处理了：同脸三张、喊读成惊讶；生气不重做，写了理由。
- [x] 婆婆：C.1 已定 A（G5R3-65），清单不用改。
- [x] 上次不合格的四个原因，各有对应的条目：
  - 比例偏成熟：编辑代替新画，加上 G4、G9、4.3；
  - 半透明的泪：G7；
  - 读不出来，缺符号：G10，并且要求不靠符号也读得出；
  - 灰底没有透明通道：G3、4.4，提示词里不给第二个选择。
- [x] 刘海盖住眉（G5R3-8）：小鹊每一项的提示词都写了。
- [x] 朱痕在右眼下（G5R2-10）：しをね每一项的提示词都写了。

## 出处

- IT Brief，"OpenAI launches Images 2.5 with faster editing tools"（2026-09-08）：<https://itbrief.news/story/openai-launches-images-2-5-with-faster-editing-tools>
- Qwen-Image-Bench（arXiv 2605.28091，2026）：<https://arxiv.org/abs/2605.28091>。中英文提示词的对比在附录 A.3、表 2 和表 5，下载 PDF 读的。
- OpenAI 帮助中心：ChatGPT Images（<https://help.openai.com/en/articles/11084440-chatgpt-images>）、编辑图片（<https://help.openai.com/en/articles/9055440-editing-your-images-with-chatgpt-images>）。这两页对本机返回 403；选择工具、改动会溢出、可去背景这几点来自搜索引擎对它们的摘要，没有读到原文。
- OpenAI 社区，"Gpt-image-1 - Transparent backgrounds with Edit request"：<https://community.openai.com/t/gpt-image-1-transparent-backgrounds-with-edit-request/1240577>。有人报告"透明"其实是画上去的格子，同样来自搜索摘要。
- 本地：knowledge/13 §10（第四版的做法、盲测、上次素材不合格的原因）；`tools/art/portraits4/config.py`（每个表情的原画和两眼坐标）；原画包 manifest.csv（每张原画的动作说明和 SHA-256）。
