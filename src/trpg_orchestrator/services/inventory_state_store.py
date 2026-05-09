from __future__ import annotations

import copy
import time
from pathlib import Path
from typing import Any

from ..config import CAMPAIGNS_DIR
from ..json_utils import read_json, write_json
from .asset_rules import safe_segment


INVENTORY_STATE_SCHEMA = "trpg.inventory_state.v1"
INVENTORY_EVENTS_SCHEMA = "trpg.inventory_events.v1"


def inventory_extensions_dir(campaign_id: str) -> Path:
    return CAMPAIGNS_DIR / safe_segment(campaign_id) / "extensions"


def inventory_state_path(campaign_id: str) -> Path:
    return inventory_extensions_dir(campaign_id) / "inventory_state.json"


def inventory_events_path(campaign_id: str) -> Path:
    return inventory_extensions_dir(campaign_id) / "inventory_events.json"


def empty_inventory_state(campaign_id: str) -> dict[str, Any]:
    resolved = safe_segment(campaign_id)
    return {
        "schema": INVENTORY_STATE_SCHEMA,
        "campaign_id": resolved,
        "updated_turn": 0,
        "items": [],
    }


def empty_inventory_events(campaign_id: str) -> dict[str, Any]:
    resolved = safe_segment(campaign_id)
    return {
        "schema": INVENTORY_EVENTS_SCHEMA,
        "campaign_id": resolved,
        "events": [],
    }


def load_inventory_state(campaign_id: str) -> dict[str, Any]:
    resolved = safe_segment(campaign_id)
    path = inventory_state_path(resolved)
    if not path.exists():
        return empty_inventory_state(resolved)
    state = read_json(path)
    validate_inventory_state(resolved, state)
    return state


def load_inventory_events(campaign_id: str) -> dict[str, Any]:
    resolved = safe_segment(campaign_id)
    path = inventory_events_path(resolved)
    if not path.exists():
        return empty_inventory_events(resolved)
    events = read_json(path)
    validate_inventory_events(resolved, events)
    return events


def save_inventory_state(campaign_id: str, state: Any) -> dict[str, Any]:
    resolved = safe_segment(campaign_id)
    validate_inventory_state(resolved, state)
    path = inventory_state_path(resolved)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, state)
    return state


def save_inventory_events(campaign_id: str, events: Any) -> dict[str, Any]:
    resolved = safe_segment(campaign_id)
    validate_inventory_events(resolved, events)
    path = inventory_events_path(resolved)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, events)
    return events


def apply_inventory_payload(campaign_id: str, payload: Any) -> dict[str, Any]:
    resolved = safe_segment(campaign_id)
    current = load_inventory_state(resolved)
    change = classify_inventory_change(current, payload)
    next_state = copy.deepcopy(current)
    items = next_state["items"]
    action = change["action"]
    item_id = required_item_payload_id(payload)
    if action == "update_existing":
        index = change["index"]
        items[index] = merge_inventory_item(items[index], payload)
    else:
        items.append(new_inventory_item(payload))
    save_inventory_state(resolved, next_state)
    append_inventory_event(resolved, {
        "action": action,
        "item_id": item_id,
        "source_item_id": str(payload.get("source_item_id") or ""),
    })
    return inventory_response(resolved)


def classify_inventory_change(current_state: dict[str, Any], item_payload: Any) -> dict[str, Any]:
    if not isinstance(item_payload, dict):
        raise RuntimeError("inventory item payload must be object")
    item_id = required_item_payload_id(item_payload)
    required_item_payload_title(item_payload)
    campaign_id = str(current_state.get("campaign_id") or "")
    validate_inventory_state(campaign_id, current_state)
    by_id = inventory_item_index(current_state)
    if item_id in by_id:
        return {"action": "update_existing", "item_id": item_id, "index": by_id[item_id]}
    source_item_id = str(item_payload.get("source_item_id") or "").strip()
    if source_item_id:
        if source_item_id not in by_id:
            raise RuntimeError(f"source_item_id not found: {source_item_id}")
        return {"action": "create_derived", "item_id": item_id, "source_item_id": source_item_id}
    return {"action": "create_new", "item_id": item_id}


def append_inventory_event(campaign_id: str, event: Any) -> dict[str, Any]:
    if not isinstance(event, dict):
        raise RuntimeError("inventory event must be object")
    resolved = safe_segment(campaign_id)
    events = load_inventory_events(resolved)
    events["events"].append({
        **copy.deepcopy(event),
        "created_at": int(time.time()),
    })
    return save_inventory_events(resolved, events)


