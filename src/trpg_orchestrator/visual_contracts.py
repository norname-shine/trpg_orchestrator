# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any


SCHEMA = "trpg_orchestrator.visual_contracts.v1"
CONTRACT_FILE = "visual_contracts.json"


def default_visual_contracts(campaign_id: str) -> dict[str, Any]:
    return {
        "campaign_id": campaign_id,
        "schema": SCHEMA,
        "contracts": {},
        "notes": [
            "Campaign-bound visual interpretation layer. Source memory remains in the referenced memory files.",
        ],
    }


def stable_contract_hash(contract: dict[str, Any]) -> str:
    payload = deepcopy(contract)
    payload.pop("visual_contract_hash", None)
    payload.pop("updated_at", None)
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def normalize_visual_contract_candidate(candidate: Any, campaign_id: str, source: str = "") -> dict[str, Any]:
    if not isinstance(candidate, dict):
        return {}
    raw_entity_type = str(candidate.get("entity_type") or candidate.get("type") or candidate.get("kind") or "").strip()
    entity_type = safe_key(raw_entity_type) if raw_entity_type else ""
    allowed_entity_types = {"player", "companion", "character", "map", "cg", "item", "prop"}
    if entity_type and entity_type not in allowed_entity_types:
        raise RuntimeError(f"unknown visual contract entity_type: {entity_type}")
    display = str(candidate.get("display_name") or candidate.get("title") or candidate.get("name") or "").strip()
    entity_key = str(candidate.get("entity_key") or "").strip()
    if not entity_key and entity_type and display:
        entity_key = f"{entity_type}:{safe_key(display)}"
    if not entity_key:
        return {}
    if ":" in entity_key and not entity_type:
        entity_type = safe_key(entity_key.split(":", 1)[0])
    if not entity_type:
        raise RuntimeError("visual contract entity_type is required")
    if entity_type not in allowed_entity_types:
        raise RuntimeError(f"unknown visual contract entity_type: {entity_type}")
    render_intent = object_or_empty(candidate.get("render_intent"))
    primary = safe_key(render_intent.get("primary") or "")
    if "portrait" in primary and entity_type not in {"player", "companion", "character"}:
        raise RuntimeError(f"{entity_type} visual contract cannot use portrait render intent")
    contract = {
        "entity_key": entity_key,
        "entity_type": entity_type,
        "display_name": display or readable_from_key(entity_key),
        "source": str(candidate.get("source") or source or "director_candidate"),
        "binding": normalize_binding(candidate.get("binding"), campaign_id, candidate.get("memory_refs")),
        "visibility": str(candidate.get("visibility") or "player_visible"),
        "confidence": str(candidate.get("confidence") or "confirmed"),
        "visual_identity": object_or_empty(candidate.get("visual_identity")),
        "render_intent": render_intent,
        "style_constraints": object_or_empty(candidate.get("style_constraints")),
        "negative_constraints": list_of_strings(candidate.get("negative_constraints")),
        "update_policy": object_or_empty(candidate.get("update_policy")),
    }
    for key in ("details", "spatial", "physical", "actor", "image_prompt"):
        if isinstance(candidate.get(key), dict):
            contract.setdefault("visual_identity", {}).setdefault(key, deepcopy(candidate[key]))
    contract["visual_contract_hash"] = stable_contract_hash(contract)
    return contract


def merge_visual_contracts(existing: dict[str, Any] | None, candidates: list[Any], campaign_id: str, source: str = "") -> dict[str, Any]:
    result = default_visual_contracts(campaign_id)
    if isinstance(existing, dict):
        result.update({key: deepcopy(value) for key, value in existing.items() if key != "contracts"})
        result["campaign_id"] = campaign_id
        result["schema"] = SCHEMA
        result["contracts"] = {
            key: value for key, value in (existing.get("contracts") or {}).items()
            if isinstance(key, str) and isinstance(value, dict)
        }
    for candidate in candidates:
        contract = normalize_visual_contract_candidate(candidate, campaign_id, source)
        if not contract:
            continue
        key = contract["entity_key"]
        previous = result["contracts"].get(key)
        result["contracts"][key] = merge_single_contract(previous, contract)
        result["contracts"][key]["visual_contract_hash"] = stable_contract_hash(result["contracts"][key])
    return result


