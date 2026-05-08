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
    path = PROMPTS_DIR / name
    if path.exists():
        return read_runtime_text(path)
    matches = sorted(PROMPTS_DIR.rglob(name))
    if matches:
        return read_runtime_text(matches[0])
    return read_runtime_text(path)


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


MODEL_INPUT_OMIT_KEYS = {
    "model_config",
    "model_mode",
    "model_slots",
    "director_model",
    "actor_model",
    "single_model",
    "custom_api_key_received",
    "api_key",
    "api_key_ref",
    "ai_mode",
}

ACTOR_BACKEND_OMIT_KEYS = {
    "asset_key",
    "asset_seed",
    "audit",
    "cached_url",
    "cache_policy",
    "canvas",
    "canvas_spec",
    "canvas_style",
    "coordinates",
    "created_at",
    "debug",
    "diagnostics",
    "display_zone",
    "edges",
    "generator_version",
    "icon_rules",
    "image_prompt",
    "legend",
    "manifest",
    "map_canvas",
    "map_route",
    "metadata",
    "missing_capabilities",
    "mode",
    "negative_prompt",
    "output_requests",
    "payload_fulfillment",
    "payload_patch",
    "payloads",
    "points",
    "positive_prompt",
    "prompt_modules",
    "protocol_warnings",
    "public_think",
    "quality",
    "reason",
    "routes",
    "source_object_id",
    "style_preset",
    "trigger",
    "trigger_image_generation",
    "visual_assets",
    "visual_prompt",
    "warnings",
}

ACTOR_BACKEND_KEY_TOKENS = (
    "cache",
    "canvas",
    "debug",
    "diagnostic",
    "manifest",
    "payload_fulfillment",
    "source_object",
)

ACTOR_SCENE_KEYS = {
    "turn_type",
    "current_situation",
    "player_pressure_point",
    "npc_direction",
    "scene_boundaries",
    "forbidden_items",
    "required_choices",
    "choice_requirements",
    "state_update_hints",
    "current_scene",
    "consequences",
    "risks",
    "summary",
}

ACTOR_VISIBLE_CAPABILITY_PREFIXES = (
    "base_actor",
    "character",
    "choice",
    "clue",
    "dialogue",
    "dice",
    "dossier",
    "equipment",
    "inventory",
    "item",
    "location",
    "map",
    "npc",
    "recent_context",
    "story_progress",
)

ACTOR_WRITEBACK_TARGET_LABELS = {
    "story_progress": "story progress evidence for review",
    "inventory": "inventory evidence for review",
    "character_card": "character status evidence for review",
    "dossier": "clue or dossier evidence for review",
    "dice/check": "dice/check handling when allowed",
    "dice_or_check": "dice/check handling when allowed",
}

ACTOR_IMAGE_OMIT_KEYS = {
    "audit",
    "debug",
    "diagnostics",
    "generator_version",
    "manifest",
    "metadata",
    "mode",
    "output_requests",
    "payload_fulfillment",
    "payload_patch",
    "payloads",
    "protocol_warnings",
    "public_think",
    "reason",
    "source_object_id",
    "trigger",
    "trigger_image_generation",
    "warnings",
}


