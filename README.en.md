# Whale Song · dsh-voice

**Turn text into speech, and recordings into text.**

**English** · [中文](README.md)

## A scene first

It is 11 p.m. You have just finished editing a chapter and want to hear it before bed. You tell DeepSeek Harness:

> Read every paragraph in chapter03.txt aloud, in a warmer voice.

Whale Song reports the character count and the estimated cost first. Once you confirm, it starts. When it finishes, `chapter03_audio/` contains `part_0001.mp3`, `part_0002.mp3`, and so on — one file per paragraph.

The next morning you drop in a phone recording and say "tell me what this says." It hands you the transcript.

No browser extension, no second website, no `pip install`. The repository is a handful of Python files written entirely against the standard library.

## What it can do

- **Read aloud** — from one sentence to a whole article. 522 Chinese voices, including eight regional accents (Beijing, Taiwan, Cantonese, Sichuan, and others).
- **Act** — direct the delivery in plain language: a whisper, excitement, sarcasm, restrained grief. Write `[叹气]` `[笑]` `[咳嗽]` in the text and the voice really sighs, laughs, or coughs.
- **Design a voice** — describe a voice in words, or clone one from a recording. You get a preview first and save it only when you like it. The free tier stores up to five voices.
- **Batch narration** — one paragraph per line in a text file, one file out per paragraph. Built for audiobooks and long reads.
- **Transcribe** — turn audio and recordings into text. This part goes through Alibaba Bailian, because Breeze only does speech synthesis and has no transcription endpoint.
- **Check the bill first** — `speak` and `batch` support `--dry-run`, which shows the parameters and cost without charging anything. Custom voices generate a paid preview first; you save only if you like it.

## What it looks like

Below is real terminal output. `--dry-run` only estimates; it does not generate audio or spend credits:

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

The CLI itself speaks Chinese. Batch mode also quotes the total first:

```text
$ python assets/breeze_tts.py batch 章节.txt --dry-run
[批量] 2 段，预计消耗 52 单元 ≈ 5.2 credits

[dry-run] 未扣费。各段预览：
    1. [  24单元] 夜深了，星星在窗外眨眼睛。
    2. [  28单元] 她把书合上，轻轻说了一句晚安。

确认无误后去掉 --dry-run 重跑。
```

## Install

You need three things:

1. **Python 3.9 or newer** (the installer checks this and tells you if it is missing)
2. **A Breeze API key** — create one at <https://breezeblue.ai/app/developer/api-keys>
3. **DeepSeek Harness** — it discovers the skill automatically

Clone the repository and run the installer:

```sh
git clone https://github.com/xh0915/dsh-voice
cd dsh-voice
bash install.sh
```

On Windows, use the built-in Windows PowerShell:

```powershell
git clone https://github.com/xh0915/dsh-voice
cd dsh-voice
powershell -ExecutionPolicy Bypass -File install.ps1
```

The installer copies the skill to `~/.dsh/skills/dsh-voice`. Harness picks it up automatically; if it does not appear, restart Harness once.

Whale Song is a **skill**, not a host plugin with a UI. There is no `dsh plugin add` step; putting it under `skills/` is the whole installation.

### Add your key

Never put a key in code, and never commit one. Copy `.env.example` to `.env`, fill it in, and keep it in either place:

- your current working directory (applies to that project only)
- the skill directory, `~/.dsh/skills/dsh-voice/.env` (applies everywhere once installed)
- `~/.dsh/.env` (applies everywhere; recommended)

```dotenv
BREEZE_API_KEY=brz_your_key
DASHSCOPE_API_KEY=sk-your_key    # transcription only; skip if `bl auth login` is set up
```

### Verify

```sh
python ~/.dsh/skills/dsh-voice/assets/breeze_tts.py balance
```

On Windows, write the path as `$HOME\.dsh\skills\dsh-voice\assets\breeze_tts.py`.

If it prints a balance, the key was read correctly. This costs nothing.

### Transcription needs one extra CLI

Speech synthesis does not need it. Only "audio to text" does:

