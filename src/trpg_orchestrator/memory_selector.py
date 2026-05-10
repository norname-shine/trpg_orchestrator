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


def build_director_memory_digest(memory: dict[str, Any], capability_plan: dict[str, Any]) -> dict[str, Any]:
    profile = memory.get("campaign_profile.json", {})
    direction = memory.get("campaign_direction.json", {})
    recent = memory.get("recent_context.json", {})
    forbidden = memory.get("forbidden_changes.json", {})
    progress = memory.get("story_progress.json", {})
    blueprint = memory.get("story_blueprint.json", {})
    threads = memory.get("main_threads.json", {})
    if not isinstance(profile, dict):
        profile = {}
    if not isinstance(direction, dict):
        direction = {}
    if not isinstance(recent, dict):
        recent = {}
    if not isinstance(forbidden, dict):
        forbidden = {}
    if not isinstance(progress, dict):
        progress = {}
    if not isinstance(blueprint, dict):
        blueprint = {}
    if not isinstance(threads, dict):
        threads = {}

    digest = {
        "campaign_brief": _campaign_brief(profile, direction),
        "current_story_anchor": _current_story_anchor(progress),
        "current_runtime": _current_runtime(recent),
        "player_brief": _player_brief(profile),
        "companion_brief": _companion_brief(profile),
        "node_brief": _node_brief(progress, blueprint),
        "thread_brief": _thread_brief(threads, capability_plan),
        "asset_refs": _asset_refs(profile, capability_plan),
        "forbidden_brief": _forbidden_brief(profile, direction, forbidden),
    }
    return _compact_digest(digest)


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


def build_actor_memory_digest(
    memory: dict[str, Any],
    capability_plan: dict[str, Any],
    pressure_pack: dict[str, Any],
) -> dict[str, Any]:
    profile = memory.get("campaign_profile.json", {})
    style = memory.get("style_profile.json", {})
    recent = memory.get("recent_context.json", {})
    player_state = memory.get("player_state.json", {})
    forbidden = memory.get("forbidden_changes.json", {})
    npc_memory = memory.get("npc_memory.json", {})
    equipment = memory.get("equipment_history.json", {})
    if not isinstance(profile, dict):
        profile = {}
    if not isinstance(style, dict):
        style = {}
    if not isinstance(recent, dict):
        recent = {}
    if not isinstance(player_state, dict):
        player_state = {}
    if not isinstance(forbidden, dict):
        forbidden = {}
    if not isinstance(npc_memory, dict):
        npc_memory = {}
    if not isinstance(equipment, dict):
        equipment = {}

    digest = {
        "actor_campaign_brief": _actor_campaign_brief(profile),
        "visible_runtime": _visible_runtime(recent),
        "visible_player_state": _visible_player_state(player_state),
        "visible_npc_state": _visible_npc_state(recent, npc_memory, capability_plan),
        "visible_items": _visible_items(profile, player_state, equipment),
        "style_brief": _style_brief(style, profile),
        "visible_forbidden": _visible_forbidden(forbidden, profile),
        "actor_visible_story_progress": _actor_visible_story_progress(pressure_pack),
    }
    return _compact_digest(_actor_digest_clean(digest))


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


def _campaign_brief(profile: dict[str, Any], direction: dict[str, Any]) -> dict[str, Any]:
    allowed = [
        "campaign_id",
        "title",
        "name",
        "genre",
        "tone",
        "premise",
        "core_concept",
        "opening_situation",
        "main_conflict",
        "early_goals",
        "known_boundaries",
    ]
    brief = _pick_allowed(profile, allowed)
    for key in allowed:
        if key not in brief and key in direction:
            brief[key] = direction[key]
    for source_key, target_key in (
        ("main_tension", "main_conflict"),
        ("theme_and_tone", "tone"),
        ("background_direction", "premise"),
    ):
        if target_key not in brief and source_key in direction:
            brief[target_key] = direction[source_key]
    return brief


def _current_story_anchor(progress: dict[str, Any]) -> dict[str, Any]:
    return _pick_allowed(
        progress,
        [
            "current_chapter_id",
            "current_phase_id",
            "current_node_id",
            "pace_command",
            "turns_in_node",
        ],
    )


