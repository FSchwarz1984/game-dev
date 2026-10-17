# 30 自适应音乐与音效：研究（G5R3-53，2026-10-17）

> 用途：声音与音乐提案（`docs/design/audio-music-draft.md`，工作队列第 5 项）的依据。
>
> 规矩：每一条都附我亲眼读过的出处，访问日期都是 2026-10-17。只读过摘要的写明"只看了摘要"；翻译的二手出处（例如 Nintendo Everything 翻的原声带小册子座谈）标明是翻译；没核实的放在 §10，不当结论用。日文、英文原话照引，中文是我的译文。
>
> 访问方式：网页用 curl（User-Agent 是中性的 `TenganAssetBuild/1.0`）下载到草稿区的空目录，用标准库把 HTML 转成文本再读；少数页面用检索工具定位。没有带任何用户信息。Godot 的部分同时核对了本机的 4.7.2 源码（`/home/user/godotengine/godot`，提交 ed1daf0b "Bump version to 4.7.2-stable"）。
>
> 这里没有声卡，所有关于"好不好听"的判断都不是我能做的。本篇只记录别人怎么做、工具能做什么、条款怎么写。

## 0. 先说结论

1. **旷野之息的野外几乎不放音乐，这是设计出来的。** 声音总监若井淑说，世界无缝相连，太有主张的声音会影响游戏设计；他们按"那里有东西，所以听得见这个声音"来做声音，BGM 也是这个思路的延长。团队不再说"世界 BGM"，改叫"环境 BGM"：环境声本身就是 BGM（§1.1）。
2. **钢琴是旷野之息野外的主乐器**，用来表现大的开放世界；主题曲另加篠笛、二胡、太鼓、佛铃，避免"所有管弦乐听起来都差不多"（§1.4）。
3. **异度神剑 2、3 的区域曲成对：每个区域一首昼、一首夜，同一个作曲者**（§2.1）。第 3 作把主题交给故事里真的乐器（主角们的笛子，照篠笛做的、真做出来录音），140 首曲子共用这个乐器作主题（§2.2）。
4. **久石让**出身极简音乐；《苍鹭与少年》里现实世界只用钢琴和少数乐器，"保持距离"，不用音乐解释画面，一段音乐删到只剩一个音（§3.1）。日本动画常见的工作法是先写"イメージアルバム"，片中用它的片段和变奏（§3.1）。
5. **战斗音乐只给真正的战斗**（Ori）；**没有无处不在的旋律，冲击更大**（Silksong）；**每首曲子至少两层，进小地方淡出大编制**（Silksong）；**每首曲子有自己的层，按位置淡入淡出**（A Short Hike）（§4）。
6. **对马岛之魂的环境声是数据驱动的**：什么物种、何时、何地、多频繁；随时刻、天气、地区自适应；引导之风里叠了"吹得不完美"的竹笛（§4.8）。
7. **合成的局限**：无人深空的 Paul Weir 说程序化合成"仍然不适合做写实的声音"，他不赞成用它做风雨，因为自然声里有我们马上会反应的复杂性质（§4.10）。这是我们走合成路线必须正视的风险。
8. **Godot 4.7 有现成的自适应音乐资源**（AudioStreamInteractive、Synchronized、Playlist、Randomizer），但有硬限制：交互流报不出播放位置（源码里直接返回 0）、不能 seek、没有 stinger、一首里不能变速、淡化是线性幅度、同步流的分层音量按 128 帧一块跳变不平滑；没有卷积混响；GDScript 做逐样本合成太慢（官方文档建议 C# 或 GDExtension）（§5.3）。
9. **免费音源**：钢琴、竖琴、打击、管弦有 CC0 和 CC-BY 的成套音源（VSCO 2 CE、VCSL、Salamander），但**没找到 CC0 / CC-BY 的日本乐器音源**（筝、三味线、尺八、篠笛、太鼓）（§7）。
10. **AI 音乐服务的条款这一年变化很大**：Udio 现在禁止下载和商用；Suno 付费档可商用但只限"许可的下载"、不保证有版权；ElevenLabs 对"独立游戏"开放付费档、禁止在提示里写艺术家名和曲名（§7.5）。
11. **请作曲家的行情**：GameSoundCon 2025 年调查，独立游戏按完成的每分钟音乐收费，中位数 407 美元、平均 618 美元（§7.4）。

## 1. 旷野之息、王国之泪

### 1.1 "环境 BGM"：先有世界里的声音，再有音乐

**ファミ通的开发者访谈后编（2017-04-21）**，声音总监若井淑：

> 「今回は世界がシームレスにつながっているので、あまりに主張が強いサウンドになると、ゲームのデザインにも影響を与えてしまうので、よくないだろうな、と考えたんです。そういう意味で、今回は、物や場所そのものから鳴る音作りを意識して作っています。"このシチュエーションだから"ではなく、"そこに物があるからこういう音が聞こえるんだ"と。BGMもその考えの延長で、その場所に合わせて付けていった感じですね。」

（这次世界无缝相连，声音太有主张会影响游戏设计。所以这次有意识地做"从东西、从地方本身发出的声音"：不是"因为是这个情境"，而是"因为那里有东西，所以听得见这个声音"。BGM 也是这个思路的延长，按那个地方来配。）

> 「世界自体の表現としてBGMを使っているケースが、いままでのシリーズより多いと思います。」（把 BGM 当成世界本身的表现来用，比系列以往都多。）

同一篇里：采访者举了"远处传来手风琴，就知道吟游诗人卡西瓦在附近"；若井说祠的 BGM 是声音组里最难拿捏的，"やり過ぎるとヒントになってしまうので"（做过头就成了提示）。声音组直接用地图编辑器摆声音，"プログラマーだけでなく、コンポーザーも設定できる"（不光程序员，作曲家也能设）。

**原声带小册子的座谈**（日版原声带，2018；**Nintendo Everything 的英译，2019-01-05**，三页）：

- 若井："There was a logic behind having no music in the open world. ... When a composer makes a piece of music he has a plan and idea of how he wants to player to feel, but if this insistence is too strong it can have an effect on the actual game. We would end up forcing a feeling of intensity onto players. The music would be all stirring and dramatic, but then the player would think: 'hold on a minute, all I did was throw away a mushroom…'"（开放世界里不放音乐是有道理的……作曲的人总有想让玩家怎么感受的打算，主张太强就会影响游戏本身：音乐澎湃激昂，玩家却想"等一下，我只是扔了个蘑菇……"）
- 片冈万奈花："sticking with a BGM that allows them to hear the environmental noise and footsteps can really have a beneficial influence on their awareness of the world around them. ... we sacrificed some of the music so that the player could really experience the environment"（让玩家听得见环境声和脚步的 BGM，会让他们更意识到周围的世界……我们牺牲了一部分音乐。）
- 若井："We stopped using the phrase 'World BGM' and replaced it with 'Environmental BGM'. It wasn't just environmental noise and it wasn't just BGM, but the environmental noise becoming the BGM."（不再说"世界 BGM"，改叫"环境 BGM"：环境声成为 BGM。）
- 岩田恭明：一开始连城镇的 BGM 都想去掉；"we tested how far you had to be from a temple before the music changed, and how loud that music would be"，三个人在海拉鲁走了大约一个月，试离 temple 多远音乐开始变、变多响（temple 是英译的用词，日文原文没看到，可能指祠）。
- 若井："This huge game world is made with these areas of sparsity and density, and so we tried to replicate that variation of dense and thin."（世界有疏有密，声音也照这个疏密来做。）
- 片冈：加入团队后觉得游戏像一个"克己的硬核生存游戏"，于是和若井商量加一点清新、欢迎的感觉，"adding depth to the different phases of day, between daytime and night"（给白天和夜里各个时段加深度）。

### 1.2 曲目结构

日版原声带（日本コロムビア，2018，COCX-40308）的曲目里（我看的是 Bookoff 的商品页上的曲目表）有：「フィールド(昼)」「フィールド(夜)」「襲歩(昼)」「襲歩(夜)」（襲歩是马的全速奔跑）、「フィールド(極寒)」「フィールド(灼熱)」「フィールド(酷暑)」「戦闘(フィールド)」「馬宿」。即：野外曲和骑马曲都分昼夜两版，另有按气候的变体。游戏里什么时候切换，我没有找到官方说明（§10）。

### 1.3 随时间、随进度变

同一篇ファミ通访谈，若井："あれは段階を追って変化させて、気づく人は気づくように仕上げています。一方、村などは、時間経過に合わせて少しずつテンポや楽器を変えていくので気づきにくいかなと。"（神兽里随着启动终端一段段变化，留心的人听得出来；村子则随时间一点点改速度和乐器，不容易察觉。）

### 1.4 主乐器与主题

