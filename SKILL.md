---
name: dsh-voice
metadata:
  version: "2.0.0"
  requires:
    env: ["BREEZE_API_KEY"]
description: >-
  语音合成（TTS）与语音识别（STT）入口：用户要把文字读出来、配音、生成语音、
  换音色、控制语气情绪，或要听懂一段音频/录音说了什么时使用。
  **定制专属音色也走本技能**：文字描述造声（design）、上传音频克隆声音（clone）、
  保存为可复用音色（save）、查看/删除我的音色（myvoices/delete）。
  **批量合成（batch）** 适合有声书、长文配音、批量播报，跑前可 --dry-run 预估成本。
  TTS 走 Breeze Blue（breeze-tts-2，522 个中文音色、8 种中文口音、
  表演指令、音效标签，实测首音延迟约 525ms）；STT 走阿里百炼 bl CLI
  （Breeze 只有 TTS，无转写端点，实测确认 60 path / 84 op 零个 ASR）。
  零第三方依赖，纯 Python 标准库实现；429/503 自动按 Retry-After 退避重试。
  反触发：普通问答、编程、写作不触发；只是要放个本地音频文件用宿主的
  present 工具即可，不需要本技能。
---

# 语音合成与识别（鲸歌 · dsh-voice）

用 `assets/` 下的两个脚本。**当前工作目录可能不是本技能目录**，先定位技能根：

```bash
SKILL_DIR="$(dirname "$(find ~/.dsh/skills -name SKILL.md -path '*dsh-voice*' 2>/dev/null | head -1)")"
```

Windows 下找不到就直接用绝对路径 `~/.dsh/skills/dsh-voice/assets/`。

---

## 一、TTS：文字 → 语音

脚本 `assets/breeze_tts.py`（纯标准库，无需 pip install）。

### 常用

```bash
# 最简：自动挑一个中性普通话音色
python "$SKILL_DIR/assets/breeze_tts.py" speak "你好，世界" -o hello.mp3

# 指定音色（先用 voices 命令查 voice_id）
python "$SKILL_DIR/assets/breeze_tts.py" speak "你好" --voice voc_4zu675fmv6g5 -o hi.mp3

# 加表演指令 + 强度（指令必须与正文同语言，≤1000字符）
python "$SKILL_DIR/assets/breeze_tts.py" speak "我不知道他会来这里。" \
  --instructions "压低声音耳语，紧张而克制，像怕被旁边的人听见。" \
  --guidance 2.0 -o whisper.mp3
```

### 找音色（不扣费）

```bash
# 中性标准口音（推荐用于通用对话）
python "$SKILL_DIR/assets/breeze_tts.py" voices --lang zh --accent null

# 按关键词搜
python "$SKILL_DIR/assets/breeze_tts.py" voices --lang zh --search 温暖

# 带口音的（北京/台湾/粤语等，用 accent 码，不用 null）
python "$SKILL_DIR/assets/breeze_tts.py" voices --lang zh --search 京巷
```

### 查余额 / 模型（不扣费）

```bash
python "$SKILL_DIR/assets/breeze_tts.py" balance
python "$SKILL_DIR/assets/breeze_tts.py" models
```

---

## 一.5、定制音色（造声 / 克隆 / 保存）

想让 AI 说特定的声音，两条路：**文字描述造声** 或 **上传音频克隆**。
两者都是「先生成预览 → 试听 → 保存为音色」，**保存后拿到 voice_id 就能像内置音色一样用**。

### 路线 A：文字描述造声

```bash
# 生成 2 个候选，脚本就是试听用的那句
python "$SKILL_DIR/assets/breeze_tts.py" design \
  "一个温柔的年轻女声，带一点气声，语速偏慢，适合讲睡前故事。" \
  --text "夜深了，星星在窗外眨眼睛。" \
  --guidance 3 --count 2 --out design_preview
```