def inventory_response(campaign_id: str) -> dict[str, Any]:
    resolved = safe_segment(campaign_id)
    return {
        "ok": True,
        "campaign_id": resolved,
        "state": load_inventory_state(resolved),
        "events": load_inventory_events(resolved),
    }


def merge_inventory_item(existing: dict[str, Any], item_payload: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(existing)
    remove_fields = item_payload.get("remove_fields")
    if remove_fields is not None and not isinstance(remove_fields, list):
        raise RuntimeError("inventory item remove_fields must be list")
    for field in remove_fields or []:
        if field != "item_id":
            merged.pop(str(field), None)
    for key, value in item_payload.items():
        if key == "remove_fields":
            continue
        if key == "item_id":
            if value != merged.get("item_id"):
                raise RuntimeError("inventory item_id cannot be changed")
            continue
        if key in {"state", "payload"}:
            if not isinstance(value, dict):
                raise RuntimeError(f"inventory item {key} must be object")
            base = merged.get(key) if isinstance(merged.get(key), dict) else {}
            merged[key] = shallow_merge(base, value)
        else:
            merged[key] = copy.deepcopy(value)
    merged.setdefault("state", {})
    merged.setdefault("payload", {})
    validate_inventory_item(merged, -1)
    return merged


def new_inventory_item(item_payload: dict[str, Any]) -> dict[str, Any]:
    item = copy.deepcopy(item_payload)
    item.setdefault("state", {})
    item.setdefault("payload", {})
    item.pop("remove_fields", None)
    validate_inventory_item(item, -1)
    return item


def shallow_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in patch.items():
        merged[key] = copy.deepcopy(value)
    return merged


def validate_inventory_state(campaign_id: str, state: Any) -> None:
    if not isinstance(state, dict):
        raise RuntimeError("inventory_state payload must be object")
    if state.get("schema") != INVENTORY_STATE_SCHEMA:
        raise RuntimeError(f"inventory_state.schema must be {INVENTORY_STATE_SCHEMA}")
    if state.get("campaign_id") != campaign_id:
        raise RuntimeError("inventory_state.campaign_id does not match campaign_id")
    if not isinstance(state.get("items"), list):
        raise RuntimeError("inventory_state.items must be list")
    seen: set[str] = set()
    for index, item in enumerate(state["items"]):
        validate_inventory_item(item, index)
        item_id = item["item_id"]
        if item_id in seen:
            raise RuntimeError(f"duplicate inventory item_id: {item_id}")
        seen.add(item_id)


def validate_inventory_events(campaign_id: str, events: Any) -> None:
    if not isinstance(events, dict):
        raise RuntimeError("inventory_events payload must be object")
    if events.get("schema") != INVENTORY_EVENTS_SCHEMA:
        raise RuntimeError(f"inventory_events.schema must be {INVENTORY_EVENTS_SCHEMA}")
    if events.get("campaign_id") != campaign_id:
        raise RuntimeError("inventory_events.campaign_id does not match campaign_id")
    if not isinstance(events.get("events"), list):
        raise RuntimeError("inventory_events.events must be list")


def validate_inventory_item(item: Any, index: int) -> None:
    if not isinstance(item, dict):
        raise RuntimeError(f"inventory_state.items[{index}] must be object")
    for key in ("item_id", "title"):
        value = item.get(key)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"inventory item missing required field: {key}")
    for key in ("state", "payload"):
        if key not in item or not isinstance(item.get(key), dict):
            raise RuntimeError(f"inventory item {key} must be object")


def inventory_item_index(state: dict[str, Any]) -> dict[str, int]:
    by_id: dict[str, int] = {}
    for index, item in enumerate(state.get("items", [])):
        item_id = item.get("item_id") if isinstance(item, dict) else None
        if not isinstance(item_id, str) or not item_id.strip():
            raise RuntimeError("inventory item missing required field: item_id")
        if item_id in by_id:
            raise RuntimeError(f"duplicate inventory item_id: {item_id}")
        by_id[item_id] = index
    return by_id


def required_item_payload_id(item_payload: dict[str, Any]) -> str:
    value = item_payload.get("item_id")
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError("inventory item_id is required")
    return value.strip()


def required_item_payload_title(item_payload: dict[str, Any]) -> str:
    title = item_payload.get("title")
    if not isinstance(title, str) or not title.strip():
        raise RuntimeError("inventory item title is required")
    return title.strip()
