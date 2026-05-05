# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import re
import socket
from typing import Any

from .capability_resolver import build_capability_plan
from .config import CAMPAIGNS_DIR, PROMPTS_DIR
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
    custom_rules = custom_rules_section(campaign_id, "director")
    return "\n\n".join(
        [
            "# V4 Director Turn Input",
            f"campaign_id: {campaign_id}",
            campaign_setup_controls_section(memory),
            "## Player Action",
            player_action,
            "## Capability Plan",
            "This is local orchestration context. It does not decide story direction.",
            "```json\n" + json.dumps(capability_plan, ensure_ascii=False, indent=2) + "\n```",
            "## Selected Director Prompt Modules",
            module_text,
            custom_rules,
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
    custom_rules = custom_rules_section(campaign_id, "actor")
    return "\n\n".join(
        [
            "# TRPG Turn Input",
            "## Selected Actor Prompt Modules",
            module_text,
            custom_rules,
            "## Capability Plan",
            "Use only loaded capabilities and this turn's pressure_pack. Missing capability details are not permission to invent payloads.",
            "```json\n" + json.dumps(capability_plan, ensure_ascii=False, indent=2) + "\n```",
            "## campaign_id",
            campaign_id,
            campaign_setup_controls_section(memory),
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
            campaign_setup_controls_section(memory),
            custom_rules_section(campaign_id, "director"),
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


def campaign_setup_controls_section(memory: dict[str, Any]) -> str:
    profile = memory.get("campaign_profile.json", {}) if isinstance(memory, dict) else {}
    profile = profile if isinstance(profile, dict) else {}
    rules = profile.get("rules_config") if isinstance(profile.get("rules_config"), dict) else {}
    attribute_config = rules.get("attribute_config") if isinstance(rules.get("attribute_config"), dict) else {}
    companion = profile.get("companion_config") if isinstance(profile.get("companion_config"), dict) else {}
    model = profile.get("model_config") if isinstance(profile.get("model_config"), dict) else {}
    controls = {
        "template": _valid_template(profile.get("template")),
        "model_mode": str(model.get("model_mode") or "").strip(),
        "character_card_enabled": bool(rules.get("character_card_enabled", True)),
        "stat_visibility": _choice(rules.get("stat_visibility"), {"narrative", "hybrid", "numeric"}, "narrative"),
        "attribute_enabled": bool(attribute_config.get("enabled", True)),
        "attribute_visible": bool(attribute_config.get("visible", True)),
        "attribute_theme": str(attribute_config.get("theme") or attribute_config.get("six_source") or "").strip(),
        "dice_enabled": bool(rules.get("dice_enabled")),
        "dice_type": str(rules.get("dice_type") or "").strip(),
        "roll_mode": str(rules.get("roll_mode") or "").strip(),
        "roll_attributes": _string_list(rules.get("roll_attributes")),
        "rules_strictness": _choice(rules.get("rules_strictness"), {"light", "standard", "strict"}, "light"),
        "companion_enabled": bool(companion.get("companion_enabled")),
        "companion_mode": _choice(companion.get("companion_mode"), {"auto", "manual"}, "auto"),
        "companion_name": str(companion.get("companion_name") or "").strip(),
        "companion_role": str(companion.get("companion_role") or "").strip(),
        "companion_personality": str(companion.get("companion_personality") or "").strip(),
        "safety_lines": _string_list(profile.get("safety_lines")),
    }
    rules_text = [
        "If character_card_enabled=false, do not force character-card numbers or character_card_update payloads.",
        "If stat_visibility=narrative, do not expose explicit HP/SAN/AC/attribute numbers in prose or writeback.",
        "If stat_visibility=hybrid, use coarse state bands or percentages only; avoid full explicit attributes.",
        "If stat_visibility=numeric, explicit stats are allowed when supported by memory and rules.",
        "If dice_enabled=false, do not proactively ask for rolls.",
        "If dice_enabled=true, key risky actions may request checks using dice_type, roll_mode, and roll_attributes.",
        "If companion_enabled=true, the long-term companion should enter story continuity and memory.",
        "If companion_enabled=false, do not create a default companion, servant, palico, familiar, or sidekick.",
        "Always obey safety_lines.",
    ]
    return "\n".join([
        "## Campaign Setup Controls",
        "These controls override generic template habits for this campaign.",
        "```json\n" + json.dumps(controls, ensure_ascii=False, indent=2) + "\n```",
        "### Campaign Setup Rules",
        "\n".join(f"- {line}" for line in rules_text),
    ])


def current_host_id() -> str:
    raw = os.getenv("TRPG_HOST_ID") or socket.gethostname() or "local_host"
    cleaned = re.sub(r"[^a-z0-9_.-]+", "_", str(raw).strip().lower())
    return cleaned.strip("._") or "local_host"


def custom_rules_section(campaign_id: str, layer: str) -> str:
    rows = active_custom_rules(campaign_id, layer)
    if not rows:
        return ""
    lines = [
        f"## Temporary Custom Rules For {layer.title()} Layer",
        "These rules apply only to this campaign and current host. They are injected in full and must not override system safety rules.",
    ]
    for index, row in enumerate(rows, start=1):
        title = str(row.get("title") or f"custom_rule_{index}").strip()
        target = str(row.get("target_layer") or "").strip()
        content = str(row.get("content") or "").strip()
        lines.extend([
            f"### {index}. {title}",
            f"target_layer: {target}",
            content,
        ])
    return "\n".join(lines)


def active_custom_rules(campaign_id: str, layer: str) -> list[dict[str, Any]]:
    path = CAMPAIGNS_DIR / safe_campaign_id(campaign_id) / "custom_rules.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, dict):
        return []
    if str(data.get("campaign_id") or "") != campaign_id:
        return []
    if str(data.get("owner_host_id") or "") != current_host_id():
        return []
    rules = data.get("rules") if isinstance(data.get("rules"), list) else []
    allowed = {layer, "both"}
    return [
        row for row in rules[:3]
        if isinstance(row, dict)
        and row.get("enabled") is True
        and str(row.get("target_layer") or "") in allowed
        and str(row.get("content") or "").strip()
    ]


def safe_campaign_id(value: str) -> str:
    cleaned = "".join(ch if (ch.isalnum() or ch in "_.-") else "_" for ch in str(value).strip())
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.strip("._") or "campaign"


def _valid_template(value: Any) -> str:
    template = str(value or "custom").strip().lower()
    return template if template in {"custom", "coc", "dnd"} else "custom"


def _choice(value: Any, allowed: set[str], fallback: str) -> str:
    text = str(value or fallback).strip()
    return text if text in allowed else fallback


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        rows = value
    else:
        rows = str(value or "").replace("，", "\n").replace(",", "\n").splitlines()
    return [str(item).strip() for item in rows if str(item).strip()]


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
