# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from typing import Any

from .config import PROMPTS_DIR
from .encoding_utils import read_text_auto


def read_prompt(name: str) -> str:
    return read_text_auto(PROMPTS_DIR / name)


DIRECTOR_LAYER_FILES = [
    "campaign_profile.json",
    "character_prompt.json",
    "campaign_direction.json",
    "npc_profiles.json",
    "monster_profiles.json",
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


def build_director_user_prompt(campaign_id: str, player_action: str, memory: dict[str, Any]) -> str:
    director_context = _pick(memory, DIRECTOR_LAYER_FILES)
    runtime_memory = _pick(memory, RUNTIME_MEMORY_FILES)
    return "\n\n".join(
        [
            f"campaign_id: {campaign_id}",
            "Model layer contract:",
            read_prompt("model_layer_contract_rules.md"),
            "Player action:",
            player_action,
            "V4 director-layer long-term context rules:",
            read_prompt("v4_campaign_context_prompt.md"),
            "```json\n" + json.dumps(director_context, ensure_ascii=False, indent=2) + "\n```",
            "Runtime memory for this turn:",
            "```json\n" + json.dumps(runtime_memory, ensure_ascii=False, indent=2) + "\n```",
            "Based on long-term records and runtime memory, output only strict JSON for the scene pressure pack and macro director decisions. Do not write player-readable prose. Do not expand into a full plot outline.",
        ]
    )


def build_chatgpt_input(
    campaign_id: str,
    player_action: str,
    memory: dict[str, Any],
    pressure_pack: dict[str, Any],
) -> str:
    layer_contract = read_prompt("model_layer_contract_rules.md")
    host_rules = read_prompt("chatgpt_host_prompt.md")
    actor_rules = "\n\n".join(
        [
            read_prompt("chatgpt_style_rules.md"),
            read_prompt("chatgpt_image_rules.md"),
            read_prompt("chatgpt_npc_voice_rules.md"),
            read_prompt("chatgpt_monster_rules.md"),
            read_prompt("character_card_json_rules.md"),
        ]
    )
    visible_memory = _pick(memory, CHATGPT_VISIBLE_FILES)
    return "\n\n".join(
        [
            "# ChatGPT TRPG Turn Input",
            "## Your Role",
            "You are the actor-layer prose host. V4 is the director. Codex is the local script supervisor and QA layer. Do not take director-layer authority.",
            "## Model Layer Contract",
            layer_contract,
            "## Fixed Output Rules",
            host_rules,
            "## Actor-Layer Detail Rules",
            actor_rules,
            "## campaign_id",
            campaign_id,
            "## Player Action",
            player_action,
            "## Visible Memory For This Turn",
            "These records are only for performance consistency. Do not expand unconfirmed content. Do not invent long-term setting.",
            "```json\n" + json.dumps(visible_memory, ensure_ascii=False, indent=2) + "\n```",
            "## DeepSeek V4 Scene Pressure Pack",
            "The V4 pressure pack is this turn's director instruction. Follow its pressure, boundaries, NPC direction, forbidden items, and choice requirements. Do not copy its structure directly.",
            "```json\n" + json.dumps(pressure_pack, ensure_ascii=False, indent=2) + "\n```",
            "Output strict JSON only: blocks, summary, and state_writeback. No text outside JSON.",
        ]
    )


def build_audit_user_prompt(
    campaign_id: str,
    memory: dict[str, Any],
    pressure_pack: dict[str, Any],
    writeback: dict[str, Any],
) -> str:
    audit_memory = {
        "director_layer": _pick(memory, DIRECTOR_LAYER_FILES),
        "runtime_memory": _pick(memory, RUNTIME_MEMORY_FILES),
        "style_layer": _pick(memory, ["style_profile.json", "image_profile.json"]),
    }
    return "\n\n".join(
        [
            f"campaign_id: {campaign_id}",
            "Local memory JSON:",
            json.dumps(audit_memory, ensure_ascii=False, indent=2),
            "This turn's pressure pack JSON:",
            json.dumps(pressure_pack, ensure_ascii=False, indent=2),
            "ChatGPT state writeback JSON:",
            json.dumps(writeback, ensure_ascii=False, indent=2),
        ]
    )
