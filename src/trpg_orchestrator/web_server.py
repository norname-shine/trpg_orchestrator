# -*- coding: gbk -*-
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .config import CAMPAIGNS_DIR, OUTBOX_DIR, PROJECT_ROOT
from .json_utils import read_json, write_json
from .memory_store import MemoryStore
from .output_parser import parse_chatgpt_output


STATIC_DIR = PROJECT_ROOT / "web"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787


class JobState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running = False
        self.command: list[str] = []
        self.started_at = 0.0
        self.finished_at = 0.0
        self.returncode: int | None = None
        self.output = ""
        self.error = ""

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "running": self.running,
                "command": self.command,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "returncode": self.returncode,
                "output": self.output[-30000:],
                "error": self.error[-30000:],
            }

    def start(self, command: list[str]) -> None:
        with self.lock:
            if self.running:
                raise RuntimeError("A TRPG command is already running.")
            self.running = True
            self.command = command
            self.started_at = time.time()
            self.finished_at = 0.0
            self.returncode = None
            self.output = ""
            self.error = ""

    def finish(self, completed: subprocess.CompletedProcess[str]) -> None:
        with self.lock:
            self.running = False
            self.finished_at = time.time()
            self.returncode = completed.returncode
            self.output = completed.stdout or ""
            self.error = completed.stderr or ""


JOB = JobState()


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    host = os.getenv("TRPG_WEB_HOST", DEFAULT_HOST)
    port = int(os.getenv("TRPG_WEB_PORT", str(DEFAULT_PORT)))
    if "--port" in argv:
        port = int(argv[argv.index("--port") + 1])
    if "--host" in argv:
        host = argv[argv.index("--host") + 1]

    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{port}/"
    print(f"TRPG web console: {url}")
    if "--no-open" not in argv:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    server.serve_forever()
    return 0


