# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any

from .output_contract import is_optional_writeback_authorized
from .story_progress import apply_progress_writeback


WRITEBACK_FILE_MAP = {
    "player_growth": "player_state.json",
    "npc_memory_updates": "npc_memory.json",
    "world_state_updates": "world_state.json",
    "location_history_updates": "location_history.json",
    "quest_history_updates": "quest_history.json",
    "enemy_or_mystery_updates": "enemy_or_monster_ecology.json",
    "equipment_history_updates": "equipment_history.json",
    "main_thread_updates": "main_threads.json",
    "forbidden_changes_to_preserve": "forbidden_changes.json",
}


SCALAR_UPDATE_FIELDS = {
    "player_growth": ("player_state.json", "growth_log"),
    "world_state_updates": ("world_state.json", "world_updates"),
    "location_history_updates": ("location_history.json", "location_updates"),
    "quest_history_updates": ("quest_history.json", "quest_updates"),
    "enemy_or_mystery_updates": ("enemy_or_monster_ecology.json", "mystery_updates"),
    "equipment_history_updates": ("equipment_history.json", "equipment_updates"),
}

MAX_APPLIED_WRITEBACK_HASHES = 50
MEMORY_TYPES = {"confirmed_fact", "observed_clue", "npc_claim", "short_term_scene", "progress_update"}
CERTAINTY_LEVELS = {"confirmed", "likely", "uncertain"}
WRITEBACK_SOURCES = {"actor", "director", "audit", "backend"}
TTL_VALUES = {"scene", "session", "permanent"}
WRITEBACK_METADATA_KEYS = {"memory_type", "certainty", "source", "ttl"}


def normalize_writeback_entry(entry: Any, default_memory_type: str = "short_term_scene") -> dict[str, Any]:
    memory_type = default_memory_type if default_memory_type in MEMORY_TYPES else "short_term_scene"
    if isinstance(entry, dict):
        normalized = deepcopy(entry)
        if "value" not in normalized:
            for key in ("text", "note", "summary", "title", "name", "description"):
                if key in normalized:
                    normalized["value"] = normalized.get(key)
                    break
            else:
                normalized["value"] = {key: deepcopy(value) for key, value in entry.items() if key not in WRITEBACK_METADATA_KEYS}
    else:
        normalized = {"value": entry}

    if normalized.get("memory_type") not in MEMORY_TYPES:
        normalized["memory_type"] = memory_type
    if normalized.get("certainty") not in CERTAINTY_LEVELS:
        normalized["certainty"] = "uncertain"
    if normalized.get("source") not in WRITEBACK_SOURCES:
        normalized["source"] = "actor"
    if normalized.get("ttl") not in TTL_VALUES:
        normalized["ttl"] = "scene"
    return normalized


