# 06 自然环境声：真实录音的来源、许可与做法（2026-10-14）

> 编号说明：已有 `06-reference-board.md`，本篇按任务指定的文件名也用了 06，README 的索引需要补一行（我不拥有 README，留给主线）。

依据项目宪章："自然环境声用真实录音（CC0）；合成只用于音乐和法术"。v0.1 的合成引擎被认可，但"小溪边刮大风时有很怪、不和谐的声音"（knowledge/05）。本篇记录：现在游戏里用了哪些录音、许可怎么核实的、哪些找不到 CC0、怎么加工、怎么接进引擎、怎么验证、还有哪些弱点。

## 1. 现在的素材（`assets/audio/`，全部 CC0 或公有领域）

| 文件 | 内容 | 来源（作者，许可） | 时长 | 大小 |
|---|---|---|---|---|
| `night.mp3` | 夜虫合唱：4 kHz 的连续颤鸣 + 2.6 kHz 的成串脉冲（种名未核实） | radio aporee「Night in Akiyoshidai」，山口县美祢市秋吉台附近森林，2018-10-18 01:00（thomasmartinnutt，Public Domain Mark 1.0） | 30 s 循环 | 239 KB |
| `night2.mp3` | 夜虫合唱：7.5–9 kHz 的螽斯带、5 kHz 的断续鸣叫、10–16 kHz 的高频啁啾 | radio aporee「Miuda insect nightlife_long grass」，长崎县对马市三宇田，2024-09-30 23:20（abyssence，PDM 1.0） | 20 s 循环 | 161 KB |
| `wind.mp3` | 风过一棵大树的树叶，约每 8–10 秒一阵 | BigSoundBank #0659「Wind in a Tree」（Joseph SARDIN，CC0 1.0），法国 | 27.5 s 循环 | 219 KB |
| `stream.mp3` | 近处的小山溪：2.5 kHz 以下的水体 + 到 16 kHz 的气泡和水滴 | BigSoundBank #1354「Small Stream #4」（Joseph SARDIN，CC0 1.0），法国 | 20 s 循环 | 201 KB |
| `fall.mp3` | 小瀑布（近录，距离感由 field.js 加） | BigSoundBank #0219「Small waterfall #2」（gamin，CC0 1.0），法国山间小瀑布上方几米 | 16 s 循环 | 129 KB |
| `crow.mp3` | 两段乌鸦叫（3 声、3 声）＋ 4 个单声切片 | iNaturalist 观察 250986351（京都，funnieanimals，CC0；社区鉴定未完成）、331178834（冲绳，JIN Pin-Tsen / islander_iskander，CC0），均为大嘴乌鸦 | 4.6 s 精灵图 | 37 KB |
| `birds.mp3` | 早晨的鸟：栗耳短脚鹎 ×2、远东山雀 ×2、日本树莺 ×3 | iNaturalist 111523106（上田，Kōsuke Onoda）、188787166（东京大田区，Kalvin Chan）、356867013（东京世田谷，quercus_e）、367885458（相模原，bko）、206776175（京都，Ahikar）、367885761（藤泽，bko），全部 CC0 | 19.9 s 精灵图 | 156 KB |

合计 1,168,763 字节（1.14 MB）；单文件构建里以 base64 内联，约 1.5 MB。每个文件的源 URL、作者、许可、精确的剪辑与处理参数都在 `assets/audio/manifest.json`。

## 2. 许可规则与核实方式

