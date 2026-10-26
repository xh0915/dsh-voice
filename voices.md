# 中文音色速查表

> 数据来源：`GET /v1/voices?language_code=zh&accent_mode=unmarked`（实测拉取）
> 中性普通话音色共 **307 个**；中文音色总数 **522 个**（含各类口音）。
> 完整列表用 `voices` 命令查，本表只列**推荐用于对话/配音的常用款**。

## 先理解三个概念

| 概念 | 说明 |
| --- | --- |
| **中性口音** | `accent = null`，就是标准普通话。做通用 Agent **首选这类** |
| **带口音** | 北京/台湾/粤语/四川/上海/河南/陕西/东北 8 种，需要显式指定 accent 码 |
| **tone 色调** | 每个音色最多 3 个标签，如 `warm` 温暖 / `calm` 平静 / `playful` 俏皮 |

**筛选中性普通话**：`voices --lang zh --accent null`

---

## 一、日常对话 / Agent 语音（首选）

这类最像"真人跟你说话"，适合客服、助手、播客。

| voice_id | 名称 | 性别 | 年龄 | 色调 | 适合 |
| --- | --- | --- | --- | --- | --- |
| `voc_4zu675fmv6g5` | **温谈** | 男 | 中年 | friendly, steady | **通用对话首选**，生活化松弛感 |
| `voc_p36dbdewwvae` | **邻家暖心** | 女 | 青年 | warm, gentle, friendly | 日常 Vlog、温情播客 |
| `voc_pyum6u5hhakh` | 暖心健身教练 | 男 | 青年 | warm, articulate, measured | 运动、鼓励场景 |
| `voc_rp4d97swre6u` | 暖心医护向导 | 女 | 中年 | articulate, steady, compassionate | 医疗科普、专业引导 |
| `voc_kcb2gbgwh6xw` | 干练安全官 | 女 | 中年 | articulate, calm, energetic | 客服、紧急播报（语速快） |
| `voc_arfcjgb3qc92` | 清风引路人 | 女 | 中年 | steady, playful, reflective | 职场知性、午间电台 |

## 二、舒缓 / 冥想 / 睡前

语速慢、气声多、有留白。

| voice_id | 名称 | 性别 | 年龄 | 色调 |
| --- | --- | --- | --- | --- |
| `voc_gwm7kudgccrq` | 静心向导 | 女 | 青年 | authoritative, warm, gentle |
| `voc_g7u6amptef56` | 柔光疗愈师 | 女 | 青年 | calm, gentle, measured |
| `voc_s39b3dxx49cu` | 入梦引路人 | 女 | 青年 | steady, compassionate, measured |
| `voc_489858zqxwvx` | 晨曦引者 | 女 | 青年 | gentle, calm, articulate |
| `voc_88m33quvddn7` | 静雨引导者 | 女 | 青年 | measured, gentle, steady |
| `voc_xhfrasjwjgad` | 麦田 | 男 | 中年 | warm, sincere, reflective |

## 三、朗诵 / 文学 / 深沉叙事

胸腔共鸣强、有阅历感。

| voice_id | 名称 | 性别 | 年龄 | 色调 |
| --- | --- | --- | --- | --- |
| `voc_xhfrasjwjgad` | 麦田 | 男 | 中年 | warm, sincere, reflective |
| `voc_k4nugra4uwte` | 荒原守望者 | 男 | 老年 | weary, steady, reflective |
| `voc_x2h3ffe7w3we` | 松风居士 | 男 | 老年 | warm, precise, articulate |
| `voc_yxcbcvb2dz7a` | 醉月诗人 | 男 | 青年 | gentle, articulate, playful |
| `voc_7bp6w9rf637t` | 纸影说书匠 | 男 | 老年 | precise, rhythmic, refined |

## 四、游戏角色 / 戏剧化

情绪张力大，适合 NPC、有声书角色。

| voice_id | 名称 | 性别 | 年龄 | 色调 |
| --- | --- | --- | --- | --- |
| `voc_pd36639843sk` | 铁血守望者 | 男 | 中年 | authoritative, steady, passionate |
| `voc_pmkjwbcphjdr` | 狡黠猎犬 | 男 | 青年 | energetic, playful, rhythmic |
| `voc_nf7ez6x892w3` | 荒原复仇者 | 男 | 青年 | authoritative, weary, steady |
| `voc_38unzzmn7g2w` | 灵狐帕奇 | 男 | 青年 | playful, energetic, articulate |
| `voc_w3h2quj4qdfd` | 癫狂炼金士 | 男 | 中年 | passionate, urgent, articulate |
| `voc_29w68sjfb8c3` | 幻影报幕员 | 男 | 中年 | passionate, bright, gentle |

## 五、儿童 / 特殊质感

| voice_id | 名称 | 性别 | 年龄 | 色调 |
| --- | --- | --- | --- | --- |
| `voc_uejhdugavcdu` | 灵动雨珠 | 女 | 儿童 | bright, precise, articulate |
| `voc_522jzr944zs4` | 古木假面 | 女 | 老年 | weary, articulate, measured |
| `voc_w45se56jp6xm` | 虚空执事 | 男 | 青年 | bright, precise, refined |

---

## 六、带口音的音色

需要显式指定，**不能用 `--accent null`**。用关键词搜索：

```bash
# 北京口音（京巷系列，约 12 个）
voices --lang zh --search 京巷
# 例：京巷潮生(男青年) 京巷书灯(男中年) 京巷霞光(女中年) 京巷风铃(男老年)
```

**8 种中文口音码**（`accent` 字段）：

| 口音 | accent 码 |
| --- | --- |
| 普通话（标准） | `null` |
| 东北 | `mandarin_northeastern` |
| 陕西 | `mandarin_shaanxi` |
| 上海 | `mandarin_shanghai` |
| 四川 | `mandarin_sichuan` |
| 河南 | `mandarin_henan` |
| 北京 | `mandarin_beijing` |
| 台湾 | `mandarin_taiwan` |
| 粤语 | `cantonese` |

---

## 七、tone 色调码全表（20 个）

挑音色时按这个对照：

`warm` 温暖 · `calm` 平静 · `bright` 明亮 · `gentle` 柔和 · `energetic` 有活力
`authoritative` 威严 · `sincere` 真诚 · `weary` 疲惫 · `precise` 精准 · `refined` 优雅
`urgent` 急促 · `friendly` 亲切 · `articulate` 吐字清晰 · `steady` 稳定 · `playful` 俏皮
`compassionate` 有同理心 · `reflective` 沉思 · `measured` 从容 · `rhythmic` 有节奏 · `passionate` 饱满

---

## 八、换音色对比测试的做法

想知道哪个音色最适合你，用同一段文本批量试：

```bash
for V in voc_4zu675fmv6g5 voc_p36dbdewwvae voc_xhfrasjwjgad; do
  python breeze_tts.py speak "这是同一段测试文本。" --voice $V -o "test_$V.mp3"
done
```

**注意**：每次合成都扣费（10 个汉字 ≈ 20 单元 ≈ 2 credits）。
先用 `voices` 命令看描述筛掉明显不合适的，再实测 2-3 个。