- 钢琴（NE 座谈，若井）："the idea with changing the usual Zelda score was to express this feeling of a large, open-world. So, I thought: isn't it OK to use a large instrument that isn't necessarily portable? In the end I decided on a piano"（要表现大的开放世界，用一件不能随身带的大乐器也可以吧，最后定了钢琴。）
- 主题曲（片冈）：管弦乐团演的大曲听起来都差不多，所以主题曲里加了不常用的乐器："the Japanese bamboo flute or the 'Erhu (Chinese flute)'"（原文如此，二胡其实是拉弦乐器），"for percussion we mixed in Taiko drums and Buddhist bells"。
- 主题的用法（若井）："we were careful not to put in those references all over the place without meaning"（不在没有意义的地方到处引用主题）。
- 减法：座谈里岩田说，若井曾要他把一首曲子"cut the music and make it soundless"，再一点点加回去；"By hollowing out the music in order to emphasize the speech, I think ultimately that gave more life to both the words and the music."（把音乐掏空来突出台词，台词和音乐都更有生命。）英译里看不清这说的是哪一首。

### 1.5 王国之泪（任天堂「開発者に訊きました」Vol. 9，新加坡站英文版）

- 第 3 章，若井："Sound transitions are done seamlessly as well, but the background music in particular needed to change according to the situation. Because of this, we needed to place transition triggers to indicate where the music should switch."（声音的过渡是无缝的，但 BGM 要按情境切换，所以要摆"过渡触发点"标出在哪里切换。）声音组常常追问程序：地面和天空的分界线到底在哪。
- 第 5 章，若井想让玩家注意的："the sense of distance created as a player moves away from a nearby sound and it becomes increasingly hazy and echoey, disappearing into other ambient sounds"（离近处的声音越来越远时，它变得越来越朦胧、带回声，最后融进别的环境声）；从前作起就按环绕声做，耳机和立体声音箱都能听出来。
- 第 4 章：比起不写实的抽象声音，"'unrefined sounds' that give players a more realistic sense of texture and accomplishment often feel right"（给人真实质感和成就感的"粗粝的声音"往往对）；"粘上"的声音会反复听到，所以关键是让它带来成就感，让人真心享受这个过程。
- 第 2 章：用拍手等声音在音乐里表现"手"的主题；得到东西、解开谜题这类标志性的声音沿用前作。

### 启示

- 野外默认是"环境 BGM"：风、水、虫、鸟、脚步就是音乐的一部分；音乐是少量、短小、留白多的片段。
- 地点主题要能"走近才渐渐听到"，半径和音量要在地图上一个个调（他们走了一个月）。
- 最常听到的声音（"粘上"）要花最多心思，目标是"愿意一直听"。
- 远的声音变朦胧、带回声、融进环境：这和我们的遠化（"看得见却不再近"）是同一个方向。

## 2. 异度神剑

### 2.1 区域曲的昼夜两版

光田康典的公司 PROCYON STUDIO 的原声带页面（官方）：

- 《异度神剑 2》原声带：アヴァリティア商会/夜、グーラ領/夜、トリゴの街/夜、フレースヴェルグ傭兵団/夜、インヴィディア烈王国/夜、首都フォンス・マイム/夜、帝都アルバ・マーゲン/夜、スペルビア帝国/夜、リベラリタス島嶼群/夜、故郷/夜、ルクスリア王国/夜……；黄金之国 DLC 另有イーラ王国/夜、王都アウルリウム/夜。
- 《异度神剑 3》原声带（142 曲）：イザナ平原、イザナ平原/夜（作曲、编曲同为 ACE）；ミリク平原、ミリク平原/夜（同为平松建治）；アルフェト渓谷/夜、イーグス荒野/夜、リビ平原/夜、ダナ砂漠/夜、レーベ高原/夜、コンティ大瀑布/夜、モルクナ大森林/夜、シウェラ浮遊岩礁地帯/夜、エルティア海/夜……，几乎每个区域、殖民地都有夜版，昼夜由同一作曲者写。

### 2.2 《异度神剑 3》：主题由故事里的乐器来演（「開発者に訊きました」Vol. 6 第 2 章）

- 送行人（おくりびと）的身份用乐器表现；打击乐难表现沉重和感伤，弦乐要够大才好听，主角们要战斗，只能随身带，于是光田建议了篠笛，高桥哲哉喜欢它的声音和"日本的味道"。
- 光田在动笔前提出"先做笛子"："By making the flutes from scratch, you can create a sound that hasn't been heard before."（从零做笛子，能做出没人听过的声音。）笛子在 MONOLITHSOFT 设计，请篠笛匠人照做、漆匠上漆，真拿来录音。诺亚的笛子大一点、音低一点，弥央的小一点、音高一点，两支笛子的音阶不同，两人的旋律交织成一首。
- 高桥："Using these flutes, he had to create melodies that sound good in isolation while keeping in mind that the flutes' sound would also be used as a theme across different scenes."（旋律单独听要好听，同时笛声要在感人、悲伤、温柔、战斗各种场面里当主题。）
- 约 140 首曲子。原因（高桥）："Even if the melody is the same, we want a slightly different sound in scenes where the emotions are different."（同一个旋律，情绪不同的场面里也要有一点不同的声音，所以要更多变体。）
- 分工：故事相关的曲子主要是光田、Mariam Abounnasr、清田爱未；环境相关的主要是 ACE 和平松建治；大家约定用笛子演主题，所以合起来是一部作品。
- 场面切换（野外→战斗→过场）尽量不读盘、无缝，这是系列第一次尝试，"很有挑战"。

### 启示

- 同一个区域的昼夜两版，结构相同、配器和色彩不同，才能在黄昏无缝交叉。
- 主题交给故事里看得见的乐器，比让配乐空降一个主题更有说服力。我们的故事里正好有这样的乐器：遠囃子的笛和鼓（天岸的祭典）、盆踊的鼓、她哼的半句（见 `docs/design/script-05-draft.md` 第 3 场、`story.md`）。

## 3. 久石让与宫崎骏；新海诚

### 3.1 久石让

- 官方简历（joehisaishi.com/biography，日英双语）：以现代音乐作曲家出道，音乐大学毕业后对极简音乐产生兴趣，1981 年发表「MKWAJU」，次年的「Information」是他作为独奏艺术家的起点；从《风之谷》（1984）起为宫崎骏的 11 部电影作曲。
- Classic FM 的访谈（2025-10-31）："I love minimal music ... It's like Baroque music"（像巴洛克，指有条理地重复的型）。北野武的片子"very minimal style and not so emotional style"，宫崎骏的动画"there is more emotional feeling"，对他是两回事。记者的概括（不是久石原话）：他的音乐融合了浪漫主义管弦乐的传统、极简主义的重复型和日本民间音乐的影响；擅长用简单好记的动机，编成宏大的配乐。
- Variety（2024-02-22，《苍鹭与少年》）：
  - 前半是孤独、带着阴暗的少年，后半是幻想世界；他用极简的方式、很少的音乐：现实世界里只有钢琴和少数乐器，到幻想世界才稍多一些。
  - 不想强调悲伤和情绪，也不想用音乐解释画面上的东西："I tried to keep a distance."
  - 苍鹭第一次出现在窗口：宫崎骏觉得不需要音乐；久石觉得是特别的一场，写了一段，"it was too much and too overblown ... I kept subtracting parts from the music, and finally, we ended up with just one note"，这一个音成了苍鹭的标志，下一次再加几个音。
  - 主题曲「Ask Me Why」在片中出现三次，"I use muted instrumentation and just play the piano"；"I threw away the concept of using variations of a theme throughout the film."
- イメージアルバム（Marco Bellano，《The Palgrave Handbook of Music and Sound in Japanese Animation》2024 年的一章；**我只看了摘要**）：日本动画的音乐制作通常先要一张"image album"——按前期资料、美术写的一组音乐；片中的交响乐段落是 image album 的变奏；久石为宫崎骏写的配乐很大程度上基于先以近乎音乐会形式写成的音乐。
- **没找到可靠出处的**：久石旋律的音阶特征（常被说是ヨナ抜き、五声音阶等）。检索到的论文都是讲ヨナ抜き音阶本身，不是分析久石的。这一条不当结论用。

### 3.2 新海诚

- Real Sound（2019-04-10，《天气之子》）：新海在《你的名字。》上映一周年那天把刚写完的剧本发给 RADWIMPS 的野田洋次郎，"想知道从这个剧本里，洋次郎的脑子里会响起什么声音"；收到「愛にできることはまだあるかい」后觉得"这是一部应该拍出来的电影"。双方和前作一样从剧本阶段就密集开会；重要场面用 RADWIMPS 写的几首歌，加上配乐。
- Real Sound（2022-09-20，《铃芽之旅》）：配乐由 RADWIMPS 和陣内一真合写，部分在 Abbey Road 录音。陣内："2人がそれぞれ独自にメロディを次々と作っていくとテーマ性が薄れてしまいます。洋次郎さんが担当されたシーンにも、私が担当したシーンにも、それぞれ音楽的なテーマが必要でした。"（两个人各自不断写新旋律，主题性就淡了；每场都需要音乐主题。）
- Real Sound（2016-09-02，高野裕也分析《你的名字。》的配乐）：按类型分四类：①以弦乐、钢琴为中心、西洋音乐成分多的；②用 pad 音色、没有明确旋律的氛围类；③以吉他为中心的乐队器乐；④也当配乐用的乐队歌曲。片中①最多，③只有 3 首；歌曲当配乐用时不跟画面对拍，"音乐自由进行，歌词含蓄地表达世界观"。