def _current_runtime(recent: dict[str, Any]) -> dict[str, Any]:
    return _pick_allowed(
        recent,
        [
            "turn_index",
            "recent_summary",
            "current_scene",
            "last_player_action",
            "last_outcome",
            "short_term_state",
        ],
    )


def _player_brief(profile: dict[str, Any]) -> dict[str, Any]:
    allowed = [
        "name",
        "role",
        "summary",
        "background",
        "personality",
        "motivation",
        "abilities_and_limits",
        "visible_unknowns_or_player_owned",
    ]
    brief: dict[str, Any] = {}
    for source in (
        profile.get("protagonist_patch"),
        (profile.get("character_card_patch") or {}).get("identity") if isinstance(profile.get("character_card_patch"), dict) else None,
        (profile.get("character_card_patch") or {}).get("profile") if isinstance(profile.get("character_card_patch"), dict) else None,
    ):
        if isinstance(source, dict):
            brief.update(_pick_allowed(source, allowed))
    return brief


def _companion_brief(profile: dict[str, Any]) -> dict[str, Any]:
    allowed = [
        "enabled",
        "name",
        "role",
        "personality",
        "relationship_to_protagonist",
        "availability_note",
    ]
    brief: dict[str, Any] = {}
    config = profile.get("companion_config")
    if isinstance(config, dict):
        mapped = {
            "enabled": config.get("enabled", config.get("companion_enabled")),
            "name": config.get("name", config.get("companion_name")),
            "role": config.get("role", config.get("companion_role")),
            "personality": config.get("personality", config.get("companion_personality")),
            "relationship_to_protagonist": config.get("relationship_to_protagonist"),
            "availability_note": config.get("availability_note"),
        }
        brief.update({key: value for key, value in mapped.items() if value not in (None, "", [], {})})
    patch = profile.get("companion_patch")
    if isinstance(patch, dict):
        brief.update(_pick_allowed(patch, allowed))
    return brief


def _node_brief(progress: dict[str, Any], blueprint: dict[str, Any]) -> dict[str, Any]:
    current_node_id = str(progress.get("current_node_id") or "")
    current_chapter_id = str(progress.get("current_chapter_id") or "")
    node, chapter = _find_current_node(blueprint, current_node_id)
    brief: dict[str, Any] = {}
    if current_chapter_id:
        brief["chapter_id"] = current_chapter_id
    if isinstance(chapter, dict):
        brief["chapter_id"] = brief.get("chapter_id") or chapter.get("chapter_id") or chapter.get("id")
        brief["chapter_title"] = chapter.get("chapter_title") or chapter.get("title") or chapter.get("name")
    if current_node_id:
        brief["node_id"] = current_node_id
    if isinstance(node, dict):
        for key in ("node_id", "title", "goal", "beat_checklist", "next_nodes", "requires_deep_instruction"):
            if key in node:
                brief[key] = node[key]
        if "node_id" not in brief:
            brief["node_id"] = node.get("id")
    return {key: value for key, value in brief.items() if value not in (None, "", [], {})}


def _thread_brief(threads: dict[str, Any], capability_plan: dict[str, Any]) -> dict[str, Any]:
    brief = _pick_allowed(
        threads,
        [
            "main_threads",
            "side_threads",
            "unresolved_questions",
            "uncertain_or_unconfirmed",
        ],
        keep_empty=True,
    )
    capabilities = _capabilities(capability_plan)
    if _has_any(capabilities, {"dossier", "clue_found", "investigation"}):
        clues = threads.get("clue_summary")
        if clues not in (None, "", [], {}):
            brief["clue_summary"] = clues
    return brief


