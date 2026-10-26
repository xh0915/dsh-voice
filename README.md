# 鲸歌 · dsh-voice

**把文字读成声音，把录音听写成文字。**

**中文** · [English](README.en.md)

## 先看一个场景

晚上十一点，你改完一章小说，想听一遍再睡。你在 DeepSeek Harness 里说：

> 把 chapter03.txt 里每一段都读出来，用温暖一点的声音。

鲸歌先报出总字数和预计花费，你确认之后再开始合成。跑完，`chapter03_audio/` 里是 `part_0001.mp3`、`part_0002.mp3`……一段一个文件。

第二天你把手机录音丢回去，说「听听这段说了什么」，它把录音转成文字给你。

不用装浏览器插件，不用打开第二个网站，也不用 `pip install`。仓库里只有几个 Python 文件，全部用标准库写完。

## 能做什么

- **朗读**：一句话到一整篇文章。522 个中文音色，含北京、台湾、粤语、四川等 8 种口音。
- **表演**：用自然语言指挥语气——耳语、兴奋、讥讽、克制的悲伤。文本里写 `[叹气]` `[笑]` `[咳嗽]`，读出来就真的有这些反应。
- **定制专属音色**：文字描述造声，或上传一段录音克隆。先出预览，试听满意再保存；免费档最多存 5 个。
- **批量配音**：文本文件每行一段，一次跑完，适合有声书和长文。
- **听写**：把音频、录音转成文字。这一步走阿里百炼，因为 Breeze 只做语音合成，没有转写接口。
- **先算钱**：`speak` 和 `batch` 支持 `--dry-run`，只看参数和成本，不扣费。定制音色会先生成预览（预览会计费），试听满意再保存。

## 长这样

下面是真实终端输出。`--dry-run` 只算钱，不生成音频，也不扣费：

```text
$ python assets/breeze_tts.py speak "你好，世界" --dry-run
[计费预估] 5 字符 = 9 单元 ≈ 0.9 credits

[dry-run] 未扣费。合成参数：
  音色   (自动挑选)
  模型   breeze-tts-2   语言 zh   格式 mp3_44100_128
  语速   1.0   强度 1.0
  文本   你好，世界

确认无误后去掉 --dry-run 重跑。
```

批量合成也会先报总成本：

```text
$ python assets/breeze_tts.py batch 章节.txt --dry-run
[批量] 2 段，预计消耗 52 单元 ≈ 5.2 credits

[dry-run] 未扣费。各段预览：
    1. [  24单元] 夜深了，星星在窗外眨眼睛。
    2. [  28单元] 她把书合上，轻轻说了一句晚安。

确认无误后去掉 --dry-run 重跑。
```

## 怎么装

需要三样东西：

1. **Python 3.9 或更高**（安装器会先检查；没有会直接提示）
2. **Breeze API key** —— 在 <https://breezeblue.ai/app/developer/api-keys> 申请
3. **DeepSeek Harness** —— 技能装好后会自动发现

把仓库克隆下来，运行安装器：

```sh
git clone https://github.com/xh0915/dsh-voice
cd dsh-voice
bash install.sh
```

Windows 用自带的 Windows PowerShell：

```powershell
git clone https://github.com/xh0915/dsh-voice
cd dsh-voice
powershell -ExecutionPolicy Bypass -File install.ps1
```

安装器会把技能复制到 `~/.dsh/skills/dsh-voice`。之后 Harness 会自动发现；如果没出现，重开一次 Harness。

鲸歌是一个**技能（skill）**，不是带界面的宿主插件；所以不需要 `dsh plugin add`，装到 skills 目录就够了。

### 填 key

不要把 key 写进代码，也不要提交到任何仓库。把仓库里的 `.env.example` 复制成 `.env`，填好后放在下面任意一个位置：

- 你当前的工作目录（只对这个项目生效）
- 技能目录 `~/.dsh/skills/dsh-voice/.env`（装好后对所有项目生效）
- `~/.dsh/.env`（对所有项目生效，推荐）

```dotenv
BREEZE_API_KEY=brz_你的key
DASHSCOPE_API_KEY=sk-你的key    # 只有听写需要；已用 bl auth login 登录可留空
```

### 验证

```sh
python ~/.dsh/skills/dsh-voice/assets/breeze_tts.py balance
```

Windows 上把路径写成 `$HOME\.dsh\skills\dsh-voice\assets\breeze_tts.py`。

能打印出余额，就说明 key 读到了。这一步不扣费。

