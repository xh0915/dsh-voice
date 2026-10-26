#!/usr/bin/env python3
"""
breeze_stt.py — 语音转文字（STT）封装
======================================

Breeze Blue 只有 TTS（实测确认：60 path / 84 op，零个转写端点），
所以 STT 这一头用阿里百炼的 `bl` CLI（FunAudio-ASR / Qwen-ASR Flash）。

本脚本封装 `bl speech recognize`，处理它已知的坑：

  1. `bl` 无论 --out 传什么，都会先硬编码 mkdir
     `C:\\Users\\<user>\\bailian-output\\speech`
     → 在受限沙箱里这会 EPERM 失败。
     → STT 不落盘、直接读 stdout，天然绕开。

  2. `--file` 不是合法参数，正确的是 `--url`（同时接受本地路径和 http URL）。

用法:
  python breeze_stt.py 音频.mp3                    # 识别本地文件
  python breeze_stt.py 音频.mp3 --language zh      # 加语言提示提升准确率
  python breeze_stt.py a.mp3 b.mp3 c.wav           # 一次识别多个
  python breeze_stt.py 音频.mp3 --json             # 输出 JSON（含时间戳）

环境:
  DASHSCOPE_API_KEY   可选；优先环境变量，其次从 .env 读取。
                      已用 bl auth login 登录过可省略。

前置:
  bl CLI 已安装并在 PATH（默认 bl speech --help 可执行）
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Windows 管道捕获（agent 调用）时 stdout/stderr 默认 locale 编码（如 GBK），中文会乱码
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass


def check_bl() -> str:
    """确认 bl CLI 存在，返回其路径。"""
    p = shutil.which("bl")
    if not p:
        sys.exit(
            "[错误] 找不到 bl CLI（阿里百炼命令行）。\n"
            "  安装: https://help.aliyun.com/zh/model-studio/\n"
            "  或确认 bl 在 PATH 中：  bl --version"
        )
    return p


def load_env_file() -> dict:
    """极简 .env 解析（与 breeze_tts.py 一致）。就近优先：工作区 > 技能目录 > ~/.dsh。"""
    out = {}
    for cand in (Path(".env"), Path(__file__).resolve().parent.parent / ".env",
                 Path.home() / ".dsh" / ".env"):
        if not cand.is_file():
            continue
        try:
            for line in cand.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except OSError:
            continue
    return out


def check_key():
    if os.environ.get("DASHSCOPE_API_KEY"):
        return
    k = load_env_file().get("DASHSCOPE_API_KEY", "").strip()
    if k:
        os.environ["DASHSCOPE_API_KEY"] = k   # bl 作为子进程需要继承
        return
    print(
        "[警告] 未找到 DASHSCOPE_API_KEY（环境变量与 .env 都没有）。\n"
        "  若已用 bl auth login 登录过可忽略；否则 export DASHSCOPE_API_KEY=sk-...",
        file=sys.stderr,
    )


def recognize(bl: str, files: list[str], *, model: str, language: str | None,
              json_out: bool, timeout: int) -> None:
    """
    调 bl speech recognize。

    关键：不传 --out，让它把转写结果直接打到 stdout。
    这样既避免了 bailian-output 的 mkdir 权限问题，也少一次文件读写。
    """
    for f in files:
        p = Path(f)
        if not p.is_file():
            print(f"[跳过] 文件不存在: {f}", file=sys.stderr)
            continue

        cmd = [bl, "speech", "recognize", "--url", str(p.resolve()),
               "--model", model, "--timeout", str(timeout)]
        if language:
            cmd += ["--language", language]
        if json_out:
            cmd += ["--output", "json"]

        print(f"[识别] {p.name}  ({p.stat().st_size} bytes, model={model})",
              file=sys.stderr)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding="utf-8", errors="replace")
        except OSError as e:
            sys.exit(f"[错误] 无法执行 bl: {e}")

        # bl 把进度/元信息打到 stderr，把转写结果打到 stdout
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "").strip()
            print(f"[失败] {p.name}\n{err}", file=sys.stderr)
            # 常见错误的定向提示
            low = err.lower()
            if "eperm" in low or "permission denied" in low:
                print("  提示: 这是沙箱目录权限问题。本脚本不落盘本应避开；"
                      "若仍出现，说明 bl 内部仍在建默认目录，"
                      "请在非沙箱终端运行。", file=sys.stderr)
            continue

        out = (r.stdout or "").strip()
        if out:
            print(f"\n=== {p.name} ===")
            print(out)
        else:
            print(f"[空结果] {p.name}（可能无有效语音）", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="breeze_stt.py",
        description="语音转文字 — 封装阿里百炼 bl speech recognize",
    )
    ap.add_argument("files", nargs="+", help="音频文件路径（mp3/wav/m4a 等）")
    ap.add_argument("--model", default="qwen3-asr-flash",
                    help="ASR 模型，默认 qwen3-asr-flash（同步）；"
                         "长音频可用 fun-asr / paraformer-*")
    ap.add_argument("--language", "-l", default="zh",
                    help="语言提示，默认 zh；传空字符串禁用")
    ap.add_argument("--json", action="store_true", help="输出 JSON 格式")
    ap.add_argument("--timeout", type=int, default=120, help="超时秒数")
    a = ap.parse_args(argv)

    check_key()
    bl = check_bl()
    recognize(bl, a.files, model=a.model,
              language=a.language or None,
              json_out=a.json, timeout=a.timeout)


if __name__ == "__main__":
    main()
