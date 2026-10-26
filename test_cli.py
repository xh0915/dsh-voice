"""离线测试：不联网、不扣费、不读真实 key。"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "assets" / "breeze_tts.py"


def run(*args: str, cwd: str | None = None, home: str | None = None):
    env = os.environ.copy()
    env.pop("BREEZE_API_KEY", None)
    env.pop("DASHSCOPE_API_KEY", None)
    env["PYTHONIOENCODING"] = "utf-8"
    if home:
        env["HOME"] = home
        env["USERPROFILE"] = home
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
        env=env,
        timeout=30,
    )


class IdentityTest(unittest.TestCase):
    def test_skill_name_matches_both_installers(self):
        name = re.search(
            r"(?m)^name:\s*(\S+)\s*$",
            (ROOT / "SKILL.md").read_text(encoding="utf-8"),
        ).group(1)
        sh = (ROOT / "install.sh").read_text(encoding="utf-8")
        ps = (ROOT / "install.ps1").read_text(encoding="utf-8-sig")
        self.assertIn(f'SKILL_NAME="{name}"', sh)
        self.assertRegex(ps, rf'\$SkillName\s*=\s*"{re.escape(name)}"')


class HelpTest(unittest.TestCase):
    def test_lists_every_command(self):
        p = run("--help")
        self.assertEqual(p.returncode, 0, p.stderr)
        for cmd in ("speak", "batch", "design", "clone", "save", "delete",
                    "voices", "myvoices", "balance", "models"):
            self.assertIn(cmd, p.stdout)

    def test_save_lang_defaults_to_zh(self):
        p = run("save", "--help")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("默认 zh", p.stdout)


class DryRunTest(unittest.TestCase):
    def test_speak_dry_run_costs_nothing_and_needs_no_voice(self):
        with tempfile.TemporaryDirectory() as d:
            p = run("speak", "你好，世界", "--dry-run", cwd=d, home=d)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("计费预估", p.stderr)
            self.assertIn("[dry-run] 未扣费", p.stdout)
            self.assertIn("(自动挑选)", p.stdout)
            self.assertIn("≈ 0.9 credits", p.stderr)
            self.assertEqual(list(Path(d).glob("whale_*")), [])

    def test_speak_dry_run_reports_requested_format(self):
        with tempfile.TemporaryDirectory() as d:
            p = run("speak", "测试", "--format", "wav", "--dry-run",
                    cwd=d, home=d)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("格式 wav", p.stdout)
            self.assertEqual(list(Path(d).glob("*.wav")), [])

    def test_batch_dry_run_does_not_create_output_dir(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "章节.txt"
            src.write_text(
                "夜深了，星星在窗外眨眼睛。\n她把书合上，轻轻说了一句晚安。\n",
                encoding="utf-8",
            )
            p = run("batch", str(src), "--dry-run", cwd=d, home=d)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("2 段", p.stderr)
            self.assertIn("5.2 credits", p.stderr)
            self.assertIn("未扣费", p.stdout)
            self.assertFalse((Path(d) / "章节_audio").exists())

    def test_batch_missing_file_fails_clearly(self):
        with tempfile.TemporaryDirectory() as d:
            p = run("batch", "不存在.txt", "--dry-run", cwd=d, home=d)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("文件不存在", p.stderr)


class ValidationTest(unittest.TestCase):
    def test_instructions_over_limit_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = run("speak", "你好", "--instructions", "长" * 1001,
                    "--dry-run", cwd=d, home=d)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("1000", p.stderr)

    def test_guidance_out_of_range_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = run("speak", "你好", "--guidance", "0.5",
                    "--dry-run", cwd=d, home=d)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("1.0 - 10.0", p.stderr)


class SecretHygieneTest(unittest.TestCase):
    PATTERNS = (
        re.compile(r"brz_[A-Za-z0-9]{20,}"),
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
    )

    def test_no_real_key_is_committed(self):
        hits = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.name == ".env":
                continue
            if any(part in {"__pycache__", ".git", ".venv"} for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for pattern in self.PATTERNS:
                if pattern.search(text):
                    hits.append(str(path.relative_to(ROOT)))
                    break
        self.assertEqual(hits, [], f"疑似真实密钥出现在: {hits}")

    def test_env_is_ignored(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertRegex(ignored, r"(?m)^\.env$")


if __name__ == "__main__":
    unittest.main()
