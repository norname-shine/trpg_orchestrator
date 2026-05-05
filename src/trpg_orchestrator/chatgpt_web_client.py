# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, SCRIPTS_DIR
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
        if use_browser_worker():
            return
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

    def send_file_and_capture(self, input_path: Path, output_path: Path, mode: str = "text") -> None:
        self.validate_binding()
        if not input_path.exists():
            raise FileNotFoundError(f"missing ChatGPT input file: {input_path}")
        automation_mode = os.getenv("TRPG_CHATGPT_AUTOMATION", "manual").lower()
        if automation_mode != "playwright":
            raise RuntimeError("send_file_and_capture requires TRPG_CHATGPT_AUTOMATION=playwright.")
        self._send_with_playwright(input_path, output_path, mode=mode)

    def capture_latest(self, output_path: Path) -> None:
        self.validate_binding()
        mode = os.getenv("TRPG_CHATGPT_AUTOMATION", "manual").lower()
        if mode != "playwright":
            raise RuntimeError("capture requires TRPG_CHATGPT_AUTOMATION=playwright.")
        self._send_with_playwright(Path("__capture_only__"), output_path, capture_only=True)

    def _send_with_playwright(self, chatgpt_input_path: Path, output_path: Path, capture_only: bool = False, mode: str = "text") -> None:
        user_data_dir = os.getenv("TRPG_BROWSER_USER_DATA_DIR")
        if not user_data_dir:
            raise RuntimeError("TRPG_BROWSER_USER_DATA_DIR is required when TRPG_CHATGPT_AUTOMATION=playwright.")
        if use_browser_worker() and not capture_only:
            run_via_browser_worker(chatgpt_input_path, output_path, mode=mode)
            return
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
            "--mode",
            mode,
        ]
        if capture_only:
            command.extend(["--capture-only", "true"])
        if os.getenv("TRPG_CHATGPT_CREATE_IF_MISSING", "0") == "1":
            command.extend(["--create-if-missing", "true"])
        if os.getenv("TRPG_STREAM_VISIBLE_REPLY") == "1":
            completed = run_playwright_streaming(command)
        else:
            completed = subprocess.run(
                command,
                cwd=str(SCRIPTS_DIR.parent),
                text=True,
                encoding="utf-8",
                capture_output=True,
            )

        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            if detail:
                raise RuntimeError(f"ChatGPT Playwright automation stopped: {detail}")
            raise RuntimeError(f"ChatGPT Playwright automation stopped with exit code {completed.returncode}")
        if not output_path.exists():
            raise RuntimeError("ChatGPT automation finished but did not create chatgpt_raw_output.md.")
        captured = read_runtime_text(output_path)
        if mode != "image":
            missing = missing_markers(captured)
            if missing:
                raise RuntimeError(f"Captured ChatGPT reply missing markers: {', '.join(missing)}")


def run_playwright_streaming(command: list[str]) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        command,
        cwd=str(SCRIPTS_DIR.parent),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []

    def drain(pipe: Any, target: list[str], sink: Any) -> None:
        if pipe is None:
            return
        try:
            for line in pipe:
                target.append(line)
                sink.write(line)
                sink.flush()
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    threads = [
        threading.Thread(target=drain, args=(process.stdout, stdout_parts, sys.stdout), daemon=True),
        threading.Thread(target=drain, args=(process.stderr, stderr_parts, sys.stderr), daemon=True),
    ]
    for thread in threads:
        thread.start()
    returncode = process.wait()
    for thread in threads:
        thread.join(timeout=1)
    return subprocess.CompletedProcess(command, returncode, "".join(stdout_parts), "".join(stderr_parts))


def use_browser_worker() -> bool:
    return os.getenv("TRPG_BROWSER_WORKER", "1").strip().lower() in {"1", "true", "yes", "on"}


def worker_root() -> Path:
    return Path(os.getenv("TRPG_CHATGPT_WORKER_DIR") or (PROJECT_ROOT / ".runtime" / "chatgpt_worker"))


def run_via_browser_worker(input_path: Path, output_path: Path, mode: str = "text") -> None:
    root = worker_root()
    tasks = root / "tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    ensure_browser_worker(root)
    task_id = f"task_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
    task_path = tasks / f"{task_id}.json"
    status_path = tasks / f"{task_id}.status.json"
    payload = {
        "id": task_id,
        "state": "pending",
        "input_path": str(input_path),
        "output_path": str(output_path),
        "mode": mode,
        "capture_only": False,
        "created_at": time.time(),
    }
    task_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    deadline = time.time() + float(os.getenv("TRPG_CHATGPT_WORKER_TIMEOUT", "900"))
    last_status = ""
    while time.time() < deadline:
        status = read_worker_status(status_path)
        if status:
            emit_worker_public_status(status)
            state = str(status.get("state") or "")
            if state == "complete":
                if not output_path.exists():
                    raise RuntimeError("ChatGPT worker completed but did not create chatgpt_raw_output.md.")
                return
            if state == "failed":
                raise RuntimeError(str(status.get("error") or "ChatGPT browser worker failed."))
            last_status = json.dumps(status, ensure_ascii=False)
        elif not worker_alive(root):
            ensure_browser_worker(root)
        time.sleep(0.8)
    raise RuntimeError(f"ChatGPT browser worker timed out. Last status: {last_status}")


def ensure_browser_worker(root: Path) -> None:
    if worker_alive(root):
        return
    script = SCRIPTS_DIR / "chatgpt_browser_worker.mjs"
    npx = shutil.which("npx.cmd") or shutil.which("npx.exe") or shutil.which("npx")
    if not npx:
        raise RuntimeError("npx is required for Playwright browser worker, but it was not found on PATH.")
    env = os.environ.copy()
    env["TRPG_CHATGPT_WORKER_DIR"] = str(root)
    env.setdefault("TRPG_BROWSER_USER_DATA_DIR", str(PROJECT_ROOT / ".browser-profile"))
    subprocess.Popen(
        [npx, "-y", "-p", "playwright", "node", str(script)],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    deadline = time.time() + 25
    while time.time() < deadline:
        if worker_alive(root):
            return
        time.sleep(0.5)
    raise RuntimeError("ChatGPT browser worker did not become ready.")


def worker_alive(root: Path) -> bool:
    status = read_worker_status(root / "worker_status.json")
    if not status:
        return False
    pid = int(status.get("pid") or 0)
    updated_at = float(status.get("updated_at") or 0) / 1000
    if not pid or (updated_at and time.time() - updated_at > 120):
        return False
    if os.name == "nt":
        return windows_pid_alive(pid)
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def windows_pid_alive(pid: int) -> bool:
    try:
        completed = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            text=True,
            encoding="utf-8",
            errors="ignore",
            capture_output=True,
            timeout=5,
        )
    except Exception:
        return False
    output = completed.stdout or ""
    return f'"{pid}"' in output or f",{pid}," in output or f" {pid} " in output


def read_worker_status(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def emit_worker_public_status(status: dict[str, Any]) -> None:
    public = {
        "stage": status.get("stage") or "actor_waiting",
        "percent": status.get("percent"),
        "label": status.get("label") or "",
        "needs_human_verification": bool(status.get("needs_human_verification")),
    }
    encoded = json.dumps(public, ensure_ascii=False)
    print(f"TRPG_WORKER_STATUS {encoded}", flush=True)


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