def apply_approved_writeback(
    memory: dict[str, Any],
    approved_writeback: dict[str, Any],
    extra_hashes: list[str] | None = None,
    pressure_pack: dict[str, Any] | None = None,
    prose_chars_delta: int | None = None,
) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    long_term = approved_writeback.get("long_term_memory", approved_writeback)
    short_term = approved_writeback.get("short_term_state", {})

    for field, (filename, bucket) in SCALAR_UPDATE_FIELDS.items():
        value = long_term.get(field)
        if value in (None, "", [], {}):
            continue
        for entry in as_list(value):
            normalized = normalize_writeback_entry(entry)
            route_general_writeback_entry(memory, updates, field, filename, bucket, normalized)

    npc_updates = long_term.get("npc_memory_updates")
    if isinstance(npc_updates, dict) and npc_updates:
        target = deepcopy(updates.get("npc_memory.json") or memory["npc_memory.json"])
        target.setdefault("npcs", {})
        for name, note in npc_updates.items():
            npc = target["npcs"].setdefault(name, {"facts": [], "uncertain": [], "notes": []})
            for entry in as_list(note):
                normalized = normalize_writeback_entry(
                    entry,
                    default_memory_type="npc_claim" if isinstance(entry, dict) else "short_term_scene",
                )
                routed = make_entry("npc_memory_updates", normalized)
                if is_confirmed_fact(normalized):
                    append_unique(npc, "facts", routed)
                elif normalized["memory_type"] == "npc_claim":
                    append_unique(npc, "uncertain", routed)
                else:
                    append_unique(npc, "notes", routed)
        updates["npc_memory.json"] = target

    thread_updates = long_term.get("main_thread_updates")
    if thread_updates:
        target = deepcopy(updates.get("main_threads.json") or memory["main_threads.json"])
        target.setdefault("main_threads", [])
        for item in as_list(thread_updates):
            normalized = normalize_writeback_entry(item, default_memory_type="progress_update")
            if normalized["memory_type"] in {"progress_update", "confirmed_fact"}:
                append_thread(target["main_threads"], normalized)
        for item in as_list(approved_writeback.get("new_open_threads")):
            append_thread(target.setdefault("side_threads", []), item)
        for item in as_list(approved_writeback.get("closed_threads")):
            append_thread(target.setdefault("closed_threads", []), item)
        updates["main_threads.json"] = target

    forbidden_updates = long_term.get("forbidden_changes_to_preserve")
    if forbidden_updates:
        target = deepcopy(updates.get("forbidden_changes.json") or memory["forbidden_changes.json"])
        target.setdefault("campaign_specific_forbidden", [])
        for item in as_list(forbidden_updates):
            append_plain_unique(target["campaign_specific_forbidden"], item)
        updates["forbidden_changes.json"] = target

    if short_term or approved_writeback.get("summary_for_recent_context"):
        recent = deepcopy(updates.get("recent_context.json") or memory["recent_context.json"])
        summary = approved_writeback.get("summary_for_recent_context", recent.get("last_outcome", ""))
        recent["last_outcome"] = summary
        recent.setdefault("recent_summary", [])
        if summary:
            append_plain_unique(recent["recent_summary"], summary)
            recent["recent_summary"] = recent["recent_summary"][-12:]
        recent["short_term_state"] = short_term
        recent["turn_index"] = int(recent.get("turn_index", 0)) + 1
        scene = recent.setdefault("current_scene", {})
        if short_term.get("location"):
            scene["location"] = short_term["location"]
        if short_term.get("npcs"):
            scene["active_npcs"] = list(short_term["npcs"].keys())
        if short_term.get("quest"):
            scene["immediate_pressure"] = short_term["quest"]
        updates["recent_context.json"] = recent

    protocol_warnings: list[str] = []
    progress_writeback = approved_writeback.get("progress_writeback")
    if isinstance(progress_writeback, dict):
        if prose_chars_delta is None:
            prose_chars_delta = _writeback_prose_chars(approved_writeback)
        updated_progress = apply_progress_writeback(
            memory.get("story_blueprint.json", {}),
            memory.get("story_progress.json", {}),
            progress_writeback,
            prose_chars_delta=prose_chars_delta or 0,
        )
        updates["story_progress.json"] = updated_progress
        protocol_warnings.extend(updated_progress.get("protocol_warnings", []))

    optional_writebacks = approved_writeback.get("optional_writebacks")
    if isinstance(optional_writebacks, dict) and optional_writebacks:
        allowed = _authorized_optional_writebacks(optional_writebacks, pressure_pack or {})
        blocked = sorted(set(optional_writebacks) - allowed)
        if blocked:
            protocol_warnings.append("unauthorized optional_writebacks ignored: " + ", ".join(blocked))
            target = deepcopy(updates.get("story_progress.json") or memory.get("story_progress.json", {}))
            target.setdefault("protocol_warnings", [])
            for warning in protocol_warnings:
                append_plain_unique(target["protocol_warnings"], warning)
            updates["story_progress.json"] = target
        if allowed:
            apply_optional_writebacks(memory, approved_writeback, pressure_pack or {}, updates, allowed)

    remember_applied_writeback_hashes(updates, memory, approved_writeback, extra_hashes)
    stamp_updates(updates, memory)
    return updates


