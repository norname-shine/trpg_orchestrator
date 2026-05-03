# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from typing import Any

from .capability_resolver import build_capability_plan
from .config import PROMPTS_DIR
from .encoding_utils import read_runtime_text
from .memory_selector import select_memory_for_actor, select_memory_for_audit, select_memory_for_director
from .output_contract import summarize_payload_keys
from .prompt_module_registry import get_prompt_module_warnings, load_prompt_modules, select_prompt_modules


def read_prompt(name: str) -> str:
    return read_runtime_text(PROMPTS_DIR / name)


DIRECTOR_LAYER_FILES = [
    "campaign_profile.json",
    "character_prompt.json",
    "campaign_direction.json",
    "npc_profiles.json",
    "monster_profiles.json",
    "story_blueprint.json",
    "forbidden_changes.json",
]

RUNTIME_MEMORY_FILES = [
    "recent_context.json",
    "player_state.json",
    "npc_memory.json",
    "world_state.json",
    "location_history.json",
    "quest_history.json",
    "enemy_or_monster_ecology.json",
    "equipment_history.json",
    "main_threads.json",
    "story_progress.json",
]

CHATGPT_VISIBLE_FILES = [
    "campaign_profile.json",
    "style_profile.json",
    "image_profile.json",
    "recent_context.json",
    "player_state.json",
    "npc_memory.json",
    "main_threads.json",
    "forbidden_changes.json",
]


def _pick(memory: dict[str, Any], filenames: list[str]) -> dict[str, Any]:
    return {name: memory.get(name, {}) for name in filenames}


def build_director_user_prompt(
    campaign_id: str,
    player_action: str,
    memory: dict[str, Any],
    capability_plan: dict[str, Any] | None = None,
) -> str:
    capability_plan = capability_plan or build_capability_plan(campaign_id, player_action, memory)
    director_memory = select_memory_for_director(memory, capability_plan)
    module_ids = select_prompt_modules(capability_plan, "director")
    module_text = load_prompt_modules(module_ids)
    _append_module_warnings(capability_plan)
    return "\n\n".join(
        [
            "# V4 Director Turn Input",
            f"campaign_id: {campaign_id}",
            "## Player Action",
            player_action,
            "## Capability Plan",
            "This is local orchestration context. It does not decide story direction.",
            "```json\n" + json.dumps(capability_plan, ensure_ascii=False, indent=2) + "\n```",
            "## Selected Director Prompt Modules",
            module_text,
            "## Selected Director Memory",
            "```json\n" + json.dumps(director_memory, ensure_ascii=False, indent=2) + "\n```",
            "Output only strict pressure_pack JSON. Follow progress_control, output_requests, and payloads contracts. Do not write player-readable prose. Do not expand into a full plot outline.",
        ]
    )


def build_chatgpt_input(
    campaign_id: str,
    player_action: str,
    memory: dict[str, Any],
    pressure_pack: dict[str, Any],
    capability_plan: dict[str, Any] | None = None,
) -> str:
    capability_plan = capability_plan or build_capability_plan(campaign_id, player_action, memory)
    visible_memory = select_memory_for_actor(memory, capability_plan, pressure_pack)
    visible_story_progress = visible_memory.get("actor_visible_story_progress", build_actor_visible_story_progress(memory, pressure_pack))
    module_ids = select_prompt_modules(capability_plan, "actor", pressure_pack)
    module_text = load_prompt_modules(module_ids)
    _append_module_warnings(capability_plan)
    return "\n\n".join(
        [
            "# TRPG Turn Input",
            "## Selected Actor Prompt Modules",
            module_text,
            "## Capability Plan",
            "Use only loaded capabilities and this turn's pressure_pack. Missing capability details are not permission to invent payloads.",
            "```json\n" + json.dumps(capability_plan, ensure_ascii=False, indent=2) + "\n```",
            "## campaign_id",
            campaign_id,
            "## Player Action",
            player_action,
            "## Visible Memory For This Turn",
            "These records are only for performance consistency. Do not expand unconfirmed content. Do not invent long-term setting.",
            "```json\n" + json.dumps(visible_memory, ensure_ascii=False, indent=2) + "\n```",
            "## Visible Story Progress Control",
            "This is a sanitized current-node summary derived from V4 progress_control. It is not a full story blueprint.",
            "```json\n" + json.dumps(visible_story_progress, ensure_ascii=False, indent=2) + "\n```",
            "## Scene Control Pack",
            "Follow this turn's pressure, boundaries, NPC direction, forbidden items, and choice requirements. Do not copy its structure directly.",
            "```json\n" + json.dumps(pressure_pack, ensure_ascii=False, indent=2) + "\n```",
            "Output strict JSON only: blocks, summary, and state_writeback. No text outside JSON.",
        ]
    )


