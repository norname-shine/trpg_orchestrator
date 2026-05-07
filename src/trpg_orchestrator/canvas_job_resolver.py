# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


CANVAS_JOB_KINDS = {
    "map",
    "portrait",
    "player_portrait",
    "companion_portrait",
    "character_portrait",
    "npc_portrait",
    "monster_portrait",
    "item",
    "prop",
    "gallery_scene",
}
CANVAS_JOB_TRIGGERS = {"user_requested", "director_triggered", "system_required"}
CANVAS_CACHE_POLICIES = {"stable", "scene_only", "rebuild_on_version"}


def resolve_canvas_jobs(pressure_pack: dict[str, Any], campaign_id: str, asset_seed: str) -> list[dict[str, Any]]:
    return canvas_jobs_from_payloads(pressure_pack, campaign_id, asset_seed)


def canvas_jobs_from_payloads(pressure_pack: dict[str, Any], campaign_id: str, asset_seed: str) -> list[dict[str, Any]]:
    payloads = pressure_pack.get("payloads") if isinstance(pressure_pack, dict) else {}
    payloads = payloads if isinstance(payloads, dict) else {}
    output_requests = pressure_pack.get("output_requests") if isinstance(pressure_pack, dict) else {}
    canvas_request = output_requests.get("canvas_jobs", {}) if isinstance(output_requests, dict) and isinstance(output_requests.get("canvas_jobs"), dict) else {}
    map_request = output_requests.get("map", {}) if isinstance(output_requests, dict) and isinstance(output_requests.get("map"), dict) else {}
    jobs = payloads.get("canvas_jobs") if isinstance(payloads.get("canvas_jobs"), list) else []
    resolved: list[dict[str, Any]] = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        item = dict(job)
        item.setdefault("campaign_id", campaign_id)
        item.setdefault("asset_seed", asset_seed)
        validate_canvas_job(item)
        resolved.append(item)
    if resolved:
        return resolved
    if canvas_request.get("mode") == "create" or map_request.get("mode") == "update_canvas":
        route = payloads.get("map_route") if isinstance(payloads.get("map_route"), dict) else {}
        if route.get("nodes"):
            job = {
                "job_id": "map_current_area",
                "kind": "map",
                "renderer": "pixel_map",
                "trigger": "director_triggered",
                "input_ref": "payloads.map_route",
                "asset_key": "map:current_area",
                "cache_policy": "stable",
                "campaign_id": campaign_id,
                "asset_seed": asset_seed,
            }
            validate_canvas_job(job)
            return [job]
    return []


def validate_canvas_job(job: dict[str, Any]) -> None:
    if not isinstance(job, dict):
        raise ValueError("canvas job must be an object")
    for key in ("job_id", "kind", "renderer", "trigger", "input_ref", "asset_key", "cache_policy"):
        if not str(job.get(key) or "").strip():
            raise ValueError(f"canvas job missing {key}")
    if job.get("kind") not in CANVAS_JOB_KINDS:
        raise ValueError(f"invalid canvas job kind: {job.get('kind')}")
    if job.get("trigger") not in CANVAS_JOB_TRIGGERS:
        raise ValueError(f"invalid canvas job trigger: {job.get('trigger')}")
    if job.get("cache_policy") not in CANVAS_CACHE_POLICIES:
        raise ValueError(f"invalid canvas job cache_policy: {job.get('cache_policy')}")
    text = " ".join(str(job.get(key) or "").lower() for key in ("job_id", "input_ref", "asset_key"))
    if "placeholder" in text or text.strip() in {"", "trpg"}:
        raise ValueError("placeholder canvas job forbidden")
