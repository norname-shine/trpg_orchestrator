# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import hashlib
import json
import shutil
import subprocess
import sys
import threading
import time
import uuid
import urllib.request
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, SCRIPTS_DIR
from .env_loader import load_project_env
from .encoding_utils import read_runtime_text, write_text_utf8
from .output_parser import missing_markers


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def browser_evidence_path(output_path: Path) -> Path:
    return output_path.parent / "browser_evidence.json"


def build_browser_evidence(
    *,
    ok: bool,
    mode: str,
    campaign_id: str,
    input_hash: str = "",
    output_hash: str = "",
    markers_ok: bool = False,
    blocked_reason: str = "",
    error: str = "",
) -> dict[str, Any]:
    return {
        "ok": bool(ok),
        "mode": mode,
        "campaign_id": campaign_id,
        "input_hash": input_hash,
        "output_hash": output_hash,
        "markers_ok": bool(markers_ok),
        "blocked_reason": blocked_reason,
        "error": error,
    }


def write_browser_evidence(output_path: Path, evidence: dict[str, Any]) -> None:
    write_text_utf8(browser_evidence_path(output_path), json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")


def evaluate_browser_output(output_path: Path, mode: str) -> tuple[bool, bool, str, str]:
    if not output_path.exists():
        return False, False, "empty_output", "ChatGPT automation did not create an output file."
    captured = read_runtime_text(output_path)
    if not captured.strip():
        return False, False, "empty_output", "Captured ChatGPT reply is empty."
    safety_reason = browser_safety_stop_reason(captured)
    if safety_reason:
        return False, False, "blocked_browser_state", safety_reason
    if mode != "image":
        missing = missing_markers(captured)
        if missing:
            return False, False, "missing_markers", f"Captured ChatGPT reply missing markers: {', '.join(missing)}"
    return True, True if mode != "image" else True, "", ""


class ChatGPTWebClient:
    """Restricted ChatGPT web adapter.

    Manual mode is the default. Playwright mode is opt-in through
    TRPG_CHATGPT_AUTOMATION=playwright.
    """

    def __init__(self, campaign_profile: dict[str, Any], campaign_memory: dict[str, Any] | None = None) -> None:
        load_project_env()
        self.campaign_profile = campaign_profile if isinstance(campaign_profile, dict) else {}
        self.campaign_memory = campaign_memory if isinstance(campaign_memory, dict) else {}
        binding = campaign_profile.get("chatgpt_conversation_binding", {})
        story_name = str(self.campaign_profile.get("title") or self.campaign_profile.get("name") or "").strip()
        binding_project = str(binding.get("project_name") or "").strip()
        binding_conversation = str(binding.get("conversation_name") or "").strip()
        self.project_name = binding_project or story_name
        self.conversation_name = binding_conversation or self._conversation_title(story_name)

    def _conversation_title(self, story_name: str, fallback: str = "") -> str:
        progress = self.campaign_memory.get("story_progress.json", {})
        chapter = progress.get("current_chapter") if isinstance(progress, dict) else {}
        if isinstance(chapter, dict):
            title = str(chapter.get("name") or chapter.get("title") or "").strip()
            if title:
                return title
        if story_name:
            return f"{story_name} 固定对话"
        return fallback

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
        campaign_id = str(self.campaign_profile.get("campaign_id") or "")
        evidence_mode = "capture_only" if capture_only else mode
        input_hash = "" if capture_only else sha256_file(chatgpt_input_path)
        try:
            if use_browser_worker() and not capture_only:
                run_via_browser_worker(
                    chatgpt_input_path,
                    output_path,
                    mode=mode,
                    project_name=self.project_name,
                    conversation_name=self.conversation_name,
                    campaign_id=campaign_id,
                )
                ok, markers_ok, blocked_reason, error = evaluate_browser_output(output_path, mode)
                write_browser_evidence(output_path, build_browser_evidence(
                    ok=ok,
                    mode=evidence_mode,
                    campaign_id=campaign_id,
                    input_hash=input_hash,
                    output_hash=sha256_file(output_path),
                    markers_ok=markers_ok,
                    blocked_reason=blocked_reason,
                    error=error,
                ))
                if not ok:
                    raise RuntimeError(error or blocked_reason or "ChatGPT browser evidence failed.")
                return
        except Exception as exc:
            write_browser_evidence(output_path, build_browser_evidence(
                ok=False,
                mode=evidence_mode,
                campaign_id=campaign_id,
                input_hash=input_hash,
                output_hash=sha256_file(output_path),
                markers_ok=False,
                blocked_reason=browser_safety_stop_reason(read_runtime_text(output_path)) if output_path.exists() else "browser_automation_error",
                error=str(exc),
            ))
            raise
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
        command.extend(["--evidence", str(browser_evidence_path(output_path))])
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
            write_browser_evidence(output_path, build_browser_evidence(
                ok=False,
                mode=evidence_mode,
                campaign_id=campaign_id,
                input_hash=input_hash,
                output_hash=sha256_file(output_path),
                markers_ok=False,
                blocked_reason=browser_safety_stop_reason(read_runtime_text(output_path)) if output_path.exists() else "browser_automation_error",
                error=detail or f"ChatGPT Playwright automation stopped with exit code {completed.returncode}",
            ))
            if detail:
                raise RuntimeError(f"ChatGPT Playwright automation stopped: {detail}")
            raise RuntimeError(f"ChatGPT Playwright automation stopped with exit code {completed.returncode}")
        ok, markers_ok, blocked_reason, error = evaluate_browser_output(output_path, mode)
        write_browser_evidence(output_path, build_browser_evidence(
            ok=ok,
            mode=evidence_mode,
            campaign_id=campaign_id,
            input_hash=input_hash,
            output_hash=sha256_file(output_path),
            markers_ok=markers_ok,
            blocked_reason=blocked_reason,
            error=error,
        ))
        if not ok:
            raise RuntimeError(error or blocked_reason or "ChatGPT browser evidence failed.")


def run_playwright_streaming(command: list[str]) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        command,
        cwd=str(SCRIPTS_DIR.parent),
        text=True,
        encoding="utf-8",
        errors="strict",
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


def run_via_browser_worker(
    input_path: Path,
    output_path: Path,
    mode: str = "text",
    project_name: str = "",
    conversation_name: str = "",
    campaign_id: str = "",
) -> None:
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
        "evidence_path": str(browser_evidence_path(output_path)),
        "mode": mode,
        "capture_only": False,
        "project_name": project_name,
        "conversation_name": conversation_name,
        "auto_create": True,
        "campaign_id": campaign_id,
        "created_at": time.time(),
    }
    write_text_utf8(task_path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    deadline = time.time() + float(os.getenv("TRPG_CHATGPT_WORKER_TIMEOUT", "900"))
    stale_worker_seconds = float(os.getenv("TRPG_CHATGPT_WORKER_STALE_SECONDS", "120"))
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
            updated_at = float(status.get("updated_at") or 0) / 1000
            stale_seconds = time.time() - updated_at if updated_at else 0
            if stale_seconds > stale_worker_seconds:
                write_text_utf8(status_path, json.dumps({
                    "task_id": task_id,
                    "state": "running",
                    "stage": "browser_restarting",
                    "label": "ChatGPT browser worker stopped updating; restarting",
                    "percent": 10,
                    "updated_at": int(time.time() * 1000),
                }, ensure_ascii=False, indent=2) + "\n")
                reset_worker_task(task_path, task_id)
                terminate_browser_worker(root)
                ensure_browser_worker(root)
            last_status = json.dumps(status, ensure_ascii=False)
        elif not worker_alive(root):
            reset_worker_task(task_path, task_id)
            ensure_browser_worker(root)
        time.sleep(0.8)
    raise RuntimeError(f"ChatGPT browser worker timed out. Last status: {last_status}")


def reset_worker_task(task_path: Path, task_id: str) -> None:
    data = read_worker_status(task_path)
    if not data or str(data.get("id") or "") != task_id:
        return
    if str(data.get("state") or "") in {"complete", "failed"}:
        return
    data["state"] = "pending"
    data["requeued_at"] = time.time()
    write_text_utf8(task_path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def terminate_browser_worker(root: Path) -> None:
    status = read_worker_status(root / "worker_status.json")
    pid = int(status.get("pid") or 0)
    if not pid:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            text=True,
            encoding="utf-8",
            errors="ignore",
            capture_output=True,
            timeout=10,
        )
        return
    try:
        os.kill(pid, 15)
    except Exception:
        pass


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
    if not cdp_alive(str(status.get("cdp_url") or os.getenv("TRPG_BROWSER_CDP_URL") or "http://127.0.0.1:9222")):
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


def cdp_alive(cdp_url: str) -> bool:
    try:
        with urllib.request.urlopen(cdp_url.rstrip("/") + "/json/version", timeout=3) as response:
            return 200 <= int(getattr(response, "status", 0) or 0) < 300
    except Exception:
        return False


def read_worker_status(path: Path) -> dict[str, Any]:
    try:
        return json.loads(read_runtime_text(path))
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