def merge_single_contract(previous: dict[str, Any] | None, incoming: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(previous, dict):
        return incoming
    merged = deepcopy(previous)
    for key in ("display_name", "source", "visibility", "confidence"):
        if incoming.get(key):
            merged[key] = incoming[key]
    for key in ("binding", "visual_identity", "render_intent", "style_constraints", "update_policy"):
        merged[key] = deep_merge_dict(merged.get(key), incoming.get(key))
    merged["negative_constraints"] = list(dict.fromkeys([
        *list_of_strings(merged.get("negative_constraints")),
        *list_of_strings(incoming.get("negative_constraints")),
    ]))
    return merged


def build_initial_visual_contract_candidates(
    campaign_id: str,
    profile: dict[str, Any],
    character_card: dict[str, Any],
    companion_config: dict[str, Any],
    initial_assets: dict[str, Any],
    campaign_taxonomy: dict[str, Any],
    v4_setup: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    style = campaign_taxonomy.get("visual_style") if isinstance(campaign_taxonomy.get("visual_style"), dict) else {}
    render_rules = profile.get("render_rules") if isinstance(profile.get("render_rules"), dict) else {}
    player_name = nested_text(character_card, ("identity", "name")) or "player"
    player_title = nested_text(character_card, ("identity", "title"))
    candidates.append({
        "entity_key": f"player:{safe_key(player_name)}",
        "entity_type": "player",
        "display_name": player_name,
        "source": "campaign_initialization",
        "memory_refs": ["player_state.json.character_card", "character_prompt.json"],
        "visual_identity": {
            "actor": {
                "identity_markers": list_of_strings([player_name, player_title, nested_text(character_card, ("identity", "summary"))]),
                "background": nested_text(character_card, ("profile", "background")),
                "personality": nested_text(character_card, ("profile", "personality")),
                "motivation": nested_text(character_card, ("profile", "motivation")),
            }
        },
        "render_intent": {"primary": "player_portrait", "details": {"portrait_asset_kind": "player_portrait"}},
        "style_constraints": {"campaign_visual_style": style, "render_rule": render_rules.get("player_portrait", {})},
        "negative_constraints": ["do not reuse companion silhouette", "do not use generic placeholder"],
        "update_policy": {"cache_policy": "stable", "rebuild_when": ["identity_changed", "visual_identity_changed"]},
    })
    companion_name = str(companion_config.get("companion_name") or nested_text(character_card, ("companion", "name")) or "").strip()
    if companion_name:
        candidates.append({
            "entity_key": f"companion:{safe_key(companion_name)}",
            "entity_type": "companion",
            "display_name": companion_name,
            "source": "campaign_initialization",
            "memory_refs": ["companion_profiles.json", "character_prompt.json.companion_card"],
            "visual_identity": {
                "actor": {
                    "role": companion_config.get("companion_role", ""),
                    "personality": companion_config.get("companion_personality", ""),
                    "relationship": nested_text(character_card, ("companion", "relationship_to_protagonist")),
                }
            },
            "render_intent": {"primary": "companion_portrait", "details": {"portrait_asset_kind": "companion_portrait"}},
            "style_constraints": {"campaign_visual_style": style, "render_rule": render_rules.get("companion_portrait", {})},
            "negative_constraints": ["do not reuse player face template", "do not draw as ordinary npc unless confirmed"],
            "update_policy": {"cache_policy": "stable", "rebuild_when": ["companion_profile_changed", "visual_identity_changed"]},
        })
    initial_map_canvas = initial_assets.get("initial_map_canvas") if isinstance(initial_assets.get("initial_map_canvas"), dict) else {}
    route = initial_map_canvas.get("map_route") if isinstance(initial_map_canvas.get("map_route"), dict) else {}
    draw_instructions = initial_map_canvas.get("canvas_draw_instructions") if isinstance(initial_map_canvas.get("canvas_draw_instructions"), dict) else {}
    if route.get("nodes") or draw_instructions.get("nodes"):
        title = str(route.get("title") or profile.get("title") or "opening_map")
        candidates.append({
            "entity_key": f"map:{safe_key(title)}",
            "entity_type": "map",
            "display_name": title,
            "source": "campaign_initialization",
            "memory_refs": ["campaign_profile.json.initial_assets.initial_map_canvas", "map_history.json"],
            "visual_identity": {
                "summary": draw_instructions.get("style") or "",
                "spatial": {"map_route": route, "canvas_draw_instructions": draw_instructions},
            },
            "render_intent": {"primary": "map_canvas", "details": {"usage": "regional_route_map"}},
            "style_constraints": {"campaign_visual_style": style, "render_rule": render_rules.get("map", {})},
            "negative_constraints": ["empty map", "generic default map", "protected franchise names"],
            "update_policy": {"cache_policy": "stable", "rebuild_when": ["map_route_changed", "canvas_draw_instructions_changed"]},
        })
    initial_cg = initial_assets.get("initial_cg") if isinstance(initial_assets.get("initial_cg"), dict) else {}
    cg_prompt = initial_cg.get("cg_prompt") if isinstance(initial_cg.get("cg_prompt"), dict) else {}
    if cg_prompt:
        candidates.append({
            "entity_key": f"cg:{safe_key(profile.get('title') or 'opening_cg')}",
            "entity_type": "cg",
            "display_name": f"{profile.get('title') or 'Opening'} CG",
            "source": "campaign_initialization",
            "memory_refs": ["campaign_profile.json.initial_assets.initial_cg", "image_profile.json"],
            "visual_identity": {
                "summary": initial_cg.get("generation_instruction") or "",
                "image_prompt": cg_prompt,
            },
            "render_intent": {"primary": "cg_image", "details": {"usage": "opening_cg"}},
            "style_constraints": {"campaign_visual_style": style, "render_rule": render_rules.get("cg", {})},
            "negative_constraints": ["map canvas data", "protected franchise names"],
            "update_policy": {"cache_policy": "stable", "rebuild_when": ["cg_prompt_changed"]},
        })
    item_rules = initial_assets.get("item_canvas_rules") if isinstance(initial_assets.get("item_canvas_rules"), dict) else {}
    for item in initial_assets.get("initial_items", []) if isinstance(initial_assets.get("initial_items"), list) else []:
        if not isinstance(item, dict):
            continue
        item_id = safe_key(item.get("id") or item.get("key") or item.get("name") or "item")
        name = str(item.get("name") or item.get("title") or item.get("label") or item_id)
        rule = item_rules.get(item_id) if isinstance(item_rules.get(item_id), dict) else {}
        candidates.append({
            "entity_key": f"item:{item_id}",
            "entity_type": "item",
            "display_name": name,
            "source": "campaign_initialization",
            "memory_refs": [f"equipment_history.json.initial_items.{item_id}"],
            "visual_identity": {
                "physical": {
                    "item_type": item.get("type") or item.get("category") or item.get("kind") or "",
                    "description": item.get("description") or item.get("detail") or "",
                    "stat": item.get("stat") if isinstance(item.get("stat"), dict) else {},
                    "canvas_rule": rule,
                }
            },
            "render_intent": {"primary": "item_icon", "details": {"usage": "inventory_or_gallery_icon"}},
            "style_constraints": {"campaign_visual_style": style, "render_rule": render_rules.get("item", {})},
            "negative_constraints": ["generic satchel unless item identity is unknown"],
            "update_policy": {"cache_policy": "stable", "rebuild_when": ["item_identity_changed", "visual_identity_changed"]},
        })
    if isinstance(v4_setup, dict):
        raw = v4_setup.get("visual_contract_candidates")
        if isinstance(raw, list):
            candidates.extend(raw)
    return candidates


def contract_public_payload(contracts: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(contracts, dict):
        return {}
    rows = contracts.get("contracts") if isinstance(contracts.get("contracts"), dict) else {}
    return {
        "schema": contracts.get("schema") or SCHEMA,
        "contracts": rows,
    }


def find_contract(contracts: dict[str, Any] | None, entity_key: str = "", entity_type: str = "", display_name: str = "") -> dict[str, Any]:
    rows = (contracts or {}).get("contracts") if isinstance((contracts or {}).get("contracts"), dict) else {}
    if entity_key and entity_key in rows:
        return rows[entity_key]
    expected = f"{safe_key(entity_type)}:{safe_key(display_name)}" if entity_type and display_name else ""
    if expected and expected in rows:
        return rows[expected]
    normalized_display = safe_key(display_name)
    for row in rows.values():
        if not isinstance(row, dict):
            continue
        if entity_type and row.get("entity_type") != entity_type:
            continue
        if normalized_display and safe_key(row.get("display_name")) == normalized_display:
            return row
    return {}


def visual_prompt_from_contract(contract: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(contract, dict) or not contract:
        return {}
    identity = contract.get("visual_identity") if isinstance(contract.get("visual_identity"), dict) else {}
    physical = identity.get("physical") if isinstance(identity.get("physical"), dict) else {}
    actor = identity.get("actor") if isinstance(identity.get("actor"), dict) else {}
    render = contract.get("render_intent") if isinstance(contract.get("render_intent"), dict) else {}
    style = contract.get("style_constraints") if isinstance(contract.get("style_constraints"), dict) else {}
    return {
        "archetype": physical.get("item_type") or render.get("primary") or contract.get("entity_type"),
        "source_text": " / ".join(list_of_strings([
            contract.get("display_name"),
            physical.get("description"),
            actor.get("role"),
            actor.get("relationship"),
            identity.get("summary"),
        ])),
        "canvas_style": physical.get("canvas_rule") if isinstance(physical.get("canvas_rule"), dict) else {},
        "style_constraints": style,
        "negative_constraints": list_of_strings(contract.get("negative_constraints")),
    }


def normalize_binding(binding: Any, campaign_id: str, memory_refs: Any = None) -> dict[str, Any]:
    data = deepcopy(binding) if isinstance(binding, dict) else {}
    data["campaign_id"] = campaign_id
    refs = list_of_strings(memory_refs if memory_refs is not None else data.get("memory_refs"))
    data["memory_refs"] = refs
    return data


def deep_merge_dict(base: Any, incoming: Any) -> dict[str, Any]:
    result = deepcopy(base) if isinstance(base, dict) else {}
    if not isinstance(incoming, dict):
        return result
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge_dict(result[key], value)
        elif value not in (None, "", [], {}):
            result[key] = deepcopy(value)
    return result


def object_or_empty(value: Any) -> dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def list_of_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        values = value
    else:
        values = [value]
    result: list[str] = []
    for item in values:
        if isinstance(item, dict):
            text = item.get("label") or item.get("name") or item.get("title") or item.get("id") or ""
        else:
            text = item
        text = str(text or "").strip()
        if text:
            result.append(text)
    return result


def safe_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", text)
    return text.strip("_")[:80] or "unknown"


def readable_from_key(entity_key: str) -> str:
    return entity_key.split(":", 1)[1] if ":" in entity_key else entity_key


def nested_text(data: dict[str, Any], path: tuple[str, ...]) -> str:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
    return str(current or "").strip()