def sanitize_model_input(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if str(key) in MODEL_INPUT_OMIT_KEYS:
                continue
            if str(key) == "setup_controls" and isinstance(item, list):
                item = [row for row in item if "model" not in str(row).lower()]
            cleaned[key] = sanitize_model_input(item)
        return cleaned
    if isinstance(value, list):
        return [sanitize_model_input(item) for item in value]
    if isinstance(value, str):
        return sanitize_model_terms(value)
    return value


def sanitize_model_terms(text: str) -> str:
    replacements = {
        "DeepSeek V4": "导演层",
        "deepseek_v4": "director",
        "V4": "导演层",
        "ChatGPT": "演员层",
        "chatgpt": "actor",
        "GPT": "演员层",
        "Codex": "本地后台",
        "CODEX": "本地后台",
    }
    result = str(text)
    for old, new in replacements.items():
        result = result.replace(old, new)
    result = re.sub(r"(?im)^.*model_(?:mode|slots)=[^\n]*\n?", "", result)
    result = re.sub(r"(?im)^.*(?:director_model|actor_model|single_model)[^\n]*\n?", "", result)
    return result


def sanitize_actor_prompt_value(value: Any) -> Any:
    cleaned = _actor_clean_value(sanitize_model_input(value))
    return cleaned if cleaned is not None else {}


def build_actor_capability_view(capability_plan: dict[str, Any]) -> dict[str, Any]:
    loaded = capability_plan.get("loaded_capabilities", []) if isinstance(capability_plan, dict) else []
    capabilities = []
    for capability in loaded if isinstance(loaded, list) else []:
        text = str(capability or "").strip()
        if text.endswith("_preload"):
            continue
        if text and text.startswith(ACTOR_VISIBLE_CAPABILITY_PREFIXES):
            capabilities.append(text)
    return sanitize_actor_prompt_value({
        "visible_capabilities": capabilities,
        "contract": "Use only these visible story tools for this turn.",
    })


def build_actor_scene_control(pressure_pack: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(pressure_pack, dict):
        return {}
    scene = {key: pressure_pack.get(key) for key in ACTOR_SCENE_KEYS if key in pressure_pack}
    if "pressure_pack" in pressure_pack:
        scene["scene_pressure"] = pressure_pack.get("pressure_pack")
    output_requests = pressure_pack.get("output_requests") if isinstance(pressure_pack.get("output_requests"), dict) else {}
    writeback_targets: list[str] = []
    for name, request in output_requests.items():
        if not isinstance(request, dict):
            continue
        mode = str(request.get("mode") or "").strip()
        label = ACTOR_WRITEBACK_TARGET_LABELS.get(str(name))
        if mode and mode != "none" and label:
            writeback_targets.append(label)
    if writeback_targets:
        scene["allowed_state_updates"] = sorted(set(writeback_targets))
    payloads = pressure_pack.get("payloads") if isinstance(pressure_pack.get("payloads"), dict) else {}
    for key in ("state_update_hints", "npc_direction", "choice_requirements", "required_choices"):
        if key not in scene and key in payloads:
            scene[key] = payloads.get(key)
    return sanitize_actor_prompt_value(scene)


def sanitize_actor_image_asset(value: Any) -> Any:
    cleaned = _actor_image_clean_value(sanitize_model_input(value))
    return cleaned if cleaned is not None else {}


def _actor_image_clean_value(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            if lowered in ACTOR_IMAGE_OMIT_KEYS:
                continue
            if lowered.endswith("_mode"):
                continue
            cleaned = _actor_image_clean_value(item)
            if _actor_is_empty(cleaned):
                continue
            clean[key_text] = cleaned
        return clean or None
    if isinstance(value, list):
        rows = [_actor_image_clean_value(item) for item in value]
        rows = [item for item in rows if not _actor_is_empty(item)]
        return rows or None
    if isinstance(value, str):
        text = sanitize_model_terms(value).strip()
        return text or None
    return value


def _actor_clean_value(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        seen_values: set[str] = set()
        for key, item in value.items():
            key_text = str(key)
            if _actor_should_prune_key(key_text):
                continue
            cleaned = _actor_clean_value(item)
            if _actor_is_empty(cleaned):
                continue
            signature = _stable_compact_json(cleaned)
            if signature in seen_values:
                continue
            seen_values.add(signature)
            clean[key_text] = cleaned
        return clean or None
    if isinstance(value, list):
        rows = []
        seen_items: set[str] = set()
        for item in value:
            cleaned = _actor_clean_value(item)
            if _actor_is_empty(cleaned):
                continue
            signature = _stable_compact_json(cleaned)
            if signature in seen_items:
                continue
            seen_items.add(signature)
            rows.append(cleaned)
        return rows or None
    if isinstance(value, str):
        text = sanitize_model_terms(value).strip()
        return text or None
    return value


def _actor_should_prune_key(key: str) -> bool:
    lowered = key.lower()
    if lowered in ACTOR_BACKEND_OMIT_KEYS:
        return True
    if lowered.endswith("_mode"):
        return True
    return any(token in lowered for token in ACTOR_BACKEND_KEY_TOKENS)


def _actor_is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _stable_compact_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except TypeError:
        return str(value)


def current_story_anchor(memory: dict[str, Any]) -> dict[str, Any]:
    blueprint = memory.get("story_blueprint.json", {}) if isinstance(memory, dict) else {}
    progress = memory.get("story_progress.json", {}) if isinstance(memory, dict) else {}
    chapters = blueprint.get("chapters") if isinstance(blueprint, dict) and isinstance(blueprint.get("chapters"), list) else []
    current_node_id = str(progress.get("current_node_id") or "") if isinstance(progress, dict) else ""
    current_chapter_id = str(progress.get("current_chapter_id") or "") if isinstance(progress, dict) else ""
    current_chapter: dict[str, Any] = {}
    current_node: dict[str, Any] = {}
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        nodes = chapter.get("nodes") if isinstance(chapter.get("nodes"), list) else []
        if current_chapter_id and str(chapter.get("chapter_id") or "") == current_chapter_id:
            current_chapter = chapter
        for node in nodes:
            if isinstance(node, dict) and current_node_id and str(node.get("node_id") or "") == current_node_id:
                current_node = node
                current_chapter = current_chapter or chapter
                break
        if current_node:
            break
    if not current_node:
        first_chapter = next((chapter for chapter in chapters if isinstance(chapter, dict) and isinstance(chapter.get("nodes"), list) and chapter.get("nodes")), {})
        current_chapter = first_chapter if isinstance(first_chapter, dict) else {}
        current_node = current_chapter.get("nodes", [{}])[0] if isinstance(current_chapter.get("nodes"), list) and current_chapter.get("nodes") else {}
    beats = current_node.get("beat_checklist") if isinstance(current_node.get("beat_checklist"), list) else []
    next_nodes = current_node.get("next_nodes") if isinstance(current_node.get("next_nodes"), list) else []
    return sanitize_model_input({
        "current_chapter_id": current_chapter.get("chapter_id", ""),
        "current_chapter_name": current_chapter.get("title") or current_chapter.get("name") or "",
        "current_node_id": current_node.get("node_id", ""),
        "current_node_name": current_node.get("title") or current_node.get("name") or "",
        "node_goal": current_node.get("goal") or current_node.get("summary") or "",
        "beat_targets_this_turn": [str((beats[0] if isinstance(beats[0], dict) else {}).get("beat_id") or "")] if beats else [],
        "legal_next_nodes": [str(item) for item in next_nodes if str(item)],
        "pace_command": str((progress if isinstance(progress, dict) else {}).get("pace_command") or "normal"),
    })


def build_director_user_prompt(
    campaign_id: str,
    player_action: str,
    memory: dict[str, Any],
    capability_plan: dict[str, Any] | None = None,
) -> str:
    capability_plan = capability_plan or build_capability_plan(campaign_id, player_action, memory)
    director_memory = sanitize_model_input(select_memory_for_director(memory, capability_plan))
    module_ids = select_prompt_modules(capability_plan, "director")
    module_text = sanitize_model_terms(load_prompt_modules(module_ids))
    _append_module_warnings(capability_plan)
    custom_rules = custom_rules_section(campaign_id, "director")
    return "\n\n".join(
        [
            "# Director Turn Input",
            f"campaign_id: {campaign_id}",
            campaign_setup_controls_section(memory),
            "## Player Action",
            player_action,
            "## Current Story Anchor",
            "Use this anchor for progress_control when it is non-empty.",
            "```json\n" + json.dumps(current_story_anchor(memory), ensure_ascii=False, indent=2) + "\n```",
            "## Capability Plan",
            "This is local orchestration context. It does not decide story direction.",
            "```json\n" + json.dumps(sanitize_model_input(capability_plan), ensure_ascii=False, indent=2) + "\n```",
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
    visible_memory = sanitize_actor_prompt_value(select_memory_for_actor(memory, capability_plan, pressure_pack))
    visible_story_progress = visible_memory.get("actor_visible_story_progress", build_actor_visible_story_progress(memory, pressure_pack))
    actor_capability_view = build_actor_capability_view(capability_plan)
    actor_scene_control = build_actor_scene_control(pressure_pack)
    module_ids = select_prompt_modules(capability_plan, "actor", pressure_pack)
    module_text = sanitize_model_terms(load_prompt_modules(module_ids))
    _append_module_warnings(capability_plan)
    custom_rules = custom_rules_section(campaign_id, "actor")
    return "\n\n".join(
        [
            "# TRPG Turn Input",
            "## Selected Actor Prompt Modules",
            module_text,
            custom_rules,
            "## Available Story Tools",
            "Use only these visible story tools for this turn.",
            "```json\n" + json.dumps(actor_capability_view, ensure_ascii=False, indent=2) + "\n```",
            "## campaign_id",
            campaign_id,
            campaign_setup_controls_section(memory),
            "## Player Action",
            player_action,
            "## Visible Memory For This Turn",
            "These records are only for performance consistency. Do not expand unconfirmed content. Do not invent long-term setting.",
            "```json\n" + json.dumps(visible_memory, ensure_ascii=False, indent=2) + "\n```",
            "## Current Story Position",
            "This is the visible current-node summary for this turn. It is not a full story blueprint.",
            "```json\n" + json.dumps(visible_story_progress, ensure_ascii=False, indent=2) + "\n```",
            "## Scene Brief For This Turn",
            "Follow this turn's visible pressure, boundaries, NPC direction, forbidden items, choice requirements, and allowed state updates.",
            "```json\n" + json.dumps(actor_scene_control, ensure_ascii=False, indent=2) + "\n```",
            "Output strict JSON only: turn_title, blocks, summary, and state_writeback. No text outside JSON.",
        ]
    )


def build_chatgpt_image_input(
    campaign_id: str,
    player_action: str,
    pressure_pack: dict[str, Any],
    visual_assets: list[dict[str, Any]],
) -> str:
    rows = [sanitize_actor_image_asset(row) for row in visual_assets[:1]] or [{
        "id": "requested_image",
        "title": "本回合关键画面",
        "positive_prompt": "Use the current visible TRPG scene brief to generate one coherent image. Keep only confirmed visible details.",
        "negative_prompt": "low quality, blurry, text artifacts, watermark, logo, extra limbs, malformed hands, incoherent layout",
        "aspect_ratio": "16:9",
        "style_preset": "cinematic anime urban horror, Fate-inspired, controlled lighting",
        "quality": {"steps": 30, "cfg_scale": 6.5, "sampler": "DPM++ 2M Karras", "size": "2304x2304"},
    }]
    image_asset = sanitize_actor_image_asset(rows[0])
    scene_context = build_actor_scene_control(pressure_pack)
    return "\n\n".join(
        [
            "# Actor Image Generation Pass",
            "This is a separate actor image-only pass. Do not continue the story and do not output state_writeback JSON.",
            "Generate exactly one image from the image instruction below.",
            "Do not include new plot facts. Do not reveal unknown canon details. Use only confirmed or visible scene details.",
            "Generate one 2304x2304 square image containing both a 16:9 horizontal panel and a 9:16 vertical panel for the same scene. Use original descriptive style language and avoid copyrighted names, trademarks, artist names, or directly imitative style labels.",
            f"campaign_id: {campaign_id}",
            "Player action for this image pass:",
            player_action,
            "Actor image instruction:",
            "```json\n" + json.dumps(image_asset, ensure_ascii=False, indent=2) + "\n```",
            "Visible scene brief for image context:",
            "```json\n" + json.dumps(scene_context, ensure_ascii=False, indent=2) + "\n```",
            "Generate one image now. No story prose, no choices, no state_writeback.",
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
    controls = {
        "template": _valid_template(profile.get("template")),
        "character_card_enabled": bool(rules.get("character_card_enabled", True)),
        "stat_visibility": _choice(rules.get("stat_visibility"), {"narrative", "hybrid", "numeric"}, "narrative"),
        "attribute_enabled": bool(attribute_config.get("enabled", True)),
        "attribute_visible": bool(attribute_config.get("visible", True)),
        "attribute_theme": str(attribute_config.get("theme") or attribute_config.get("six_source") or "").strip(),
        "dice_enabled": bool(rules.get("dice_enabled")),
        "dice_type": str(rules.get("dice_type") or "").strip(),
        "roll_style": str(rules.get("roll_mode") or "").strip(),
        "roll_attributes": _string_list(rules.get("roll_attributes")),
        "rules_strictness": _choice(rules.get("rules_strictness"), {"light", "standard", "strict"}, "light"),
        "companion_enabled": bool(companion.get("companion_enabled")),
        "companion_handling": _choice(companion.get("companion_mode"), {"auto", "manual"}, "auto"),
        "companion_name": str(companion.get("companion_name") or "").strip(),
        "companion_role": str(companion.get("companion_role") or "").strip(),
        "companion_personality": str(companion.get("companion_personality") or "").strip(),
        "safety_lines": _string_list(profile.get("safety_lines")),
    }
    rules_text = [
        "If character_card_enabled=false, do not force character-card numbers or character-card structured updates.",
        "If stat_visibility=narrative, do not expose explicit HP/SAN/AC/attribute numbers in prose or writeback.",
        "If stat_visibility=hybrid, use coarse state bands or percentages only; avoid full explicit attributes.",
        "If stat_visibility=numeric, explicit stats are allowed when supported by memory and rules.",
        "If dice_enabled=false, do not proactively ask for rolls.",
        "If dice_enabled=true, key risky actions may request checks using dice_type, roll_style, and roll_attributes.",
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
        data = json.loads(read_runtime_text(path))
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
