# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any

from .capability_events import detect_capability_events


DEFAULT_CAPABILITIES = ["base_director", "base_actor", "story_progress", "recent_context"]


KEYWORDS = {
    "map": ["地图", "更新地图", "点阵地图", "路线", "区域图", "map", "route"],
    "image": ["生图", "生成图", "画图", "图片", "立绘", "头像", "场景图", "怪物图", "image", "generate image", "portrait"],
    "dossier": ["资料", "资料夹", "档案", "dossier", "archive"],
    "inventory": ["物品", "背包", "装备", "道具", "检查物品", "使用", "获得", "丢失", "inventory", "item", "equipment"],
    "character_card": ["角色卡", "状态", "属性", "受伤", "成长", "经验", "character", "status", "injury", "growth"],
    "dice": ["检定", "骰子", "投骰", "判定", "d20", "dice", "roll", "check"],
}

NEGATED_IMAGE_PATTERNS = [
    "不生图",
    "不要生图",
    "别生图",
    "不生成图",
    "不要生成图",
    "别生成图",
    "no image",
    "do not generate image",
    "don't generate image",
]


def build_capability_plan(
    campaign_id: str,
    player_action: str,
    memory: dict[str, Any],
    frontend_flags: dict[str, Any] | None = None,
) -> dict[str, Any]:
    action = str(player_action or "")
    action_lower = action.lower()
    loaded = list(DEFAULT_CAPABILITIES)
    explicit: list[str] = []
    secondary: list[str] = []
    warnings: list[str] = []
    events = detect_capability_events(action, memory)
    image_negated = _has_negated_image(action_lower) or any(event.get("event") == "image_negated" for event in events)

    def enable(name: str, request: str | None = None) -> None:
        if name == "visual_assets" and image_negated:
            return
        if name not in loaded:
            loaded.append(name)
        if request and request not in explicit:
            explicit.append(request)
        if request and request not in secondary:
            secondary.append(request)

    if _has_keywords(action_lower, KEYWORDS["map"]):
        enable("map", "user_requested_map")
    if _has_keywords(action_lower, KEYWORDS["image"]) and not image_negated:
        enable("visual_assets", "user_requested_image")
    if _has_keywords(action_lower, KEYWORDS["dossier"]):
        enable("dossier", "user_requested_dossier")
    if _has_keywords(action_lower, KEYWORDS["inventory"]):
        enable("inventory", "user_requested_inventory")
    if _has_keywords(action_lower, KEYWORDS["character_card"]):
        enable("character_card", "user_requested_character_card")
    if _has_keywords(action_lower, KEYWORDS["dice"]):
        enable("dice_check_requested", "user_requested_dice")

    for event in events:
        event_name = str(event.get("event") or "")
        confidence = str(event.get("confidence") or "")
        if event_name == "image_negated":
            warnings.append("visual_assets_disabled_by_player_request")
            continue
        if confidence != "high":
            warnings.append(f"possible_{event_name}_detected_but_low_confidence")
            continue
        for capability, request in _event_capability_requests(event_name):
            enable(capability, request)

    recent = memory.get("recent_context.json", {}) if isinstance(memory, dict) else {}
    scene = recent.get("current_scene", {}) if isinstance(recent, dict) else {}
    active_npcs = scene.get("active_npcs", []) if isinstance(scene, dict) else []
    if isinstance(active_npcs, list) and active_npcs:
        enable("npc_voice")
        enable("npc_present")

    pressure_text = " ".join(
        str(value)
        for value in [
            scene.get("immediate_pressure", "") if isinstance(scene, dict) else "",
            recent.get("last_outcome", "") if isinstance(recent, dict) else "",
        ]
    ).lower()
    if _has_keywords(pressure_text, ["enemy", "monster", "mystery", "怪物", "敌", "谜", "危险", "威胁"]):
        enable("enemy_or_mystery")

    profile = memory.get("campaign_profile.json", {}) if isinstance(memory, dict) else {}
    mechanics = profile.get("mechanics", {}) if isinstance(profile, dict) else {}
    if isinstance(mechanics, dict) and mechanics.get("use_dice") is True:
        enable("dice_possible")

    if isinstance(frontend_flags, dict):
        if frontend_flags.get("map_panel") == "update":
            enable("map", "frontend_requested_map")

    for capability, request in _forecast_capability_requests(memory, warnings):
        enable(capability, request)

    if image_negated and "visual_assets" in loaded:
        loaded = [capability for capability in loaded if capability != "visual_assets"]
        explicit = [request for request in explicit if request not in {"user_requested_image", "event_requested_image"}]
        secondary = [request for request in secondary if request not in {"user_requested_image", "event_requested_image"}]

    return {
        "schema": "trpg_orchestrator.capability_plan.v1",
        "campaign_id": campaign_id,
        "turn_intent": {
            "primary": _primary_intent(explicit),
            "secondary": secondary,
            "user_explicit_requests": explicit,
        },
        "loaded_capabilities": loaded,
        "prompt_modules": {"director": [], "actor": [], "audit": [], "excluded": []},
        "memory_refs": {"director": [], "actor_visible": [], "audit": []},
        "output_contract": {
            "allow_map_payload": "map" in loaded,
            "allow_visual_assets": "visual_assets" in loaded,
            "visual_assets_scope": "media_only",
            "allow_character_card_update": "character_card" in loaded,
            "allow_dossier_update": "dossier" in loaded,
            "allow_dice_check": "dice_check_requested" in loaded,
            "allow_canvas_jobs": False,
            "allow_story_progress_writeback": True,
            "gallery_assets": "global_state_writeback",
            "inventory_items": "global_state_writeback",
        },
        "frontend_refresh": {
            "story_log": "update",
            "story_progress": "update",
            "map_panel": "update" if "map" in loaded else "keep_previous",
            "gallery": "extension_store",
            "inventory": "extension_store",
            "character_card": "update" if "character_card" in loaded else "no_update",
            "dossier": "update" if "dossier" in loaded else "no_update",
        },
        "warnings": warnings,
    }


