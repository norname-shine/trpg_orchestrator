# -*- coding: gbk -*-
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .config import SCRIPTS_DIR
from .env_loader import load_project_env
from .encoding_utils import read_runtime_text
from .output_parser import missing_markers


class ChatGPTWebClient:
    """Restricted ChatGPT web adapter.

    Manual mode is the default. Playwright mode is opt-in through
    TRPG_CHATGPT_AUTOMATION=playwright.
    """

    def __init__(self, campaign_profile: dict[str, Any]) -> None:
        load_project_env()
        binding = campaign_profile.get("chatgpt_conversation_binding", {})
        self.project_name = binding.get("project_name", "")
        self.conversation_name = binding.get("conversation_name", "")

    def validate_binding(self) -> None:
        if not self.project_name or not self.conversation_name:
            raise RuntimeError(
                "ChatGPT fixed conversation is not configured. "
                "Set campaign_profile.json chatgpt_conversation_binding.project_name "
                "and conversation_name first."
            )

    def send_and_capture(self, chatgpt_input_path: Path, output_path: Path) -> None:
        self.validate_binding()
        if not chatgpt_input_path.exists():
            raise FileNotFoundError(f"missing ChatGPT input file: {chatgpt_input_path}")
        mode = os.getenv("TRPG_CHATGPT_AUTOMATION", "manual").lower()
        if mode == "playwright":
            self._send_with_playwright(chatgpt_input_path, output_path)
            return
        raise RuntimeError(
            "Manual ChatGPT send mode. Paste outbox/chatgpt_input.md into the configured fixed "
            "conversation, save the latest reply to outbox/chatgpt_raw_output.md, then run trpg ingest. "
            "To opt into browser automation, set TRPG_CHATGPT_AUTOMATION=playwright and "
            "TRPG_BROWSER_USER_DATA_DIR."
        )

    def send_file_and_capture(self, input_path: Path, output_path: Path) -> None:
        self.validate_binding()
        if not input_path.exists():
            raise FileNotFoundError(f"missing ChatGPT input file: {input_path}")
        mode = os.getenv("TRPG_CHATGPT_AUTOMATION", "manual").lower()
        if mode != "playwright":
            raise RuntimeError("send_file_and_capture requires TRPG_CHATGPT_AUTOMATION=playwright.")
        self._send_with_playwright(input_path, output_path)

    def capture_latest(self, output_path: Path) -> None:
        self.validate_binding()
        mode = os.getenv("TRPG_CHATGPT_AUTOMATION", "manual").lower()
        if mode != "playwright":
            raise RuntimeError("capture requires TRPG_CHATGPT_AUTOMATION=playwright.")
        self._send_with_playwright(Path("__capture_only__"), output_path, capture_only=True)

    def _send_with_playwright(self, chatgpt_input_path: Path, output_path: Path, capture_only: bool = False) -> None:
        user_data_dir = os.getenv("TRPG_BROWSER_USER_DATA_DIR")
        if not user_data_dir:
            raise RuntimeError("TRPG_BROWSER_USER_DATA_DIR is required when TRPG_CHATGPT_AUTOMATION=playwright.")
        script = SCRIPTS_DIR / "chatgpt_web_send.mjs"
        npx = shutil.which("npx.cmd") or shutil.which("npx.exe") or shutil.which("npx")
        if not npx:
            raise RuntimeError("npx is required for Playwright automation, but it was not found on PATH.")
        command = [
            npx,
            "-y",
            "-p",
            "playwright",
            "node",
            str(script),
            "--input",
            str(chatgpt_input_path),
            "--output",
            str(output_path),
            "--project",
            self.project_name,
            "--conversation",
            self.conversation_name,
        ]
        if capture_only:
            command.extend(["--capture-only", "true"])
        if os.getenv("TRPG_CHATGPT_CREATE_IF_MISSING", "0") == "1":
            command.extend(["--create-if-missing", "true"])
        completed = subprocess.run(
            command,
            cwd=str(SCRIPTS_DIR.parent),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(f"ChatGPT Playwright automation stopped: {detail}")
        if not output_path.exists():
            raise RuntimeError("ChatGPT automation finished but did not create chatgpt_raw_output.md.")
        captured = read_runtime_text(output_path)
        missing = missing_markers(captured)
        if missing:
            raise RuntimeError(f"Captured ChatGPT reply missing markers: {', '.join(missing)}")


def browser_safety_stop_reason(page_text: str) -> str | None:
    lowered = page_text.lower()
    blocked_terms = [
        "log in",
        "sign in",
        "captcha",
        "verification",
        "verify your identity",
        "payment",
        "billing",
        "subscription",
        "account settings",
        "privacy settings",
        "security settings",
        "security",
        "账号设置",
        "安全验证",
        "验证码",
        "支付",
        "订阅",
        "隐私设置",
    ]
    for term in blocked_terms:
        if term.lower() in lowered:
            return f"blocked browser state detected: {term}"
    return None