### 听写要额外装一个命令行工具

语音合成不需要它；只有「把音频转成文字」才需要：

```sh
npm install -g bailian-cli     # 需要 Node.js 22.12 或更高
bl auth login --console        # 或者 bl auth login --api-key sk-...
```

## 怎么用

装好后直接在 Harness 里说：

```text
把这段话用温暖的声音读出来：欢迎回来，今天辛苦了。
```

```text
帮我找一个适合睡前故事的中文音色。
```

```text
听听这段录音说了什么：C:\audio\meeting.mp3
```

也可以自己敲命令：

```sh
SKILL=~/.dsh/skills/dsh-voice/assets

# 先看成本，不扣费
python $SKILL/breeze_tts.py speak "你好，世界" --dry-run

# 确认后合成
python $SKILL/breeze_tts.py speak "你好，世界" -o hello.mp3

# 加表演指令
python $SKILL/breeze_tts.py speak "我不知道他会来这里。" \
  --instructions "压低声音耳语，紧张而克制，像怕被旁边的人听见。" \
  --guidance 2.0 -o whisper.mp3

# 找音色（不扣费）
python $SKILL/breeze_tts.py voices --lang zh --search 温暖
```

定制音色、批量合成、听写的完整用法，写在 `SKILL.md` 里，agent 会自己查。

## 要花多少钱

**按加权字符数计费：中文/日文/韩文字每个算 2 个单元，其他字符算 1 个，10 单元 = 1 credit。**

| 项目 | 价格 |
| --- | --- |
| 充值 | $3 = 10,000 credits（最低 $5 起充） |
| 100 个中文字 | ≈ 20 credits ≈ **$0.006**（约 4 分钱） |
| Free 档并发 | 2 个生成槽 |
| Free 档每日 | 可领 400 credits，够跑约 15 轮完整测试 |

**不扣费的操作**：`voices` / `models` / `balance` / `myvoices`，以及任何 `--dry-run`。
**扣费的操作**：`speak` / `batch` / `design` / `clone`。

实测参考：design 生成 2 个候选 + save + 用自建音色合成 + clone，一共约 **14.4 credits**；batch 3 段（约 30 个汉字）约 **5.4 credits**，和预估值一致。

价格以 Breeze 官方计价页为准；本仓库不代收费用。

## 它不会做的事

- **不会偷偷扣费。** `speak` / `batch` 生成前先报成本，`--dry-run` 只算不跑；定制音色的预览会计费，但只有你明确要求时才调用。
- **不会内置 key，也不会把 key 发给我们。** 这个项目没有服务器，key 只在你本机读取，再直接发给服务商。
- **不做实时通话，也不接麦克风。** 它处理的是文本和音频文件，不是电话或直播。
- **不替你翻译。** 中英文用默认模型；其他语言要显式加 `breeze-tts-2-multilingual`，语言不匹配会直接报错。
- **不盲目重试。** 只有 429（并发满）和 503（容量不足）会按服务端提示退避重试；网络超时后会停下来提醒你先查余额，避免重复扣费。
- **不克隆未经授权的声音。** 克隆他人声音前，必须自己拿到说话者的同意。
- **不帮你绕过商用限制。** Free 档的 `commercial_use_allowed` 是 `false`，对外商用要先升级付费套餐。
- **不假装 Breeze 能听写。** Breeze 只有语音合成；听写这部分明确走阿里百炼，不会混在一起说。

## 隐私与 key

- 仓库里**没有任何真实 key**，`.env` 已被 `.gitignore` 排除。
- key 只从环境变量或 `.env` 读取，不写进代码，不写进日志。
- 合成时，文本会发给 Breeze；定制音色时，描述或参考音频也只发给 Breeze；听写时，音频发给阿里百炼。这是生成所必需，除此之外没有别的上传。
- 生成的音频只写在你指定的本地目录。
- 没有遥测、没有统计、没有远程配置。
- 如果 key 泄露，立刻去平台轮换：`POST /v1/api-keys/{key_id}/rotate`（旧 key 有 30 天兼容期）。

## 设置

| 变量 | 必需 | 用途 |
| --- | --- | --- |
| `BREEZE_API_KEY` | 合成必需 | Breeze Blue 的 API key，`brz_` 开头 |
| `DASHSCOPE_API_KEY` | 听写需要 | 阿里百炼的 key；已 `bl auth login` 登录过可省略 |