def _has_keywords(text: str, keywords: list[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def _has_negated_image(text: str) -> bool:
    compact = re.sub(r"\s+", " ", text)
    return any(pattern in compact for pattern in NEGATED_IMAGE_PATTERNS)


def _primary_intent(explicit: list[str]) -> str:
    if not explicit:
        return "continue_scene"
    return explicit[0]


def _event_capability_requests(event_name: str) -> list[tuple[str, str]]:
    mapping = {
        "location_changed": [("map", "event_location_changed")],
        "item_obtained": [("inventory", "event_item_obtained")],
        "item_lost": [("inventory", "event_item_lost")],
        "item_inspected": [("inventory", "event_item_inspected")],
        "clue_observed": [],
        "npc_present": [("npc_voice", "event_npc_present"), ("npc_present", "event_npc_present")],
        "status_changed": [("character_card", "event_status_changed")],
        "dice_requested": [("dice_check_requested", "event_dice_requested")],
        "image_requested": [("visual_assets", "event_requested_image")],
    }
    return mapping.get(event_name, [])


def _forecast_capability_requests(memory: dict[str, Any], warnings: list[str]) -> list[tuple[str, str]]:
    recent = memory.get("recent_context.json", {}) if isinstance(memory, dict) else {}
    forecast = recent.get("orchestration_forecast") if isinstance(recent, dict) else {}
    if not isinstance(forecast, dict) or forecast.get("for_backend_only") is not True:
        return []
    current_turn = int(recent.get("turn_index", 0) or 0)
    expires_at = int(forecast.get("expires_at_turn", current_turn) or 0)
    if expires_at < current_turn:
        return []
    valid_until = str(forecast.get("valid_until_node_id") or "").strip()
    current_node = _current_node_id(memory)
    if valid_until and current_node and valid_until != current_node:
        return []
    hotload = forecast.get("hotload_next_turn")
    if not isinstance(hotload, dict):
        return []
    result: list[tuple[str, str]] = []
    for bucket in ("director_modules", "actor_modules", "payload_modules"):
        modules = hotload.get(bucket)
        if not isinstance(modules, list):
            continue
        for raw in modules:
            module = str(raw or "").strip()
            if not module:
                continue
            mapped = _forecast_module_capability(module)
            if not mapped:
                warnings.append(f"unknown orchestration_forecast module ignored: {module}")
                continue
            if mapped not in result:
                result.append(mapped)
    return result


def _forecast_module_capability(module: str) -> tuple[str, str] | None:
    mapping = {
        "director_visual_payload_min": ("visual_preload", "forecast_visual_preload"),
        "director_map_payload_min": ("map_preload", "forecast_map_preload"),
        "npc_voice_deep": ("dialogue_heavy_preload", "forecast_dialogue_heavy_preload"),
    }
    return mapping.get(module)


def _current_node_id(memory: dict[str, Any]) -> str:
    story_progress = memory.get("story_progress.json", {}) if isinstance(memory, dict) else {}
    if isinstance(story_progress, dict):
        for key in ("current_node_id", "active_node_id"):
            value = str(story_progress.get(key) or "").strip()
            if value:
                return value
        current_node = story_progress.get("current_node")
        if isinstance(current_node, dict):
            value = str(current_node.get("id") or current_node.get("node_id") or "").strip()
            if value:
                return value
    recent = memory.get("recent_context.json", {}) if isinstance(memory, dict) else {}
    if isinstance(recent, dict):
        value = str(recent.get("current_node_id") or "").strip()
        if value:
            return value
        scene = recent.get("current_scene")
        if isinstance(scene, dict):
            return str(scene.get("node_id") or scene.get("current_node_id") or "").strip()
    return ""