- **只收 CC0 或公有领域。** 不用 NC、ND。CC BY / BY-SA 只下载到临时目录供决策，不进 `assets/`。
- iNaturalist：许可是**每段录音**单独的（`sounds[].license_code`），不是观察记录的许可；用 API 的 `sound_license=cc0` 过滤，下载后再逐条核对 `license_code == "cc0"`。
- BigSoundBank：每个音效页面写明「License CC0 (public domain)」，站点许可页写明 CC0 1.0（另附 WTFPL）。下载用的是页面播放器自己的文件（`/UPLOAD/ogg|mp3/<id>`，OGG 约 200–260 kbps、MP3 160–320 kbps），**没有**绕过下载页的倒计时和反机器人表单。
- radio aporee（archive.org）：每条录音带 `licenseurl`。我只用了 `publicdomain/mark/1.0`（Public Domain Mark）。注意：PDM 严格说是"标记已在公有领域的作品"，录音者用它表示放弃权利；按任务规则视为公有领域，但法律上不如 CC0 干净。如果要零风险，可以只保留 CC0 的部分（iNaturalist、BigSoundBank），夜虫就只剩合成。

## 3. 渠道（2026-10-14 的网络环境）

| 渠道 | 状态 | 有什么 |
|---|---|---|
| freesound.org、pixabay | 被网络策略封锁（403），未尝试绕过 | — |
| Wikimedia Commons | 网页可达；API 经常 429（共享出口 IP 限流），退避重试可以用；upload.wikimedia.org 下载也会 429 | 蜩只有 CC BY 2.1 JP、CC BY 4.0、CC BY-SA 3.0；铃虫只有 CC BY 2.1 JP（多许可，含 BSD）。CirrusSearch 的 `hastemplate:Cc-zero filetype:audio` 可以筛 CC0，但几乎全是发音文件 |
| archive.org / radio aporee ::: maps | 可达 | 日本境内 875 条，其中 297 条 PDM。**注意：新条目的 coverage 字段写"日本"不写"Japan"，只搜 Japan 会漏掉一半** |
| iNaturalist API + static.inaturalist.org | 可达 | 日本的鸟有不少 CC0 录音（鹎 15 条、树莺 12 条、山雀 5 条、乌鸦 5 条）；蜩、铃虫、河鹿蛙、树蛙 0 条 CC0 |
| GBIF | 可达 | 用来统计许可分布（汇总 iNaturalist、BioAcoustica 等） |
| BigSoundBank | 可达 | 法国录音，CC0；水、风很好，虫鸟是欧洲种 |
| xeno-canto | 可达但有 Anubis 反机器人页，API v2 已下线；未使用 | — |
| opengameart、kenney | 可达；未深入搜索（以游戏音效为主，没有带地点和种名的野外录音） | — |

## 4. 找不到 CC0 的（需要决定）

**蜩（ヒグラシ，Tanna japonensis）——黄昏最关键的声音，没有找到 CC0 或公有领域的录音。**
iNaturalist 132 条有声观察：CC BY-NC 69、CC BY 21、保留所有权利 16、BY-NC-ND 1、BY-NC-SA 1、CC0 0。GBIF：BY-NC 72、BY 27、BY-NC-SA 1。Commons 三条都是 BY/BY-SA。radio aporee 的 PDM 日本录音里没有黄昏的蜩（"Late Summer Cicadas" 是下午 13:30 的寒蝉 Meimuna opalifera 和别的蝉，不是蜩）。