`.env` 的读取顺序是**就近优先**：当前工作目录 → 技能目录（`~/.dsh/skills/dsh-voice/.env`）→ `~/.dsh/.env`。

<details>
<summary><b>技术细节（要改代码的人点这里）</b></summary>

### 目录

```text
SKILL.md                 # 技能定义：触发条件、命令用法、计费与约束
README.md                # 本文件
README.en.md             # 英文版
LICENSE                  # MIT + 第三方服务边界说明
CHANGELOG.md             # 版本记录
.env.example             # 配置示例（复制为 .env）
install.sh               # 安装 / 检查 / 卸载（Linux、macOS）
install.ps1              # 安装 / 检查 / 卸载（Windows PowerShell）
assets/
  breeze_tts.py          # 语音合成、定制音色、批量合成、重试（纯标准库）
  breeze_stt.py          # 语音识别封装，调用 bl CLI
reference/
  voices.md              # 中文音色速查表（307 个中性普通话）
tests/
  test_cli.py            # 离线测试：help、dry-run、错误处理、无密钥泄露
```

`开发资料/` 和 `Breeze_Blue_文档全景.md` 是本地开发归档，不进入公开仓库，也不会随安装器复制。

### 命令总览

| 命令 | 作用 | 扣费 |
| --- | --- | --- |
| `speak` | 文本 → 音频 | 是 |
| `batch` | 文本文件 → 多段音频 | 是 |
| `design` | 文字描述造声 | 是 |
| `clone` | 上传音频克隆 | 是 |
| `save` | 把预览保存为音色 | 否（占名额） |
| `delete` | 删除音色，释放名额 | 否 |
| `voices` | 查公共音色目录 | 否 |
| `myvoices` | 查我的音色 | 否 |
| `balance` | 查余额 | 否 |
| `models` | 查可用模型 | 否 |

### 两家的分工

| 能力 | 走哪家 | 为什么 |
| --- | --- | --- |
| 语音合成 | [Breeze Blue](https://breezeblue.ai)，模型 `breeze-tts-2` | 中文音色多、口音细、支持表演指令和音效标签 |
| 语音识别 | 阿里百炼 `bl speech recognize` | Breeze 没有转写端点（实测 60 个 path / 84 个 operation 里零个 ASR） |

两家已验证互通：Breeze 生成的音频，`bl` 能正确识别。

### 已知限制

| 限制 | 说明 |
| --- | --- |
| 沙箱里 `subprocess` 不能创建进程 | Windows 沙箱下 Python 调 `bl` 会 WinError 5。SKILL.md 给了 shell 直调的替代方案 |
| `bl` 的 `--out` 在沙箱里报 EPERM | 它硬编码 mkdir `C:\Users\<user>\bailian-output`。TTS 用 `--stream` 走 stdout 绕开 |
| Cloudflare 拦截无 UA 请求 | 必须带 User-Agent，否则 403 / error code 1010（代码里已处理） |
| 单次请求 ≤ 1000 字符 | 获批账号最高 2000；超长直接拒绝，不截断 |
| 中文 > 500 字自动分段 | 仅非流式 + 显式 `language_code=zh`；最多 5 段，段间插 0.25 秒静音 |

### 开发与测试

零第三方依赖，Python 3.9+ 即可。跑离线测试：

```sh
python -m unittest discover -s tests -v
```

测试不会联网、不会扣费，也不会读取真实 key。改完代码至少跑一遍。

### 卸载

```sh
bash install.sh --uninstall      # macOS / Linux
powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall   # Windows
```

卸载只删除 `~/.dsh/skills/dsh-voice`。`~/.dsh/.env` 里的 key 不会动，需要你自己删；如果 key 放在技能目录的 `.env` 里，会随目录一起删除。

### 改名

fork 后要改名的话，这些地方必须同步：

`SKILL.md` → `name`；`install.sh` → `SKILL_NAME`；`install.ps1` → `$SkillName`；`README.md` / `README.en.md` → 标题与安装路径；`assets/breeze_tts.py` → `UA` 里的标识与默认输出文件名前缀。

</details>

## 许可证

MIT

**第三方服务条款**：

- Breeze Blue — <https://breezeblue.ai>
- 阿里云百炼 — <https://bailian.console.aliyun.com>

使用本技能即表示你同意遵守这两个平台的服务条款。MIT 许可证只覆盖本仓库的代码与文档，不覆盖第三方服务本身。

作者：[里卡多 / xh0915](https://xh0915.github.io)
