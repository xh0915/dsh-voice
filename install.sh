#!/usr/bin/env bash
# ============================================================
# 鲸歌 · dsh-voice 一键安装（Linux / macOS）
# ============================================================
# 用法:
#   bash install.sh              # 安装
#   bash install.sh --check      # 只检查环境，不安装
#   bash install.sh --uninstall  # 卸载
#
# 做了什么:
#   1. 检查 Python 3.9+（必需）
#   2. 检查 bl CLI（只有 STT 需要，缺失不阻断安装）
#   3. 把本目录复制到 ~/.dsh/skills/dsh-voice
#   4. 检查 BREEZE_API_KEY 是否已配置
#
# 零第三方依赖：不需要 pip install 任何东西。
# ============================================================

set -euo pipefail

SKILL_NAME="dsh-voice"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DST_DIR="$HOME/.dsh/skills/$SKILL_NAME"

ok()   { printf '  \033[32m\342\234\223\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m\342\230\240\033[0m %s\n' "$1"; }
err()  { printf '  \033[31m\342\234\227\033[0m %s\n' "$1"; }

echo "=========================================="
echo " 鲸歌 · dsh-voice 安装器"
echo "=========================================="
echo "源目录: $SRC_DIR"
echo "目标:   $DST_DIR"
echo

# ---------------- 卸载 ----------------
if [[ "${1:-}" == "--uninstall" ]]; then
    if [[ -d "$DST_DIR" ]]; then
        rm -rf "$DST_DIR"
        ok "已卸载: $DST_DIR"
    else
        warn "未安装过，无需卸载"
    fi
    echo
    echo "注意: ~/.dsh/.env 里的 BREEZE_API_KEY 不会自动删除。"
    echo "      如果 key 放在技能目录的 .env 里，会随目录一起删除。"
    exit 0
fi

# ---------------- 检查 Python ----------------
echo "[1/4] 检查 Python"
# Windows 的 Git Bash 里 python3 可能只是 Microsoft Store 占位符，必须实际跑一下
PY=""
for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1 && "$cand" -c 'import sys' >/dev/null 2>&1; then
        PY="$cand"
        break
    fi
done
if [[ -z "$PY" ]]; then
    err "找不到可用的 Python。请安装 Python 3.9+"
    exit 1
fi
PY_VER=$("$PY" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_OK=$("$PY" -c 'import sys; print(1 if sys.version_info >= (3,9) else 0)')
if [[ "$PY_OK" == "1" ]]; then
    ok "Python $PY_VER（$PY）"
else
    err "Python $PY_VER 过旧，需要 3.9+"
    exit 1
fi

# ---------------- 检查 bl CLI（STT 用，可选）----------------
echo
echo "[2/4] 检查 bl CLI（只有语音识别 STT 需要）"
if command -v bl >/dev/null 2>&1; then
    ok "bl 已安装"
else
    warn "未找到 bl —— 语音合成功能不受影响，只有语音识别用不了"
    echo "     安装方法见 https://help.aliyun.com/zh/model-studio/"
fi

key_source() {
    if [[ -n "${BREEZE_API_KEY:-}" ]]; then
        echo "环境变量"
        return 0
    fi
    for f in "$HOME/.dsh/.env" "$DST_DIR/.env" "$SRC_DIR/.env" "$SRC_DIR/../.env"; do
        if [[ -f "$f" ]] && grep -qs '^BREEZE_API_KEY=' "$f"; then
            echo "$f"
            return 0
        fi
    done
    return 1
}

# ---------------- 只检查模式 ----------------
if [[ "${1:-}" == "--check" ]]; then
    echo
    echo "[3/4] 检查 API key"
    if KEY_SRC=$(key_source); then
        ok "BREEZE_API_KEY 已配置（$KEY_SRC）"
    else
        warn "BREEZE_API_KEY 未配置"
        echo "     获取: https://breezeblue.ai/app/developer/api-keys"
    fi
    echo
    echo "[4/4] 跳过安装（--check 模式）"
    exit 0
fi

# ---------------- 复制文件 ----------------
echo
echo "[3/4] 安装到 $DST_DIR"
mkdir -p "$DST_DIR"
# 只复制需要的文件，排除开发产物
for item in SKILL.md README.md README.en.md LICENSE CHANGELOG.md .env.example assets reference; do
    if [[ -e "$SRC_DIR/$item" ]]; then
        rm -rf "$DST_DIR/$item"
        cp -R "$SRC_DIR/$item" "$DST_DIR/$item"
        ok "复制 $item"
    fi
done
# 清理字节码缓存
find "$DST_DIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find "$DST_DIR" -name '*.pyc' -delete 2>/dev/null || true

# ---------------- 检查 key ----------------
echo
echo "[4/4] 检查 API key"
if KEY_SRC=$(key_source); then
    if [[ "$KEY_SRC" == "环境变量" || "$KEY_SRC" == "$HOME/.dsh/.env" || "$KEY_SRC" == "$DST_DIR/.env" ]]; then
        ok "BREEZE_API_KEY 已配置（$KEY_SRC）"
    else
        warn "已在 $KEY_SRC 找到 BREEZE_API_KEY（仅从该目录运行时生效）"
        echo "     如果 Harness 打开的就是这个工作区，可以直接用；否则请移到 ~/.dsh/.env"
    fi
else
    warn "BREEZE_API_KEY 尚未配置（合成时会报错）"
    echo "     获取: https://breezeblue.ai/app/developer/api-keys"
    echo "     配置: 在 ~/.dsh/.env 加一行  BREEZE_API_KEY=brz_你的key"
fi

echo
echo "=========================================="
echo " 安装完成"
echo "=========================================="
echo
echo "在 DeepSeek Harness 里直接说："
echo "  「把这段话读出来：你好世界」"
echo "  「造一个温柔的女声讲睡前故事」"
echo "  「把这章小说生成有声书」"
echo
echo "命令行直接用："
echo "  $PY $DST_DIR/assets/breeze_tts.py speak \"你好\" -o hi.mp3"
echo
echo "验证安装："
echo "  $PY $DST_DIR/assets/breeze_tts.py balance"
