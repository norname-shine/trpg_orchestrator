# -*- coding: gbk -*-
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any


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


MAX_WRITEBACK_HASHES = 50


def apply_approved_writeback(memory: dict[str, Any], approved_writeback: dict[str, Any], extra_hashes: list[str] | None = None) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    long_term = approved_writeback.get("long_term_memory", approved_writeback)
    short_term = approved_writeback.get("short_term_state", {})

    for field, (filename, bucket) in SCALAR_UPDATE_FIELDS.items():
        value = long_term.get(field)
        if value in (None, "", [], {}):
            continue
        target = deepcopy(updates.get(filename) or memory[filename])
        append_unique(target, bucket, make_entry(field, value))
        updates[filename] = target

    npc_updates = long_term.get("npc_memory_updates")
    if isinstance(npc_updates, dict) and npc_updates:
        target = deepcopy(updates.get("npc_memory.json") or memory["npc_memory.json"])
        target.setdefault("npcs", {})
        for name, note in npc_updates.items():
            npc = target["npcs"].setdefault(name, {"facts": [], "uncertain": [], "notes": []})
            append_unique(npc, "facts", make_entry("npc_memory_updates", note))
        updates["npc_memory.json"] = target

    thread_updates = long_term.get("main_thread_updates")
    if thread_updates:
        target = deepcopy(updates.get("main_threads.json") or memory["main_threads.json"])
        target.setdefault("main_threads", [])
        for item in as_list(thread_updates):
            append_thread(target["main_threads"], item)
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

    writeback_hashes = writeback_hashes_to_record(approved_writeback, extra_hashes)
    if short_term or approved_writeback.get("summary_for_recent_context") or writeback_hashes:
        recent = deepcopy(updates.get("recent_context.json") or memory["recent_context.json"])
        summary = approved_writeback.get("summary_for_recent_context", recent.get("last_outcome", ""))
        recent["last_outcome"] = summary
        recent.setdefault("recent_summary", [])
        if summary:
            append_plain_unique(recent["recent_summary"], summary)
            recent["recent_summary"] = recent["recent_summary"][-12:]
        recent["short_term_state"] = short_term
        remember_writeback_hashes(recent, writeback_hashes)
        recent["turn_index"] = int(recent.get("turn_index", 0)) + 1
        scene = recent.setdefault("current_scene", {})
        if short_term.get("location"):
            scene["location"] = short_term["location"]
        if short_term.get("npcs"):
            scene["active_npcs"] = list(short_term["npcs"].keys())
        if short_term.get("quest"):
            scene["immediate_pressure"] = short_term["quest"]
        updates["recent_context.json"] = recent

    stamp_updates(updates, memory)
    return updates


def writeback_hashes_to_record(approved_writeback: dict[str, Any], extra_hashes: list[str] | None = None) -> list[str]:
    hashes: list[str] = []
    current_hash = writeback_hash(approved_writeback)
    if current_hash:
        hashes.append(current_hash)
    for digest in extra_hashes or []:
        if digest:
            hashes.append(str(digest))
    return hashes


def remember_writeback_hashes(recent: dict[str, Any], hashes: list[str]) -> None:
    if not hashes:
        return
    existing = recent.get("applied_writeback_hashes", [])
    if not isinstance(existing, list):
        existing = []
    for digest in hashes:
        append_plain_unique(existing, digest)
    recent["applied_writeback_hashes"] = existing[-MAX_WRITEBACK_HASHES:]


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
    if not digest:
        return False
    recent = memory.get("recent_context.json", {})
    applied = recent.get("applied_writeback_hashes", [])
    return isinstance(applied, list) and digest in applied