### 启示

- 音乐跟剧本一起开始，不是最后补上。
- 主题少而准：每个场面要有主题，但不同的人各写各的旋律会冲淡主题。
- 钢琴 + 少量乐器 + 留白，"保持距离"、不解释画面，比铺满更动人；删减本身是方法。
- 先写一组"概念曲"（イメージアルバム）定下主题和色彩，游戏里用它的片段和变奏，这正好对应自适应音乐。

## 4. 其它值得学的

### 4.1 大神（原声带小册子，上田雅美；Square Enix Music Online 的英译）

上田："There was really only a limited number of the instruments which we could use for Japanese style music and, for that matter, we could count the numbers of the instruments that could play a melody on one hand, like the shinobue or shakuhachi." 他想要的"治愈感"在现代和风音乐里找不到，反而在廉价的童谣 CD 里找到了。"A pure Japanese melody is quite beautiful, but often dark. ... I instead ignored anything theoretical and compromised with something that would sound Japanese-styled and soothing anyway."（纯粹的日本旋律很美，但常常是暗的……我不管理论，折中成听起来和风而又治愈的东西。）

### 4.2 Ori and the Will of the Wisps（Spitfire Audio 对 Gareth Coker 的访谈，2020）

- "we only have combat music when you *have* to kill something to progress. You're in and out of combat so quickly that changing the music from ambient to combat music feels gimmicky / gamey"（只有必须打倒才能前进时才放战斗音乐；进出战斗太快，从环境音乐切到战斗音乐显得廉价、"游戏味"。）
- 木管演奏者录了一大批笛子的渐强和装饰音："We used these for stingers in the game, but also for transitional bits (often with added reverb and delay) that kind of function as the classic cymbal roll, but…without the cymbal roll."
- "Ori's music is largely horizontal but changes sometimes on a granular level according to whatever actions Ori has completed in the game."（以横向为主，按 Ori 完成的动作做细粒度的变化。）他举的例子：一个机关房间每拉一次杆，音乐升高、加快、加乐器；难点在暂停、死亡、离开再回来时状态要对。
- 他给负责实现的 Guy Whitmore 发"叠好音乐的游戏录屏 + 字幕写明音乐怎么变 + 一份 PDF"。

### 4.3 A Short Hike

- 开发者 Adam Robinson-Yu（Nintendo Everything 访谈，2020-10-17）："He also went the extra mile and created unique layers for each piece that fade in and out depending on where you are."（作曲 Mark Sparling 给每首曲子做了独立的层，按你所在的位置淡入淡出。）
- Bandcamp Daily（2022-09-22）："the songs create a seamless musical map of A Short Hike's landscape, shifting in tone as the player traverses the island."

### 4.4 风来之国（Chucklefish 博客对 Joel Corelitz 的访谈，2021-08-31）

- "Each piece on the soundtrack is either about a place, a character, or a mood. We decided to start with a character"，从阿尔娃的主题开始，一块一块搭起来。
- 8 位、16 位的芯片音色，和更现代、更高解析的声音与制作结合。

### 4.5 星之海（Game Informer，2023-03-24）

- 普通战斗只有两首：一首白天、一首夜里，基本相同，夜版"more shiny bells and other subtle rearrangements"。
- 菜单音是听得最多的声音："I don't want it to sound retro. But I want it to sound pleasing."
- 作曲 Eric W. Brown：老游戏的曲子好记，是因为限制多、钩子强。

### 4.6 Outer Wilds（SPIN 对 Andrew Prahlow 的访谈，2020-06-17）

"instead of having a Traveler each playing their own tune on their planet, they're all playing the same song together like parts of a band. That's slowly revealed over time in the game"（各个星球上的旅行者不是各奏各的，而是像乐队一样合奏同一首歌的各个声部，游戏里慢慢揭示。）

### 4.7 Hollow Knight: Silksong（Bandcamp Daily 对 Christopher Larkin 的访谈，2025-11-10）

"All the tracks have two audio stems, at least, and it gives us a lot of flexibility with changing the instrumentation ever-so-slightly, so that whenever Hornet moves to a side area or a smaller area, Team Cherry can fade out the larger arrangement and we're left with something a bit more intimate. I'm really grateful that they chose to use some silence, as well. The impact is bigger if there's not an omnipresent melody."（每首至少两层；进入旁支或小的区域就淡出大编制，剩下更私密的；有些地方音乐完全停下；没有无处不在的旋律，冲击更大。）

### 4.8 对马岛之魂

- GDC 2021 演讲《Big World, Small Team: Designing a Scalable Ambience System for 'Ghost of Tsushima'》（Apoorva Bansal、Bradley D. Meyer；**我只看了 GDC Vault 上的摘要**）：音频组很小，世界比工作室以往大 14 倍；做了一套"随时刻、天气、地区和其他参数自适应的环境声系统"。
- A Sound Effect 对 Meyer、Josh Lord 的访谈（2020-07-22）：
  - 以前所有发声点都手摆，这次改成数据驱动："we control what species play when, where, and how often"；任务、登神社这类特别的地方仍然手摆。
  - 引导之风：声音沿三条样条线朝目标走（一条在玩家正上方、两边各隔约 5 米）；风随环境变，一侧是草原一侧是竹林时，两边分别是高草的沙沙和竹子的碰撞。
  - 从微风到暴风雪都要支持，同时"keeping the mix clean and minimizing a buildup of white noise"；引导风要和环境风分得开，叠了一层"吹得不完美"的竹笛录音，带一点像人声的质感但不做成魔法感。
  - 小细节：破屋里风从木板间灌进来，破纸门随风速抖动，屋顶的大木头吱呀。

### 4.9 荒野大镖客：救赎 1、2

- Hollywood Reporter 对 Ivan Pavlovich 的访谈（2019-08-09）：二代有三套音乐系统：任务配乐、动态开放世界配乐、关键时刻的歌；另有游戏里角色自己演奏的音乐。动态配乐由拆成分轨（stems）的曲子组成，实时叠加或过渡；"The original Red Dead Redemption also used a stem system, but we were limited to five separate tracks of stems, and each had to be recorded in the same key and tempo. For Red Dead Redemption 2, we had 11 separate tracks of stems to work with and we weren't limited by tempo or key."；做的音乐超过一次通关能听到的三倍。
- Rolling Stone Italia 对作曲 Woody Jackson 的访谈（2018-11-11）：一代的曲子常是同一个情绪，130 bpm、A 小调；二代世界太大，不能一直用同一个速度和调。

### 4.10 无人深空（A Sound Effect 对 Paul Weir 的访谈，2017-03-28）

- "Very little of the audio is procedurally created, only the creature vocals and background fauna. At the moment it's too expensive and risky to widely use this approach"
- "It's still a poor way to create realistic sounds. I'm not generally in favour of using it to create wind or rain effects for example. ... Wind can be cold, gentle, spooky, reassuring. There are complex qualities that we instantly react to with natural sounds, it's a lot harder to do this with synthetic sound."
- 生成式音乐系统 Pulse："a glorified random file player with the ability to control sets of sounds based on gameplay mechanics"：一个"乐器"是一组同类声音的变体，规定它多久能响、音高、声像、音量。
- 不可预测有多少发声体，"We have to use a lot of voice limiting based on distance"。

## 5. 自适应音乐的技术

### 5.1 横向重排、纵向分层（Winifred Phillips 在 Game Developer 上的 GDC 2021 系列，第 2、3 篇，引她的书《A Composer's Guide to Game Music》）

- 横向重排："a musical composition is constructed as a collection of segments ... Each segment of music may contain digital markers that indicate convenient and logical points at which the game engine may switch between that music segment and another"（曲子由片段组成，片段里有标记，标出可以切换的位置：每拍、每小节或特定点。）她的 Spyder 每关三十多个片段，随机排列，会"ebb and flow, and even settle into silence periodically"（起伏，周期性地落入安静）。
- 纵向分层："the playing of multiple independent audio files simultaneously ... in perfect synchronization"；和混音分轨不同，分层的每一层"are not always meant to play simultaneously"，要按各种组合都好听来写。
- 两者可以混合（她的第 4、6 篇，我只看了标题）。

### 5.2 常用的拼接手段

- **对齐到拍或小节再切**；**过门**（一段专门的过渡片段）；**stinger**（叠在当前音乐上的短乐句，Ori 用笛子渐强做 stinger 和过门）；**回到原处**（战斗结束回到野外曲刚才的位置）。
- **同调同速**：一代 RDR 的分轨都用同一个调、同一个速度，任意组合都不冲突（§4.9）；这是分层系统最省事的约束。
- **昼夜同构**：异度神剑的昼夜两版、星之海的战斗曲昼夜两版，结构相同才能在同一位置交叉淡化。

### 5.3 Godot 4.7 能做到什么、做不到什么

文档：docs.godotengine.org/en/4.7（类参考与教程）；源码：本机 4.7.2-stable 的 `modules/interactive_music/`、`servers/audio/`。

