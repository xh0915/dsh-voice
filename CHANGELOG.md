# Changelog

本项目的所有重要变更都记录在此文件。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1./)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [2.0.0] - 2026-10-26

### 变更（不兼容）

- **技能标识改名**：`breeze-tts` → `dsh-voice`，中文名「鲸歌」，与作者已发布的
  `dsh-chart` / `dsh-voyage-log` / `dsh-lighthouse` 命名保持一致。
  安装路径随之变为 `~/.dsh/skills/dsh-voice`；旧目录需要手动删除或重装
- 默认输出文件名前缀 `breeze_` → `whale_`；请求 UA 标识同步更新
- README 按公开仓库风格重写：场景优先、真实终端输出、成本、隐私、限制，
  技术细节收进 `<details>`；新增英文版 `README.en.md`
- 开发归档 `开发资料/` 与 `Breeze_Blue_文档全景.md` 不再进入公开仓库
  （`.gitignore` 已排除，本地文件保留）

### 新增

- `tests/test_cli.py`：离线测试，覆盖帮助、`--dry-run`、批量预览、错误处理
  和密钥泄露扫描；不联网、不扣费、不读真实 key

### 修复

- **`speak --dry-run` 不再联网**：此前会先请求音色目录挑默认音色，断网时
  连成本都算不了。现在未指定音色时显示「(自动挑选)」，预检完全离线

### 文档

- 安装器同步 `README.en.md`
- `.env.example`、`LICENSE`、`SKILL.md` 中的项目名与路径全部更新

## [1.1.1] - 2026-10-26

### 修复

- **Windows 管道输出乱码**：agent 捕获 stdout/stderr 时中文变乱码（实测管道下
  Python 编码为 GBK/cp936）。两脚本启动时统一 `reconfigure(encoding="utf-8")`
- **breeze_stt.py 不读 `.env`**：按 README 把 key 写在 `.env` 后 STT 仍报缺 key。
  现与 TTS 脚本一致：先环境变量、再从 `.env` 读取（就近优先），并传给 `bl` 子进程；
  两处都没有时降级为警告（`bl auth login` 登录用户不受影响）
- **`--format wav/flac/pcm` 时输出文件仍叫 `.mp3`**：`speak` / `batch` 从
  `--format` 推导扩展名
- **网络超时/断连抛裸 traceback**：现捕获网络错误并提示"先跑 balance 查是否已扣费，
  不要盲目重发"（此前仅捕获 HTTPError；克隆上传同样修复）
- **`.env` 优先级**：改为就近优先（工作区 > 技能目录 > `~/.dsh`），此前后者会覆盖前者
- **`delete` 报错**：不再把鉴权/网络失败误报为"音色不存在"

### 文档

- README：修正 `bl` CLI 安装命令（原 `npm install -g @anthropic-ai/bl` 在 npm 上
  不存在，正确为 `npm install -g bailian-cli`，需 Node.js ≥ 22.12.0）
- README：删除重复的"命令总览"表
- SKILL.md：`save` 的 `--lang` 说明与实现对齐（默认 zh，非必填）
- 新增 `.env.example` 配置示例

## [1.1.0] - 2026-10-26

### 新增

- **定制音色**（核心能力）
  - `design` — 文字描述造声，支持 `--count` 多候选、`--guidance` 贴合强度
  - `clone` — 上传音频克隆，支持 `--denoise` 去噪，中文样本自动限定 ASR
  - `save` — 把预览保存为可复用音色，支持 `--tone` 色调标注
  - `myvoices` — 列出已保存音色（免费档上限 5 个）
  - `delete` — 删除音色释放名额，**带安全闸门**（默认拒绝删公共目录音色）

- **批量合成**
  - `batch` — 整个文本文件一次生成多段音频，适合有声书/长文配音
  - 按行切分（空行自动跳过），支持 `--separator` 自定义分隔
  - 单段失败不影响其余段，最后报成功/失败统计

- **健壮性**
  - `request()` 自动重试：429（并发满）/503（容量耗尽）按 `Retry-After` 退避，
    最多 3 次；不可重试错误（401/402/404/422）立即退出
  - `--dry-run` 成本预检：`speak` / `batch` 支持，只算钱不扣费

- **工程化**
  - `install.sh` / `install.ps1` 一键安装（含 `-Check` 环境检查、`-Uninstall` 卸载）
  - `LICENSE`（MIT）—— 此前 README 声称 MIT 但文件缺失
  - `CHANGELOG.md`、`.gitignore`

### 变更

- 目录名 `breeze-tts-skill` → `breeze-tts`，与 SKILL.md 的 `name` 字段一致
- README 补齐命令总览表、健壮性说明、克隆素材要求
- SKILL.md 补齐定制音色、批量合成、成本预检、健壮性说明
- `myvoices` 的删除提示从裸 API 调用改为 CLI 命令

## [1.0.0] - 2026-10-26

首个版本。

### 新增

- **TTS 语音合成**（走 Breeze Blue `breeze-tts-2`）
  - `speak` — 文本合成语音，支持 `--instructions` 表演指令、`--guidance` 强度、
    `--speed` 语速、`--format` 输出格式
  - `voices` — 查公共音色目录，支持 `--search` / `--accent` / 语言筛选
  - `balance` / `models` — 查余额与模型（不扣费）

- **STT 语音识别**（走阿里百炼 `bl speech recognize`）
  - `breeze_stt.py` — 封装 `bl` CLI，处理已知的沙箱限制
  - 说明：Breeze 平台**只有 TTS 无 STT**（实测 60 path / 84 op 零个 ASR 端点）

- **零第三方依赖**
  - 纯 Python 标准库实现，clone 即用，无需 `pip install`
  - 处理了 Cloudflare 拦截无 User-Agent 请求的问题（403 / error code 1010）

- **文档**
  - `SKILL.md` — 技能定义，含触发条件、调用指令、关键约束
  - `README.md` — 安装说明、计费规则、合规声明、已知限制
  - `reference/voices.md` — 307 个中性普通话音色速查表

---

## 版本对应的实测数据

以下数字来自真实 API 调用，可作为成本参考：

| 场景 | 消耗 |
| --- | --- |
| design 2 候选 + save + 自建音色合成 + clone | ≈ 14.4 credits |
| batch 3 段（约 30 汉字） | ≈ 5.4 credits（与预估一致） |
| TTFA 实测（Realtime WebSocket） | 平均 525ms，合成快于实时 1.9 倍 |

计费规则：**CJK 字符每个 2 计费单元，10 单元 = 1 credit**。
