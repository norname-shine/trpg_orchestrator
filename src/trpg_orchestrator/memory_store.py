# -*- coding: gbk -*-
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import CAMPAIGNS_DIR, MEMORY_FILE_NAMES, REGISTRY_PATH, CampaignPaths
from .json_utils import read_json, write_json


def utc_stamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def default_memory(campaign_id: str, name: str = "") -> dict[str, Any]:
    return {
        "campaign_profile.json": {
            "campaign_id": campaign_id,
            "title": name or campaign_id,
            "genre": "",
            "tone": "",
            "world_rules": [],
            "narration_rules": [],
            "mechanics": {
                "use_dice": False,
                "dice_system": "",
                "use_combat_rules": False,
                "stats_style": "light",
            },
            "chatgpt_conversation_binding": {
                "project_name": "",
                "conversation_name": "",
            },
            "hard_limits": [],
        },
        "character_prompt.json": {
            "campaign_id": campaign_id,
            "purpose": "Long-term player character prompt for V4 director context.",
            "confirmed_identity": {},
            "confirmed_background": [],
            "personality_and_voice": [],
            "abilities_and_limits": [],
            "growth_direction": [],
            "unknown_or_player_owned": [],
        },
        "campaign_direction.json": {
            "campaign_id": campaign_id,
            "purpose": "Long-term campaign direction prompt for V4 director context.",
            "background_direction": [],
            "main_tension": [],
            "theme_and_tone": [],
            "main_threads_direction": [],
            "side_threads_direction": [],
            "pace_rules": [],
            "do_not_force_every_turn": [],
        },
        "npc_profiles.json": {
            "campaign_id": campaign_id,
            "purpose": "Long-term NPC personality and motive prompt for V4 director context.",
            "profiles": {},
            "voice_rules": {},
            "relationship_rules": {},
        },
        "monster_profiles.json": {
            "campaign_id": campaign_id,
            "purpose": "Long-term enemy, monster, mystery, and ecology prompt for V4 director context.",
            "profiles": {},
            "ecology_rules": [],
            "reveal_rules": [],
            "misdirection_rules": [],
        },
        "style_profile.json": {
            "campaign_id": campaign_id,
            "purpose": "Campaign-specific prose, immersion, localization, and anti-AI style prompt.",
            "prose_style": [],
            "immersion_rules": [],
            "dialogue_rules": [],
            "localization_rules": [],
            "avoid_patterns": [],
        },
        "image_profile.json": {
            "campaign_id": campaign_id,
            "purpose": "Optional image generation and visual-description rules. Do not trigger image generation unless requested.",
            "visual_direction": [],
            "image_generation_rules": [],
            "do_not_generate": [],
        },
        "player_state.json": base_memory(campaign_id, "player"),
        "npc_memory.json": base_memory(campaign_id, "npcs"),
        "world_state.json": base_memory(campaign_id, "world"),
        "location_history.json": base_memory(campaign_id, "locations"),
        "quest_history.json": base_memory(campaign_id, "quests"),
        "enemy_or_monster_ecology.json": base_memory(campaign_id, "enemy_or_mystery"),
        "equipment_history.json": base_memory(campaign_id, "equipment"),
        "main_threads.json": {
            "campaign_id": campaign_id,
            "last_updated_turn": 0,
            "main_threads": [],
            "side_threads": [],
            "closed_threads": [],
            "uncertain_or_unconfirmed": [],
        },
        "recent_context.json": {
            "campaign_id": campaign_id,
            "turn_index": 0,
            "recent_summary": [],
            "current_scene": {
                "time": "",
                "location": "",
                "active_npcs": [],
                "immediate_pressure": "",
            },
            "last_player_action": "",
            "last_outcome": "",
        },
        "forbidden_changes.json": {
            "campaign_id": campaign_id,
            "global_forbidden": [],
            "campaign_specific_forbidden": [],
            "secrets_not_to_reveal": [],
            "npc_knowledge_boundaries": {},
            "unconfirmed_should_not_be_written_as_fact": [],
        },
    }


def base_memory(campaign_id: str, scope: str) -> dict[str, Any]:
    return {
        "campaign_id": campaign_id,
        "scope": scope,
        "last_updated_turn": 0,
        "facts": [],
        "uncertain_or_unconfirmed": [],
        "notes": [],
    }