def _writeback_prose_chars(writeback: dict[str, Any]) -> int:
    parts = [
        writeback.get("summary_for_recent_context", ""),
        writeback.get("next_turn_suggestions", ""),
    ]
    short = writeback.get("short_term_state", {})
    if isinstance(short, dict):
        parts.extend(str(value) for value in short.values() if isinstance(value, str))
    return len("".join(str(part) for part in parts if part))


def is_confirmed_fact(entry: dict[str, Any]) -> bool:
    return entry.get("memory_type") == "confirmed_fact" and entry.get("certainty") == "confirmed"


def route_general_writeback_entry(
    memory: dict[str, Any],
    updates: dict[str, Any],
    field: str,
    filename: str,
    bucket: str,
    entry: dict[str, Any],
) -> None:
    if is_confirmed_fact(entry):
        target = deepcopy(updates.get(filename) or memory[filename])
        append_unique(target, bucket, make_entry(field, entry))
        updates[filename] = target
        return
    if entry["memory_type"] == "observed_clue":
        append_clue_entry(memory, updates, field, entry)
        return
    if entry["memory_type"] == "progress_update":
        target = deepcopy(updates.get("main_threads.json") or memory.get("main_threads.json", {}))
        target.setdefault("main_threads", [])
        append_thread(target["main_threads"], entry)
        updates["main_threads.json"] = target
        return
    append_recent_writeback_note(memory, updates, field, entry)


def append_clue_entry(memory: dict[str, Any], updates: dict[str, Any], field: str, entry: dict[str, Any]) -> None:
    target = deepcopy(updates.get("clue_history.json") or memory.get("clue_history.json", {}))
    target.setdefault("notes", [])
    append_plain_unique(target["notes"], make_entry(field, entry))
    updates["clue_history.json"] = target


def append_recent_writeback_note(memory: dict[str, Any], updates: dict[str, Any], field: str, entry: dict[str, Any]) -> None:
    recent = deepcopy(updates.get("recent_context.json") or memory["recent_context.json"])
    recent.setdefault("writeback_observations", [])
    append_plain_unique(recent["writeback_observations"], make_entry(field, entry))
    updates["recent_context.json"] = recent


def _authorized_optional_writebacks(optional_writebacks: dict[str, Any], pressure_pack: dict[str, Any]) -> set[str]:
    output_requests = pressure_pack.get("output_requests") if isinstance(pressure_pack, dict) else {}
    if not isinstance(output_requests, dict):
        return set()
    return {key for key in optional_writebacks if is_optional_writeback_authorized(key, output_requests)}


def apply_optional_writebacks(
    memory: dict[str, Any],
    approved_writeback: dict[str, Any],
    pressure_pack: dict[str, Any],
    updates: dict[str, Any],
    allowed_keys: set[str] | None = None,
) -> None:
    optional = approved_writeback.get("optional_writebacks")
    if not isinstance(optional, dict):
        return
    allowed = allowed_keys if allowed_keys is not None else _authorized_optional_writebacks(optional, pressure_pack)
    if "inventory_updates" in allowed:
        apply_inventory_writeback(memory, optional.get("inventory_updates"), updates)
    if "dossier_updates" in allowed:
        apply_dossier_writeback(memory, optional.get("dossier_updates"), updates)
    if "character_card_update" in allowed:
        apply_character_card_writeback(memory, optional.get("character_card_update"), updates)
    if "map_route" in allowed or "map_canvas" in allowed or "map" in allowed:
        apply_map_writeback(memory, optional, updates)
    if "canvas_jobs" in allowed:
        apply_canvas_jobs_writeback(memory, optional.get("canvas_jobs"), updates)


def apply_inventory_writeback(memory: dict[str, Any], payload: Any, updates: dict[str, Any]) -> None:
    if payload in (None, "", [], {}):
        return
    target = deepcopy(updates.get("equipment_history.json") or memory.get("equipment_history.json", {}))
    target.setdefault("inventory_updates", [])
    for item in as_list(payload):
        normalized = normalize_inventory_update_item(item)
        if normalized:
            append_plain_unique(target["inventory_updates"], normalized)
    updates["equipment_history.json"] = target