def _asset_refs(profile: dict[str, Any], capability_plan: dict[str, Any]) -> dict[str, Any]:
    refs: dict[str, Any] = {
        "existing_map_summary": "",
        "existing_cg_summary": "",
        "known_items": [],
        "note": "Existing assets are references only. Do not emit payloads unless output_contract authorizes them.",
    }
    assets = profile.get("initial_assets")
    if isinstance(assets, dict):
        map_canvas = assets.get("initial_map_canvas")
        if isinstance(map_canvas, dict):
            route = map_canvas.get("map_route")
            if isinstance(route, dict):
                title = route.get("title") or route.get("name") or ""
                node_labels = _route_node_labels(route.get("nodes"))
                parts = [str(title)] if title else []
                if node_labels:
                    parts.append("nodes: " + ", ".join(node_labels))
                refs["existing_map_summary"] = "; ".join(parts)
        initial_cg = assets.get("initial_cg")
        if isinstance(initial_cg, dict):
            refs["existing_cg_summary"] = _short_text(initial_cg.get("generation_instruction") or initial_cg.get("title") or initial_cg.get("description") or "")
        initial_items = assets.get("initial_items")
        if isinstance(initial_items, list):
            refs["known_items"] = [_item_ref(item) for item in initial_items if isinstance(item, dict)]
    capabilities = _capabilities(capability_plan)
    if _has_any(capabilities, {"visual_preload", "user_requested_image"}):
        visual_style = profile.get("visual_style_summary") or profile.get("image_style_summary")
        if visual_style not in (None, "", [], {}):
            refs["visual_style_summary"] = visual_style
    if _has_any(capabilities, {"map_preload", "user_requested_map", "map"}):
        map_summary = profile.get("map_summary")
        if map_summary not in (None, "", [], {}):
            refs["map_summary"] = map_summary
    return refs


def _forbidden_brief(profile: dict[str, Any], direction: dict[str, Any], forbidden: dict[str, Any]) -> dict[str, Any]:
    brief = _pick_allowed(
        forbidden,
        [
            "secrets_not_to_reveal_early",
            "global_forbidden",
            "campaign_specific_forbidden",
            "unconfirmed_should_not_be_written_as_fact",
            "known_boundaries",
            "safety_lines",
            "soft_lines",
            "tone_limits",
        ],
        keep_empty=True,
    )
    if "secrets_not_to_reveal_early" not in brief and "secrets_not_to_reveal" in forbidden:
        brief["secrets_not_to_reveal_early"] = forbidden["secrets_not_to_reveal"]
    for key in ("known_boundaries", "safety_lines", "soft_lines", "tone_limits"):
        if key not in brief and key in profile:
            brief[key] = profile[key]
        if key not in brief and key in direction:
            brief[key] = direction[key]
    safety = direction.get("safety_interpretation")
    if isinstance(safety, dict):
        for key in ("safety_lines", "soft_lines", "tone_limits"):
            if key not in brief and key in safety:
                brief[key] = safety[key]
    return brief


def _actor_campaign_brief(profile: dict[str, Any]) -> dict[str, Any]:
    brief = _pick_allowed(profile, ["campaign_id", "title", "name", "genre", "tone", "premise"])
    player = _actor_person_visible_summary(
        profile.get("protagonist_patch"),
        (profile.get("character_card_patch") or {}).get("identity") if isinstance(profile.get("character_card_patch"), dict) else None,
        (profile.get("character_card_patch") or {}).get("profile") if isinstance(profile.get("character_card_patch"), dict) else None,
    )
    companion = _actor_companion_visible_summary(profile)
    if player:
        brief["protagonist_visible_summary"] = player
    if companion:
        brief["companion_visible_summary"] = companion
    return brief


def _actor_person_visible_summary(*sources: Any) -> dict[str, Any]:
    allowed = [
        "identity",
        "name",
        "role",
        "summary",
        "visible_summary",
        "background",
        "personality",
        "motivation",
        "abilities_and_limits",
        "visible_unknowns_or_player_owned",
    ]
    summary: dict[str, Any] = {}
    for source in sources:
        if isinstance(source, dict):
            summary.update(_pick_allowed(source, allowed))
    return summary


