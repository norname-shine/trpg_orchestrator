# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import json
import math
import os
import re
import shutil
import socket
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
from .output_parser import parse_chatgpt_output, public_output, visible_prose_chars
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
        self.job_id = ""
        self.stream_text = ""
        self.stream_updated_at = 0.0
        self.stream_enabled = False
        self.stage = ""
        self.public_think: list[dict[str, str]] = []
        self.public_note = ""
        self.needs_human_verification = False

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
                "job_id": self.job_id,
                "stream_text": self.stream_text[-50000:],
                "stream_updated_at": self.stream_updated_at,
                "stream_enabled": self.stream_enabled,
                "stage": self.stage,
                "public_think": self.public_think[-12:],
                "public_note": self.public_note,
                "needs_human_verification": self.needs_human_verification,
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
            self.job_id = f"job_{int(self.started_at * 1000)}"
            self.stream_text = ""
            self.stream_updated_at = 0.0
            self.stream_enabled = streaming_preview_enabled()
            self.stage = ""
            self.public_think = []
            self.public_note = ""
            self.needs_human_verification = False

    def finish(self, completed: subprocess.CompletedProcess[str]) -> None:
        with self.lock:
            self.running = False
            self.finished_at = time.time()
            self.returncode = completed.returncode
            self.output = completed.stdout or ""
            self.error = completed.stderr or ""

    def finish_code(self, returncode: int) -> None:
        with self.lock:
            self.running = False
            self.finished_at = time.time()
            self.returncode = returncode

    def append_output(self, text: str) -> None:
        if not text:
            return
        with self.lock:
            self.output = (self.output + text)[-60000:]

    def append_error(self, text: str) -> None:
        if not text:
            return
        with self.lock:
            self.error = (self.error + text)[-60000:]

    def update_stream_text(self, text: str) -> None:
        with self.lock:
            self.stream_text = text[-50000:]
            self.stream_updated_at = time.time()

    def update_public_status(self, status: dict[str, Any]) -> None:
        with self.lock:
            self.stage = str(status.get("stage") or self.stage or "")
            self.public_note = str(status.get("label") or status.get("public_note") or self.public_note or "")
            self.needs_human_verification = bool(status.get("needs_human_verification"))
            label = self.public_note.strip()
            incoming_think = sanitize_public_think(status.get("public_think"))
            for item in incoming_think:
                if item not in self.public_think:
                    self.public_think.append(item)
            if label:
                item = {"stage": self.stage or "running", "text": label}
                if item not in self.public_think:
                    self.public_think.append(item)
                    self.public_think = self.public_think[-12:]
            self.stream_updated_at = time.time()


JOB = JobState()
NEW_CAMPAIGN_JOBS: dict[str, dict[str, Any]] = {}
NEW_CAMPAIGN_JOBS_LOCK = threading.Lock()
STREAM_SNAPSHOT_PREFIX = "TRPG_STREAM_SNAPSHOT "
WORKER_STATUS_PREFIX = "TRPG_WORKER_STATUS "

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
        if parsed.path == "/api/run-turn-stream":
            query = parse_qs(parsed.query)
            self._json(run_turn_stream_payload(first_query(query, "job_id")))
            return
        if parsed.path.startswith("/api/module/"):
            query = parse_qs(parsed.query)
            self._json(module_payload_response(
                parsed.path.removeprefix("/api/module/"),
                first_query(query, "campaign_id"),
                first_query(query, "cursor"),
                first_query(query, "limit"),
                first_query(query, "kind"),
            ))
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
        if parsed.path == "/api/create-campaign-smart-progress":
            query = parse_qs(parsed.query)
            self._json(new_campaign_progress_payload(first_query(query, "job_id")))
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
            if parsed.path == "/api/delete-campaign":
                payload = self._read_json()
                self._json(delete_campaign_payload(payload))
                return
            if parsed.path == "/api/init-campaign":
                payload = self._read_json()
                self._json(init_campaign_payload(payload))
                return
            if parsed.path == "/api/create-campaign-smart":
                payload = self._read_json()
                self._json(create_campaign_smart_payload(payload))
                return
            if parsed.path == "/api/create-campaign-smart-start":
                payload = self._read_json()
                self._json(start_create_campaign_smart_job(payload))
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
            migrated = migrateAssetKinds(data, build_actor_identity_context(campaign_id))
            if migrated.get("_migration_changed"):
                migrated.pop("_migration_changed", None)
                write_json(path, migrated)
                return migrated
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


def scoped_asset_key(campaign_id: str, kind: str, object_id: Any, variant: str = "default", generator_version: int = 17) -> str:
    resolved = safe_segment(campaign_id or MemoryStore().resolve_campaign_id(None))
    seed = campaign_asset_seed(resolved)
    obj = safe_segment(str(object_id or "unknown"))
    return f"{resolved}:{seed}:{safe_segment(kind)}:{obj}:{safe_segment(variant)}:v{generator_version}"


ROLE_PRIORITY = {
    "player": 10,
    "companion": 20,
    "master": 30,
    "npc": 40,
    "item": 50,
    "scene": 60,
}

ROLE_ASSET_KIND = {
    "player": "player_portrait",
    "companion": "companion_portrait",
    "master": "master_portrait",
    "npc": "npc_portrait",
    "item": "item_icon",
    "scene": "scene_image",
    "map": "map_image",
    "monster": "monster_image",
    "cg": "cg_image",
}

ACTOR_ROLES = {"player", "companion", "master", "npc"}
GALLERY_VISIBLE_KINDS = {
    "companion_portrait",
    "master_portrait", "npc_portrait", "item_icon", "scene_image", "map_image",
    "monster_image", "cg_image", "gallery_image",
}


def normalize_asset_kind(kind: Any, metadata: dict[str, Any] | None = None, key: str = "") -> str:
    raw = str(kind or "").lower()
    metadata = metadata or {}
    if "attribute_star" in raw or "attribute_star" in str(key).lower():
        return "attribute_star"
    role = infer_asset_role({"kind": raw, "key": key, "metadata": metadata})
    if role in ROLE_ASSET_KIND:
        return ROLE_ASSET_KIND[role]
    if raw in ROLE_ASSET_KIND.values():
        return raw
    if raw in {"portrait"}:
        return "player_portrait"
    if raw in {"companion"}:
        return "companion_portrait"
    if raw in {"npc", "character"} or "npc" in raw:
        return "npc_portrait"
    if raw in {"item", "weapon", "supply", "material", "ritual_tool", "equipment"}:
        return "item_icon"
    if raw in {"scene", "location"}:
        return "scene_image"
    if raw == "map" or "gallery_map" in raw:
        return "map_image"
    if "monster" in raw or "ecology" in raw:
        return "monster_image"
    if "cg" in raw or "gallery_image" in raw or "formal_cg" in raw:
        return "cg_image" if "cg" in raw else "gallery_image"
    return raw


def infer_asset_role(asset: dict[str, Any]) -> str:
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    explicit = str(metadata.get("role") or metadata.get("entity_role") or asset.get("role") or "").lower()
    if explicit in ROLE_PRIORITY:
        return explicit
    entity_key = str(metadata.get("entity_key") or asset.get("entity_key") or "")
    if ":" in entity_key:
        prefix = entity_key.split(":", 1)[0].lower()
        if prefix in ROLE_PRIORITY:
            return prefix
    text = " ".join(str(value or "") for value in (
        asset.get("kind"), asset.get("key"), metadata.get("kind"), metadata.get("title"),
        metadata.get("display_name"), metadata.get("detail"), metadata.get("object_id"),
    )).lower()
    if any(token in text for token in ("companion", "伙伴", "同行")):
        return "companion"
    if any(token in text for token in ("master", "御主")):
        return "master"
    kind = str(asset.get("kind") or "").lower()
    if "attribute_star" in kind or "attribute_star" in str(asset.get("key") or "").lower():
        return ""
    if kind in {"portrait", "player_portrait"}:
        return "player"
    if kind in {"item", "item_icon", "weapon", "supply", "material", "ritual_tool", "equipment"}:
        return "item"
    if kind in {"map", "map_image"}:
        return "map"
    if kind in {"scene", "scene_image", "location"}:
        return "scene"
    if "monster" in kind:
        return "monster"
    if "cg" in kind:
        return "cg"
    if "npc" in kind or "portrait" in kind:
        return "npc"
    return ""


def asset_display_name(asset: dict[str, Any]) -> str:
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    return str(metadata.get("display_name") or metadata.get("title") or asset.get("display_name") or asset.get("title") or "").strip()


def entity_key_for_asset(asset: dict[str, Any]) -> str:
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    existing = str(metadata.get("entity_key") or asset.get("entity_key") or "").strip()
    if existing:
        return existing
    role = infer_asset_role(asset) or "item"
    name = asset_display_name(asset) or metadata.get("object_id") or asset.get("key") or role
    return f"{role}:{safe_segment(str(name).lower())}"


