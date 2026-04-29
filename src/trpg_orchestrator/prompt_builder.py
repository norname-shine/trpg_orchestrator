# -*- coding: gbk -*-
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
            "玩家行动：",
            player_action,
            "V4 导演层长期资料：",
            read_prompt("v4_campaign_context_prompt.md"),
            "```json\n" + json.dumps(director_context, ensure_ascii=False, indent=2) + "\n```",
            "本回合运行记忆：",
            "```json\n" + json.dumps(runtime_memory, ensure_ascii=False, indent=2) + "\n```",
            "请根据长期资料和运行记忆，只输出严格 JSON 现场压力包。不要写正文，不要写剧情大纲。",
        ]
    )


def build_chatgpt_input(
    campaign_id: str,
    player_action: str,
    memory: dict[str, Any],
    pressure_pack: dict[str, Any],
) -> str:
    host_rules = read_prompt("chatgpt_host_prompt.md")
    actor_rules = "\n\n".join(
        [
            read_prompt("chatgpt_style_rules.md"),
            read_prompt("chatgpt_image_rules.md"),
            read_prompt("chatgpt_npc_voice_rules.md"),
            read_prompt("chatgpt_monster_rules.md"),
        ]
    )
    visible_memory = _pick(memory, CHATGPT_VISIBLE_FILES)
    return "\n\n".join(
        [
            "# ChatGPT TRPG 回合输入",
            "## 你的分工",
            "你是演员层正文主持。V4 是导演，Codex 是本地场记和质检。你不得抢导演层权限。",
            "## 固定输出规则",
            host_rules,
            "## 演员层细化规则",
            actor_rules,
            "## campaign_id",
            campaign_id,
            "## 玩家行动",
            player_action,
            "## 本回合可见记忆",
            "这些资料只用于维持表演一致性。不要扩写其中未确认内容，不要自行发明长期设定。",
            "```json\n" + json.dumps(visible_memory, ensure_ascii=False, indent=2) + "\n```",
            "## DeepSeek V4 现场压力包",
            "V4 压力包是本回合导演指令。必须服从其中的压力、边界、NPC 方向、禁止事项和选择要求。不要照搬结构。",
            "```json\n" + json.dumps(pressure_pack, ensure_ascii=False, indent=2) + "\n```",
            "请只输出规定格式的本回合正文、选择点、回合摘要和状态回写。",
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
            "本地记忆 JSON：",
            json.dumps(audit_memory, ensure_ascii=False, indent=2),
            "本回合压力包 JSON：",
            json.dumps(pressure_pack, ensure_ascii=False, indent=2),
            "ChatGPT 状态回写 JSON：",
            json.dumps(writeback, ensure_ascii=False, indent=2),
        ]
    )