class MemoryStore:
    def load_registry(self) -> dict[str, Any]:
        if not REGISTRY_PATH.exists():
            return {"active_campaign": "", "campaigns": {}}
        return read_json(REGISTRY_PATH)

    def save_registry(self, registry: dict[str, Any]) -> None:
        write_json(REGISTRY_PATH, registry)

    def resolve_campaign_id(self, campaign_id: str | None = None) -> str:
        if campaign_id:
            return campaign_id
        registry = self.load_registry()
        active = registry.get("active_campaign")
        if not active:
            raise RuntimeError("找不到 active_campaign，请先指定或初始化一个 campaign_id。")
        return active

    def init_campaign(self, campaign_id: str, name: str) -> CampaignPaths:
        paths = CampaignPaths.from_id(campaign_id)
        paths.logs.mkdir(parents=True, exist_ok=True)
        paths.backups.mkdir(parents=True, exist_ok=True)
        for filename, content in default_memory(campaign_id, name).items():
            path = paths.root / filename
            if not path.exists():
                write_json(path, content)

        registry = self.load_registry()
        registry.setdefault("campaigns", {})
        registry["active_campaign"] = registry.get("active_campaign") or campaign_id
        registry["campaigns"][campaign_id] = {
            "name": name,
            "chatgpt_project_name": "",
            "chatgpt_conversation_name": "",
            "status": "active",
            "created_at": registry.get("campaigns", {}).get(campaign_id, {}).get("created_at") or utc_stamp(),
            "updated_at": utc_stamp(),
        }
        self.save_registry(registry)
        return paths

    def load_campaign_memory(self, campaign_id: str) -> dict[str, Any]:
        paths = CampaignPaths.from_id(campaign_id)
        missing = [name for name in MEMORY_FILE_NAMES if not (paths.root / name).exists()]
        if missing:
            raise FileNotFoundError(f"跑团记忆文件缺失: {', '.join(missing)}")
        return {name: read_json(paths.root / name) for name in MEMORY_FILE_NAMES}

    def backup_files(self, campaign_id: str, filenames: list[str]) -> Path:
        paths = CampaignPaths.from_id(campaign_id)
        backup_dir = paths.backups / utc_stamp()
        backup_dir.mkdir(parents=True, exist_ok=True)
        for filename in filenames:
            source = paths.root / filename
            if source.exists():
                shutil.copy2(source, backup_dir / filename)
        return backup_dir

    def write_memory_updates(self, campaign_id: str, updates: dict[str, Any]) -> list[str]:
        touched: list[str] = []
        paths = CampaignPaths.from_id(campaign_id)
        for filename, content in updates.items():
            if filename not in MEMORY_FILE_NAMES:
                continue
            write_json(paths.root / filename, content)
            touched.append(filename)
        return touched

    def update_chatgpt_binding(self, campaign_id: str, project_name: str, conversation_name: str) -> None:
        paths = CampaignPaths.from_id(campaign_id)
        profile_path = paths.root / "campaign_profile.json"
        profile = read_json(profile_path)
        profile.setdefault("chatgpt_conversation_binding", {})
        profile["chatgpt_conversation_binding"]["project_name"] = project_name
        profile["chatgpt_conversation_binding"]["conversation_name"] = conversation_name
        write_json(profile_path, profile)

        registry = self.load_registry()
        registry.setdefault("campaigns", {})
        registry.setdefault("campaigns", {}).setdefault(campaign_id, {})
        registry["campaigns"][campaign_id]["chatgpt_project_name"] = project_name
        registry["campaigns"][campaign_id]["chatgpt_conversation_name"] = conversation_name
        registry["campaigns"][campaign_id]["updated_at"] = utc_stamp()
        self.save_registry(registry)

    def write_log(self, campaign_id: str, payload: dict[str, Any]) -> Path:
        paths = CampaignPaths.from_id(campaign_id)
        path = paths.logs / f"{utc_stamp()}_turn.json"
        write_json(path, payload)
        return path

    def campaign_root(self, campaign_id: str) -> Path:
        return CAMPAIGNS_DIR / campaign_id