def build_chatgpt_image_input(
    campaign_id: str,
    player_action: str,
    pressure_pack: dict[str, Any],
    visual_assets: list[dict[str, Any]],
) -> str:
    rows = visual_assets[:1] or [{
        "id": "requested_image",
        "title": "本回合关键画面",
        "positive_prompt": "Use the current TRPG scene pressure pack to generate one coherent image. Keep only confirmed visible details.",
        "negative_prompt": "low quality, blurry, text artifacts, watermark, logo, extra limbs, malformed hands, incoherent layout",
        "aspect_ratio": "16:9",
        "style_preset": "cinematic anime urban horror, Fate-inspired, controlled lighting",
        "quality": {"steps": 30, "cfg_scale": 6.5, "sampler": "DPM++ 2M Karras", "size": "1280x720"},
    }]
    return "\n\n".join(
        [
            "# Image Generation Pass",
            "This is a separate image-only conversation pass. Do not continue the story and do not output state writeback JSON.",
            "Generate exactly one image for the first visual asset below. If multiple assets are listed, use only the first one.",
            "Do not include new plot facts. Do not reveal unknown canon details. Use only confirmed or visible scene details.",
            "For cross-device CG previews, prefer a PC-first 16:9 composition. If a dual preview template is explicitly requested, place a 16:9 PC crop on the left and a 9:16 mobile crop on the right, with the main subject inside both safe areas.",
            f"campaign_id: {campaign_id}",
            "Player action that triggered the image pass:",
            player_action,
            "Image asset instruction:",
            "```json\n" + json.dumps(rows[0], ensure_ascii=False, indent=2) + "\n```",
            "Reference control pack for context only:",
            "```json\n" + json.dumps(pressure_pack, ensure_ascii=False, indent=2) + "\n```",
            "Generate one image now. No story prose, no choices, no state writeback.",
        ]
    )


def build_actor_visible_story_progress(memory: dict[str, Any], pressure_pack: dict[str, Any]) -> dict[str, Any]:
    progress_control = pressure_pack.get("progress_control") if isinstance(pressure_pack, dict) else {}
    if not isinstance(progress_control, dict):
        progress_control = {}
    return {
        "current_chapter_id": str(progress_control.get("current_chapter_id") or ""),
        "current_phase_id": str(progress_control.get("current_phase_id") or ""),
        "current_node_id": str(progress_control.get("current_node_id") or ""),
        "current_node_name": str(progress_control.get("current_node_name") or ""),
        "node_goal": str(progress_control.get("node_goal") or ""),
        "beat_targets_this_turn": progress_control.get("beat_targets_this_turn") if isinstance(progress_control.get("beat_targets_this_turn"), list) else [],
        "pace_command": str(progress_control.get("pace_command") or ""),
        "legal_next_nodes": progress_control.get("legal_next_nodes") if isinstance(progress_control.get("legal_next_nodes"), list) else [],
        "must_not_repeat": progress_control.get("must_not_repeat") if isinstance(progress_control.get("must_not_repeat"), list) else [],
    }