| 资源 | 能做 | 限制（文档或源码核对过） |
|---|---|---|
| **AudioStreamInteractive**（4.3 起） | 一组片段（clip）+ 转换表；从哪里转：立即、下一拍、下一小节、片段结束；转到哪里：同一位置、开头、上次离开的位置；按拍数淡入、淡出、交叉或自动；可插过门片段（filler）；`hold_previous` + 自动前进的"回到保持的片段"；`CLIP_ANY` 通配；`switch_to_clip(_by_name)` 切换 | 拍和小节靠片段自己的 bpm、拍数、每小节拍数（Ogg/MP3 导入时设；**WAV 没有这些属性**，只能走"无 bpm"的简单过渡）；没有 bpm 时淡化长度按秒算。**`get_playback_position()` 在源码里直接返回 0，`seek` 不支持**：拿不到当前音乐位置，stinger 对拍只能自己记时钟。**一个片段一个固定速度**，不能变速。**淡化是线性幅度**（不相关的两段在中点约低 3 dB）。**没有 stinger、没有拍点回调**。 |
| **AudioStreamSynchronized** | 最多 32 条流同时起、同时走；每条单独音量 | 它会把子流的 bpm、拍数、每小节拍数报上去（源码），所以可以当 Interactive 的一个片段（昼、夜各一组分层）。**每层音量在混音时按 128 帧一块取常数、不插值**：直接改会跳变，要每帧小步慢慢改，或者分层改用多个 AudioStreamPlayer（播放器的音量在每个混音块里是线性插值的，源码 `audio_server.cpp`）。 |
| **AudioStreamPlaylist** | 最多 64 条依次播放；可洗牌（每次开始和每次循环重洗）；`fade_time` | 文档："Streams are expected to have an extra bit of audio after the end to help with fading."（每条结尾要留一点尾巴给淡化。）中间插静默得自己放静音片段。 |
| **AudioStreamRandomizer** | 从池里随机挑；"不连续重复"模式；随机音高（按倍数或按半音设）、随机音量（±dB）；权重 | 只挑一条，不分层。 |
| **AudioStreamGenerator** | 脚本逐样本生成 | 文档："Due to performance constraints, this class is best used from C# or from a compiled language via GDExtension. If you still want to use this class from GDScript, consider using a lower mix_rate such as 11,025 Hz or 22,050 Hz." |
| **总线与效果** | 压缩器可以用别的总线做侧链（文档原话：常用于对话时压低音乐和音效，即 ducking）；滤波、EQ、延迟、合唱、移相、限幅、硬限幅、频谱分析、录音等 | **只有算法混响**（源码是 Freeverb 的梳状 + 全通结构），**没有卷积混响**：v0.1 生成冲激响应的"林间空气"混响不能原样搬，要么预先渲染进素材，要么用算法混响重调。 |
| **AudioStreamPlayer3D / Area3D** | 衰减模型（反比、平方反比、对数、关）、距离低通（默认 5 kHz、−24 dB）、发声角、多普勒、`max_polyphony`；Area3D 可以把进入的声音转到某条总线、按区域送混响（含"均匀度"） | — |
| **导入** | WAV 默认用 QOA 有损压缩导入（"much higher quality and the lowest memory usage"）；文档：Ogg 解码比 WAV 费 CPU，大量同时发声的音效建议用 WAV | — |
| **延迟** | 默认输出延迟 15 ms（`audio/driver/output_latency`），实际以系统和驱动为准 | 法术反馈"0.1 秒内必有声音"留得出余量；真机上的感受只有用户能确认。 |
| **验证** | Movie Maker（`--write-movie`）非实时录视频和音频（AVI 里是未压缩音频，或 PNG 序列 + WAV）；无头运行时的 Dummy 音频驱动也在线程里真实混音（源码），可以挂 AudioEffectRecord 录整机输出 | 录到的是"逻辑上"的输出；Windows 真机的延迟、设备、音量只有用户那里能听。 |

**结论**：Godot 自带的东西足够做"片段 + 地点主题（昼夜同构）+ 分层 + 过门"，但 stinger 对拍、音乐位置、分层的平滑音量、卷积混响都要自己补；不需要引入 FMOD、Wwise 之类的中间件（它们的许可条款这次没有核实，§10）。

## 6. 合成音效：怎么不"循环、重复、无变化、突兀"

### 6.1 Godot 版现在的问题（读 `godot/core/audio.gd`，2026-10-17）

- 取、予、放、拒绝、回流、点燃、界面、脚步、说话音，**每种只生成一份缓冲并缓存**（`_synth` 按键缓存）：每次听到的都是同一段波形，只有脚步的音高有一点变化。
- 合成本身很简陋：一个扫频的振荡器或滤过的噪声，4 ms 起音、平方衰减，没有分层、没有共鸣体、没有空间。
- 没有位置（全是不带位置的播放器）、没有混响。
- 环境声原来是 20–30 秒的录音循环，现在按 G5R3-53 关掉了（`FIELD_RECORDINGS = false`），鸟和乌鸦的单发叫声也关了：世界几乎是安静的。
- `music()` 是空函数：没有音乐。

### 6.2 v0.1 做对了什么（读 `legacy/v0.1/src/audio.js`，1777 行；JS 版的移植在 `src/audio/audio.js`）

- 总线：音乐、环境、音效、说话、"远"五条；两个**生成的卷积混响**（林间空气约 2.8 秒，带树干和石头的稀疏早期反射；"远"约 5.5 秒，暗、慢慢开花）；总压缩器；暂停时整体低通。
- **每次发声都重新随机**：脚步的滤波频率 ±15%、音量 0.8–1.05、噪声播放速率 0.8–1.2、从噪声缓冲的随机位置起播；乌鸦每声的长度、基频、间隔都随机。
- **按材质的脚步**：草、土、石、木、水、落叶、沙、苔各有滤波和衰减；草和落叶用"颗粒"包络（几个不规则的小爆发）；木头叠一声"敲"，石头叠一声"嗒"；**重的时候加闷响**；她每走两步有一声几乎听不见的铃（JS 版也保留了；现在的剧本里铃声属于さぢ，见剧本第 0 场）。
- **乐器**：Karplus–Strong 的筝和三味线（三味线带 sawari 的嗡）、加法合成的铃、锣、玻璃、铃（rin）、钲、締太鼓、太鼓、大太鼓、带气声的笛、慢慢开的 pad。
- **环境**：风（粉噪声 + 随机游走的阵风）、树叶（随阵风的沙沙爆发）、竹（高频 + 阵风）、溪（四个游走的带通 + "咕嘟"气泡）、瀑布、雨（高通的雨声 + 两种雨滴）；**按时辰的生物事件**：油蝉、蜩（会接力应答）、树莺、山雀、乌鸦、铃虫、河鹿蛙、竹子相碰、风铃、滴水、雷；每种有一天里的时间窗、泊松发生率、并发上限，按地貌和"近"（遠化）加权，雨天少。
- **音乐**：前瞻的音序器；阳音阶（D）；她的主题"九音上行、第十拍全体静默"（数到九十九、到不了一百）；标题、序章、野外（大部分时间安静，每 25–70 秒一个短乐句，按时辰换乐器：早上笛子配轻的筝、正午筝独奏、黄昏低音三味线、夜里钢片琴或泛音）、家、紧张、远眺；stinger（发现、供奉、建造、完成、觉醒、遠、标题、入夜、天明）。
- **遠囃子**：生成的祭囃子（篠笛 16 小节 + 締太鼓、钲、大太鼓），从极远处传来：慢的音高摇晃、合唱、偶尔移相、陡的低通、随风起伏、声像漂移。
- **收音机**：小喇叭的滤波、静电、调台的啸叫、信号衰落。

### 6.3 被批评的怪声与教训（knowledge/05、07）

- "小溪边刮大风时有很怪、不和谐的声音"：最可能是"大风中树干吱呀"（`evCreak`：14–36 Hz 锯齿波过 200–300 Hz、Q=12 的带通，发生率随风速平方），听起来像电子嗡鸣；另一个可能是遠囃子（**故意调高约 6–13 音分**，加音高摇晃和随风变化的音量）。JS 版已删 `evCreak`。注意背负子的"摇晃吱嘎"（`SFX.wobble`）用的是同一种锯齿波过高 Q 共振的做法，有同样的风险。
- knowledge/07：不要用不同的播放速率给同一段稳定音调的声音"去重复"，会拍频、镶边；两个声部错开 0.382 个循环长度；循环接缝要按"接缝处和循环内部普通的点比"来查。
- G5R3-53（用户）："很大一部分不適，來自於遊戲內循環的重複的無變化的突兀的音效"。

### 6.4 方法（来自 §1–§4 与 Godot 的能力）

