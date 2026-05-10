# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from .canvas_job_resolver import resolve_canvas_jobs
from .output_contract import filter_unauthorized_payloads


def build_frontend_modules(
    campaign_id: str,
    frontend_state_base: dict[str, Any],
    pressure_pack: dict[str, Any],
    assets: list[dict[str, Any]],
    story_progress_payload: dict[str, Any],
) -> dict[str, Any]:
    output_requests = pressure_pack.get("output_requests") if isinstance(pressure_pack, dict) else {}
    output_requests = output_requests if isinstance(output_requests, dict) else {}
    payloads = pressure_pack.get("payloads") if isinstance(pressure_pack, dict) else {}
    payloads = payloads if isinstance(payloads, dict) else {}
    payloads, warnings = filter_unauthorized_payloads(payloads, output_requests)
    asset_seed = str(frontend_state_base.get("asset_seed") or campaign_id)
    initialization = frontend_state_base.get("initialization_payload") if isinstance(frontend_state_base.get("initialization_payload"), dict) else {}
    canvas_jobs = resolve_canvas_jobs({"payloads": payloads, "output_requests": output_requests}, campaign_id, asset_seed)
    initial_canvas_jobs = initialization.get("canvas_jobs") if isinstance(initialization.get("canvas_jobs"), list) else []
    canvas_jobs = [*initial_canvas_jobs, *canvas_jobs]
    map_request = _request(output_requests, "map", "keep_previous")
    module_refs = frontend_state_base.get("module_refs", {}) if isinstance(frontend_state_base.get("module_refs"), dict) else {}
    map_panel = initialization.get("map_panel") if isinstance(initialization.get("map_panel"), dict) else {}
    if not map_panel:
        map_panel = _map_module(map_request, payloads, assets, warnings)
    return {
        "story_log": {"mode": "update", "state": "ready", "update_requested": True, "payload": {}, "payload_ref": module_refs.get("story_log", "")},
        "story_progress": {"mode": "update", "state": "ready", "update_requested": True, "payload": story_progress_payload},
        "map_panel": map_panel,
        "dossier": _payload_module(output_requests, payloads, "dossier", "dossier_updates", payloads.get("dossier_updates", []), payload_ref=module_refs.get("dossier", "")),
        "gallery": _removed_module("gallery"),
        "inventory": _removed_module("inventory"),
        "character_card": _payload_module(output_requests, payloads, "character_card", "character_card_update", payloads.get("character_card_update", {}), cached_state="cached"),
        "canvas_jobs": {
            "mode": "update" if canvas_jobs else "no_update",
            "state": "ready" if canvas_jobs else "idle",
            "update_requested": bool(canvas_jobs),
            "payload": canvas_jobs,
        },
        "debug": {"mode": "admin_only", "state": "hidden"},
    }


def _request(output_requests: dict[str, Any], module: str, default_mode: str = "none") -> dict[str, Any]:
    request = output_requests.get(module)
    if not isinstance(request, dict):
        return {"mode": default_mode, "trigger": "none", "reason": ""}
    return request


def _removed_module(module: str) -> dict[str, Any]:
    return {
        "mode": "removed",
        "state": "removed",
        "update_requested": False,
        "payload": [],
        "payload_ref": "",
        "reason": f"legacy {module} module removed; use extension endpoint",
    }


def _map_module(request: dict[str, Any], payloads: dict[str, Any], assets: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
    mode = str(request.get("mode") or "keep_previous")
    latest = next((item for item in assets if item.get("kind") in {"map", "map_image"} or str(item.get("kind", "")).startswith("gallery_map")), {})
    if mode in {"none", "no_update"}:
        return {"mode": "no_update", "state": "idle", "update_requested": False, "payload": {}, "payload_ref": "", "reason": request.get("reason", "")}
    if mode == "keep_previous":
        return {
            "mode": "keep_previous",
            "state": "cached" if latest else "empty",
            "update_requested": False,
            "payload": {},
            "payload_ref": latest.get("url", "") if latest else "",
            "reason": request.get("reason", "") or ("current campaign cached map asset" if latest else "no current campaign map asset"),
        }
    route = payloads.get("map_route") if isinstance(payloads.get("map_route"), dict) and payloads.get("map_route", {}).get("nodes") else {}
    canvas = payloads.get("map_canvas") if isinstance(payloads.get("map_canvas"), dict) else {}
    payload = {"map_route": route, "map_canvas": canvas}
    payload = {key: value for key, value in payload.items() if value}
    return {
        "mode": "update",
        "state": "ready" if payload else "deferred",
        "update_requested": bool(route.get("nodes") or canvas),
        "payload": payload,
        "payload_ref": "",
        "reason": request.get("reason", ""),
        "warnings": warnings,
    }


def _payload_module(
    output_requests: dict[str, Any],
    payloads: dict[str, Any],
    module: str,
    payload_key: str,
    payload: Any,
    cached_state: str = "idle",
    payload_ref: str = "",
) -> dict[str, Any]:
    request = _request(output_requests, module)
    mode = str(request.get("mode") or "none")
    if mode in {"none", "keep_previous"}:
        return {"mode": "no_update", "state": cached_state, "update_requested": False, "payload": {} if isinstance(payload, dict) else [], "payload_ref": payload_ref}
    has_payload = payload not in (None, "", [], {})
    return {
        "mode": "update" if has_payload else "no_update",
        "state": "ready" if has_payload else "deferred",
        "update_requested": has_payload,
        "payload": payload if has_payload else ({} if isinstance(payload, dict) else []),
        "payload_ref": payload_ref,
        "reason": request.get("reason", ""),
    }