```sh
npm install -g bailian-cli     # requires Node.js 22.12 or newer
bl auth login --console        # or: bl auth login --api-key sk-...
```

## How to use it

Once installed, just talk to Harness:

```text
Read this in a warm voice: welcome back, you worked hard today.
```

```text
Find me a Chinese voice that suits a bedtime story.
```

```text
Tell me what this recording says: C:\audio\meeting.mp3
```

You can also run the commands yourself:

```sh
SKILL=~/.dsh/skills/dsh-voice/assets

# Estimate first; no charge
python $SKILL/breeze_tts.py speak "Hello, world." --lang en --dry-run

# Then generate
python $SKILL/breeze_tts.py speak "Hello, world." --lang en -o hello.mp3

# Add a performance direction
python $SKILL/breeze_tts.py speak "I did not know he would come." \
  --instructions "Whisper, tense and restrained, as if afraid of being overheard." \
  --guidance 2.0 -o whisper.mp3

# Find a voice (no charge)
python $SKILL/breeze_tts.py voices --lang zh --search 温暖
```

Voice design, batch narration, and transcription are documented in `SKILL.md`, which the agent reads on its own.

## What it costs

**Billing is weighted by character: each Chinese, Japanese, or Korean character counts as 2 units, every other character as 1, and 10 units = 1 credit.**

| Item | Price |
| --- | --- |
| Top-up | $3 = 10,000 credits (minimum $5) |
| 100 Chinese characters | ≈ 20 credits ≈ **$0.006** |
| Free-tier concurrency | 2 generation slots |
| Free tier daily | 400 claimable credits, about 15 full test runs per day |

**Free operations**: `voices` / `models` / `balance` / `myvoices`, plus any `--dry-run`.
**Charged operations**: `speak` / `batch` / `design` / `clone`.

Measured examples: designing two candidates, saving one, synthesizing with it, and cloning a voice cost about **14.4 credits**; a three-paragraph batch of roughly 30 Chinese characters cost about **5.4 credits**, matching the estimate.

Prices follow Breeze's official pricing page. This repository never bills you.

## What it won't do

- **It won't charge you quietly.** `speak` and `batch` quote the cost before generating, and `--dry-run` only estimates. Custom-voice previews are charged, but only when you explicitly ask for them.
- **It won't bundle a key, and it won't send your key to us.** There is no server. The key is read locally and sent directly to the provider.
- **It won't do live calls or listen to a microphone.** It works on text and audio files, not phone calls or streams.
- **It won't translate for you.** Chinese and English use the default model; other languages require `breeze-tts-2-multilingual` explicitly, and a language mismatch fails loudly.
- **It won't retry blindly.** Only 429 (concurrency) and 503 (capacity) are retried with the server's backoff hint. After a network timeout it stops and tells you to check the balance first, so you don't pay twice.
- **It won't clone a voice without permission.** You must have the speaker's consent before cloning their voice.
- **It won't help you dodge the commercial restriction.** The free tier sets `commercial_use_allowed` to `false`; commercial use requires a paid plan.
- **It won't pretend Breeze can transcribe.** Breeze is synthesis only; transcription goes to Alibaba Bailian, and the README says so plainly.

## Privacy and keys

- **No real key exists in this repository.** `.env` is excluded by `.gitignore`.
- The key is read only from the environment or `.env`; it is never written into code or logs.
- Text goes to Breeze for synthesis; for custom voices, the description or reference audio also goes only to Breeze; audio goes to Alibaba Bailian for transcription. That is the only upload, and it is required to do the job.
- Generated audio is written only to the local path you specify.
- No telemetry, no analytics, no remote configuration.
- If a key leaks, rotate it immediately: `POST /v1/api-keys/{key_id}/rotate` (old keys stay valid for 30 days).

## Settings

| Variable | Required | Purpose |
| --- | --- | --- |
| `BREEZE_API_KEY` | For synthesis | Breeze Blue API key, starts with `brz_` |
| `DASHSCOPE_API_KEY` | For transcription | Alibaba Bailian key; not needed if `bl auth login` is configured |

`.env` lookup is **nearest first**: current working directory → skill directory (`~/.dsh/skills/dsh-voice/.env`) → `~/.dsh/.env`.