1. **每次都不一样**：离线渲染每个声音的多份变奏（不同随机种子、不同参数），运行时用"不连续重复"抽取，再抖音高、音量、滤波。最常听到的声音（脚步、界面、取予、说话音）变奏最多。
2. **分层**：一次发声由几层拼成（例如脚步 = 地面层 + 身体状态层 + 背着的东西），层与层独立抽取，组合数相乘。
3. **包络**：起音不短于 1–2 ms，结尾有尾巴；长床不硬开硬关，循环点按 knowledge/07 的方法查。
4. **空间**：世界里的声音有位置；远了变闷、混响多（王国之泪的"朦胧、带回声、融进环境"）；按区域换混响。
5. **闪避**：对话、重要提示时压低音乐和环境（Godot 侧链压缩或按总线压）。
6. **调度代替循环**：环境里的生物和事件按规则发生（v0.1 的时间窗、泊松率、并发上限；对马岛的"什么物种何时何地多频繁"）；底床做成长的、由几层互质长度叠成的循环，层的比重随时间慢慢游走。
7. **连续参数**（风速、雨量、离水多远）：渲染几档强度，按参数交叉淡化；阵风是单独的事件，和画面上的风用同一份数据（G5R3-45：风要有随机的频率和会变的方向）。
8. **声部上限**：按距离和优先级限制同时发声的数量（无人深空）。
9. **最常听到的声音花最多心思**：星之海的菜单音、王国之泪的"粘上"。

### 6.5 合成的极限与对策

Weir 的话（§4.10）是对的：合成的风雨更容易显得"功能性"。对策不是假装合成能像录音，而是：① 风格上和画面一致，做"画出来的声音"而不是"照片"（我们的画面也不是照片，是按像素画渲染的 3D）；② 把离线渲染的算力花在合成里难的部分（颗粒化的雨、模态合成的木头和石头、好的混响）；③ 每个声音都有看得见的声源（宪章）；④ 留一个严格的例外通道：确有必要、能保证体验的录音，逐条由用户听过才进包（G5R3-53 的原话允许这个例外）。

## 7. 音乐制作的资源与条款（事实，2026-10-17）

### 7.1 免费采样音源与渲染工具

| 名称 | 许可 | 内容 | 渠道（容器里实测） |
|---|---|---|---|
| **VSCO 2 Community Edition**（Versilian Studios） | **CC0**（页面原话："The library is under a Creative Commons 0 (i.e. public domain) license"） | 约 3 GB 的室内乐团子集；SFZ（给 Sforzando、sfizz 等）和原始 WAV（44.1 kHz，16/24 位）；官方说 SFZ 版"great for ambient and calm orchestral, but may seem a little 'loose'" | 官方直链在 GitHub：容器里 curl 访问 GitHub **403**；页面上的第三方 XRNI 转换版（FLAC，Versilian 镜像在 S3）可达，776,751,985 字节 |
| **VCSL**（Versilian Community Sample Library） | **CC0**（"you can do whatever you want with these sounds (even make commercial software), no royalties, no credit"） | 约 5 GB：三角钢琴（Kawai、Steinway B）、立式钢琴、竖琴、民间竖琴、索尔特里琴、越南筝（Dan Tranh）、拇指琴、钢片琴、马林巴、颤音琴、锣、尼泊尔手铃、管钟、定音鼓、框鼓、陶笛、竖笛等；**没有筝、三味线、尺八、篠笛、太鼓** | GitHub（容器里 403） |
| **Salamander Grand Piano V3**（Alexander Holm） | **CC-BY 3.0**（要署名） | Yamaha C5，AB 制式两支 AKG C414，48 kHz/24 位，**16 个力度层**，每小三度采一个音（相邻音要变调 ±1 半音），击弦噪声与共鸣释放另采 | Freepats 镜像可达：SFZ+FLAC 707 MiB（741,757,374 字节）、WAV 48k/24 1.18 GiB、44.1k/16 394 MiB、SF2 296 MiB |
| Freepats Upright Piano KW | CC0 | Kawai 立式，家里用 Zoom H1 录，2 个力度层 | Freepats |
| University of Iowa MIS | 页面原话："may be downloaded and used for any projects, without restrictions" | 消声室里录的半音阶单音（pp、mf、ff），不是现成的乐器映射 | 网站可达 |
| **sfizz**（SFZ 采样器） | BSD-2-Clause（Arch Linux 的包信息）；1.2.3（2024-01-14） | 有命令行 `sfizz_render --sfz … --wav … --midi …`，一次渲染一个乐器（正好出分轨） | 源码在 GitHub（容器里 403）；Ubuntu 的软件源里**没有** sfizz |
| **FluidSynth**（SF2 合成器） | LGPL-2.1+（Debian 的版权文件） | SoundFont 2/3；最新 2.6.1（2026-09-19） | Ubuntu 软件源里有 2.3.4，没装 |
| **STK**（Synthesis ToolKit，Cook & Scavone） | MIT 式的许可；作者请求"If you make compositions with it, put us in the program notes"；说明里提到部分技术可能有专利 | 物理建模：长笛、拨弦、西塔琴、曼陀林、弓弦、模态打击、Shakers（颗粒化的摇晃类声音）等 | 斯坦福 CCRMA 网站可达 |
| 本机已有 | — | ffmpeg 6.1（`ebur128`、`astats`、`silencedetect`、`showspectrumpic` 等）、numpy 2.5、scipy 1.18、无头 Chromium（playwright，`/opt/pw-browsers`），JS 时期的 `tools/audio/field_browser_check.mjs` 就是用它跑 OfflineAudioContext | — |

### 7.2 日本乐器

- 没找到 CC0 或 CC-BY 的成套筝、三味线、尺八、篠笛、太鼓音源。
- 商业的：Impact Soundworks「Instruments of Japan」合集（Koto Nation：筝、低音筝、三味线；Ventus Winds：尺八；Kageyama Taikos），现价 199 美元，**要 Kontakt 完整版**（Windows/Mac 插件，容器里跑不了）。检索结果里有一份「Koto Nation - Serum 2-SFZ-WAV」的说明书，说明筝那部分可能另有 SFZ/WAV 版，**没有核实**价格和许可。
- v0.1 自己合成过筝、三味线、篠笛、太鼓、钲；大神的上田也说和风的旋律乐器"一只手数得过来"（§4.1）。

### 7.3 现成的音乐

- Kevin MacLeod（incompetech）：CC BY 4.0，FAQ 说游戏通常把署名放在"制作人员"页。
- OpenGameArt：许可按作品各自标，没有逐个核查。
- 用现成曲子做主题的问题：风格和动机不统一；自适应要的分层、昼夜同构版本，都得重新编配，等于自己做。

### 7.4 请作曲家（GameSoundCon 2025 年游戏音频行业调查）

- 按"完成的每分钟音乐"收费：独立游戏最常见 400 美元/分钟，平均 618，中位数 407（比 2023 年降 13%）；中型游戏平均 998、中位数 1,000；3A 平均 1,871、中位数 1,700，最高到 5,000/分钟。独立和中型的上限都到 2,100。
- 独立游戏的自由作曲家里，55% 按分钟收费；36% 说上一个项目是把音乐**授权**给开发者（不是买断）。
- 真人演奏、录音棚、混音另算，这次没有查价格。

### 7.5 AI 音乐服务（条款以访问当天的页面为准）

| 服务 | 条款日期 | 和我们相关的 |
|---|---|---|
| **Suno** | 服务条款最后修订 2026-08-10，2026-09-03 生效；同日的官方博客 | Pro、Premier 订阅者：Suno 把它对输出的权利转让给用户，但"Due to the nature of machine learning, Suno makes no representation or warranty to you that any copyright will vest in any Output"；**只有通过许可的下载拿到的输出才能商用**，下载按档有上限（博客：Pro 每月 20 次，Premier 每月 60 次，Premier 用 Suno Studio 生成、处理分轨不限量；免费档 9 月 3 日前注册的一生最多 7 次试用下载，之后注册的只是偶尔给，试用下载只限个人用途）；Suno 可以在输出上加指纹、水印、元数据，用户不得为隐瞒来源去掉；用户授予 Suno 对内容（含输出）极宽的许可，包括训练模型、公开标明是 Suno 生成的；免费档只能个人非商用 |
| **Udio** | 服务条款最后修订 2025-11-12 | 1.2："You may not download copies of any Output"，也不能发到任何个人设备或流媒体平台；禁止"exploit the Services, any Output ... for any commercial purpose"。**不能用于商业游戏** |
| **ElevenLabs Music** | Music Terms 最后更新 2026-10-09 | 定义了"独立游戏"（游戏累计收入低于 50 万美元，且开发或发行方上一财年所有游戏收入低于 100 万美元）；各付费自助档的媒体权利是"All online and offline commercial use permitted, except film, TV, radio, and Studio Games"（独立游戏不在排除之列）；免费档不许下载、要署名，付费档不用署名；Starter 到 Pro 档限个人使用，Scale 档限 10 人以下的组织，Business 档限 50 人以下；"工作室游戏"只有 Enterprise Music 档可以；**提示里不能写任何艺术家名、词曲作者名、曲名、专辑名、厂牌名**；用户自己负责在使用前审查输出是否可以清权 |
| Stability AI（Stable Audio） | 许可页 | 年收入低于 100 万美元的个人和组织适用社区许可，可商用；"as between you and Stability, you own outputs"（页面把 Stable Audio 列在许可页上；每个模型的许可文本没有逐个核对） |
| AIVA | 定价页 | 免费、Standard 档"Copyright owned by AIVA"；Pro 档"Copyright owned by YOU"；能导出 MIDI |
| Google Lyria | — | 输出权利和商用条款没有找到官方原文，不评价（§10） |

