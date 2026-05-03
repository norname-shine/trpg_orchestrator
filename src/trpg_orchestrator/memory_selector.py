# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy
from typing import Any


DIRECTOR_BASE = [
    "campaign_profile.json",
    "campaign_direction.json",
    "recent_context.json",
    "forbidden_changes.json",
    "story_progress.json",
    "story_blueprint.json",
    "main_threads.json",
]

ACTOR_BASE = [
    "campaign_profile.json",
    "style_profile.json",
    "recent_context.json",
    "player_state.json",
    "forbidden_changes.json",
]

AUDIT_BASE = [
    "campaign_profile.json",
    "campaign_direction.json",
    "recent_context.json",
    "forbidden_changes.json",
    "story_progress.json",
    "story_blueprint.json",
    "main_threads.json",
    "player_state.json",
    "npc_profiles.json",
    "npc_memory.json",
    "monster_profiles.json",
    "enemy_or_monster_ecology.json",
    "clue_history.json",
    "equipment_history.json",
]


def select_memory_for_director(memory: dict[str, Any], capability_plan: dict[str, Any]) -> dict[str, Any]:
    capabilities = _capabilities(capability_plan)
    names = list(DIRECTOR_BASE)
    if _has_any(capabilities, {"npc_present", "npc_voice", "dialogue_expected", "social"}):
        names.extend(["npc_profiles.json", "npc_memory.json"])
    if _has_any(capabilities, {"monster_present", "enemy_or_mystery", "monster_combat", "mystery_pressure"}):
        names.extend(["monster_profiles.json", "enemy_or_monster_ecology.json"])
    if _has_any(capabilities, {"map", "user_requested_map", "location_changed", "route_split"}):
        names.extend(["map_history.json", "location_history.json"])
    if _has_any(capabilities, {"inventory", "equipment_changed", "item_used", "item_gained", "item_lost"}):
        names.append("equipment_history.json")
    if _has_any(capabilities, {"dossier", "clue_found", "document_found", "investigation"}):
        names.extend(["clue_history.json", "main_threads.json"])
    selected = _pick(memory, names)
    _record_refs(capability_plan, "director", selected)
    return selected


def select_memory_for_actor(memory: dict[str, Any], capability_plan: dict[str, Any], pressure_pack: dict[str, Any]) -> dict[str, Any]:
    capabilities = _capabilities(capability_plan)
    names = list(ACTOR_BASE)
    if _has_any(capabilities, {"npc_present", "npc_voice", "dialogue_expected", "social"}):
        names.append("npc_memory.json")
    if _has_any(capabilities, {"monster_present", "enemy_or_mystery", "monster_combat", "mystery_pressure"}):
        names.append("enemy_or_monster_ecology.json")
    if _has_any(capabilities, {"map", "user_requested_map", "location_changed", "route_split"}):
        names.append("location_history.json")
    if _has_any(capabilities, {"inventory", "equipment_changed", "item_used", "item_gained", "item_lost"}):
        names.append("equipment_history.json")
    if _has_any(capabilities, {"dossier", "clue_found", "document_found", "investigation"}):
        names.append("clue_history.json")
    selected = _sanitize_actor_memory(_pick(memory, names))
    selected["actor_visible_story_progress"] = _actor_visible_story_progress(pressure_pack)
    _record_refs(capability_plan, "actor_visible", selected)
    return selected


def select_memory_for_audit(
    memory: dict[str, Any],
    capability_plan: dict[str, Any],
    writeback: dict[str, Any],
    pressure_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    capabilities = _capabilities(capability_plan)
    names = list(AUDIT_BASE)
    if _has_any(capabilities, {"map", "user_requested_map"}):
        names.extend(["map_history.json", "location_history.json"])
    if _has_any(capabilities, {"visual_assets"}):
        names.append("image_profile.json")
    selected = _pick(memory, names)
    _record_refs(capability_plan, "audit", selected)
    return selected


def _actor_visible_story_progress(pressure_pack: dict[str, Any]) -> dict[str, Any]:
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


def _pick(memory: dict[str, Any], filenames: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in filenames:
        if name not in result:
            result[name] = deepcopy(memory.get(name, {}))
    return result


def _capabilities(capability_plan: dict[str, Any]) -> set[str]:
    if not isinstance(capability_plan, dict):
        return set()
    loaded = capability_plan.get("loaded_capabilities", [])
    return set(loaded if isinstance(loaded, list) else [])


def _has_any(capabilities: set[str], candidates: set[str]) -> bool:
    return bool(capabilities.intersection(candidates))


def _record_refs(capability_plan: dict[str, Any], layer: str, selected: dict[str, Any]) -> None:
    if not isinstance(capability_plan, dict):
        return
    refs = capability_plan.setdefault("memory_refs", {"director": [], "actor_visible": [], "audit": []})
    if isinstance(refs, dict):
        refs[layer] = sorted(selected.keys())


def _sanitize_actor_memory(data: Any) -> Any:
    hidden_keys = {
        "story_blueprint.json",
        "story_progress.json",
        "npc_profiles.json",
        "monster_profiles.json",
        "main_threads.json",
        "secrets_not_to_reveal",
        "forbidden_reveals",
        "future_nodes",
        "hidden_truth",
        "hidden_motive",
        "hidden_motives",
        "director_notes",
        "npc_knowledge_boundaries",
    }
    if isinstance(data, dict):
        clean: dict[str, Any] = {}
        for key, value in data.items():
            if key in hidden_keys:
                continue
            lowered = str(key).lower()
            if any(token in lowered for token in ("hidden", "secret", "director_note", "future_node", "forbidden_reveal")):
                continue
            clean[key] = _sanitize_actor_memory(value)
        return clean
    if isinstance(data, list):
        return [_sanitize_actor_memory(item) for item in data]
    return data