class Handler(BaseHTTPRequestHandler):
    server_version = "TRPGOrchestrator/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/app.css":
            self._send_file(STATIC_DIR / "app.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self._send_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
            return
        if parsed.path == "/new-campaign-demo.html":
            self._send_file(STATIC_DIR / "new-campaign-demo.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/map-item-preview.html":
            self._send_file(STATIC_DIR / "map-item-preview.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/api/status":
            self._json(status_payload())
            return
        if parsed.path == "/api/output":
            self._json(output_payload())
            return
        if parsed.path == "/api/export":
            self._download_export()
            return
        if parsed.path == "/api/asset":
            query = parse_qs(parsed.query)
            self._json(asset_lookup(
                first_query(query, "campaign_id"),
                first_query(query, "key"),
            ))
            return
        if parsed.path.startswith("/campaign-assets/"):
            self._send_campaign_asset(parsed.path)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/run-turn":
                payload = self._read_json()
                action = str(payload.get("action", "")).strip()
                if not action:
                    raise RuntimeError("Player action is empty.")
                campaign_id = str(payload.get("campaign_id", "")).strip()
                command = cli_command(["run-turn", "--action", action, "--auto-rewrite", "--rewrite-attempts", "2"], campaign_id)
                launch_job(command)
                self._json({"ok": True, "job": JOB.snapshot()})
                return
            if parsed.path == "/api/prepare":
                payload = self._read_json()
                action = str(payload.get("action", "")).strip()
                if not action:
                    raise RuntimeError("Player action is empty.")
                campaign_id = str(payload.get("campaign_id", "")).strip()
                command = cli_command(["prepare", "--action", action], campaign_id)
                launch_job(command)
                self._json({"ok": True, "job": JOB.snapshot()})
                return
            if parsed.path == "/api/select-campaign":
                payload = self._read_json()
                campaign_id = str(payload.get("campaign_id", "")).strip()
                select_campaign(campaign_id)
                self._json({"ok": True, "status": status_payload()})
                return
            if parsed.path == "/api/asset":
                payload = self._read_json()
                self._json(save_asset(payload))
                return
            if parsed.path == "/api/command":
                payload = self._read_json()
                name = str(payload.get("name", "")).strip()
                campaign_id = str(payload.get("campaign_id", "")).strip()
                allowed = {
                    "send": ["send"],
                    "capture": ["capture"],
                    "ingest": ["ingest"],
                    "validate-memory": ["validate-memory"],
                    "memory-report": ["memory-report"],
                    "rewrite-plan": ["rewrite-plan"],
                    "run-rewrite": ["run-rewrite", "--max-attempts", "2"],
                }
                if name not in allowed:
                    raise RuntimeError(f"Command is not allowed: {name}")
                command = cli_command(allowed[name], campaign_id)
                launch_job(command)
                self._json({"ok": True, "job": JOB.snapshot()})
                return
        except Exception as exc:
            self._json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stdout.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(body or "{}")

    def _json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        raw = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_campaign_asset(self, request_path: str) -> None:
        try:
            parts = unquote(request_path).split("/", 3)
            if len(parts) != 4:
                raise RuntimeError("invalid asset path")
            campaign_id = safe_segment(parts[2])
            rel = Path(parts[3])
            root = (CAMPAIGNS_DIR / campaign_id / "assets").resolve()
            target = (root / rel).resolve()
            if root not in target.parents and target != root:
                raise RuntimeError("asset path escapes campaign assets")
            if not target.exists() or target.suffix.lower() != ".png":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._send_file(target, "image/png")
        except Exception:
            self.send_error(HTTPStatus.NOT_FOUND)

    def _download_export(self) -> None:
        payload = export_payload()
        raw = payload.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", "text/markdown; charset=utf-8")
        self.send_header("content-disposition", "attachment; filename=trpg_export.md")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def first_query(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key) or [""]
    return str(values[0]).strip()


def safe_segment(value: str) -> str:
    cleaned = "".join(ch if (ch.isalnum() or ch in "_.-") else "_" for ch in str(value).strip())
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.strip("._") or "asset"


def asset_manifest_path(campaign_id: str) -> Path:
    return CAMPAIGNS_DIR / safe_segment(campaign_id) / "assets" / "manifest.json"


def load_asset_manifest(campaign_id: str) -> dict[str, Any]:
    path = asset_manifest_path(campaign_id)
    if not path.exists():
        return {"assets": {}}
    try:
        data = read_json(path)
        if isinstance(data, dict):
            data.setdefault("assets", {})
            return data
    except Exception:
        pass
    return {"assets": {}}


def asset_lookup(campaign_id: str, key: str) -> dict[str, Any]:
    if not campaign_id:
        campaign_id = MemoryStore().resolve_campaign_id(None)
    if not key:
        raise RuntimeError("asset key is required")
    manifest = load_asset_manifest(campaign_id)
    entry = manifest.get("assets", {}).get(key)
    if not entry:
        return {"ok": True, "exists": False}
    rel_path = str(entry.get("path", ""))
    full = CAMPAIGNS_DIR / safe_segment(campaign_id) / rel_path
    if not rel_path or not full.exists():
        return {"ok": True, "exists": False}
    url_path = rel_path.replace("\\", "/")
    if url_path.startswith("assets/"):
        url_path = url_path[len("assets/"):]
    return {
        "ok": True,
        "exists": True,
        "entry": entry,
        "url": f"/campaign-assets/{safe_segment(campaign_id)}/{url_path}",
    }


def save_asset(payload: dict[str, Any]) -> dict[str, Any]:
    campaign_id = str(payload.get("campaign_id") or "").strip() or MemoryStore().resolve_campaign_id(None)
    key = str(payload.get("key") or "").strip()
    if not key:
        raise RuntimeError("asset key is required")
    data_url = str(payload.get("data_url") or "")
    prefix = "data:image/png;base64,"
    if not data_url.startswith(prefix):
        raise RuntimeError("asset data_url must be a PNG data URL")
    raw = base64.b64decode(data_url[len(prefix):], validate=True)
    subdir = safe_segment(str(payload.get("subdir") or payload.get("kind") or "misc"))
    filename = safe_segment(str(payload.get("filename") or key)) + ".png"
    rel_path = Path("assets") / subdir / filename
    root = CAMPAIGNS_DIR / safe_segment(campaign_id)
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)

    manifest = load_asset_manifest(campaign_id)
    manifest.setdefault("assets", {})[key] = {
        "path": rel_path.as_posix(),
        "kind": str(payload.get("kind") or subdir),
        "seed": str(payload.get("seed") or key),
        "style": str(payload.get("style") or "canvas_pixel"),
        "generator_version": int(payload.get("generator_version") or 1),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        manifest["assets"][key]["metadata"] = metadata
    write_json(asset_manifest_path(campaign_id), manifest)
    return asset_lookup(campaign_id, key)


def cli_command(parts: list[str], campaign_id: str = "") -> list[str]:
    command = [sys.executable, "-m", "trpg_orchestrator.cli", *parts]
    if campaign_id and parts[0] not in {"validate-memory", "memory-report", "rewrite-plan", "run-rewrite"}:
        command.extend(["--campaign-id", campaign_id])
    return command


def launch_job(command: list[str]) -> None:
    JOB.start(command)
    thread = threading.Thread(target=run_command, args=(command,), daemon=True)
    thread.start()


def run_command(command: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    env.setdefault("TRPG_CHATGPT_AUTOMATION", "playwright")
    env.setdefault("TRPG_BROWSER_USER_DATA_DIR", str(PROJECT_ROOT / ".browser-profile"))
    env.setdefault("TRPG_BROWSER_CHANNEL", "chrome")
    completed = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    JOB.finish(completed)


def status_payload() -> dict[str, Any]:
    store = MemoryStore()
    registry = store.load_registry()
    cid = registry.get("active_campaign") or ""
    campaigns = registry.get("campaigns", {})
    current = campaigns.get(cid, {}) if cid else {}
    return {
        "project_root": str(PROJECT_ROOT),
        "active_campaign": cid,
        "campaigns": campaigns,
        "campaign_list": campaign_list(registry),
        "campaign_state": campaign_state(cid),
        "chatgpt_project": current.get("chatgpt_project_name", ""),
        "chatgpt_conversation": current.get("chatgpt_conversation_name", ""),
        "job": JOB.snapshot(),
        "output": output_payload(),
    }

def campaign_list(registry: dict[str, Any]) -> list[dict[str, Any]]:
    active = registry.get("active_campaign") or ""
    rows = []
    for campaign_id, meta in registry.get("campaigns", {}).items():
        root = CAMPAIGNS_DIR / campaign_id
        profile = read_json(root / "campaign_profile.json") if (root / "campaign_profile.json").exists() else {}
        recent = read_json(root / "recent_context.json") if (root / "recent_context.json").exists() else {}
        rows.append({
            "campaign_id": campaign_id,
            "name": meta.get("name") or profile.get("title") or campaign_id,
            "title": profile.get("title") or meta.get("name") or campaign_id,
            "genre": profile.get("genre", ""),
            "tone": profile.get("tone", ""),
            "chapter": recent.get("current_scene", {}).get("chapter") or recent.get("chapter", "") or recent.get("current_scene", {}).get("time", ""),
            "conversation": meta.get("chatgpt_conversation_name", ""),
            "project": meta.get("chatgpt_project_name", ""),
            "active": campaign_id == active,
            "status": meta.get("status", ""),
        })
    return rows


def campaign_state(campaign_id: str) -> dict[str, Any]:
    if not campaign_id:
        return {}
    root = CAMPAIGNS_DIR / campaign_id

    def maybe(name: str) -> dict[str, Any]:
        path = root / name
        return read_json(path) if path.exists() else {}

    profile = maybe("campaign_profile.json")
    return {
        "title": profile.get("title") or campaign_id,
        "genre": profile.get("genre", ""),
        "tone": profile.get("tone", ""),
        "mechanics": profile.get("mechanics", {}),
        "player": maybe("player_state.json"),
        "character_prompt": maybe("character_prompt.json"),
        "recent": maybe("recent_context.json"),
        "quests": maybe("quest_history.json"),
        "equipment": maybe("equipment_history.json"),
        "locations": maybe("location_history.json"),
        "world": maybe("world_state.json"),
        "ecology": maybe("enemy_or_monster_ecology.json"),
        "npcs": maybe("npc_memory.json"),
        "threads": maybe("main_threads.json"),
    }


def select_campaign(campaign_id: str) -> None:
    store = MemoryStore()
    registry = store.load_registry()
    if campaign_id not in registry.get("campaigns", {}):
        raise RuntimeError(f"unknown campaign_id: {campaign_id}")
    registry["active_campaign"] = campaign_id
    store.save_registry(registry)


def export_payload() -> str:
    status = status_payload()
    output = status.get("output", {})
    parsed = output.get("parsed", {})
    lines = [
        f"# {status.get('active_campaign', 'TRPG Export')}",
        "",
        "## Body",
        parsed.get("body", ""),
        "",
        "## Choices",
        parsed.get("choices", ""),
        "",
        "## Summary",
        parsed.get("summary", ""),
        "",
        "## V4 Pressure Pack",
        "```json",
        json.dumps(output.get("pressure_pack", {}), ensure_ascii=False, indent=2),
        "```",
    ]
    return "\n".join(lines)

def output_payload() -> dict[str, Any]:
    clean_path = OUTBOX_DIR / "chatgpt_clean_output.md"
    raw_path = OUTBOX_DIR / "chatgpt_raw_output.md"
    pressure_path = OUTBOX_DIR / "pressure_pack.json"
    audit_path = OUTBOX_DIR / "v4_audit_result.json"
    flavor_path = OUTBOX_DIR / "ai_flavor_report.json"
    text = ""
    parsed: dict[str, Any] = {"body": "", "choices": "", "summary": "", "blocks": []}
    source = ""
    for path in (clean_path, raw_path):
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
            source = path.name
            break
    if text:
        try:
            p = parse_chatgpt_output(text) if "【状态回写_BEGIN】" in text else None
            if p:
                parsed = {"body": p.body, "choices": p.choices, "summary": p.summary, "blocks": p.blocks}
            else:
                parsed = split_public(text)
        except Exception:
            parsed = split_public(text)
    return {
        "source": source,
        "public_text": text,
        "parsed": parsed,
        "pressure_pack": read_json(pressure_path) if pressure_path.exists() else {},
        "audit_result": read_json(audit_path) if audit_path.exists() else {},
        "ai_flavor_report": read_json(flavor_path) if flavor_path.exists() else {},
    }


def split_public(text: str) -> dict[str, str]:
    body = ""
    choices = ""
    summary = ""
    if "【正文】" in text:
        body = text.split("【正文】", 1)[1].split("【选择点】", 1)[0].strip()
    if "【选择点】" in text:
        choices = text.split("【选择点】", 1)[1].split("【回合摘要】", 1)[0].strip()
    if "【回合摘要】" in text:
        summary = text.split("【回合摘要】", 1)[1].split("【状态回写_BEGIN】", 1)[0].strip()
    return {"body": body, "choices": choices, "summary": summary, "blocks": []}


if __name__ == "__main__":
    raise SystemExit(main())