### 7.6 版权与平台

- 美国版权局《版权与人工智能》第二部分（2025-01-29）：生成式 AI 的输出"can be protected by copyright only where a human author has determined sufficient expressive elements"，可以包括人在输出里看得出的创作、人对输出的创造性编排和修改，"but not the mere provision of prompts"；用 AI 辅助创作、或把 AI 生成的材料放进更大的人类作品，不妨碍那部分的保护。**这同样适用于代理写的曲子**：音符是模型决定的部分，版权状态不确定；不影响我们在游戏里使用。
- Steam（Valve 2024-01 的开发者公告，GameFromScratch 2024-01-10 的文章引用了公告原文）：内容问卷新增 AI 披露，"Pre-Generated: Any kind of content (art/code/sound/etc) created with the help of AI tools during development"，披露内容会显示在商店页。我们的美术、代码、文字本来就是 AI 做的，选哪条音乐路线都要披露；2026 年是否又改过没有核实（§10）。

## 8. 响度与客观检查

- G.A.N.G. 的 IESD 文件《Mix Recommendations》v03.02（2015-03-11，文件抬头"GANG IESD MIX RECOMMENDATIONS"）：主机游戏的平均响度建议 −24 LUFS（±2 LU），真峰值不超过 −1 dBTP，按 ITU-R BS.1770-3 测；手机和掌机 −16 LUFS（±2 LU），响度范围 10–15 LU。PC 没有单独的数字。
- 本机能做的检查：ffmpeg 的 `ebur128`（积分响度、短期响度、真峰值）、`astats`（直流、峰值、削波计数）、`silencedetect`、频谱图；numpy/scipy 做互相关、包络自相关、频谱统计；Godot 的 Movie Maker 录整机输出（§5.3）。
- 只有耳朵能判断的：好不好听、动不动人、音色是不是"电子味"、长时间听会不会腻、日本味对不对、和画面合不合。

## 9. 对我们的启示（汇总，提案里逐条用）

1. 野外以环境声为主、音乐为辅；音乐是短片段加长留白（旷野之息、Spyder、Silksong）。
2. 地点主题做昼夜同构的两版，黄昏、黎明在同一位置交叉（异度神剑、星之海）；可以按位置淡入淡出层（A Short Hike、Silksong）。
3. 主题少而准，交给故事里看得见的乐器：遠囃子的笛和鼓、盆踊的鼓、她哼的半句（异度神剑 3、Outer Wilds、荒野大镖客的角色演奏）。
4. 战斗音乐只给真正的战斗（Ori）。
5. 音乐跟着进度长出来：《流れぬ雛》里学会一种性质音乐就多一层（knowledge/12 §"学性质的时刻"），这是用户自己的设计。
6. 远的声音变朦胧、带回声、融进环境（王国之泪），和遠化同一个方向。
7. 音效用离线渲染的多份变奏 + 运行时随机、分层、空间、闪避、调度（§6.4）；Godot 的资源够用，缺的自己补（§5.3）。
8. 合成的风雨有天然的局限（§6.5），要用"画出来的声音"的风格和看得见的声源来对冲，并保留严格的录音例外通道。
9. 代理写谱 + 免费音源，在"稀疏钢琴、弹拨、柔和的 pad"这类写法上最有机会；管弦乐的长音连奏、铜管、日本管乐是免费音源最弱的地方（§7.1、§7.2）。

## 10. 没核实、没找到的

- 任天堂「社長が訊く」异度神剑（Wii）：网站当天 503，没读到；里面有没有讲音乐不知道。
- 旷野之息里骑马曲、气候曲的触发条件（曲目表里有，但没找到官方说明）；天气对音乐的影响。
- 王国之泪地底、空岛的音乐设计细节（只读到 §1.5 的几条）。
- 久石让的旋律、音阶、配器的音乐学分析（没找到可靠的）。
- 新海诚早期作品（天门）的音乐做法。
- FMOD、Wwise 用在 Godot 上的插件和许可条款（没查）。
- Audiokinetic、FMOD 的官方文档页（curl 403 或需要 JavaScript），所以过门、stinger 的定义没有引它们的原文。
- Andy Farnell《Designing Sound》（MIT Press 页面 403），程序化音频的经典论述没有引。
- Steam 的 AI 披露政策在 2025–2026 年有没有再改（有报道说 2026 年 1 月放宽了开发工具，单一来源，没核实）。
- Google Lyria 的输出权利与商用条款。
- Suno 与环球、索尼诉讼的现状（检索里有单一来源的说法，没核实）。
- Impact Soundworks 筝音源的 SFZ/WAV 版本的价格和许可。
- 免费音源里有没有不该有的杂音（椅子声、呼吸、演奏者的声音）：要下载下来逐个查，这次没有下载大音源包。
- 在本机实测 GDScript 能实时合成几路声音：渲染测试正占满 CPU，没跑；结论只引了官方文档。

## 11. 出处（均为 2026-10-17 访问）