因此现在黄昏仍由引擎合成的蜩发声（field.js 不会静音它）。CC BY 候选（已下载到临时目录并做了加工样品，**未放入 assets/**）：

| 候选 | 作者 | 许可 | 地址 | 评价 |
|---|---|---|---|---|
| 蜩合唱，那须（栃木），2025-08-02 18:12 | Yoshihiro Tokue（tokue） | CC BY 4.0 | https://www.inaturalist.org/observations/303075754 （声音 1590381） | **推荐做黄昏底床**：几只蜩此起彼伏，4.3 kHz 基频和泛音清楚，背景干净（35 s） |
| 蜩单句，仙台青叶区，2023-07-29 16:43 | Timur Kalininsky | CC BY 4.0 | https://www.inaturalist.org/observations/175909347 （声音 782217） | 可切单句"カナカナカナ"做事件；32 kHz 采样，12 kHz 以上没有 |
| 蜩，西乡（福岛），2026-07-11 17:34 | Yoshihiro Tokue | CC BY 4.0 | https://www.inaturalist.org/observations/380247687 | 较远，10 秒处有风噪/碰触声，不推荐 |
| File:Tanna japonensis v01.ogg（川崎，2011-07-17，96 s） | Σ64 | CC BY 4.0（另 GFDL） | https://commons.wikimedia.org/wiki/File:Tanna_japonensis_v01.ogg | 下载被 429，未分析 |
| File:Higurashi 20180728 1902.ogg（青森，19:02） | あおもりくま | CC BY-SA 3.0 / GFDL | https://commons.wikimedia.org/wiki/File:Higurashi_20180728_1902.ogg | SA 条款更重，不推荐 |
| File:Higurashi 06c5856.ogg（川崎，2006） | ISAKA Yoji（cory） | CC BY 2.1 JP / BSD / GFDL | https://commons.wikimedia.org/wiki/File:Higurashi_06c5856.ogg | 说明里写有车声、风声、人声，不推荐 |

**铃虫（スズムシ，Meloimorpha japonica）**：同样没有 CC0。GBIF：BY-NC 40、BY 9、BY-NC-SA 11。iNaturalist 日本境内 CC BY 19 条，录音者主要是 岸本年郎（kishimoto_toshio）、WATANABE Hitoshi 渡辺仁（tbc_watanabe）、Yoshihiro Tokue。看过的样品里，观察 135648854（声音 538117，静冈，6 s）是干净的"リーン"，观察 308057302（声音 1611471，挂川，11 s）有合唱；都很短，适合做事件而不是底床。Commons 的 Suzumushi 06z3286.ogg / 06z3310.ogg（cory，CC BY 2.1 JP / BSD / GFDL，相机内置麦克风，2006 年兵库余部站）未能下载分析。
现在的夜虫底床是真实的日本秋夜合唱，但里面没有能辨认出来的铃虫"リーン"。

**河鹿蛙、日本树蛙等蛙类**：iNaturalist 0 条 CC0；引擎的合成河鹿蛙保留（只在传入 water 时出现）。

如果批准 CC BY：运行 `python3 -I tools/audio/build_field.py --ccby` 会把 `dusk.mp3`（30 s 蜩合唱循环）和 `higu.mp3`（两句单句）写进 `assets/audio/`，META 自动更新，field.js 会接管并静音合成的蜩。代价：游戏的制作人员名单必须写出处（manifest.json 里会生成 `attribution` 字段），体积多约 300 KB。

## 5. 加工方法（`tools/audio/build_field.py`，可重跑）

1. 解码 → soxr 重采样到 44.1 kHz → 选声道。**秋吉台那条立体声两声道反相相关（r = −0.55），直接相加会在 1–3 kHz 抵消 11 dB，所以单声道取 (L−R)/2**；溪流那条两声道不相关，取单边避免梳状滤波。
2. 滤波：4 阶高通（60–300 Hz，按内容）去直流与低频轰鸣；瀑布预先低通 8 kHz（它永远在远处，省码率给中低频）；乌鸦低通 8 kHz；鸟和乌鸦用 FFT 降噪（afftdn，降 10 dB）。
3. 风：原录音里有隐约的鸟叫（欧洲种）。做了时频修复：1.5–10 kHz 内，凡比局部时频中位数高出 6 dB 以上的格子压回该水平（只动了 6.4% 的格子），宽带的风声不受影响。
4. 无缝循环：取 L+X 秒，把最后 X 秒用等功率（sin/cos）交叉淡入开头。这样循环点上的 L−1 → 0 正好是原录音里相邻的两个采样，**接缝处本身就是连续的录音**；交叉淡化发生在循环开头的 X 秒内。
5. MP3 编码延迟：LAME 在文件开头加约 1105 个采样的延迟，各浏览器是否裁掉不一致。每个循环文件前后各补 0.25 s 的周期延拓（循环尾 + 循环 + 循环头），field.js 在 loopStart=0.25、loopEnd=0.25+L 之间循环；无论解码器裁不裁延迟（±1300 采样内），循环内容都是同一周期，接缝不变。实测 Chromium 的 decodeAudioData 读 LAME 头、裁掉了延迟和尾部填充（解码长度与编码前的 PCM 长度完全相同）；Safari、Firefox 未测，但周期延拓让结果与此无关。
6. 响度：底床 −23 LUFS（积分），事件 −18 LUFS；样本峰值限制在 −1 dBFS 以下。
7. 编码：单声道、44.1 kHz、CBR 64 kbps（溪流 80 kbps，高频气泡需要码率），去掉所有标签。
8. 事件打成精灵图（每段之间 0.45 s 静音），field.js 按 `[起点, 长度]` 播放切片；乌鸦另有 4 个单声子切片（从三连叫里切出，播放时加 12/50 ms 渐入渐出）。
9. 构建脚本同时写 `assets/audio/manifest.json`（来源、许可、全部编辑步骤）和 `src/audio/field.js` 里 `META:BEGIN/END` 之间的循环点与切片表，二者不会对不上。

## 6. 接入引擎（`src/audio/field.js`）

```js
import { createFieldAmbience } from './audio/field.js';
import night from '../assets/audio/night.mp3';   // 构建需要 loader: { '.mp3': 'dataurl' }
// ……night2, wind, stream, fall, crow, birds 同样
const amb = createFieldAmbience(AU, { sources: { night, night2, wind, stream, fall, crow, birds } });
// AU.init() 成功之后（用户手势里）：
amb.load();                                  // 逐个解码，不阻塞，不抛异常；AU 未初始化时返回 []，可以之后再调
// 每帧，在 AU.update() 之后：
amb.update(dt, { waterDist: 35 });           // 可选 streamDist / stream(0..1) / waterPan(-1..1)
// 另有 amb.setEnabled(false|true)（A/B 对比：关掉时合成层恢复）和 amb.stats()
```

- 所有声音进 `AU.ambBus()` 的 inp（干声）和 wet（房间混响），所以引擎的近远低通（远化时"隔着一层纸"）、indoor/cinematic 衰减、`AU.duck()` 都照常作用。
- 每个录音**解码成功之后**才 `AU.mute()` 它取代的合成层：night/night2 → suzu；wind → wind、leaves；stream → stream；fall → fall；crow → crow；birds → ugu、tit；（CC BY 获批后）dusk/higu → higu。任何文件失败，对应的合成层继续响。
- 时段：黄昏 16:48–19:24（CC BY 蜩层，若有）；早晨没有单独的底床（稀疏的鸟叫是事件，铺底的是风和水）；夜 18:36–04:48，两条夜虫录音每 20–45 秒换一次比重，避免听出循环；鸟 04:48–10:30（之后到 17:12 只剩三成）；乌鸦 04:42–19:12，清晨和傍晚加倍。雨会压低虫鸟。生物事件的频率和音量都乘以引擎的 act（远化规则：越"远"越少越轻）。
- 底床由同一循环的两个声部组成，相隔 0.382 个循环长度、左右分开。不用 0.5（会每半个循环左右镜像重复一次），也不用不同播放速率（稳定的虫鸣会拍频，两个声部相位漂到一起时会产生镶边/flanging 的怪声）。
- 距离：瀑布 1/d（参考 20 m），35 m 时约 −37 LUFS（"远处轻柔的水声"），同时随距离降低低通截止、增加混响；溪流参考 6 m。
- 电平（在引擎环境声输入处）：夜虫约 −33 LUFS（合成铃虫约 −38），风（wind=0.3）约 −32（合成风+树叶约 −32），瀑布 11 m 内约 −26（合成 fall=1 约 −21.5）。合成电平是 `tools/audio/synth_levels.py` 的估算。无头 Chromium 实录整机输出：黄昏、夜、早晨、早晨远化四个场景，录音层与纯合成层的响度差都在 1 dB 以内。

## 7. 验证

- `python3 -I tools/audio/verify_field.py [目录]`：ffmpeg 解码无错误、时长与 META 一致；循环接缝在"解码器裁延迟"和"不裁延迟（+1105 采样）"两种情况下，把接缝处的采样跳变、50 ms RMS 变化、高频能量和循环内部 400 个普通切点比较（无缝的接缝只是录音里普通的一点）；补的周期延拓确实重复了循环开头；精灵图每段有声、段前安静；为每个文件和每个接缝出频谱图。
- `node tools/audio/field_browser_check.mjs [目录] [--sweep]`：在无头 Chromium 里用 decodeAudioData 解码（与构建一样的 data: URL）、用 OfflineAudioContext 真实循环渲染接缝、把 audio.js + field.js 按游戏循环驱动并录下送到扬声器的整机输出（与纯合成基线对比响度、核对被静音的合成层），并测试损坏文件时合成层保留、不抛异常。
- `python3 -I tools/audio/preview_field.py 目录 [--ccby 样品目录]`：离线渲染 60 s 黄昏→夜（17:30→21:00）和 30 s 早晨（含远化版本），电平模型与浏览器实录相差约 1 dB。

## 8. 弱点（诚实清单）

- **蜩和铃虫都不是录音**：黄昏的标志性声音仍是合成的，除非批准 CC BY；夜虫底床里听不出铃虫的"リーン"。
- 夜虫录音是 9 月底和 10 月的秋虫，比盂兰盆（8 月中旬）晚一个多月；种类未鉴定（秋吉台那条可能以蟋蟀科为主）。夜里没有蛙。
- 水和风是法国录音。水声与地域无关；风的录音里原本有欧洲鸟的轻声啁啾，修复后仍可能残留极弱的痕迹（频谱检测剩少数几帧）。
- 风的循环里有两三次明显的阵风，27.5 秒一个周期，长时间站着可能听出节律；随机的电平起伏能掩盖一部分。
- 乌鸦只有 2 段原始叫声（京都那条的鉴定状态为"待鉴定"）；鸟只有 7 段，长时间听会重复。没有斑鸠、绣眼、白鹡鸰等其他早晨常见鸟。
- 底床是单声道，靠两个声部做出宽度；没有真正的立体声空间感。
- 64 kbps MP3 对夜虫的高频有轻微压缩痕迹（在频谱上可见 16 kHz 截止），实际听感未经人耳确认——**所有判断都来自频谱、响度和统计，没有人听过**。
- 解码后约 140 秒 PCM（48 kHz 设备上约 27 MB 内存）。
- PDM（公有领域标记）不是 CC0；见第 2 节。
- 只在桌面版无头 Chromium 上测过；Safari（含 iOS）和 Firefox 没有实测（MP3 解码、StereoPannerNode 需 Safari 14.1+）。
- 合成层里仍在响的：白天的蝉（minmin）、河鹿蛙、竹子碰撞、风铃、滴水、雨、雷，以及黄昏的蜩（见第 4 节）。静音引擎的 wind 床也停掉了它的阵风逻辑，竹林（sasa）的阵风调制随之不再变化。

## 9. 教训

- 先查"每段录音"的许可，而不是网页或观察记录的许可。
- 搜 radio aporee 时 coverage 要同时搜"Japan / 日本 / Japon"。
- 立体声野外录音合成单声道前先查两声道相关性；反相的录音一加就没了。
- MP3 循环不能信任文件边界：要么带周期延拓，要么换容器（Safari 对 Ogg/Opus 支持不全，所以仍选 MP3）。
- 不要用不同播放速率给同一段稳定音调的录音"去重复"：会拍频、会镶边，这正是用户说的"怪声"那一类。