def actor_identity_names_from_state(state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    prompt = state.get("character_prompt", {}) if isinstance(state.get("character_prompt"), dict) else {}
    player = state.get("player", {}) if isinstance(state.get("player"), dict) else {}
    provided = first_dict(player.get("character_card"), prompt.get("character_card"))
    identity = first_dict(provided.get("identity"), player.get("confirmed_identity"), prompt.get("confirmed_identity"))
    companion = first_dict(provided.get("companion"), prompt.get("companion_card"))
    if not companion and isinstance(identity.get("companion"), dict):
        companion = identity.get("companion")
    return identity, companion


def actor_identity_context_from_state(campaign_id: str, state: dict[str, Any]) -> dict[str, Any]:
    identity, companion = actor_identity_names_from_state(state)
    player_name = str(identity.get("name") or inferred_player_name(
        state.get("player", {}) if isinstance(state.get("player"), dict) else {},
        state.get("character_prompt", {}) if isinstance(state.get("character_prompt"), dict) else {},
    ) or "").strip()
    companion_name = str(companion.get("name") or "").strip()
    companion_config = state.get("companion_config") if isinstance(state.get("companion_config"), dict) else {}
    if not companion_name and companion_config.get("companion_enabled") and companion_config.get("companion_name"):
        companion_name = str(companion_config.get("companion_name") or "").strip()
    player_key = f"player:{stable_entity_name(player_name or campaign_id)}"
    companion_key = f"companion:{stable_entity_name(companion_name)}" if companion_name else ""
    companion_type = str(
        companion.get("companion_type")
        or companion.get("kind")
        or companion.get("type")
        or companion_config.get("companion_type")
        or companion.get("archetype")
        or ""
    ).strip()
    return {
        "campaign_id": campaign_id,
        "player": {"name": player_name, "entity_key": player_key},
        "companion": {
            "name": companion_name,
            "entity_key": companion_key,
            "companion_type": companion_type,
            "companion_type_raw": companion_type,
            "archetype": str(companion.get("archetype") or companion.get("class") or companion.get("kind") or "").strip(),
            "species": str(companion.get("species") or companion.get("race") or "").strip(),
            "source": companion,
        },
        "protected_actor_keys": {key for key in (player_key, companion_key) if key},
        "protected_actor_names": {normalized_name(name) for name in (player_name, companion_name) if name},
    }


def build_actor_identity_context(campaign_id: str) -> dict[str, Any]:
    try:
        return actor_identity_context_from_state(campaign_id, campaign_state(campaign_id))
    except Exception:
        return {"campaign_id": campaign_id, "player": {}, "companion": {}, "protected_actor_keys": set(), "protected_actor_names": set()}


def build_companion_visual_profile(companion: dict[str, Any], campaign_memory: dict[str, Any] | None = None, style_profile: dict[str, Any] | None = None, image_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    companion = companion if isinstance(companion, dict) else {}
    campaign_memory = campaign_memory if isinstance(campaign_memory, dict) else {}
    style_profile = style_profile if isinstance(style_profile, dict) else {}
    image_profile = image_profile if isinstance(image_profile, dict) else {}
    raw_type = str(
        companion.get("companion_type_raw")
        or companion.get("companion_type")
        or companion.get("kind")
        or companion.get("type")
        or companion.get("archetype")
        or companion.get("role")
        or ""
    ).strip()
    species = list_payload(companion.get("species") or companion.get("race") or companion.get("origin") or "")
    archetype = str(companion.get("archetype") or companion.get("class") or companion.get("kind") or "").strip()
    personality = list_payload(companion.get("personality") or companion.get("temperament") or "")
    equipment = list_payload(companion.get("equipment") or companion.get("weapon") or companion.get("gear") or "")
    direction = campaign_memory.get("campaign_direction") if isinstance(campaign_memory.get("campaign_direction"), dict) else {}
    background_markers = list_payload(
        direction.get("background_direction")
        or direction.get("core_concept")
        or direction.get("opening_situation")
        or campaign_memory.get("genre")
        or ""
    )
    relationship = list_payload(companion.get("relationship_to_protagonist") or companion.get("relationship") or "")
    style_markers = list_payload(style_profile.get("style") or style_profile.get("tone") or image_profile.get("style_preset") or campaign_memory.get("template") or "")
    text = " ".join([raw_type, archetype, " ".join(species), " ".join(personality), " ".join(equipment)]).lower()
    preset = "custom"
    body_form = raw_type or archetype or "distinct campaign companion"
    body_structure: list[str] = []
    material_traits: list[str] = []
    face_rules: list[str] = []
    silhouette_rules = ["must differ from the main player silhouette", "do not reuse player face template"]
    pose_rules = ["companion-focused posture", "clear role silhouette"]
    color_rules = ["use campaign palette markers without copying the player palette"]
    if re.search(r"palico|felyne|cat|feline|猫|艾露", text):
        preset = "palico"
        body_form = "small feline companion"
        body_structure.extend(["large ears", "compact body", "tail marker"])
        material_traits.extend(["fur", "cloth or leather support gear"])
        face_rules.extend(["cat nose", "whisker marks", "non-human muzzle"])
    elif re.search(r"servant|assassin|caster|saber|knight|rider|lancer|archer|从者|英灵|骑士|术士|暗杀", text):
        preset = "servant"
        body_form = "high-spec humanoid companion with class silhouette"
        body_structure.extend(["ceremonial posture", "class-readable outline"])
        material_traits.extend(["ritual cloth", "metal or shadow accents"])
        face_rules.extend(["masked or stylized face option", "not the player face"])
    elif re.search(r"familiar|spirit|ghost|wisp|summon|灵|魔宠|使魔|召唤", text):
        preset = "familiar"
        body_form = "spiritual or magical familiar"
        body_structure.extend(["floating or compact magical body", "non-ordinary companion outline"])
        material_traits.extend(["glow", "mist", "soft magical edges"])
        face_rules.extend(["symbolic face", "non-player facial structure"])
    elif re.search(r"mechanical|construct|robot|drone|ai|android|mecha|机械|构装|无人机|机器人", text):
        preset = "mechanical"
        body_form = "mechanical companion"
        body_structure.extend(["segmented chassis", "visible joints", "device-like head"])
        material_traits.extend(["metal", "glass", "indicator lights"])
        face_rules.extend(["sensor face", "no human skin template"])
    elif re.search(r"ship|vehicle|bike|car|mount|载具|船|车|坐骑", text):
        preset = "vehicle"
        body_form = "vehicle or mount companion"
        body_structure.extend(["vehicle silhouette", "front marker", "utility attachments"])
        material_traits.extend(["painted shell", "metal", "worn utility surfaces"])
        face_rules.extend(["no human face"])
    certainty = "confirmed" if raw_type or species or archetype else "fallback"
    return {
        "source": "resolved_from_campaign_memory",
        "companion_type_raw": raw_type,
        "companion_type_preset": preset,
        "body_form": body_form,
        "body_structure": body_structure or ["custom companion silhouette", "distinct from player body"],
        "species_or_origin": species or list_payload(archetype),
        "material_traits": material_traits or ["campaign-appropriate material markers"],
        "costume_or_equipment": equipment,
        "temperament": personality,
        "campaign_style_markers": style_markers,
        "background_markers": background_markers[:8],
        "relationship_markers": relationship[:6],
        "scale": str(companion.get("scale") or "companion scale"),
        "silhouette_rules": silhouette_rules,
        "face_rules": face_rules or ["do not reuse player face template", "avoid ordinary NPC face unless confirmed"],
        "pose_rules": pose_rules,
        "color_rules": color_rules,
        "avoid": [
            "do_not_reuse_player_face_template",
            "do_not_draw_as_ordinary_npc_unless_confirmed",
            "do_not_ignore_non_human_structure",
        ],
        "certainty": certainty,
    }


def build_player_visual_profile(campaign_id: str, state: dict[str, Any], character_card: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state if isinstance(state, dict) else {}
    character_card = character_card if isinstance(character_card, dict) else {}
    root = CAMPAIGNS_DIR / campaign_id
    direction = read_json(root / "campaign_direction.json") if (root / "campaign_direction.json").exists() else {}
    style_profile = read_json(root / "style_profile.json") if (root / "style_profile.json").exists() else {}
    image_profile = read_json(root / "image_profile.json") if (root / "image_profile.json").exists() else {}
    prompt = state.get("character_prompt", {}) if isinstance(state.get("character_prompt"), dict) else {}
    player = state.get("player", {}) if isinstance(state.get("player"), dict) else {}
    provided = first_dict(character_card, player.get("character_card"), prompt.get("character_card"))
    identity = first_dict(provided.get("identity"), player.get("confirmed_identity"), prompt.get("confirmed_identity"))
    profile = first_dict(provided.get("profile"), prompt.get("profile"))
    direction_text = " ".join(list_payload(direction.get("background_direction"))[:6])
    protagonist_text = " ".join([
        str(prompt.get("confirmed_identity") or ""),
        " ".join(list_payload(prompt.get("confirmed_background"))[:4]),
        " ".join(list_payload(prompt.get("personality_and_voice"))[:4]),
        " ".join(list_payload(prompt.get("growth_direction"))[:4]),
    ])
    text = " ".join([
        str(identity.get("name") or ""),
        str(identity.get("role") or identity.get("class_or_role") or identity.get("summary") or ""),
        str(profile.get("background") or ""),
        str(profile.get("motivation") or ""),
        str(profile.get("personality") or ""),
        direction_text,
        protagonist_text,
        str(state.get("template") or ""),
        str(state.get("genre") or ""),
        str(state.get("tone") or ""),
    ])
    normalized = text.lower()
    equipment: list[str] = []
    motifs: list[str] = []
    palette: list[str] = []
    if re.search(r"剑|盾|骑士|勇者|冒险|地城|神殿|遗迹|fantasy|adventure|knight|sword|shield|ruin|temple", normalized):
        equipment.extend(["traveler cloak", "adventurer gear", "sword or shield marker"])
        motifs.extend(["ancient triangle mark", "ruin light", "destiny emblem"])
        palette.extend(["forest green", "weathered leather", "ancient gold"])
    if re.search(r"森林|林|精灵|自然|forest|wood|elf", normalized):
        motifs.extend(["leaf silhouette", "forest rim light"])
        palette.extend(["moss green", "warm bark"])
    if re.search(r"调查|侦探|旧案|失踪|悬疑|克苏鲁|恐怖|san|detective|investigation|horror", normalized):
        equipment.extend(["notebook", "lantern", "long coat"])
        motifs.extend(["paper clue", "low shadow"])
        palette.extend(["lamp amber", "deep shadow"])
    if re.search(r"魔法|法术|巫|灵|命运|圣杯|magic|spell|fate|spirit", normalized):
        motifs.extend(["soft magical glow", "arcane badge"])
        palette.extend(["blue glow", "silver accent"])
    return {
        "source": "campaign_initialization",
        "role": "player",
        "identity_markers": list(dict.fromkeys(list_payload(" / ".join([
            str(identity.get("name") or ""),
            str(identity.get("role") or identity.get("class_or_role") or ""),
            str(identity.get("title") or ""),
            str(identity.get("summary") or ""),
        ]))))[:8],
        "background_markers": list(dict.fromkeys([
            *list_payload(profile.get("background")),
            *list_payload(direction.get("background_direction")),
            *list_payload(direction.get("core_concept")),
            *list_payload(direction.get("opening_situation")),
        ]))[:10],
        "personality_markers": list(dict.fromkeys([
            *list_payload(profile.get("personality")),
            *list_payload(prompt.get("personality_and_voice")),
        ]))[:8],
        "motivation_markers": list(dict.fromkeys([
            *list_payload(profile.get("motivation")),
            *list_payload(prompt.get("growth_direction")),
        ]))[:8],
        "costume_or_equipment": list(dict.fromkeys(equipment or ["campaign travel outfit", "role-readable gear"]))[:8],
        "palette_hints": list(dict.fromkeys(palette or [state.get("genre", ""), state.get("tone", ""), state.get("template", "")]))[:8],
        "pose_rules": ["full-body readable silhouette", "protagonist posture", "do not crop to only face"],
        "symbolic_motifs": list(dict.fromkeys(motifs or ["campaign fate marker"]))[:8],
        "campaign_style_markers": list(dict.fromkeys([
            *list_payload(state.get("template")),
            *list_payload(state.get("genre")),
            *list_payload(state.get("tone")),
            *list_payload(style_profile.get("style") or style_profile.get("tone")),
            *list_payload(image_profile.get("style_preset")),
        ]))[:8],
        "avoid": ["do_not_use_generic_placeholder", "do_not_reuse_companion_silhouette", "do_not_ignore_story_background"],
    }


def actor_name_candidates(asset: dict[str, Any], key: str = "") -> set[str]:
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    values = {
        asset.get("display_name"),
        asset.get("title"),
        asset.get("name"),
        asset.get("object_id"),
        metadata.get("display_name"),
        metadata.get("title"),
        metadata.get("name"),
        metadata.get("object_id"),
        metadata.get("actor_id"),
        metadata.get("avatar_key"),
    }
    entity_key = str(metadata.get("entity_key") or asset.get("entity_key") or "")
    if ":" in entity_key:
        values.add(entity_key.split(":", 1)[1])
    for part in re.split(r"[:/\\_-]+", str(key or asset.get("key") or "")):
        values.add(part)
    return {normalized_name(value) for value in values if normalized_name(value)}


def _identity_template(role: str, entity_key: str, display_name: str = "") -> dict[str, Any]:
    if role == "player":
        return {
            "entity_key": entity_key,
            "runtime_role": "player",
            "role": "player",
            "companion_type": "",
            "archetype": "",
            "species": "",
            "asset_kind": "player_portrait",
            "portrait_asset_kind": "player_portrait",
            "display_slot": "main_character_card",
            "detail_slot": "main_character_detail",
            "gallery_category": "hidden",
            "visible_in_gallery": False,
            "not_in_gallery_filters": True,
            "avatar_key": entity_key,
            "render_tier": "player",
            "avatar_locked_by_vcg": False,
            "display_name": display_name,
        }
    if role == "companion":
        return {
            "entity_key": entity_key,
            "runtime_role": "companion",
            "role": "companion",
            "companion_type": "generic",
            "companion_type_raw": "",
            "companion_type_preset": "custom",
            "archetype": "",
            "species": "",
            "asset_kind": "companion_portrait",
            "portrait_asset_kind": "companion_portrait",
            "display_slot": "companion_card",
            "detail_slot": "companion_detail",
            "gallery_category": "hidden",
            "visible_in_gallery": False,
            "not_in_gallery_filters": True,
            "avatar_key": entity_key,
            "render_tier": "companion",
            "avatar_locked_by_vcg": False,
            "display_name": display_name,
        }
    category = "npc" if role in {"", "unknown", "npc"} else role
    return {
        "entity_key": entity_key,
        "runtime_role": "npc" if role in {"", "unknown"} else role,
        "role": "npc" if role in {"", "unknown"} else role,
        "companion_type": "",
        "archetype": "",
        "species": "",
        "asset_kind": "npc_portrait" if category in {"npc", "master", "servant", "key_character"} else ROLE_ASSET_KIND.get(category, f"{category}_image"),
        "portrait_asset_kind": "npc_portrait" if category in {"npc", "master", "servant", "key_character"} else ROLE_ASSET_KIND.get(category, f"{category}_image"),
        "display_slot": "dossier_gallery",
        "detail_slot": "dossier_detail",
        "gallery_category": "npc" if category == "key_character" else category,
        "visible_in_gallery": category != "hidden",
        "not_in_gallery_filters": False,
        "avatar_key": entity_key,
        "render_tier": "npc" if category in {"npc", "master", "servant", "key_character"} else category,
        "avatar_locked_by_vcg": False,
        "display_name": display_name,
    }


def resolve_entity_role(entity_or_asset: dict[str, Any], memory: dict[str, Any] | None = None, manifest_entry: dict[str, Any] | None = None) -> dict[str, Any]:
    context = memory if isinstance(memory, dict) else {}
    asset = {**(manifest_entry or {}), **(entity_or_asset or {})}
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    key = str(asset.get("key") or "")
    display = asset_display_name(asset) or readable_asset_name(key, str(asset.get("kind") or ""))
    names = actor_name_candidates(asset, key)
    existing_entity_key = str(metadata.get("entity_key") or asset.get("entity_key") or "").strip()
    player = context.get("player") if isinstance(context.get("player"), dict) else {}
    companion = context.get("companion") if isinstance(context.get("companion"), dict) else {}
    player_key = str(player.get("entity_key") or "")
    companion_key = str(companion.get("entity_key") or "")
    player_name = normalized_name(player.get("name"))
    companion_name = normalized_name(companion.get("name"))
    if player_key and (existing_entity_key == player_key or existing_entity_key.startswith("player:") or (player_name and player_name in names)):
        return _identity_template("player", player_key, str(player.get("name") or display))
    if companion_key and (
        existing_entity_key == companion_key
        or existing_entity_key.startswith("companion:")
        or (existing_entity_key.startswith(("npc:", "master:", "servant:")) and companion_name and existing_entity_key.split(":", 1)[1] == stable_entity_name(companion.get("name")))
        or (companion_name and companion_name in names)
    ):
        identity = _identity_template("companion", companion_key, str(companion.get("name") or display))
        identity["companion_type"] = str(companion.get("companion_type_raw") or companion.get("companion_type") or "")
        identity["companion_type_raw"] = str(companion.get("companion_type_raw") or companion.get("companion_type") or "")
        identity["archetype"] = str(companion.get("archetype") or "")
        identity["species"] = str(companion.get("species") or "")
        identity["visual_profile"] = build_companion_visual_profile(companion.get("source") or companion, context, {}, {})
        identity["companion_type_preset"] = identity["visual_profile"].get("companion_type_preset", "custom")
        return identity
    role = str(metadata.get("runtime_role") or metadata.get("role") or asset.get("runtime_role") or asset.get("role") or infer_asset_role(asset) or "").lower()
    category = str(metadata.get("gallery_category") or asset.get("gallery_category") or normalize_frontend_gallery_kind(asset.get("kind")) or role or "npc").lower()
    if role in {"player", "companion"}:
        role = "npc"
    if category in {"", "character", "gallery_npc", "npc_portrait"}:
        category = "npc"
    if role in {"item", "scene", "map", "monster", "cg"}:
        category = role
    if category in {"master", "servant", "npc", "monster"}:
        role = "npc" if category in {"master", "servant"} else category
    entity_key = existing_entity_key or entity_key_for_asset(asset)
    if category in {"master", "servant"} and not entity_key.startswith(f"{category}:"):
        entity_key = f"{category}:{stable_entity_name(display or key)}"
    if category == "npc" and not entity_key.startswith("npc:"):
        entity_key = f"npc:{stable_entity_name(display or key)}"
    identity = _identity_template(role or category or "npc", entity_key, display)
    identity["gallery_category"] = category
    identity["visible_in_gallery"] = category != "hidden"
    return identity


def add_migration_note(entry: dict[str, Any], note: str) -> None:
    notes = entry.setdefault("migration_notes", [])
    if isinstance(notes, list) and note not in notes:
        notes.append(note)


def apply_actor_identity_to_asset(entry: dict[str, Any], identity: dict[str, Any]) -> None:
    metadata = entry.setdefault("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
        entry["metadata"] = metadata
    old_kind = str(entry.get("kind") or "")
    old_role = str(metadata.get("role") or entry.get("role") or "")
    old_category = str(metadata.get("gallery_category") or entry.get("gallery_category") or "")
    old_visible = metadata.get("visible_in_gallery", entry.get("visible_in_gallery", None))
    entry["kind"] = identity["asset_kind"]
    entry["role"] = identity["role"]
    entry["entity_key"] = identity["entity_key"]
    entry["visible_in_gallery"] = bool(identity["visible_in_gallery"])
    metadata.update({
        "role": identity["role"],
        "runtime_role": identity["runtime_role"],
        "entity_key": identity["entity_key"],
        "avatar_key": identity["avatar_key"],
        "portrait_asset_kind": identity["portrait_asset_kind"],
        "gallery_category": identity["gallery_category"],
        "visible_in_gallery": bool(identity["visible_in_gallery"]),
        "not_in_gallery_filters": bool(identity["not_in_gallery_filters"]),
        "display_slot": identity["display_slot"],
        "detail_slot": identity["detail_slot"],
        "render_tier": identity["render_tier"],
    })
    for field in ("companion_type", "companion_type_raw", "companion_type_preset", "archetype", "species", "display_name"):
        if identity.get(field):
            metadata[field] = identity[field]
    if identity.get("visual_profile") and not isinstance(metadata.get("visual_profile"), dict):
        metadata["visual_profile"] = identity["visual_profile"]
    if identity["runtime_role"] == "player":
        if old_role != "player":
            add_migration_note(entry, "actor_role_corrected_to_player")
        if old_kind != "player_portrait":
            add_migration_note(entry, "portrait_kind_corrected_to_player_portrait")
    if identity["runtime_role"] == "companion":
        if old_role != "companion":
            add_migration_note(entry, "actor_role_corrected_to_companion")
        if old_kind != "companion_portrait":
            add_migration_note(entry, "portrait_kind_corrected_to_companion_portrait")
    if identity["runtime_role"] in {"player", "companion"}:
        if old_category and old_category != "hidden":
            add_migration_note(entry, "gallery_category_corrected_to_hidden_for_player_or_companion")
        if old_visible is not False:
            add_migration_note(entry, "visible_in_gallery_corrected_false_for_player_or_companion")


def is_gallery_visible_asset(asset: dict[str, Any]) -> bool:
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    if is_attribute_star_asset(asset):
        return False
    role = str(metadata.get("runtime_role") or metadata.get("role") or asset.get("runtime_role") or asset.get("role") or "").lower()
    category = str(metadata.get("gallery_category") or asset.get("gallery_category") or normalize_frontend_gallery_kind(asset.get("kind")) or "").lower()
    if asset.get("debug_only") or metadata.get("debug_only"):
        return False
    if asset.get("visible_in_gallery") is False or metadata.get("visible_in_gallery") is False:
        return False
    if metadata.get("not_in_gallery_filters") is True or asset.get("not_in_gallery_filters") is True:
        return False
    if category in {"", "hidden", "companion"}:
        return False
    if role in {"player", "companion"}:
        return False
    return True


def has_route_nodes(value: Any) -> bool:
    route = value if isinstance(value, dict) else {}
    nodes = route.get("nodes")
    return isinstance(nodes, list) and bool(nodes)


def is_valid_cached_map_asset(asset: dict[str, Any]) -> bool:
    if not isinstance(asset, dict):
        return False
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    kind = str(asset.get("kind") or "")
    key_text = " ".join(str(value or "") for value in (
        asset.get("key"), asset.get("path"), asset.get("filename"), kind,
        metadata.get("kind"), metadata.get("source"), metadata.get("object_id"),
    )).lower()
    if not asset.get("url") or asset.get("exists") is False:
        return False
    if asset.get("placeholder") or metadata.get("placeholder"):
        return False
    if any(token in key_text for token in ("placeholder", "empty_map", "base_map", "default_map")):
        return False
    normalized_kind = normalize_asset_kind(kind, metadata, str(asset.get("key") or ""))
    if normalized_kind not in {"map_image", "scene_image"} and kind != "map" and not kind.startswith("gallery_map"):
        return False
    return has_route_nodes(metadata.get("map_route")) or has_route_nodes(asset.get("map_route"))


def is_vcg_avatar_asset(asset: dict[str, Any]) -> bool:
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    text = " ".join(str(value or "") for value in (
        asset.get("key"), asset.get("path"), asset.get("filename"),
        metadata.get("avatar_source"), metadata.get("source"), metadata.get("generator_version"),
    )).lower()
    return (
        ":vcg" in str(asset.get("key") or "").lower()
        or "_vcg" in text
        or str(metadata.get("avatar_source") or "").lower() == "vcg"
        or str(metadata.get("source") or "").lower() in {"formal_cg_crop", "cg_feedback", "manual_import_cg_crop", "vcg"}
        or str(metadata.get("generator_version") or "").upper() == "VCG"
    )


def avatar_asset_priority(asset: dict[str, Any]) -> tuple[int, int, str]:
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    if is_attribute_star_asset(asset):
        return (-1, 0, "")
    source = str(metadata.get("source") or metadata.get("avatar_source") or "").lower()
    if is_vcg_avatar_asset(asset):
        tier = 500
    elif source in {"manual_import_cg_crop", "formal_cg_crop", "cg_feedback"}:
        tier = 400
    elif int(asset.get("generator_version") or 0) >= 17:
        tier = 300
    elif asset.get("placeholder") or metadata.get("placeholder"):
        tier = 0
    else:
        tier = 200
    try:
        version = int(asset.get("generator_version") or 0)
    except Exception:
        version = 0
    return (tier, version, str(asset.get("created_at") or asset.get("key") or ""))


def is_attribute_star_asset(asset: dict[str, Any]) -> bool:
    if not isinstance(asset, dict):
        return False
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    text = " ".join(str(value or "") for value in (
        asset.get("key"),
        asset.get("path"),
        asset.get("filename"),
        asset.get("kind"),
        asset.get("title"),
        asset.get("display_name"),
        metadata.get("kind"),
        metadata.get("source"),
        metadata.get("object_id"),
        metadata.get("title"),
        metadata.get("display_name"),
    )).lower()
    return "attribute_star" in text or "属性星图" in text or "六芒星" in text


def select_best_avatar_asset(entity_key: str, portrait_asset_kind: str, assets: list[dict[str, Any]]) -> dict[str, Any]:
    exact = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        if is_attribute_star_asset(asset):
            continue
        metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
        if str(metadata.get("entity_key") or asset.get("entity_key") or "") != entity_key:
            continue
        kind = normalize_asset_kind(asset.get("kind"), metadata, str(asset.get("key") or ""))
        portrait_kind = str(metadata.get("portrait_asset_kind") or kind)
        if portrait_kind != portrait_asset_kind and kind != portrait_asset_kind:
            continue
        exact.append(asset)
    if not exact:
        return {}
    return sorted(exact, key=avatar_asset_priority, reverse=True)[0]


def looks_like_hash_title(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(re.fullmatch(r"[0-9a-fA-F]{10,}", text) or re.fullmatch(r"[0-9a-fA-F]{6,}(?:[-_:][0-9a-fA-F]{4,})+", text))


def looks_like_generated_asset_title(title: Any, key: Any = "") -> bool:
    text = normalized_name(title)
    raw_key = normalized_name(key)
    if not text:
        return True
    if looks_like_hash_title(title):
        return True
    if re.search(r"[0-9a-f]{10,}", text) and any(token in raw_key for token in ("npcportrait", "playerportrait", "companionportrait", "itemicon", "gallery")):
        return True
    if any(token in text for token in ("npcportrait", "playerportrait", "companionportrait", "itemicon", "gallerynpc", "galleryitem")):
        return True
    return False


def migrateAssetKinds(manifest: dict[str, Any], entityIndex: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        return manifest
    assets = manifest.setdefault("assets", {})
    if not isinstance(assets, dict):
        return manifest
    changed = False
    context = entityIndex if isinstance(entityIndex, dict) else {}
    for key, entry in list(assets.items()):
        if not isinstance(entry, dict):
            continue
        metadata = entry.setdefault("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
            entry["metadata"] = metadata
        before = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        identity = resolve_entity_role({"key": key, **entry, "metadata": metadata}, context, entry)
        if identity.get("runtime_role") in {"player", "companion"}:
            apply_actor_identity_to_asset(entry, identity)
            normalized_kind = str(entry.get("kind") or "")
        else:
            role = infer_asset_role({"key": key, **entry, "metadata": metadata})
            normalized_kind = normalize_asset_kind(entry.get("kind"), metadata, key)
            entry["kind"] = normalized_kind
            if role:
                metadata["role"] = role
                metadata["runtime_role"] = metadata.get("runtime_role") or role
            metadata["entity_key"] = metadata.get("entity_key") or entity_key_for_asset({"key": key, **entry, "metadata": metadata})
            category = str(metadata.get("gallery_category") or normalize_frontend_gallery_kind(normalized_kind) or role or "").lower()
            if category == "companion":
                category = "npc"
            if normalized_kind == "npc_portrait" and category in {"", "character", "portrait"}:
                category = "npc"
            if category:
                metadata["gallery_category"] = category
            if normalized_kind == "npc_portrait" and metadata.get("runtime_role") not in {"player", "companion"}:
                metadata["role"] = "npc"
                metadata["runtime_role"] = "npc"
                metadata["portrait_asset_kind"] = "npc_portrait"
                metadata["render_tier"] = "npc"
                metadata.setdefault("display_slot", "dossier_gallery")
                metadata.setdefault("detail_slot", "dossier_detail")
                metadata["visible_in_gallery"] = metadata.get("visible_in_gallery", entry.get("visible_in_gallery", True))
                entry["visible_in_gallery"] = bool(metadata["visible_in_gallery"])
        display = asset_display_name({"key": key, **entry, "metadata": metadata})
        if display:
            metadata.setdefault("display_name", display)
        title = metadata.get("display_name") or metadata.get("title") or ""
        if normalized_kind == "attribute_star":
            entry["visible_in_gallery"] = False
            entry["debug_only"] = True
            metadata["visible_in_gallery"] = False
            metadata["debug_only"] = True
        elif identity.get("runtime_role") not in {"player", "companion"} and (not title or looks_like_generated_asset_title(title, key)) and normalized_kind in {"npc_portrait", "companion_portrait"}:
            entry["visible_in_gallery"] = False
            entry["debug_only"] = True
            metadata["visible_in_gallery"] = False
            metadata["debug_only"] = True
        elif normalized_kind in GALLERY_VISIBLE_KINDS and identity.get("runtime_role") not in {"player", "companion"}:
            entry["visible_in_gallery"] = bool(metadata.get("visible_in_gallery", entry.get("visible_in_gallery", True)))
            metadata["visible_in_gallery"] = entry.get("visible_in_gallery", True)
        note = f"asset_kind_migrated:{normalized_kind}"
        notes = entry.setdefault("migration_notes", [])
        if isinstance(notes, list) and note not in notes and before != json.dumps(entry, ensure_ascii=False, sort_keys=True):
            notes.append(note)
        if before != json.dumps(entry, ensure_ascii=False, sort_keys=True):
            changed = True
    if changed:
        manifest["_migration_changed"] = True
    return manifest


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
    if str(entry.get("campaign_id") or campaign_id) != campaign_id:
        return {"ok": True, "exists": False}
    rel_path = str(entry.get("path", ""))
    try:
        full = safe_asset_read_path(campaign_id, rel_path)
    except Exception:
        return {"ok": True, "exists": False}
    if not rel_path or not full.exists():
        return {"ok": True, "exists": False}
    url_path = rel_path.replace("\\", "/")
    if url_path.startswith("assets/"):
        url_path = url_path[len("assets/"):]
    return {
        "ok": True,
        "exists": True,
        "key": key,
        "entry": normalized_asset_entry(campaign_id, key, entry),
        "url": f"/campaign-assets/{safe_segment(campaign_id)}/{url_path}",
    }



def asset_entry_payload(campaign_id: str, key: str, entry: dict[str, Any]) -> dict[str, Any]:
    entry = normalized_asset_entry(campaign_id, key, entry)
    if entry.get("placeholder") or entry.get("metadata", {}).get("placeholder"):
        return {}
    rel_path = str(entry.get("path", ""))
    try:
        full = safe_asset_read_path(campaign_id, rel_path)
    except Exception:
        full = Path()
    url_path = rel_path.replace("\\", "/")
    if url_path.startswith("assets/"):
        url_path = url_path[len("assets/"):]
    return {
        "campaign_id": campaign_id,
        "asset_seed": entry.get("asset_seed") or campaign_asset_seed(campaign_id),
        "key": key,
        "kind": entry.get("kind", ""),
        "path": rel_path,
        "exists": bool(rel_path and full.exists()),
        "url": f"/campaign-assets/{safe_segment(campaign_id)}/{url_path}" if rel_path else "",
        "generator_version": entry.get("generator_version", 1),
        "metadata": entry.get("metadata", {}),
        "entity_key": entry.get("entity_key", ""),
        "role": entry.get("role", ""),
        "display_name": entry.get("display_name", ""),
        "visible_in_gallery": entry.get("visible_in_gallery", True),
        "debug_only": entry.get("debug_only", False),
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
        normalized = normalized_asset_entry(campaign_id, key, entry)
        if normalized.get("campaign_id") != campaign_id:
            continue
        if normalized.get("placeholder") or normalized.get("metadata", {}).get("placeholder"):
            continue
        if is_attribute_star_asset(normalized):
            continue
        if normalize_asset_kind(normalized.get("kind"), normalized.get("metadata", {}), normalized.get("key", "")) == "map_image" and not is_valid_cached_map_asset(normalized):
            continue
        if kind and str(entry.get("kind", "")) != kind:
            continue
        payload = asset_entry_payload(campaign_id, key, normalized)
        if payload:
            entries.append(payload)
    entries.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return {"ok": True, "campaign_id": campaign_id, "assets": entries}


def normalized_asset_entry(campaign_id: str, key: str, entry: dict[str, Any]) -> dict[str, Any]:
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    normalized = {**entry, "key": str(entry.get("key") or key), "metadata": metadata}
    role = infer_asset_role(normalized)
    kind = normalize_asset_kind(entry.get("kind", ""), metadata, key)
    entity_key = str(metadata.get("entity_key") or entry.get("entity_key") or entity_key_for_asset({**normalized, "kind": kind}))
    display_name = asset_display_name({**normalized, "kind": kind})
    visible = entry.get("visible_in_gallery", metadata.get("visible_in_gallery", True))
    debug_only = bool(entry.get("debug_only") or metadata.get("debug_only"))
    runtime_role = str(metadata.get("runtime_role") or role or "").lower()
    gallery_category = str(metadata.get("gallery_category") or normalize_frontend_gallery_kind(kind) or "").lower()
    not_in_filters = bool(metadata.get("not_in_gallery_filters") or entry.get("not_in_gallery_filters"))
    if runtime_role in {"player", "companion"} or gallery_category == "hidden" or not_in_filters:
        visible = False
    return {
        **entry,
        "campaign_id": str(entry.get("campaign_id") or campaign_id),
        "asset_seed": str(entry.get("asset_seed") or campaign_asset_seed(campaign_id)),
        "key": str(entry.get("key") or key),
        "kind": kind,
        "role": role,
        "runtime_role": runtime_role,
        "entity_key": entity_key,
        "display_name": display_name,
        "visible_in_gallery": bool(visible) and not debug_only,
        "gallery_category": gallery_category,
        "not_in_gallery_filters": not_in_filters,
        "portrait_asset_kind": str(metadata.get("portrait_asset_kind") or kind),
        "render_tier": str(metadata.get("render_tier") or ""),
        "debug_only": debug_only,
        "metadata": {
            **metadata,
            "role": metadata.get("role") or role,
            "runtime_role": runtime_role or metadata.get("role") or role,
            "entity_key": entity_key,
            "display_name": metadata.get("display_name") or display_name,
            "visible_in_gallery": bool(visible) and not debug_only,
            "gallery_category": gallery_category,
            "not_in_gallery_filters": not_in_filters,
            "portrait_asset_kind": metadata.get("portrait_asset_kind") or kind,
            "render_tier": metadata.get("render_tier") or "",
            "debug_only": debug_only,
        },
    }


def module_payload_response(module_name: str, campaign_id: str = "", cursor: str = "", limit: str = "", kind: str = "") -> dict[str, Any]:
    resolved = MemoryStore().resolve_campaign_id(campaign_id or None)
    safe_limit = max(1, min(120, int(limit or 40))) if str(limit or "").isdigit() else 40
    offset = max(0, int(cursor or 0)) if str(cursor or "").isdigit() else 0
    state = campaign_state(resolved)
    output = output_payload(resolved, require_parse_ready=True)
    if module_name == "story-log":
        parsed = output.get("parsed", {}) if isinstance(output.get("parsed"), dict) else {}
        blocks = parsed.get("blocks", []) if isinstance(parsed.get("blocks"), list) else []
        rows = blocks[offset:offset + safe_limit]
        return {
            "ok": True,
            "campaign_id": resolved,
            "module": "story_log",
            "payload": {
                "campaign_id": resolved,
                "source": output.get("source", ""),
                "blocks": rows,
                "summary": parsed.get("summary", ""),
                "body": parsed.get("body", "") if offset == 0 else "",
                "choices": parsed.get("choices", "") if offset == 0 else "",
            },
            "next_cursor": str(offset + safe_limit) if offset + safe_limit < len(blocks) else "",
        }
    if module_name == "gallery":
        assets = asset_list(resolved).get("assets", [])
        gallery = frontend_gallery(resolved, state, output, assets)
        rows = gallery.get("assets", []) if isinstance(gallery.get("assets"), list) else []
        if kind and kind != "all":
            rows = [row for row in rows if str(row.get("kind") or "") == kind]
        page = rows[offset:offset + safe_limit]
        return {
            "ok": True,
            "campaign_id": resolved,
            "module": "gallery",
            "payload": {"filters": gallery.get("filters", []), "taxonomy": gallery.get("taxonomy", {}), "assets": page},
            "next_cursor": str(offset + safe_limit) if offset + safe_limit < len(rows) else "",
        }
    if module_name == "map-panel":
        assets = asset_list(resolved).get("assets", [])
        recent = state.get("recent", {}) if isinstance(state.get("recent"), dict) else {}
        scene = recent.get("current_scene", {}) if isinstance(recent.get("current_scene"), dict) else {}
        return {"ok": True, "campaign_id": resolved, "module": "map_panel", "payload": frontend_map_panel(resolved, scene, output, assets)}
    if module_name == "inventory":
        return {"ok": True, "campaign_id": resolved, "module": "inventory", "payload": frontend_inventory(state)}
    if module_name == "dossier":
        return {"ok": True, "campaign_id": resolved, "module": "dossier", "payload": frontend_dossier(state)}
    return {"ok": False, "error": f"unknown module: {module_name}"}


def safe_asset_read_path(campaign_id: str, rel_path: str) -> Path:
    if not rel_path:
        raise RuntimeError("asset path is empty")
    root = (CAMPAIGNS_DIR / safe_segment(campaign_id) / "assets").resolve()
    target = (CAMPAIGNS_DIR / safe_segment(campaign_id) / rel_path).resolve()
    if root not in target.parents and target != root:
        raise RuntimeError("asset path escapes campaign assets")
    if target.suffix.lower() != ".png":
        raise RuntimeError("only PNG assets are readable")
    return target


def frontend_state_response(campaign_id: str = "") -> dict[str, Any]:
    store = MemoryStore()
    registry = store.load_registry()
    resolved = store.resolve_campaign_id(campaign_id or None) if (campaign_id or registry.get("active_campaign")) else ""
    if not resolved:
        job = JOB.snapshot()
        return {
            "ok": True,
            "project_root": str(PROJECT_ROOT),
            "active_campaign": "",
            "campaigns": registry.get("campaigns", {}),
            "campaign_list": campaign_list(registry),
            "campaign_state": {},
            "chatgpt_project": "",
            "chatgpt_conversation": "",
            "job": job,
            "streaming_preview": streaming_preview_enabled(),
            "pipeline": {},
            "output": empty_output_payload("", "no active campaign"),
            "frontend_state": {},
        }
    campaigns = registry.get("campaigns", {})
    current = campaigns.get(resolved, {})
    state = campaign_state(resolved)
    output = output_payload(resolved, require_parse_ready=True)
    assets = asset_list(resolved).get("assets", [])
    frontend = build_frontend_state(resolved, current, state, output, assets)
    output_shell = lightweight_output_shell(output)
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
        "streaming_preview": streaming_preview_enabled(),
        "pipeline": frontend_pipeline_status(resolved, output, job),
        "output": output_shell,
        "frontend_state": frontend,
    }


def lightweight_output_shell(output: dict[str, Any]) -> dict[str, Any]:
    parsed = output.get("parsed") if isinstance(output.get("parsed"), dict) else {}
    return {
        "campaign_id": output.get("campaign_id", ""),
        "source": output.get("source", ""),
        "parsed": {
            "body": "",
            "choices": "",
            "summary": parsed.get("summary", ""),
            "blocks": [],
        },
        "pressure_pack": output.get("pressure_pack", {}) if isinstance(output.get("pressure_pack"), dict) else {},
        "audit_result": output.get("audit_result", {}) if isinstance(output.get("audit_result"), dict) else {},
        "ai_flavor_report": output.get("ai_flavor_report", {}) if isinstance(output.get("ai_flavor_report"), dict) else {},
        "image_job": output.get("image_job", {}) if isinstance(output.get("image_job"), dict) else {},
        "stage": output.get("stage", ""),
        "warning": output.get("warning", ""),
    }


def build_frontend_state(campaign_id: str, meta: dict[str, Any], state: dict[str, Any], output: dict[str, Any], assets: list[dict[str, Any]]) -> dict[str, Any]:
    recent = state.get("recent", {}) if isinstance(state.get("recent"), dict) else {}
    scene = recent.get("current_scene", {}) if isinstance(recent.get("current_scene"), dict) else {}
    setup = frontend_campaign_setup(campaign_id, state)
    profile = {
        "id": campaign_id,
        "title": state.get("title") or meta.get("name") or campaign_id,
        "asset_seed": campaign_asset_seed(campaign_id),
        "genre": state.get("genre", ""),
        "tone": state.get("tone", ""),
        "template": setup["template"],
        "chapter": campaign_chapter(campaign_id),
        "status": meta.get("status", ""),
        "binding": {
            "project_name": meta.get("chatgpt_project_name", ""),
            "conversation_name": meta.get("chatgpt_conversation_name", ""),
        },
        "scene": scene,
    }
    gallery_payload_ref = f"/api/module/gallery?campaign_id={safe_segment(campaign_id)}&limit=60"
    story_log_payload_ref = f"/api/module/story-log?campaign_id={safe_segment(campaign_id)}&limit=20"
    gallery_taxonomy = gallery_taxonomy_for_campaign(campaign_id, state)
    gallery = {"filters": gallery_filters_from_taxonomy(gallery_taxonomy), "taxonomy": gallery_taxonomy, "assets": [], "payload_ref": gallery_payload_ref}
    story_progress_payload = frontend_story_progress_payload(campaign_id)
    map_panel = frontend_map_panel(campaign_id, scene, output, assets)
    visual_registry = build_visual_registry(campaign_id, state, assets)
    pressure = normalize_pressure_pack_compat(output.get("pressure_pack", {}) if isinstance(output.get("pressure_pack"), dict) else {})
    action_path = resolve_outbox_dir(campaign_id) / "last_player_action.txt"
    last_player_action = read_runtime_text(action_path).strip() if action_path.exists() else ""
    frontend_base = {
        "asset_seed": profile["asset_seed"],
        "module_refs": {
            "story_log": story_log_payload_ref,
            "gallery": gallery_payload_ref,
            "map_panel": f"/api/module/map-panel?campaign_id={safe_segment(campaign_id)}",
            "inventory": f"/api/module/inventory?campaign_id={safe_segment(campaign_id)}",
            "dossier": f"/api/module/dossier?campaign_id={safe_segment(campaign_id)}",
        },
        "story_log": {
            "campaign_id": output.get("campaign_id", campaign_id),
            "source": output.get("source", ""),
            "blocks": [],
            "summary": output.get("parsed", {}).get("summary", "") if isinstance(output.get("parsed"), dict) else "",
        },
    }
    modules = build_frontend_modules(campaign_id, frontend_base, pressure, assets, story_progress_payload)
    return {
        "schema": "trpg_orchestrator.frontend_state.v1",
        "asset_seed": profile["asset_seed"],
        "campaign": profile,
        "template": setup["template"],
        "rules_config": setup["rules_config"],
        "companion_config": setup["companion_config"],
        "model_config_summary": setup["model_config_summary"],
        "safety_lines": setup["safety_lines"],
        "roll_actions": setup["roll_actions"],
        "last_player_action": last_player_action,
        "character_card": frontend_character_card(campaign_id, state, setup["rules_config"]),
        "companion_card": frontend_companion_card(campaign_id, state, setup["companion_config"]),
        "map_panel": map_panel,
        "quests": frontend_quests(state),
        "inventory": frontend_inventory(state),
        "gallery": gallery,
        "gallery_taxonomy": gallery_taxonomy,
        "visual_registry": visual_registry,
        "avatar_index": visual_registry.get("avatar_index", {}),
        "story_progress": story_progress_payload,
        "modules": modules,
        "story_log": {
            "campaign_id": output.get("campaign_id", campaign_id),
            "source": output.get("source", ""),
            "blocks": [],
            "summary": output.get("parsed", {}).get("summary", "") if isinstance(output.get("parsed"), dict) else "",
            "payload_ref": story_log_payload_ref,
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


def frontend_campaign_setup(campaign_id: str, state: dict[str, Any]) -> dict[str, Any]:
    root = CAMPAIGNS_DIR / safe_segment(campaign_id)
    profile = read_json(root / "campaign_profile.json") if (root / "campaign_profile.json").exists() else {}
    if not isinstance(profile, dict):
        profile = {}
    template = str(profile.get("template") or "custom").strip().lower()
    if template not in {"custom", "coc", "dnd"}:
        template = "custom"
    rules_config = normalize_rules_config(profile.get("rules_config"))
    raw_companion_config = profile.get("companion_config")
    companion_config = normalize_companion_config(raw_companion_config)
    if not isinstance(raw_companion_config, dict) and legacy_companion_available(state):
        companion_config["companion_enabled"] = True
        companion_config["companion_mode"] = "auto"
    return {
        "template": template,
        "rules_config": rules_config,
        "story_config": normalize_story_config(profile.get("story_config", {})),
        "companion_config": companion_config,
        "model_config_summary": summarize_model_config(profile.get("model_config")),
        "safety_lines": list_payload(profile.get("safety_lines")),
        "roll_actions": frontend_roll_actions(rules_config),
    }


def normalize_rules_config(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    stat_visibility = str(source.get("stat_visibility") or "narrative").strip()
    if stat_visibility not in {"narrative", "hybrid", "numeric"}:
        stat_visibility = "narrative"
    rules_strictness = str(source.get("rules_strictness") or "light").strip()
    if rules_strictness not in {"light", "standard", "strict"}:
        rules_strictness = "light"
    dice_enabled = bool(source.get("dice_enabled"))
    attribute_config = source.get("attribute_config") if isinstance(source.get("attribute_config"), dict) else {}
    attribute_roll_config = source.get("attribute_roll_config") if isinstance(source.get("attribute_roll_config"), dict) else {}
    return {
        "character_card_enabled": bool(source.get("character_card_enabled", True)),
        "stat_visibility": stat_visibility,
        "attribute_config": {
            "enabled": bool(attribute_config.get("enabled", True)),
            "visible": bool(attribute_config.get("visible", True)),
            "theme": str(attribute_config.get("theme") or attribute_config.get("six_source") or "generic").strip(),
            "cap": int(attribute_config.get("cap") or 20),
            "float_ratio": float(attribute_config.get("float_ratio") or 1.2),
            "three_enabled": bool(attribute_config.get("three_enabled", True)),
            "six_enabled": bool(attribute_config.get("six_enabled", True)),
            "six_source": str(attribute_config.get("six_source") or "").strip(),
        },
        "attribute_roll_config": {
            "enabled": bool(attribute_roll_config.get("enabled", True)),
            "method": str(attribute_roll_config.get("method") or "balanced_random").strip(),
            "min": int(attribute_roll_config.get("min") or 6),
            "max": int(attribute_roll_config.get("max") or 18),
        },
        "dice_enabled": dice_enabled,
        "dice_type": str(source.get("dice_type") or "").strip() if dice_enabled else "",
        "roll_mode": str(source.get("roll_mode") or "").strip() if dice_enabled else "",
        "roll_attributes": list_payload(source.get("roll_attributes")) if dice_enabled else [],
        "rules_strictness": rules_strictness,
    }


def normalize_companion_config(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    enabled = bool(source.get("companion_enabled"))
    mode = str(source.get("companion_mode") or "auto").strip()
    if mode not in {"auto", "manual"}:
        mode = "auto"
    return {
        "companion_enabled": enabled,
        "companion_mode": mode if enabled else "auto",
        "companion_name": str(source.get("companion_name") or "").strip() if enabled else "",
        "companion_role": str(source.get("companion_role") or "").strip() if enabled else "",
        "companion_personality": str(source.get("companion_personality") or "").strip() if enabled else "",
        "companion_card_visible": bool(source.get("companion_card_visible")) if enabled else False,
    }


def normalize_story_config(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    try:
        return resolve_story_config(source.get("story_length") or "medium")
    except RuntimeError:
        return resolve_story_config("medium")


def legacy_companion_available(state: dict[str, Any]) -> bool:
    prompt = state.get("character_prompt", {}) if isinstance(state.get("character_prompt"), dict) else {}
    player = state.get("player", {}) if isinstance(state.get("player"), dict) else {}
    provided = first_dict(player.get("character_card"), prompt.get("character_card"))
    identity = first_dict(provided.get("identity"), player.get("confirmed_identity"), prompt.get("confirmed_identity"))
    source = first_dict(provided.get("companion"), prompt.get("companion_card"))
    return bool(source.get("name") or identity.get("companion"))


def summarize_model_config(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    raw_slots = source.get("model_slots") if isinstance(source.get("model_slots"), dict) else {}
    slots: dict[str, Any] = {}
    for key in ("director", "actor", "single"):
        slot = raw_slots.get(key) if isinstance(raw_slots.get(key), dict) else {}
        slots[key] = {
            "enabled": bool(slot.get("enabled")),
            "provider_type": str(slot.get("provider_type") or "").strip(),
            "base_url": str(slot.get("base_url") or "").strip(),
            "model_name": str(slot.get("model_name") or "").strip(),
            "has_api_key_ref": bool(str(slot.get("api_key_ref") or "").strip()),
        }
    return {
        "model_mode": normalize_model_mode(source.get("model_mode") or "dual_director_actor"),
        "director_model": str(source.get("director_model") or "").strip(),
        "actor_model": str(source.get("actor_model") or "").strip(),
        "single_model": str(source.get("single_model") or "").strip(),
        "model_slots": slots,
        "custom_provider": str(source.get("custom_provider") or "").strip(),
        "custom_base_url": str(source.get("custom_base_url") or "").strip(),
        "custom_model_name": str(source.get("custom_model_name") or "").strip(),
        "custom_role": str(source.get("custom_role") or "").strip(),
        "has_custom_api_key_ref": bool(str(source.get("custom_api_key_ref") or "").strip()),
    }


def frontend_roll_actions(rules_config: dict[str, Any]) -> list[dict[str, str]]:
    if not rules_config.get("dice_enabled"):
        return []
    dice_type = str(rules_config.get("dice_type") or "").strip()
    roll_mode = str(rules_config.get("roll_mode") or "").strip()
    rows = []
    for label in list_payload(rules_config.get("roll_attributes")):
        key = safe_segment(label.lower()) or f"roll_{len(rows) + 1}"
        rows.append({"key": key, "label": label, "dice_type": dice_type, "roll_mode": roll_mode, "icon": "dice"})
    return rows


def campaign_chapter(campaign_id: str) -> str:
    root = CAMPAIGNS_DIR / safe_segment(campaign_id)
    profile = read_json(root / "campaign_profile.json") if (root / "campaign_profile.json").exists() else {}
    recent = read_json(root / "recent_context.json") if (root / "recent_context.json").exists() else {}
    scene = recent.get("current_scene", {}) if isinstance(recent.get("current_scene"), dict) else {}
    return profile.get("chapter", "") or scene.get("chapter", "") or recent.get("chapter", "") or scene.get("time", "")


def frontend_character_card(campaign_id: str, state: dict[str, Any], rules_config: dict[str, Any] | None = None) -> dict[str, Any]:
    if rules_config is None:
        rules_config = frontend_campaign_setup(campaign_id, state)["rules_config"]
    if rules_config.get("character_card_enabled") is False:
        return {"enabled": False, "stat_visibility": rules_config.get("stat_visibility", "narrative"), "reason": "character_card_disabled"}
    prompt = state.get("character_prompt", {}) if isinstance(state.get("character_prompt"), dict) else {}
    player = state.get("player", {}) if isinstance(state.get("player"), dict) else {}
    provided = first_dict(player.get("character_card"), prompt.get("character_card"))
    identity = first_dict(provided.get("identity"), player.get("confirmed_identity"), prompt.get("confirmed_identity"))
    recent = state.get("recent", {}) if isinstance(state.get("recent"), dict) else {}
    scene = recent.get("current_scene", {}) if isinstance(recent.get("current_scene"), dict) else {}
    fallback = character_fallback_profile(campaign_id, state, scene)
    name = str(identity.get("name") or inferred_player_name(player, prompt) or state.get("title") or "玩家角色")
    identity_text = " / ".join([str(x) for x in (identity.get("ancestry"), identity.get("class_or_role") or identity.get("role"), identity.get("level_or_stage")) if x]) or fallback["identity"]
    provided_attributes = provided.get("attributes")
    provided_vitals = provided.get("vitals")
    if not provided_vitals and isinstance(provided_attributes, dict):
        provided_vitals = build_character_vitals_from_three(provided_attributes)
    tag_source = provided.get("conditions") or provided.get("tags") or provided.get("badges")
    card = {
        "enabled": True,
        "stat_visibility": rules_config.get("stat_visibility", "narrative"),
        "name": name,
        "identity": identity_text,
        "visual_profile": build_player_visual_profile(campaign_id, state, provided),
        "portrait": {
            "asset_key": scoped_asset_key(campaign_id, "player_portrait", f"player:{name}"),
            "type": "player_full_body_pixel",
            "quality": "high",
        },
        "progress": normalize_frontend_progress(provided.get("progression"), fallback["progress"]),
        "core_stats": normalize_frontend_core_stats(provided_vitals, fallback["core_stats"]),
        "tags": normalize_frontend_tags(tag_source, fallback["tags"]),
        "attributes": normalize_frontend_attributes(provided_attributes, fallback["attributes"]),
    }
    return apply_stat_visibility_to_card(card, str(rules_config.get("stat_visibility") or "narrative"))


def apply_stat_visibility_to_card(card: dict[str, Any], stat_visibility: str) -> dict[str, Any]:
    if stat_visibility == "numeric":
        return card
    if stat_visibility == "hybrid":
        card["core_stats"] = [hybrid_stat_row(row, index) for index, row in enumerate(card.get("core_stats") or [])]
        card["attributes"] = [hybrid_attribute_row(row) for row in (card.get("attributes") or [])[:6]]
        return card
    card["progress"] = {"label": card.get("progress", {}).get("label", "状态"), "text": card.get("progress", {}).get("text") or "叙事记录", "percent": None}
    card["core_stats"] = narrative_status_rows(card.get("tags") or [])
    card["attributes"] = []
    return card


def narrative_status_rows(tags: list[Any]) -> list[dict[str, Any]]:
    labels = [str(item).strip() for item in tags if str(item).strip()]
    while len(labels) < 4:
        labels.append(["稳定", "受压", "疲惫", "轻伤"][len(labels)])
    return [{"key": f"narrative_{index}", "label": "状态", "text": label, "tone": ["green", "blue", "amber", "red"][index % 4]} for index, label in enumerate(labels[:4])]


def hybrid_stat_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    current = row.get("current")
    maximum = row.get("max") or row.get("maximum")
    percent = row.get("percent")
    if percent is None and isinstance(current, (int, float)) and isinstance(maximum, (int, float)) and maximum:
        percent = round(max(0, min(100, current / maximum * 100)))
    return {"key": row.get("key") or f"hybrid_{index}", "label": row.get("label") or "状态", "text": f"状态 {int(percent)}%" if isinstance(percent, (int, float)) else row.get("text", "状态记录"), "percent": percent, "tone": row.get("tone", "")}


def hybrid_attribute_row(row: dict[str, Any]) -> dict[str, Any]:
    percent = row.get("percent")
    return {"label": row.get("label") or row.get("short") or row.get("key") or "项", "text": f"{int(percent)}%" if isinstance(percent, (int, float)) else row.get("rank") or row.get("text") or "记录", "percent": percent}


def frontend_companion_card(campaign_id: str, state: dict[str, Any], companion_config: dict[str, Any] | None = None) -> dict[str, Any]:
    if companion_config is None:
        companion_config = frontend_campaign_setup(campaign_id, state)["companion_config"]
    if not companion_config.get("companion_enabled"):
        return {"enabled": False, "reason": "companion_disabled"}
    if companion_config.get("companion_mode") == "manual":
        name = str(companion_config.get("companion_name") or "").strip()
        if name:
            source = {"name": name, "role": companion_config.get("companion_role", ""), "personality": companion_config.get("companion_personality", ""), "source": "campaign_setup"}
            return {
                "enabled": True,
                "pending": False,
                "name": name,
                "identity": str(companion_config.get("companion_role") or "长期伙伴"),
                "archetype": "companion",
                "portrait": {"asset_key": scoped_asset_key(campaign_id, "companion_portrait", f"companion:{name}"), "type": "companion_portrait_pixel"},
                "visual_profile": build_companion_visual_profile(source, state, {}, {}),
                "meta": source,
            }
    prompt = state.get("character_prompt", {}) if isinstance(state.get("character_prompt"), dict) else {}
    player = state.get("player", {}) if isinstance(state.get("player"), dict) else {}
    provided = first_dict(player.get("character_card"), prompt.get("character_card"))
    identity = first_dict(provided.get("identity"), player.get("confirmed_identity"), prompt.get("confirmed_identity"))
    source = first_dict(provided.get("companion"), prompt.get("companion_card"))
    if not source and isinstance(identity.get("companion"), dict):
        source = identity.get("companion")
    if not source:
        return {"enabled": True, "pending": True, "name": "伙伴待生成", "identity": "长期伙伴待生成", "archetype": "companion", "meta": {"mode": companion_config.get("companion_mode", "auto")}}
    name = str(source.get("name") or "").strip()
    if not name:
        return {}
    archetype = "companion"
    identity_text = str(source.get("identity") or source.get("class") or source.get("species") or source.get("kind") or "伙伴")
    return {
        "enabled": True,
        "pending": False,
        "name": name,
        "identity": identity_text,
        "archetype": archetype,
        "portrait": {"asset_key": scoped_asset_key(campaign_id, "companion_portrait", f"companion:{name}"), "type": "companion_portrait_pixel"},
        "visual_profile": build_companion_visual_profile(source, state, {}, {}),
        "meta": source,
    }


def stable_entity_name(value: Any) -> str:
    return safe_segment(str(value or "unknown").lower())


def build_visual_registry(campaign_id: str, state: dict[str, Any], assets: list[dict[str, Any]]) -> dict[str, Any]:
    actors: dict[str, dict[str, Any]] = {}
    objects: dict[str, dict[str, Any]] = {}
    asset_key_index: dict[str, str] = {}
    role_index: dict[str, list[str]] = {}
    gallery_visibility: dict[str, bool] = {}
    avatar_index: dict[str, dict[str, Any]] = {}
    context = actor_identity_context_from_state(campaign_id, state)

    def add_entity(entity_key: str, role: str, display_name: str, asset: dict[str, Any] | None = None, fallback_seed: str = "", identity: dict[str, Any] | None = None) -> None:
        if not entity_key:
            return
        identity = identity or _identity_template(role, entity_key, display_name)
        if role in ROLE_PRIORITY:
            prefix = entity_key.split(":", 1)[0].lower() if ":" in entity_key else ""
            if prefix != role:
                entity_key = f"{role}:{stable_entity_name(display_name)}"
        expected_kind = identity.get("portrait_asset_kind") or ROLE_ASSET_KIND.get(role, normalize_asset_kind(asset.get("kind") if asset else role))
        asset_kind = normalize_asset_kind(asset.get("kind") if asset else "", asset.get("metadata") if asset else {}, asset.get("key", "") if asset else "") if asset else ""
        if asset and role in ACTOR_ROLES and asset_kind != expected_kind:
            asset = None
        selected = select_best_avatar_asset(entity_key, expected_kind, assets) if role in ACTOR_ROLES else (asset or {})
        if selected:
            asset = selected
        kind = expected_kind
        row = {
            "entity_key": entity_key,
            "runtime_role": identity.get("runtime_role") or role,
            "role": identity.get("role") or role,
            "companion_type": identity.get("companion_type", ""),
            "asset_kind": kind,
            "asset_key": asset.get("key", "") if asset else "",
            "url": asset.get("url", "") if asset else "",
            "selected_avatar_key": asset.get("key", "") if asset else "",
            "selected_avatar_url": asset.get("url", "") if asset else "",
            "display_name": display_name,
            "fallback_seed": fallback_seed or f"{campaign_id}:{entity_key}:{role}",
            "renderer": "item_icon" if role == "item" else "actor_portrait",
            "display_slot": identity.get("display_slot", ""),
            "gallery_category": identity.get("gallery_category", ""),
            "visible_in_gallery": bool(identity.get("visible_in_gallery", asset.get("visible_in_gallery", True) if asset else True)),
            "portrait_asset_kind": identity.get("portrait_asset_kind") or kind,
            "visual_profile": identity.get("visual_profile") if isinstance(identity.get("visual_profile"), dict) else {},
            "avatar_locked_by_vcg": bool(asset and is_vcg_avatar_asset(asset)),
        }
        bucket = objects if role in {"item", "scene", "map", "monster", "cg"} else actors
        existing = bucket.get(entity_key)
        if not existing or ROLE_PRIORITY.get(role, 99) <= ROLE_PRIORITY.get(existing.get("role"), 99):
            bucket[entity_key] = row
            if role in ACTOR_ROLES:
                avatar_index[entity_key] = {
                    "entity_key": entity_key,
                    "runtime_role": row["runtime_role"],
                    "display_slot": row["display_slot"],
                    "gallery_category": row["gallery_category"],
                    "selected_avatar_key": row["selected_avatar_key"],
                    "selected_avatar_url": row["selected_avatar_url"],
                    "companion_type": row.get("companion_type", ""),
                    "visible_in_gallery": row["visible_in_gallery"],
                    "portrait_asset_kind": row["portrait_asset_kind"],
                    "visual_profile": row.get("visual_profile", {}),
                    "avatar_locked_by_vcg": row["avatar_locked_by_vcg"],
                }
        if row["asset_key"]:
            asset_key_index[row["asset_key"]] = entity_key
        role_index.setdefault(role, [])
        if entity_key not in role_index[role]:
            role_index[role].append(entity_key)
        if row["asset_key"]:
            gallery_visibility[row["asset_key"]] = row["visible_in_gallery"]

    character = frontend_character_card(campaign_id, state)
    name_role_index: dict[str, tuple[str, str]] = {}
    if character.get("name"):
        entity_key = context.get("player", {}).get("entity_key") or f"player:{stable_entity_name(character['name'])}"
        name_role_index[normalized_name(character["name"])] = ("player", entity_key)
        identity = _identity_template("player", entity_key, character["name"])
        identity["visual_profile"] = character.get("visual_profile") if isinstance(character.get("visual_profile"), dict) else {}
        add_entity(entity_key, "player", character["name"], None, campaign_id, identity)
    companion = frontend_companion_card(campaign_id, state)
    if companion.get("name"):
        role = "companion"
        entity_key = context.get("companion", {}).get("entity_key") or f"companion:{stable_entity_name(companion['name'])}"
        name_role_index[normalized_name(companion["name"])] = (role, entity_key)
        identity = _identity_template("companion", entity_key, companion["name"])
        identity["companion_type"] = str(context.get("companion", {}).get("companion_type") or companion.get("archetype") or "generic")
        identity["archetype"] = str(context.get("companion", {}).get("archetype") or companion.get("archetype") or "")
        identity["species"] = str(context.get("companion", {}).get("species") or "")
        identity["visual_profile"] = companion.get("visual_profile") if isinstance(companion.get("visual_profile"), dict) else {}
        add_entity(entity_key, role, companion["name"], None, campaign_id, identity)
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        display = asset.get("display_name") or asset_display_name(asset) or readable_asset_name(asset.get("key", ""), asset.get("kind", ""))
        identity = resolve_entity_role(asset, context, asset)
        role = identity.get("runtime_role") or asset.get("role") or infer_asset_role(asset)
        entity_key = identity.get("entity_key") or asset.get("entity_key") or entity_key_for_asset(asset)
        known = name_role_index.get(normalized_name(display))
        if known and role not in {"player", "master", "item", "scene", "map", "monster", "cg"}:
            role, entity_key = known
        add_entity(entity_key, role or "item", display, asset, f"{campaign_id}:{entity_key}", identity)
    return {
        "actors": actors,
        "objects": objects,
        "asset_key_index": asset_key_index,
        "role_index": role_index,
        "gallery_visibility": gallery_visibility,
        "avatar_index": avatar_index,
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
    latest = next((item for item in assets if item.get("campaign_id") == campaign_id and is_valid_cached_map_asset(item)), {})
    if map_mode not in {"update_route", "update_canvas"}:
        if latest and latest.get("url"):
            return {
                "mode": "keep_previous",
                "state": "cached",
                "update_requested": False,
                "payload": {},
                "payload_ref": latest.get("url", ""),
                "reason": map_request.get("reason", "") or "current campaign cached map asset",
            }
        return {
            "mode": "keep_previous",
            "state": "empty",
            "update_requested": False,
            "payload": {},
            "payload_ref": "",
            "reason": "no current campaign map asset",
        }
    if not isinstance(route.get("nodes"), list) or not route.get("nodes"):
        return {
            "mode": "keep_previous",
            "state": "empty" if not latest else "cached",
            "update_requested": False,
            "payload": {},
            "payload_ref": latest.get("url", "") if latest else "",
            "reason": "map update requested without route nodes",
        }
    return {
        "latest_map": {
            "asset_key": latest.get("key") or f"{campaign_id}:{campaign_asset_seed(campaign_id)}:map:{safe_segment(scene.get('location') or campaign_id)}:route:v17",
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
        "mode": "update",
        "state": "ready",
        "update_requested": True,
        "payload": {
            "map_route": route,
            "map_canvas": canvas,
            "title": route.get("title") or scene.get("location") or "当前区域地图",
            "visual_assets": pressure.get("visual_assets", []),
        },
        "payload_ref": "",
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
            "payload_ref": map_panel.get("latest_map", {}).get("url") or "",
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


def frontend_dossier(state: dict[str, Any]) -> list[dict[str, Any]]:
    clues = state.get("clues", {}) if isinstance(state.get("clues"), dict) else {}
    npcs = state.get("npcs", {}) if isinstance(state.get("npcs"), dict) else {}
    rows = []
    for index, row in enumerate(normalize_memory_rows(clues.get("notes")) + normalize_memory_rows(clues.get("facts"))):
        rows.append({"id": f"clue_{index + 1}", "title": row["title"], "detail": row["detail"], "kind": "clue"})
    profiles = npcs.get("npcs") if isinstance(npcs.get("npcs"), dict) else {}
    for npc_id, npc in profiles.items():
        if not isinstance(npc, dict):
            continue
        detail_rows = normalize_memory_rows(npc.get("facts")) + normalize_memory_rows(npc.get("notes"))
        detail = "；".join(row["title"] for row in detail_rows[:2])
        rows.append({"id": str(npc_id), "title": str(npc.get("display_name") or npc.get("name") or npc_id), "detail": detail, "kind": "npc"})
    return rows[:80]


def frontend_gallery(campaign_id: str, state: dict[str, Any], output: dict[str, Any], assets: list[dict[str, Any]]) -> dict[str, Any]:
    taxonomy = gallery_taxonomy_for_campaign(campaign_id, state)
    filters = gallery_filters_from_taxonomy(taxonomy)
    allowed_kinds = gallery_allowed_filter_ids(filters)
    rows = []
    context = actor_identity_context_from_state(campaign_id, state)
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
        identity = resolve_entity_role(asset, context, asset)
        if identity.get("runtime_role") in {"player", "companion"}:
            continue
        if not is_gallery_visible_asset(asset):
            continue
        metadata = asset.get("metadata", {}) if isinstance(asset.get("metadata"), dict) else {}
        kind = str(metadata.get("gallery_category") or asset.get("gallery_category") or identity.get("gallery_category") or normalize_frontend_gallery_kind(asset.get("kind")))
        kind = coerce_gallery_kind_to_allowed(kind, allowed_kinds)
        if not kind:
            continue
        title = asset.get("display_name") or metadata.get("display_name") or metadata.get("title") or readable_asset_name(asset.get("key", ""), kind)
        if not is_gallery_cache_asset(asset, protected, inventory_titles, inventory_ids, active_npc_ids, kind, title):
            continue
        selected = select_best_avatar_asset(str(identity.get("entity_key") or asset.get("entity_key") or ""), str(identity.get("portrait_asset_kind") or asset.get("kind") or ""), assets)
        selected_key = selected.get("key") or asset.get("key", "")
        cached_url = selected.get("url") or asset.get("url", "")
        rows.append({
            "kind": kind,
            "key": selected_key,
            "title": title,
            "meta": metadata.get("meta") or kind,
            "detail": metadata.get("detail") or "",
            "cached_url": cached_url,
            "entity_key": identity.get("entity_key") or asset.get("entity_key", ""),
            "role": identity.get("role") or asset.get("role", ""),
            "runtime_role": identity.get("runtime_role", ""),
            "gallery_category": kind,
            "asset_kind": asset.get("kind", ""),
            "visible_in_gallery": asset.get("visible_in_gallery", True),
            "visual_prompt": metadata.get("visual_prompt") or {},
            "image_prompt": metadata.get("image_prompt") or {},
            "status": metadata.get("status") or metadata.get("current_status") or asset.get("status") or "",
            "created_at": asset.get("created_at", ""),
            "archived": bool(metadata.get("archived") or metadata.get("superseded")),
        })
    return {"filters": filters, "taxonomy": taxonomy, "assets": mark_frontend_scene_archive_state(dedupe_frontend_assets(rows))[:120]}


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
    return "companion"


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


def stable_actor_entity_id(name: Any) -> str:
    text = re.sub(r"\s+", "", str(name or ""))
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
    title = str(title or metadata.get("display_name") or metadata.get("title") or readable_asset_name(key, kind))
    role = str(asset.get("role") or metadata.get("role") or "").lower()
    if is_attribute_star_asset(asset):
        return False
    if asset.get("debug_only") or asset.get("visible_in_gallery") is False or metadata.get("debug_only") or metadata.get("visible_in_gallery") is False:
        return False
    if not title or looks_like_generated_asset_title(title, key):
        return False
    if normalized_kind == "scene":
        if kind in {"map", "map_image"} or metadata.get("source") == "map_route":
            return is_valid_cached_map_asset(asset)
        if kind not in {"scene_image"}:
            return False
    if normalized_name(title) in protected or normalized_name(metadata.get("object_id")) in protected:
        return False
    if role in {"player", "master"} and normalized_kind != role:
        return False
    if role == "companion" and normalized_kind != "companion":
        return False
    if normalized_kind == "npc" and role in {"player", "master", "companion"}:
        return False
    if kind in {"portrait", "player_portrait"}:
        return False
    if kind not in GALLERY_VISIBLE_KINDS and not kind.startswith("gallery_"):
        if kind != "npc_portrait":
            return False
    if kind == "npc_portrait":
        return normalized_kind not in {"", "hidden", "cg", "item", "scene", "map"}
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
    return {
        "identity": "角色 / 状态待确认",
        "progress": {"label": "进展", "text": "记录中", "percent": 0},
        "core_stats": [
            {"key": "condition", "label": "状态", "current": 60, "max": 100, "tone": "green", "text": "稳定"},
            {"key": "focus", "label": "专注", "current": 50, "max": 100, "tone": "blue", "text": "待记录"},
            {"key": "resource", "label": "资源", "current": 50, "max": 100, "tone": "amber", "text": "待记录"},
        ],
        "tags": ["稳定", "叙事记录", "待确认"],
        "attributes": [],
    }
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
    rows = [("all", "全部"), ("cg", "CG"), ("companion", "伙伴"), ("master", "御主"), ("npc", "NPC"), ("scene", "场景"), ("item", "物品")]
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
    if value in {"cg_image", "gallery_image"}:
        return "cg"
    if value == "companion_portrait":
        return "companion"
    if value == "master_portrait":
        return "master"
    if value in {"scene_image", "map_image"}:
        return "scene"
    if value == "npc_portrait":
        return "npc"
    if value == "monster_image":
        return "monster"
    if value == "item_icon":
        return "item"
    if "companion" in value:
        return "companion"
    if any(token in value for token in ("cg", "generated_cg", "gallery_image", "formal_cg", "剧情图", "生图")):
        return "cg"
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


def gallery_taxonomy_for_campaign(campaign_id: str, state: dict[str, Any]) -> dict[str, Any]:
    root = CAMPAIGNS_DIR / safe_segment(campaign_id)
    profile = read_json(root / "campaign_profile.json") if (root / "campaign_profile.json").exists() else {}
    profile = profile if isinstance(profile, dict) else {}
    taxonomy = profile.get("gallery_taxonomy") if isinstance(profile.get("gallery_taxonomy"), dict) else {}
    core = taxonomy.get("core_categories") if isinstance(taxonomy.get("core_categories"), list) else []
    if not core:
        core = [
            {"id": "cg", "label": "CG", "locked": True},
            {"id": "npc", "label": "NPC", "locked": True},
            {"id": "scene", "label": "Scene", "locked": True},
            {"id": "item", "label": "Item", "locked": True},
        ]
    campaign_rows = []
    for row in taxonomy.get("campaign_categories", []) if isinstance(taxonomy.get("campaign_categories"), list) else []:
        normalized = normalize_gallery_taxonomy_row(row, "campaign_profile")
        if normalized:
            campaign_rows.append(normalized)
    for source_key, source_name in (
        ("gallery_categories", "campaign_profile"),
        ("campaign_categories", "campaign_profile"),
    ):
        for row in profile.get(source_key, []) if isinstance(profile.get(source_key), list) else []:
            normalized = normalize_gallery_taxonomy_row(row, source_name)
            if normalized:
                campaign_rows.append(normalized)
    rules = profile.get("rules_config") if isinstance(profile.get("rules_config"), dict) else {}
    for row in rules.get("gallery_categories", []) if isinstance(rules.get("gallery_categories"), list) else []:
        normalized = normalize_gallery_taxonomy_row(row, "rules_config")
        if normalized:
            campaign_rows.append(normalized)
    template = str(profile.get("template") or state.get("template") or "").lower()
    if template in {"coc", "call_of_cthulhu"}:
        campaign_rows.extend([
            {"id": "clue", "label": "Clue", "source": "template"},
            {"id": "document", "label": "Document", "source": "template"},
            {"id": "location", "label": "Location", "source": "template"},
        ])
    elif template in {"dnd", "dnd5e"}:
        campaign_rows.extend([
            {"id": "monster", "label": "Monster", "source": "template"},
            {"id": "location", "label": "Location", "source": "template"},
            {"id": "magic_item", "label": "Magic Item", "source": "template"},
        ])
    elif template in {"fate"}:
        campaign_rows.extend([
            {"id": "master", "label": "Master", "source": "template"},
            {"id": "servant", "label": "Servant", "source": "template"},
        ])
    campaign_rows = dedupe_taxonomy_rows(campaign_rows, {row.get("id") for row in core if isinstance(row, dict)})
    return {
        "core_categories": dedupe_taxonomy_rows([normalize_gallery_taxonomy_row(row, "system") for row in core], set()),
        "campaign_categories": campaign_rows,
        "hidden_runtime_roles": ["player", "companion"],
        "rules": {
            "exclude_current_player_from_gallery": True,
            "exclude_current_companion_from_gallery": True,
            "dedupe_by_entity_key": True,
        },
    }


def normalize_gallery_taxonomy_row(row: Any, source: str = "inferred") -> dict[str, Any]:
    if isinstance(row, str):
        category_id = safe_segment(row.lower())
        label = row
    elif isinstance(row, dict):
        category_id = safe_segment(str(row.get("id") or row.get("key") or row.get("name") or "").lower())
        label = str(row.get("label") or row.get("title") or category_id).strip()
    else:
        return {}
    if not category_id or category_id in {"all", "hidden", "player", "companion", "companion_portrait"}:
        return {}
    result = {"id": category_id, "label": label or category_id, "source": source}
    if isinstance(row, dict) and row.get("locked") is not None:
        result["locked"] = bool(row.get("locked"))
    return result


def dedupe_taxonomy_rows(rows: list[dict[str, Any]], blocked: set[str]) -> list[dict[str, Any]]:
    seen = {str(item or "") for item in blocked}
    output = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        category_id = str(row.get("id") or "")
        if not category_id or category_id in seen:
            continue
        seen.add(category_id)
        output.append(row)
    return output


def gallery_filters_from_taxonomy(taxonomy: dict[str, Any]) -> list[dict[str, str]]:
    filters = [{"key": "all", "label": "All"}]
    core = taxonomy.get("core_categories") if isinstance(taxonomy.get("core_categories"), list) else []
    campaign = taxonomy.get("campaign_categories") if isinstance(taxonomy.get("campaign_categories"), list) else []
    for row in core + campaign:
        if not isinstance(row, dict):
            continue
        category_id = str(row.get("id") or "").strip()
        if category_id and category_id not in {"hidden", "player", "companion"}:
            filters.append({"key": category_id, "label": str(row.get("label") or category_id)})
    return filters


def gallery_filters_for_campaign(campaign_id: str, state: dict[str, Any]) -> list[dict[str, str]]:
    return gallery_filters_from_taxonomy(gallery_taxonomy_for_campaign(campaign_id, state))


def coerce_gallery_kind_to_allowed(kind: Any, allowed: set[str]) -> str:
    raw = str(kind or "").lower()
    if raw in {"hidden", "companion", "companion_portrait"}:
        return ""
    if "gallery_npc" in raw:
        return ""
    if any(token in raw for token in ("generated_cg", "gallery_image", "formal_cg", "cg_image")):
        return "cg" if "cg" in allowed else ""
    if raw in allowed:
        return raw
    value = normalize_frontend_gallery_kind(kind)
    if value in {"hidden", "companion"}:
        return ""
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


def readable_asset_name(key: str, kind: str) -> str:
    text = re.sub(r"^[^:]+:", "", str(key or kind or "asset"))
    text = re.sub(r":v\d+$", "", text).replace("_", " ").strip()
    return concise_text(text or kind, 18)


def dedupe_frontend_assets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    by_key: dict[str, dict[str, Any]] = {}
    output = []
    for row in rows:
        if row.get("entity_key"):
            key = str(row.get("entity_key"))
        elif row.get("kind") == "scene":
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
    asset_seed = str(payload.get("asset_seed") or campaign_asset_seed(campaign_id))
    if campaign_id not in key:
        raise RuntimeError("asset key must include campaign_id")
    if asset_seed and asset_seed not in key:
        raise RuntimeError("asset key must include asset_seed")
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    if is_placeholder_asset_payload(payload, metadata):
        raise RuntimeError("placeholder assets must not be saved")
    data_url = str(payload.get("data_url") or "")
    prefix = "data:image/png;base64,"
    if not data_url.startswith(prefix):
        raise RuntimeError("asset data_url must be a PNG data URL")
    raw = base64.b64decode(data_url[len(prefix):], validate=True)
    if len(raw) < 128:
        raise RuntimeError("empty PNG assets must not be saved")
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
        "campaign_id": campaign_id,
        "key": key,
        "path": rel_path.as_posix(),
        "kind": str(payload.get("kind") or subdir),
        "seed": str(payload.get("seed") or key),
        "asset_seed": asset_seed,
        "style": str(payload.get("style") or "canvas_pixel"),
        "generator_version": int(payload.get("generator_version") or 1),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if isinstance(metadata, dict):
        canonical_kind = normalize_asset_kind(payload.get("kind") or subdir, metadata, key)
        metadata.setdefault("role", infer_asset_role({"key": key, "kind": canonical_kind, "metadata": metadata}))
        metadata.setdefault("entity_key", entity_key_for_asset({"key": key, "kind": canonical_kind, "metadata": metadata}))
        if metadata.get("display_name") or metadata.get("title"):
            metadata.setdefault("visible_in_gallery", True)
        manifest["assets"][key]["metadata"] = metadata
        manifest["assets"][key]["kind"] = canonical_kind
        manifest["assets"][key]["role"] = metadata.get("role", "")
        manifest["assets"][key]["entity_key"] = metadata.get("entity_key", "")
        manifest["assets"][key]["visible_in_gallery"] = bool(metadata.get("visible_in_gallery", True))
    write_json(asset_manifest_path(campaign_id), manifest)
    return asset_lookup(campaign_id, key)


def is_placeholder_asset_payload(payload: dict[str, Any], metadata: dict[str, Any]) -> bool:
    text = " ".join(str(payload.get(name, "")) for name in ("key", "kind", "seed", "filename", "style"))
    text = f"{text} {metadata.get('title', '')} {metadata.get('source', '')} {metadata.get('status', '')}".lower()
    if payload.get("placeholder") or metadata.get("placeholder") or metadata.get("fallback"):
        return True
    if metadata.get("cache_policy") == "placeholder":
        return True
    if any(token in text for token in ("placeholder", "fallback", "default_trpg", "empty_map", "base_map")):
        return True
    route = metadata.get("map_route")
    if str(payload.get("kind") or "") == "map" and isinstance(route, dict) and not route.get("nodes"):
        return True
    return False



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


def streaming_preview_enabled() -> bool:
    return os.getenv("TRPG_STREAMING_PREVIEW", "").strip().lower() in {"1", "true", "yes", "on"}


def default_chatgpt_project_name() -> str:
    return os.getenv("TRPG_CHATGPT_PROJECT_NAME", "").strip() or os.getenv("TRPG_DEFAULT_CHATGPT_PROJECT", "").strip() or "TRPG 自动主持"


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
    if streaming_preview_enabled():
        env["TRPG_BROWSER_WORKER"] = "1"
        run_command_streaming(command, env)
        return
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


def run_command_streaming(command: list[str], env: dict[str, str]) -> None:
    process = subprocess.Popen(
        command,
        cwd=str(PROJECT_ROOT),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )

    def read_pipe(pipe: Any, is_error: bool = False) -> None:
        if pipe is None:
            return
        try:
            for line in pipe:
                if not is_error:
                    maybe_update_stream_from_line(line)
                    JOB.append_output(line)
                else:
                    JOB.append_error(line)
        finally:
            try:
                pipe.close()
            except Exception:
                pass

    threads = [
        threading.Thread(target=read_pipe, args=(process.stdout, False), daemon=True),
        threading.Thread(target=read_pipe, args=(process.stderr, True), daemon=True),
    ]
    for thread in threads:
        thread.start()
    returncode = process.wait()
    for thread in threads:
        thread.join(timeout=1)
    JOB.finish_code(returncode)


def maybe_update_stream_from_line(line: str) -> None:
    text = str(line or "").strip()
    if text.startswith(WORKER_STATUS_PREFIX):
        raw = text.removeprefix(WORKER_STATUS_PREFIX).strip()
        try:
            status = json.loads(raw)
        except Exception:
            return
        if isinstance(status, dict):
            JOB.update_public_status(status)
        return
    if not text.startswith(STREAM_SNAPSHOT_PREFIX):
        return
    encoded = text.removeprefix(STREAM_SNAPSHOT_PREFIX).strip()
    if not encoded:
        return
    try:
        decoded = base64.b64decode(encoded.encode("ascii")).decode("utf-8", errors="replace")
    except Exception:
        return
    JOB.update_stream_text(decoded)


def run_turn_stream_payload(job_id: str = "") -> dict[str, Any]:
    job = JOB.snapshot()
    if job_id and job.get("job_id") and job_id != job.get("job_id"):
        return {"ok": False, "error": "unknown or expired stream job", "job_id": job_id}
    return {
        "ok": True,
        "streaming_enabled": streaming_preview_enabled(),
        "job_id": job.get("job_id", ""),
        "running": bool(job.get("running")),
        "returncode": job.get("returncode"),
        "stream_text": job.get("stream_text", ""),
        "stream_updated_at": job.get("stream_updated_at", 0),
        "stage": job.get("stage", ""),
        "public_think": job.get("public_think", []),
        "public_note": job.get("public_note", ""),
        "needs_human_verification": job.get("needs_human_verification", False),
        "output_tail": str(job.get("output") or "")[-5000:],
        "error_tail": str(job.get("error") or "")[-5000:],
    }





def new_campaign_defaults_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "defaults": default_rule_bundle(),
        "templates": campaign_template_options(),
        "template_defaults": CAMPAIGN_TEMPLATE_DEFAULTS,
        "modes": ai_mode_options(),
    }


def ai_mode_options() -> list[dict[str, str]]:
    return [
        {"id": "dual_director_actor", "label": "V4 \u5bfc\u6f14 + GPT \u6f14\u5458", "director": "deepseek_v4", "actor": "chatgpt"},
        {"id": "single_model", "label": "\u5355\u6a21\u578b\u5168\u6d41\u7a0b", "director": "custom", "actor": "custom"},
        {"id": "custom_dual", "label": "\u81ea\u5b9a\u4e49\u53cc\u5c42\u63a5\u5165", "director": "custom", "actor": "custom"},
    ]


def campaign_template_options() -> list[dict[str, str]]:
    return [
        {"id": "custom", "label": "\u81ea\u5b9a\u4e49"},
        {"id": "coc", "label": "COC"},
        {"id": "dnd", "label": "DND"},
    ]


COC_DEFAULT_PROMPT = "\u4e00\u7ec4\u8c03\u67e5\u5458\u6536\u5230\u4e00\u4efd\u5f02\u5e38\u59d4\u6258\uff0c\u524d\u5f80\u4e00\u5ea7\u88ab\u65e7\u6848\u3001\u5931\u8e2a\u8005\u548c\u5730\u65b9\u4f20\u95fb\u7b3c\u7f69\u7684\u57ce\u9547\u3002\u5e0c\u671b\u5f3a\u8c03\u7ebf\u7d22\u8c03\u67e5\u3001\u4eba\u7269\u5173\u7cfb\u3001\u7406\u667a\u538b\u529b\u3001\u8d44\u6599\u6863\u6848\u3001\u9690\u79d8\u771f\u76f8\u548c\u9010\u6b65\u5347\u7ea7\u7684\u5f02\u5e38\u611f\u3002\u4e0d\u8981\u8fc7\u65e9\u63ed\u9732\u771f\u76f8\u3002"
DND_DEFAULT_PROMPT = "\u4e00\u652f\u521d\u51fa\u8305\u5e90\u7684\u5192\u9669\u961f\u62b5\u8fbe\u8fb9\u5883\u57ce\u9547\uff0c\u7b2c\u4e00\u4efd\u59d4\u6258\u4e0e\u5931\u8e2a\u5546\u961f\u3001\u5730\u4e0b\u9057\u8ff9\u548c\u9644\u8fd1\u602a\u7269\u6d3b\u52a8\u6709\u5173\u3002\u5e0c\u671b\u5f3a\u8c03\u961f\u4f0d\u534f\u4f5c\u3001\u804c\u4e1a\u80fd\u529b\u3001\u63a2\u7d22\u3001\u8d44\u6e90\u6d88\u8017\u3001\u6218\u6597\u98ce\u9669\u548c\u9010\u6b65\u5c55\u5f00\u7684\u5192\u9669\u4e3b\u7ebf\u3002"


CAMPAIGN_TEMPLATE_DEFAULTS: dict[str, dict[str, Any]] = {
    "custom": {
        "name": "",
        "user_prompt": "",
        "character_card_enabled": True,
        "stat_visibility": "narrative",
        "dice_enabled": False,
        "dice_type": "",
        "roll_mode": "",
        "roll_attributes": [],
        "rules_strictness": "light",
    },
    "coc": {
        "name": "\u96fe\u6e2f\u8c03\u67e5\u6863\u6848",
        "user_prompt": COC_DEFAULT_PROMPT,
        "character_card_enabled": True,
        "stat_visibility": "numeric",
        "dice_enabled": True,
        "dice_type": "d100",
        "roll_mode": "percentile",
        "roll_attributes": ["\u4fa6\u67e5", "\u8046\u542c", "\u56fe\u4e66\u9986\u4f7f\u7528", "\u5fc3\u7406\u5b66", "\u95ea\u907f", "\u7406\u667a"],
        "rules_strictness": "standard",
    },
    "dnd": {
        "name": "\u8fb9\u5883\u5730\u57ce\u8fdc\u5f81",
        "user_prompt": DND_DEFAULT_PROMPT,
        "character_card_enabled": True,
        "stat_visibility": "numeric",
        "dice_enabled": True,
        "dice_type": "d20",
        "roll_mode": "d20_attribute",
        "roll_attributes": ["\u529b\u91cf", "\u654f\u6377", "\u4f53\u8d28", "\u667a\u529b", "\u611f\u77e5", "\u9b45\u529b"],
        "rules_strictness": "standard",
    },
}

def default_rule_bundle() -> dict[str, Any]:
    categories = [
        {
            "rule_id": "story_progress_rules",
            "title_zh": "故事与进度规则",
            "title_en": "Story and Progress Rules",
            "desc_zh": "控制故事篇幅、章节节奏、当前节点推进和不要过早揭露的信息。",
            "desc_en": "Controls story length, chapter pacing, node progress, and information that should not be revealed too early.",
            "files": ["story_progress_rules.md", "v4_campaign_context_prompt.md"],
        },
        {
            "rule_id": "character_attribute_rules",
            "title_zh": "角色卡与属性规则",
            "title_en": "Character Card and Attribute Rules",
            "desc_zh": "控制主角资料、属性值、角色卡显示和状态写回。",
            "desc_en": "Controls protagonist profile, attributes, character-card display, and state writeback.",
            "files": ["character_card_json_rules.md", "dice_check_rules_CN.md"],
        },
        {
            "rule_id": "style_rules",
            "title_zh": "正文风格规则",
            "title_en": "Prose Style Rules",
            "desc_zh": "控制叙事口吻、对白风格、画面感和避免 AI 味的写法。",
            "desc_en": "Controls prose tone, dialogue style, vivid scene writing, and anti-AI-flavor constraints.",
            "files": ["chatgpt_style_rules.md", "chatgpt_host_prompt.md"],
        },
        {
            "rule_id": "npc_monster_rules",
            "title_zh": "NPC / 怪物规则",
            "title_en": "NPC and Monster Rules",
            "desc_zh": "控制 NPC 行为、怪物生态、阵营关系和长期资料一致性。",
            "desc_en": "Controls NPC behavior, monster ecology, factions, and long-term dossier consistency.",
            "files": ["chatgpt_npc_voice_rules.md", "chatgpt_monster_rules.md"],
        },
        {
            "rule_id": "image_gallery_rules",
            "title_zh": "图像与资料规则",
            "title_en": "Image and Gallery Rules",
            "desc_zh": "控制地图、头像、CG、资料夹条目和可视化资产的生成与展示。",
            "desc_en": "Controls maps, portraits, CGs, dossiers, and visual asset display.",
            "files": ["chatgpt_image_rules.md", "visual_asset_protocol.md", "gallery_asset_rules.md"],
        },
        {
            "rule_id": "safety_rules",
            "title_zh": "安全边界规则",
            "title_en": "Safety Boundary Rules",
            "desc_zh": "控制禁忌内容、淡化内容、玩家边界和不可越过的叙事限制。",
            "desc_en": "Controls forbidden content, softened content, player boundaries, and hard narrative limits.",
            "files": ["forbidden_changes.json", "v4_audit_prompt.md"],
        },
        {
            "rule_id": "memory_writeback_rules",
            "title_zh": "记忆与写回规则",
            "title_en": "Memory and Writeback Rules",
            "desc_zh": "控制哪些事实可以长期记忆、哪些内容需要保持未确认，以及回合结束后的状态写入。",
            "desc_en": "Controls durable facts, uncertain information, and end-of-turn state writeback.",
            "files": ["state_writeback_schema.md", "v4_audit_prompt.md"],
        },
    ]
    return {"categories": categories}


def bool_payload(payload: dict[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "enabled"}


def list_payload(value: Any) -> list[str]:
    if isinstance(value, list):
        rows = value
    else:
        rows = re.split(r"[\n,，、]+", str(value or ""))
    return [str(item).strip() for item in rows if str(item).strip()]


def normalize_model_mode(value: Any) -> str:
    raw = str(value or "").strip()
    aliases = {
        "v4_director_chatgpt_api_actor": "dual_director_actor",
        "v4_api_chatgpt_conversation": "dual_director_actor",
        "dual": "dual_director_actor",
        "custom_model": "single_model",
        "deepseek_v4_only": "single_model",
        "chatgpt_only": "single_model",
    }
    mode = aliases.get(raw, raw or "dual_director_actor")
    valid = {row["id"] for row in ai_mode_options()}
    if mode not in valid:
        raise RuntimeError("invalid model_mode")
    return mode


STORY_LENGTH_CONFIGS: dict[str, dict[str, Any]] = {
    "short": {"title": "\u77ed\u7bc7", "target_total_chars": 30000, "target_chapters": 3, "target_nodes": 9},
    "medium": {"title": "\u4e2d\u7bc7", "target_total_chars": 80000, "target_chapters": 6, "target_nodes": 24},
    "long": {"title": "\u957f\u7bc7", "target_total_chars": 160000, "target_chapters": 10, "target_nodes": 50},
}


def resolve_story_config(story_length: Any) -> dict[str, Any]:
    key = str(story_length or "medium").strip().lower()
    if key not in STORY_LENGTH_CONFIGS:
        raise RuntimeError("invalid story_length")
    row = STORY_LENGTH_CONFIGS[key]
    return {
        "story_length": key,
        "target_total_chars": row["target_total_chars"],
        "target_chapters": row["target_chapters"],
        "target_nodes": row["target_nodes"],
    }


def split_chapter_seed(seed: Any, index: int) -> tuple[str, str]:
    text = stringify_brief(seed, 180).strip()
    if not text:
        return f"第{index}章", "推进本章主要矛盾，并留下可追踪的下一步目标。"
    parts = re.split(r"\s*[-—–：:]\s*", text, maxsplit=1)
    title = parts[0].strip() or f"第{index}章"
    goal = parts[1].strip() if len(parts) > 1 else text
    return title, goal


def distribute_node_counts(target_nodes: int, chapter_count: int) -> list[int]:
    chapter_count = max(1, int(chapter_count or 1))
    target_nodes = max(chapter_count, int(target_nodes or chapter_count))
    base = target_nodes // chapter_count
    extra = target_nodes % chapter_count
    return [base + (1 if idx < extra else 0) for idx in range(chapter_count)]


def slugify_ascii(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "node"


def build_node_seed(chapter_title: str, chapter_goal: str, chapter_index: int, node_index: int, node_count: int) -> dict[str, Any]:
    labels = ["opening", "clue", "pressure", "choice", "consequence", "transition"]
    public_labels = ["开场锚点", "线索推进", "冲突升级", "选择分歧", "后果整理", "过渡钩子"]
    label = labels[min(node_index - 1, len(labels) - 1)]
    public_label = public_labels[min(node_index - 1, len(public_labels) - 1)]
    if node_index == 1:
        goal = f"建立「{chapter_title}」的场景、压力和玩家可行动目标。"
    elif node_index == node_count:
        goal = "结算本章关键选择，并把故事引向下一章或下一节点。"
    elif node_index == 2:
        goal = f"围绕本章目标推进核心线索：{chapter_goal}"
    elif node_index == 3:
        goal = "制造明确阻力、代价或新信息，让玩家需要做出判断。"
    else:
        goal = "整理已确认事实、资源变化和下一步路线。"
    node_id = f"c{chapter_index}_n{node_index}_{label}"
    return {
        "node_id": node_id,
        "title": public_label,
        "goal": goal,
        "target_chars": 2800 if node_index in {1, node_count} else 3400,
        "max_turns": 3 if node_index in {1, node_count} else 4,
        "next_nodes": [],
        "beat_checklist": [
            {"beat_id": f"{node_id}_b1", "title": "确认当前场景与玩家处境", "weight": 1},
            {"beat_id": f"{node_id}_b2", "title": "推进一个可见线索或压力", "weight": 1},
            {"beat_id": f"{node_id}_b3", "title": "给出清晰的下一步行动入口", "weight": 1},
        ],
    }


def synthesize_story_chapters(blueprint: dict[str, Any], story_config: dict[str, Any]) -> list[dict[str, Any]]:
    existing = blueprint.get("chapters") if isinstance(blueprint.get("chapters"), list) else []
    if any(isinstance(chapter, dict) and isinstance(chapter.get("nodes"), list) and chapter.get("nodes") for chapter in existing):
        return existing
    seeds = blueprint.get("chapter_seeds") if isinstance(blueprint.get("chapter_seeds"), list) else []
    clean_seeds = [seed for seed in seeds if str(seed or "").strip()]
    target_chapters = max(1, int(story_config.get("target_chapters") or len(clean_seeds) or 6))
    chapter_count = min(max(len(clean_seeds), 1), target_chapters) if clean_seeds else target_chapters
    while len(clean_seeds) < chapter_count:
        idx = len(clean_seeds) + 1
        if idx == 1:
            clean_seeds.append(f"第{idx}章：开场与异常 - 建立主角处境、开场压力和第一条调查线。")
        elif idx == chapter_count:
            clean_seeds.append(f"第{idx}章：收束与选择 - 回收核心矛盾并让玩家做出关键决定。")
        else:
            clean_seeds.append(f"第{idx}章：线索推进 - 推进主线、引入阻力并保留下一章钩子。")
    counts = distribute_node_counts(int(story_config.get("target_nodes") or chapter_count * 4), chapter_count)
    chapters: list[dict[str, Any]] = []
    for cidx, seed in enumerate(clean_seeds[:chapter_count], start=1):
        title, goal = split_chapter_seed(seed, cidx)
        nodes = [build_node_seed(title, goal, cidx, nidx, counts[cidx - 1]) for nidx in range(1, counts[cidx - 1] + 1)]
        for nidx, node in enumerate(nodes):
            if nidx + 1 < len(nodes):
                node["next_nodes"] = [nodes[nidx + 1]["node_id"]]
            elif cidx < chapter_count:
                node["next_nodes"] = [f"c{cidx + 1}_n1_opening"]
        chapters.append({
            "chapter_id": f"chapter_{cidx}",
            "title": title,
            "goal": goal,
            "summary": goal,
            "weight": 1,
            "nodes": nodes,
        })
    return chapters


def ensure_story_progress_current(progress: dict[str, Any], blueprint: dict[str, Any]) -> dict[str, Any]:
    chapters = blueprint.get("chapters") if isinstance(blueprint.get("chapters"), list) else []
    first_chapter = next((chapter for chapter in chapters if isinstance(chapter, dict) and chapter.get("nodes")), {})
    first_node = first_chapter.get("nodes", [{}])[0] if isinstance(first_chapter, dict) and first_chapter.get("nodes") else {}
    progress = progress if isinstance(progress, dict) else {}
    progress.setdefault("campaign_id", blueprint.get("campaign_id", ""))
    progress.setdefault("schema", "trpg_orchestrator.story_progress.v1")
    if first_chapter and not progress.get("current_chapter_id"):
        progress["current_chapter_id"] = first_chapter.get("chapter_id", "")
    if first_node and not progress.get("current_node_id"):
        progress["current_node_id"] = first_node.get("node_id", "")
    if not progress.get("current_phase_id"):
        progress["current_phase_id"] = "opening"
    progress.setdefault("turns_in_node", 0)
    progress.setdefault("chars_in_node", 0)
    progress.setdefault("total_chars", 0)
    progress.setdefault("completed_node_ids", [])
    progress.setdefault("beat_status", {})
    progress.setdefault("pace_command", "normal")
    progress.setdefault("last_transition", {})
    warnings = progress.get("protocol_warnings") if isinstance(progress.get("protocol_warnings"), list) else []
    progress["protocol_warnings"] = [warning for warning in warnings if "story_blueprint empty" not in str(warning)]
    progress.setdefault("last_updated_turn", 0)
    progress["calculated_progress"] = {"overall": 0, "chapter": 0, "node": 0, "updated_by": "backend"}
    return progress


def empty_model_slot() -> dict[str, Any]:
    return {"enabled": False, "provider_type": "", "base_url": "", "model_name": "", "api_key_ref": ""}


def normalize_model_slot(raw: Any, enabled: bool, fallback_key_ref: str = "") -> dict[str, Any]:
    source = raw if isinstance(raw, dict) else {}
    provider = str(source.get("provider_type") or "").strip()
    if enabled and provider not in {"openai_compatible", "deepseek_compatible", "custom_http"}:
        provider = "openai_compatible"
    base_url = str(source.get("base_url") or "").strip()
    model_name = str(source.get("model_name") or "").strip()
    api_key_received = bool(str(source.get("api_key") or "").strip())
    if enabled:
        if not base_url:
            raise RuntimeError("model slot base_url is required")
        if not model_name:
            raise RuntimeError("model slot model_name is required")
    return {
        "enabled": bool(enabled),
        "provider_type": provider if enabled else "",
        "base_url": base_url if enabled else "",
        "model_name": model_name if enabled else "",
        "api_key_ref": fallback_key_ref if api_key_received else "",
    }


def normalize_model_config(payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    mode = normalize_model_mode(payload.get("model_mode") or payload.get("ai_mode"))
    raw_slots = payload.get("model_slots") if isinstance(payload.get("model_slots"), dict) else {}
    legacy_slot = {
        "provider_type": payload.get("provider_type") or "openai_compatible",
        "base_url": payload.get("custom_base_url") or "",
        "model_name": payload.get("custom_model_name") or "",
        "api_key": payload.get("custom_api_key") or "",
    }
    slots = {"director": empty_model_slot(), "actor": empty_model_slot(), "single": empty_model_slot()}
    if mode == "single_model":
        slots["single"] = normalize_model_slot(raw_slots.get("single") or legacy_slot, True, "local_single_api_key")
    elif mode == "custom_dual":
        slots["director"] = normalize_model_slot(raw_slots.get("director") or legacy_slot, True, "local_director_api_key")
        slots["actor"] = normalize_model_slot(raw_slots.get("actor") or {}, True, "local_actor_api_key")
    config = {
        "model_mode": mode,
        "director_model": "deepseek_v4" if mode == "dual_director_actor" else (slots["director"]["model_name"] if mode == "custom_dual" else ""),
        "actor_model": "chatgpt" if mode == "dual_director_actor" else (slots["actor"]["model_name"] if mode == "custom_dual" else ""),
        "single_model": slots["single"]["model_name"] if mode == "single_model" else "",
        "model_slots": slots,
    }
    received_key = any(slot.get("api_key_ref") for slot in slots.values())
    return config, received_key


AUTO_TEXT_SENTINELS = {"默认", "ai定", "ai 定", "AI定", "AI 定", "自动", "自动生成", "auto", "default"}


def is_auto_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    compact = re.sub(r"\s+", "", text).lower()
    sentinels = {re.sub(r"\s+", "", item).lower() for item in AUTO_TEXT_SENTINELS}
    return compact in sentinels


def confirmed_text(value: Any) -> str:
    return "" if is_auto_text(value) else str(value or "").strip()


def is_unresolved_text(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return True
    return is_auto_text(text) or any(token in text for token in ("\u5f85\u786e\u8ba4", "\u672a\u6307\u5b9a", "unknown", "tbd"))


def ai_generation_label(value: Any) -> str:
    text = str(value or "").strip()
    return "请 AI 生成" if is_auto_text(text) else text


def build_protagonist_identity(payload: dict[str, Any], user_prompt: str) -> dict[str, str]:
    name = confirmed_text(payload.get("protagonist_name"))
    role = confirmed_text(payload.get("protagonist_role"))
    summary = role or first_prompt_sentence(user_prompt, 80)
    return {"name": name, "role": role, "title": "", "summary": summary}


def extract_background_from_prompt(user_prompt: str) -> str:
    text = " ".join(str(user_prompt or "").split())
    if not text:
        return ""
    markers = ["主角", "玩家", "调查员", "冒险者", "角色"]
    sentences = re.split(r"[。！？!?；;]\s*", text)
    for sentence in sentences:
        if any(marker in sentence for marker in markers):
            return stringify_brief(sentence, 180)
    return stringify_brief(sentences[0], 180) if sentences else ""


def build_protagonist_profile(payload: dict[str, Any], user_prompt: str) -> dict[str, Any]:
    background_auto = is_auto_text(payload.get("protagonist_background"))
    background = confirmed_text(payload.get("protagonist_background"))
    if not background and not background_auto:
        background = extract_background_from_prompt(user_prompt)
    if not background and not background_auto:
        background = "主角背景待正文确认，当前仅记录为本团开局角色。"
    return {
        "background": background,
        "motivation": confirmed_text(payload.get("protagonist_motivation")),
        "personality": confirmed_text(payload.get("protagonist_personality")),
        "notes": [],
    }


def first_prompt_sentence(text: str, limit: int = 80) -> str:
    rows = re.split(r"[。！？!?；;\n]\s*", str(text or "").strip())
    return stringify_brief(next((row for row in rows if row.strip()), ""), limit)


ATTRIBUTE_CAP = 20
ATTRIBUTE_FLOAT_RATIO = 1.2
ATTRIBUTE_FLOAT_CAP = math.ceil(ATTRIBUTE_CAP * ATTRIBUTE_FLOAT_RATIO)
ATTRIBUTE_ROLL_MIN = 6
ATTRIBUTE_ROLL_MAX = 18


ATTRIBUTE_THEME_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "coc": {
        "title": "COC 属性主题",
        "summary": "适用于调查、克苏鲁、恐怖、悬疑、旧案、失踪、精神压力、理智消耗类故事。",
        "short_hint": "COC 团使用调查与理智压力取向的三维与六维属性。",
    },
    "dnd": {
        "title": "DND 属性主题",
        "summary": "适用于奇幻、冒险、地城、职业、法术、等级、队伍探索、战斗成长类故事。",
        "short_hint": "DND 团使用职业冒险与战斗探索取向的三维与六维属性。",
    },
    "generic": {
        "title": "通用团属性主题",
        "summary": "适用于自定义世界观、FATE、怪猎、现代都市、校园、轻小说、原创奇幻、原创悬疑等不想绑定固定规则体系的跑团。",
        "short_hint": "自定义团不建议过早写死专属属性名。默认使用通用三维与六维，让 AI 在后续剧情中根据角色定位和玩法重心判断属性用途。",
    },
}


THREE_ATTRIBUTE_THEMES: dict[str, list[dict[str, str]]] = {
    "coc": [
        {"key": "BODY", "label": "体能", "description": "代表身体承受、逃跑、攀爬、负伤后的行动能力。"},
        {"key": "OBSERVE", "label": "观察", "description": "代表寻找线索、注意异常、发现痕迹、判断现场细节的能力。"},
        {"key": "SANITY", "label": "心智", "description": "代表精神稳定、恐惧承受、异常事件下保持判断的能力。"},
    ],
    "dnd": [
        {"key": "BODY", "label": "体魄", "description": "代表力量、体质、负重、近身冲突和身体承受能力。"},
        {"key": "SKILL", "label": "技艺", "description": "代表敏捷、技巧、武器操作、潜行、开锁、闪避等行动能力。"},
        {"key": "MIND", "label": "心智", "description": "代表知识、感知、判断、意志、魅力和施法相关倾向。"},
    ],
    "generic": [
        {"key": "BODY", "label": "体能", "description": "代表身体基础、负重、抗伤、长时间行动和直接身体压力。"},
        {"key": "ACTION", "label": "行动", "description": "代表反应、执行、移动、战斗动作、操作工具和临场应变。"},
        {"key": "MIND", "label": "心智", "description": "代表判断、理解、意志、记忆、抗压和复杂局面下的选择能力。"},
    ],
}


SIX_ATTRIBUTE_THEMES: dict[str, list[dict[str, str]]] = {
    "coc": [
        {"key": "BODY", "label": "体能", "description": "身体力量、耐力、基础行动能力。"},
        {"key": "DEX", "label": "敏捷", "description": "反应速度、闪避、潜行、手部动作和快速行动。"},
        {"key": "MIND", "label": "心智", "description": "理解力、知识调用、推理、记忆和判断。"},
        {"key": "POW", "label": "意志", "description": "精神抵抗、执念、抗压、面对未知时维持自我的能力。"},
        {"key": "LUCK", "label": "幸运", "description": "偶然性、危险边缘的转机、关键时刻的运气。"},
        {"key": "SAN", "label": "理智", "description": "面对恐惧、怪异、禁忌知识时的精神稳定程度。"},
    ],
    "dnd": [
        {"key": "STR", "label": "力量", "description": "近战力量、负重、破坏、推拉、攀爬和身体压制。"},
        {"key": "DEX", "label": "敏捷", "description": "闪避、先手、潜行、远程攻击、精细动作。"},
        {"key": "CON", "label": "体质", "description": "生命力、耐力、抗毒、抗病、受伤后的承受能力。"},
        {"key": "INT", "label": "智力", "description": "知识、调查、奥术理解、逻辑推理和记忆。"},
        {"key": "WIS", "label": "感知", "description": "直觉、观察、洞察、野外生存和精神警觉。"},
        {"key": "CHA", "label": "魅力", "description": "说服、威慑、表演、领导力和人格影响力。"},
    ],
    "generic": [
        {"key": "BODY", "label": "体能", "description": "基础身体素质、耐力、力量、伤势承受。"},
        {"key": "REFLEX", "label": "反应", "description": "速度、闪避、先手、快速判断和危险来临时的身体反射。"},
        {"key": "ENDURE", "label": "耐受", "description": "长时间压力、伤痛、疲劳、恐惧、环境恶劣时的承受力。"},
        {"key": "MIND", "label": "心智", "description": "理解、推理、学习、计划、精神稳定和意志判断。"},
        {"key": "SENSE", "label": "感知", "description": "观察、直觉、危险预感、线索捕捉和环境阅读。"},
        {"key": "SOCIAL", "label": "社交", "description": "交涉、说服、伪装、共情、威慑、组织关系和人际影响力。"},
    ],
}


def resolve_attribute_theme(template: Any) -> str:
    value = str(template or "custom").strip().lower()
    if value == "coc":
        return "coc"
    if value == "dnd":
        return "dnd"
    return "generic"


def build_three_attribute_definitions(theme: str) -> list[dict[str, str]]:
    return [dict(item) for item in THREE_ATTRIBUTE_THEMES.get(theme, THREE_ATTRIBUTE_THEMES["generic"])]


def build_six_attribute_definitions(theme: str) -> list[dict[str, str]]:
    return [dict(item) for item in SIX_ATTRIBUTE_THEMES.get(theme, SIX_ATTRIBUTE_THEMES["generic"])]


def int_payload(payload: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(payload.get(key, default))
    except (TypeError, ValueError):
        raise RuntimeError(f"{key} must be an integer")


def float_payload(payload: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(payload.get(key, default))
    except (TypeError, ValueError):
        raise RuntimeError(f"{key} must be a number")


def validate_attribute_roll_result(values: Any, cap: int, dimension: int, float_ratio: float) -> list[int]:
    raw = values if isinstance(values, list) else []
    if len(raw) != dimension:
        raise RuntimeError(f"attribute roll result requires {dimension} values")
    float_cap = math.ceil(cap * float_ratio)
    total_budget = cap * dimension
    rows: list[int] = []
    total = 0
    for index in range(dimension):
        value = raw[index]
        if isinstance(value, bool):
            raise RuntimeError("attribute roll value must be a non-negative integer")
        try:
            number = int(value)
        except (TypeError, ValueError):
            raise RuntimeError("attribute roll value must be a non-negative integer")
        if str(value).strip() not in {str(number), f"{number}.0"} and not isinstance(value, int):
            raise RuntimeError("attribute roll value must be a non-negative integer")
        if number < 0:
            raise RuntimeError("attribute roll value must be non-negative")
        if number > float_cap:
            raise RuntimeError(f"attribute roll value exceeds float_cap {float_cap}")
        rows.append(number)
        total += number
    if total > total_budget:
        raise RuntimeError(f"attribute roll total exceeds budget {total_budget}")
    return rows


def distribute_balanced_values(count: int, cap: int, low: int = ATTRIBUTE_ROLL_MIN, high: int = ATTRIBUTE_ROLL_MAX, float_ratio: float = ATTRIBUTE_FLOAT_RATIO) -> list[int]:
    import random
    float_cap = math.ceil(cap * float_ratio)
    high = min(high, float_cap)
    low = min(low, high)
    budget = cap * count
    base = max(low, min(high, min(18, cap)))
    values = [base for _ in range(count)]
    remaining = min(budget - sum(values), max(0, float_cap - base) * count)
    while remaining > 0 and values:
        candidates = [index for index, value in enumerate(values) if value < float_cap]
        if not candidates:
            break
        index = random.choice(candidates)
        values[index] += 1
        remaining -= 1
    return values


def build_attribute_items(defs: list[dict[str, str]], values: list[int]) -> list[dict[str, Any]]:
    return [
        {"key": item.get("key", ""), "label": item.get("label", ""), "value": values[index] if index < len(values) else 0}
        for index, item in enumerate(defs)
    ]


def build_character_vitals_from_three(attributes: Any) -> list[dict[str, Any]]:
    source = attributes if isinstance(attributes, dict) else {}
    three = source.get("three") if isinstance(source.get("three"), dict) else {}
    items = three.get("items") if isinstance(three.get("items"), list) else []
    if not items:
        return []
    float_cap = number_or_none(source.get("float_cap")) or ATTRIBUTE_FLOAT_CAP

    def pick(keys: set[str], fallback_index: int) -> dict[str, Any]:
        for item in items:
            if isinstance(item, dict) and str(item.get("key") or "").upper() in keys:
                return item
        return items[fallback_index] if fallback_index < len(items) and isinstance(items[fallback_index], dict) else {}

    picked = [
        ("status", "状态", pick({"BODY"}, 0), "green"),
        ("focus", "专注", pick({"ACTION", "REFLEX", "SKILL", "OBSERVE"}, 1), "blue"),
        ("resource", "资源", pick({"MIND", "SANITY"}, 2), "amber"),
    ]
    rows = []
    for key, label, item, tone in picked:
        value = number_or_none(item.get("value")) or 0
        item_label = str(item.get("label") or item.get("key") or label)
        percent = round(max(0, min(100, value / float_cap * 100))) if float_cap else 0
        rows.append({
            "key": key,
            "label": label,
            "current": value,
            "max": float_cap,
            "percent": percent,
            "text": f"{item_label} {int(value) if float(value).is_integer() else value}/{int(float_cap) if float(float_cap).is_integer() else float_cap}",
            "tone": tone,
            "source_attribute": str(item.get("key") or ""),
        })
    return rows


def roll_parallel_attributes(
    three_defs: list[dict[str, str]],
    six_defs: list[dict[str, str]],
    cap: int = ATTRIBUTE_CAP,
    float_ratio: float = ATTRIBUTE_FLOAT_RATIO,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    three_values = distribute_balanced_values(len(three_defs), cap, ATTRIBUTE_ROLL_MIN, ATTRIBUTE_ROLL_MAX, float_ratio)
    six_values = distribute_balanced_values(len(six_defs), cap, ATTRIBUTE_ROLL_MIN, ATTRIBUTE_ROLL_MAX, float_ratio)
    return build_attribute_items(three_defs, three_values), build_attribute_items(six_defs, six_values)


def normalize_attribute_roll_result(raw: Any, theme: str, three_defs: list[dict[str, str]], six_defs: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source = raw if isinstance(raw, dict) else {}
    raw_three = source.get("three", {}).get("items") if isinstance(source.get("three"), dict) else []
    raw_six = source.get("six", {}).get("items") if isinstance(source.get("six"), dict) else []

    def values_for(defs: list[dict[str, str]], rows: Any) -> list[int]:
        items = rows if isinstance(rows, list) else []
        by_key = {str(item.get("key") or ""): item for item in items if isinstance(item, dict)}
        ordered = []
        for definition in defs:
            item = by_key.get(definition["key"])
            ordered.append(item.get("value") if item else None)
        return ordered

    three_values = validate_attribute_roll_result(values_for(three_defs, raw_three), ATTRIBUTE_CAP, 3, ATTRIBUTE_FLOAT_RATIO)
    six_values = validate_attribute_roll_result(values_for(six_defs, raw_six), ATTRIBUTE_CAP, 6, ATTRIBUTE_FLOAT_RATIO)
    return build_attribute_items(three_defs, three_values), build_attribute_items(six_defs, six_values)


def current_host_id() -> str:
    raw = os.getenv("TRPG_HOST_ID") or socket.gethostname() or "local_host"
    return safe_segment(str(raw).strip().lower()) or "local_host"


def normalize_custom_rules(value: Any) -> list[dict[str, Any]]:
    rows = value if isinstance(value, list) else []
    output: list[dict[str, Any]] = []
    for index, row in enumerate(rows[:3], start=1):
        if not isinstance(row, dict):
            continue
        target_layer = str(row.get("target_layer") or "director").strip()
        if target_layer not in {"director", "actor", "both"}:
            target_layer = "director"
        output.append({
            "id": f"custom_rule_{index}",
            "enabled": bool_payload(row, "enabled", True),
            "title": stringify_brief(row.get("title") or f"临时客制规则 {index}", 80),
            "target_layer": target_layer,
            "content": str(row.get("content") or "").strip(),
        })
    return [row for row in output if row["title"] or row["content"]]


def write_custom_rules(campaign_id: str, owner_host_id: str, rules: list[dict[str, Any]]) -> None:
    root = CAMPAIGNS_DIR / safe_segment(campaign_id)
    write_json(root / "custom_rules.json", {
        "campaign_id": campaign_id,
        "owner_host_id": owner_host_id,
        "rules": rules[:3],
    })


def normalize_new_campaign_payload(payload: dict[str, Any]) -> dict[str, Any]:
    template = str(payload.get("template") or "custom").strip().lower()
    if template not in CAMPAIGN_TEMPLATE_DEFAULTS:
        template = "custom"
    defaults = CAMPAIGN_TEMPLATE_DEFAULTS[template]
    name = str(payload.get("name") or defaults.get("name") or "").strip()
    raw_user_prompt = payload.get("user_prompt")
    user_prompt_auto = is_auto_text(raw_user_prompt)
    user_prompt = "" if user_prompt_auto else str(raw_user_prompt or defaults.get("user_prompt") or "").strip()
    if not name:
        raise RuntimeError("name is required")
    if not user_prompt and not user_prompt_auto:
        raise RuntimeError("user_prompt is required")

    model_config, custom_api_key_received = normalize_model_config(payload)
    story_config = resolve_story_config(payload.get("story_length") or "medium")

    character_card_enabled = bool_payload(payload, "character_card_enabled", bool(defaults.get("character_card_enabled", True)))
    attribute_enabled = bool_payload(payload, "attribute_enabled", True)
    attribute_theme = resolve_attribute_theme(template)
    three_defs = build_three_attribute_definitions(attribute_theme)
    six_defs = build_six_attribute_definitions(attribute_theme)
    roll_result = payload.get("attribute_roll_result") if isinstance(payload.get("attribute_roll_result"), dict) else None
    if roll_result:
        three_items, six_items = normalize_attribute_roll_result(roll_result, attribute_theme, three_defs, six_defs)
    else:
        three_items, six_items = roll_parallel_attributes(three_defs, six_defs, ATTRIBUTE_CAP, ATTRIBUTE_FLOAT_RATIO)
    character_card = {
        "enabled": character_card_enabled,
        "mode": "strict_stats" if character_card_enabled and attribute_enabled else "narrative",
        "identity": build_protagonist_identity(payload, user_prompt),
        "profile": build_protagonist_profile(payload, user_prompt),
        "vitals": [],
        "attributes": {
            "enabled": attribute_enabled,
            "visible": attribute_enabled,
            "theme": attribute_theme,
            "cap": ATTRIBUTE_CAP,
            "float_ratio": ATTRIBUTE_FLOAT_RATIO,
            "float_cap": ATTRIBUTE_FLOAT_CAP,
            "three": {"template": "three", "source": attribute_theme, "items": three_items},
            "six": {"template": "six", "source": attribute_theme, "items": six_items},
        },
        "badges": [],
    }
    character_card["vitals"] = build_character_vitals_from_three(character_card["attributes"])

    rules_strictness = str(payload.get("rules_strictness") or defaults.get("rules_strictness") or "light").strip()
    if rules_strictness not in {"light", "standard", "strict"}:
        raise RuntimeError("invalid rules_strictness")

    companion_enabled = bool_payload(payload, "companion_enabled", False)
    companion_mode = str(payload.get("companion_mode") or "auto").strip()
    if companion_mode not in {"auto", "manual"}:
        raise RuntimeError("invalid companion_mode")
    companion_name = str(payload.get("companion_name") or "").strip()
    if companion_enabled and companion_mode == "manual" and not companion_name:
        raise RuntimeError("companion_name is required when companion_mode is manual")
    companion_config = {
        "companion_enabled": companion_enabled,
        "companion_mode": companion_mode if companion_enabled else "auto",
        "companion_name": companion_name if companion_enabled else "",
        "companion_role": str(payload.get("companion_role") or "").strip() if companion_enabled else "",
        "companion_personality": str(payload.get("companion_personality") or "").strip() if companion_enabled else "",
        "companion_card_visible": True if companion_enabled else False,
    }
    custom_rules = normalize_custom_rules(payload.get("custom_rules"))
    owner_host_id = current_host_id()

    return {
        "template": template,
        "name": name,
        "user_prompt": user_prompt,
        "auto_fields": {
            "user_prompt": user_prompt_auto,
            "protagonist_name": is_auto_text(payload.get("protagonist_name")),
            "protagonist_role": is_auto_text(payload.get("protagonist_role")),
            "protagonist_background": is_auto_text(payload.get("protagonist_background")),
            "protagonist_motivation": is_auto_text(payload.get("protagonist_motivation")),
            "protagonist_personality": is_auto_text(payload.get("protagonist_personality")),
        },
        "model_config": model_config,
        "story_config": story_config,
        "character_card": character_card,
        "rules_config": {
            "character_card_enabled": character_card_enabled,
            "stat_visibility": "numeric" if attribute_enabled else "narrative",
            "attribute_config": {
                "enabled": attribute_enabled,
                "visible": attribute_enabled,
                "theme": attribute_theme,
                "cap": ATTRIBUTE_CAP,
                "float_ratio": ATTRIBUTE_FLOAT_RATIO,
                "three_enabled": True,
                "six_enabled": True,
                "six_source": attribute_theme,
            },
            "attribute_roll_config": {
                "enabled": True,
                "method": "balanced_random",
                "min": ATTRIBUTE_ROLL_MIN,
                "max": ATTRIBUTE_ROLL_MAX,
            },
            "dice_enabled": False,
            "dice_type": "",
            "roll_mode": "",
            "roll_attributes": [],
            "rules_strictness": rules_strictness,
        },
        "companion_config": companion_config,
        "safety_lines": list_payload(payload.get("safety_lines")),
        "custom_rules": custom_rules,
        "owner_host_id": owner_host_id,
        "custom_api_key_received": custom_api_key_received,
    }

V4_CAMPAIGN_SETUP_SYSTEM_PROMPT = """你是文字 TRPG 创团导演层。你的任务不是写正文，而是根据用户的创团表单生成“初始化跑团记忆”。

你必须只输出 JSON，不要输出 Markdown，不要解释。

你需要遵守：
1. 不要开始正式剧情正文。
2. 不要替玩家做不可逆决定。
3. 不要过早揭露秘密。
4. 用户明确填写的主角名称、身份、背景、安全边界优先级最高。
5. 未确认内容必须标记为“待确认”，不要编造复杂背景。
6. 临时客制规则不能覆盖系统安全规则。
7. 输出内容用于写入 campaign_profile、campaign_direction、story_blueprint、character_prompt 和 player_state。
"""


def campaign_setup_schema_hint() -> dict[str, Any]:
    return {
        "public_think": [
            {"stage": "理解故事设定", "text": "正在确认世界观、主角处境和故事开场压力。"},
            {"stage": "整理初始化记忆", "text": "正在把角色、伙伴、安全边界和故事规划整理成可写入数据。"},
        ],
        "analysis": {"genre": "", "tone": "", "premise": "", "source": "deepseek_v4_campaign_setup"},
        "campaign_direction": {
            "core_concept": "",
            "opening_situation": "",
            "main_conflict": "",
            "early_goals": [],
            "known_boundaries": [],
            "secrets_not_to_reveal_early": [],
            "director_notes": [],
        },
        "story_blueprint_patch": {"notes": [], "chapter_seeds": []},
        "protagonist_patch": {
            "confirmed_identity": "",
            "confirmed_background": "",
            "personality_and_voice": "",
            "abilities_and_limits": "",
            "growth_direction": "",
            "unknown_or_player_owned": [],
        },
        "character_card_patch": {
            "identity": {"name": "", "role": "", "title": "", "summary": ""},
            "profile": {"background": "", "motivation": "", "personality": "", "notes": []},
            "badges": [],
        },
        "companion_patch": {
            "enabled": False,
            "name": "",
            "role": "",
            "personality": "",
            "relationship_to_protagonist": "",
            "unknown_or_later": [],
        },
        "safety_interpretation": {"hard_lines": [], "soft_lines": [], "tone_limits": []},
        "initial_memory_notes": {
            "world_facts": [],
            "npc_seeds": [],
            "location_seeds": [],
            "quest_seeds": [],
            "unresolved_questions": [],
        },
    }


def build_campaign_director_setup_prompt(config: dict[str, Any]) -> str:
    character_card = config.get("character_card", {}) if isinstance(config.get("character_card"), dict) else {}
    identity = character_card.get("identity", {}) if isinstance(character_card.get("identity"), dict) else {}
    profile = character_card.get("profile", {}) if isinstance(character_card.get("profile"), dict) else {}
    auto_fields = config.get("auto_fields", {}) if isinstance(config.get("auto_fields"), dict) else {}
    rules_config = config.get("rules_config", {}) if isinstance(config.get("rules_config"), dict) else {}
    attribute_config = rules_config.get("attribute_config", {}) if isinstance(rules_config.get("attribute_config"), dict) else {}
    prompt_input = {
        "跑团名称": config.get("name", ""),
        "模板": config.get("template", "custom"),
        "故事篇幅": config.get("story_config", {}).get("story_length", "medium") if isinstance(config.get("story_config"), dict) else "medium",
        "用户开场 Prompt": config.get("user_prompt", ""),
        "模型模式": config.get("model_config", {}).get("model_mode", "") if isinstance(config.get("model_config"), dict) else "",
        "主角名称": identity.get("name", ""),
        "主角身份 / 职业": identity.get("role", ""),
        "主角背景": profile.get("background", ""),
        "主角动机": profile.get("motivation", ""),
        "主角性格关键词": profile.get("personality", ""),
        "属性主题": attribute_config.get("theme", ""),
        "伙伴配置": config.get("companion_config", {}),
        "规则强度": rules_config.get("rules_strictness", "light"),
        "安全边界": config.get("safety_lines", []),
        "临时客制规则": config.get("custom_rules", []),
    }
    prompt_input["auto_fields"] = auto_fields
    prompt_input["resolved_form_fields"] = {
        "story_setting_prompt": ai_generation_label(config.get("user_prompt", "")) if auto_fields.get("user_prompt") else config.get("user_prompt", ""),
        "protagonist_name": ai_generation_label(identity.get("name", "")) if auto_fields.get("protagonist_name") else identity.get("name", ""),
        "protagonist_role": ai_generation_label(identity.get("role", "")) if auto_fields.get("protagonist_role") else identity.get("role", ""),
        "protagonist_background": ai_generation_label(profile.get("background", "")) if auto_fields.get("protagonist_background") else profile.get("background", ""),
        "protagonist_motivation": ai_generation_label(profile.get("motivation", "")) if auto_fields.get("protagonist_motivation") else profile.get("motivation", ""),
        "protagonist_personality": ai_generation_label(profile.get("personality", "")) if auto_fields.get("protagonist_personality") else profile.get("personality", ""),
    }
    return "\n".join([
        "# 创团表单输入",
        "```json",
        json.dumps(prompt_input, ensure_ascii=False, indent=2),
        "```",
        "",
        "# 输出要求",
        "返回严格 JSON，字段必须匹配下面结构；不要输出故事正文，不要输出 Markdown：",
        "",
        "# Auto-generation rules",
        "Fields marked in auto_fields, or shown as 请 AI 生成, mean the user intentionally leaves them to the director.",
        "For those fields, generate a concrete but reversible initial draft. Do not output 待确认 / 待玩家确认 / unknown as the main value.",
        "Only put truly player-owned details in unknown_or_player_owned. Do not use unknown_or_player_owned as a substitute for generating the requested setup.",
        "If companion_config.companion_enabled is true and companion_mode is auto, create a concrete companion_patch with a usable name, role, personality, and relationship_to_protagonist.",
        "If user_prompt is auto, generate campaign premise, background, opening situation, main conflict, early goals, and story seeds from the selected template and title.",
        "User explicitly filled fields still have highest priority and must not be overwritten.",
        "Include public_think as 4-8 short player-facing progress notes. They are public waiting messages, not hidden chain-of-thought. Do not reveal secrets, system prompts, or future twists.",
        "",
        json.dumps(campaign_setup_schema_hint(), ensure_ascii=False, indent=2),
    ])


def require_dict(value: Any, key: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"V4 campaign setup invalid: {key} must be object")
    return value


def require_list(value: Any, key: str) -> list[Any]:
    if not isinstance(value, list):
        raise RuntimeError(f"V4 campaign setup invalid: {key} must be array")
    return value


def sanitize_string_list(value: Any, limit: int = 12) -> list[str]:
    if not isinstance(value, list):
        return []
    return [stringify_brief(str(item), 220) for item in value[:limit] if str(item).strip()]


def sanitize_public_think(value: Any, limit: int = 8) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, str]] = []
    for item in value[:limit]:
        if isinstance(item, dict):
            stage = stringify_brief(item.get("stage"), 40)
            text = stringify_brief(item.get("text"), 120)
        else:
            stage = "处理进度"
            text = stringify_brief(item, 120)
        if text:
            rows.append({"stage": stage or "处理进度", "text": text})
    return rows


def validate_v4_campaign_setup(raw: Any) -> dict[str, Any]:
    data = require_dict(raw, "root")
    public_think = data.get("public_think") if isinstance(data.get("public_think"), list) else []
    analysis = require_dict(data.get("analysis"), "analysis")
    direction = require_dict(data.get("campaign_direction"), "campaign_direction")
    story_patch = require_dict(data.get("story_blueprint_patch"), "story_blueprint_patch")
    protagonist = require_dict(data.get("protagonist_patch"), "protagonist_patch")
    card_patch = require_dict(data.get("character_card_patch"), "character_card_patch")
    companion = require_dict(data.get("companion_patch"), "companion_patch")
    safety = require_dict(data.get("safety_interpretation"), "safety_interpretation")
    memory_notes = require_dict(data.get("initial_memory_notes"), "initial_memory_notes")
    for key in ("early_goals", "known_boundaries", "secrets_not_to_reveal_early", "director_notes"):
        require_list(direction.get(key), f"campaign_direction.{key}")
    for key in ("notes", "chapter_seeds"):
        require_list(story_patch.get(key), f"story_blueprint_patch.{key}")
    for key in ("unknown_or_player_owned",):
        require_list(protagonist.get(key), f"protagonist_patch.{key}")
    require_dict(card_patch.get("identity"), "character_card_patch.identity")
    require_dict(card_patch.get("profile"), "character_card_patch.profile")
    require_list(card_patch.get("badges"), "character_card_patch.badges")
    require_list(companion.get("unknown_or_later"), "companion_patch.unknown_or_later")
    for key in ("hard_lines", "soft_lines", "tone_limits"):
        require_list(safety.get(key), f"safety_interpretation.{key}")
    for key in ("world_facts", "npc_seeds", "location_seeds", "quest_seeds", "unresolved_questions"):
        require_list(memory_notes.get(key), f"initial_memory_notes.{key}")
    return {
        "public_think": sanitize_public_think(public_think),
        "analysis": {
            "genre": stringify_brief(analysis.get("genre"), 80),
            "tone": stringify_brief(analysis.get("tone"), 100),
            "premise": stringify_brief(analysis.get("premise"), 240),
            "source": "deepseek_v4_campaign_setup",
        },
        "campaign_direction": {
            "core_concept": stringify_brief(direction.get("core_concept"), 240),
            "opening_situation": stringify_brief(direction.get("opening_situation"), 260),
            "main_conflict": stringify_brief(direction.get("main_conflict"), 240),
            "early_goals": sanitize_string_list(direction.get("early_goals")),
            "known_boundaries": sanitize_string_list(direction.get("known_boundaries")),
            "secrets_not_to_reveal_early": sanitize_string_list(direction.get("secrets_not_to_reveal_early")),
            "director_notes": sanitize_string_list(direction.get("director_notes")),
        },
        "story_blueprint_patch": {
            "notes": sanitize_string_list(story_patch.get("notes")),
            "chapter_seeds": sanitize_string_list(story_patch.get("chapter_seeds")),
        },
        "protagonist_patch": {
            "confirmed_identity": stringify_brief(protagonist.get("confirmed_identity"), 180),
            "confirmed_background": stringify_brief(protagonist.get("confirmed_background"), 260),
            "personality_and_voice": stringify_brief(protagonist.get("personality_and_voice"), 180),
            "abilities_and_limits": stringify_brief(protagonist.get("abilities_and_limits"), 220),
            "growth_direction": stringify_brief(protagonist.get("growth_direction"), 200),
            "unknown_or_player_owned": sanitize_string_list(protagonist.get("unknown_or_player_owned")),
        },
        "character_card_patch": {
            "identity": {
                "name": stringify_brief(card_patch.get("identity", {}).get("name"), 80),
                "role": stringify_brief(card_patch.get("identity", {}).get("role"), 80),
                "title": stringify_brief(card_patch.get("identity", {}).get("title"), 80),
                "summary": stringify_brief(card_patch.get("identity", {}).get("summary"), 180),
            },
            "profile": {
                "background": stringify_brief(card_patch.get("profile", {}).get("background"), 260),
                "motivation": stringify_brief(card_patch.get("profile", {}).get("motivation"), 180),
                "personality": stringify_brief(card_patch.get("profile", {}).get("personality"), 140),
                "notes": sanitize_string_list(card_patch.get("profile", {}).get("notes")),
            },
            "badges": sanitize_string_list(card_patch.get("badges"), 8),
        },
        "companion_patch": {
            "enabled": bool(companion.get("enabled")),
            "name": stringify_brief(companion.get("name"), 80),
            "role": stringify_brief(companion.get("role"), 100),
            "personality": stringify_brief(companion.get("personality"), 160),
            "relationship_to_protagonist": stringify_brief(companion.get("relationship_to_protagonist"), 180),
            "unknown_or_later": sanitize_string_list(companion.get("unknown_or_later")),
        },
        "safety_interpretation": {
            "hard_lines": sanitize_string_list(safety.get("hard_lines")),
            "soft_lines": sanitize_string_list(safety.get("soft_lines")),
            "tone_limits": sanitize_string_list(safety.get("tone_limits")),
        },
        "initial_memory_notes": {
            "world_facts": sanitize_string_list(memory_notes.get("world_facts")),
            "npc_seeds": sanitize_string_list(memory_notes.get("npc_seeds")),
            "location_seeds": sanitize_string_list(memory_notes.get("location_seeds")),
            "quest_seeds": sanitize_string_list(memory_notes.get("quest_seeds")),
            "unresolved_questions": sanitize_string_list(memory_notes.get("unresolved_questions")),
        },
    }


def call_v4_campaign_setup(config: dict[str, Any]) -> dict[str, Any]:
    client = DeepSeekClient()
    if not client.is_configured():
        raise RuntimeError("缺少 DEEPSEEK_API_KEY，无法调用 V4 导演初始化创团。")
    system_prompt = V4_CAMPAIGN_SETUP_SYSTEM_PROMPT + "\n\n" + (
        "Important auto-generation override: when the user leaves a field blank, enters 默认, AI定, 自动生成, "
        "or the payload marks it in auto_fields, that field is delegated to you. "
        "Generate a concrete initial setup draft for it. Do not answer 待确认 for delegated story background, "
        "protagonist background, motivation, personality, or auto companion. "
        "Keep the draft reversible and player-editable, but make it usable for campaign initialization."
    )
    raw = client.complete_json(system_prompt, build_campaign_director_setup_prompt(config))
    return validate_v4_campaign_setup(extract_json_object(raw))


def merge_v4_setup_into_config(config: dict[str, Any], setup: dict[str, Any]) -> None:
    config["v4_setup"] = setup
    analysis = dict(setup.get("analysis") or {})
    analysis["source"] = "deepseek_v4_campaign_setup"
    config["analysis"] = analysis
    character_card = config.get("character_card", {}) if isinstance(config.get("character_card"), dict) else {}
    auto_fields = config.get("auto_fields", {}) if isinstance(config.get("auto_fields"), dict) else {}
    card_patch = setup.get("character_card_patch", {}) if isinstance(setup.get("character_card_patch"), dict) else {}
    identity = character_card.setdefault("identity", {})
    profile_data = character_card.setdefault("profile", {})
    patch_identity = card_patch.get("identity", {}) if isinstance(card_patch.get("identity"), dict) else {}
    patch_profile = card_patch.get("profile", {}) if isinstance(card_patch.get("profile"), dict) else {}
    for key in ("name", "role", "title", "summary"):
        auto_key = {"name": "protagonist_name", "role": "protagonist_role"}.get(key, "")
        if (not str(identity.get(key) or "").strip() or (auto_key and auto_fields.get(auto_key)) or is_auto_text(identity.get(key))) and patch_identity.get(key):
            identity[key] = patch_identity.get(key)
    for key in ("background", "motivation", "personality"):
        auto_key = {
            "background": "protagonist_background",
            "motivation": "protagonist_motivation",
            "personality": "protagonist_personality",
        }.get(key, "")
        if (not str(profile_data.get(key) or "").strip() or (auto_key and auto_fields.get(auto_key)) or is_auto_text(profile_data.get(key))) and patch_profile.get(key):
            profile_data[key] = patch_profile.get(key)
    notes = profile_data.setdefault("notes", [])
    if isinstance(notes, list):
        notes.extend(sanitize_string_list(patch_profile.get("notes"), 8))
    badges = character_card.setdefault("badges", [])
    if isinstance(badges, list):
        badges.extend(sanitize_string_list(card_patch.get("badges"), 8))


def enforce_v4_auto_generation(config: dict[str, Any], setup: dict[str, Any]) -> None:
    auto_fields = config.get("auto_fields", {}) if isinstance(config.get("auto_fields"), dict) else {}
    analysis = setup.get("analysis", {}) if isinstance(setup.get("analysis"), dict) else {}
    direction = setup.get("campaign_direction", {}) if isinstance(setup.get("campaign_direction"), dict) else {}
    card_patch = setup.get("character_card_patch", {}) if isinstance(setup.get("character_card_patch"), dict) else {}
    identity = card_patch.get("identity", {}) if isinstance(card_patch.get("identity"), dict) else {}
    profile = card_patch.get("profile", {}) if isinstance(card_patch.get("profile"), dict) else {}
    companion = setup.get("companion_patch", {}) if isinstance(setup.get("companion_patch"), dict) else {}
    missing: list[str] = []
    if auto_fields.get("user_prompt"):
        if is_unresolved_text(analysis.get("premise")):
            missing.append("story premise")
        if is_unresolved_text(direction.get("core_concept")) or is_unresolved_text(direction.get("opening_situation")):
            missing.append("story direction")
    for field, source, label in (
        ("protagonist_name", identity.get("name"), "protagonist name"),
        ("protagonist_role", identity.get("role"), "protagonist role"),
        ("protagonist_background", profile.get("background"), "protagonist background"),
        ("protagonist_motivation", profile.get("motivation"), "protagonist motivation"),
        ("protagonist_personality", profile.get("personality"), "protagonist personality"),
    ):
        if auto_fields.get(field) and is_unresolved_text(source):
            missing.append(label)
    companion_config = config.get("companion_config", {}) if isinstance(config.get("companion_config"), dict) else {}
    if companion_config.get("companion_enabled") and companion_config.get("companion_mode") == "auto":
        if not companion.get("enabled") or is_unresolved_text(companion.get("name")) or is_unresolved_text(companion.get("role")):
            missing.append("auto companion")
    if missing:
        raise RuntimeError("V4 did not generate required auto setup fields: " + ", ".join(dict.fromkeys(missing)))


def create_campaign_smart_payload(payload: dict[str, Any], progress: Any | None = None) -> dict[str, Any]:
    if progress:
        progress(5, "校验创团表单")
    config = normalize_new_campaign_payload(payload)
    name = config["name"]
    template = config["template"]
    user_prompt = config["user_prompt"]
    custom_rules = config.get("custom_rules", [])
    if progress:
        progress(15, "正在请求 V4 导演生成初始设定")
    setup = call_v4_campaign_setup(config)
    if progress:
        progress(50, "V4 导演设定已返回", setup.get("public_think", []))
    enforce_v4_auto_generation(config, setup)
    merge_v4_setup_into_config(config, setup)
    if progress:
        progress(75, "正在本地分析角色、规则与记忆")

    campaign_id = unique_campaign_id(name)
    store = MemoryStore()
    previous_registry = store.load_registry()
    previous_active = previous_registry.get("active_campaign") or ""
    paths = store.init_campaign(campaign_id, name)
    try:
        registry = store.load_registry()
        registry.setdefault("campaigns", {}).setdefault(campaign_id, {})
        registry["campaigns"][campaign_id]["initialization_status"] = "creating"
        registry["campaigns"][campaign_id]["status"] = "creating"
        registry["active_campaign"] = previous_active
        store.save_registry(registry)

        apply_campaign_template(paths.root, name, template)
        analysis = config.get("analysis", {})
        director_rules = [row.get("content", "") for row in custom_rules if row.get("enabled") and row.get("target_layer") in {"director", "both"} and row.get("content")]
        actor_rules = [row.get("content", "") for row in custom_rules if row.get("enabled") and row.get("target_layer") in {"actor", "both"} and row.get("content")]
        routing = {"director_rules": director_rules, "actor_rules": actor_rules, "source": "local_new_campaign_form"}
        generated_project = default_chatgpt_project_name()
        generated_conversation = f"{name} \u56fa\u5b9a\u5bf9\u8bdd"
        store.update_chatgpt_binding(campaign_id, generated_project, generated_conversation)
        config.update({
            "analysis": analysis,
            "routing": routing,
            "generated_project": generated_project,
            "generated_conversation": generated_conversation,
        })
        apply_smart_campaign_config(paths.root, config)
        write_custom_rules(campaign_id, config.get("owner_host_id") or current_host_id(), custom_rules)

        registry = store.load_registry()
        registry.setdefault("campaigns", {}).setdefault(campaign_id, {})
        registry["campaigns"][campaign_id].update({
            "name": name,
            "status": "active",
            "initialization_status": "ready",
            "updated_at": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
        })
        registry["active_campaign"] = campaign_id
        store.save_registry(registry)
    except Exception:
        cleanup_failed_campaign(campaign_id, previous_active)
        raise
    if progress:
        progress(100, "初始化完成，正在进入控制台")
    return {
        "ok": True,
        "campaign_id": campaign_id,
        "analysis": analysis,
        "routing": routing,
        "api_key_persisted": False,
        "api_key_ref": next((slot.get("api_key_ref", "") for slot in config["model_config"].get("model_slots", {}).values() if slot.get("api_key_ref")), ""),
        "custom_api_key_received": config.get("custom_api_key_received", False),
        "status": status_payload(),
    }


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


def cleanup_failed_campaign(campaign_id: str, previous_active: str = "") -> None:
    safe_id = safe_segment(campaign_id)
    if not safe_id or safe_id != campaign_id:
        return
    root = CAMPAIGNS_DIR / safe_id
    try:
        if root.exists():
            shutil.rmtree(root)
    finally:
        store = MemoryStore()
        registry = store.load_registry()
        campaigns = registry.setdefault("campaigns", {})
        campaigns.pop(campaign_id, None)
        registry["active_campaign"] = previous_active if previous_active in campaigns else next(iter(campaigns.keys()), "")
        store.save_registry(registry)


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
    character_path = root / "character_prompt.json"
    companion_path = root / "companion_profiles.json"
    profile = read_json(profile_path)
    direction = read_json(direction_path)
    style = read_json(style_path)
    image = read_json(image_path)
    npc = read_json(npc_path)
    character = read_json(character_path)
    companions = read_json(companion_path)
    analysis = config.get("analysis", {})
    routing = config.get("routing", {})
    model_config = dict(config.get("model_config") or {})
    rules_config = dict(config.get("rules_config") or {})
    story_config = dict(config.get("story_config") or resolve_story_config("medium"))
    character_card = dict(config.get("character_card") or {})
    companion_config = dict(config.get("companion_config") or {})
    safety_lines = list(config.get("safety_lines") or [])
    v4_setup = config.get("v4_setup", {}) if isinstance(config.get("v4_setup"), dict) else {}
    v4_direction = v4_setup.get("campaign_direction", {}) if isinstance(v4_setup.get("campaign_direction"), dict) else {}
    v4_story_patch = v4_setup.get("story_blueprint_patch", {}) if isinstance(v4_setup.get("story_blueprint_patch"), dict) else {}
    v4_protagonist = v4_setup.get("protagonist_patch", {}) if isinstance(v4_setup.get("protagonist_patch"), dict) else {}
    v4_companion = v4_setup.get("companion_patch", {}) if isinstance(v4_setup.get("companion_patch"), dict) else {}
    v4_safety = v4_setup.get("safety_interpretation", {}) if isinstance(v4_setup.get("safety_interpretation"), dict) else {}
    v4_memory = v4_setup.get("initial_memory_notes", {}) if isinstance(v4_setup.get("initial_memory_notes"), dict) else {}
    mode = next((row for row in ai_mode_options() if row["id"] == model_config.get("model_mode")), ai_mode_options()[0])
    profile.update({
        "title": config.get("name", profile.get("title", "")),
        "name": config.get("name", profile.get("title", "")),
        "initialization_status": "ready",
        "template": config.get("template", "custom"),
        "genre": analysis.get("genre", ""),
        "tone": analysis.get("tone", ""),
        "analysis": analysis,
        "initial_prompt": config.get("user_prompt", ""),
        "user_prompt": config.get("user_prompt", ""),
        "model_config": model_config,
        "rules_config": rules_config,
        "story_config": story_config,
        "companion_config": companion_config,
        "safety_lines": safety_lines,
        "ai_mode": mode,
        "mechanics": {
            "use_dice": bool(rules_config.get("dice_enabled")),
            "dice_system": rules_config.get("dice_type", ""),
            "use_combat_rules": rules_config.get("rules_strictness") == "strict",
            "stats_style": rules_config.get("stat_visibility", "narrative"),
            "roll_mode": rules_config.get("roll_mode", ""),
            "roll_attributes": rules_config.get("roll_attributes", []),
            "attribute_config": rules_config.get("attribute_config", {}),
            "attribute_roll_config": rules_config.get("attribute_roll_config", {}),
        },
        "prompt_routing": {
            "director_receives": ["campaign_profile", "campaign_direction", "director_rules", "memory"],
            "actor_receives": ["chatgpt_host_prompt", "style_rules", "dialogue_rules", "image_rules", "actor_rules"],
            "custom_rule_classification": routing,
        },
        "director_setup": v4_setup,
    })
    profile["hard_limits"] = list(dict.fromkeys([*profile.get("hard_limits", []), *safety_lines]))

    direction.setdefault("background_direction", []).append(analysis.get("premise", ""))
    direction.setdefault("background_direction", []).extend([
        item for item in [
            v4_direction.get("core_concept", ""),
            v4_direction.get("opening_situation", ""),
            v4_direction.get("main_conflict", ""),
        ] if item
    ])
    direction.setdefault("theme_and_tone", []).extend([analysis.get("genre", ""), analysis.get("tone", "")])
    direction.setdefault("pace_rules", []).extend(routing.get("director_rules", []))
    direction.setdefault("early_goals", []).extend(v4_direction.get("early_goals", []) if isinstance(v4_direction.get("early_goals"), list) else [])
    direction.setdefault("known_boundaries", []).extend(v4_direction.get("known_boundaries", []) if isinstance(v4_direction.get("known_boundaries"), list) else [])
    direction.setdefault("secrets_not_to_reveal_early", []).extend(v4_direction.get("secrets_not_to_reveal_early", []) if isinstance(v4_direction.get("secrets_not_to_reveal_early"), list) else [])
    direction.setdefault("director_notes", []).extend(v4_direction.get("director_notes", []) if isinstance(v4_direction.get("director_notes"), list) else [])
    direction.setdefault("setup_controls", []).extend([
        f"template={config.get('template', 'custom')}",
        f"model_mode={model_config.get('model_mode', '')}",
        f"character_card_enabled={rules_config.get('character_card_enabled')}",
        f"stat_visibility={rules_config.get('stat_visibility', '')}",
        f"story_length={story_config.get('story_length', 'medium')}",
        f"attribute_enabled={rules_config.get('attribute_config', {}).get('enabled')}",
        f"dice_enabled={rules_config.get('dice_enabled')}",
        f"rules_strictness={rules_config.get('rules_strictness', '')}",
        f"companion_enabled={companion_config.get('companion_enabled')}",
    ])
    if safety_lines:
        direction.setdefault("safety_rules", []).extend(safety_lines)
    direction.setdefault("safety_interpretation", {}).update(v4_safety)
    direction.setdefault("initial_memory_notes", {}).update(v4_memory)

    style.setdefault("prose_style", []).extend(routing.get("actor_rules", []))
    image.setdefault("image_generation_rules", []).append("Use merged canvas and image rules from default rule bundle; cache generated PNG assets locally.")
    npc.setdefault("voice_rules", {})["custom_actor_rules"] = routing.get("actor_rules", [])

    character["character_card_enabled"] = bool(rules_config.get("character_card_enabled"))
    character["stat_visibility"] = rules_config.get("stat_visibility", "narrative")
    character["dice_enabled"] = bool(rules_config.get("dice_enabled"))
    character["roll_attributes"] = rules_config.get("roll_attributes", [])
    identity = character_card.get("identity", {}) if isinstance(character_card.get("identity"), dict) else {}
    profile_data = character_card.get("profile", {}) if isinstance(character_card.get("profile"), dict) else {}
    character["confirmed_identity"] = {
        "name": identity.get("name", ""),
        "role": identity.get("role", ""),
        "title": identity.get("title", ""),
        "summary": identity.get("summary", ""),
    }
    character["confirmed_background"] = [item for item in [profile_data.get("background", ""), v4_protagonist.get("confirmed_background", "")] if item]
    character["personality_and_voice"] = [item for item in [profile_data.get("personality", ""), v4_protagonist.get("personality_and_voice", "")] if item]
    character["abilities_and_limits"] = [item for item in ["属性值已记录在 player_state.json 的 player.character_card.attributes。", v4_protagonist.get("abilities_and_limits", "")] if item]
    character["growth_direction"] = [item for item in [profile_data.get("motivation", ""), v4_protagonist.get("growth_direction", "")] if item]
    character["unknown_or_player_owned"] = ["未填写或未确认的主角细节由玩家后续确认。", *sanitize_string_list(v4_protagonist.get("unknown_or_player_owned"))]
    if companion_config.get("companion_enabled"):
        companion_note = {
            "enabled": True,
            "mode": companion_config.get("companion_mode", "auto"),
            "name": companion_config.get("companion_name", ""),
            "role": companion_config.get("companion_role", ""),
            "personality": companion_config.get("companion_personality", ""),
            "card_visible": bool(companion_config.get("companion_card_visible")),
        }
        character["companion_request"] = companion_note
        companion_name = str(companion_config.get("companion_name") or "").strip()
        companion_role = str(companion_config.get("companion_role") or "").strip()
        companion_personality = str(companion_config.get("companion_personality") or "").strip()
        if not companion_name and bool(v4_companion.get("enabled")) and not is_unresolved_text(v4_companion.get("name")):
            companion_name = stringify_brief(v4_companion.get("name"), 80)
            companion_role = companion_role or stringify_brief(v4_companion.get("role") or v4_companion.get("relationship_to_protagonist"), 120)
            companion_personality = companion_personality or stringify_brief(v4_companion.get("personality"), 160)
        if companion_name:
            character["companion_card"] = {
                "name": companion_name,
                "kind": "companion",
                "archetype": "companion",
                "role": companion_role,
                "personality": companion_personality,
                "relationship_to_protagonist": stringify_brief(v4_companion.get("relationship_to_protagonist"), 180),
                "unknown_or_later": sanitize_string_list(v4_companion.get("unknown_or_later"), 8),
                "visible": bool(companion_config.get("companion_card_visible")),
                "visual_seed": f"companion:{safe_segment(companion_name.lower())}",
            }
            companions.setdefault("profiles", {})[safe_segment(companion_name.lower())] = {
                "name": companion_name,
                "role": companion_role,
                "personality": companion_personality,
                "relationship_to_protagonist": stringify_brief(v4_companion.get("relationship_to_protagonist"), 180),
                "visible": bool(companion_config.get("companion_card_visible")),
                "source": "v4_campaign_setup" if not companion_config.get("companion_name") else "new_campaign_form",
            }
    else:
        character.pop("companion_request", None)
        character.pop("companion_card", None)

    player_path = root / "player_state.json"
    player = read_json(player_path)
    character_card["vitals"] = build_character_vitals_from_three(character_card.get("attributes"))
    player["character_card"] = character_card

    blueprint_path = root / "story_blueprint.json"
    blueprint = read_json(blueprint_path) if blueprint_path.exists() else {}
    blueprint.update({
        "campaign_id": profile.get("campaign_id", ""),
        "schema": "trpg_orchestrator.story_blueprint.v1",
        "story_length": story_config.get("story_length", "medium"),
        "target_total_chars": story_config.get("target_total_chars", 80000),
        "target_chapters": story_config.get("target_chapters", 6),
        "target_nodes": story_config.get("target_nodes", 24),
        "chapters": blueprint.get("chapters", []) if isinstance(blueprint.get("chapters"), list) else [],
        "notes": blueprint.get("notes", []) if isinstance(blueprint.get("notes"), list) else [],
    })
    blueprint["notes"].extend(v4_story_patch.get("notes", []) if isinstance(v4_story_patch.get("notes"), list) else [])
    if isinstance(v4_story_patch.get("chapter_seeds"), list) and v4_story_patch.get("chapter_seeds"):
        blueprint["chapter_seeds"] = v4_story_patch.get("chapter_seeds")
    blueprint["chapters"] = synthesize_story_chapters(blueprint, story_config)

    progress_path = root / "story_progress.json"
    progress = read_json(progress_path) if progress_path.exists() else {}
    progress = ensure_story_progress_current(progress, blueprint)

    write_json(profile_path, profile)
    write_json(direction_path, direction)
    write_json(style_path, style)
    write_json(image_path, image)
    write_json(npc_path, npc)
    write_json(character_path, character)
    write_json(companion_path, companions)
    write_json(player_path, player)
    write_json(blueprint_path, blueprint)
    write_json(progress_path, progress)

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
    if template not in {"dnd", "coc", "custom"}:
        raise RuntimeError("template must be custom, coc, or dnd")
    paths = MemoryStore().init_campaign(campaign_id, name)
    apply_campaign_template(paths.root, name, template)
    return {"ok": True, "campaign_id": campaign_id, "template": template, "root": str(paths.root), "status": status_payload()}


def apply_campaign_template(root: Path, name: str, template: str) -> None:
    template = str(template or "custom").strip().lower()
    if template not in CAMPAIGN_TEMPLATE_DEFAULTS:
        template = "custom"
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
        character["companion_card"] = {"name": "Assassin", "kind": "companion", "archetype": "companion", "class": "Assassin", "true_name": "\u672a\u516c\u5f00", "personality": "\u5e73\u9759\u3001\u514b\u5236\u3001\u5371\u9669\u3001\u4e0d\u54c4\u4eba\u3001\u4e0d\u8f7b\u6613\u89e3\u91ca", "visual_seed": "companion:assassin:lingchuan"}
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
        "memory_files": {name: redact_secret_values(read_json(root / name)) for name in MEMORY_FILE_NAMES if (root / name).exists()},
        "asset_manifest": load_asset_manifest(resolved),
        "recent_logs": logs,
        "outbox": safe_outbox_snapshot(resolved),
    }


def redact_secret_values(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            lower = str(key).lower()
            if "api_key" in lower and not lower.endswith("_ref"):
                redacted[key] = ""
            else:
                redacted[key] = redact_secret_values(item)
        return redacted
    if isinstance(value, list):
        return [redact_secret_values(item) for item in value]
    return value


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


def current_visible_prose_chars(campaign_id: str = "") -> int:
    outbox_dir = resolve_outbox_dir(campaign_id)
    blocks_path = outbox_dir / "chatgpt_blocks.json"
    if blocks_path.exists():
        data = read_json(blocks_path)
        blocks = data.get("blocks") if isinstance(data, dict) else []
        return visible_prose_chars(blocks)
    raw_path = outbox_dir / "chatgpt_raw_output.md"
    if raw_path.exists():
        parsed = parse_chatgpt_output(read_runtime_text(raw_path))
        return visible_prose_chars(parsed.blocks)
    return 0


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
        pending_updates = apply_approved_writeback(memory, approved, extra_hashes=[raw_digest], pressure_pack=pressure_pack, prose_chars_delta=current_visible_prose_chars(resolved))
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
    updates = apply_approved_writeback(memory, approved, extra_hashes=[raw_digest], pressure_pack=pressure_pack, prose_chars_delta=current_visible_prose_chars(resolved))
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
    visible_campaigns = campaign_list(registry)
    if cid and not any(row.get("campaign_id") == cid for row in visible_campaigns):
        cid = visible_campaigns[0]["campaign_id"] if visible_campaigns else ""
        registry["active_campaign"] = cid
        store.save_registry(registry)
        visible_campaigns = campaign_list(registry)
    current = campaigns.get(cid, {}) if cid else {}
    output = output_payload(cid) if cid else empty_output_payload("", "no active campaign")
    return {
        "project_root": str(PROJECT_ROOT),
        "active_campaign": cid,
        "campaigns": campaigns,
        "campaign_list": visible_campaigns,
        "campaign_state": campaign_state(cid),
        "chatgpt_project": current.get("chatgpt_project_name", ""),
        "chatgpt_conversation": current.get("chatgpt_conversation_name", ""),
        "job": JOB.snapshot(),
        "output": output,
    }

def campaign_list(registry: dict[str, Any]) -> list[dict[str, Any]]:
    active = registry.get("active_campaign") or ""
    rows = []
    for campaign_id, meta in registry.get("campaigns", {}).items():
        root = CAMPAIGNS_DIR / campaign_id
        status = str(meta.get("initialization_status") or "").lower()
        if status in {"creating", "failed"}:
            continue
        if not root.exists():
            continue
        missing_key_files = not (root / "campaign_profile.json").exists() or not (root / "player_state.json").exists()
        if missing_key_files and status != "ready":
            continue
        profile = read_json(root / "campaign_profile.json") if (root / "campaign_profile.json").exists() else {}
        if str(profile.get("initialization_status") or "").lower() in {"creating", "failed"}:
            continue
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
        "template": profile.get("template", "custom"),
        "genre": profile.get("genre", ""),
        "tone": profile.get("tone", ""),
        "mechanics": profile.get("mechanics", {}),
        "rules_config": profile.get("rules_config", {}),
        "story_config": normalize_story_config(profile.get("story_config", {})),
        "companion_config": profile.get("companion_config", {}),
        "model_config": summarize_model_config(profile.get("model_config", {})),
        "safety_lines": list_payload(profile.get("safety_lines")),
        "campaign_direction": maybe("campaign_direction.json"),
        "style_profile": maybe("style_profile.json"),
        "image_profile": maybe("image_profile.json"),
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


def delete_campaign_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_campaign_id = str(payload.get("campaign_id", "")).strip()
    campaign_id = safe_segment(raw_campaign_id)
    if not raw_campaign_id or raw_campaign_id != campaign_id:
        raise RuntimeError("invalid campaign_id")

    store = MemoryStore()
    registry = store.load_registry()
    campaigns = registry.setdefault("campaigns", {})
    if campaign_id not in campaigns:
        raise RuntimeError(f"unknown campaign_id: {campaign_id}")

    campaigns_root = CAMPAIGNS_DIR.resolve()
    root = (CAMPAIGNS_DIR / campaign_id).resolve()
    if root.parent != campaigns_root or root == campaigns_root:
        raise RuntimeError("campaign path is unsafe")

    if root.exists():
        if not root.is_dir():
            raise RuntimeError("campaign path is not a directory")
        shutil.rmtree(root)

    campaigns.pop(campaign_id, None)
    if registry.get("active_campaign") == campaign_id:
        registry["active_campaign"] = next(iter(campaigns.keys()), "")
    store.save_registry(registry)
    return {"ok": True, "deleted_campaign_id": campaign_id, "status": status_payload()}


def set_new_campaign_job(job_key: str, **updates: Any) -> None:
    with NEW_CAMPAIGN_JOBS_LOCK:
        job = NEW_CAMPAIGN_JOBS.setdefault(job_key, {})
        job.update(updates)
        job["updated_at"] = time.time()


def start_create_campaign_smart_job(payload: dict[str, Any]) -> dict[str, Any]:
    job_id = f"new_campaign_{int(time.time() * 1000)}_{safe_segment(str(threading.get_ident()))}"
    set_new_campaign_job(
        job_id,
        ok=True,
        job_id=job_id,
        stage="queued",
        percent=1,
        label="开始初始化故事",
        done=False,
        error="",
        campaign_id="",
        result={},
        created_at=time.time(),
    )

    def progress(percent: int, label: str, public_think: Any = None) -> None:
        updates: dict[str, Any] = {"stage": "running", "percent": max(1, min(100, int(percent))), "label": label}
        if public_think is not None:
            updates["public_think"] = sanitize_public_think(public_think)
        set_new_campaign_job(job_id, **updates)

    def worker() -> None:
        try:
            result = create_campaign_smart_payload(payload, progress=progress)
            set_new_campaign_job(
                job_id,
                stage="done",
                percent=100,
                label="初始化完成，正在进入控制台",
                done=True,
                error="",
                campaign_id=result.get("campaign_id", ""),
                result=result,
            )
        except Exception as exc:
            set_new_campaign_job(
                job_id,
                stage="error",
                label=str(exc),
                done=True,
                error=str(exc),
                percent=0,
            )

    threading.Thread(target=worker, daemon=True).start()
    return {"ok": True, "job_id": job_id}


def new_campaign_progress_payload(job_id: str) -> dict[str, Any]:
    if not job_id:
        return {"ok": False, "error": "job_id is required"}
    with NEW_CAMPAIGN_JOBS_LOCK:
        job = dict(NEW_CAMPAIGN_JOBS.get(job_id) or {})
    if not job:
        return {"ok": False, "job_id": job_id, "error": f"unknown new campaign job: {job_id}"}
    job["ok"] = True
    return job


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