- `description` 必填，**3–500 字符**，写角色/基础声音/音色质感/语速/情绪中心
- `--text` 试听脚本，3–500 字符（建议写该角色会自然说出的话）
- `--guidance` 1.0–10.0，贴合度；**省略则随机 1–4**
- `--count` 一次生成几个候选（计费**不随候选数翻倍**，只按脚本算一次）

### 路线 B：上传音频克隆

```bash
python "$SKILL_DIR/assets/breeze_tts.py" clone 我的录音.wav \
  --name "我的声音" --lang zh --out clone_preview.mp3
```

**参考音频硬性要求**（不满足会被拒）：

| 项 | 要求 |
| --- | --- |
| 数量 | 恰好 1 个文件 |
| 格式 | **MP3 或 WAV** |
| 时长 | **≥ 3 秒**（无上限） |
| 大小 | **≤ 5 MB** |
| 内容 | **单一说话人，无背景音乐/噪音** |

> ⚠️ **想克隆的片段必须放在音频前 60 秒内**——只分析前 60 秒，最多保留 30 秒，
> 并在完整句子处截断。上传完整素材让它自己选切点。
> `--denoise` 可对嘈杂样本先去噪。

### 保存为音色（两条路线共用）

```bash
python "$SKILL_DIR/assets/breeze_tts.py" save gvi_xxxxxxxxxx \
  --name "睡前故事女声" --lang zh \
  --description "温柔带气声的年轻女声" \
  --tone "gentle,warm,calm"
```

- `preview_id` 是预览的 `generated_voice_id`（`gvi_` 开头），**不是** voice_id
- `--lang` 默认 zh；参考音频/描述是其他语言时显式指定
- `--tone` 最多 3 个，20 个色调码见 `reference/voices.md`

### 管理我的音色

```bash
python "$SKILL_DIR/assets/breeze_tts.py" myvoices          # 列出（不扣费）
python "$SKILL_DIR/assets/breeze_tts.py" delete <voice_id> # 删除，释放名额
```

**免费档最多保存 5 个音色**，满了必须先删一个。
`delete` 默认拒绝删公共目录音色（保护误删），要删自己的才有效。

### 批量合成（有声书 / 长文配音）

文本文件**每行一段**（空行自动跳过），一次跑完：

```bash
# 先算成本，不扣费
python "$SKILL_DIR/assets/breeze_tts.py" batch 章节.txt --dry-run

# 确认后真跑
python "$SKILL_DIR/assets/breeze_tts.py" batch 章节.txt \
  --voice <voice_id> --outdir out/
```

- 输出 `out/part_0001.mp3`, `part_0002.mp3`, …
- `--separator` 可改分隔方式（默认按行）
- `--instructions` 统一应用到所有段
- 跑前必报总成本，单段失败不影响其余段

### 成本预检（怕扣费先跑这个）

```bash
python "$SKILL_DIR/assets/breeze_tts.py" speak "文本" --dry-run   # 只看参数与成本
```

### 健壮性说明

- **自动重试**：429（并发满）/503（容量耗尽）按 `Retry-After` 退避重试，最多 3 次
- **不可重试错误立即退出**：401/402/404/422 不浪费时间重试
- **删除保护**：`delete` 拒绝删公共音色，需 `--force`

### 计费与限制

| 操作 | 计费 |
| --- | --- |
| speak / batch | 按文本（CJK 每字 2 单元，10 单元 = 1 credit） |
| design | 预览脚本一次（CJK 每字 2 单元）；候选数不翻倍；全失败则退还 |
| clone | 预览脚本一次 **+ 参考音频上传分析 1 credit** |
| save | **不额外扣费**（只占一个音色名额） |
| myvoices / voices / delete / balance / models | 不扣费 |

实测参考：
- design 2 候选 + save + 自建音色合成 + clone ≈ **14.4 credits**
- batch 3 段（约 30 汉字）≈ **5.4 credits**，与预估一致

---

## 二、STT：音频 → 文字