def _brief(value: Any, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit].rstrip()


def _safe_id(value: Any) -> str:
    text = re.sub(r"[^0-9a-zA-Z_\-\u4e00-\u9fff]+", "_", str(value or "").strip().lower())
    return text.strip("_") or "item"


def _owner_allowed(owner: Any, owner_ref: Any = "", evidence: Any = "") -> bool:
    owner_value = str(owner or "").strip().lower()
    if owner_value in {"player", "companion"}:
        return True
    if owner_value != "party":
        return False
    relation_text = f"{owner_ref} {evidence}".lower()
    return any(token in relation_text for token in ("player", "protagonist", "companion", "主角", "玩家", "伙伴", "同伴", "随身", "携带", "持有", "共用"))


def normalize_inventory_update_item(item: Any) -> dict[str, Any]:
    value = item.get("value") if isinstance(item, dict) and isinstance(item.get("value"), dict) else item
    if not isinstance(value, dict):
        return {}
    name = _brief(value.get("name") or value.get("title"), 80)
    item_type = _safe_id(value.get("item_type") or value.get("type") or "generic")
    owner = str(value.get("owner") or "").strip().lower()
    owner_ref = _brief(value.get("owner_ref") or value.get("holder"), 80)
    evidence = _brief(value.get("source_evidence") or value.get("evidence") or value.get("short_description") or value.get("description"), 220)
    if not name or not _owner_allowed(owner, owner_ref, evidence):
        return {}
    status = str(value.get("status") or "confirmed").strip().lower()
    if status not in {"confirmed", "limited", "damaged", "uncertain"}:
        status = "confirmed"
    certainty = str(value.get("certainty") or "confirmed").strip().lower()
    if certainty not in {"confirmed", "clue", "uncertain"}:
        certainty = "confirmed"
    return {
        "id": _safe_id(value.get("id") or f"{owner}:{item_type}:{name}"),
        "name": name,
        "category": _safe_id(value.get("category") or "item"),
        "item_type": item_type,
        "status": status,
        "owner": owner,
        "owner_ref": owner_ref,
        "short_description": _brief(value.get("short_description") or value.get("description") or evidence, 180),
        "canvas_style": value.get("canvas_style") if isinstance(value.get("canvas_style"), dict) else {},
        "visual_hint": value.get("visual_hint") if isinstance(value.get("visual_hint"), dict) else {},
        "simple_prompt": _brief(value.get("simple_prompt") or value.get("prompt") or evidence, 180),
        "certainty": certainty,
        "source_evidence": evidence,
    }


def apply_dossier_writeback(memory: dict[str, Any], payload: Any, updates: dict[str, Any]) -> None:
    if payload in (None, "", [], {}):
        return
    target = deepcopy(updates.get("clue_history.json") or memory.get("clue_history.json", {}))
    target.setdefault("notes", [])
    for item in as_list(payload):
        append_plain_unique(target["notes"], {"source": "optional_dossier_update", "value": item})
    updates["clue_history.json"] = target


def apply_character_card_writeback(memory: dict[str, Any], payload: Any, updates: dict[str, Any]) -> None:
    if not isinstance(payload, dict) or not payload:
        return
    target = deepcopy(updates.get("player_state.json") or memory.get("player_state.json", {}))
    target["character_card"] = payload
    updates["player_state.json"] = target


def apply_map_writeback(memory: dict[str, Any], payload: dict[str, Any], updates: dict[str, Any]) -> None:
    target = deepcopy(updates.get("map_history.json") or memory.get("map_history.json", {}))
    target.setdefault("route_history", [])
    route = payload.get("map_route") if isinstance(payload.get("map_route"), dict) else payload.get("map")
    if route:
        append_plain_unique(target["route_history"], {"source": "optional_map_writeback", "value": route})
    updates["map_history.json"] = target


def apply_canvas_jobs_writeback(memory: dict[str, Any], payload: Any, updates: dict[str, Any]) -> None:
    if payload in (None, "", [], {}):
        return
    target = deepcopy(updates.get("run_records.json") or memory.get("run_records.json", {}))
    target.setdefault("canvas_jobs", [])
    for item in as_list(payload):
        append_plain_unique(target["canvas_jobs"], item)
    updates["run_records.json"] = target