def build_v4_light_action_user_prompt(
    campaign_id: str,
    player_action: str,
    memory: dict[str, Any],
) -> str:
    director_context = _pick(memory, DIRECTOR_LAYER_FILES)
    runtime_memory = _pick(memory, RUNTIME_MEMORY_FILES)
    return "\n\n".join(
        [
            f"campaign_id: {campaign_id}",
            "Light action rules:",
            read_prompt("v4_light_action_rules.md"),
            "Player light action:",
            player_action,
            "Long-term context rules:",
            read_prompt("v4_campaign_context_prompt.md"),
            "Long-term context:",
            "```json\n" + json.dumps(director_context, ensure_ascii=False, indent=2) + "\n```",
            "Runtime memory for this turn:",
            "```json\n" + json.dumps(runtime_memory, ensure_ascii=False, indent=2) + "\n```",
            "Output strict JSON only. The JSON must contain blocks, summary, and state_writeback. Keep prose concise and operational because this is a lightweight fixed action.",
        ]
    )


def build_audit_user_prompt(
    campaign_id: str,
    memory: dict[str, Any],
    pressure_pack: dict[str, Any],
    writeback: dict[str, Any],
    capability_plan: dict[str, Any] | None = None,
) -> str:
    capability_plan = capability_plan or build_capability_plan(campaign_id, "", memory)
    audit_memory = select_memory_for_audit(memory, capability_plan, writeback, pressure_pack)
    module_ids = select_prompt_modules(capability_plan, "audit", pressure_pack)
    module_text = load_prompt_modules(module_ids)
    _append_module_warnings(capability_plan)
    return "\n\n".join(
        [
            "# V4 Audit Input",
            f"campaign_id: {campaign_id}",
            "Audit prompt modules:",
            module_text,
            "Capability plan JSON:",
            json.dumps(capability_plan, ensure_ascii=False, indent=2),
            "Pressure pack output_requests JSON:",
            json.dumps(pressure_pack.get("output_requests", {}) if isinstance(pressure_pack, dict) else {}, ensure_ascii=False, indent=2),
            "Pressure pack payload summary JSON:",
            json.dumps(summarize_payload_keys(pressure_pack), ensure_ascii=False, indent=2),
            "Selected audit memory JSON:",
            json.dumps(audit_memory, ensure_ascii=False, indent=2),
            "This turn's pressure pack JSON:",
            json.dumps(pressure_pack, ensure_ascii=False, indent=2),
            "State writeback JSON:",
            json.dumps(writeback, ensure_ascii=False, indent=2),
            "Audit must reject or revise unauthorized optional_writebacks, unsupported payloads, progress_writeback without evidence, forbidden leaks, and unconfirmed long-term facts.",
        ]
    )


def selected_memory_debug(
    campaign_id: str,
    player_action: str,
    memory: dict[str, Any],
    pressure_pack: dict[str, Any] | None = None,
    capability_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    capability_plan = capability_plan or build_capability_plan(campaign_id, player_action, memory)
    director = select_memory_for_director(memory, capability_plan)
    actor = select_memory_for_actor(memory, capability_plan, pressure_pack or {})
    return {"director": director, "actor_visible": actor}


def selected_prompt_modules_debug(
    capability_plan: dict[str, Any],
    pressure_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    director = select_prompt_modules(capability_plan, "director", pressure_pack)
    actor = select_prompt_modules(capability_plan, "actor", pressure_pack)
    audit = select_prompt_modules(capability_plan, "audit", pressure_pack)
    return {
        "director": director,
        "actor": actor,
        "audit": audit,
        "excluded": capability_plan.get("prompt_modules", {}).get("excluded", []) if isinstance(capability_plan.get("prompt_modules"), dict) else [],
    }


def _append_module_warnings(capability_plan: dict[str, Any]) -> None:
    warnings = get_prompt_module_warnings()
    if not warnings or not isinstance(capability_plan, dict):
        return
    target = capability_plan.setdefault("warnings", [])
    if not isinstance(target, list):
        capability_plan["warnings"] = warnings
        return
    for warning in warnings:
        if warning not in target:
            target.append(warning)
