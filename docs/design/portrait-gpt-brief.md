<!--
Source of the PDF "Tengan_Portraits_GPT_Brief" (G5R3-64): the final portrait list written as a brief that ChatGPT
reads directly. Same 20 items, references and method as docs/design/portrait-gpt-list.md; this file is the
authoritative version of the prompts and repair sentences. Built with the scratchpad tool brief_tools/make_brief.py
(thumbnail pictures are added only in the PDF, at the "thumbs" comments).
-->

<div class="cover" markdown="1">

# 《天岸》对话立绘补充：给 ChatGPT 的说明书

**这一页是给你的。**第 2 页起是英文正文，写给 ChatGPT 看：它照着做，也照着自检。内容就是你已经收到的那份最终清单（GP-01…GP-20、同一批参考图、同一种做法"在原画上只改脸"），只是写得更细，不是第二版。婆婆按你的答复做（选 A）；新增的五种表情也按你同意的做。

**准备**：你手上的 `Tengan_PortraitRefs.zip`（参考图，文件名不变）和这份 PDF。第 2–8 页是通用说明和总表；第 9 页起每一项一页：GP-01 在第 9 页，依次到 GP-16 在第 24 页；婆婆在第 25–29 页。

**每一项这样做**

1. 在 ChatGPT 里新开一个对话，一项一个对话。（如果你用 ChatGPT 的"项目"，可以把这份 PDF 放进项目文件，以后每一项在项目里新开对话，就不用每次都传 PDF。）
2. 上传这份 PDF 和这一项的参考图：`GP-xx_ref_a.png`；GP-17 传 `GP-17_ref_a.png` 和 `GP-17_ref_b.png` 两张；GP-18…20 传你通过的那张 GP-17（`GP-17_granny_neutral.png`）。
3. 发一句："按这份文档做 GP-06。"（换成这一项的编号）
4. 它会先用中文复述：改哪张图、改什么、哪些不能动。编号或图对不上，让它停下重来。
5. 出图后它按文档自检，不合格会自己补救，最多两次；还不行，它会说清楚哪里不行。它出图后没有自检，就回一句"按文档自检"。
6. 你再做下面两个检查。过了就下载原图，按文档 A10 节的表改文件名。

**两个检查（各半分钟）**

- **翻页检查**：新图和参考图放在同一个文件夹，用"照片"打开，按左右方向键来回切。只有脸在变；笠、头发、角、发箍、发绳、衣服、手、人的位置和大小都不动。
- **缩小检查**：在"画图"里把两张都缩小（调整大小 → 百分比：小鹊和婆婆 45，しをね和さぢ 40），并排看。新的表情一眼看得出，和参考图明显不同。看不出来就是太轻。
- 顺便看一眼：文件夹缩略图里人物外面是纯色，不是灰白格子（格子是假透明）；没有汗滴、"！"、白气、泪这类符号。

**不合格时**：用中文告诉它哪里不对就行。同一个对话里最多补救两次；还不行就新开对话从头来一次；再不行就跳过，交回时说一句哪一项、哪里不行。

**顺序**：先做 GP-01…GP-16（三个女孩）。婆婆先做 GP-17，**单独交回**；我们转成游戏里的像素立绘给你看，你满意了再做 GP-18…GP-20。外观四项（白发小髻、洗旧的藍染木棉单衣、深色前挂け、不拄拐杖）先按默认画。

**交回**：一项一张 PNG，用 ChatGPT 下载的原图，不缩放、不裁、不转 JPG；文件名见 A10 节（例如 `GP-06_tsuzumi_shout.png`），用了绿底的加 `_green`，一项有两张都满意的第二张加 `_b`。打成一个 zip 在 Claude 的对话里上传，或者放进上次的 Google Drive 文件夹并告诉我们文件名。可以分批交。

**另外**：压缩包里的 `GP-xx_prompt.txt` 不用再复制，以这份说明书为准（提示词在这里补了一段尺寸）。ChatGPT 说读不了 PDF 时，把同名的 .md 文件传给它，文字一样，只是没有小图。每一项旁边的小图是参考图里游戏裁取的那一块（红框），只用来认图；ChatGPT 要改的是你上传的原图。

</div>

<div class="pb"></div>

# Tengan: dialogue portrait edits — brief for ChatGPT

Version 2026-10-17 · 20 items (GP-01 … GP-20) · from the game's art team.

**How to read this brief.** At the start of each conversation, read Part A (sections A1–A10, pages 2–7); it applies to every item. Then read the section of the item the user names in Part B (from page 9, one page per item). Everything you need for one item is in Part A plus that item's section.

## Part A — Read this for every item

### A1. What you are doing

- The user is making a pixel-art game, *Tengan*. You are making **dialogue portraits**: the face picture shown next to the text when a character speaks.
- Each item is **one new facial expression** of one character. For GP-01 … GP-16 and GP-18 … GP-20 you **edit an existing illustration and change only the face**. GP-17 is the only item where you draw something new: a new character.
- You are working directly with the game's art team: the user passes this brief to you and your pictures back to us. We turn your picture into a 128 × 128-pixel portrait with a fixed process (A4). Your job is to give that process a face whose expression is strong and clean enough to survive it.
- The illustrations are the user's own character art. All the other expressions of these characters are finished and approved. Your new face has to fit in among them: when the game switches to it, nothing but the face may move.
- Write to the user in Chinese (they write Traditional Chinese; either script is fine). Give the image tool the English prompt from the item (A2, step 3).

### A2. Your procedure for each item

**1. Identify.** The user writes something like "按这份文档做 GP-06" ("do GP-06 following this document"). Find the item in Part B. Check the uploaded picture: its file name should be the one the item names (for example `GP-06_ref_a.png`). If you cannot see file names, compare the picture with the item's "Original" line. If a file the item needs is missing, or the picture does not match, say so and stop. Do not guess, and never use a picture from this document instead.

**2. Restate before drawing**, in Chinese, briefly:

```text
【GP-06 · 小鹊 · 喊】
编辑：GP-06_ref_a.png（这张图的样子，一句话）
要改：3–5 条（来自本项的 Target）
不改：3–5 条（笠、头发、衣服、手、姿势、人的位置和大小、画风、颜色……）
```

**3. Edit.** Give the image tool the uploaded original as the image to edit, and the item's **image-tool prompt** word for word. You may add sentences from the item's Target; do not shorten or soften the prompt. If your tool lets you choose, ask for 1024 × 1536 and a transparent background. Make **one** picture.

**4. Check** the result against A6 (U1–U12) and the item's own checks (C1 …), then report in Chinese:

```text
【自检 GP-06】
U1–U12：逐条写 通过 / 不通过 / 无法核实，各一句理由
本项 C1–C5：逐条写 通过 / 不通过
结论：交付 / 重画（第几次，改什么）/ 停止（还差什么）
文件名：GP-06_tsuzumi_shout.png
```

Be honest. If you cannot verify something (for example whether the PNG really has an alpha channel), write 无法核实, never 通过. If you cannot look at your result in the same turn, say so; the user will reply "按文档自检".

**5. Retry at most twice.** When a check fails, use the matching repair in A7:

- only the face is wrong (too weak, a feature too small, a symbol left in): edit your last result;
- anything outside the face changed (hat, hair, clothes, hands, the figure's size or position): start again from the **original** upload.

After two retries (three pictures in all), stop. Show the best picture and say exactly which checks still fail and why. Do not go on trying, and do not report a pass you are not sure of.

**6. One item per conversation.** When the item is done, give the user its file name (A10). If the user asks for another item in the same conversation, tell them a new conversation works better (edits drift as a conversation goes on); do it if they insist.

### A3. Never do these

- Never put two items, two expressions or "variations" in one picture: no grids, collages, character sheets or extra views.
- Never redraw the figure from scratch for an edit item. Edit the uploaded original.
- Never "improve" the design: no new accessories, no changes to the hair, clothes, colours or body, no beautifying, no making her look older or younger, no straightening or turning the head, no cropping, zooming or moving the figure.
- Never show Kasasagi's eyebrows. Never move Shione's red marks, give her marks under the other eye, or give her a second horn.
- Never draw symbols, text, tears or wet shine (U6, U7).
- Never edit the small pictures in this document: they are for identification only and far too small.
- GP-18, GP-19 and GP-20 are made from the user's approved GP-17. Do not start them until the user gives you that approved picture.

### A4. What the game does with your picture

The art team runs this process on your picture; you do not do any of it.

1. **Crop.** A fixed square around the face is cut out, placed by the two pupils. Its side is about 290 px of your 1024 × 1536 canvas for Kasasagi and about 325 px for Shione and Saji: from the top of the head (or the hat brim) down to the collar. The red square on each item's small whole-figure picture shows it. Every expression of a character is cropped at the same scale, which is why the head must not change size or position.
2. **Shrink** that square to 128 × 128 px. One game pixel is about 2.3 px of your canvas (Kasasagi) or 2.5 px (Shione, Saji). The distance between the pupils becomes about 25–32 game pixels (it depends on how far the head is turned); the face is about 60 game pixels wide.
3. **Flatten and pixelise.** Soft painting becomes flat areas. Dark strokes (lash lines, mouth lines, outlines) survive as 1-pixel lines if they are dark and clear.
4. **Reduce colours.** Each character has a fixed set of 30 colours, measured from her existing expressions. Every pixel snaps to the nearest one, without dithering. A colour that her originals do not have is replaced by the nearest one they have.
5. **Clean.** Specks of 1–2 game pixels (about 5 × 5 px on your canvas) merge into their surroundings, except inside the eyes and the mouth.
6. **Eyes and mouth.** Inside the eyes the colours snap to her eye colours and the white catchlights are put back. A closed mouth becomes one continuous 1-pixel line along your mouth line; an open mouth becomes a lip line, a dark inside and the tongue colour.

What this means for you:

- **Shapes carry the expression, not shading.** Change the eye opening, the eyelid line, where the irises sit, the mouth's shape and size, the jaw, the outline of the cheek. Subtle shading, soft gradients and fine texture disappear.
- **Make each change big enough.** A change smaller than about 0.1 D (6–7 px on your canvas, about 3 game pixels; D is explained in A5) cannot be seen in the game. Each item's Target gives the sizes to aim for.
- **Keep lines dark and clean.** Lash lines and the mouth line must be dark and at least about 3 px thick on your canvas. Do not draw a mouth or an eyelid with a pale or broken line.
- **Keep her colours** (A8). New colours get replaced.
- **Nothing semi-transparent.** Semi-transparent tears, glows and shine turn into grey smudges.

### A5. How we measure: D

<!-- figure measure -->

- **D** is the distance between the centres of her two pupils on the 1024 × 1536 canvas. Each item gives D for its original (61–75 px). Sizes in this brief are fractions of D, so they do not depend on how big the head is drawn.
- **The eye line** runs through both pupils. Every head here is tilted: the eye line slopes down toward the right side of the image by 16–28°. In a face, "up" and "down" mean along the face, at right angles to the eye line (the blue line in the figure), not straight up and down the canvas.
- **Near eye, far eye.** Every face here is turned toward the right side of the image. The eye on the left side of the image is the near eye (larger); the eye on the right is the far eye (narrower, foreshortened). Measurements are taken on the near eye.
- **Eye opening**: from the lower edge of the upper lash line to the lower lid, through the pupil.
- **Lid cover**: how much of the iris's height is hidden under the upper lid (0% = the lid just touches the top of the iris).
- **Below the eye line**: distances from the eye line down the face. In Kasasagi's neutral face the mouth is 0.71 D below it and the tip of the chin 1.12 D.

### A6. Checks for every item

- **U1** One picture, one figure, one expression. No collage, grid, extra view, text or frame.
- **U2** PNG, 1024 × 1536 (portrait). A larger picture of exactly 2:3 (for example 1365 × 2048) is also fine.
- **U3** Real transparency: an alpha channel around the figure. Not a painted grey-and-white checkerboard, not a grey or white background, no ground shadow.
- **U4 Flip test.** Flipping back and forth between the original and your picture, only the face changes. The hat, the hair (bangs, locks and tips), horn, headband, cords and ties, clothes, hands, props, the body, and the figure's size and position stay exactly as they were; both eyes stay in place.
- **U5 One face.** The whole face is redrawn as one expression: eyes, eyelids, gaze, mouth, cheeks and jaw agree with each other and with the tilt of the head. No new eyes or mouth pasted onto the old face. When the mouth opens wide, the jaw drops, and the mouth's centre line follows the tilt of the head.
- **U6 No symbols, no text.** No sweat drops, anger marks, "!" or "?", thought bubbles, puffs of air, blush hatching lines, sparkles, music notes, "…", speech bubbles, letters, signatures or watermarks. Blush is soft colour only. The game adds its own symbols. Some originals have a faint sweat drop or pink hatching lines: leave them out (the item says where).
- **U7** No tears and no wet shine on the eyes or cheeks.
- **U8 Design intact** (A8): Kasasagi's eyebrows hidden under her bangs; Saji's tuft, headband and bell; Shione's single horn on the left side of the image and the two red marks under her right eye (the eye on the left side of the image).
- **U9 Proportions unchanged**: head size, face shape, eye size and spacing, eye-to-chin distance, except the jaw drop an item asks for.
- **U10 Readable when small.** Shrink your picture and the original to 45% (Kasasagi, Granny) or 40% (Shione, Saji) and look at them side by side: the new expression reads at a glance and is clearly different from the original. At that size the face is as big as in the game.
- **U11 Same drawing style**: clean anime line art and soft cel shading, with the original's line weight and finish. Not painterly, not realistic, not 3D, not pixel art.
- **U12 Same colours**: hair, skin, eyes and clothes keep the original's colours (A8). Blush and the inside of an open mouth use colours the original already has.

### A7. Repairs

Use these sentences (in English) when a check fails. The user may also paste them to you.

| Problem | Repair sentence |
|---|---|
| Expression too weak (U10 or an item check) | "The expression is too weak. Make it about twice as strong. Keep everything except the face exactly the same." |
| One feature changed too little | "Make the change to the [eyelids / irises / mouth / cheek] bigger: [the size from the item's Target]. Keep everything else exactly the same." |
| Something outside the face changed (U4) | "You changed other parts (the hat / hair / clothes / hands / size or position). Start again from the original image I attached and change only the face." |
| Mouth looks pasted on (U5) | "The mouth looks pasted on. Redraw the whole face — eyes, eyelids, cheeks, mouth and jaw — as one expression that follows the tilt of her head." |
| Symbol, blush lines, tears or shine (U6, U7) | "Remove the sweat drop / blush lines / tears / wet shine / symbol. Change nothing else." |
| Not truly transparent (U3) | "The background must be truly transparent (a real PNG alpha channel, not a checkerboard pattern). Give me the same image again with a transparent background and nothing else changed." |
| Transparency failed twice | "Give me the same image again, but fill the whole background with one flat pure green colour, #00FF00 (RGB 0, 255, 0): no gradient, no ground shadow, no green light reflected on her, and a clean edge around her hair. Change nothing else." Then tell the user to add `_green` to the file name. If Granny's clothes ever come out green, use magenta #FF00FF for her instead. |
| Kasasagi's eyebrows show | "Her eyebrows must stay hidden under her bangs, as in the original. Keep the bangs exactly as in the original." |
| Shione's marks moved | "The two short red marks must stay under her right eye — the eye on the left side of the image — exactly as in the original." |
| Eyes look empty, grey or glowing | "Keep her normal iris colour and the white highlights in her eyes. The eyes must look alive." |
| Face older, longer or a different shape (U9) | "Keep her face shape and proportions exactly as in the original: the same head size, eye size and distance from the eyes to the chin." |
| Style changed (U11) | "Keep the drawing style of the original exactly: the same clean anime line art and soft cel shading, the same line weight and colours." |

### A8. The characters

The colours below were sampled from the originals (hex values, approximate). They are here so that you notice drift; the original picture is always the authority.

#### A8.1 Kasasagi — 百々かさゝぎ (file id `tsuzumi`, originals A_xx)

- **Who she is.** A young porter who carries loads over a mountain pass for people and yokai. Polite, formal and almost expressionless; underneath, a little petty and mischievous. Her straight face is the joke. She speaks in short sentences, conclusion first. (`tsuzumi` is her earlier name, kept in the file names.)
- **Hat.** A very wide, shallow straw hat (sugegasa): cream on top, deep navy underneath, a crimson band across the top.
- **Hair.** Very long, straight, black with a violet cast. **Thick, blunt bangs always cover her eyebrows completely; her eyebrows are never drawn.** Two long locks in front of her shoulders, each bound with a white–crimson–white tie.
- **Eyes.** Grey-violet irises, darker at the top and lighter at the bottom; a round white catchlight in the upper part of each iris; a heavy dark upper lash line.
- **Clothes.** A navy kimono top with a V collar (white over crimson); a wide cream sash with a crimson cord tied in a bow at the front and long crimson tails; an open cream over-robe with very wide sleeves, edged in navy; navy wide trousers gathered at the ankles; white ankle wraps; dark tabi and sandals.
- **Her expressions.** With the brows hidden, every expression is in the eyes, eyelids, gaze and mouth. She is nearly expressionless by design, so her quiet expressions must differ by clear shapes (A4), not by acting.

| Part | Main | Shadow / darker | Other |
|---|---|---|---|
| Skin | #fde4d3 | #f1c2ad, #e4ae9b | |
| Hair | #48394c | #251b25 | sheen #5e4e63 |
| Iris | #595364 | pupil #2e2731 | lower iris #a8a4ae; catchlight #f6edec |
| Hat, top / underside | #faeee0 / #32344f | #ecdbce / #1d1a29 | |
| Crimson (hat band, cord, tails) | #a03b52 | #803147, #541827 | |
| Hair ties | #f6e6dc | | stripe #b24c61 |
| Navy (top, trousers, edges) | #3d3c5d | #2f2f48 | |
| Cream (sash, over-robe) | #faefe6 | #ebded9, #d9caca | |
| Collar | #fbf1e7 (white) | | #a44757 (crimson) |

**Her neutral face** (A_35, D = 67 px): eye opening ≈ 0.40 D; near iris ≈ 0.33 D wide (far iris ≈ 0.25 D); the upper lid just touches the top of the iris; a tiny closed mouth ≈ 0.14 D wide, 0.71 D below the eye line; a tiny nose stroke ≈ 0.35 D below it; the tip of the chin ≈ 1.12 D below it.

#### A8.2 Saji — 家守さぢ (file id `saji`, originals C_xx)

- **Who she is.** A zashiki-warashi, the luck spirit of a house, who has just lost her house. Loud, greedy, mischievous, a bad loser; short sentences and exclamation marks; she calls food "Lord Dumpling" and the like. A small child at heart. She will ride on top of Kasasagi's carrying frame and claim it as her new house.
- **Hair.** A messy red bob with one upright tuft on top; a dark teal headband. Her eyebrows show: thin, red-brown, above the eyes.
- **Eyes.** Teal irises, dark at the top and light at the bottom, white catchlights.
- **Cheeks.** Naturally rosy. This is part of her design: keep it in every expression.
- **Clothes.** A pale mint-green cape collar with a dark teal edge; a golden bell with a little red cord at the collar; a dark wine-red kimono top with a red collar; white sleeves lined in red; a dark teal sash tied in a big bow at the side; a red skirt with a cream stripe near the hem; white socks tied with red ribbons; dark boots.

| Part | Main | Shadow / darker | Other |
|---|---|---|---|
| Skin | #fde0c7 | #fdc9ad (also her rosy cheeks) | |
| Hair | #d43433 | #bc2524, #90252b | highlight #f86e65 |
| Iris | #306e76 | #183942 | lower iris #7ab9ac; white catchlights |
| Headband | #1f444e | | |
| Cape | #dadebf | #c8d3ba | edge #2c5762 |
| Bell | #eaaa49 | slit #2a1d05 | highlight #fcecbb |
| Kimono top | #773046 | #4c1d2d | collar #d5312f |
| Sash | #34646e | #1e3c46 | |
| Skirt | #e13937 | #851d26 | |

**Her face** (C_04, D = 75 px): eye opening ≈ 0.46 D; near iris ≈ 0.37 D wide; brows visible above the eyes; the mouth ≈ 0.6 D below the eye line; the tip of the chin ≈ 1.08 D below it.

#### A8.3 Shione — 垣外しをね (file id `shione`, originals B_xx)

- **Who she is.** An oni girl who has watched over forgotten graves for eight hundred years. Gentle, very polite and slow-spoken; enormously strong without noticing; she never lies. Her expressions are softer and smaller than the other two girls', but they must still read at game size.
- **Hair.** Pale silver-lavender and long; straight, thin bangs (her eyebrows faintly show through); a long, low ponytail tied at the nape with a big crimson cord, and again further down.
- **Horn.** **A single dark wine-red crescent horn on the left side of her head as seen in the image.** Only one.
- **Marks.** **Two short, parallel, vertical red marks under her right eye — the eye on the left side of the image** — just below the lower lid, under the iris; each about 0.17 D long, about 0.1 D apart. These are her only face markings.
- **Eyes.** Rose-red irises, dark at the top and light pink at the bottom, white catchlights.
- **Clothes.** A white kimono with a dark wine-red collar; wide sleeves lined in pink with a dark edge; a crimson sash tied in a bow with long tails; a long, dark plum pleated hakama with pink showing at the slit; white tabi boots.

| Part | Main | Shadow / darker | Other |
|---|---|---|---|
| Skin | #fdeee1 | #edbdaf | |
| Hair | #e4cdd6 | #cbb1c2, #98819b | |
| Iris | #8c4a55 | pupil #431e27 | lower iris #f19c9c; catchlight #f7ebdb |
| Horn | #633547 | #3e1c2d | |
| Marks | #ba2d32 | | |
| Cords, sash | #993849 | #6a1e2e | |
| Kimono | #faf3eb | #e6d4cf | collar #4f2f40 |
| Hakama | #59374a | #3c2433 | pink #e5abab |

**Her face** (B_25, D = 65 px): eye opening ≈ 0.38 D; near iris ≈ 0.28 D wide; a closed mouth ≈ 0.23 D wide, 0.68 D below the eye line; the tip of the chin ≈ 1.10 D below it.

#### A8.4 The drawing style they share

- Clean anime line art in dark, warm brown-black. Measured on Kasasagi's face (D = 67 px): face outline 2–3 px; upper lash line 5–8 px at its thickest, tapering to a flick at the outer corner; lower lid line 1–3 px and broken; a closed mouth about 2 px (draw new mouth lines at least 3 px, A4); hair strands 1–2 px.
- Cel shading with two or three tones per material: skin has one shadow tone (under the bangs, under the chin, on the neck) and a soft pink blush on the cheeks (a gentle gradient, never lines).
- Eyes: the iris is dark at the top and lighter at the bottom; the pupil is darker still; one round white catchlight in the upper part of the iris plus a smaller one.
- Hair: a mid tone, a darker shadow tone and light sheen streaks along the strands.
- No glow, no texture, no painterly brush marks.

### A9. Proportions measured on the originals, and what went wrong before

| | Kasasagi (A) | Shione (B) | Saji (C) |
|---|---|---|---|
| D (changes with how far the head is turned) | 57–72 px | 55–76 px | 61–78 px |
| Eye line to chin ÷ D, mouth closed | 1.05–1.15 | 1.0–1.15 | 1.05–1.2 |
| Eye line to the top of the sash ÷ D | 3.7 | 3.3 (top of the hakama) | 3.7 |
| Height in heads | 6.7 | 6.9 | 6.2 |
| Head tilt (slope of the eye line) | 19–33° | 12–27° | 19–34° |

- A wide-open shouting mouth may lengthen the face by up to about 0.2 D; each shouting item says how much.
- Earlier attempts that failed, so avoid:
    - figures redrawn from scratch drifted: Kasasagi's face became longer and older (eye-to-chin 1.26 D; eye-to-sash about 7 D), and the heads were straightened to about 14°;
    - semi-transparent tears became grey smudges in the game;
    - backgrounds came back grey, or as a painted checkerboard, instead of transparent;
    - expressions were too subtle to read without symbols;
    - a big shouting mouth pasted onto a calm face did not follow the perspective of the head; this is why the whole face is always redrawn;
    - a "blank" face with grey, highlight-less eyes looked eerie.

### A10. What to hand back

- One PNG per item, as generated: not resized, cropped or converted to JPG.
- Give the user the file name from this table; they rename the download.

| Item | File name | Item | File name |
|---|---|---|---|
| GP-01 | `GP-01_tsuzumi_serious.png` | GP-11 | `GP-11_saji_smug.png` |
| GP-02 | `GP-02_tsuzumi_evasive.png` | GP-12 | `GP-12_shione_pout.png` |
| GP-03 | `GP-03_tsuzumi_downcast.png` | GP-13 | `GP-13_shione_shout.png` |
| GP-04 | `GP-04_tsuzumi_blank.png` | GP-14 | `GP-14_shione_grin.png` |
| GP-05 | `GP-05_tsuzumi_smug.png` | GP-15 | `GP-15_shione_serious.png` |
| GP-06 | `GP-06_tsuzumi_shout.png` | GP-16 | `GP-16_shione_blank.png` |
| GP-07 | `GP-07_tsuzumi_pout.png` | GP-17 | `GP-17_granny_neutral.png` |
| GP-08 | `GP-08_tsuzumi_think.png` | GP-18 | `GP-18_granny_smile.png` |
| GP-09 | `GP-09_saji_pout.png` | GP-19 | `GP-19_granny_wistful.png` |
| GP-10 | `GP-10_saji_shout.png` | GP-20 | `GP-20_granny_stern.png` |

- With the green background (A7), the name ends in `_green`, for example `GP-03_tsuzumi_downcast_green.png`.
- If the user likes two results for one item, the second one ends in `_b`.
- If you had to stop (A2, step 5), tell the user which checks failed; they report it to us.

<div class="pb"></div>

## Part B — The items

| Item | Character | Expression | Kind | Edit this file | Original |
|---|---|---|---|---|---|
| GP-01 | Kasasagi | serious 认真 | redo | `GP-01_ref_a.png` | A_35 |
| GP-02 | Kasasagi | evasive 避开视线 | new | `GP-02_ref_a.png` | A_35 |
| GP-03 | Kasasagi | downcast 低落 | new | `GP-03_ref_a.png` | A_35 |
| GP-04 | Kasasagi | blank 茫然 | new | `GP-04_ref_a.png` | A_35 |
| GP-05 | Kasasagi | smug 得意 | new | `GP-05_ref_a.png` | A_35 |
| GP-06 | Kasasagi | shout 喊 | redo | `GP-06_ref_a.png` | A_12 |
| GP-07 | Kasasagi | pout 鼓腮 | redo | `GP-07_ref_a.png` | A_04 |
| GP-08 | Kasasagi | think 思考 | redo | `GP-08_ref_a.png` | A_34 |
| GP-09 | Saji | pout 鼓腮 | redo | `GP-09_ref_a.png` | C_04 |
| GP-10 | Saji | shout 喊 | redo | `GP-10_ref_a.png` | C_12 |
| GP-11 | Saji | smug 得意 | new | `GP-11_ref_a.png` | C_04 |
| GP-12 | Shione | pout 鼓腮 | redo | `GP-12_ref_a.png` | B_04 |
| GP-13 | Shione | shout 喊 | redo | `GP-13_ref_a.png` | B_12 |
| GP-14 | Shione | grin 开怀 | redo | `GP-14_ref_a.png` | B_02 |
| GP-15 | Shione | serious 认真 | redo | `GP-15_ref_a.png` | B_25 |
| GP-16 | Shione | blank 茫然 | redo | `GP-16_ref_a.png` | B_35 |
| GP-17 | Granny | design + neutral 设定兼平常 | new drawing | — (style references `GP-17_ref_a.png`, `GP-17_ref_b.png`) | B_01, C_01 |
| GP-18 | Granny | smile 笑 | new | the approved GP-17 | — |
| GP-19 | Granny | wistful 怀念 | new | the approved GP-17 | — |
| GP-20 | Granny | stern 板脸 | new | the approved GP-17 | — |

"Redo" means the game already has this expression but it failed (the item says why); "new" means the script needs an expression the game does not have. Kasasagi's GP-01 … GP-05 all edit the same original (A_35, the picture behind her neutral portrait), so that her six quiet faces — neutral plus these five — differ only in the face. They must also be clearly different from each other:

| Expression | Eyelids | Irises | Mouth |
|---|---|---|---|
| neutral (A_35 as it is) | normally open | centred, looking right | small, flat |
| serious GP-01 | upper lids flat and lower, lower lids raised: narrower | centred, steady | a longer straight line |
| evasive GP-02 | normal or a little lower | **far left** in the eyes | small, pressed |
| downcast GP-03 | **upper lids heavy, half closed** | looking down | corners slightly down |
| blank GP-04 | **wider than normal** | smaller, unfocused | **lips slightly apart** |
| smug GP-05 | half lowered, lower lids pushed up | glancing right | **one corner up** |

<div class="pb"></div>

### GP-01 · Kasasagi · serious 认真 · redo

<!-- thumbs GP-01 -->

**Edit:** `GP-01_ref_a.png` (A_35, the picture behind her neutral portrait).
**Original:** Kasasagi standing; the hand on the right side of the image raised to the brim of her hat, the other hand holding a small paper lantern; a calm face, mouth closed.
**Original's face:** D = 67 px, eye line tilted 25°; eye opening ≈ 0.40 D; the upper lid just touching the iris; irises centred; closed mouth ≈ 0.14 D wide, 0.71 D below the eye line.

**Story.** Ten lines where she talks about her trade or locks onto a job, for example:
"The rope at the top of the third pillar is one turn short — the drum will shake it loose before midnight." (she will not take up the word "come back" and talks shop instead) · "So — where is this to be delivered?" (she turns a farewell gift into a delivery) · "This is my carrying frame." / "Get down." (the one thing she calls "mine"; the order slips out first) · "That was paid for with a peach." (watching a crow make off with a dumpling).
**Inner state:** a craftswoman sizing up a load — focused, competent, a little stern. Nothing emotional.

**Why redo.** Her neutral, serious and determined pictures were almost the same face; in three rounds of blind tests people could not tell them apart. This one must be clearly different from her neutral face, which is the very picture you edit.

**Target**

- Upper lids: lowered and drawn as a straight line, level with the eye line; lid cover 25–30%.
- Lower lids: raised ≈ 0.03–0.05 D, a little flatter.
- Eye opening ≈ 0.27–0.30 D (about 70% of now). Irises keep their size and place; catchlights stay (they may sit just under the lid line).
- Mouth: closed, a firm straight line ≈ 0.20–0.22 D long (about 1.5 × now), at the same height; corners neither up nor down; at least 3 px thick.
- No eyebrows, no blush.

**Must not read as:** angry (the lids must not slant down toward the nose), sleepy (lids level, not drooping; the lower lids raised, not slack), sad, smug.

**Checks for this item**

- C1 At 45%, the eyes are clearly narrower than in the original and the upper lids are flat.
- C2 The mouth is one straight line, visibly longer than in the original.
- C3 It does not look angry or sleepy.
- C4 The irises and catchlights are still visible.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-02 · Kasasagi · evasive 避开视线 · new

<!-- thumbs GP-02 -->

**Edit:** `GP-02_ref_a.png` (A_35).
**Original:** as GP-01 — standing, one hand at the hat brim, a small paper lantern in the other hand; a calm face.
**Original's face:** D = 67 px, eye line tilted 25°; eye opening ≈ 0.40 D; irises centred in the eyes; closed mouth ≈ 0.14 D wide.

**Story.** Six lines where she denies something or excuses herself with a perfectly straight face:
"Short people keep a load steadier." (deflecting a remark that she has not grown in thirty years) · "I did not eat it. I am only exchanging it." (to a stone statue, before anyone asks) · "I did not stagger." (nobody believes her) · "On the way down I… suffered a slight mishap." (she describes a fall the way a samurai describes a defeat) · and once in a sad scene: "Anyway, that wasn't a job."
**Inner state:** she will not meet the other person's eyes, but her face stays straight. The game adds a sweat-drop symbol in the comic lines and nothing in the sad one, so the face itself must carry no feeling: no embarrassment, no sadness.

**Why new.** Denying and excusing herself is her most frequent habit in the script, and none of her existing faces looks away.

**Target**

- Irises: both moved to the left side of the image until they touch the left corners of the eyes; a strip of white ≥ 0.12 D wide on the right of the near iris (about a third of the iris width).
- Upper lids: slightly lower; lid cover 15–20%; the lid line level.
- Mouth: closed, small (≈ 0.10–0.12 D), pressed — a slightly darker, firmer line; corners level.
- Nothing else changes: no blush, no frown.

**Must not read as:** shy or embarrassed (no blush, no wavy mouth), scared (eyes not wider), sad (lids not heavy), annoyed.

**Checks for this item**

- C1 At 45% you see at once that the irises sit at the left of the eyes (in the original they are centred).
- C2 The face is calm: not shy, not sad, not scared.
- C3 No blush.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-03 · Kasasagi · downcast 低落 · new

<!-- thumbs GP-03 -->

**Edit:** `GP-03_ref_a.png` (A_35).
**Original:** as GP-01 — standing, one hand at the hat brim, a small paper lantern in the other hand; a calm face.
**Original's face:** D = 67 px; eye opening ≈ 0.40 D; the upper lid just touching the iris; closed mouth ≈ 0.14 D wide.

**Story.** Three lines after the catastrophe:
"…go round by the mountain…" (on a treetop, looking at a drumstick and at the drum tower far below, she repeats what Granny asked of her; her voice trails off) · "At Granny's they'd be making lunch about now." (looking at a stove with no smoke) · "Thirty years, and not once late…" (she cannot finish).
**Inner state:** quiet grief she keeps to herself. She never says she is sad and she does not cry; the sadness has to be in the face.

**Why new.** Her existing "sad" face has tears.

**Target**

- Upper lids: lowered heavily; lid cover 45–55%; the lash line curving gently down toward the outer corner.
- Eye opening ≈ 0.18–0.22 D (about half of now).
- Irises: moved down, the lower edge resting on the lower lid; she looks down toward the lower right, at the ground in front of her.
- A small catchlight stays in each iris, so the eyes still look alive.
- Mouth: small and closed (≈ 0.12 D); corners ≈ 0.02 D lower than the middle.
- No tears, no wet shine, no blush.

**Must not read as:** sleepy (sleepy eyes still look ahead and the mouth is slack; here she looks down and the mouth corners drop), serious (flat lids, level gaze), crying, eyes closed (the irises must show).

**Checks for this item**

- C1 At 45%, the eyelids are clearly lowered and she is looking down.
- C2 No tears and no wet shine.
- C3 Clearly different from serious (GP-01): serious looks straight ahead with flat lids; downcast looks down with heavy lids.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-04 · Kasasagi · blank 茫然 · new

<!-- thumbs GP-04 -->

**Edit:** `GP-04_ref_a.png` (A_35).
**Original:** as GP-01 — standing, one hand at the hat brim, a small paper lantern in the other hand; a calm face.
**Original's face:** D = 67 px; eye opening ≈ 0.40 D; near iris ≈ 0.33 D wide; closed mouth ≈ 0.14 D wide, 0.71 D below the eye line.

**Story.** Four lines in which something enormous has happened and she talks about something small:
"It's almost noon." (waking up after the night of the catastrophe) · "I only waxed the door groove yesterday." (her fingers pass straight through the door handle: the house has become "far") · "It says not to call out." (passing on a radio announcement to the empty space beside her) · "I have not eaten it. I have only taken it into my keeping." (just after her first transfer; she answers only half the question).
**Inner state:** stunned; she has not caught up with what happened. The user once criticised that the heroine "showed no reaction at all" to a world-changing event: this face is her reaction.

**Why new.** Her "surprised" face is a quick jolt; this is a stopped, frozen moment.

**Target**

- Eye opening ≈ 0.46–0.50 D (about a fifth more than now); a thin line of white (≥ 0.03 D) above or below each iris.
- Irises 10–15% smaller (near iris ≈ 0.28–0.30 D wide), centred, looking straight ahead at nothing: both irises parallel, not turned toward anyone.
- Her normal iris colour and the catchlights stay.
- Mouth: the lips parted by a small dark gap ≈ 0.12–0.15 D wide and ≈ 0.04–0.05 D tall: a slit, not a round "o"; at the same place as now.
- The face is slack. No blush, no sweat.

**Must not read as:** surprised (a surprised mouth is round and the face tense), scared, eerie or dead (no empty, grey or glowing eyes; the user called such eyes eerie before), happy.

**Checks for this item**

- C1 At 45%, the eyes are visibly wider than in the original and the lips are slightly apart.
- C2 The eyes have their normal colour and highlights: not empty, grey or glowing.
- C3 It does not look surprised: the mouth is a slit, not a round "o".

**Image-tool prompt**

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

<div class="pb"></div>

### GP-05 · Kasasagi · smug 得意 · new

<!-- thumbs GP-05 -->

**Edit:** `GP-05_ref_a.png` (A_35).
**Original:** as GP-01 — standing, one hand at the hat brim, a small paper lantern in the other hand; a calm face.
**Original's face:** D = 67 px; eye opening ≈ 0.40 D; irises centred; closed mouth ≈ 0.14 D wide.

**Story.** Three lines:
"The Ninety-Nine Bends? I could go down them with my eyes closed." (a boast; later she falls on that very road) · "Take this as a deposit." (handing over Granny's rice ball as a deposit) · "It paid with a dumpling." (third beat of a running gag: what the crow stole has become "paid").
**Inner state:** a tiny flash of being one up, under a straight face — the straight-faced prankster. Only at the moment she has the upper hand.

**Why new.** The boast needs a smug face on its first beat for the later beats to land.

**Target**

- Upper lids lowered; lid cover 30–35%; the lid line almost flat.
- Lower lids pushed up ≈ 0.05 D and curved upward (the eyes smile from below); eye opening ≈ 0.22–0.26 D.
- Irises glancing toward the right (moved ≈ 0.05 D toward the right corners).
- Mouth: closed, ≈ 0.18–0.20 D long; its end on the right side of the image lifted ≈ 0.03–0.04 D, the other end level: a one-sided smirk, which may end in a tiny upward tick.
- Both eyes equally open (no wink). No teeth, no blush.

**Must not read as:** a happy smile (that is symmetrical with lifted cheeks), a wink, sleepy, serious.

**Checks for this item**

- C1 At 45% it reads as "pleased with herself, knows something": not her neutral face and not a happy smile.
- C2 The raised mouth corner on the right side of the image is visible.
- C3 No wink, no teeth, no blush.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-06 · Kasasagi · shout 喊 · redo

<!-- thumbs GP-06 -->

**Edit:** `GP-06_ref_a.png` (A_12, the picture behind her current shout portrait; keep the pose).
**Original:** Kasasagi walking quickly; the hand on the right side of the image raised to the hat brim, the other hand at her sash; mouth a little open, worried; a faint sweat drop on her near cheek.
**Original's face:** D = 61 px, eye line tilted 24°; eye opening ≈ 0.47 D; near iris ≈ 0.35 D wide; open mouth ≈ 0.34 D wide × 0.22 D tall, its centre 0.82 D below the eye line; the tip of the chin 1.30 D below it.

**Story.** One line: "Granny——!" A white tide sweeps up from the plain, and she calls down the mountain toward Granny's farmhouse. It is the only time in the whole segment that she raises her voice.
**Inner state:** desperate fear for someone she loves. Alarm, not anger.

**Why redo.** The current picture is a big mouth added onto a face that was not shouting; the user said it did not fit the perspective of her face. Blind testers also read all the current shouting faces as "surprised".

**Target**

- Mouth: open ≈ 0.42–0.50 D wide × 0.45–0.55 D tall — more than twice as tall as now and about a third wider; wide at the top and rounded at the bottom; a band of upper teeth ≈ 0.05 D tall along the top; the tongue in the lower third; inside a dark red-brown, much darker than the skin.
- Jaw: the chin moves down ≈ 0.12–0.18 D; the jaw line and cheek outline follow, so the face is visibly longer.
- The mouth's centre line follows the head: at right angles to the eye line, not straight down the canvas.
- Eyes: opening ≈ 0.50–0.55 D; irises about 15% smaller (≈ 0.30 D); a sliver of white above each iris; each upper lid line rises toward the nose (worry); catchlights stay.
- The faint sweat drop on her cheek goes. No eyebrows.

**Must not read as:** surprised (a small round "o" with no teeth), angry (lids slanting down toward the nose, clenched teeth), crying, laughing.

**Checks for this item**

- C1 (U5, check closely) The mouth is wide open with teeth showing, the jaw has dropped, and the mouth follows the tilt of the head.
- C2 At 45% it reads as shouting, not surprise.
- C3 Desperate, not angry: the upper lids rise toward the nose.
- C4 No sweat drop.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-07 · Kasasagi · pout 鼓腮 · redo

<!-- thumbs GP-07 -->

**Edit:** `GP-07_ref_a.png` (A_04; keep the hands-on-hips pose).
**Original:** Kasasagi standing with both hands on her hips; a small "3"-shaped pouting mouth.
**Original's face:** D = 72 px, eye line tilted 21°; eye opening ≈ 0.40 D; near iris ≈ 0.30 D wide; "3" mouth ≈ 0.15 D wide, ≈ 0.62 D below the eye line; the tip of the chin ≈ 1.03 D below it.

**Story.** Not used in the first segment; the user asked for all three girls' pouts to be redone for later scenes.
**Inner state:** sulking, piqued.

**Why redo.** The user: "I can't really see Kasasagi being huffy like the other two, and the white puffs next to their mouths make no sense." The original's tiny "3" mouth disappears at 128 px, so the puffed cheeks must change the outline of the face instead.

**Target**

- Far cheek (the right edge of her face in the image, between eye level and mouth level): pushed out ≈ 0.08–0.12 D beyond the original outline in one smooth curve (about a third of an iris width). The near cheek looks rounder through its shading.
- Mouth: a small pursed pout ≈ 0.08–0.10 D wide (about two thirds of now), lips pressed; at the same place.
- Eyes: lid cover 20–25%; irises glancing to the left side of the image, away from the listener on the right.
- Blush: soft pink on both cheeks, clearly pinker than her skin; colour only, no lines.
- No puff of air, no symbol near the mouth.

**Must not read as:** angry (no frown, no teeth), sad, a kiss.

**Checks for this item**

- C1 At 45%, the outline of her face (the cheek on the right side of the image) clearly bulges.
- C2 Nothing white and no symbol beside the mouth.
- C3 The blush is pink colour only, without lines.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-08 · Kasasagi · think 思考 · redo

<!-- thumbs GP-08 -->

**Edit:** `GP-08_ref_a.png` (A_34; keep the hands and the map).
**Original:** Kasasagi holding an open, folded map in both hands in front of her chest; a small mouth.
**Original's face:** D = 66 px, eye line tilted 27°; eye opening ≈ 0.42 D; near iris ≈ 0.32 D wide; small mouth ≈ 0.15 D wide, 0.68 D below the eye line.

**Story.** Not used in the first segment; the user said her current thinking face "looks odd".
**Inner state:** thinking hard, trying to recall or work something out.

**Why redo.** The original's face while reading the map is almost her neutral face; the current portrait only adds a thought bubble. The face itself has to show the thinking.

**Target**

- Irises: moved up and toward the left side of the image; the top 25–35% of each hidden under the upper lid; white showing below each iris (≥ 0.05 D).
- Near eye (on the left side of the image) narrowed: its lower lid raised ≈ 0.05 D, so it is a little narrower than the far eye.
- Mouth: closed, a short crooked line ≈ 0.14–0.16 D long, moved ≈ 0.04–0.05 D toward the left side of the image, its left end ≈ 0.02–0.03 D higher than its right end.
- Hands and map exactly as they are. No thought bubble, no question mark, no hand on the chin.

**Must not read as:** evasive (GP-02: irises to the left but level; here they go up), annoyed, sleepy.

**Checks for this item**

- C1 At 45% it reads as thinking without any bubble: irises up and to the left, the mouth pulled to one side.
- C2 No thought bubble, no question mark.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-09 · Saji · pout 鼓腮 · redo

<!-- thumbs GP-09 -->

**Edit:** `GP-09_ref_a.png` (C_04; keep the hands-on-hips pose).
**Original:** Saji standing with both hands on her hips; a small "3"-shaped pouting mouth; brows angled down.
**Original's face:** D = 75 px, eye line tilted 27°; eye opening ≈ 0.46 D; near iris ≈ 0.37 D wide; "3" mouth ≈ 0.13 D wide, ≈ 0.58 D below the eye line; the tip of the chin ≈ 1.08 D below it.

**Story.** Two lines: "You know weights so well — do something!" (her grown-up manner drops away and she whines like a child) · "No! This is MY house!" (refusing to climb down from Kasasagi's carrying frame).
**Inner state:** a childish sulk, stubborn and cross; not crying.

**Why redo.** The user asked for all three pouts to be redone (the white puffs make no sense, the huffiness does not show); the "3" mouth disappears at game size.

**Target**

- Cheeks: the far outline of her face (right side of the image) pushed out ≈ 0.10–0.15 D; the near cheek's lower contour visibly rounder. Both cheeks look puffed like a hamster's.
- Mouth: a small round pout ≈ 0.10–0.12 D across (about a third of an iris width), lips pushed forward.
- Brows: angled down toward the nose more steeply than now (inner ends ≈ 0.05 D lower).
- Eyes: upper lids slightly lowered at the nose side (a glare); irises toward the right corners of the eyes, glaring at the person on the right.
- Blush: a deeper pink than her natural rosy cheeks; colour only.
- Keep the headband, the bell and her natural rosy cheeks. No tears, no puff of air.

**Must not read as:** about to cry (no wet eyes, no wobbling mouth), shouting (the mouth is closed), a kiss.

**Checks for this item**

- C1 At 40%, both cheeks bulge out of the face outline: clearly "huffy".
- C2 Headband, bell and rosy cheeks are all there.
- C3 Nothing white beside the mouth.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-10 · Saji · shout 喊 · redo

<!-- thumbs GP-10 -->

**Edit:** `GP-10_ref_a.png` (C_12; keep the pose).
**Original:** Saji running forward, hands in loose fists; mouth open, brows worried; a faint sweat drop on her near cheek.
**Original's face:** D = 72 px, eye line tilted 23°; eye opening ≈ 0.52 D; near iris ≈ 0.39 D wide; open mouth ≈ 0.37 D wide × 0.27 D tall, its centre 0.85 D below the eye line; the tip of the chin 1.27 D below it.

**Story.** Four lines while Kasasagi is about to leave: "I'll give you luck! Luck! Lots! Five years' — no, ten years'!" · "Th-then, Lord Dumpling! I know where Lord Dumpling is kept!" · "Wait! I haven't given you Lord Dumpling yet!" · "Going won't help! People ran all night and never even touched the gate!"
**Inner state:** a small child desperately trying to stop someone from leaving; upset and close to tears, but not crying.

**Why redo.** As GP-06: the mouth did not fit the face, and blind testers read the shout as surprise.

**Target**

- Mouth: open ≈ 0.50–0.60 D wide × 0.50–0.60 D tall (about 1.5 × as wide and twice as tall as now); upper teeth showing; tongue; a dark inside.
- Jaw: the chin moves down ≈ 0.15–0.20 D; the face is visibly longer.
- Brows: raised high and drawn together; inner ends ≈ 0.05 D higher than now.
- Eyes: opening ≈ 0.55–0.60 D; irises about 10% smaller; catchlights stay.
- Cheeks flushed, deeper pink than her natural rosy cheeks.
- The faint sweat drop on her cheek goes. No tears.

**Must not read as:** surprised (a smaller round mouth), angry (brows down), crying.

**Checks for this item**

- C1 (U5, check closely) The mouth is wide open with teeth and tongue showing, and the jaw has dropped.
- C2 At 40% it reads as shouting, not surprise.
- C3 No tears, no sweat drop.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-11 · Saji · smug 得意 · new

<!-- thumbs GP-11 -->

**Edit:** `GP-11_ref_a.png` (C_04, the same original as GP-09; keep the hands-on-hips pose).
**Original:** Saji standing with both hands on her hips; a small "3"-shaped pouting mouth; brows angled down.
**Original's face:** D = 75 px; eye opening ≈ 0.46 D; "3" mouth ≈ 0.13 D wide.

**Story.** Two lines: "Decided. From today, this is my house!" (claiming Kasasagi's carrying frame as her home) · "And you, porter! If you walk under my house, pay rent!"
**Inner state:** proud, bossy and delighted with herself: a little landlady.

**Why new.** Her existing happy face reads as plain joy, and her mischievous face winks and reads as joking. This uses the same original as GP-09, so the two faces can alternate in the same scene without her body jumping.

**Target**

- Upper lids lowered and flat; lid cover 35–45%; the lower lids flat or slightly raised: half-lidded and superior.
- Brows: raised in a relaxed arc, no longer angled down; outer ends ≈ 0.05 D higher than now.
- Mouth: a closed grin ≈ 0.35–0.40 D wide (about three times the original mouth), U-shaped, the corners ≈ 0.05–0.07 D above the middle; no teeth, no fang.
- Cheeks flushed with pride, deeper pink than her natural rosy cheeks.
- Both eyes equally open: no wink.

**Must not read as:** her mischievous face (a wink and a fang), a plain happy smile (round open eyes), sleepy, angry.

**Checks for this item**

- C1 At 40% it reads as proud and pleased with herself.
- C2 No wink, no fang.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-12 · Shione · pout 鼓腮 · redo

<!-- thumbs GP-12 -->

**Edit:** `GP-12_ref_a.png` (B_04; keep the pose).
**Original:** Shione standing with both hands on her hips; a small wavy "3"-shaped pouting mouth.
**Original's face:** D = 68 px, eye line tilted 22°; eye opening ≈ 0.35 D; near iris ≈ 0.28 D wide; wavy mouth ≈ 0.2–0.25 D wide, ≈ 0.65 D below the eye line; the tip of the chin ≈ 1.07 D below it.

**Story.** Shione has no lines in the first segment; the user asked for all three pouts to be redone for later scenes.
**Inner state:** mild, well-mannered displeasure: she is calm and very polite, so her pout is small, but it must still read at game size.

**Why redo.** As GP-07: the white puff makes no sense, and the cheeks do not puff.

**Target**

- Far cheek (right side of the image): pushed out ≈ 0.06–0.08 D (about a quarter of an iris width) in a smooth curve.
- Mouth: a small pressed pout ≈ 0.10–0.12 D wide (about half the original wavy mouth).
- Eyes: lid cover ≈ 20%; irises glancing to the left side of the image.
- Blush: faint pink, colour only.
- The two red marks under the eye on the left side of the image and the single horn stay exactly as they are.
- No puff of air, no symbol.

**Must not read as:** angry, sad, a kiss.

**Checks for this item**

- C1 At 40%, the cheek on the right side of the image bulges a little and she reads as displeased.
- C2 The two red marks are in place; there is only one horn.
- C3 Nothing white beside the mouth.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-13 · Shione · shout 喊 · redo

<!-- thumbs GP-13 -->

**Edit:** `GP-13_ref_a.png` (B_12; keep the pose).
**Original:** Shione walking briskly, one hand in a loose fist; mouth open.
**Original's face:** D = 64.5 px, eye line tilted 19°; eye opening ≈ 0.44 D; near iris ≈ 0.31 D wide; open mouth ≈ 0.34 D wide × 0.20 D tall, its centre 0.82 D below the eye line; the tip of the chin ≈ 1.27 D below it.

**Story.** No lines in the first segment. She rarely raises her voice; when she does, it is to warn someone of danger.
**Inner state:** urgent, not fierce.

**Why redo.** The added mouth did not fit the face; blind testers read the shout as surprise.

**Target**

- Mouth: open ≈ 0.42–0.48 D wide × 0.40–0.48 D tall (about a third wider and more than twice as tall as now); upper teeth showing; a dark inside.
- Jaw: the chin moves down ≈ 0.10–0.15 D.
- Brows (through the thin bangs): raised and drawn together, worried.
- Eyes: opening ≈ 0.50 D; irises slightly smaller; catchlights stay.
- Marks and horn stay exactly as they are.

**Must not read as:** surprised, angry, frightened or crying.

**Checks for this item**

- C1 (U5, check closely) The mouth is wide open, the jaw has dropped, and the mouth follows the tilt of the head.
- C2 At 40% it reads as shouting.
- C3 The red marks and the horn are as in the original.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-14 · Shione · grin 开怀 · redo

<!-- thumbs GP-14 -->

**Edit:** `GP-14_ref_a.png` (B_02; keep the waving pose).
**Original:** Shione waving, the hand on the right side of the image raised; an open, round smiling mouth; faint pink hatching lines on her far cheek.
**Original's face:** D = 69.5 px, eye line tilted 23°; eye opening ≈ 0.41 D; near iris ≈ 0.35 D wide; open mouth ≈ 0.45 D wide × 0.30 D tall, its centre ≈ 0.69 D below the eye line; the tip of the chin ≈ 1.12 D below it.

**Story.** No lines in the first segment. Laughing warmly with a friend.

**Why redo.** In blind tests the original's round open mouth with wide-open eyes was read as shouting; the current portrait replaced it with a thin, unnatural line. Here the smiling eyes must make it read as happy.

**Target**

- Eyes: smiling crescents. The lower lids are pushed up into an upward curve; eye opening ≈ 0.15–0.20 D (about half of now); part of the iris and its catchlight still show.
- Cheeks lifted; a soft blush, colour only. Leave out the faint pink hatching lines the original has on her far cheek.
- Mouth: an open smile ≈ 0.40–0.45 D wide × 0.15–0.20 D tall (about as wide as now, two thirds as tall); a flat upper edge showing a band of upper teeth, a curved lower edge; the corners clearly turned up (≈ 0.06–0.08 D).
- Marks and horn stay exactly as they are.

**Must not read as:** shouting (a tall round mouth with open eyes), surprised, the thin line of a mouth in the current portrait.

**Checks for this item**

- C1 At 40% the eyes are curved with laughter and she reads as happy at once, not shouting or surprised.
- C2 The mouth is not a thin line.
- C3 The red marks and the horn are as in the original; no pink hatching lines.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-15 · Shione · serious 认真 · redo

<!-- thumbs GP-15 -->

**Edit:** `GP-15_ref_a.png` (B_25; keep the raised hand).
**Original:** Shione with the hand on the left side of the image raised, palm out (a "please wait" gesture); mouth closed.
**Original's face:** D = 65 px, eye line tilted 21°; eye opening ≈ 0.38 D; near iris ≈ 0.28 D wide; closed mouth ≈ 0.23 D wide, 0.68 D below the eye line.

**Story.** No lines in the first segment. Asking someone to stop and listen: calm, gently firm.

**Why redo.** The current portrait's pressed eyelids and drawn-on brows look unnatural.

**Target**

- Upper lids: slightly lower and straight; lid cover 20–25%.
- Lower lids: raised ≈ 0.02–0.03 D.
- Irises: a steady look at the listener on the right (slightly toward the right corners); catchlights stay.
- Brows (through the thin bangs): straight and level.
- Mouth: closed, a straight line ≈ 0.20 D, no curve.
- Marks, horn and the raised hand stay exactly as they are.

**Must not read as:** angry, cold, sad, or her ordinary calm face (round eyes, a soft small mouth).

**Checks for this item**

- C1 At 40% it reads as serious and steady, clearly different from her ordinary face: flatter lids, a straight mouth.
- C2 Not fierce, not cold, not sad.
- C3 The raised hand is unchanged.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-16 · Shione · blank 茫然 · redo

<!-- thumbs GP-16 -->

**Edit:** `GP-16_ref_a.png` (B_35; keep the lantern pose).
**Original:** Shione holding a paper lantern in the hand on the left side of the image, the other hand holding her sleeve; lips slightly parted; a few short pink-red strokes on her far cheek.
**Original's face:** D = 67 px, eye line tilted 17°; eye opening ≈ 0.40 D; near iris ≈ 0.31 D wide; mouth ≈ 0.18 D wide, slightly open, 0.72 D below the eye line.

**Story.** No lines in the first segment. This is the face for the moment she tells Kasasagi "I feel I have met you before" and startles herself: her memory is perfect, and she never half-remembers anything.
**Inner state:** a faint memory surfacing; for a moment she is lost in it.

**Why redo.** The current portrait made her irises grey and took the highlights out; the user called it eerie and unnatural.

**Target**

- Eyes: open as now, or up to ≈ 10% wider (≈ 0.42–0.45 D).
- Irises: normal rose-red with their catchlights; the gaze unfocused, drifting past the viewer into the distance: both irises shifted ≈ 0.03 D upward and looking the same way.
- Brows: inner ends raised ≈ 0.03–0.05 D.
- Mouth: the lips parted by a small gap ≈ 0.03–0.05 D tall, ≈ 0.12–0.15 D wide.
- Leave out the short pink-red strokes on her far cheek (below the eye on the right side of the image). Her only markings are the two red marks under the eye on the left side of the image.
- Horn and lantern pose stay exactly as they are.

**Must not read as:** eerie (no grey, pale, empty or glowing eyes), surprised (no round mouth, eyes not very wide), sad, sleepy.

**Checks for this item**

- C1 The eyes are their normal red with highlights: not grey, not empty, not glowing.
- C2 At 40% she reads as absent, clearly different from her ordinary face: her gaze is not on the viewer and her lips are slightly apart.
- C3 Nothing frightening about it; no marks under the eye on the right side of the image.

**Image-tool prompt**

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

<div class="pb"></div>

### Granny: GP-17 … GP-20

- **Order.** Make GP-17 first and hand it back on its own. The art team converts it into the game's pixel portrait and shows it to the user. Only when the user is satisfied do GP-18 … GP-20 follow, each in a new conversation, each an edit of the approved GP-17. If GP-17 is wrong, all three would have to be redone.
- **Who she is.** About seventy; the mother of the head of the village's leading farming household. She speaks 21 of the 32 lines of the prologue; the game's first line is hers. Gruff, practical and dry-humoured, warm underneath: she feeds people first, asks for things only halfway, jokes about her knees and her age, and never lets her kindness show. Her contrast with Kasasagi, who has not aged in thirty years, is the point of the scene: the height marks on a post, "The year I carved this, my hair was still black."
- **What the script says about her.** Bad knees (she sits on the wooden step inside the back door and pushes on her knees to stand up); stiff fingers; her hair used to be black; she has been shrinking and is now only a little taller than Kasasagi ("one day I'll be your height"); the little one of the house has hidden her glasses, so she squints at everything; she wipes a drumstick with her sleeve (a kimono with sleeves).
- **Appearance, for now** (the user approved these defaults and will look before deciding further): white hair pulled back into a small bun; a plain, faded indigo cotton summer kimono with a small pattern and ordinary sleeves; a dark apron (maekake); work-worn hands; no glasses, no walking stick, no jewellery. No regional costume: where the village is has not been decided.
- **No glasses in any of the four pictures.** In this scene they have been hidden.

<div class="pb"></div>

### GP-17 · Granny · design and neutral face 设定兼平常 · new drawing

<!-- thumbs GP-17 -->

**Style references:** `GP-17_ref_a.png` (B_01, Shione standing, one hand at her collar) and `GP-17_ref_b.png` (C_01, Saji standing, a fist at her chest, smiling). They show the style only: line work, colouring, level of detail, and how big a figure is on the canvas. Two different girls are attached so that it is clear you should copy the style, not a person. Draw a new character; give the image tool both pictures.

**Story.** Her everyday face, for ten lines, for example: "That's a bow knot. Tying the tower up like a present — what's that supposed to be?" · "Mm. Welcome back." · "There's a cucumber hanging in the well… Eat it while it's cool." · "Go round by the mountain."
**Inner state:** gruff everyday talk; affection disguised as orders.

**Target**

- One figure, full body, standing, a three-quarter view facing the right side of the image, head turned to the right like the girls; arms relaxed, hands empty, nothing in front of the face.
- Head size like the girls': D 60–75 px on the 1024 × 1536 canvas; the same kind of anime face as theirs, only old — not realistic. Eye line to chin about 1.1–1.25 D. About 6.5–7 heads tall standing straight; the slight stoop takes a little off (in the story she is now only a little taller than Kasasagi).
- Eyes: a squint — narrowed, curved eyelids with a little of the dark iris still showing (so that her other expressions can be made from this picture), and fine wrinkles at the outer corners.
- Mouth: a slightly grumpy line ≈ 0.25 D wide, the corners a little down.
- Age at a glance: white hair, a few clean wrinkle lines (eye corners, beside the mouth), a slight stoop. Wrinkles drawn as lines in the girls' style, not as texture.
- Colours: hair white with cool grey shading; the kimono a soft, greyish faded indigo, clearly lighter and greyer than deep navy (so she never looks like Kasasagi); the apron dark charcoal.

**Checks for this item** (instead of U4 and U9)

- C1 She reads as about seventy at a glance: white hair, wrinkles at the eyes and mouth, a slight stoop.
- C2 She squints (no glasses), and her mouth is a slightly grumpy line.
- C3 Side by side with the two references, she looks drawn by the same artist: line weight, colouring, level of detail.
- C4 She does not look like either girl: no horn, headband, cords or their clothes.
- C5 One full-body figure, three-quarter view facing right; hands empty, not covering the face.
- C6 1024 × 1536, truly transparent (U3); no text, colour swatches, extra views, background or ground shadow; no symbols (U6).
- C7 Her head is about as big as the girls' heads: D 60–75 px.
- C8 At 45% she is still clearly a squinting old woman.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-18 · Granny · smile 笑 · new (edit of the approved GP-17)

<!-- thumbs GP-18 -->

**Edit:** the user's approved GP-17 (`GP-17_granny_neutral.png`). Only after the user has approved GP-17.

**Story.** Two lines: "The grandchildren passed your mark long ago." (teasing Kasasagi about the height marks on the post) · "Me, I keep shrinking. One day I'll be your height." (joking about herself — and wishing to stand beside her).
**Inner state:** a dry, teasing grandmother's grin.

**Target**

- Eyes squeezed almost shut into curved slits; deep laugh lines at the outer corners.
- Cheeks pushed up.
- Mouth: a crooked closed-mouth grin, or slightly open; the corners clearly up (≈ 0.05 D).
- No blush, no glasses.

**Must not read as:** a sweet, soft smile; mockery.

**Checks for this item**

- C1 (U4) Against GP-17, only the face changes.
- C2 At 45% she reads as grinning: eyes squeezed into slits, laugh lines.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-19 · Granny · wistful 怀念 · new (edit of the approved GP-17)

<!-- thumbs GP-19 -->

**Edit:** the user's approved GP-17 (`GP-17_granny_neutral.png`).

**Story.** Four lines: "The year I carved this, my hair was still black." (touching an old mark on the post) · "Shame about that drum." (it is being played badly; her late husband used to play it) · "There's one person missing at the top." (looking up at the drum tower) · "I know one." (a glance at the hemp stalks by the door, set out for the returning dead — her husband — without saying who).
**Inner state:** quiet, private nostalgia.

**Target**

- Eyelids lowered: she looks down at something close in front of her.
- The squint softened.
- Mouth relaxed, with the faintest sad smile, small but visible.
- No tears, no wet shine, no glasses.

**Must not read as:** sleepy, crying, stern.

**Checks for this item**

- C1 (U4) Against GP-17, only the face changes.
- C2 At 45% she reads as remembering: eyes lowered to something nearby.
- C3 No tears, no wet shine.

**Image-tool prompt**

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

<div class="pb"></div>

### GP-20 · Granny · stern 板脸 · new (edit of the approved GP-17)

<!-- thumbs GP-20 -->

**Edit:** the user's approved GP-17 (`GP-17_granny_neutral.png`).

**Story.** Five lines: "Ten. Don't count this one in." (keeping back the tenth lantern) · "This one's for coming back. Light your feet with it on the way down." · "Whoever says that falls first." · "Give me back my glasses!" (to the hidden little one indoors) · "Change? It wouldn't dare."
**Inner state:** an elder scolding a child: stern but fond.

**Target**

- Brows drawn together and down (inner ends ≈ 0.05–0.08 D lower).
- Eyes narrowed into a hard squint.
- Mouth pressed into a frown; the corners turned down ≈ 0.03–0.05 D, visible when small.
- No glasses.

**Must not read as:** truly angry, hateful, sad.

**Checks for this item**

- C1 (U4) Against GP-17, only the face changes.
- C2 At 45% she reads as scolding: brows down, eyes narrowed, mouth corners down.
- C3 Stern but fond; not real anger.

**Image-tool prompt**

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
