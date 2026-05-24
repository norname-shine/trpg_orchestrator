# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


REQUEST_TO_CAPABILITY = {
    "map": "map",
    "visual_assets": "visual_assets",
    "character_card": "character_card",
    "dossier": "dossier",
    "dice_or_check": "dice_or_check",
    "canvas_jobs": "canvas_jobs",
}

OPTIONAL_WRITEBACK_TO_REQUEST = {
    "map": "map",
    "map_route": "map",
    "map_canvas": "map",
    "visual_assets": "visual_assets",
    "character_card": "character_card",
    "character_card_update": "character_card",
    "dossier": "dossier",
    "dossier_updates": "dossier",
    "dice_or_check": "dice_or_check",
    "dice_check_request": "dice_or_check",
    "canvas_jobs": "canvas_jobs",
}

PAYLOAD_KEY_TO_REQUEST = {
    "map_route": "map",
    "map_canvas": "map",
    "visual_assets": "visual_assets",
    "character_card_update": "character_card",
    "dossier_updates": "dossier",
    "dice_check_request": "dice_or_check",
    "canvas_jobs": "canvas_jobs",
}


def output_requests_to_capabilities(output_requests: dict[str, Any]) -> list[str]:
    if not isinstance(output_requests, dict):
        return []
    capabilities: list[str] = []
    for module, capability in REQUEST_TO_CAPABILITY.items():
        request = output_requests.get(module)
        if not isinstance(request, dict):
            continue
        mode = str(request.get("mode") or "none")
        if _request_mode_authorizes(module, mode) and capability not in capabilities:
            capabilities.append(capability)
    return capabilities


def is_optional_writeback_authorized(optional_key: str, output_requests: dict[str, Any]) -> bool:
    module = OPTIONAL_WRITEBACK_TO_REQUEST.get(optional_key)
    if not module or not isinstance(output_requests, dict):
        return False
    request = output_requests.get(module)
    if not isinstance(request, dict):
        return False
    return _request_mode_authorizes(module, str(request.get("mode") or "none"))


def is_payload_authorized(payload_key: str, output_requests: dict[str, Any]) -> bool:
    module = PAYLOAD_KEY_TO_REQUEST.get(payload_key)
    if not module or not isinstance(output_requests, dict):
        return False
    request = output_requests.get(module)
    if not isinstance(request, dict):
        return False
    return _request_mode_authorizes(module, str(request.get("mode") or "none"))


def validate_payload_contract(payloads: dict[str, Any], output_requests: dict[str, Any]) -> None:
    if payloads in (None, {}):
        return
    if not isinstance(payloads, dict):
        raise ValueError("payloads must be an object")
    for key, value in payloads.items():
        if not is_payload_authorized(key, output_requests):
            raise ValueError(f"payloads.{key} is not authorized")
        if not _valid_payload(key, value):
            raise ValueError(f"payloads.{key} is empty or placeholder")


def filter_unauthorized_payloads(payloads: dict[str, Any], output_requests: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(payloads, dict):
        return {}, ["payloads ignored because it is not an object"]
    filtered: dict[str, Any] = {}
    warnings: list[str] = []
    for key, value in payloads.items():
        if not is_payload_authorized(key, output_requests):
            warnings.append(f"unauthorized payload ignored: {key}")
            continue
        if not _valid_payload(key, value):
            warnings.append(f"empty or placeholder payload ignored: {key}")
            continue
        filtered[key] = value
    return filtered, warnings


def summarize_payload_keys(pressure_pack: dict[str, Any]) -> dict[str, Any]:
    payloads = pressure_pack.get("payloads") if isinstance(pressure_pack, dict) else {}
    if not isinstance(payloads, dict):
        payloads = {}
    return {
        "payload_keys": sorted(payloads.keys()),
        "top_level_payload_keys": sorted(
            key for key in ("map_route", "map_canvas", "visual_assets") if isinstance(pressure_pack, dict) and key in pressure_pack
        ),
        "non_empty_payload_keys": sorted(key for key, value in payloads.items() if _has_payload(value)),
    }


def _request_mode_authorizes(module: str, mode: str) -> bool:
    if module == "map":
        return mode in {"update_route", "update_canvas"}
    if module == "visual_assets":
        return mode in {"create", "update"}
    if module == "dice_or_check":
        return mode == "request_check"
    if module == "canvas_jobs":
        return mode == "create"
    return mode == "update"


def _has_payload(value: Any) -> bool:
    if value in (None, "", [], {}):
        return False
    return True


def _valid_payload(key: str, value: Any) -> bool:
    if not _has_payload(value):
        return False
    if key in {"visual_assets", "dossier_updates"}:
        return isinstance(value, list) and any(_valid_payload_item(item) for item in value)
    if key == "canvas_jobs":
        return isinstance(value, list) and all(_valid_canvas_job(item) for item in value) and bool(value)
    if key in {"map_route", "map_canvas", "character_card_update", "dice_check_request"}:
        return isinstance(value, dict) and _valid_payload_item(value)
    return _valid_payload_item(value)


def _valid_payload_item(item: Any) -> bool:
    if item in (None, "", [], {}):
        return False
    if isinstance(item, str):
        text = item.strip().lower()
        return bool(text) and text not in {"placeholder", "todo", "tbd", "trpg"}
    if isinstance(item, dict):
        text = " ".join(str(value).lower() for value in item.values() if isinstance(value, (str, int, float)))
        meaningful = [key for key, value in item.items() if key not in {"id", "title", "name", "asset_key"} and _has_payload(value)]
        if not text.strip() and not meaningful:
            return False
        if "placeholder" in text or text.strip() in {"trpg", "todo", "tbd"}:
            return False
        return bool(meaningful)
    if isinstance(item, list):
        return any(_valid_payload_item(value) for value in item)
    return True


def _valid_canvas_job(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    required = ("job_id", "kind", "renderer", "trigger", "input_ref", "asset_key", "cache_policy")
    if any(not str(item.get(key) or "").strip() for key in required):
        return False
    text = " ".join(str(item.get(key) or "").lower() for key in required)
    return "placeholder" not in text and "todo" not in text and "tbd" not in text