def remember_applied_writeback_hashes(
    updates: dict[str, Any],
    memory: dict[str, Any],
    approved_writeback: dict[str, Any],
    extra_hashes: list[str] | None = None,
) -> None:
    digests = [writeback_hash(approved_writeback), *(extra_hashes or [])]
    digests = [digest for digest in digests if digest]
    if not digests:
        return
    recent = deepcopy(updates.get("recent_context.json") or memory["recent_context.json"])
    applied = recent.setdefault("applied_writeback_hashes", [])
    if not isinstance(applied, list):
        applied = []
        recent["applied_writeback_hashes"] = applied
    for digest in digests:
        append_plain_unique(applied, digest)
    recent["applied_writeback_hashes"] = applied[-MAX_APPLIED_WRITEBACK_HASHES:]
    updates["recent_context.json"] = recent


def migrate_legacy_facts(memory: dict[str, Any]) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for filename, data in memory.items():
        facts = data.get("facts")
        if not isinstance(facts, list) or not facts:
            continue
        target = deepcopy(data)
        changed = False
        for fact in facts:
            if not isinstance(fact, dict) or fact.get("source") != "state_writeback":
                continue
            field = fact.get("field")
            value = fact.get("value")
            if field == "npc_memory_updates" and isinstance(value, dict):
                target.setdefault("npcs", {})
                for name, note in value.items():
                    npc = target["npcs"].setdefault(name, {"facts": [], "uncertain": [], "notes": []})
                    append_unique(npc, "facts", make_entry(field, note))
                    changed = True
            elif field == "main_thread_updates":
                target.setdefault("main_threads", [])
                for item in as_list(value):
                    append_thread(target["main_threads"], item)
                    changed = True
            elif field == "forbidden_changes_to_preserve":
                target.setdefault("campaign_specific_forbidden", [])
                for item in as_list(value):
                    append_plain_unique(target["campaign_specific_forbidden"], item)
                    changed = True
            elif field in SCALAR_UPDATE_FIELDS:
                _, bucket = SCALAR_UPDATE_FIELDS[field]
                append_unique(target, bucket, make_entry(field, value))
                changed = True
        if changed:
            target["legacy_facts_migrated"] = True
            updates[filename] = target
    return updates



def stamp_updates(updates: dict[str, Any], memory: dict[str, Any]) -> None:
    recent = updates.get("recent_context.json") or memory.get("recent_context.json", {})
    turn = int(recent.get("turn_index", 0))
    for data in updates.values():
        if isinstance(data, dict) and "last_updated_turn" in data:
            data["last_updated_turn"] = turn

def make_entry(field: str, value: Any) -> dict[str, Any]:
    return {"source": "state_writeback", "field": field, "value": value}


def append_unique(target: dict[str, Any], key: str, entry: dict[str, Any]) -> None:
    target.setdefault(key, [])
    if entry not in target[key]:
        target[key].append(entry)


def append_plain_unique(items: list[Any], value: Any) -> None:
    if value not in items:
        items.append(value)


def append_thread(items: list[Any], title: Any) -> None:
    if not title:
        return
    if isinstance(title, dict):
        entry = title
        identity = title.get("title") or title.get("name") or str(title)
    else:
        identity = str(title)
        entry = {"title": identity, "status": "open", "source": "state_writeback"}
    for existing in items:
        if isinstance(existing, dict) and (existing.get("title") == identity or existing.get("name") == identity):
            return
        if existing == title or existing == identity:
            return
    items.append(entry)


def as_list(value: Any) -> list[Any]:
    if value in (None, "", {}, []):
        return []
    return value if isinstance(value, list) else [value]


def writeback_hash(writeback: dict[str, Any]) -> str:
    payload = json.dumps(writeback, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def has_applied_writeback(memory: dict[str, Any], digest: str) -> bool:
    recent = memory.get("recent_context.json", {})
    return digest in recent.get("applied_writeback_hashes", [])
