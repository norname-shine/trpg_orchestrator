# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import json
import os
import re
import shutil
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

from .capability_resolver import build_capability_plan
from .config import CAMPAIGNS_DIR, MEMORY_FILE_NAMES, OUTBOX_DIR, PROJECT_ROOT, PROMPTS_DIR
from .encoding_utils import read_runtime_text, read_text_auto
from .frontend_module_state import build_frontend_modules
from .json_utils import extract_json_object, read_json, write_json
from .memory_compactor import build_compaction_report
from .memory_store import MemoryStore
from .output_parser import parse_chatgpt_output, public_output
from .prompt_builder import build_audit_user_prompt, read_prompt
from .deepseek_client import DeepSeekClient
from .schema_validator import normalize_pressure_pack_compat, validate_audit_result, validate_writeback
from .story_progress import build_frontend_story_progress
from .writeback import apply_approved_writeback, has_applied_writeback, writeback_hash


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

OUTBOX_SNAPSHOT_NAMES = (
    "last_player_action.txt",
    "v4_director_input.md",
    "chatgpt_input.md",
    "chatgpt_raw_output.md",
    "chatgpt_clean_output.md",
    "chatgpt_blocks.json",
    "state_writeback.json",
    "pressure_pack.json",
    "v4_audit_result.json",
    "ai_flavor_report.json",
    "chatgpt_image_input.md",
    "chatgpt_image_raw_output.md",
    "image_job.json",
)


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
        if parsed.path == "/director-debug.html":
            self._send_file(STATIC_DIR / "director-debug.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/writeback-review.html":
            self._send_file(STATIC_DIR / "writeback-review.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/prompt-inspector.html":
            self._send_file(STATIC_DIR / "prompt-inspector.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/api/status":
            self._json(status_payload())
            return
        if parsed.path == "/api/frontend-state":
            query = parse_qs(parsed.query)
            self._json(frontend_state_response(first_query(query, "campaign_id")))
            return
        if parsed.path == "/api/output":
            query = parse_qs(parsed.query)
            self._json(output_payload(first_query(query, "campaign_id")))
            return
        if parsed.path == "/api/raw-output":
            query = parse_qs(parsed.query)
            self._json(raw_output_payload(first_query(query, "campaign_id")))
            return
        if parsed.path == "/api/canvas-rules":
            self._json(canvas_rules_payload())
            return
        if parsed.path == "/api/new-campaign-defaults":
            self._json(new_campaign_defaults_payload())
            return
        if parsed.path == "/api/rules":
            query = parse_qs(parsed.query)
            self._json(rules_payload(first_query(query, "name"), first_query(query, "q")))
            return
        if parsed.path == "/api/prompt-inspector":
            query = parse_qs(parsed.query)
            self._json(prompt_inspector_payload(first_query(query, "campaign_id")))
            return
        if parsed.path == "/api/memory-report":
            query = parse_qs(parsed.query)
            self._json(memory_report_payload(first_query(query, "campaign_id")))
            return
        if parsed.path == "/api/assets":
            query = parse_qs(parsed.query)
            self._json(asset_list(
                first_query(query, "campaign_id"),
                first_query(query, "kind"),
            ))
            return
        if parsed.path == "/api/writeback-review":
            query = parse_qs(parsed.query)
            self._json(writeback_review_payload(first_query(query, "campaign_id")))
            return
        if parsed.path == "/api/campaign-profile":
            query = parse_qs(parsed.query)
            self._json(campaign_profile_payload(first_query(query, "campaign_id")))
            return
        if parsed.path == "/api/export":
            self._download_export()
            return
        if parsed.path == "/api/export-campaign":
            query = parse_qs(parsed.query)
            self._download_campaign_export(first_query(query, "campaign_id"))
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
            if parsed.path == "/api/init-campaign":
                payload = self._read_json()
                self._json(init_campaign_payload(payload))
                return
            if parsed.path == "/api/create-campaign-smart":
                payload = self._read_json()
                self._json(create_campaign_smart_payload(payload))
                return
            if parsed.path == "/api/set-chatgpt-binding":
                payload = self._read_json()
                self._json(set_chatgpt_binding_payload(payload))
                return
            if parsed.path == "/api/campaign-profile":
                payload = self._read_json()
                self._json(update_campaign_profile_payload(payload))
                return
            if parsed.path == "/api/campaign-status":
                payload = self._read_json()
                self._json(update_campaign_status_payload(payload))
                return
            if parsed.path == "/api/audit-writeback":
                payload = self._read_json()
                self._json(audit_writeback_payload(str(payload.get("campaign_id", "")).strip()))
                return
            if parsed.path == "/api/apply-writeback":
                payload = self._read_json()
                self._json(apply_writeback_payload(str(payload.get("campaign_id", "")).strip()))
                return
            if parsed.path == "/api/asset":
                payload = self._read_json()
                self._json(save_asset(payload))
                return
            if parsed.path == "/api/rebuild-assets":
                payload = self._read_json()
                self._json(rebuild_assets(payload))
                return
            if parsed.path == "/api/command":
                payload = self._read_json()
                name = str(payload.get("name", "")).strip()
                campaign_id = str(payload.get("campaign_id", "")).strip()
                allowed = {
                    "send": ["send"],
                    "send-image": ["send-image"],
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

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/asset":
                query = parse_qs(parsed.query)
                self._json(delete_asset({
                    "campaign_id": first_query(query, "campaign_id"),
                    "key": first_query(query, "key"),
                }))
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
        self.send_header("cache-control", "no-store, max-age=0")
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

    def _download_campaign_export(self, campaign_id: str = "") -> None:
        payload = campaign_export_payload(campaign_id)
        resolved = safe_segment(str(payload.get("campaign_id") or "campaign"))
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-disposition", f"attachment; filename={resolved}_campaign_export.json")
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
        return {"campaign_id": campaign_id, "asset_seed": campaign_asset_seed(campaign_id), "assets": {}}
    try:
        data = read_json(path)
        if isinstance(data, dict):
            data.setdefault("campaign_id", campaign_id)
            data.setdefault("asset_seed", campaign_asset_seed(campaign_id))
            data.setdefault("assets", {})
            return data
    except Exception:
        pass
    return {"campaign_id": campaign_id, "asset_seed": campaign_asset_seed(campaign_id), "assets": {}}


def campaign_asset_seed(campaign_id: str) -> str:
    root = CAMPAIGNS_DIR / safe_segment(campaign_id)
    profile_path = root / "campaign_profile.json"
    if profile_path.exists():
        try:
            profile = read_json(profile_path)
            if profile.get("asset_seed"):
                return str(profile["asset_seed"])
        except Exception:
            pass
    registry_path = CAMPAIGNS_DIR / "campaign_registry.json"
    if registry_path.exists():
        try:
            registry = read_json(registry_path)
            seed = registry.get("campaigns", {}).get(campaign_id, {}).get("asset_seed")
            if seed:
                return str(seed)
        except Exception:
            pass
    import hashlib
    return hashlib.sha256(f"trpg-assets:{campaign_id}".encode("utf-8")).hexdigest()[:16]


def campaign_outbox_dir(campaign_id: str) -> Path:
    return CAMPAIGNS_DIR / safe_segment(campaign_id) / "outbox"


def outbox_has_content(path: Path) -> bool:
    return any((path / name).exists() for name in OUTBOX_SNAPSHOT_NAMES)


def outbox_campaign_id(path: Path) -> str:
    for name in ("pressure_pack.json", "state_writeback.json", "chatgpt_blocks.json"):
        candidate = path / name
        if not candidate.exists():
            continue
        try:
            data = read_json(candidate)
        except Exception:
            continue
        if isinstance(data, dict):
            value = data.get("campaign_id") or data.get("campaign")
            if value:
                return str(value)
    return ""


def sync_global_outbox_to_campaign(campaign_id: str) -> Path:
    target = campaign_outbox_dir(campaign_id)
    target.mkdir(parents=True, exist_ok=True)
    marker_mtime = max(
        file_mtime(OUTBOX_DIR / "pressure_pack.json"),
        file_mtime(OUTBOX_DIR / "state_writeback.json"),
    )
    for name in OUTBOX_SNAPSHOT_NAMES:
        source = OUTBOX_DIR / name
        if source.exists():
            if name in {"chatgpt_raw_output.md", "chatgpt_clean_output.md", "chatgpt_blocks.json"} and is_stale_public_output(source, marker_mtime):
                continue
            shutil.copy2(source, target / name)
    return target


def file_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime if path.exists() else 0.0
    except OSError:
        return 0.0


def is_stale_public_output(path: Path, marker_mtime: float) -> bool:
    if not marker_mtime:
        return False
    return bool(file_mtime(path) and file_mtime(path) + 60 < marker_mtime)


def outbox_latest_mtime(path: Path) -> float:
    mtimes = []
    for name in OUTBOX_SNAPSHOT_NAMES:
        candidate = path / name
        if candidate.exists():
            try:
                mtimes.append(candidate.stat().st_mtime)
            except OSError:
                pass
    return max(mtimes) if mtimes else 0.0


def resolve_outbox_dir(campaign_id: str = "") -> Path:
    if not campaign_id:
        campaign_id = MemoryStore().resolve_campaign_id(None)
    scoped = campaign_outbox_dir(campaign_id)
    global_matches = outbox_campaign_id(OUTBOX_DIR) == campaign_id
    if global_matches and outbox_latest_mtime(OUTBOX_DIR) > outbox_latest_mtime(scoped):
        return sync_global_outbox_to_campaign(campaign_id)
    if outbox_has_content(scoped):
        return scoped
    if global_matches:
        return sync_global_outbox_to_campaign(campaign_id)
    return scoped


def read_web_capability_plan(outbox_dir: Path, campaign_id: str, memory: dict[str, Any]) -> dict[str, Any]:
    path = outbox_dir / "capability_plan.json"
    if path.exists():
        data = read_json(path)
        if isinstance(data, dict):
            return data
    action_path = outbox_dir / "last_player_action.txt"
    action = read_runtime_text(action_path) if action_path.exists() else ""
    return build_capability_plan(campaign_id, action, memory)


def require_outbox_campaign(outbox_dir: Path, campaign_id: str) -> None:
    if not campaign_id:
        return
    found = outbox_campaign_id(outbox_dir)
    if found and found != campaign_id:
        raise RuntimeError(f"outbox campaign mismatch: expected {campaign_id}, got {found}")


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
        "key": key,
        "entry": entry,
        "url": f"/campaign-assets/{safe_segment(campaign_id)}/{url_path}",
    }



def asset_entry_payload(campaign_id: str, key: str, entry: dict[str, Any]) -> dict[str, Any]:
    rel_path = str(entry.get("path", ""))
    full = CAMPAIGNS_DIR / safe_segment(campaign_id) / rel_path
    url_path = rel_path.replace("\\", "/")
    if url_path.startswith("assets/"):
        url_path = url_path[len("assets/"):]
    return {
        "key": key,
        "exists": bool(rel_path and full.exists()),
        "url": f"/campaign-assets/{safe_segment(campaign_id)}/{url_path}" if rel_path else "",
        "asset_seed": entry.get("asset_seed") or campaign_asset_seed(campaign_id),
        **entry,
    }


def asset_list(campaign_id: str, kind: str = "") -> dict[str, Any]:
    if not campaign_id:
        campaign_id = MemoryStore().resolve_campaign_id(None)
    manifest = load_asset_manifest(campaign_id)
    entries = []
    for key, entry in manifest.get("assets", {}).items():
        if not isinstance(entry, dict):
            continue
        if kind and str(entry.get("kind", "")) != kind:
            continue
        entries.append(asset_entry_payload(campaign_id, key, entry))
    entries.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return {"ok": True, "campaign_id": campaign_id, "assets": entries}


def frontend_state_response(campaign_id: str = "") -> dict[str, Any]:
    store = MemoryStore()
    registry = store.load_registry()
    resolved = store.resolve_campaign_id(campaign_id or None)
    campaigns = registry.get("campaigns", {})
    current = campaigns.get(resolved, {})
    state = campaign_state(resolved)
    output = output_payload(resolved, require_parse_ready=True)
    assets = asset_list(resolved).get("assets", [])
    frontend = build_frontend_state(resolved, current, state, output, assets)
    job = JOB.snapshot()
    return {
        "ok": True,
        "project_root": str(PROJECT_ROOT),
        "active_campaign": resolved,
        "campaigns": campaigns,
        "campaign_list": campaign_list(registry),
        "campaign_state": state,
        "chatgpt_project": current.get("chatgpt_project_name", ""),
        "chatgpt_conversation": current.get("chatgpt_conversation_name", ""),
        "job": job,
        "pipeline": frontend_pipeline_status(resolved, output, job),
        "output": output,
        "assets": assets,
        "frontend_state": frontend,
    }


def build_frontend_state(campaign_id: str, meta: dict[str, Any], state: dict[str, Any], output: dict[str, Any], assets: list[dict[str, Any]]) -> dict[str, Any]:
    recent = state.get("recent", {}) if isinstance(state.get("recent"), dict) else {}
    scene = recent.get("current_scene", {}) if isinstance(recent.get("current_scene"), dict) else {}
    profile = {
        "id": campaign_id,
        "title": state.get("title") or meta.get("name") or campaign_id,
        "asset_seed": campaign_asset_seed(campaign_id),
        "genre": state.get("genre", ""),
        "tone": state.get("tone", ""),
        "chapter": campaign_chapter(campaign_id),
        "status": meta.get("status", ""),
        "binding": {
            "project_name": meta.get("chatgpt_project_name", ""),
            "conversation_name": meta.get("chatgpt_conversation_name", ""),
        },
        "scene": scene,
    }
    gallery = frontend_gallery(campaign_id, state, output, assets)
    story_progress_payload = frontend_story_progress_payload(campaign_id)
    map_panel = frontend_map_panel(campaign_id, scene, output, assets)
    pressure = normalize_pressure_pack_compat(output.get("pressure_pack", {}) if isinstance(output.get("pressure_pack"), dict) else {})
    frontend_base = {
        "asset_seed": profile["asset_seed"],
        "story_log": {
            "campaign_id": output.get("campaign_id", campaign_id),
            "source": output.get("source", ""),
            "blocks": output.get("parsed", {}).get("blocks", []) if isinstance(output.get("parsed"), dict) else [],
            "summary": output.get("parsed", {}).get("summary", "") if isinstance(output.get("parsed"), dict) else "",
        },
    }
    modules = build_frontend_modules(campaign_id, frontend_base, pressure, assets, story_progress_payload)
    return {
        "schema": "trpg_orchestrator.frontend_state.v1",
        "asset_seed": profile["asset_seed"],
        "campaign": profile,
        "character_card": frontend_character_card(campaign_id, state),
        "companion_card": frontend_companion_card(state),
        "map_panel": map_panel,
        "quests": frontend_quests(state),
        "inventory": frontend_inventory(state),
        "gallery": gallery,
        "story_progress": story_progress_payload,
        "modules": modules,
        "story_log": {
            "campaign_id": output.get("campaign_id", campaign_id),
            "source": output.get("source", ""),
            "blocks": output.get("parsed", {}).get("blocks", []) if isinstance(output.get("parsed"), dict) else [],
            "summary": output.get("parsed", {}).get("summary", "") if isinstance(output.get("parsed"), dict) else "",
            "record_tabs": ["story", "summary", "logs"],
            "mode_tabs": ["immersive", "story", "logs"],
            "admin_pages": {
                "director": "/director-debug.html",
                "writeback": "/writeback-review.html",
            },
        },
        "quick_actions": [
            {"id": "continue", "label": "继续", "action": "继续"},
            {"id": "observe", "label": "观察周围", "action": "观察周围"},
            {"id": "talk", "label": "与 NPC 对话", "action": "与 NPC 对话"},
            {"id": "inspect_item", "label": "检查物品", "action": "检查物品"},
            {"id": "recap", "label": "复盘", "action": "复盘"},
        ],
    }


def campaign_chapter(campaign_id: str) -> str:
    root = CAMPAIGNS_DIR / safe_segment(campaign_id)
    profile = read_json(root / "campaign_profile.json") if (root / "campaign_profile.json").exists() else {}
    recent = read_json(root / "recent_context.json") if (root / "recent_context.json").exists() else {}
    scene = recent.get("current_scene", {}) if isinstance(recent.get("current_scene"), dict) else {}
    return profile.get("chapter", "") or scene.get("chapter", "") or recent.get("chapter", "") or scene.get("time", "")


def frontend_character_card(campaign_id: str, state: dict[str, Any]) -> dict[str, Any]:
    prompt = state.get("character_prompt", {}) if isinstance(state.get("character_prompt"), dict) else {}
    player = state.get("player", {}) if isinstance(state.get("player"), dict) else {}
    provided = first_dict(player.get("character_card"), prompt.get("character_card"))
    identity = first_dict(provided.get("identity"), player.get("confirmed_identity"), prompt.get("confirmed_identity"))
    recent = state.get("recent", {}) if isinstance(state.get("recent"), dict) else {}
    scene = recent.get("current_scene", {}) if isinstance(recent.get("current_scene"), dict) else {}
    fallback = character_fallback_profile(campaign_id, state, scene)
    name = str(identity.get("name") or inferred_player_name(player, prompt) or state.get("title") or "玩家角色")
    identity_text = " / ".join([str(x) for x in (identity.get("ancestry"), identity.get("class_or_role") or identity.get("role"), identity.get("level_or_stage")) if x]) or fallback["identity"]
    return {
        "name": name,
        "identity": identity_text,
        "portrait": {
            "asset_key": f"portrait:{safe_segment(name)}",
            "type": "player_full_body_pixel",
            "quality": "high",
        },
        "progress": normalize_frontend_progress(provided.get("progression"), fallback["progress"]),
        "core_stats": normalize_frontend_core_stats(provided.get("vitals"), fallback["core_stats"]),
        "tags": normalize_frontend_tags(provided.get("conditions"), fallback["tags"]),
        "attributes": normalize_frontend_attributes(provided.get("attributes"), fallback["attributes"]),
    }


def frontend_companion_card(state: dict[str, Any]) -> dict[str, Any]:
    prompt = state.get("character_prompt", {}) if isinstance(state.get("character_prompt"), dict) else {}
    player = state.get("player", {}) if isinstance(state.get("player"), dict) else {}
    provided = first_dict(player.get("character_card"), prompt.get("character_card"))
    identity = first_dict(provided.get("identity"), player.get("confirmed_identity"), prompt.get("confirmed_identity"))
    source = first_dict(provided.get("companion"), prompt.get("companion_card"))
    if not source and isinstance(identity.get("companion"), dict):
        source = identity.get("companion")
    if not source:
        return {}
    name = str(source.get("name") or "").strip()
    if not name:
        return {}
    archetype = normalize_companion_archetype(str(source.get("archetype") or source.get("kind") or source.get("species") or source.get("type") or source.get("name") or "companion"))
    identity_text = str(source.get("identity") or source.get("class") or source.get("species") or source.get("kind") or "伙伴")
    return {
        "name": name,
        "identity": identity_text,
        "archetype": archetype,
        "portrait": {"asset_key": f"companion:{safe_segment(name)}", "type": "companion_portrait_pixel"},
        "meta": source,
    }


def frontend_map_panel(campaign_id: str, scene: dict[str, Any], output: dict[str, Any], assets: list[dict[str, Any]]) -> dict[str, Any]:
    pressure = normalize_pressure_pack_compat(output.get("pressure_pack", {}) if isinstance(output.get("pressure_pack"), dict) else {})
    if not pressure:
        pressure_path = resolve_outbox_dir(campaign_id) / "pressure_pack.json"
        pressure = normalize_pressure_pack_compat(read_json(pressure_path)) if pressure_path.exists() else {}
    output_requests = pressure.get("output_requests", {}) if isinstance(pressure.get("output_requests"), dict) else {}
    map_request = output_requests.get("map", {}) if isinstance(output_requests.get("map"), dict) else {}
    map_mode = map_request.get("mode", "keep_previous")
    payloads = pressure.get("payloads", {}) if isinstance(pressure.get("payloads"), dict) else {}
    route = payloads.get("map_route") if map_mode in {"update_route", "update_canvas"} and isinstance(payloads.get("map_route"), dict) else {}
    canvas_raw = payloads.get("map_canvas") if map_mode == "update_canvas" and isinstance(payloads.get("map_canvas"), dict) else {}
    if not route and map_mode in {"update_route", "update_canvas"} and isinstance(pressure.get("map_route"), dict):
        route = pressure.get("map_route", {})
    canvas = normalize_map_canvas(canvas_raw, route, scene) if route or canvas_raw else {}
    latest = next((item for item in assets if item.get("kind") == "map" or str(item.get("kind", "")).startswith("gallery_map")), {})
    return {
        "latest_map": {
            "asset_key": latest.get("key") or f"map:{safe_segment(scene.get('location') or campaign_id)}",
            "url": latest.get("url", ""),
            "source": "map_canvas" if canvas.get("points") else "cached_or_generated",
            "ascii_grid": "\n".join(canvas.get("ascii", [])) if isinstance(canvas.get("ascii"), list) else "",
            "generated_at_turn": scene.get("turn_index", ""),
            "title": route.get("title") or scene.get("location") or "当前区域地图",
            "map_route": route,
            "map_canvas": canvas,
            "story_topology": pressure.get("story_topology", {}) if isinstance(pressure.get("story_topology"), dict) else {},
            "visual_assets": pressure.get("visual_assets", []),
        },
        "mode": map_mode,
        "update_requested": map_mode in {"update_route", "update_canvas"} and bool(route.get("nodes")),
        "keep_previous": True,
    }


def frontend_story_progress_payload(campaign_id: str) -> dict[str, Any]:
    root = CAMPAIGNS_DIR / safe_segment(campaign_id)
    blueprint_path = root / "story_blueprint.json"
    progress_path = root / "story_progress.json"
    blueprint = read_json(blueprint_path) if blueprint_path.exists() else {}
    progress = read_json(progress_path) if progress_path.exists() else {}
    return build_frontend_story_progress(blueprint, progress)


def frontend_modules(output: dict[str, Any], story_progress: dict[str, Any], map_panel: dict[str, Any]) -> dict[str, Any]:
    pressure = normalize_pressure_pack_compat(output.get("pressure_pack", {}) if isinstance(output.get("pressure_pack"), dict) else {})
    output_requests = pressure.get("output_requests", {}) if isinstance(pressure.get("output_requests"), dict) else {}
    map_request = output_requests.get("map", {}) if isinstance(output_requests.get("map"), dict) else {}
    map_mode = map_request.get("mode") or "keep_previous"
    return {
        "story_log": {
            "mode": "update",
            "state": "ready",
            "update_requested": True,
            "payload": output.get("parsed", {}) if isinstance(output.get("parsed"), dict) else {},
        },
        "story_progress": {
            "mode": "update",
            "state": "ready",
            "update_requested": True,
            "payload": story_progress,
        },
        "map_panel": {
            "mode": map_mode,
            "state": "ready" if map_panel.get("latest_map") else "cached",
            "update_requested": map_mode in {"update_route", "update_canvas"} and bool(map_panel.get("latest_map", {}).get("map_route", {}).get("nodes")),
            "payload": map_panel.get("latest_map", {}),
            "payload_ref": map_panel.get("latest_map", {}).get("url") or "asset://map/latest",
            "reason": map_request.get("reason", ""),
        },
        "gallery": {"mode": "no_update", "state": "idle", "update_requested": False},
        "inventory": {"mode": "no_update", "state": "idle", "update_requested": False},
        "dossier": {"mode": "no_update", "state": "idle", "update_requested": False},
        "character_card": {"mode": "no_update", "state": "cached", "update_requested": False},
        "debug": {"mode": "admin_only", "state": "hidden"},
    }


def normalize_map_canvas(raw: Any, route: dict[str, Any], scene: dict[str, Any]) -> dict[str, Any]:
    base = {
        "canvas": {"width": 1280, "height": 720, "grid_cols": 32, "grid_rows": 18},
        "legend": {"#": "wall_or_block", ".": "walkable", "~": "water_or_anomaly", "!": "hazard", "?": "clue", "+": "resource"},
        "ascii": [],
        "points": [],
        "routes": [],
        "hazards": [],
    }
    if isinstance(raw, dict) and (raw.get("points") or raw.get("ascii")):
        result = {**base, **raw}
        result["canvas"] = {**base["canvas"], **(raw.get("canvas") if isinstance(raw.get("canvas"), dict) else {})}
        result["legend"] = {**base["legend"], **(raw.get("legend") if isinstance(raw.get("legend"), dict) else {})}
        result["ascii"] = normalize_ascii_grid(result.get("ascii"), result["canvas"]["grid_cols"], result["canvas"]["grid_rows"])
        return result
    return map_canvas_from_route(route, scene, base)


def normalize_ascii_grid(value: Any, cols: int, rows: int) -> list[str]:
    source = value if isinstance(value, list) else []
    output = []
    for row in source[:rows]:
        text = str(row or "")[:cols]
        output.append(text + "." * max(0, cols - len(text)))
    while len(output) < rows:
        output.append("." * cols)
    return output


def map_canvas_from_route(route: dict[str, Any], scene: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    cols = base["canvas"]["grid_cols"]
    rows = base["canvas"]["grid_rows"]
    layout = [(4, 12), (9, 10), (14, 8), (20, 6), (26, 8), (22, 12), (13, 14)]
    nodes = route.get("nodes") if isinstance(route.get("nodes"), list) else []
    points = []
    for index, node in enumerate(nodes[:7]):
        if not isinstance(node, dict):
            continue
        x, y = layout[index % len(layout)]
        point_id = str(node.get("id") or node.get("label") or f"node_{index + 1}")
        points.append({
            "id": point_id,
            "label": str(node.get("label") or point_id),
            "x": x,
            "y": y,
            "symbol": "?" if node.get("certainty") in {"clue", "uncertain", "inferred"} else "+",
            "certainty": node.get("certainty") or "confirmed",
        })
    edges = route.get("edges") if isinstance(route.get("edges"), list) else []
    routes = [edge for edge in edges if isinstance(edge, dict)]
    if not routes and len(points) > 1:
        routes = [{"from": points[i]["id"], "to": points[i + 1]["id"], "kind": "route"} for i in range(len(points) - 1)]
    markers = route.get("markers") if isinstance(route.get("markers"), list) else []
    marker_layout = [(18, 4), (27, 12), (8, 6), (16, 15), (23, 4)]
    hazards = []
    for index, marker in enumerate(markers[:5]):
        if not isinstance(marker, dict):
            continue
        x, y = marker_layout[index % len(marker_layout)]
        kind = str(marker.get("kind") or "clue")
        hazards.append({
            "id": str(marker.get("id") or f"marker_{index + 1}"),
            "label": str(marker.get("label") or kind),
            "x": x,
            "y": y,
            "symbol": "!" if re.search(r"hazard|danger|危险", kind, re.I) else "?",
            "kind": kind,
            "certainty": marker.get("certainty") or "uncertain",
        })
    grid = [["." for _ in range(cols)] for _ in range(rows)]
    for point in points:
        if 0 <= point["x"] < cols and 0 <= point["y"] < rows:
            grid[point["y"]][point["x"]] = str(point.get("symbol") or "+")[:1]
    for hazard in hazards:
        if 0 <= hazard["x"] < cols and 0 <= hazard["y"] < rows:
            grid[hazard["y"]][hazard["x"]] = str(hazard.get("symbol") or "!")[:1]
    return {**base, "ascii": ["".join(row) for row in grid], "points": points, "routes": routes, "hazards": hazards, "title": route.get("title") or scene.get("location") or ""}


def frontend_quests(state: dict[str, Any]) -> list[dict[str, Any]]:
    quests = state.get("quests", {}) if isinstance(state.get("quests"), dict) else {}
    rows = []
    for index, row in enumerate(normalize_memory_rows(quests.get("quest_updates")) + normalize_memory_rows(quests.get("facts"))):
        rows.append({"id": f"quest_{index + 1}", "short_name": concise_text(row["title"], 18), "detail": row["detail"], "status": "active", "priority": "main"})
    return rows[:12]


def frontend_inventory(state: dict[str, Any]) -> list[dict[str, Any]]:
    equipment = state.get("equipment", {}) if isinstance(state.get("equipment"), dict) else {}
    recent = state.get("recent", {}) if isinstance(state.get("recent"), dict) else {}
    source = []
    items = equipment.get("items") if isinstance(equipment.get("items"), dict) else {}
    for item_id, item in items.items():
        if not isinstance(item, dict):
            continue
        confirmed = item.get("confirmed") if isinstance(item.get("confirmed"), dict) else {}
        uncertain = item.get("uncertain") if isinstance(item.get("uncertain"), list) else []
        detail = "；".join(str(x) for x in [
            confirmed.get("observed_reaction"),
            confirmed.get("appearance"),
            confirmed.get("current_status"),
            *uncertain[:2],
        ] if x)
        source.append({
            "title": str(item.get("display_name") or item.get("name") or item_id),
            "detail": detail,
            "tag": str(item.get("category") or "物品"),
        })
    source.extend(normalize_memory_rows(equipment.get("equipment_updates")) + normalize_memory_rows(equipment.get("facts")))
    scene = recent.get("short_term_state", {}) if isinstance(recent.get("short_term_state"), dict) else {}
    for key in ("resources",):
        if scene.get(key):
            source.extend(split_clause_rows(scene.get(key), "物品"))
    keywords = re.compile(r"手机|信号|拨号|屏幕|电话|斧|剑|药|瓶|盒|匣|钥匙|书|信|照片|骨|素材|装备|物件|货车|泥|痕|油灯|登记册|任务板|缰绳|行囊|鳞|补给|样本|碎片")
    merged: dict[str, dict[str, Any]] = {}
    for item in [row for row in source if keywords.search(row["title"] + row["detail"]) and is_inventory_candidate(row)]:
        analysis = analyze_inventory_item(item["title"], item["detail"])
        if analysis["category"] == "misc" and analysis["role"] == "record":
            continue
        entity_id = stable_inventory_entity_id(item["title"], item["detail"], analysis)
        detail = item["detail"] or item["title"]
        if entity_id in merged:
            merged[entity_id]["detail"] = merge_detail_text(merged[entity_id]["detail"], detail)
            merged[entity_id]["raw_name"] = merge_detail_text(merged[entity_id]["raw_name"], item["title"])
            continue
        merged[entity_id] = {
            "id": entity_id,
            "raw_name": item["title"],
            "short_name": analysis["short_name"],
            "category": analysis["category"],
            "role": analysis["role"],
            "detail": detail,
            "visual_prompt": analysis["visual_prompt"],
            "asset_key": f"item:{safe_segment(entity_id)}",
        }
    return list(merged.values())[:16]


def frontend_gallery(campaign_id: str, state: dict[str, Any], output: dict[str, Any], assets: list[dict[str, Any]]) -> dict[str, Any]:
    filters = gallery_filters_for_campaign(campaign_id, state)
    allowed_kinds = gallery_allowed_filter_ids(filters)
    rows = []
    scene = state.get("recent", {}).get("current_scene", {}) if isinstance(state.get("recent"), dict) else {}
    protected = protected_actor_names(state)
    active_npc_names = [str(name) for name in scene.get("active_npcs", []) if str(name).strip()] if isinstance(scene.get("active_npcs"), list) else []
    active_npc_ids = {stable_actor_entity_id(name) for name in active_npc_names}
    npc_row_by_id: dict[str, dict[str, Any]] = {}
    inventory = frontend_inventory(state)
    inventory_titles = {normalized_name(item.get("short_name")) for item in inventory}
    inventory_ids = {str(item.get("id") or "") for item in inventory}
    inventory_row_by_id = {str(item.get("id") or ""): item for item in inventory}
    for name in active_npc_names:
        if normalized_name(name) in protected:
            continue
        actor_id = stable_actor_entity_id(name)
        row = {"kind": "npc", "key": f"npc:{actor_id}", "title": name, "meta": "NPC", "detail": "当前场景角色"}
        npc_row_by_id[actor_id] = row
        rows.append(row)
    for item in inventory[:8]:
        rows.append({"kind": "item", "key": item["asset_key"], "title": item["short_name"], "meta": item["category"], "detail": item["detail"], "visual_prompt": item.get("visual_prompt", {})})
    pressure = output.get("pressure_pack", {}) if isinstance(output.get("pressure_pack"), dict) else {}
    parsed = output.get("parsed", {}) if isinstance(output.get("parsed"), dict) else {}
    for block in parsed.get("blocks", []) if isinstance(parsed.get("blocks"), list) else []:
        if not isinstance(block, dict) or block.get("type") != "cg_image":
            continue
        kind = coerce_gallery_kind_to_allowed("cg", allowed_kinds)
        if not kind:
            continue
        cached_url = str(block.get("cached_url") or block.get("image_url") or block.get("url") or "")
        if not cached_url:
            continue
        rows.append({
            "kind": kind,
            "key": str(block.get("asset_key") or block.get("id") or cached_url),
            "title": "CG",
            "meta": "CG",
            "detail": str(block.get("image_detail") or block.get("body") or ""),
            "cached_url": cached_url,
            "status": "current",
        })
    for index, asset in enumerate(pressure.get("visual_assets", []) if isinstance(pressure.get("visual_assets"), list) else []):
        asset = normalize_visual_asset_prompt(asset)
        kind = normalize_frontend_gallery_kind(asset.get("kind"))
        display_zone = str(asset.get("display_zone") or "").lower()
        if kind == "scene" and display_zone != "map":
            kind = "item"
        kind = coerce_gallery_kind_to_allowed(kind, allowed_kinds)
        if not kind:
            continue
        title = str(asset.get("title") or asset.get("id") or kind)
        detail = str(asset.get("detail") or asset.get("source_memory") or "")
        if kind == "npc":
            actor_id = stable_actor_entity_id(title)
            if actor_id in npc_row_by_id:
                npc_row_by_id[actor_id]["detail"] = merge_detail_text(npc_row_by_id[actor_id].get("detail", ""), detail)
                npc_row_by_id[actor_id]["meta"] = asset.get("certainty") or npc_row_by_id[actor_id].get("meta") or "NPC"
                continue
        row = {"kind": kind, "key": f"v4:{kind}:{asset.get('id') or index}", "title": title, "meta": asset.get("certainty") or kind, "detail": detail, "image_prompt": asset.get("image_prompt", {})}
        if kind in {"item", "clue", "document", "anomaly"}:
            analysis = analyze_inventory_item(title, detail)
            entity_id = stable_inventory_entity_id(title, detail, analysis)
            if entity_id in inventory_row_by_id:
                inventory_row_by_id[entity_id]["detail"] = merge_detail_text(inventory_row_by_id[entity_id].get("detail", ""), detail)
                continue
            row["kind"] = "item" if kind in {"clue", "document", "anomaly"} else kind
            if row["kind"] == "item" and str(asset.get("kind") or "").lower() == "scene":
                row["meta"] = "视觉记录"
                row["visual_prompt"] = analyze_scene_visual_asset(title, detail)
            else:
                row["meta"] = analysis["category"] if analysis["category"] != "misc" else row["meta"]
                row["visual_prompt"] = analysis["visual_prompt"]
        rows.append(row)
    for asset in assets:
        kind = normalize_frontend_gallery_kind(asset.get("kind"))
        kind = coerce_gallery_kind_to_allowed(kind, allowed_kinds)
        if not kind:
            continue
        metadata = asset.get("metadata", {}) if isinstance(asset.get("metadata"), dict) else {}
        title = metadata.get("title") or readable_asset_name(asset.get("key", ""), kind)
        if not is_gallery_cache_asset(asset, protected, inventory_titles, inventory_ids, active_npc_ids, kind, title):
            continue
        rows.append({
            "kind": kind,
            "key": asset.get("key", ""),
            "title": title,
            "meta": metadata.get("meta") or kind,
            "detail": metadata.get("detail") or "",
            "cached_url": asset.get("url", ""),
            "visual_prompt": metadata.get("visual_prompt") or {},
            "image_prompt": metadata.get("image_prompt") or {},
            "status": metadata.get("status") or metadata.get("current_status") or asset.get("status") or "",
            "created_at": asset.get("created_at", ""),
            "archived": bool(metadata.get("archived") or metadata.get("superseded")),
        })
    return {"filters": filters, "assets": mark_frontend_scene_archive_state(dedupe_frontend_assets(rows))[:120]}


def normalize_visual_asset_prompt(asset: Any) -> dict[str, Any]:
    row = dict(asset) if isinstance(asset, dict) else {}
    title = str(row.get("title") or row.get("id") or "visual asset")
    detail = str(row.get("detail") or row.get("source_memory") or "")
    style = str(row.get("style_preset") or row.get("style") or "cinematic anime urban horror, Fate-inspired, controlled lighting")
    positive = str(row.get("positive_prompt") or row.get("prompt") or "").strip()
    if not positive:
        positive = concise_text(f"{title}, {detail}, {style}, clear subject, coherent composition, readable scene details", 420)
    negative = str(row.get("negative_prompt") or "").strip()
    if not negative:
        negative = "low quality, blurry, text artifacts, watermark, logo, extra limbs, malformed hands, incoherent layout, overexposed, underexposed"
    row["positive_prompt"] = positive
    row["negative_prompt"] = negative
    row["aspect_ratio"] = str(row.get("aspect_ratio") or ("16:9" if row.get("display_zone") == "map" or row.get("kind") in {"scene", "map"} else "1:1"))
    row["style_preset"] = style
    quality = row.get("quality")
    row["quality"] = quality if isinstance(quality, dict) else {
        "steps": 30,
        "cfg_scale": 6.5,
        "sampler": "DPM++ 2M Karras",
        "size": "1280x720" if row["aspect_ratio"] == "16:9" else "1024x1024",
    }
    row["image_prompt"] = {
        "positive_prompt": row["positive_prompt"],
        "negative_prompt": row["negative_prompt"],
        "aspect_ratio": row["aspect_ratio"],
        "style_preset": row["style_preset"],
        "quality": row["quality"],
    }
    return row


def first_dict(*values: Any) -> dict[str, Any]:
    for value in values:
        if isinstance(value, dict):
            return value
    return {}


def normalize_companion_archetype(value: str) -> str:
    text = value.lower()
    if "palico" in text or "艾露" in text or "艾鲁" in text or "浩文" in text:
        return "palico"
    if "servant" in text or "从者" in text or "英灵" in text or "assassin" in text:
        return "servant"
    return text or "companion"


def normalized_name(value: Any) -> str:
    return re.sub(r"[\s_：:「」'\"]+", "", str(value or "").lower())


def stable_actor_entity_id(name: Any) -> str:
    text = str(name or "")
    text = re.sub(r"[（(].*?[）)]", "", text)
    text = re.sub(r"\s+", "", text)
    if "许守井" in text:
        return "xu_shoujing"
    if "陈航" in text:
        return "chen_hang"
    if re.search(r"assassin|从者|英灵", text, re.I):
        return "assassin"
    if re.search(r"lee", text, re.I):
        return "lee"
    return safe_segment(normalized_name(text) or "actor")


def protected_actor_names(state: dict[str, Any]) -> set[str]:
    prompt = state.get("character_prompt", {}) if isinstance(state.get("character_prompt"), dict) else {}
    player = state.get("player", {}) if isinstance(state.get("player"), dict) else {}
    provided = first_dict(player.get("character_card"), prompt.get("character_card"))
    identity = first_dict(provided.get("identity"), player.get("confirmed_identity"), prompt.get("confirmed_identity"))
    names = {identity.get("name"), prompt.get("confirmed_identity", {}).get("name") if isinstance(prompt.get("confirmed_identity"), dict) else ""}
    companion = first_dict(provided.get("companion"), prompt.get("companion_card"))
    names.add(companion.get("name"))
    return {normalized_name(name) for name in names if name}


def is_inventory_candidate(row: dict[str, str]) -> bool:
    title = str(row.get("title", "")).strip()
    detail = str(row.get("detail", "")).strip()
    if not title or re.fullmatch(r"\d+[.、]?", title):
        return False
    if re.match(r"^\d+[.、]\s*", title):
        return False
    if title.endswith("：") or title.endswith(":"):
        return False
    if title in {"主要经历", "当前重要物件"}:
        return False
    text = f"{title} {detail}"
    if re.search(r"接触|完成|参与|调查|学会|发现|确认|升级|封锁", title) and not re.search(r"手机|信号|拨号|屏幕|电话|斧|剑|药|瓶|盒|匣|钥匙|书|信|照片|骨|素材|装备|物件|油灯|登记册|任务板|缰绳|行囊|鳞|补给|样本|碎片", title):
        return False
    return bool(re.search(r"手机|信号|拨号|屏幕|电话|斧|剑|药|瓶|盒|匣|钥匙|书|信|照片|骨|素材|装备|物件|油灯|登记册|任务板|缰绳|行囊|鳞|补给|样本|碎片", text))


def is_gallery_cache_asset(asset: dict[str, Any], protected: set[str], inventory_titles: set[str] | None = None, inventory_ids: set[str] | None = None, active_npc_ids: set[str] | None = None, normalized_kind: str = "", title: str = "") -> bool:
    kind = str(asset.get("kind", ""))
    key = str(asset.get("key", ""))
    metadata = asset.get("metadata", {}) if isinstance(asset.get("metadata"), dict) else {}
    title = str(title or metadata.get("title") or readable_asset_name(key, kind))
    if normalized_kind == "scene" and not (kind == "map" or metadata.get("source") == "map_route"):
        return False
    if normalized_name(title) in protected or normalized_name(metadata.get("object_id")) in protected:
        return False
    if kind in {"portrait", "player_portrait", "companion", "companion_portrait"}:
        return False
    if not (kind == "map" or kind.startswith("gallery_")):
        if kind != "npc_portrait":
            return False
    if kind == "npc_portrait":
        return normalized_kind == "npc"
    if normalized_kind == "npc" and active_npc_ids is not None:
        actor_id = stable_actor_entity_id(title or metadata.get("title") or metadata.get("object_id") or key)
        if actor_id in active_npc_ids and normalized_name(title) not in {normalized_name("许守井"), normalized_name("陈航")}:
            return False
    if normalized_kind == "item":
        detail = str(metadata.get("detail") or "")
        analysis = analyze_inventory_item(title, detail)
        entity_id = stable_inventory_entity_id(title, detail, analysis)
        if inventory_ids is not None and entity_id not in inventory_ids:
            return False
        if inventory_titles is not None and normalized_name(title) not in inventory_titles:
            return False
    if re.fullmatch(r"\d+[.、]?", title.strip()):
        return False
    if str(metadata.get("meta", "")).lower() in {"misc", "record"}:
        return False
    return True


def inferred_player_name(player: dict[str, Any], prompt: dict[str, Any]) -> str:
    identity = first_dict(player.get("confirmed_identity"), prompt.get("confirmed_identity"))
    if identity.get("name"):
        return str(identity.get("name"))
    facts = " ".join(str(x) for x in player.get("facts", []) if isinstance(player.get("facts", []), list))
    if "Lee" in facts:
        return "Lee"
    return ""


def character_fallback_profile(campaign_id: str, state: dict[str, Any], scene: dict[str, Any]) -> dict[str, Any]:
    text = f"{campaign_id} {state.get('title', '')} {state.get('genre', '')} {state.get('tone', '')}".lower()
    pressured = bool(scene.get("immediate_pressure"))
    if "coc" in text or "克苏鲁" in text or "调查" in text:
        return {
            "identity": "COC 调查员",
            "progress": {"label": "调查进展", "text": "线索初开，风险升高" if pressured else "案件导入，保持观察", "percent": 38 if pressured else 24},
            "core_stats": [
                {"key": "health", "label": "生命值", "current": 84, "max": 100, "tone": "red", "text": "未受伤"},
                {"key": "sanity", "label": "理智值", "current": 68 if pressured else 78, "max": 100, "tone": "blue", "text": "轻微动摇" if pressured else "稳定"},
                {"key": "stamina", "label": "体力值", "current": 70, "max": 100, "tone": "green", "text": "潮湿疲惫"},
            ],
            "tags": ["谨慎", "COC检定", "潮湿", "线索压力" if pressured else "案件导入"],
            "attributes": [{"key": "observe", "label": "侦", "text": "观察"}, {"key": "library", "label": "图", "text": "资料"}, {"key": "talk", "label": "说", "text": "话术"}, {"key": "stealth", "label": "潜", "text": "隐蔽"}, {"key": "first_aid", "label": "医", "text": "急救"}, {"key": "sanity", "label": "稳", "text": "理智"}],
        }
    if "dnd" in text or "奇幻" in text or "冒险" in text:
        return {
            "identity": "DND 队伍代表",
            "progress": {"label": "冒险进展", "text": "任务展开，局势紧张" if pressured else "第一章，接受委托", "percent": 34 if pressured else 22},
            "core_stats": [
                {"key": "hp", "label": "生命值", "current": 86, "max": 100, "tone": "red", "text": "可战斗"},
                {"key": "focus", "label": "专注值", "current": 74, "max": 100, "tone": "blue", "text": "警戒"},
                {"key": "stamina", "label": "体力值", "current": 80, "max": 100, "tone": "green", "text": "整备中"},
            ],
            "tags": ["警戒", "D20检定", "整备", "任务压力" if pressured else "酒馆待命"],
            "attributes": [{"key": "str", "label": "力", "text": "近战"}, {"key": "dex", "label": "敏", "text": "闪避"}, {"key": "con", "label": "体", "text": "耐久"}, {"key": "int", "label": "智", "text": "知识"}, {"key": "wis", "label": "感", "text": "察觉"}, {"key": "cha", "label": "魅", "text": "交涉"}],
        }
    if "fate" in text or "圣杯" in text or "御主" in text or "从者" in text:
        return {
            "identity": "普通高中生 / 新任御主",
            "progress": {"label": "同步状态", "text": "令咒完整，黑痕扩散" if pressured else "契约未稳，异常同步", "percent": 45 if pressured else 32},
            "core_stats": [
                {"key": "health", "label": "生命值", "current": 72, "max": 100, "tone": "red", "text": "惊惧疲惫" if pressured else "可行动"},
                {"key": "focus", "label": "专注值", "current": 54, "max": 100, "tone": "blue", "text": "受干扰"},
                {"key": "stamina", "label": "体力值", "current": 58, "max": 100, "tone": "green", "text": "奔逃后消耗"},
            ],
            "tags": ["怕死", "令咒完整", "异常同步", "黑痕压力" if pressured else "契约未稳"],
            "attributes": [{"key": "command_spell", "label": "令", "text": "令咒"}, {"key": "leyline", "label": "脉", "text": "灵脉"}, {"key": "escape", "label": "逃", "text": "撤退"}, {"key": "observe", "label": "察", "text": "观察"}, {"key": "box", "label": "匣", "text": "井匣"}, {"key": "contract", "label": "契", "text": "从者"}],
        }
    return {
        "identity": "猎人 / 生态调查",
        "progress": {"label": "成长", "text": "新人阶段，稳步成长", "percent": 42},
        "core_stats": [
            {"key": "health", "label": "生命值", "current": 82, "max": 100, "tone": "red", "text": "状态良好"},
            {"key": "focus", "label": "专注值", "current": 78, "max": 100, "tone": "blue", "text": "稳定"},
            {"key": "stamina", "label": "体力值", "current": 72, "max": 100, "tone": "green", "text": "有消耗"},
        ],
        "tags": ["谨慎", "叙事判定", "生态调查", "任务压力" if pressured else "整备中"],
        "attributes": [{"key": "axe", "label": "斧", "text": "牵制"}, {"key": "sword", "label": "剑", "text": "爆发"}, {"key": "track", "label": "迹", "text": "追踪"}, {"key": "camp", "label": "营", "text": "补给"}, {"key": "trap", "label": "捕", "text": "陷阱"}, {"key": "retreat", "label": "退", "text": "保命"}],
    }


def normalize_frontend_progress(value: Any, fallback: dict[str, Any]) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    current = number_or_none(source.get("current"))
    max_value = number_or_none(source.get("max"))
    if current is not None and max_value and max_value > 0:
        return {"label": source.get("label", fallback.get("label", "进展")), "text": f"{current:g} / {max_value:g}", "percent": max(0, min(100, current / max_value * 100))}
    return {"label": source.get("label") or fallback.get("label", "进展"), "text": source.get("text") or fallback.get("text", ""), "percent": source.get("percent") if isinstance(source.get("percent"), (int, float)) else fallback.get("percent", 0)}


def normalize_frontend_core_stats(value: Any, fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = value if isinstance(value, list) and value else fallback
    normalized = []
    for index, row in enumerate(rows[:3]):
        if not isinstance(row, dict):
            continue
        current = number_or_none(row.get("current"))
        max_value = number_or_none(row.get("max"))
        percent = number_or_none(row.get("percent"))
        if current is None:
            current = percent if percent is not None else 66
        if not max_value:
            max_value = 100
        normalized.append({"key": row.get("key") or f"core_{index}", "label": row.get("label") or "状态", "current": current, "max": max_value, "text": row.get("state") or row.get("text") or "", "tone": row.get("tone") or ["red", "blue", "green"][index % 3]})
    return normalized


def normalize_frontend_tags(value: Any, fallback: list[str]) -> list[str]:
    rows = value if isinstance(value, list) and value else fallback
    labels = []
    for item in rows:
        label = item if isinstance(item, str) else item.get("label") or item.get("name") if isinstance(item, dict) else ""
        if label:
            labels.append(str(label))
    return labels[:8]


def normalize_frontend_attributes(value: Any, fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = value if isinstance(value, list) and value else fallback
    attrs = []
    for index, item in enumerate(rows[:6]):
        if isinstance(item, str):
            attrs.append({"key": f"attr_{index}", "label": item[:1], "text": item})
        elif isinstance(item, dict):
            attrs.append({"key": item.get("key") or f"attr_{index}", "label": item.get("short") or item.get("label") or item.get("key") or "项", "text": item.get("text") or item.get("state") or item.get("rank") or str(item.get("value", ""))})
    return attrs


def number_or_none(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_memory_rows(rows: Any) -> list[dict[str, str]]:
    values = rows if isinstance(rows, list) else [rows] if rows else []
    output = []
    for row in values:
        if isinstance(row, str):
            output.append(split_fact_text(row))
        elif isinstance(row, dict):
            text = row.get("value") or row.get("summary") or row.get("title") or row.get("name") or row.get("text") or row.get("description") or row.get("id") or ""
            parsed = split_fact_text(str(text))
            parsed["tag"] = str(row.get("kind") or row.get("type") or row.get("field") or parsed.get("tag") or "记录")
            output.append(parsed)
    return [row for row in output if row.get("title")]


def split_fact_text(text: str) -> dict[str, str]:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean:
        return {"title": "", "detail": "", "tag": "记录"}
    parts = [part.strip() for part in re.split(r"[；;。]", clean) if part.strip()]
    title = parts[0][:42] if parts else clean[:42]
    return {"title": title, "detail": "；".join(parts[1:])[:160], "tag": "记录"}


def split_clause_rows(value: Any, tag: str = "记录") -> list[dict[str, str]]:
    text = value if isinstance(value, str) else "；".join(str(x) for x in value) if isinstance(value, list) else ""
    rows = []
    for part in re.split(r"[；;。]", text):
        row = split_fact_text(part)
        if row.get("title"):
            row["tag"] = tag
            rows.append(row)
    return rows


def analyze_inventory_item(title: str, detail: str = "") -> dict[str, Any]:
    text = f"{title} {detail}"
    category = "misc"
    role = "record"
    visual_type = "satchel"
    material = ""
    silhouette = ""
    if re.search(r"手机|电话|信号|拨号|屏幕", text):
        category, role, visual_type = "device", "communication_or_clue", "phone"
        material = "glass_and_plastic"
        silhouette = "smartphone"
    elif re.search(r"斩斧|switch\s*axe", text, re.I):
        category, role, visual_type = "weapon", "equipment", "switch_axe"
        material = "bone_and_metal"
        silhouette = "long_transforming_axe_sword"
    elif re.search(r"斧|剑|弓|枪|武器|刀", text):
        category, role, visual_type = "weapon", "equipment", "weapon"
        material = "metal_or_bone"
        silhouette = "weapon"
    elif re.search(r"药|瓶|补给|绷带|食物", text):
        category, role, visual_type = "supply", "resource", "bottle"
        material = "glass_or_wood_crate"
        silhouette = "supply_container"
    elif re.search(r"信|照片|书|文件|登记|地图|记录", text):
        category, role, visual_type = "document", "clue", "paper"
        material = "paper"
        silhouette = "document"
    elif re.search(r"井匣|金属盒|盒|匣", text):
        category, role, visual_type = "ritual_tool", "clue", "sealed_relic_box"
        material = "dark_metal"
        silhouette = "sealed_square_box"
    elif re.search(r"骨|符|匣|盒|钥匙|仪式|占卜", text):
        category, role, visual_type = "ritual_tool", "clue", "ritual_bone"
        material = "bone_or_talisman"
        silhouette = "ritual_object"
    elif re.search(r"泥甲|泥壳|甲片", text):
        category, role, visual_type = "material", "loot_or_trace", "mud_armor_fragment"
        material = "mud_shell"
        silhouette = "broken_armor_fragment"
    elif re.search(r"鳞|羽|素材|碎片|样本|痕", text):
        category, role, visual_type = "material", "loot_or_trace", "material"
        material = "organic_material"
        silhouette = "fragment"
    return {
        "short_name": shorten_item_name(title),
        "category": category,
        "role": role,
        "visual_prompt": {
            "type": visual_type,
            "category": category,
            "role": role,
            "material": material,
            "silhouette": silhouette,
            "source_text": concise_text(text, 120),
        },
    }


def analyze_scene_visual_asset(title: str, detail: str = "") -> dict[str, Any]:
    text = f"{title} {detail}"
    visual_type = "scene_visual"
    material = "environment"
    silhouette = "scene_marker"
    if re.search(r"卷帘|红光|gate|red", text, re.I):
        visual_type = "red_gate_signal"
        material = "metal_door_and_red_light"
        silhouette = "door_crack_light"
    elif re.search(r"楼上|撞击|木门|裂", text):
        visual_type = "broken_door_impact"
        material = "wood_and_shadow"
        silhouette = "cracked_door"
    elif re.search(r"门|door", text, re.I):
        visual_type = "red_gate_signal"
        material = "metal_door_and_red_light"
        silhouette = "door_crack_light"
    elif re.search(r"黑水|倒影|影", text):
        visual_type = "black_water_shadow"
        material = "dark_water_reflection"
        silhouette = "shadow_figures"
    return {
        "type": visual_type,
        "category": "scene_visual",
        "role": "visual_record",
        "material": material,
        "silhouette": silhouette,
        "source_text": concise_text(text, 120),
    }


def stable_inventory_entity_id(title: str, detail: str, analysis: dict[str, Any]) -> str:
    text = f"{title} {detail}"
    if re.search(r"井匣|金属盒|盒面|符纹|盒子", text):
        return "well_box"
    if re.search(r"手机|电话|信号|拨号|屏幕", text):
        return "phone"
    if re.search(r"骨制斩斧|骨斩斧|斩斧", text):
        return "switch_axe"
    if re.search(r"旧红伞|红伞", text):
        return "red_umbrella"
    if re.search(r"药货箱", text):
        return "medicine_crate"
    return safe_segment(analysis.get("short_name") or title or "item")


def merge_detail_text(current: str, new: str, limit: int = 180) -> str:
    parts = []
    seen = set()
    for value in re.split(r"[；;。]\s*", f"{current}；{new}"):
        item = value.strip()
        if not item:
            continue
        key = normalized_name(item)
        if key in seen:
            continue
        seen.add(key)
        parts.append(item)
    return concise_text("；".join(parts), limit)


def shorten_item_name(name: str) -> str:
    text = re.sub(r"[《》「」\"']", "", str(name or "")).strip()
    replacements = [("蛇身骨质占卜", "骨占卜"), ("骨制斩斧", "骨斩斧"), ("大怪鸟碎羽", "碎羽"), ("金属盒", "井匣"), ("旧红伞", "红伞")]
    for source, target in replacements:
        if source in text:
            return target
    if re.search(r"手机|电话|信号|拨号|屏幕", text):
        return "手机"
    if re.search(r"井匣|盒面|符纹|盒子|金属盒", text):
        return "井匣"
    text = re.sub(r"(当前重要物件|主要经历|装备|物品|线索|记录)[:：]?", "", text).strip()
    if "药货箱" in text:
        return "药货箱"
    if "药油" in text:
        return "药油"
    if "防泥片" in text:
        return "防泥片"
    if len(text) <= 6:
        return text or "物品"
    for token in re.split(r"[、,，/ ]+", text):
        token = token.strip()
        if 1 < len(token) <= 6:
            return token
    return text[:6]


def gallery_filters_for_campaign(campaign_id: str, state: dict[str, Any]) -> list[dict[str, str]]:
    text = f"{campaign_id} {state.get('genre', '')} {state.get('title', '')}".lower()
    if "fate" in text or "圣杯" in text:
        rows = [("all", "全部"), ("cg", "CG"), ("servant", "从者"), ("master", "御主"), ("npc", "NPC"), ("scene", "场景"), ("item", "物品")]
    elif "coc" in text or "克苏鲁" in text:
        rows = [("all", "全部"), ("cg", "CG"), ("clue", "线索"), ("npc", "NPC"), ("scene", "地点"), ("document", "文献"), ("anomaly", "异常")]
    elif "dnd" in text:
        rows = [("all", "全部"), ("cg", "CG"), ("character", "角色"), ("monster", "怪物"), ("scene", "地点"), ("item", "装备"), ("quest", "任务")]
    else:
        rows = [("all", "全部"), ("cg", "CG"), ("monster", "怪物"), ("npc", "NPC"), ("scene", "场景"), ("item", "物品")]
    return [{"key": key, "label": label} for key, label in rows]


def gallery_allowed_filter_ids(filters: list[dict[str, str]]) -> set[str]:
    return {str(row.get("key") or "") for row in filters if str(row.get("key") or "") and str(row.get("key")) != "all"}


def coerce_gallery_kind_to_allowed(kind: Any, allowed: set[str]) -> str:
    raw = str(kind or "").lower()
    if "gallery_npc" in raw:
        return ""
    if any(token in raw for token in ("generated_cg", "gallery_image", "formal_cg", "cg_image")):
        return "cg" if "cg" in allowed else ""
    value = normalize_frontend_gallery_kind(kind)
    if value in allowed:
        return value
    aliases = {
        "location": "scene",
        "map": "scene",
        "ecology": "monster",
        "weapon": "item",
        "supply": "item",
        "material": "item",
        "ritual_tool": "item",
    }
    value = aliases.get(value, value)
    if value in allowed:
        return value
    if value == "character" and "npc" in allowed:
        return "npc"
    return ""


def normalize_frontend_gallery_kind(kind: Any) -> str:
    value = str(kind or "").lower()
    if any(token in value for token in ("cg", "generated_cg", "gallery_image", "formal_cg", "剧情图", "生图")):
        return "cg"
    if "servant" in value or "从者" in value:
        return "servant"
    if "master" in value or "御主" in value:
        return "master"
    if "document" in value or "文献" in value:
        return "document"
    if "clue" in value or "线索" in value:
        return "clue"
    if "anomaly" in value or "异常" in value:
        return "anomaly"
    if "map" in value or "scene" in value or "location" in value:
        return "scene"
    if "npc" in value or "portrait" in value:
        return "npc"
    if "monster" in value or "ecology" in value:
        return "monster"
    if "quest" in value or "任务" in value:
        return "quest"
    if "character" in value or "角色" in value:
        return "character"
    if any(token in value for token in ("item", "weapon", "supply", "material", "ritual_tool", "equipment", "物品", "装备", "补给", "材料", "仪式")):
        return "item"
    return ""


def readable_asset_name(key: str, kind: str) -> str:
    text = re.sub(r"^[^:]+:", "", str(key or kind or "asset"))
    text = re.sub(r":v\d+$", "", text).replace("_", " ").strip()
    return concise_text(text or kind, 18)


def dedupe_frontend_assets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    by_key: dict[str, dict[str, Any]] = {}
    output = []
    for row in rows:
        if row.get("kind") == "scene":
            key = str(row.get("key") or f"scene:{normalized_name(row.get('title'))}:{row.get('created_at')}")
        else:
            key = f"{row.get('kind')}:{normalized_name(row.get('title'))}" if row.get("title") else str(row.get("key") or row.get("kind"))
        if key in seen:
            existing = by_key.get(key)
            if existing:
                for field in ("cached_url", "visual_prompt", "source_object_id", "created_at"):
                    if row.get(field) and not existing.get(field):
                        existing[field] = row[field]
                if row.get("detail"):
                    existing["detail"] = merge_detail_text(existing.get("detail", ""), row.get("detail", ""))
                if row.get("status") and not existing.get("status"):
                    existing["status"] = row["status"]
            continue
        seen.add(key)
        by_key[key] = row
        output.append(row)
    return output


def mark_frontend_scene_archive_state(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    current_seen = False
    output = []
    for row in rows:
        if row.get("kind") == "scene" and row.get("cached_url"):
            if current_seen:
                row = {**row, "status": "archived", "archived": True}
            else:
                row = {**row, "status": "current", "archived": False}
                current_seen = True
        output.append(row)
    return output


def concise_text(value: Any, limit: int = 42) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit] + ("..." if len(text) > limit else "")

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
    manifest.setdefault("campaign_id", campaign_id)
    manifest.setdefault("asset_seed", campaign_asset_seed(campaign_id))
    manifest.setdefault("assets", {})[key] = {
        "path": rel_path.as_posix(),
        "kind": str(payload.get("kind") or subdir),
        "seed": str(payload.get("seed") or key),
        "asset_seed": str(payload.get("asset_seed") or campaign_asset_seed(campaign_id)),
        "style": str(payload.get("style") or "canvas_pixel"),
        "generator_version": int(payload.get("generator_version") or 1),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        manifest["assets"][key]["metadata"] = metadata
    write_json(asset_manifest_path(campaign_id), manifest)
    return asset_lookup(campaign_id, key)



def safe_asset_target(campaign_id: str, rel_path: str) -> Path:
    if not rel_path:
        raise RuntimeError("asset path is empty")
    root = (CAMPAIGNS_DIR / safe_segment(campaign_id) / "assets").resolve()
    target = (CAMPAIGNS_DIR / safe_segment(campaign_id) / rel_path).resolve()
    if root not in target.parents and target != root:
        raise RuntimeError("asset path escapes campaign assets")
    if target.suffix.lower() != ".png":
        raise RuntimeError("only PNG assets can be removed")
    return target


def delete_asset(payload: dict[str, Any]) -> dict[str, Any]:
    campaign_id = str(payload.get("campaign_id") or "").strip() or MemoryStore().resolve_campaign_id(None)
    key = str(payload.get("key") or "").strip()
    if not key:
        raise RuntimeError("asset key is required")
    manifest = load_asset_manifest(campaign_id)
    entry = manifest.get("assets", {}).pop(key, None)
    removed_file = False
    warnings: list[str] = []
    if isinstance(entry, dict) and entry.get("path"):
        try:
            target = safe_asset_target(campaign_id, str(entry.get("path", "")))
            if target.exists():
                target.unlink()
                removed_file = True
        except Exception as exc:
            warnings.append(str(exc))
    write_json(asset_manifest_path(campaign_id), manifest)
    return {"ok": True, "campaign_id": campaign_id, "key": key, "removed_file": removed_file, "warnings": warnings}


def rebuild_assets(payload: dict[str, Any]) -> dict[str, Any]:
    campaign_id = str(payload.get("campaign_id") or "").strip() or MemoryStore().resolve_campaign_id(None)
    kind = str(payload.get("kind") or "").strip()
    manifest = load_asset_manifest(campaign_id)
    removed: list[str] = []
    warnings: list[str] = []
    for key, entry in list(manifest.get("assets", {}).items()):
        if kind and str(entry.get("kind", "")) != kind:
            continue
        if isinstance(entry, dict) and entry.get("path"):
            try:
                target = safe_asset_target(campaign_id, str(entry.get("path", "")))
                if target.exists():
                    target.unlink()
            except Exception as exc:
                warnings.append(f"{key}: {exc}")
        manifest.get("assets", {}).pop(key, None)
        removed.append(key)
    write_json(asset_manifest_path(campaign_id), manifest)
    return {"ok": True, "campaign_id": campaign_id, "kind": kind, "removed": removed, "warnings": warnings}
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
    env["PYTHONUTF8"] = "1"
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
        errors="strict",
        capture_output=True,
    )
    JOB.finish(completed)





def new_campaign_defaults_payload() -> dict[str, Any]:
    return {"ok": True, "defaults": default_rule_bundle(), "modes": ai_mode_options()}


def ai_mode_options() -> list[dict[str, str]]:
    return [
        {"id": "v4_director_chatgpt_api_actor", "label": "Deepseek V4 \u5bfc\u6f14 + ChatGPT API \u6f14\u5458\u751f\u6210", "director": "deepseek_v4", "actor": "chatgpt_api"},
        {"id": "v4_api_chatgpt_conversation", "label": "Deepseek V4 API + ChatGPT \u5bf9\u8bdd\u8054\u52a8", "director": "deepseek_v4", "actor": "chatgpt_conversation"},
        {"id": "deepseek_v4_only", "label": "\u5168\u7a0b\u4ec5\u4f7f\u7528 Deepseek V4 API", "director": "deepseek_v4", "actor": "deepseek_v4"},
        {"id": "chatgpt_only", "label": "\u5168\u7a0b\u4ec5\u4f7f\u7528 ChatGPT AI", "director": "chatgpt", "actor": "chatgpt"},
    ]

def default_rule_bundle() -> dict[str, Any]:
    categories = [
        {"id": "architecture", "title": "\u7cfb\u7edf\u67b6\u6784\u89c4\u5219", "files": ["model_layer_contract_rules.md", "codex_system_architecture_rules.md"]},
        {"id": "image", "title": "\u751f\u56fe\u89c4\u5219", "files": ["chatgpt_image_rules.md"]},
        {"id": "codex_visual", "title": "Codex \u89c6\u89c9\u8d44\u4ea7\u89c4\u5219", "files": ["visual_asset_protocol.md", "canvas_asset_generation_rules.md", "gallery_asset_rules.md"]},
        {"id": "dialogue", "title": "\u5bf9\u8bdd\u89c4\u5219", "files": ["chatgpt_host_prompt.md", "chatgpt_npc_voice_rules.md"]},
        {"id": "style", "title": "\u884c\u6587\u89c4\u5219", "files": ["chatgpt_style_rules.md"]},
        {"id": "npc", "title": "NPC / \u602a\u7269\u8bbe\u5b9a\u89c4\u5219", "files": ["chatgpt_monster_rules.md"]},
        {"id": "director_schema", "title": "V4 \u7ed3\u6784\u8f93\u51fa\u89c4\u5219", "files": ["character_card_json_rules.md"]},
        {"id": "codex_qa", "title": "Codex \u8d28\u68c0\u4e0e\u7f13\u5b58\u89c4\u5219", "files": ["ai_flavor_check_rules.md", "asset_cache_lifecycle_rules.md"]},
    ]
    rows = []
    for category in categories:
        parts = []
        used = []
        for filename in category["files"]:
            path = PROMPTS_DIR / filename
            if path.exists():
                used.append(filename)
                parts.append(f"## {filename}\n{read_text_auto(path)}".strip())
        rows.append({"id": category["id"], "title": category["title"], "files": used, "content": "\n\n".join(parts)})
    return {"categories": rows}

def create_campaign_smart_payload(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or "").strip()
    template = str(payload.get("template") or "custom").strip().lower()
    ai_mode = str(payload.get("ai_mode") or "v4_director_chatgpt_api_actor").strip()
    user_prompt = str(payload.get("user_prompt") or "").strip()
    custom_rules = str(payload.get("custom_rules") or "").strip()
    if not name:
        raise RuntimeError("name is required")
    if not user_prompt:
        raise RuntimeError("user_prompt is required")
    if template not in {"fate", "dnd", "coc", "custom"}:
        raise RuntimeError("template must be fate, dnd, coc, or custom")
    valid_modes = {row["id"] for row in ai_mode_options()}
    if ai_mode not in valid_modes:
        raise RuntimeError("invalid ai mode")

    campaign_id = unique_campaign_id(name)
    paths = MemoryStore().init_campaign(campaign_id, name)
    apply_campaign_template(paths.root, name, template)
    analysis = summarize_campaign_prompt(name, template, user_prompt)
    routing = classify_custom_rules(custom_rules)
    generated_project = f"TRPG {name}"
    generated_conversation = f"{name} \u56fa\u5b9a\u5bf9\u8bdd"
    MemoryStore().update_chatgpt_binding(campaign_id, generated_project, generated_conversation)
    select_campaign(campaign_id)
    apply_smart_campaign_config(paths.root, {
        "name": name,
        "template": template,
        "ai_mode": ai_mode,
        "user_prompt": user_prompt,
        "custom_rules": custom_rules,
        "analysis": analysis,
        "routing": routing,
        "generated_project": generated_project,
        "generated_conversation": generated_conversation,
    })
    return {"ok": True, "campaign_id": campaign_id, "analysis": analysis, "routing": routing, "status": status_payload()}


def unique_campaign_id(name: str) -> str:
    base = re.sub(r"[^a-z0-9_.-]+", "_", name.lower()).strip("._-")
    if not base:
        base = "campaign"
    stamp = time.strftime("%Y%m%d%H%M%S", time.localtime())
    candidate = f"{base}_{stamp}"
    root = CAMPAIGNS_DIR / candidate
    index = 2
    while root.exists():
        candidate = f"{base}_{stamp}_{index}"
        root = CAMPAIGNS_DIR / candidate
        index += 1
    return candidate


def summarize_campaign_prompt(name: str, template: str, user_prompt: str) -> dict[str, str]:
    client = DeepSeekClient()
    if client.is_configured():
        try:
            raw = client.complete_json(
                "Return concise JSON for a TRPG campaign setup. Keys: genre, tone, premise.",
                json.dumps({"name": name, "template": template, "prompt": user_prompt}, ensure_ascii=False),
            )
            data = extract_json_object(raw)
            return {
                "genre": stringify_brief(data.get("genre") or infer_genre(user_prompt, template), 80),
                "tone": stringify_brief(data.get("tone") or infer_tone(user_prompt, template), 100),
                "premise": stringify_brief(data.get("premise") or user_prompt, 220),
                "source": "deepseek_v4",
            }
        except Exception:
            pass
    return {"genre": infer_genre(user_prompt, template), "tone": infer_tone(user_prompt, template), "premise": stringify_brief(user_prompt, 220), "source": "local_heuristic"}


def infer_genre(text: str, template: str) -> str:
    lower = text.lower()
    if template == "dnd" or any(word in lower for word in ("dragon", "dungeon", "\u9b54\u6cd5", "\u5730\u4e0b\u57ce", "\u738b\u56fd", "\u7cbe\u7075")):
        return "\u5947\u5e7b\u5192\u9669"
    if template == "coc" or any(word in lower for word in ("coc", "\u514b\u82cf\u9c81", "\u8c03\u67e5", "\u7406\u667a", "\u90aa\u795e", "\u5bc6\u6559")):
        return "\u8c03\u67e5\u6050\u6016"
    if template == "fate" or any(word in lower for word in ("fate", "\u5723\u676f", "\u5fa1\u4e3b", "\u4ece\u8005", "\u82f1\u7075", "\u4ee4\u5492")):
        return "FATE \u4e9a\u79cd\u5723\u676f\u6218\u4e89 / \u73b0\u4ee3\u57ce\u5e02\u9b54\u672f\u4e8b\u6545"
    if any(word in lower for word in ("\u730e\u4eba", "\u602a\u7269", "\u751f\u6001", "\u72e9\u730e", "\u516c\u4f1a")):
        return "\u751f\u6001\u72e9\u730e / \u5192\u9669\u8c03\u67e5"
    if any(word in lower for word in ("\u8d5b\u535a", "\u592a\u7a7a", "\u661f\u8230", "ai", "\u4e49\u4f53")):
        return "\u79d1\u5e7b\u5192\u9669"
    return "\u81ea\u5b9a\u4e49\u8dd1\u56e2"

def infer_tone(text: str, template: str) -> str:
    lower = text.lower()
    tones = []
    for word, label in (("\u9ed1\u6697", "\u9ed1\u6697"), ("\u6050\u6016", "\u538b\u8feb"), ("\u60ac\u7591", "\u60ac\u7591"), ("\u8f7b\u677e", "\u8f7b\u677e"), ("\u7535\u5f71", "\u7535\u5f71\u5316"), ("\u786c\u6838", "\u786c\u6838"), ("\u8352\u91ce", "\u8352\u91ce"), ("\u653f\u6cbb", "\u590d\u6742\u535a\u5f08"), ("\u4fdd\u547d", "\u8c28\u614e\u6c42\u751f")):
        if word in lower:
            tones.append(label)
    if not tones:
        tones = ["\u82f1\u96c4\u5192\u9669", "\u63a2\u7d22"] if template == "dnd" else ["\u8c03\u67e5", "\u5fc3\u7406\u538b\u529b"] if template == "coc" else ["Fate\u5473", "\u73b0\u4ee3\u57ce\u5e02", "\u5931\u63a7\u4e8b\u6545"] if template == "fate" else ["\u6c89\u6d78", "\u53ef\u63a8\u8fdb"]
    return "\u3001".join(dict.fromkeys(tones))

def classify_custom_rules(custom_rules: str) -> dict[str, Any]:
    if not custom_rules:
        return {"director_rules": [], "actor_rules": [], "source": "empty"}
    client = DeepSeekClient()
    if client.is_configured():
        try:
            raw = client.complete_json(
                "Classify user TRPG rules into director_rules and actor_rules JSON arrays. Director rules control plot, memory, pacing, mechanics. Actor rules control prose, dialogue, images, NPC voice.",
                custom_rules,
            )
            data = extract_json_object(raw)
            return {"director_rules": list(data.get("director_rules") or []), "actor_rules": list(data.get("actor_rules") or []), "source": "deepseek_v4"}
        except Exception:
            pass
    director = []
    actor = []
    for line in split_lines(custom_rules):
        lower = line.lower()
        if any(word in lower for word in ("\u5267\u60c5", "\u8282\u594f", "\u89c4\u5219", "\u68c0\u5b9a", "\u8bb0\u5fc6", "\u79d8\u5bc6", "\u96be\u5ea6", "\u5bfc\u6f14")):
            director.append(line)
        else:
            actor.append(line)
    return {"director_rules": director, "actor_rules": actor, "source": "local_heuristic"}

def apply_smart_campaign_config(root: Path, config: dict[str, Any]) -> None:
    profile_path = root / "campaign_profile.json"
    direction_path = root / "campaign_direction.json"
    style_path = root / "style_profile.json"
    image_path = root / "image_profile.json"
    npc_path = root / "npc_profiles.json"
    profile = read_json(profile_path)
    direction = read_json(direction_path)
    style = read_json(style_path)
    image = read_json(image_path)
    npc = read_json(npc_path)
    analysis = config.get("analysis", {})
    routing = config.get("routing", {})
    mode = next((row for row in ai_mode_options() if row["id"] == config.get("ai_mode")), ai_mode_options()[0])
    profile.update({
        "title": config.get("name", profile.get("title", "")),
        "genre": analysis.get("genre", ""),
        "tone": analysis.get("tone", ""),
        "initial_prompt": config.get("user_prompt", ""),
        "ai_mode": mode,
        "prompt_routing": {
            "director_receives": ["campaign_profile", "campaign_direction", "director_rules", "memory"],
            "actor_receives": ["chatgpt_host_prompt", "style_rules", "dialogue_rules", "image_rules", "actor_rules"],
            "custom_rule_classification": routing,
        },
    })
    direction.setdefault("background_direction", []).append(analysis.get("premise", ""))
    direction.setdefault("theme_and_tone", []).extend([analysis.get("genre", ""), analysis.get("tone", "")])
    direction.setdefault("pace_rules", []).extend(routing.get("director_rules", []))
    style.setdefault("prose_style", []).extend(routing.get("actor_rules", []))
    image.setdefault("image_generation_rules", []).append("Use merged canvas and image rules from default rule bundle; cache generated PNG assets locally.")
    npc.setdefault("voice_rules", {})["custom_actor_rules"] = routing.get("actor_rules", [])
    write_json(profile_path, profile)
    write_json(direction_path, direction)
    write_json(style_path, style)
    write_json(image_path, image)
    write_json(npc_path, npc)

def canvas_rules_payload() -> dict[str, Any]:
    path = PROMPTS_DIR / "canvas_asset_generation_rules.md"
    return {
        "ok": True,
        "path": str(path),
        "rules": read_text_auto(path) if path.exists() else "",
    }

def rules_payload(name: str = "", query: str = "") -> dict[str, Any]:
    if name:
        if "/" in name or "\\" in name or not name.endswith(".md"):
            raise RuntimeError("invalid rule name")
        path = PROMPTS_DIR / name
        return {
            "ok": True,
            "name": name,
            "path": str(path),
            "content": read_text_auto(path) if path.exists() else "",
            "exists": path.exists(),
        }
    rules = []
    matches = []
    needle = query.strip().lower()
    for path in sorted(PROMPTS_DIR.glob("*.md")):
        content = read_text_auto(path)
        title = path.stem.replace("_", " ")
        for line in content.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        item = {
            "name": path.name,
            "title": title,
            "path": str(path),
            "size": path.stat().st_size,
        }
        rules.append(item)
        if needle and needle in f"{path.name} {title} {content}".lower():
            matches.append({**item, "snippets": rule_snippets(content, query, 3)})
    return {"ok": True, "rules": rules, "query": query, "matches": matches}


PROMPT_INSPECTOR_GROUPS = [
    {
        "id": "contract",
        "title": "模型分层契约",
        "files": ["model_layer_contract_rules.md"],
    },
    {
        "id": "director",
        "title": "DeepSeek V4 导演层",
        "files": ["v4_director_prompt.md", "v4_campaign_context_prompt.md", "v4_light_action_rules.md", "character_card_json_rules.md", "v4_audit_prompt.md"],
    },
    {
        "id": "actor",
        "title": "ChatGPT 演员层",
        "files": ["chatgpt_host_prompt.md", "chatgpt_style_rules.md", "chatgpt_image_rules.md", "chatgpt_npc_voice_rules.md", "chatgpt_monster_rules.md"],
    },
    {
        "id": "visual",
        "title": "Codex 视觉资产规则",
        "files": ["visual_asset_protocol.md", "canvas_asset_generation_rules.md", "gallery_asset_rules.md"],
    },
    {
        "id": "codex",
        "title": "Codex 本地工程层",
        "files": ["codex_system_architecture_rules.md", "codex_computer_use_prompt.md", "encoding_rules.md", "campaign_data_lifecycle_rules.md", "frontend_interaction_rules.md", "ai_flavor_check_rules.md", "asset_cache_lifecycle_rules.md"],
    },
]


def prompt_inspector_payload(campaign_id: str = "") -> dict[str, Any]:
    resolved = MemoryStore().resolve_campaign_id(campaign_id or None)
    groups = []
    for group in PROMPT_INSPECTOR_GROUPS:
        files = []
        for filename in group["files"]:
            path = PROMPTS_DIR / filename
            cn_path = PROMPTS_DIR / f"{Path(filename).stem}_CN.md"
            files.append({
                "name": filename,
                "exists": path.exists(),
                "path": str(path),
                "content": read_text_auto(path) if path.exists() else "",
                "cn": {
                    "name": cn_path.name,
                    "exists": cn_path.exists(),
                    "path": str(cn_path),
                    "content": read_text_auto(cn_path) if cn_path.exists() else "",
                },
            })
        groups.append({**group, "files": files})
    outbox = safe_outbox_snapshot(resolved)
    raw = raw_output_payload(resolved)
    return {
        "ok": True,
        "campaign_id": resolved,
        "groups": groups,
        "rules": rules_payload().get("rules", []),
        "outbox": outbox,
        "parsed_raw_output": raw,
    }


def rule_snippets(content: str, query: str, limit: int = 3) -> list[str]:
    needle = query.strip().lower()
    if not needle:
        return []
    rows: list[str] = []
    for line in content.splitlines():
        clean = line.strip()
        if needle in clean.lower():
            rows.append(clean[:180])
        if len(rows) >= limit:
            break
    if rows:
        return rows
    index = content.lower().find(needle)
    if index < 0:
        return []
    return [content[max(0, index - 60):index + len(query) + 100].replace("\n", " ").strip()]

def init_campaign_payload(payload: dict[str, Any]) -> dict[str, Any]:
    campaign_id = str(payload.get("campaign_id") or "").strip()
    name = str(payload.get("name") or "").strip()
    template = str(payload.get("template") or "custom").strip().lower()
    if not campaign_id:
        raise RuntimeError("campaign_id is required")
    if not name:
        raise RuntimeError("name is required")
    if template not in {"fate", "dnd", "coc", "custom"}:
        raise RuntimeError("template must be fate, dnd, coc, or custom")
    paths = MemoryStore().init_campaign(campaign_id, name)
    apply_campaign_template(paths.root, name, template)
    return {"ok": True, "campaign_id": campaign_id, "template": template, "root": str(paths.root), "status": status_payload()}


def apply_campaign_template(root: Path, name: str, template: str) -> None:
    if template == "custom":
        return
    profile_path = root / "campaign_profile.json"
    direction_path = root / "campaign_direction.json"
    style_path = root / "style_profile.json"
    character_path = root / "character_prompt.json"
    profile = read_json(profile_path)
    direction = read_json(direction_path)
    style = read_json(style_path)
    character = read_json(character_path)
    if template == "fate":
        profile.update({
            "title": profile.get("title") or name,
            "genre": "FATE \u4e9a\u79cd\u5723\u676f\u6218\u4e89",
            "tone": "Fate\u5473\u3001\u73b0\u4ee3\u57ce\u5e02\u3001\u6709\u9650\u89c6\u89d2\u3001\u5931\u63a7\u4e8b\u6545\u3001\u4fe1\u606f\u788e\u7247",
            "world_rules": [
                "\u4f7f\u7528 Fate \u6838\u5fc3\u6982\u5ff5\uff1a\u5fa1\u4e3b\u3001\u4ece\u8005\u3001\u4ee4\u5492\u3001\u804c\u9636\u3001\u771f\u540d\u3001\u5b9d\u5177\u3001\u9b54\u672f\u56de\u8def\u3001\u7075\u8109\u3001\u5723\u676f\u6218\u4e89\u3001\u9b54\u672f\u534f\u4f1a\u3001\u795e\u79d8\u906e\u853d\u3001\u82f1\u7075\u5ea7\u3002",
                "\u89d2\u8272\u3001\u57ce\u5e02\u3001\u5723\u676f\u6218\u4e89\u89c4\u5219\u548c\u654c\u65b9\u9635\u8425\u5168\u90e8\u539f\u521b\uff1b\u4e0d\u8ba9\u6b63\u4f5c\u4eba\u7269\u767b\u573a\u6216\u62a2\u4e3b\u7ebf\u3002",
                "\u73b0\u4ee3\u4e2d\u56fd\u67b6\u7a7a\u57ce\u5e02\u4e2d\u7684\u4e9a\u79cd\u5723\u676f\u6218\u4e89\uff0c\u80dc\u5229\u6761\u4ef6\u88ab\u9690\u85cf\uff0c\u771f\u76f8\u901a\u8fc7\u4e8b\u6545\u3001\u75d5\u8ff9\u3001\u68a6\u5883\u3001NPC \u53cd\u5e94\u548c\u9b54\u672f\u6b8b\u7559\u9010\u6b65\u66b4\u9732\u3002",
            ],
            "narration_rules": [
                "\u53ea\u8f93\u51fa\u8dd1\u56e2\u6b63\u6587\u3001\u5fc5\u8981\u72b6\u6001\u548c\u5173\u952e\u9009\u62e9\uff1b\u4e0d\u5c55\u793a\u601d\u7ef4\u94fe\uff0c\u4e0d\u89e3\u91ca\u5199\u4f5c\u65b9\u6cd5\u3002",
                "\u4e0d\u7528\u65c1\u767d\u89e3\u91ca\u5371\u9669\uff0c\u8ba9\u96e8\u6c34\u3001\u95e8\u69db\u3001\u706f\u3001\u624b\u673a\u3001\u4e66\u5305\u3001\u9ed1\u6c34\u3001\u94dc\u94b1\u548c\u4eba\u7269\u52a8\u4f5c\u63a8\u52a8\u73b0\u573a\u3002",
                "NPC \u4e0d\u8bf4\u8bbe\u5b9a\u8bf4\u660e\uff0c\u4fe1\u606f\u5fc5\u987b\u4ece\u6050\u60e7\u3001\u6025\u8e81\u3001\u56de\u907f\u3001\u4e8b\u6545\u548c\u88ab\u6253\u65ad\u7684\u534a\u53e5\u8bdd\u91cc\u6f0f\u51fa\u6765\u3002",
                "Lee \u662f 16 \u5c81\u666e\u901a\u9ad8\u4e2d\u751f\uff0c\u4f1a\u614c\u3001\u4f1a\u6015\u6b7b\u3001\u4f1a\u72af\u9519\uff1b\u5224\u65ad\u5e94\u8be5\u662f\u4ece\u6050\u60e7\u91cc\u6324\u51fa\u6765\u7684\u3002",
            ],
            "hard_limits": [
                "\u4e0d\u63d0\u524d\u8bf4\u660e\u771f\u5b9e\u5723\u676f\u89c4\u5219\u6216\u80dc\u5229\u6761\u4ef6\u3002",
                "\u4e0d\u8ba9 Assassin \u50cf\u5bfc\u5e08\u4e00\u6837\u9891\u7e41\u8bf4\u91d1\u53e5\uff0c\u66f4\u591a\u7528\u52a8\u4f5c\u3001\u7ad9\u4f4d\u3001\u6c89\u9ed8\u548c\u4ee3\u4ef7\u8868\u73b0\u3002",
                "\u4e0d\u628a\u9009\u62e9\u5199\u6210\u5e73\u8861\u653b\u7565\u83dc\u5355\uff0c\u9009\u9879\u8981\u662f\u73b0\u573a\u903c\u51fa\u6765\u7684\u574f\u529e\u6cd5\u3002",
            ],
        })
        profile["mechanics"] = {"use_dice": False, "dice_system": "\u53d9\u4e8b\u5224\u5b9a / \u5fc5\u8981\u65f6\u9690\u6027\u96be\u5ea6", "use_combat_rules": True, "stats_style": "narrative_status"}
        direction["background_direction"] = [
            "\u6545\u4e8b\u53d1\u751f\u5728\u73b0\u4ee3\u4e2d\u56fd\u67b6\u7a7a\u5185\u9646\u57ce\u5e02\u9675\u5ddd\u5e02\uff1a\u65e7\u57ce\u533a\u3001\u591c\u5e02\u3001\u5b66\u6821\u3001\u534a\u5730\u4e0b\u7f51\u5427\u3001\u83dc\u5e02\u573a\u3001\u8001\u5c45\u6c11\u697c\u3001\u65e7\u7801\u5934\u548c\u88ab\u57ce\u5e02\u5efa\u8bbe\u8986\u76d6\u7684\u7075\u8109\u8282\u70b9\u3002",
            "\u9675\u5ddd\u7684\u795e\u79d8\u662f Fate \u5f0f\u5730\u65b9\u9b54\u672f\u57fa\u76d8\uff1a\u6709\u4f20\u627f\u3001\u6709\u4ee3\u4ef7\u3001\u6709\u65ad\u5c42\u3001\u6709\u5931\u63a7\u98ce\u9669\uff0c\u4e0d\u5199\u6210\u4fee\u4ed9\u6216\u7384\u5e7b\u3002",
            "Lee \u548c\u9648\u822a\u4ece\u84dd\u9cb8\u7f51\u5496\u9003\u5230\u83dc\u5e02\u573a\u9644\u8fd1\u5c0f\u5356\u90e8\u95e8\u53e3\uff0c\u8bb8\u5b88\u4e95\u51fa\u73b0\uff0c\u9ed1\u6c34\u3001\u4e95\u5323\u3001\u83dc\u5e02\u573a\u95e8\u7f1d\u7ea2\u5149\u6b63\u5728\u4e92\u76f8\u547c\u5e94\u3002",
        ]
        direction["main_tension"] = [
            "\u4e9a\u79cd\u5723\u676f\u4eea\u5f0f\u7684\u771f\u5b9e\u80dc\u5229\u6761\u4ef6\u88ab\u9690\u85cf\uff0c\u5723\u676f\u53ef\u80fd\u5728\u7b5b\u9009\u5bb9\u5668\u6216\u94a5\u5319\u3002",
            "Lee \u8981\u6d3b\u4e0b\u53bb\uff0c\u4f46\u8fd9\u4e2a\u6267\u5ff5\u4f1a\u6162\u6162\u53d8\u6210\uff1a\u6211\u60f3\u6d3b\u4e0b\u53bb\uff0c\u90a3\u522b\u4eba\u5462\uff1f",
        ]
        direction["theme_and_tone"] = ["Fate\u5473", "\u73b0\u4ee3\u57ce\u5e02", "\u4e9a\u79cd\u5723\u676f", "\u6709\u9650\u89c6\u89d2", "\u5931\u63a7\u4e8b\u6545", "\u4fe1\u606f\u788e\u7247"]
        direction["pace_rules"] = ["\u964d\u4f4e\u63a8\u8fdb\u901f\u5ea6\uff0c\u4f18\u5148\u5199\u73b0\u573a\u538b\u529b\u3001\u8eab\u4f53\u53cd\u5e94\u3001\u4eba\u7269\u5e72\u6270\u548c\u88ab\u6253\u65ad\u7684\u4fe1\u606f\u3002", "\u5173\u952e\u9009\u62e9\u624d\u7ed9 2-5 \u4e2a\u52a8\u4f5c\u5316\u9009\u9879\uff0c\u9009\u9879\u8981\u6709\u4ee3\u4ef7\u548c\u574f\u529e\u6cd5\u611f\u3002"]
        style["prose_style"] = ["\u5c11\u89e3\u91ca\uff0c\u591a\u8ba9\u73b0\u573a\u8bf4\u8bdd\u3002", "\u4e0d\u7528\u6d41\u6c34\u8d26\u548c\u4efb\u52a1\u6d41\u7a0b\u53e3\u543b\u3002", "\u7ec6\u8282\u5fc5\u987b\u5f71\u54cd\u884c\u52a8\uff0c\u4e0d\u53ea\u505a\u6c14\u6c1b\u88c5\u9970\u3002"]
        style["avoid_patterns"] = ["\u8fd9\u8bf4\u660e", "\u8fd9\u610f\u5473\u7740", "Lee \u610f\u8bc6\u5230", "\u771f\u6b63\u7684\u95ee\u9898\u4e0d\u662f", "\u6f02\u4eae\u4f46\u5047\u7684\u91d1\u53e5"]
        character["confirmed_identity"] = {"name": "Lee", "gender": "\u7537", "age": 16, "role": "\u666e\u901a\u9ad8\u4e2d\u751f / \u65b0\u4efb\u5fa1\u4e3b", "companion": "Assassin"}
        character["personality_and_voice"] = ["\u5c11\u5e74\u611f\u3001\u5634\u786c\u3001\u4f1a\u614c\u3001\u6015\u6b7b\uff0c\u7b2c\u4e00\u53cd\u5e94\u662f\u627e\u9000\u8def\u548c\u51fa\u53e3\u3002", "\u4e0d\u559c\u6b22\u901e\u82f1\u96c4\uff0c\u4f46\u88ab\u903c\u5230\u4e0d\u80fd\u9000\u65f6\u4f1a\u54ac\u7259\u505a\u4e00\u4ef6\u81ea\u5df1\u4e5f\u5bb3\u6015\u7684\u4e8b\u3002"]
        character["abilities_and_limits"] = ["\u539f\u672c\u4e0d\u662f\u9b54\u672f\u5e08\u3002\u4ee4\u5492\u8f6c\u79fb\u540e\u5bf9\u7075\u8109\u3001\u4ece\u8005\u6b8b\u7559\u3001\u4e95\u5323\u548c\u65e7\u7b26\u7eb9\u51fa\u73b0\u5f02\u5e38\u540c\u6b65\u3002", "\u8fc7\u5ea6\u63a5\u89e6\u5f02\u5e38\u4f1a\u5e26\u6765\u5e7b\u89c9\u3001\u8bb0\u5fc6\u6c61\u67d3\u3001\u9ed1\u75d5\u6269\u6563\u548c\u88ab\u4e95\u91cc\u7684\u4e1c\u897f\u6807\u8bb0\u3002"]
        character["companion_card"] = {"name": "Assassin", "kind": "servant", "archetype": "servant", "class": "Assassin", "true_name": "\u672a\u516c\u5f00", "personality": "\u5e73\u9759\u3001\u514b\u5236\u3001\u5371\u9669\u3001\u4e0d\u54c4\u4eba\u3001\u4e0d\u8f7b\u6613\u89e3\u91ca", "visual_seed": "servant:assassin:lingchuan"}
    elif template == "dnd":
        profile.update({
            "title": profile.get("title") or name,
            "genre": "DND \u5947\u5e7b\u5192\u9669",
            "tone": "\u82f1\u96c4\u5192\u9669\u3001\u63a2\u7d22\u3001\u9635\u8425\u4e0e\u4ee3\u4ef7",
            "world_rules": ["\u4f7f\u7528\u961f\u4f0d\u3001\u5730\u70b9\u3001\u9635\u8425\u548c\u4efb\u52a1\u94a9\u5b50\u63a8\u52a8\u5192\u9669\u3002", "\u9b54\u6cd5\u3001\u804c\u4e1a\u80fd\u529b\u4e0e\u602a\u7269\u80fd\u529b\u9700\u8981\u4fdd\u6301\u524d\u540e\u4e00\u81f4\u3002"],
            "narration_rules": ["\u5148\u5448\u73b0\u573a\u666f\u53ef\u884c\u52a8\u4fe1\u606f\uff0c\u518d\u7ed9\u51fa\u98ce\u9669\u4e0e\u673a\u4f1a\u3002", "\u6218\u6597\u8f6e\u6b21\u4e2d\u660e\u786e\u8ddd\u79bb\u3001\u76ee\u6807\u3001\u63a9\u62a4\u548c\u8d44\u6e90\u6d88\u8017\u3002"],
            "hard_limits": ["\u4e0d\u8981\u66ff\u73a9\u5bb6\u51b3\u5b9a\u89d2\u8272\u884c\u52a8\u3002", "\u5173\u952e\u68c0\u5b9a\u548c\u6218\u6597\u540e\u679c\u5fc5\u987b\u53ef\u8ffd\u8e2a\u3002"],
        })
        profile["mechanics"] = {"use_dice": True, "dice_system": "d20", "use_combat_rules": True, "stats_style": "strict_stats"}
        direction["theme_and_tone"] = ["\u5947\u5e7b\u5192\u9669", "\u5730\u4e0b\u57ce\u63a2\u7d22", "\u9635\u8425\u51b2\u7a81", "\u6210\u957f\u4e0e\u9009\u62e9"]
        direction["pace_rules"] = ["Alternate exploration, social scenes, and combat.", "Give a clear next action entry after each turn."]
        style["prose_style"] = ["Clear, concrete, adventurous prose.", "Mark rule outcomes in short standalone lines."]
        character["growth_direction"] = ["Track class, level, resources, equipment, and key feats."]
    elif template == "coc":
        profile.update({
            "title": profile.get("title") or name,
            "genre": "COC \u514b\u82cf\u9c81\u8c03\u67e5",
            "tone": "\u8c03\u67e5\u3001\u60ac\u7591\u3001\u5fc3\u7406\u538b\u529b\u3001\u4e0d\u53ef\u77e5\u6050\u60e7",
            "world_rules": ["Clue chains must be traceable and avoid single failure points.", "Reveal supernatural truth layer by layer, not all at once."],
            "narration_rules": ["Emphasize environmental details, conflicting testimony, time pressure, and sanity risk.", "Failed checks should still advance with a cost."],
            "hard_limits": ["Do not reveal truths unknown to investigators.", "Do not write unconfirmed guesses as facts."],
        })
        profile["mechanics"] = {"use_dice": True, "dice_system": "d100", "use_combat_rules": False, "stats_style": "strict_stats"}
        direction["theme_and_tone"] = ["\u8c03\u67e5\u6050\u6016", "\u7ebf\u7d22\u63a8\u7406", "\u7406\u667a\u538b\u529b", "\u4eba\u7c7b\u8106\u5f31\u6027"]
        direction["pace_rules"] = ["Advance through clues, testimony, and location investigation.", "Give observable warning signs before danger escalates."]
        style["prose_style"] = ["Restrained, calm prose with oppressive details.", "Avoid plainly explaining the source of horror."]
        character["growth_direction"] = ["Track investigation skills, sanity, injuries, contacts, and important clues."]
    write_json(profile_path, profile)
    write_json(direction_path, direction)
    write_json(style_path, style)
    write_json(character_path, character)

def set_chatgpt_binding_payload(payload: dict[str, Any]) -> dict[str, Any]:
    campaign_id = str(payload.get("campaign_id") or "").strip() or MemoryStore().resolve_campaign_id(None)
    project_name = str(payload.get("project_name") or "").strip()
    conversation_name = str(payload.get("conversation_name") or "").strip()
    if not project_name:
        raise RuntimeError("project_name is required")
    if not conversation_name:
        raise RuntimeError("conversation_name is required")
    MemoryStore().update_chatgpt_binding(campaign_id, project_name, conversation_name)
    return {"ok": True, "campaign_id": campaign_id, "status": status_payload()}




def campaign_profile_payload(campaign_id: str = "") -> dict[str, Any]:
    resolved = campaign_id or MemoryStore().resolve_campaign_id(None)
    root = CAMPAIGNS_DIR / safe_segment(resolved)
    path = root / "campaign_profile.json"
    if not path.exists():
        raise RuntimeError(f"missing campaign_profile.json: {resolved}")
    registry = MemoryStore().load_registry()
    meta = registry.get("campaigns", {}).get(resolved, {})
    return {"ok": True, "campaign_id": resolved, "profile": read_json(path), "registry_meta": meta}


def update_campaign_profile_payload(payload: dict[str, Any]) -> dict[str, Any]:
    campaign_id = str(payload.get("campaign_id") or "").strip() or MemoryStore().resolve_campaign_id(None)
    root = CAMPAIGNS_DIR / safe_segment(campaign_id)
    path = root / "campaign_profile.json"
    if not path.exists():
        raise RuntimeError(f"missing campaign_profile.json: {campaign_id}")
    profile = read_json(path)
    for key in ("title", "genre", "tone"):
        if key in payload:
            profile[key] = str(payload.get(key) or "").strip()
    for key in ("world_rules", "narration_rules", "hard_limits"):
        if key in payload:
            value = payload.get(key)
            profile[key] = [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else split_lines(str(value or ""))
    mechanics = payload.get("mechanics")
    if isinstance(mechanics, dict):
        current = profile.setdefault("mechanics", {})
        for key in ("use_dice", "use_combat_rules"):
            if key in mechanics:
                current[key] = bool(mechanics.get(key))
        for key in ("dice_system", "stats_style"):
            if key in mechanics:
                current[key] = str(mechanics.get(key) or "").strip()
    write_json(path, profile)
    registry = MemoryStore().load_registry()
    if campaign_id in registry.get("campaigns", {}):
        registry["campaigns"][campaign_id]["name"] = profile.get("title") or registry["campaigns"][campaign_id].get("name", campaign_id)
        registry["campaigns"][campaign_id]["updated_at"] = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        MemoryStore().save_registry(registry)
    return {"ok": True, "campaign_id": campaign_id, "profile": profile, "status": status_payload()}


def update_campaign_status_payload(payload: dict[str, Any]) -> dict[str, Any]:
    campaign_id = str(payload.get("campaign_id") or "").strip() or MemoryStore().resolve_campaign_id(None)
    status = str(payload.get("status") or "").strip().lower()
    if status not in {"active", "archived"}:
        raise RuntimeError("status must be active or archived")
    store = MemoryStore()
    registry = store.load_registry()
    campaigns = registry.setdefault("campaigns", {})
    if campaign_id not in campaigns:
        raise RuntimeError(f"unknown campaign_id: {campaign_id}")
    campaigns[campaign_id]["status"] = status
    campaigns[campaign_id]["updated_at"] = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    if status == "archived" and registry.get("active_campaign") == campaign_id:
        replacement = next((cid for cid, meta in campaigns.items() if cid != campaign_id and meta.get("status") != "archived"), "")
        registry["active_campaign"] = replacement or campaign_id
    if status == "active" and not registry.get("active_campaign"):
        registry["active_campaign"] = campaign_id
    store.save_registry(registry)
    return {"ok": True, "campaign_id": campaign_id, "status": status_payload()}


def split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.replace(";", "\n").replace("|", "\n").splitlines() if line.strip()]


def memory_report_payload(campaign_id: str = "") -> dict[str, Any]:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id or None)
    memory = store.load_campaign_memory(resolved)
    recent = memory.get("recent_context.json", {})
    return {
        "ok": True,
        "campaign_id": resolved,
        "files": [memory_file_report(name, memory.get(name, {})) for name in MEMORY_FILE_NAMES],
        "recent_writes": recent_write_summary(recent),
        "unconfirmed": unconfirmed_report(memory),
        "compaction": build_compaction_report(memory),
    }


def memory_file_report(name: str, data: Any) -> dict[str, Any]:
    return {"file": name, "entries": count_memory_entries(data), "last_updated_turn": data.get("last_updated_turn", "") if isinstance(data, dict) else "", "main_bucket": main_memory_bucket(data)}


def count_memory_entries(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        total = 0
        for item in value.values():
            if isinstance(item, list):
                total += len(item)
            elif isinstance(item, dict):
                total += len(item)
        return total or len([key for key in value.keys() if key not in {"campaign_id", "scope", "purpose"}])
    return 0


def main_memory_bucket(data: Any) -> str:
    if not isinstance(data, dict):
        return ""
    for key in ("facts", "recent_summary", "main_threads", "side_threads", "profiles", "npcs", "world_updates", "location_updates", "quest_updates", "equipment_updates", "growth_log", "mystery_updates", "prose_style", "background_direction"):
        if isinstance(data.get(key), (list, dict)) and count_memory_entries(data.get(key)):
            return key
    return ""


def recent_write_summary(recent: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    summaries = recent.get("recent_summary", []) if isinstance(recent, dict) else []
    if isinstance(summaries, list):
        for item in summaries[-5:]:
            rows.append({"type": "recent_summary", "text": stringify_brief(item)})
    for key, label in (("last_player_action", "\u73a9\u5bb6\u884c\u52a8"), ("last_outcome", "\u6700\u8fd1\u7ed3\u679c")):
        text = stringify_brief(recent.get(key, "")) if isinstance(recent, dict) else ""
        if text:
            rows.append({"type": label, "text": text})
    scene = recent.get("current_scene", {}) if isinstance(recent, dict) else {}
    if isinstance(scene, dict) and scene:
        rows.append({"type": "\u5f53\u524d\u73b0\u573a", "text": stringify_brief(scene)})
    return rows[-8:]


def unconfirmed_report(memory: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for filename, data in memory.items():
        if isinstance(data, dict) and isinstance(data.get("uncertain_or_unconfirmed"), list) and data["uncertain_or_unconfirmed"]:
            rows.append({"file": filename, "count": len(data["uncertain_or_unconfirmed"]), "items": [stringify_brief(item) for item in data["uncertain_or_unconfirmed"][-8:]]})
    return rows


def stringify_brief(value: Any, limit: int = 220) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("..." if len(text) > limit else "")


def campaign_export_payload(campaign_id: str = "") -> dict[str, Any]:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id or None)
    root = CAMPAIGNS_DIR / safe_segment(resolved)
    registry = store.load_registry()
    logs = []
    log_dir = root / "logs"
    if log_dir.exists():
        for path in sorted(log_dir.glob("*.json"))[-20:]:
            try:
                logs.append({"name": path.name, "content": read_json(path)})
            except Exception as exc:
                logs.append({"name": path.name, "error": str(exc)})
    return {
        "ok": True,
        "schema": "trpg_orchestrator.campaign_export.v1",
        "campaign_id": resolved,
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "registry_meta": registry.get("campaigns", {}).get(resolved, {}),
        "memory_files": {name: read_json(root / name) for name in MEMORY_FILE_NAMES if (root / name).exists()},
        "asset_manifest": load_asset_manifest(resolved),
        "recent_logs": logs,
        "outbox": safe_outbox_snapshot(resolved),
    }


def safe_outbox_snapshot(campaign_id: str = "") -> dict[str, Any]:
    rows: dict[str, Any] = {}
    outbox_dir = resolve_outbox_dir(campaign_id)
    for name in OUTBOX_SNAPSHOT_NAMES:
        path = outbox_dir / name
        if not path.exists():
            continue
        try:
            rows[name] = read_json(path) if path.suffix == ".json" else read_runtime_text(path)
        except Exception as exc:
            rows[name] = {"error": str(exc)}
    return rows

def current_writeback(campaign_id: str = "") -> dict[str, Any]:
    outbox_dir = resolve_outbox_dir(campaign_id)
    require_outbox_campaign(outbox_dir, campaign_id)
    path = outbox_dir / "state_writeback.json"
    if path.exists():
        data = read_json(path)
        validate_writeback(data)
        return data
    raw_path = outbox_dir / "chatgpt_raw_output.md"
    if not raw_path.exists():
        raise FileNotFoundError("missing outbox/state_writeback.json or chatgpt_raw_output.md")
    parsed = parse_chatgpt_output(read_runtime_text(raw_path))
    validate_writeback(parsed.writeback)
    write_json(path, parsed.writeback)
    return parsed.writeback


def audit_writeback_payload(campaign_id: str = "") -> dict[str, Any]:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id or None)
    memory = store.load_campaign_memory(resolved)
    outbox_dir = resolve_outbox_dir(resolved)
    require_outbox_campaign(outbox_dir, resolved)
    writeback = current_writeback(resolved)
    pressure_path = outbox_dir / "pressure_pack.json"
    pressure_pack = read_json(pressure_path) if pressure_path.exists() else {}
    capability_plan = read_web_capability_plan(outbox_dir, resolved, memory)
    audit_result = extract_json_object(DeepSeekClient().complete_json(
        read_prompt("v4_audit_prompt.md"),
        build_audit_user_prompt(resolved, memory, pressure_pack, writeback, capability_plan),
    ))
    validate_audit_result(audit_result)
    if audit_result.get("decision") in {"accept", "revise"}:
        validate_writeback(audit_result.get("approved_writeback") or writeback)
    write_json(outbox_dir / "v4_audit_result.json", audit_result)
    return writeback_review_payload(resolved)


def writeback_review_payload(campaign_id: str = "") -> dict[str, Any]:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id or None)
    memory = store.load_campaign_memory(resolved)
    writeback: dict[str, Any] = {}
    audit_result: dict[str, Any] = {}
    pending_updates: dict[str, Any] = {}
    warnings: list[str] = []
    outbox_dir = resolve_outbox_dir(resolved)
    try:
        require_outbox_campaign(outbox_dir, resolved)
        writeback = current_writeback(resolved)
    except Exception as exc:
        warnings.append(str(exc))
    audit_path = outbox_dir / "v4_audit_result.json"
    if audit_path.exists():
        try:
            audit_result = read_json(audit_path)
            validate_audit_result(audit_result)
        except Exception as exc:
            warnings.append(f"invalid audit result: {exc}")
            audit_result = {}
    decision = audit_result.get("decision", "not_audited")
    approved = audit_result.get("approved_writeback") or writeback
    if decision in {"accept", "revise"} and approved:
        pressure_path = outbox_dir / "pressure_pack.json"
        pressure_pack = normalize_pressure_pack_compat(read_json(pressure_path)) if pressure_path.exists() else {}
        raw_digest = writeback_hash(writeback)
        approved_digest = writeback_hash(approved)
        for digest in (raw_digest, approved_digest):
            if digest and has_applied_writeback(memory, digest):
                warnings.append(f"duplicate writeback already applied: {digest[:12]}")
        pending_updates = apply_approved_writeback(memory, approved, extra_hashes=[raw_digest], pressure_pack=pressure_pack)
    return {
        "ok": True,
        "campaign_id": resolved,
        "writeback": writeback,
        "audit_result": audit_result,
        "decision": decision,
        "approved_writeback": approved if decision in {"accept", "revise"} else {},
        "memory_files_to_update": sorted(pending_updates.keys()),
        "pending_updates": pending_updates,
        "warnings": warnings + list(audit_result.get("warnings", [])),
    }


def apply_writeback_payload(campaign_id: str = "") -> dict[str, Any]:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id or None)
    memory = store.load_campaign_memory(resolved)
    outbox_dir = resolve_outbox_dir(resolved)
    require_outbox_campaign(outbox_dir, resolved)
    writeback = current_writeback(resolved)
    audit_path = outbox_dir / "v4_audit_result.json"
    if not audit_path.exists():
        raise RuntimeError("missing V4 audit result; run audit first")
    audit_result = read_json(audit_path)
    validate_audit_result(audit_result)
    decision = audit_result.get("decision")
    if decision == "reject":
        raise RuntimeError(f"V4 rejected writeback: {audit_result.get('reason', '')}")
    if decision not in {"accept", "revise"}:
        raise RuntimeError(f"invalid V4 audit decision: {decision}")
    approved = audit_result.get("approved_writeback") or writeback
    validate_writeback(approved)
    pressure_path = outbox_dir / "pressure_pack.json"
    pressure_pack = normalize_pressure_pack_compat(read_json(pressure_path)) if pressure_path.exists() else {}
    raw_digest = writeback_hash(writeback)
    approved_digest = writeback_hash(approved)
    for digest in (raw_digest, approved_digest):
        if has_applied_writeback(memory, digest):
            raise RuntimeError(f"duplicate writeback already applied: {digest[:12]}")
    updates = apply_approved_writeback(memory, approved, extra_hashes=[raw_digest], pressure_pack=pressure_pack)
    touched = list(updates.keys())
    if touched:
        store.backup_files(resolved, touched)
        store.write_memory_updates(resolved, updates)
    raw_path = outbox_dir / "chatgpt_raw_output.md"
    flavor_path = outbox_dir / "ai_flavor_report.json"
    image_job_path = outbox_dir / "image_job.json"
    action_path = outbox_dir / "last_player_action.txt"
    store.write_log(resolved, {
        "player_action": read_runtime_text(action_path) if action_path.exists() else "",
        "v4_pressure_pack": pressure_pack,
        "chatgpt_raw_output": read_runtime_text(raw_path) if raw_path.exists() else "",
        "ai_flavor_report": read_json(flavor_path) if flavor_path.exists() else {},
        "v4_audit_result": audit_result,
        "final_write": updates,
    })
    return {"ok": True, "campaign_id": resolved, "updated_files": touched, "status": status_payload()}
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
        "output": output_payload(cid),
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
            "chapter": profile.get("chapter", "") or recent.get("current_scene", {}).get("chapter") or recent.get("chapter", "") or recent.get("current_scene", {}).get("time", ""),
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

def output_payload(campaign_id: str = "", require_parse_ready: bool = False) -> dict[str, Any]:
    """Return parsed output. Prefer persisted structured blocks for frontend rendering."""
    # Force re-import to pick up code changes
    import importlib
    import trpg_orchestrator.output_parser as _op
    importlib.reload(_op)
    _parse = _op.parse_chatgpt_output

    resolved = MemoryStore().resolve_campaign_id(campaign_id or None) if campaign_id else MemoryStore().resolve_campaign_id(None)
    outbox_dir = resolve_outbox_dir(resolved)
    found_campaign = outbox_campaign_id(outbox_dir)
    if found_campaign and found_campaign != resolved:
        return empty_output_payload(resolved, f"outbox campaign mismatch: expected {resolved}, got {found_campaign}")
    blocks_path = outbox_dir / "chatgpt_blocks.json"
    raw_path = outbox_dir / "chatgpt_raw_output.md"
    clean_path = outbox_dir / "chatgpt_clean_output.md"
    pressure_path = outbox_dir / "pressure_pack.json"
    audit_path = outbox_dir / "v4_audit_result.json"
    flavor_path = outbox_dir / "ai_flavor_report.json"
    image_job_path = outbox_dir / "image_job.json"
    public_marker_mtime = max(
        file_mtime(pressure_path),
        file_mtime(outbox_dir / "state_writeback.json"),
    )
    text = ""
    parsed: dict[str, Any] = {"body": "", "choices": "", "summary": "", "blocks": []}
    source = ""
    parse_ready = output_parse_ready(outbox_dir)

    blocks_stale = is_stale_public_output(blocks_path, public_marker_mtime)
    keep_previous_blocks = require_parse_ready and not parse_ready
    if blocks_path.exists() and (not blocks_stale or keep_previous_blocks):
        try:
            block_payload = read_json(blocks_path)
            block_text = json.dumps(block_payload, ensure_ascii=False)
            p = _parse(block_text)
            if p.blocks:
                parsed = {
                    "body": p.body,
                    "choices": p.choices,
                    "summary": p.summary,
                    "blocks": p.blocks,
                }
                text = json.dumps(block_payload, ensure_ascii=False, indent=2)
                source = blocks_path.name
        except Exception:
            pass

    if not parsed.get("blocks") and raw_path.exists() and not is_stale_public_output(raw_path, public_marker_mtime):
        try:
            raw_text = read_runtime_text(raw_path)
            p = _parse(raw_text)
            if p.blocks:
                parsed = {"body": p.body, "choices": p.choices, "summary": p.summary, "blocks": p.blocks}
                text = raw_text
                source = raw_path.name
        except Exception:
            pass

    if not parsed.get("blocks") and clean_path.exists() and not is_stale_public_output(clean_path, public_marker_mtime):
        text = read_runtime_text(clean_path)
        source = clean_path.name
        try:
            p = _parse(text)
            parsed = {"body": p.body, "choices": p.choices, "summary": p.summary, "blocks": p.blocks}
        except Exception:
            parsed = split_public(text)
    return {
        "campaign_id": resolved,
        "source": source,
        "public_text": text,
        "parsed": parsed,
        "pressure_pack": normalize_pressure_pack_compat(read_json(pressure_path)) if pressure_path.exists() and (parse_ready or not require_parse_ready) else {},
        "audit_result": read_json(audit_path) if audit_path.exists() else {},
        "ai_flavor_report": read_json(flavor_path) if flavor_path.exists() else {},
        "image_job": read_json(image_job_path) if image_job_path.exists() else {},
        "stage": "parsed" if parsed.get("blocks") and parse_ready else ("parsed_stale" if parsed.get("blocks") else ("pending_parse" if not parse_ready else "empty")),
        "warning": "V4 pressure pack exists but ChatGPT blocks/state writeback are not ready for frontend refresh." if require_parse_ready and not parse_ready else "",
    }


def output_parse_ready(outbox_dir: Path) -> bool:
    pressure_mtime = file_mtime(outbox_dir / "pressure_pack.json")
    if not pressure_mtime:
        return True
    blocks_mtime = file_mtime(outbox_dir / "chatgpt_blocks.json")
    writeback_mtime = file_mtime(outbox_dir / "state_writeback.json")
    return bool(blocks_mtime >= pressure_mtime and writeback_mtime >= pressure_mtime)


def frontend_pipeline_status(campaign_id: str, output: dict[str, Any], job: dict[str, Any] | None = None) -> dict[str, Any]:
    outbox_dir = resolve_outbox_dir(campaign_id)
    pressure_mtime = file_mtime(outbox_dir / "pressure_pack.json")
    blocks_mtime = file_mtime(outbox_dir / "chatgpt_blocks.json")
    writeback_mtime = file_mtime(outbox_dir / "state_writeback.json")
    audit_mtime = file_mtime(outbox_dir / "v4_audit_result.json")
    job = job or {}
    baseline = float(job.get("started_at") or 0) if (job.get("running") or job.get("returncode") is None) else 0

    def fresh(mtime: float) -> bool:
        return bool(mtime and (not baseline or mtime + 0.5 >= baseline))

    parsed_blocks = output.get("parsed", {}).get("blocks", []) if isinstance(output.get("parsed"), dict) else []
    if parsed_blocks and output.get("stage") == "parsed" and (not baseline or (fresh(blocks_mtime) and fresh(writeback_mtime))):
        return {"stage": "synced", "percent": 100, "label": "已同步到页面"}
    if fresh(pressure_mtime) and audit_mtime >= pressure_mtime:
        return {"stage": "audited", "percent": 80, "label": "审核层完成"}
    if fresh(pressure_mtime) and blocks_mtime >= pressure_mtime and writeback_mtime >= pressure_mtime:
        return {"stage": "actor_parsed", "percent": 70, "label": "GPT 层完成"}
    if fresh(pressure_mtime):
        return {"stage": "director_ready", "percent": 30, "label": "V4 层完成"}
    return {"stage": "idle", "percent": 0, "label": "待机"}


def empty_output_payload(campaign_id: str, warning: str = "") -> dict[str, Any]:
    payload = {
        "campaign_id": campaign_id,
        "source": "",
        "public_text": "",
        "parsed": {"body": "", "choices": "", "summary": "", "blocks": []},
        "pressure_pack": {},
        "audit_result": {},
        "ai_flavor_report": {},
    }
    if warning:
        payload["warning"] = warning
    return payload


def split_public(text: str) -> dict[str, str]:
    body = ""
    choices = ""
    summary = ""
    body_marker = "\u3010\u6b63\u6587\u3011"
    choices_marker = "\u3010\u9009\u62e9\u70b9\u3011"
    summary_marker = "\u3010\u56de\u5408\u6458\u8981\u3011"
    writeback_marker = "\u3010\u72b6\u6001\u56de\u5199_BEGIN\u3011"
    if body_marker in text:
        body = text.split(body_marker, 1)[1].split(choices_marker, 1)[0].strip()
    if choices_marker in text:
        choices = text.split(choices_marker, 1)[1].split(summary_marker, 1)[0].strip()
    if summary_marker in text:
        summary = text.split(summary_marker, 1)[1].split(writeback_marker, 1)[0].strip()
    return {"body": body, "choices": choices, "summary": summary, "blocks": []}


def raw_output_payload(campaign_id: str = "") -> dict[str, Any]:
    """Parse chatgpt_raw_output.md directly and return rich blocks."""
    resolved = MemoryStore().resolve_campaign_id(campaign_id or None) if campaign_id else MemoryStore().resolve_campaign_id(None)
    outbox_dir = resolve_outbox_dir(resolved)
    raw_path = outbox_dir / "chatgpt_raw_output.md"
    if not raw_path.exists():
        return {"ok": False, "campaign_id": resolved, "error": "no raw output available"}
    try:
        from trpg_orchestrator.output_parser import parse_chatgpt_output
        raw_text = read_runtime_text(raw_path)
        parsed = parse_chatgpt_output(raw_text)
        return {
            "ok": True,
            "campaign_id": resolved,
            "blocks": parsed.blocks,
            "body": parsed.body,
            "choices": parsed.choices,
            "summary": parsed.summary,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


if __name__ == "__main__":
    raise SystemExit(main())