<details>
<summary><b>Technical details (for people changing the code)</b></summary>

### Layout

```text
SKILL.md                 # Skill definition: triggers, commands, billing, constraints
README.md                # Chinese README
README.en.md             # This file
LICENSE                  # MIT + third-party service boundary
CHANGELOG.md             # Version history
.env.example             # Config template (copy to .env)
install.sh               # Install / check / uninstall (Linux, macOS)
install.ps1              # Install / check / uninstall (Windows PowerShell)
assets/
  breeze_tts.py          # Synthesis, custom voices, batch, retries (stdlib only)
  breeze_stt.py          # Transcription wrapper around the bl CLI
reference/
  voices.md              # Chinese voice cheat sheet (307 neutral Mandarin voices)
tests/
  test_cli.py            # Offline tests: help, dry-run, errors, no secret leaks
```

`开发资料/` and `Breeze_Blue_文档全景.md` are local development archives. They are not part of the public repository and are not copied by the installer.

### Commands

| Command | What it does | Charged |
| --- | --- | --- |
| `speak` | Text → audio | Yes |
| `batch` | Text file → many audio files | Yes |
| `design` | Create a voice from a description | Yes |
| `clone` | Clone a voice from audio | Yes |
| `save` | Save a preview as a reusable voice | No (uses a slot) |
| `delete` | Delete a voice, freeing a slot | No |
| `voices` | Browse the public voice catalog | No |
| `myvoices` | List your saved voices | No |
| `balance` | Check the balance | No |
| `models` | List available models | No |

### Two providers

| Capability | Provider | Why |
| --- | --- | --- |
| Text to speech | [Breeze Blue](https://breezeblue.ai), model `breeze-tts-2` | Many Chinese voices, fine-grained accents, performance directions, audio tags |
| Speech to text | Alibaba Bailian `bl speech recognize` | Breeze has no transcription endpoint (60 paths / 84 operations checked; zero ASR) |

The two have been verified together: audio generated by Breeze transcribes correctly through `bl`.

### Known limits

| Limit | Detail |
| --- | --- |
| `subprocess` cannot spawn in the sandbox | On the Windows sandbox, Python calling `bl` raises WinError 5. SKILL.md documents the shell-direct alternative |
| `bl --out` hits EPERM in the sandbox | It hard-codes `mkdir C:\Users\<user>\bailian-output`. TTS bypasses this with `--stream` to stdout |
| Cloudflare blocks requests without a User-Agent | Without one you get 403 / error code 1010 (already handled) |
| 1,000 characters per request | Approved accounts allow up to 2,000; longer text is rejected, never truncated |
| Chinese text over 500 characters is split | Only for non-streaming with explicit `language_code=zh`; up to 5 segments, 0.25s silence between them |

### Development and tests

Zero third-party dependencies; Python 3.9+ is enough. Run the offline tests:

```sh
python -m unittest discover -s tests -v
```

The tests do not touch the network, spend credits, or read a real key. Run them after any change.

### Uninstall

```sh
bash install.sh --uninstall      # macOS / Linux
powershell -ExecutionPolicy Bypass -File install.ps1 -Uninstall   # Windows
```

This removes `~/.dsh/skills/dsh-voice` only. The key in `~/.dsh/.env` stays; delete it yourself if you want it gone. If you put `.env` inside the skill directory, it is removed with the directory.

### Renaming

If you fork and rename, keep these in sync:

`SKILL.md` → `name`; `install.sh` → `SKILL_NAME`; `install.ps1` → `$SkillName`; `README.md` / `README.en.md` → title and install paths; `assets/breeze_tts.py` → the identifier in `UA` and the default output filename prefix.

</details>

## License

MIT

**Third-party terms**:

- Breeze Blue — <https://breezeblue.ai>
- Alibaba Cloud Bailian — <https://bailian.console.aliyun.com>

Using this skill means you agree to both providers' terms. The MIT license covers this repository's code and docs only, not the third-party services.

Author: [里卡多 / xh0915](https://xh0915.github.io)