def _actor_companion_visible_summary(profile: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    config = profile.get("companion_config")
    if isinstance(config, dict):
        mapped = {
            "enabled": config.get("enabled", config.get("companion_enabled")),
            "name": config.get("name", config.get("companion_name")),
            "role": config.get("role", config.get("companion_role")),
            "personality": config.get("personality", config.get("companion_personality")),
            "relationship_to_protagonist": config.get("relationship_to_protagonist"),
            "availability_note": config.get("availability_note"),
            "visible_summary": config.get("visible_summary"),
        }
        summary.update({key: value for key, value in mapped.items() if value not in (None, "", [], {})})
    patch = profile.get("companion_patch")
    if isinstance(patch, dict):
        summary.update(_pick_allowed(patch, ["name", "role", "personality", "relationship_to_protagonist", "availability_note", "visible_summary"]))
    return summary


def _visible_runtime(recent: dict[str, Any]) -> dict[str, Any]:
    return _pick_allowed(
        recent,
        [
            "turn_index",
            "recent_summary",
            "current_scene",
            "last_player_action",
            "last_outcome",
            "short_term_state",
        ],
    )


def _visible_player_state(player_state: dict[str, Any]) -> dict[str, Any]:
    brief = _pick_allowed(
        player_state,
        [
            "identity",
            "name",
            "role",
            "current_condition",
            "visible_status",
            "equipment_summary",
            "known_items",
            "current_location",
            "visible_flags",
            "player_owned_unknowns",
        ],
    )
    player = player_state.get("player")
    if isinstance(player, dict):
        brief.update(_pick_allowed(player, ["identity", "name", "role", "current_condition", "visible_status", "equipment_summary", "known_items", "current_location", "visible_flags", "player_owned_unknowns"]))
    return brief


def _style_brief(style: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    allowed = [
        "language",
        "prose_tone",
        "narration_style",
        "dialogue_style",
        "avoid",
        "safety_lines",
        "tone_limits",
    ]
    brief = _pick_allowed(style, allowed)
    for key in ("language", "prose_tone", "narration_style", "dialogue_style", "avoid", "safety_lines", "tone_limits"):
        if key not in brief and key in profile:
            brief[key] = profile[key]
    return brief


def _visible_forbidden(forbidden: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    brief = _pick_allowed(
        forbidden,
        [
            "global_forbidden",
            "campaign_specific_forbidden",
            "unconfirmed_should_not_be_written_as_fact",
            "tone_limits",
            "safety_lines",
        ],
        keep_empty=True,
    )
    for key in ("tone_limits", "safety_lines"):
        if key not in brief and key in profile:
            brief[key] = profile[key]
    return brief


def _visible_npc_state(recent: dict[str, Any], npc_memory: dict[str, Any], capability_plan: dict[str, Any]) -> dict[str, Any]:
    if not _has_any(_capabilities(capability_plan), {"npc_present", "npc_voice", "dialogue_expected", "social"}):
        return {}
    current_scene = recent.get("current_scene") if isinstance(recent.get("current_scene"), dict) else {}
    state: dict[str, Any] = {}
    active_npcs = current_scene.get("active_npcs")
    if active_npcs not in (None, "", [], {}):
        state["active_npcs"] = active_npcs
    for key in ("visible_relationship_summary", "relationship_summary", "last_visible_dialogue_summary"):
        value = recent.get(key)
        if value in (None, "", [], {}):
            value = npc_memory.get(key)
        if value not in (None, "", [], {}):
            state[key] = value
    return state


def _visible_items(profile: dict[str, Any], player_state: dict[str, Any], equipment: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for source in (
        player_state.get("known_items"),
        player_state.get("items"),
        player_state.get("inventory"),
        equipment.get("known_items"),
        equipment.get("items"),
        equipment.get("inventory"),
        ((profile.get("initial_assets") or {}).get("initial_items") if isinstance(profile.get("initial_assets"), dict) else None),
    ):
        if isinstance(source, list):
            for item in source:
                if isinstance(item, dict):
                    ref = _actor_item_ref(item)
                    if ref:
                        items.append(ref)
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        identity = str(item.get("item_id") or item.get("id") or item.get("title") or item.get("name") or _stable_repr(item))
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append(item)
    return deduped


def _actor_item_ref(item: dict[str, Any]) -> dict[str, Any]:
    ref = _pick_allowed(item, ["item_id", "id", "title", "name", "type", "state", "visible_description"])
    if "visible_description" not in ref and item.get("description"):
        ref["visible_description"] = item.get("description")
    return ref


def _pick_allowed(source: dict[str, Any], keys: list[str], keep_empty: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in keys:
        if key not in source:
            continue
        value = source[key]
        if not keep_empty and value in (None, "", [], {}):
            continue
        result[key] = value
    return result


def _find_current_node(blueprint: dict[str, Any], node_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not node_id:
        return None, None
    chapters = blueprint.get("chapters")
    if not isinstance(chapters, list):
        return None, None
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        found = _find_node_in_container(chapter, node_id)
        if found:
            return found, chapter
    return None, None


def _find_node_in_container(container: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for key in ("nodes", "story_nodes"):
        nodes = container.get(key)
        if isinstance(nodes, list):
            for node in nodes:
                if isinstance(node, dict) and str(node.get("node_id") or node.get("id") or "") == node_id:
                    return node
    phases = container.get("phases")
    if isinstance(phases, list):
        for phase in phases:
            if isinstance(phase, dict):
                found = _find_node_in_container(phase, node_id)
                if found:
                    return found
    return None


def _route_node_labels(nodes: Any) -> list[str]:
    if not isinstance(nodes, list):
        return []
    labels: list[str] = []
    for node in nodes[:12]:
        if not isinstance(node, dict):
            continue
        label = node.get("label") or node.get("title") or node.get("name")
        if label:
            labels.append(_short_text(label, 80))
    return labels


def _item_ref(item: dict[str, Any]) -> dict[str, Any]:
    return _pick_allowed(item, ["id", "item_id", "name", "title", "type", "state", "description"])


def _compact_digest(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _compact_digest(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_compact_digest(item) for item in value[:20]]
    if isinstance(value, str):
        return _short_text(value)
    return deepcopy(value)


def _short_text(value: Any, limit: int = 500) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _actor_digest_clean(value: Any) -> Any:
    hidden_keys = {
        "director_setup",
        "setup_patch",
        "prompt_routing",
        "story_memory_seed",
        "initial_assets",
        "initial_map_canvas",
        "render_rules",
        "visual_contract_candidates",
        "campaign_taxonomy",
        "character_attribute_schema",
        "custom_libraries",
        "mechanics",
        "story_blueprint_patch",
        "canvas_draw_instructions",
        "item_canvas_rules",
        "icon_rules",
        "asset_key",
        "canvas",
        "image_prompt",
        "orchestration_forecast",
        "actor_dispatch",
        "hotload_next_turn",
        "upcoming_assets",
        "hidden_reason",
        "future_node",
        "future_asset",
        "applied_writeback_hashes",
        "hidden_truth",
        "hidden_motive",
        "secret",
        "secrets_not_to_reveal",
        "forbidden_reveals",
        "director_notes",
        "future_nodes",
        "npc_knowledge_boundaries",
    }
    hidden_tokens = (
        "backend",
        "cache",
        "canvas",
        "debug",
        "director_note",
        "forecast",
        "future_asset",
        "future_node",
        "hidden",
        "hotload_next_turn",
        "orchestration_forecast",
        "secret",
        "upcoming_assets",
    )
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            if key_text in hidden_keys or any(token in lowered for token in hidden_tokens):
                continue
            cleaned = _actor_digest_clean(item)
            clean[key_text] = cleaned
        return clean
    if isinstance(value, list):
        return [_actor_digest_clean(item) for item in value]
    return value


def _stable_repr(value: Any) -> str:
    try:
        return repr(sorted(value.items())) if isinstance(value, dict) else repr(value)
    except Exception:
        return repr(value)


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
        "orchestration_forecast",
        "actor_dispatch",
        "hotload_next_turn",
        "upcoming_assets",
        "hidden_reason",
        "future_asset",
        "future_node",
    }
    if isinstance(data, dict):
        clean: dict[str, Any] = {}
        for key, value in data.items():
            if key in hidden_keys:
                continue
            lowered = str(key).lower()
            if any(token in lowered for token in ("hidden", "secret", "director_note", "future_node", "forbidden_reveal", "future_asset", "hotload_next_turn", "orchestration_forecast", "actor_dispatch", "upcoming_assets")):
                continue
            clean[key] = _sanitize_actor_memory(value)
        return clean
    if isinstance(data, list):
        return [_sanitize_actor_memory(item) for item in data]
    return data
