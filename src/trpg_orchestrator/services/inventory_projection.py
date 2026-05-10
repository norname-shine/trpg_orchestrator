# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any

from .asset_rules import safe_segment


def frontend_inventory(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Project legacy equipment_history data into the old frontend card shape.

    The live UI now reads protocol inventory data from the inventory extension.
    This adapter remains for campaign initialization checks and older tooling
    that still inspect equipment_history directly.
    """
    equipment = state.get("equipment", {}) if isinstance(state.get("equipment"), dict) else {}
    source: list[dict[str, Any]] = []
    items = equipment.get("items") if isinstance(equipment.get("items"), dict) else {}
    for item_id, item in items.items():
        if not isinstance(item, dict):
            continue
        normalized = normalize_director_inventory_item({**item, "id": item.get("id") or item_id})
        if normalized:
            source.append(normalized)
    item_rules = equipment.get("item_canvas_rules") if isinstance(equipment.get("item_canvas_rules"), dict) else {}
    initial_items = equipment.get("initial_items", []) if isinstance(equipment.get("initial_items"), list) else []
    for item in initial_items:
        if not isinstance(item, dict):
            continue
        item_id = safe_segment(str(item.get("id") or item.get("key") or item.get("name") or item.get("title") or item.get("label") or "initial_item"))
        rule = item_rules.get(item_id) if isinstance(item_rules.get(item_id), dict) else {}
        normalized = normalize_director_inventory_item({
            "id": item_id,
            "name": item.get("name") or item.get("title") or item.get("label") or item_id,
            "category": item.get("category") or item.get("kind") or item.get("type") or "item",
            "item_type": item.get("item_type") or item.get("type") or item.get("category") or "initial",
            "status": item.get("status") or "confirmed",
            "owner": item.get("owner") or "party",
            "owner_ref": item.get("owner_ref") or "player_party_initial_inventory",
            "short_description": item.get("short_description") or item.get("description") or item.get("detail") or "",
            "canvas_style": {**rule, **(item.get("canvas_style") if isinstance(item.get("canvas_style"), dict) else {})},
            "certainty": item.get("certainty") or "confirmed",
            "source_evidence": item.get("source_evidence") or "campaign_initialization finalized item carried by player or companion party",
        })
        if normalized:
            source.append(normalized)
    merged: dict[str, dict[str, Any]] = {}
    for item in source:
        entity_id = str(item.get("id") or stable_director_inventory_id(item))
        detail = str(item.get("short_description") or item.get("description") or item.get("source_evidence") or item.get("name") or "")
        if entity_id in merged:
            merged[entity_id]["detail"] = merge_detail_text(merged[entity_id]["detail"], detail)
            continue
        category = str(item.get("category") or "item")
        item_type = str(item.get("item_type") or "generic")
        merged[entity_id] = {
            "id": entity_id,
            "raw_name": str(item.get("name") or entity_id),
            "short_name": stringify_brief(item.get("name") or entity_id, 40),
            "category": category,
            "role": "player_companion_item",
            "detail": detail,
            "visual_prompt": {
                "type": item_type,
                "category": category,
                "simple_prompt": item.get("simple_prompt") or "",
                "canvas_style": item.get("canvas_style") if isinstance(item.get("canvas_style"), dict) else {},
                "visual_hint": item.get("visual_hint") if isinstance(item.get("visual_hint"), dict) else {},
                "source_text": stringify_brief(item.get("source_evidence") or detail, 160),
            },
            "asset_key": f"item:{safe_segment(entity_id)}",
            "item_type": item_type,
            "owner": item.get("owner", ""),
            "owner_ref": item.get("owner_ref", ""),
            "status": item.get("status", ""),
            "certainty": item.get("certainty", ""),
        }
    return list(merged.values())[:16]


def inventory_owner_allowed(owner: Any, owner_ref: Any = "", evidence: Any = "") -> bool:
    owner_value = str(owner or "").strip().lower()
    if owner_value in {"player", "companion"}:
        return True
    if owner_value != "party":
        return False
    relation_text = f"{owner_ref} {evidence}".lower()
    return any(token in relation_text for token in ("player", "protagonist", "companion", "main character", "party", "carried"))


def short_director_item_prompt(value: Any, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def stable_director_inventory_id(item: dict[str, Any]) -> str:
    base = f"{item.get('owner') or 'player'}:{item.get('item_type') or 'item'}:{item.get('name') or item.get('title') or 'item'}"
    return safe_segment(base.lower())


def normalize_director_inventory_item(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    value = item.get("value") if isinstance(item.get("value"), dict) else item
    if not isinstance(value, dict):
        return {}
    name = stringify_brief(value.get("name") or value.get("title") or value.get("display_name"), 80)
    item_type = safe_segment(str(value.get("item_type") or value.get("type") or "generic").lower()) or "generic"
    owner = str(value.get("owner") or "").strip().lower()
    owner_ref = stringify_brief(value.get("owner_ref") or value.get("holder") or "", 80)
    evidence = stringify_brief(value.get("source_evidence") or value.get("evidence") or value.get("short_description") or value.get("description") or "", 220)
    if not name or not inventory_owner_allowed(owner, owner_ref, evidence):
        return {}
    status = str(value.get("status") or "confirmed").strip().lower()
    if status not in {"confirmed", "limited", "damaged", "uncertain"}:
        status = "confirmed"
    certainty = str(value.get("certainty") or "confirmed").strip().lower()
    if certainty not in {"confirmed", "clue", "uncertain"}:
        certainty = "confirmed"
    category = safe_segment(str(value.get("category") or "item").lower()) or "item"
    canvas_style = value.get("canvas_style") if isinstance(value.get("canvas_style"), dict) else {}
    visual_hint = value.get("visual_hint") if isinstance(value.get("visual_hint"), dict) else {}
    simple_prompt = short_director_item_prompt(value.get("simple_prompt") or value.get("prompt") or visual_hint.get("source_text") or evidence)
    return {
        "id": safe_segment(str(value.get("id") or stable_director_inventory_id({"owner": owner, "item_type": item_type, "name": name}))),
        "name": name,
        "category": category,
        "item_type": item_type,
        "status": status,
        "owner": owner,
        "owner_ref": owner_ref,
        "short_description": stringify_brief(value.get("short_description") or value.get("description") or evidence, 180),
        "canvas_style": canvas_style,
        "visual_hint": visual_hint,
        "simple_prompt": simple_prompt,
        "certainty": certainty,
        "source_evidence": evidence,
    }


def stringify_brief(value: Any, limit: int = 220) -> str:
    text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("..." if len(text) > limit else "")


def normalized_name(value: Any) -> str:
    return re.sub(r"[\s_.,;:!?\"'()\[\]{}<>-]+", "", str(value or "").lower())


def merge_detail_text(current: str, new: str, limit: int = 180) -> str:
    parts = []
    seen = set()
    for value in re.split(r"[;,\n]+", f"{current};{new}"):
        item = value.strip()
        if not item:
            continue
        key = normalized_name(item)
        if key in seen:
            continue
        seen.add(key)
        parts.append(item)
    return stringify_brief("; ".join(parts), limit)