脚本 `assets/breeze_stt.py`。**注意：沙箱里 subprocess 无法创建进程（WinError 5），
所以优先用 shell 直调 `bl`**，subprocess 版留作非沙箱环境使用。

### 首选：shell 直调（沙箱里可用）

```bash
bl speech recognize --url "/绝对路径/音频.mp3" --model qwen3-asr-flash --language zh
```

转写结果在 stdout，元信息在 stderr。

### 备选：封装脚本（非沙箱环境）

```bash
python "$SKILL_DIR/assets/breeze_stt.py" 音频.mp3 --language zh
python "$SKILL_DIR/assets/breeze_stt.py" 音频.mp3 --json
```

---

## 三、关键约束（务必遵守）

### 计费

- **CJK 字符每个算 2 个计费单元，10 单元 = 1 credit**
- `speak` 命令会打印 `[计费预估]`，合成前先看一眼
- 目录查询（`voices`/`models`/`balance`）**不扣费**，可以随便调
- Free 档并发上限 **2**，且 `commercial_use_allowed: false`

### 语言与模型

- 中英文用默认 `breeze-tts-2`；**其他 49 种语言必须加 `--model breeze-tts-2-multilingual`**
- 平台**不检测文本语言**。显式给了 `--model` 就绝不自动切换，语言不匹配直接报错

### 表演指令（instructions）

- `--instructions` ≤ 1000 字符，**必须与正文同语言**（不会自动翻译）
- `--guidance` 1.0–10.0；表达力段落建议 **2–3**，连续旁白用默认 1.0
- 指令描述**表演**（情绪/情境/意图/身体状态），不要写声音身份（年龄/口音/音色）

### 音效标签（audio tags）

- **中文用方括号 `[]`，英文用圆括号 `()`，同一请求不能混用，不要自己翻译**
- 中文示例：`[叹气]` `[笑]` `[咳嗽]` `[耳语]` `[打哈欠]` `[清嗓]`
- 英文示例：`(sighs)` `(laughs)` `(coughs)` `(whispers)`
- 常见拼写坑（英文）：`sing`→`(singing)`、`cry`→`(crying)`、`pause`→`(pause)` 无 s

### 输出格式

- 默认 `mp3_44100_128`；可 `--format mp3` / `wav` / `flac` / `pcm`
- **加采样率的格式（如 `wav_48000`）只在非流式可用**
- 原生 24000 Hz，更高采样率只是重采样，不增加音质

### 错误处理

- 收到 `429 GENERATION_CONCURRENCY_EXCEEDED` → 按 `Retry-After` 退避重试
- 收到 `503 GENERATION_CAPACITY_EXCEEDED` → 稍等再试，**不要立即重试**
- 收到 `402` → 余额或 key 预算不足，去充值，**不要重试**
- 传输超时**不要盲目重发**：先用 `balance` 查是否已扣费，避免重复计费

---

## 四、Breeze 与 bl 的分工

| 能力 | 用哪个 | 原因 |
| --- | --- | --- |
| **TTS** | **Breeze** `breeze_tts.py` | 522 个中文音色、8 种口音、表演指令、音效标签、实测 525ms 首音 |
| **STT** | **bl** `bl speech recognize` | Breeze **没有**转写端点（实测 60 path / 84 op 全查过） |

两家已验证互通：**Breeze 生成的音频，bl 能正确识别**。

如果 Breeze 不可用（无 key/欠费），TTS 可退化到 `bl speech synthesize`
（但只有 2 个音色：`longanlingxin` 龙安灵心、`longanlufeng` 龙安鲁风，
且 `--out` 在沙箱里会因 mkdir `C:\Users\<user>\bailian-output` 报 EPERM，
需改用 `--stream` 输出到 stdout 再重定向）。

---

## 五、合规提示

- Free 档 **`commercial_use_allowed: false`** —— 自用/学习/开源开发没问题，
  **对外商用必须升级付费套餐**
- **任何情况下都不要把 API key 写进代码或提交到仓库**，
  一律从环境变量或 `.env` 读取（本技能已是如此）