1. ファミ通.com，『ゼルダの伝説 ブレス オブ ザ ワイルド』開発者インタビュー【後編】，2017-04-21：<https://www.famitsu.com/news/201704/21130695.html>
2. Nintendo Everything，"Breath of the Wild composers on changing up Zelda's music formula and more"（原声带小册子座谈的英译），2019-01-05：<https://nintendoeverything.com/breath-of-the-wild-composers-on-changing-up-zeldas-music-formula-and-more/>（及 `/2/`、`/3/`）
3. 『ゼルダの伝説 ブレス オブ ザ ワイルド オリジナルサウンドトラック』曲目（Bookoff 商品页）：<https://shopping.bookoff.co.jp/used/0019027219>
4. Nintendo，Ask the Developer Vol. 9《The Legend of Zelda: Tears of the Kingdom》第 2–5 章：<https://www.nintendo.com/sg/interview/totk/02.html>、`03.html`、`04.html`、`05.html`
5. PROCYON STUDIO，『ゼノブレイド２ オリジナル・サウンドトラック』：<https://www.procyon-studio.co.jp/library/detail/144.html>；『黄金の国イーラ』：`/151.html`；『ゼノブレイド３』：`/193.html`
6. Nintendo，Ask the Developer Vol. 6《Xenoblade Chronicles 3》第 2 章：<https://www.nintendo.com/sg/interview/az3h/02.html>
7. Joe Hisaishi official biography：<https://joehisaishi.com/biography/>
8. Classic FM，久石让访谈，2025-10-31：<https://www.classicfm.com/composers/hisaishi/studio-ghibli-composer-totoro-interview/>
9. Variety，"'The Boy and the Heron' Composer Joe Hisaishi on Why the Piano Was Key…"，2024-02-22：<https://variety.com/2024/music/news/boy-and-the-heron-hayao-composer-joe-hisaishi-1235919289/>
10. Marco Bellano，"Transcultural Musical Encounters / 1: Jō Hisaishi and Yūji Nomi"，The Palgrave Handbook of Music and Sound in Japanese Animation，2024（摘要）：<https://research.unipd.it/handle/11577/3531126>
11. Real Sound，『天気の子』RADWIMPS 再タッグ，2019-04-10：<https://realsound.jp/2019/04/post-345588.html>
12. Real Sound，『すずめの戸締まり』音楽 RADWIMPS×陣内一真，2022-09-20：<https://realsound.jp/2022/09/post-1133951.html>
13. Real Sound，高野裕也「RADWIMPSが『君の名は。』で手がけた劇伴の特徴は？」，2016-09-02：<https://realsound.jp/2016/09/post-9051.html>
14. Square Enix Music Online，Okami Original Soundtrack 小册子英译：<https://squareenixmusic.com/features/liners/okami.shtml>
15. Spitfire Audio，"Gareth Coker: The Music of Ori and the Will of the Wisps"（2020）：<https://composer.spitfireaudio.com/en/articles/gareth-coker-the-music-of-ori-and-the-will-of-the-wisps>
16. Nintendo Everything，A Short Hike 开发者访谈，2020-10-17：<https://nintendoeverything.com/interview-a-short-hike-dev-on-bringing-the-game-to-switch-inspiration-art-style-possibility-of-a-sequel-more/>
17. Bandcamp Daily，"Mark Sparling Is Video Game Music's Latest Success Story"，2022-09-22：<https://daily.bandcamp.com/high-scores/high-scores-mark-sparling>
18. Chucklefish，"The Hills are Alive… with the Sound of Eastward"，2021-08-31：<https://chucklefish.org/blog/the-hills-are-alive-with-the-sound-of-eastward/>
19. Game Informer，"Diving Deep Into Sea Of Stars' Nostalgic Soundtrack"，2023-03-24：<https://www.gameinformer.com/exclusive/2023/03/24/diving-deep-into-sea-of-stars-nostalgic-soundtrack>
20. SPIN，Andrew Prahlow 访谈，2020-06-17：<https://www.spinmagazine.com/2020/06/outer-wilds-andrew-prahlow/>
21. Bandcamp Daily，Christopher Larkin 访谈，2025-11-10：<https://daily.bandcamp.com/features/christopher-larkin-hollow-knight-silksong-interview>
22. GDC Vault，"Big World, Small Team: Designing a Scalable Ambience System for 'Ghost of Tsushima'"（摘要）：<https://gdcvault.com/play/1026976/Big-World-Small-Team-Designing>
23. A Sound Effect，Ghost of Tsushima 声音访谈，2020-07-22：<https://www.asoundeffect.com/ghost-of-tsushima-sound/>
24. The Hollywood Reporter，Ivan Pavlovich 访谈，2019-08-09：<https://www.hollywoodreporter.com/news/general-news/red-dead-redemption-2-official-score-launches-digital-platforms-1230363/>
25. Rolling Stone Italia，Woody Jackson 访谈，2018-11-11：<https://www.rollingstone.it/cultura/interviste-cultura/per-un-pugno-di-pixel-parla-il-compositore-della-colonna-sonora-di-red-dead-redemption-2/434978/>
26. A Sound Effect，Paul Weir 访谈，2017-03-28：<https://www.asoundeffect.com/no-mans-sky-sound-procedural-audio/>
27. Game Developer，Winifred Phillips，横向重排（2021-09-15）：<https://www.gamedeveloper.com/audio/horizontal-resequencing-and-dynamic-transitions-for-game-music-composers-from-spyder-to-sackboy-gdc-2021->；纵向分层（2021-10-20）：<https://www.gamedeveloper.com/game-platforms/pure-vertical-layering-for-game-music-composers-from-spyder-to-sackboy-gdc-2021->
28. Godot 4.7 文档：类参考 AudioStreamInteractive、AudioStreamPlaybackInteractive、AudioStreamSynchronized、AudioStreamPlaylist、AudioStreamRandomizer、AudioStreamGenerator、AudioStream、AudioStreamOggVorbis、AudioStreamWAV、ResourceImporterOggVorbis、ResourceImporterWAV、AudioEffectCompressor、AudioStreamPlayer3D、Area3D、ProjectSettings（<https://docs.godotengine.org/en/4.7/classes/>）；教程 Audio streams、Sync the gameplay with audio and music、Creating movies；Godot 4.3 发布页 <https://godotengine.org/releases/4.3/>
29. Godot 4.7.2-stable 源码（本机）：`modules/interactive_music/audio_stream_interactive.cpp`、`audio_stream_synchronized.cpp`、`servers/audio/audio_server.cpp`、`servers/audio/audio_driver_dummy.cpp`、`servers/audio/effects/reverb_filter.cpp`
30. Versilian Studios，VSCO 2 CE：<https://versilian-studios.com/vsco-community/>；VCSL：<https://versilian-studios.com/vcsl/>
31. SFZ Instruments，Salamander Grand Piano：<https://sfzinstruments.github.io/pianos/salamander/>；Freepats，Acoustic Grand Piano：<http://freepats.zenvoid.org/Piano/acoustic-grand-piano.html>
32. University of Iowa MIS：<https://theremin.music.uiowa.edu/MIS.html>
33. sfizz：<https://sfz.tools/sfizz/>、<https://sfz.tools/sfizz/downloads/>；`sfizz_render(1)`：<https://man.archlinux.org/man/sfizz_render.1.en>；Arch 包 sfizz-lib：<https://archlinux.org/packages/extra/x86_64/sfizz-lib/>
34. FluidSynth：<https://www.fluidsynth.org/>；Debian 版权文件：<https://metadata.ftp-master.debian.org/changelogs/main/f/fluidsynth/unstable_copyright>
35. STK：<https://ccrma.stanford.edu/software/stk/>、<https://ccrma.stanford.edu/software/stk/information.html>、<https://ccrma.stanford.edu/software/stk/classes.html>
36. Impact Soundworks，Instruments of Japan Bundle：<https://impactsoundworks.com/product/instruments-of-japan-bundle/>
37. incompetech FAQ：<https://incompetech.com/music/royalty-free/faq.html>
38. GameSoundCon Game Audio Industry Survey 2025：<https://www.gamesoundcon.com/post/gamesoundcon-game-audio-industry-survey-2025>
39. Suno 服务条款：<https://suno.com/terms>；博客 "An update to our downloads policy and Terms of Service"，2026-08-10：<https://suno.com/blog/suno-updates-tos>
40. Udio 服务条款（2025-11-12 修订）：<https://www.udio.com/terms-of-service>
41. ElevenLabs Music Terms（2026-10-09 更新）：<https://elevenlabs.io/music-terms>
42. Stability AI 许可页：<https://stability.ai/license>
43. AIVA 定价页：<https://www.aiva.ai/pricing>
44. 美国版权局 AI 页：<https://www.copyright.gov/ai/>；NewsNet 1060（2025-01-29）：<https://www.copyright.gov/newsnet/2025/1060.html>
45. GameFromScratch，"Steam Makes Massive Update To AI Generation Policy"，2024-01-10：<https://gamefromscratch.com/steam-makes-massive-update-to-ai-generation-policy/>
46. IESD Mix Recommendations v03.02，2015-03-11：<https://www.audiogang.org/wp-content/uploads/2015/04/IESD-Mix-Ref-Levels-v03.02.pdf>

项目内部：`legacy/v0.1/src/audio.js`、`src/audio/audio.js`、`godot/core/audio.gd`、knowledge/05、07、12、decision-log（A-2、G5R3-18、G5R3-45、G5R3-53）、`docs/design/script-05-draft.md`、`story.md`、`characters.md`、`scope-g5.md`。

## 12. A 阶段：把 v0.1 的声音带回 Godot（2026-10-17，G5R3-63、G5R3-65）

### 12.1 做法

- **渲染**：`tools/audio/v01/render.mjs` 把 v0.1 的合成器（JS 版的移植 `src/audio/audio.js`；原版 `legacy/v0.1/src/audio.js` 只用来测量）原样放进无头 Chromium 的离线音频上下文，用虚拟时钟代替 `setInterval`、`setTimeout`（每 25 ms 一拍，和 v0.1 的调度一样），所有乐器、噪声、混响冲激响应在第一个样本之前烤好。源码是以文本打补丁的，每个补丁必须恰好匹配一次，否则停下来；补丁分两类：只为离线运行（不改声音），和 A 阶段的修正（见 12.2，可以关掉，用来测原版）。
- **配方**：`tools/audio/sound_spec.py` 列出游戏里每一个声音：调用哪个 v0.1 的函数、参数、随机种子、几份变奏、怎么切（单发、循环、乐曲按小节切）。`tools/audio/build_sounds.py` 渲染（按配方缓存）、切割、编码，写 `godot/audio/sounds.json`（游戏读）和 `godot/audio/SOURCES.json`（每个文件的生成器、引擎和渲染器源码的散列、配方、切割步骤、文件散列）。131 个声音、717 个文件；没有录音，也没有乐器采样。
- **电平**：保留 v0.1 的相对电平（渲染时绕过 v0.1 的总压缩器，各总线增益照旧）；总压缩器换成 Godot 主总线上同参数的压缩器（阈值 −15 dB、3:1、6 ms、280 ms），后面加 −1 dBTP 的硬限幅。真峰值超过 −1 dBTP 的文件压到 −1，降了多少记进清单，游戏播放时加回去。
- **变奏**：v0.1 每次发声都重新随机（滤波、速率、起播位置），离线渲染改成"每种声音多份不同种子的变奏，运行时不连续重复地抽"；v0.1 本来每次都一样的声音（「移」的锣、拒绝的闷响、界面音）另外按配方把每份播放得稍快或稍慢（±0.6%–4%）、音色稍亮或稍暗（±1–1.5 dB），检查脚本要求同一声音的任意两份最大互相关不超过 0.97。说话音例外：v0.1 用字序决定音高（"说话的旋律"），相似是设计。

### 12.2 A 阶段改掉的地方（决定三的七条和 G5R3-65 补充的一条）

