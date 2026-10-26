#!/usr/bin/env python3
"""
breeze_tts.py — 鲸歌 · dsh-voice 的语音合成实现（Breeze Blue 后端）
=====================================================

零第三方依赖：只用 Python 标准库（urllib）。Python 3.9+ 即可运行。

为什么零依赖很重要：
  作为 Harness skill 分发时，别人 clone 下来就能用，
  不需要 pip install 任何东西（在受限沙箱里 pip 往往装不进去）。

用法:
  python breeze_tts.py speak "你好世界"                          # 合成到默认文件
  python breeze_tts.py speak "你好" --voice voc_xxx -o hi.mp3
  python breeze_tts.py speak "别告诉他" --instructions "压低声音耳语，像怕被听见"
  python breeze_tts.py voices --lang zh --search 温暖            # 找音色
  python breeze_tts.py voices --lang zh --accent null           # 只要中性普通话
  python breeze_tts.py balance                                  # 查余额（不扣费）
  python breeze_tts.py models                                   # 查模型（不扣费）

环境变量:
  BREEZE_API_KEY   必需。从环境或 .env 读取。

关于 Cloudflare:
  必须带 User-Agent，否则返回 403 / error code 1010（Cloudflare bot 拦截）。
  这是实测踩到的坑，不是猜测。
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

# Windows 管道捕获（agent 调用）时 stdout/stderr 默认 locale 编码（如 GBK），中文会乱码
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        pass

BASE = "https://api.breeze.blue/v1"

# Cloudflare 拦截无 UA 的请求（403 / error code 1010），实测确认
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 dsh-voice/2.0"

DEFAULT_MODEL = "breeze-tts-2"          # 中英优化版
MULTI_MODEL = "breeze-tts-2-multilingual"  # 51 语言


# ----------------------------------------------------------------- 凭证
def load_env_file() -> dict:
    """极简 .env 解析，避免依赖 python-dotenv。就近优先：工作区 > 技能目录 > ~/.dsh。"""
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


def api_key() -> str:
    k = os.environ.get("BREEZE_API_KEY", "").strip()
    if not k:
        k = load_env_file().get("BREEZE_API_KEY", "").strip()
    if not k:
        sys.exit(
            "[错误] 没有 BREEZE_API_KEY。\n"
            "  1) 设置环境变量  export BREEZE_API_KEY=brz_...\n"
            "  2) 或在 .env 里加一行  BREEZE_API_KEY=brz_...\n"
            "     可放在：当前工作区 / 技能目录 / ~/.dsh/.env\n"
            "  获取: https://breezeblue.ai/app/developer/api-keys"
        )
    return k


# ----------------------------------------------------------------- HTTP
def _parse_retry_after(headers) -> float:
    """
    解析 Retry-After 头。文档：非负整数秒，上限 3600。
    解析失败返回 1.0 作为保守退避。
    """
    v = headers.get("Retry-After") if headers else None
    if not v:
        return 1.0
    try:
        return min(max(float(v), 0.0), 3600.0)
    except (TypeError, ValueError):
        return 1.0


def request(method: str, path: str, *, body=None, raw=False, timeout=120,
            retries: int = 3):
    """
    发一次请求。返回 bytes（raw=True）或 dict。
    统一处理 Cloudflare / 鉴权 / 业务错误码。

    重试策略（文档硬性要求）：
      429 GENERATION_CONCURRENCY_EXCEEDED / RATE_LIMITED → 按 Retry-After 退避重试
      503 GENERATION_CAPACITY_EXCEEDED                  → 稍等重试（不立即）
      其他错误                                          → 不重试，直接报错
    """
    url = f"{BASE}{path}"
    data = None
    headers = {"xi-api-key": api_key(), "User-Agent": UA}

    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    # 文档明确"可重试"的错误码
    retryable = {"GENERATION_CONCURRENCY_EXCEEDED", "RATE_LIMITED",
                 "GENERATION_CAPACITY_EXCEEDED", "GENERATION_TIMEOUT",
                 "GENERATION_INTERRUPTED", "UPSTREAM_TIMEOUT",
                 "UPSTREAM_GENERATION_ERROR", "INTERNAL_ERROR"}

    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                payload = r.read()
                if raw:
                    return payload
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as e:
            payload = e.read()
            try:
                err = json.loads(payload)
                code = err.get("code", "?")
                detail = err.get("detail", payload[:200].decode("utf-8", "replace"))
            except Exception:
                code, detail = "?", payload[:200].decode("utf-8", "replace")

            # 不可重试的错误：立即退出（如 401/402/404/422）
            if code not in retryable or attempt >= retries:
                hint = ERROR_HINTS.get(code, "")
                msg = f"[HTTP {e.code}] {code}: {detail}"
                if hint:
                    msg += f"\n  提示: {hint}"
                if e.code in (429, 503):
                    msg += f"\n  Retry-After: {_parse_retry_after(e.headers):.0f} 秒"
                sys.exit(msg)

            # 可重试：按文档要求退避（429/503 优先用 Retry-After）
            wait = _parse_retry_after(e.headers)
            if code == "GENERATION_CAPACITY_EXCEEDED" and not e.headers.get("Retry-After"):
                wait = 2.0 * (attempt + 1)   # 容量耗尽：指数退避
            elif code not in ("GENERATION_CONCURRENCY_EXCEEDED", "RATE_LIMITED"):
                wait = min(8.0, 0.5 * (2 ** attempt))   # 瞬时 5xx：指数退避

            print(f"[重试 {attempt+1}/{retries}] {code}，等待 {wait:.1f}s…",
                  file=sys.stderr)
            time.sleep(wait)

        except OSError as e:
            # 超时/断连无法确定请求是否已达服务器：不自动重试，先提示查余额
            sys.exit(
                f"[网络错误] {e}\n"
                "  传输可能已到达服务器，先跑 balance 确认是否已扣费，再决定是否重跑。"
            )


# 错误码 → 人话提示（来自官方文档的重试语义）
ERROR_HINTS = {
    "AUTH_REQUIRED": "key 缺失/格式错/已删除/已禁用。检查 BREEZE_API_KEY。",
    "BILLING_INSUFFICIENT_CREDITS": "余额不足。去 https://breezeblue.ai 充值，勿重试。",
    "API_KEY_CREDIT_LIMIT_EXCEEDED": "key 预算耗尽。提高或 reset 预算后才重试。",
    "GENERATION_CONCURRENCY_EXCEEDED": "并发槽已满。按 Retry-After 退避后重试。",
    "GENERATION_CAPACITY_EXCEEDED": "容量暂时耗尽。稍后再试（勿立即重试）。",
    "RESOURCE_NOT_FOUND": "voice_id 不存在或不可访问。用 voices 命令重新查。",
    "VALIDATION_ERROR": "参数不合法。检查 instructions 长度/语言/output_format。",
    "BAD_REQUEST": "请求不合法。HTTP 流式只接受裸 pcm/mp3/wav，不带采样率。",
}


# ----------------------------------------------------------------- 命令
def cmd_balance(_a):
    d = request("GET", "/balance")
    print(f"余额: {d.get('balance')} credits")
    for t in (d.get("topups") or [])[:3]:
        print(f"  +{t.get('amount')}  {t.get('description')}  {t.get('created_at')}")


def cmd_models(_a):
    models = request("GET", "/models")
    if isinstance(models, dict):
        models = models.get("models", [])
    for m in models:
        langs = [x.get("language_id") for x in m.get("languages", [])]
        has_zh = "是" if "zh" in langs else "否"
        print(f"{m.get('model_id')}  支持中文={has_zh}  语言数={len(langs)}")
        print(f"  {m.get('description')}")


def cmd_voices(a):
    params = [f"language_code={a.lang}", f"page_size={a.limit}"]
    if a.search:
        params.append(f"search={urllib.parse.quote(a.search)}")
    # accent_mode=unmarked 匹配 accent=null，即中性标准口音
    if a.accent == "null":
        params.append("accent_mode=unmarked")
    elif a.accent:
        params.append(f"accent={a.accent}")

    d = request("GET", "/voices?" + "&".join(params))
    voices = d.get("voices", []) if isinstance(d, dict) else d
    if not voices:
        print("没有匹配的音色。试试 --lang zh 或去掉 --search。")
        return

    total = d.get("total", len(voices)) if isinstance(d, dict) else len(voices)
    print(f"匹配 {len(voices)} 个（该语言共 {total} 个）\n")
    print(f"{'voice_id':<18}{'名称':<12}{'性别':<8}{'年龄':<14}{'口音':<22}色调")
    print("-" * 96)
    for v in voices:
        print(f"{v['voice_id']:<18}{v.get('name', ''):<12}"
              f"{str(v.get('gender')):<8}{str(v.get('age')):<14}"
              f"{str(v.get('accent')):<22}{','.join(v.get('tone') or [])}")
    print("\n用法: python breeze_tts.py speak \"文本\" --voice <voice_id>")


def _pick_default_voice(lang="zh") -> str:
    """
    没指定 --voice 时自动挑一个：中性口音、成年、tone 含 friendly/warm/gentle。
    目录读取不计费，可以放心调。
    """
    d = request("GET", f"/voices?language_code={lang}&accent_mode=unmarked&page_size=12")
    voices = d.get("voices", []) if isinstance(d, dict) else []
    if not voices:
        sys.exit(f"[错误] 没找到 {lang} 音色，请用 voices 命令手动挑选。")
    preferred = {"friendly", "warm", "gentle", "calm", "articulate"}
    pick = next(
        (v for v in voices
         if v.get("age") in ("young", "middle_aged")
         and preferred & set(v.get("tone") or [])),
        voices[0],
    )
    print(f"[自动选音色] {pick['voice_id']}  {pick.get('name')}  "
          f"tone={pick.get('tone')}", file=sys.stderr)
    return pick["voice_id"]


def cmd_speak(a):
    """核心命令：文本 → 音频文件。"""
    # CJK 字符每个算 2 个计费单元，10 单元 = 1 credit
    cjk = sum(1 for ch in a.text if "一" <= ch <= "鿿"
              or "぀" <= ch <= "ヿ" or "가" <= ch <= "힯")
    units = cjk * 2 + (len(a.text) - cjk)
    print(f"[计费预估] {len(a.text)} 字符 = {units} 单元 ≈ {units/10:.1f} credits",
          file=sys.stderr)

    body = {"text": a.text, "model_id": a.model, "language_code": a.lang}
    if a.instructions:
        # instructions ≤1000 字符，且必须与 text 同语言（不会自动翻译）
        if len(a.instructions) > 1000:
            sys.exit("[错误] instructions 超过 1000 字符")
        body["instructions"] = a.instructions
    if a.guidance != 1.0:
        if not 1.0 <= a.guidance <= 10.0:
            sys.exit("[错误] guidance_scale 必须在 1.0 - 10.0 之间")
        body["voice_settings"] = {"guidance_scale": a.guidance}
    if a.speed != 1.0:
        body.setdefault("voice_settings", {})["speed"] = a.speed

    # 成本预检：只算不扣费，也不联网查默认音色
    if a.dry_run:
        print(f"\n[dry-run] 未扣费。合成参数：")
        print(f"  音色   {a.voice or '(自动挑选)'}")
        print(f"  模型   {a.model}   语言 {a.lang}   格式 {a.format}")
        print(f"  语速   {a.speed}   强度 {a.guidance}")
        if a.instructions:
            print(f"  指令   {a.instructions[:60]}")
        print(f"  文本   {a.text[:80]}")
        print(f"\n确认无误后去掉 --dry-run 重跑。")
        return

    voice = a.voice or _pick_default_voice(a.lang)
    t0 = time.perf_counter()
    audio = request(
        "POST", f"/text-to-speech/{voice}?output_format={a.format}",
        body=body, raw=True,
    )
    dt = time.perf_counter() - t0

    ext = a.format.split("_", 1)[0]          # mp3_44100_128 → mp3
    out = Path(a.out or f"whale_{int(time.time())}.{ext}")
    out.write_bytes(audio)
    print(f"✓ {out}  ({len(audio)} bytes, {dt:.2f}s)")
    print(f"  音色 {voice}  模型 {a.model}  格式 {a.format}")


# ----------------------------------------------------------------- 定制音色
def _multipart(fields: dict, files: list[tuple]) -> tuple[bytes, str]:
    """
    手工构造 multipart/form-data（克隆上传需要）。
    fields: [(name, value_str), ...]
    files:  [(name, filename, content_bytes, content_type), ...]
    返回 (body_bytes, content_type_header)
    """
    boundary = f"----breeze{uuid.uuid4().hex}"
    crlf = b"\r\n"
    parts = []

    for name, value in fields:
        parts.append(f"--{boundary}".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        parts.append(b"")
        parts.append(value.encode("utf-8"))

    for name, filename, content, ctype in files:
        parts.append(f"--{boundary}".encode())
        parts.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"'
            .encode("utf-8")
        )
        parts.append(f"Content-Type: {ctype}".encode())
        parts.append(b"")
        parts.append(content)

    parts.append(f"--{boundary}--".encode())
    parts.append(b"")
    body = crlf.join(parts)
    return body, f"multipart/form-data; boundary={boundary}"


def _request_multipart(path: str, fields: list, files: list, timeout=300):
    """POST multipart 请求（克隆专用）。返回 dict。"""
    body, ctype = _multipart(fields, files)
    req = urllib.request.Request(
        f"{BASE}{path}", data=body, method="POST",
        headers={"xi-api-key": api_key(), "User-Agent": UA, "Content-Type": ctype},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        payload = e.read()
        try:
            err = json.loads(payload)
            code, detail = err.get("code", "?"), err.get("detail", "")
        except Exception:
            code, detail = "?", payload[:200].decode("utf-8", "replace")
        sys.exit(f"[HTTP {e.code}] {code}: {detail}")
    except OSError as e:
        # 上传中断时计费状态未知：不自动重试
        sys.exit(
            f"[网络错误] {e}\n"
            "  上传可能已到达服务器，先跑 balance 确认是否已扣费，再决定是否重传。"
        )


def _wait_preview(get_status, job_id: str, deadline=300):
    """
    轮询预览任务到终态。文档要求 ≥2 秒一次。
    get_status(job_id) -> dict
    """
    t0 = time.time()
    last = None
    while time.time() - t0 < deadline:
        d = get_status(job_id)
        st = d.get("status")
        if st != last:
            print(f"  状态: {st}", file=sys.stderr)
            last = st
        if st == "ready":
            return d
        if st in ("failed", "cancelled"):
            err = d.get("error") or {}
            sys.exit(f"[失败] {st}: {err.get('code')} {err.get('detail')}")
        time.sleep(2)
    sys.exit("[超时] 预览任务未在期限内完成，可稍后用 job_id 重查")


def cmd_design(a):
    """
    文字描述造声。两步：生成预览 → 保存为音色。
    计费：预览脚本按生成请求计一次（CJK 每字 2 单元）。
    """
    print(f"[计费] 造声预览按脚本计费一次，约 {len(a.text or '')} 字符", file=sys.stderr)

    body = {"voice_description": a.description}
    if a.text:
        body["text"] = a.text            # 3-500 字符，可选
    if a.guidance is not None:
        body["guidance_scale"] = a.guidance   # 1.0-10.0
    if a.count:
        body["preview_count"] = a.count      # 多候选

    d = request("POST", "/voice-previews/design", body=body)
    previews = d.get("previews", [])
    if not previews:
        sys.exit(f"[失败] 没有生成预览: {json.dumps(d, ensure_ascii=False)[:300]}")

    print(f"\n✓ 生成 {len(previews)} 个预览：")
    for p in previews:
        gid = p.get("generated_voice_id")
        print(f"  {gid}")
        if a.out:
            audio = request("GET", f"/voice-previews/{gid}/stream", raw=True)
            fp = Path(f"{a.out}_{gid}.mp3")
            fp.write_bytes(audio)
            print(f"    → {fp}  ({len(audio)} bytes)")

    print("\n试听满意后保存：")
    print(f"  python {Path(sys.argv[0]).name} save {previews[0]['generated_voice_id']} "
          f"--name \"我的音色\" --lang {a.lang}")


def cmd_clone(a):
    """
    上传音频克隆声音。
    要求：恰好 1 个样本、MP3/WAV、≥3 秒、≤5MB、单一说话人无背景音。
    计费：预览脚本一次 + 参考音频上传分析 1 credit。
    """
    p = Path(a.file)
    if not p.is_file():
        sys.exit(f"[错误] 文件不存在: {a.file}")
    size = p.stat().st_size
    if size > 5 * 1024 * 1024:
        sys.exit(f"[错误] 文件 {size/1024/1024:.2f}MB 超过 5MB 上限")

    ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
    if p.suffix.lower() not in (".mp3", ".wav"):
        print(f"[警告] 建议用 MP3/WAV，当前是 {p.suffix}", file=sys.stderr)

    print(f"[上传] {p.name}  ({size/1024:.1f}KB)", file=sys.stderr)
    print("[提示] 想克隆的内容要放在音频前 60 秒内（只分析前 60 秒，保留 ≤30 秒）",
          file=sys.stderr)

    fields = []
    if a.name:
        fields.append(("name", a.name))
    if a.denoise:
        fields.append(("remove_background_noise", "true"))
    if a.lang == "zh":
        # 中文样本用 Qwen ASR 限定，避免语言误判
        fields.append(("reference_language_code", "zh"))

    d = _request_multipart(
        "/voice-previews/clone",
        fields,
        [("files", p.name, p.read_bytes(), ctype)],
    )
    gid = d.get("generated_voice_id")
    if not gid:
        sys.exit(f"[失败] {json.dumps(d, ensure_ascii=False)[:300]}")

    print(f"\n✓ 克隆预览已生成: {gid}")
    print(f"  识别语言: {d.get('detected_language', '?')}")
    if a.out:
        audio = request("GET", f"/voice-previews/{gid}/stream", raw=True)
        Path(a.out).write_bytes(audio)
        print(f"  预览音频 → {a.out}  ({len(audio)} bytes)")

    print("\n试听满意后保存：")
    print(f"  python {Path(sys.argv[0]).name} save {gid} --name \"{a.name or '我的克隆'}\" "
          f"--lang {a.lang}")


def cmd_save(a):
    """把预览保存为可复用音色。language_code 必填。消耗一个 voice slot。"""
    body = {"voice_name": a.name, "language_code": a.lang}
    if a.description:
        body["voice_description"] = a.description
    if a.tone:
        # 最多 3 个
        tones = [t.strip() for t in a.tone.split(",")][:3]
        body["tone"] = tones

    d = request("POST", f"/voice-previews/{a.preview_id}/save", body=body)
    vid = d.get("voice_id")
    if not vid:
        sys.exit(f"[失败] {json.dumps(d, ensure_ascii=False)[:300]}")
    print(f"✓ 已保存为音色: {vid}  ({a.name})")
    print(f"\n现在可以直接用它合成：")
    print(f"  python {Path(sys.argv[0]).name} speak \"你好\" --voice {vid}")


def cmd_myvoices(a):
    """列出自己的音色（voice_type=personal）。免费档最多存 5 个。"""
    d = request("GET", f"/voices?voice_type=personal&page_size=50"
                       + (f"&language_code={a.lang}" if a.lang else ""))
    voices = d.get("voices", [])
    total = d.get("total", len(voices))
    print(f"我的音色: {len(voices)} 个\n")
    if not voices:
        print("（还没有自建音色。用 design 或 clone 创建。）")
        return
    print(f"{'voice_id':<18}{'名称':<16}{'来源':<10}{'语言':<6}色调")
    print("-" * 78)
    for v in voices:
        print(f"{v['voice_id']:<18}{v.get('name',''):<16}"
              f"{v.get('origin',''):<10}{v.get('language_code',''):<6}"
              f"{','.join(v.get('tone') or [])}")
    print(f"\n免费档上限 5 个。删除: breeze_tts.py delete <voice_id>")


def cmd_delete(a):
    """
    删除一个音色（软删除）。免费档只有 5 个名额，必须能删。
    默认拒绝删除内置音色（origin=cloned 且 voice_type=default 的公共目录音色）。
    """
    # 先查一下，确认是自己的音色且给出删除前信息（查不到由 request() 报明原因）
    v = request("GET", f"/voices/{a.voice_id}")

    name = v.get("name", "?")
    origin = v.get("origin", "?")
    vtype = v.get("voice_type", "?")

    # 安全闸门：公共目录音色（voice_type=default）不该被删
    if vtype == "default" and not a.force:
        sys.exit(
            f"[拒绝] {name} ({a.voice_id}) 是公共目录音色（voice_type=default），\n"
            f"       不是你的自有音色，删除它没有意义且可能影响他人。\n"
            f"       如确需删除，加 --force。"
        )

    if not a.yes:
        ans = input(f"确认删除音色「{name}」({a.voice_id}, origin={origin})? [y/N] ")
        if ans.strip().lower() not in ("y", "yes"):
            print("已取消")
            return

    request("DELETE", f"/voices/{a.voice_id}")
    print(f"✓ 已删除: {name} ({a.voice_id})")
    print("  提示: 软删除，历史用量记录仍保留。")


def cmd_batch(a):
    """
    批量合成：一次处理整个文本文件，每行（或按分隔符）生成一段音频。
    适合有声书、长文配音、批量播报。

    文本文件格式：每行一段；空行跳过。
    输出：{outdir}/part_0001.mp3, part_0002.mp3, ...
    """
    src = Path(a.file)
    if not src.is_file():
        sys.exit(f"[错误] 文件不存在: {a.file}")

    text = src.read_text(encoding="utf-8")
    # 按行切分，过滤空行；若指定 --separator 则按分隔符切
    if a.separator:
        segs = [s.strip() for s in text.split(a.separator) if s.strip()]
    else:
        segs = [ln.strip() for ln in text.splitlines() if ln.strip()]

    if not segs:
        sys.exit("[错误] 文本文件里没有可合成的内容")

    # 成本预检：CJK 每字 2 单元
    def units(s):
        cjk = sum(1 for ch in s if "一" <= ch <= "鿿"
                  or "぀" <= ch <= "ヿ" or "가" <= ch <= "힯")
        return cjk * 2 + (len(s) - cjk)

    total_units = sum(units(s) for s in segs)
    print(f"[批量] {len(segs)} 段，预计消耗 {total_units} 单元 ≈ {total_units/10:.1f} credits",
          file=sys.stderr)

    if a.dry_run:
        print("\n[dry-run] 未扣费。各段预览：")
        for i, s in enumerate(segs[:10], 1):
            print(f"  {i:3}. [{units(s):4}单元] {s[:50]}")
        if len(segs) > 10:
            print(f"  … 还有 {len(segs)-10} 段")
        print(f"\n确认无误后去掉 --dry-run 重跑。")
        return

    voice = a.voice or _pick_default_voice(a.lang)
    outdir = Path(a.outdir or (src.stem + "_audio"))
    outdir.mkdir(parents=True, exist_ok=True)
    ext = a.format.split("_", 1)[0]          # mp3_44100_128 → mp3

    body_tpl = {"model_id": a.model, "language_code": a.lang}
    if a.instructions:
        body_tpl["instructions"] = a.instructions[:1000]
    if a.guidance != 1.0:
        body_tpl["voice_settings"] = {"guidance_scale": a.guidance}

    ok, fail = 0, 0
    for i, seg in enumerate(segs, 1):
        body = {**body_tpl, "text": seg}
        try:
            audio = request(
                "POST", f"/text-to-speech/{voice}?output_format={a.format}",
                body=body, raw=True,
            )
        except SystemExit as e:
            fail += 1
            print(f"  [{i}/{len(segs)}] ✗ 失败: {e}", file=sys.stderr)
            continue

        fp = outdir / f"part_{i:04d}.{ext}"
        fp.write_bytes(audio)
        ok += 1
        print(f"  [{i}/{len(segs)}] ✓ {fp.name}  ({len(audio)}B, {units(seg)}单元)")

    print(f"\n完成: 成功 {ok}，失败 {fail}。输出目录: {outdir}")


# ----------------------------------------------------------------- CLI
def build_parser():
    p = argparse.ArgumentParser(
        prog="breeze_tts.py",
        description="鲸歌 · dsh-voice — 语音合成命令行（Breeze Blue 后端，零第三方依赖）",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("speak", help="文本合成语音")
    sp.add_argument("text", help="要朗读的文本")
    sp.add_argument("--voice", "-v", help="voice_id（省略则自动挑中性普通话音色）")
    sp.add_argument("--lang", default="zh", help="语言码，默认 zh")
    sp.add_argument("--model", default=DEFAULT_MODEL,
                    help=f"模型，默认 {DEFAULT_MODEL}（其他语言用 {MULTI_MODEL}）")
    sp.add_argument("--instructions", "-i",
                    help="表演指令，如：压低声音耳语，紧张而克制（≤1000字符）")
    sp.add_argument("--guidance", "-g", type=float, default=1.0,
                    help="表演强度 1.0-10.0，默认 1.0（建议表达力段落用 2-3）")
    sp.add_argument("--speed", type=float, default=1.0, help="语速 0.5-2.0")
    sp.add_argument("--format", default="mp3_44100_128",
                    help="输出格式，默认 mp3_44100_128；可 mp3/wav/flac/pcm")
    sp.add_argument("--out", "-o", help="输出文件路径")
    sp.add_argument("--dry-run", action="store_true",
                    help="只显示合成参数与成本，不实际扣费")
    sp.set_defaults(func=cmd_speak)

    vo = sub.add_parser("voices", help="查找音色（不扣费）")
    vo.add_argument("--lang", default="zh", help="语言码，默认 zh")
    vo.add_argument("--search", help="关键词搜索，如 温暖 / 京巷")
    vo.add_argument("--accent", help="口音码；传 null 表示只要中性标准口音")
    vo.add_argument("--limit", type=int, default=12, help="返回数量")
    vo.set_defaults(func=cmd_voices)

    b = sub.add_parser("balance", help="查余额（不扣费）")
    b.set_defaults(func=cmd_balance)

    m = sub.add_parser("models", help="查模型（不扣费）")
    m.set_defaults(func=cmd_models)

    # ---- 定制音色 ----
    de = sub.add_parser("design", help="文字描述造声（生成预览，再用 save 保存）")
    de.add_argument("description", help="声音描述，3-500 字符，如：一个温柔的年轻女声，")
    de.add_argument("--text", "-t", help="试听脚本，3-500 字符（可选）")
    de.add_argument("--guidance", "-g", type=float, default=None,
                    help="贴合强度 1.0-10.0（省略则随机 1-4）")
    de.add_argument("--count", "-n", type=int, default=None, help="候选数量，如 3")
    de.add_argument("--lang", default="zh", help="语言码，默认 zh")
    de.add_argument("--out", "-o", help="预览音频输出前缀")
    de.set_defaults(func=cmd_design)

    cl = sub.add_parser("clone", help="上传音频克隆声音（再用 save 保存）")
    cl.add_argument("file", help="参考音频路径（MP3/WAV，≥3秒，≤5MB，单人无背景音）")
    cl.add_argument("--name", "-n", help="音色名")
    cl.add_argument("--lang", default="zh", help="语言码，默认 zh（中文样本自动限定 ASR）")
    cl.add_argument("--denoise", action="store_true", help="上传前去噪（嘈杂样本用）")
    cl.add_argument("--out", "-o", help="预览音频输出路径")
    cl.set_defaults(func=cmd_clone)

    sv = sub.add_parser("save", help="把预览保存为可复用音色（消耗一个音色名额）")
    sv.add_argument("preview_id", help="预览的 generated_voice_id")
    sv.add_argument("--name", "-n", required=True, help="音色名")
    sv.add_argument("--lang", default="zh", help="语言码，默认 zh")
    sv.add_argument("--description", "-d", help="音色描述")
    sv.add_argument("--tone", help="色调，逗号分隔最多3个，如 warm,gentle,friendly")
    sv.set_defaults(func=cmd_save)

    mv = sub.add_parser("myvoices", help="列出我保存的音色（免费档上限 5 个）")
    mv.add_argument("--lang", default="", help="按语言筛选（可选）")
    mv.set_defaults(func=cmd_myvoices)

    de_ = sub.add_parser("delete", help="删除一个音色（软删除，释放名额）")
    de_.add_argument("voice_id", help="要删除的 voice_id")
    de_.add_argument("--yes", "-y", action="store_true", help="跳过确认")
    de_.add_argument("--force", action="store_true",
                     help="连公共目录音色也删（默认拒绝）")
    de_.set_defaults(func=cmd_delete)

    ba = sub.add_parser("batch", help="批量合成：整个文本文件一次生成多段音频")
    ba.add_argument("file", help="文本文件路径，每行一段（或用 --separator 指定分隔符）")
    ba.add_argument("--voice", "-v", help="voice_id（省略则自动挑）")
    ba.add_argument("--lang", default="zh", help="语言码，默认 zh")
    ba.add_argument("--model", default=DEFAULT_MODEL, help="模型")
    ba.add_argument("--instructions", "-i", help="统一表演指令，应用到所有段")
    ba.add_argument("--guidance", "-g", type=float, default=1.0, help="表演强度")
    ba.add_argument("--format", default="mp3_44100_128", help="输出格式")
    ba.add_argument("--separator", "-s", help="分隔符（默认按行切）")
    ba.add_argument("--outdir", "-d", help="输出目录（默认 <文本名>_audio/）")
    ba.add_argument("--dry-run", action="store_true",
                    help="只算成本不扣费，先确认再真跑")
    ba.set_defaults(func=cmd_batch)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