| 改动 | v0.1 的做法 | 现在 |
|---|---|---|
| 规则 1：大风里树干吱呀 | 14–36 Hz 锯齿波过 Q=12 的带通 | 不发（JS 版已删）；背负子的吱嘎同类做法，不渲染 |
| 规则 2：遠囃子不跑调 | 调高 6–13 音分，延迟线做的音高摇晃（±12 音分）、合唱（约 ±23 音分）、间歇移相；每 16 分音符 0.3% 的几率"绊一下" | 音高 1.0，不摇晃、不合唱、不移相、不绊；"远"只靠滤波、远混响、音量和随风起伏 |
| 规则 3：看得见的声源 | 生物的叫声在随机的左右位置 | 蝉和鸟在她周围 6–32 米内的树上，铃虫在草里，河鹿蛙在溪上，竹子的碰撞在竹林里，滴水在树下；没有这样的地方就不叫。乌鸦只在樟树上的乌鸦张嘴（W3Life 的 caw 姿势）、起飞时出声 |
| 规则 4：近频长音 | 铃虫最多 6 只同时、频率在 4.3–4.6 kHz 随机 | 最多 3 只，两两相差至少 60 Hz（每份的音高在构建时测出，写进清单） |
| 规则 5：起音和尾巴 | — | 单发：起点、终点都在静音附近（检查 ≤ 0.002）；循环：接缝的样本跳变不大于循环内部 99% 的跳变，接缝处的电平变化和渲染里同一点一致（±1.5 dB） |
| 规则 6：6 kHz 以上的持续单音 | — | 检查脚本逐个文件找"持续 0.5 秒以上的窄峰"，现在只作提醒：蝉（约 1.2 秒）、予的玻璃余音（约 1.2 秒）、大钟和遠化的触碰（2–4.6 秒，剧情里一次性的）；这些是 v0.1 本来的音色，频率和时长没有改 |
| 规则 7：最常听到的最软 | — | 脚步、界面、说话音、「移」变奏最多；脚步按动画落脚的那一帧出声 |
| 8.1 铃给さぢ | 她每两步一声几乎听不见的铃 | 她的脚步不带铃；さぢ光脚的脚步，每两步 80% 的几率一声铃 |
| 8.2 取上行、予下行 | 取：锣往里收、下行；予：气流上扬 | 取：分音 70→135 Hz 上行、滤波打开；予：先一声玻璃，气流 3600→380 Hz 下落；五性的"到达"声的方向同样对调（音的铃保留"取时吸进、予时敲响"） |
| G5R3-65 2.3：溪边大风的怪声 | 见 12.3 | 每张底床各用一段长噪声（白 37.3 秒、粉 41.9 秒、褐 29.1 秒，气泡 23.9 秒、雨滴 17.3/19.7 秒），每张床分开渲染、互不共用；溪的四个共振带 Q 从 5–9 降到 2.5–4；风改成实时 |

### 12.3 溪边大风的怪声：测量（G5R3-65 第 2.3 条）

用户说 v0.1 最怪的声音"主要集中在靠近溪流时溪流声音和大风声叠合的一种非常奇怪的感觉"。没有猜，用原版引擎（`legacy/v0.1/src/audio.js`，含树干吱呀和总压缩器）在溪边、正午、林中渲染，风 0.25、0.6、0.9（v0.1 的风本来在 0.25 上下摆动，下雨时到 0.9），每种情况同一个随机种子渲染九种变体（整体、无压缩器、无吱呀、只有底床、只有溪、只有风和叶、只有吱呀、只有生物），每段 90 秒（`tools/audio/v01/streamwind_probe.py`）。

| 测量 | 风 0.25 | 风 0.6 | 风 0.9（林中） | 风 0.9（竹林） |
|---|---|---|---|---|
| 总压缩器增益的摆动（第 95 与第 5 百分位之差） | 0.72 dB | 0.73 dB | 0.94 dB | 1.02 dB |
| 压缩器增益和阵风的相关 | −0.03 | −0.19 | −0.52 | −0.60 |
| 溪（只有溪）的电平中位数 | −28.6 dBFS | −28.5 | −28.5 | −28.6 |
| 风和叶的电平中位数 | −37.5 dBFS | −31.9 | −29.3 | −28.2 |
| 溪的能量里被风盖住（差不到 3 dB）的比例 | 2% | 20% | 36% | 36% |
| 吱呀：每分钟次数；比底床低多少（中位数／最响） | 0.7；−25 / −18 dB | 0.7；−24 / −14 | 1.3；−28 / −19 | 1.3；−29 / −20 |
| 溪的窄峰（高出局部频谱中位数 10 dB 以上）每帧平均个数；有窄峰的帧 | 2.7；92% | 2.8；92% | 2.8；92% | 2.7；91% |
| 风和叶的窄峰每帧平均个数 | 0.63 | 0.61 | 0.62 | 0.64 |
| **2.0 秒滞后的自相关**：只有风和叶 | — | — | **0.94** | 0.89 |
| 同上：只有溪 | — | — | **0.46** | — |
| 同上：溪边整体（无压缩器） | 0.52 | — | **0.63**（150–600 Hz 0.75，3–6 kHz 0.74） | — |
| 其它滞后（1、1.7、3、5.6、6.5 秒）的自相关 | 都在 0.07 以下（5.6、6.5 秒是溪的两份气泡循环，0.06） | | | |

结论（测量说明了什么、没说明什么）：

1. **v0.1 的环境声每 2.0 秒重复一次。** 原因在源码里：`makeNoise(2, …)` 只做了 2 秒长的白、粉、褐噪声各一段，风、叶、竹、溪、雨的底床全都循环读这几段（起点随机，但周期都是 2 秒），滤波器的慢变化盖不住它：只有风和叶时，相隔 2 秒的两段声音相关系数 0.94，几乎是同一段。人耳听得出这种重复：Kaernbach 的实验里，相当多的人能听出周期长到 20 秒的循环噪声（出处 47）；1 秒以内的重复，没训练过的人也听得出（出处 48）。
2. **这个重复只有在大风时才跑到前面来。** 风 0.25 时风和叶比溪低 9 dB，溪声把它盖住；风 0.9 时两者一样响（−29 对 −28.5 dBFS），整体在相隔 2 秒处的相关升到 0.63，低频段 0.75。用户说的"靠近溪流、大风、叠在一起"正好是这个条件。
3. **溪本身在吹口哨。** 溪的四个带通 Q 是 5–9，中心频率每 70–250 毫秒乱跳一次：92% 的帧里有窄峰（平均 2.7 个），风和叶只有 0.6 个。大风时风盖住了溪的宽带部分（36% 的能量差不到 3 dB），剩下露出来的就是这些乱跳的窄峰。
4. **压缩器的抽吸和树干吱呀都在，但太小，单独解释不了。** 抽吸最多约 1 dB，大风时和阵风相关 −0.5 到 −0.6（阵风来时溪声被压低一点）；吱呀每分钟一两次，比底床低 14–29 dB。
5. 我们听不见，没法确定用户听到的是第 1 条还是第 3 条（多半是一起）。两条都改了。

改了以后（JS 版引擎加上 12.2 的修正，同样的条件）：每张床、溪边整体在 0.25–20 秒的所有滞后上自相关都不超过 0.005；溪的窄峰每帧 1.2–1.4 个（有窄峰的帧从 92% 降到 70%），溪边整体 0.78 个；任意两张床的互相关不超过 0.009（不共用噪声）。

**以后不再出现的检查**（`tools/audio/check_sounds.py`，每次构建以后跑，任何一条不过都算失败）：每张底床在 0.25 秒到半个循环长的所有滞后上自相关 < 0.15；溪、雨、叶、竹的窄峰每帧 < 1.5；任意两张底床的互相关 < 0.1。游戏里的整机录音（`tools/audio/capture_mix.py` 的 brook 走法：溪边、下雨起风）再查一遍整体的自相关 < 0.15，并报溪声电平和风声电平的相关（抽吸）。

### 12.4 v0.1 的声音在样章里放在哪里（A 阶段，照 v0.1 原来的对应关系）

| 地方 | 声音 |
|---|---|
| 菜单 | 标题曲（v0.1 淡入 3 秒）；上下移动、确定是 v0.1 的界面音；夜的空气（风、铃虫，没有 3D 世界，在左右随机的位置） |
| 序章·树顶远景 | 黄昏：序章曲；第一盏灯离地：序章曲淡出，遠囃子从近处起；灯一路离开：遠囃子变远变稀，散成风声；天岸打开：遠囃子清清楚楚地回来；信号塔熄灭：遠化的脉冲；遠化扩散：紧张曲和遠化的潮；她喊：她的说话音；白场：一切截断 2.4 秒（v0.1 的遠化之潮结尾），回来时整片地都远了 |
| 家一带 | 风（实时）、叶、竹、溪、雨的底床，按时辰、天气、林木和离水多远；生物和雷照 v0.1 的时间窗和发生率，从看得见的地方；她和さぢ的脚步按地面（地表材质图、水、路面的石头和木段）；樟树上的乌鸦；夜里缘侧柱子上的收音机（遠囃子透过小喇叭、静电、调台）；音乐：院子里是 v0.1 的家曲，出了院子是野外的片段（大部分时间安静，按时辰换乐器） |
| 眺望岩 | 同上；她站上去远眺时放 v0.1 的远眺曲（每四分钟最多一次），之后回到野外 |
| 立绘页的对话 | v0.1 的说话音（每两个字一声）、翻页音；对话时音乐压低 9 dB、环境压低 4 dB（决定二） |

### 12.5 出处（补充）

47. Christian Kaernbach，auditory.org 邮件列表 "Re: Infrapitch"，2009：原话 "In our own experiments we could extend the range down to 0.05 Hz (up to a period length of 20 s). Quite a number of participants could successfully detect periodicities of this length."：<https://auditory.org/postings/2009/657.html>（他 2004 年的论文 *The Memory of Noise*，Experimental Psychology 51(4):240，出版社页面 403，没读到原文）
48. Rajendran, Harper, Abdel-Latif, Schnupp, "Rhythm Facilitates the Detection of Repeating Sound Patterns", Frontiers in Neuroscience 10:9，2016：引 Kaernbach (2004) 和 Agus et al. (2010)，人能在 1 秒的刺激里听出只重复了两次的 500 毫秒噪声：<https://pmc.ncbi.nlm.nih.gov/articles/PMC4731741>
