from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

from ..config import CAMPAIGNS_DIR
from ..json_utils import read_json, write_json
from .asset_rules import gallery_category_ids, safe_segment


RAW_GALLERY_SCHEMA = "trpg.gallery_raw.v2"
GALLERY_INDEX_SCHEMA = "trpg.gallery_index.v2"


def gallery_extensions_dir(campaign_id: str) -> Path:
    return CAMPAIGNS_DIR / safe_segment(campaign_id) / "extensions"


def gallery_raw_path(campaign_id: str) -> Path:
    return gallery_extensions_dir(campaign_id) / "gallery_raw.json"


def gallery_index_path(campaign_id: str) -> Path:
    return gallery_extensions_dir(campaign_id) / "gallery_index.json"


def empty_gallery_raw(campaign_id: str) -> dict[str, Any]:
    resolved = safe_segment(campaign_id)
    return {
        "schema": RAW_GALLERY_SCHEMA,
        "campaign_id": resolved,
        "updated_turn": 0,
        "assets": [],
    }


def load_gallery_raw(campaign_id: str) -> dict[str, Any]:
    path = gallery_raw_path(campaign_id)
    if not path.exists():
        return empty_gallery_raw(campaign_id)
    payload = read_json(path)
    validate_gallery_raw(safe_segment(campaign_id), payload)
    return payload


def _campaign_root(campaign_id: str) -> Path:
    return CAMPAIGNS_DIR / safe_segment(campaign_id)


def _normalized_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip()).casefold()


def _json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = read_json(path)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _protected_actor_catalog(campaign_id: str) -> tuple[set[str], set[str]]:
    root = _campaign_root(campaign_id)
    protected_types = {"player", "protagonist", "main_player", "main_character", "companion", "sub_player", "subplayer", "secondary_player"}
    protected_keys: set[str] = set()
    protected_names: set[str] = set()

    def add_name(value: Any) -> None:
        normalized = _normalized_text(value)
        if normalized:
            protected_names.add(normalized)

    def add_key(value: Any) -> None:
        normalized = _normalized_text(value)
        if normalized:
            protected_keys.add(normalized)

    visual_contracts = _json_object(root / "visual_contracts.json")
    contracts = visual_contracts.get("contracts") if isinstance(visual_contracts.get("contracts"), dict) else visual_contracts
    for key, row in contracts.items() if isinstance(contracts, dict) else []:
        if not isinstance(row, dict):
            continue
        role_text = " ".join(str(row.get(field) or "") for field in ("entity_type", "actor_role", "role", "runtime_role"))
        if not any(item in role_text.casefold() for item in protected_types):
            continue
        add_key(key)
        add_key(row.get("entity_key"))
        for field in ("display_name", "name", "title", "character_name"):
            add_name(row.get(field))

    profile = _json_object(root / "campaign_profile.json")
    for field in ("protagonist_name", "player_name", "main_player_name"):
        add_name(profile.get(field))
    card = profile.get("character_card") if isinstance(profile.get("character_card"), dict) else {}
    identity = card.get("identity") if isinstance(card.get("identity"), dict) else {}
    add_name(identity.get("name"))
    companion = profile.get("companion_config") if isinstance(profile.get("companion_config"), dict) else {}
    for field in ("name", "companion_name", "display_name"):
        add_name(companion.get(field))

    player_state = _json_object(root / "player_state.json")
    for field in ("name", "player_name", "protagonist_name", "display_name"):
        add_name(player_state.get(field))
    player_card = player_state.get("character_card") if isinstance(player_state.get("character_card"), dict) else {}
    player_identity = player_card.get("identity") if isinstance(player_card.get("identity"), dict) else {}
    add_name(player_identity.get("name"))

    return protected_keys, protected_names


def _is_protected_actor_asset(campaign_id: str, asset: dict[str, Any]) -> bool:
    protected_keys, protected_names = _protected_actor_catalog(campaign_id)
    if not protected_keys and not protected_names:
        return False
    protected_types = {"player", "protagonist", "main_player", "main_character", "companion", "sub_player", "subplayer", "secondary_player"}
    asset_role_text = " ".join(str(asset.get(field) or "") for field in ("type", "entity_type", "actor_role", "role", "runtime_role"))
    if any(item in asset_role_text.casefold() for item in protected_types):
        return True
    for field in ("id", "entity_key", "subject_key", "avatar_key"):
        if _normalized_text(asset.get(field)) in protected_keys:
            return True
    title = _normalized_text(asset.get("title") or asset.get("display_name") or asset.get("name"))
    if not title:
        return False
    return any(name == title or (len(name) >= 2 and name in title) for name in protected_names)


def sanitize_gallery_raw_payload(campaign_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = copy.deepcopy(payload)
    assets = sanitized.get("assets")
    if not isinstance(assets, list):
        return sanitized
    sanitized["assets"] = [
        asset
        for asset in assets
        if not (isinstance(asset, dict) and _is_protected_actor_asset(campaign_id, asset))
    ]
    return sanitized


def save_gallery_raw(campaign_id: str, payload: Any) -> dict[str, Any]:
    resolved = safe_segment(campaign_id)
    if isinstance(payload, dict):
        payload = sanitize_gallery_raw_payload(resolved, payload)
    validate_gallery_raw(resolved, payload)
    raw_path = gallery_raw_path(resolved)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(raw_path, payload)
    index = build_gallery_index(payload)
    write_json(gallery_index_path(resolved), index)
    return payload


def apply_gallery_assets(campaign_id: str, assets: Any) -> dict[str, Any]:
    if not isinstance(assets, list):
        raise RuntimeError("gallery_assets must be list")
    incoming: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            raise RuntimeError(f"gallery_assets[{index}] must be object")
        for key in ("id", "type", "title", "gallery_category"):
            required_asset_string(asset, key, index, prefix="gallery_assets")
        validate_gallery_category(campaign_id, asset.get("gallery_category"), index, prefix="gallery_assets")
        validate_gallery_categories(campaign_id, asset.get("gallery_categories"), asset.get("gallery_category"), index, prefix="gallery_assets")
        validate_gallery_asset_type(asset.get("type"), index, prefix="gallery_assets")
        asset_id = str(asset.get("id") or "").strip()
        if asset_id in seen:
            raise RuntimeError(f"duplicate gallery_assets id: {asset_id}")
        seen.add(asset_id)
        incoming.append(copy.deepcopy(asset))

    raw = load_gallery_raw(campaign_id)
    next_assets = [copy.deepcopy(asset) for asset in raw.get("assets", [])]
    by_id = {str(asset.get("id") or ""): index for index, asset in enumerate(next_assets) if isinstance(asset, dict)}
    for asset in incoming:
        asset_id = str(asset["id"]).strip()
        if asset_id in by_id:
            next_assets[by_id[asset_id]] = asset
        else:
            by_id[asset_id] = len(next_assets)
            next_assets.append(asset)
    raw["assets"] = next_assets
    return save_gallery_raw(campaign_id, raw)


def build_gallery_index(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise RuntimeError("gallery_raw payload must be object")
    campaign_id = str(payload.get("campaign_id") or "")
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise RuntimeError("gallery_raw.assets must be list")
    by_id: dict[str, int] = {}
    by_type: dict[str, list[str]] = {}
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            raise RuntimeError(f"gallery_raw.assets[{index}] must be object")
        asset_id = required_asset_string(asset, "id", index)
        asset_type = required_asset_string(asset, "type", index)
        if asset_id in by_id:
            raise RuntimeError(f"duplicate gallery_raw asset id: {asset_id}")
        by_id[asset_id] = index
        by_type.setdefault(asset_type, []).append(asset_id)
    return {
        "schema": GALLERY_INDEX_SCHEMA,
        "campaign_id": campaign_id,
        "by_id": by_id,
        "by_type": by_type,
    }


def gallery_response(campaign_id: str) -> dict[str, Any]:
    resolved = safe_segment(campaign_id)
    raw = sanitize_gallery_raw_payload(resolved, load_gallery_raw(resolved))
    index = build_gallery_index(raw)
    return {
        "ok": True,
        "campaign_id": resolved,
        "raw": raw,
        "index": index,
    }


def validate_gallery_raw(campaign_id: str, payload: Any) -> None:
    if not isinstance(payload, dict):
        raise RuntimeError("gallery_raw payload must be object")
    if payload.get("schema") != RAW_GALLERY_SCHEMA:
        raise RuntimeError(f"gallery_raw.schema must be {RAW_GALLERY_SCHEMA}")
    if payload.get("campaign_id") != campaign_id:
        raise RuntimeError("gallery_raw.campaign_id does not match campaign_id")
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise RuntimeError("gallery_raw.assets must be list")
    if not assets:
        raise RuntimeError("gallery_raw.assets must contain at least one asset")
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            raise RuntimeError(f"gallery_raw.assets[{index}] must be object")
        for key in ("id", "type", "title", "gallery_category"):
            required_asset_string(asset, key, index)
        validate_gallery_category(campaign_id, asset.get("gallery_category"), index)
        validate_gallery_categories(campaign_id, asset.get("gallery_categories"), asset.get("gallery_category"), index)
        validate_gallery_asset_type(asset.get("type"), index)
        validate_gallery_canvas_spec_scope(asset, index)
    build_gallery_index(payload)
    # Keep this function validation-only. Do not normalize, infer, or backfill
    # asset business fields; gallery_raw is the director-authored source.


def required_asset_string(asset: dict[str, Any], key: str, index: int, prefix: str = "gallery_raw.assets") -> str:
    value = asset.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{prefix}[{index}] missing required fields: {key}")
    return value


def validate_gallery_category(campaign_id: str, value: Any, index: int, prefix: str = "gallery_raw.assets") -> str:
    category = str(value or "").strip()
    allowed = gallery_category_ids(campaign_id)
    allowed_by_key = {item.casefold(): item for item in allowed}
    if category.casefold() not in allowed_by_key:
        raise RuntimeError(f"{prefix}[{index}] invalid gallery_category: {category or '<empty>'}")
    return allowed_by_key[category.casefold()]


def validate_gallery_categories(campaign_id: str, value: Any, primary: Any, index: int, prefix: str = "gallery_raw.assets") -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise RuntimeError(f"{prefix}[{index}] gallery_categories must be list")
    allowed = gallery_category_ids(campaign_id)
    allowed_by_key = {item.casefold(): item for item in allowed}
    categories: list[str] = []
    seen: set[str] = set()
    for raw in value:
        category = str(raw or "").strip()
        if category.casefold() not in allowed_by_key:
            raise RuntimeError(f"{prefix}[{index}] invalid gallery_categories item: {category or '<empty>'}")
        resolved = allowed_by_key[category.casefold()]
        if resolved in seen:
            raise RuntimeError(f"{prefix}[{index}] duplicate gallery_categories item: {resolved}")
        seen.add(resolved)
        categories.append(resolved)
    primary_category = validate_gallery_category(campaign_id, primary, index, prefix=prefix)
    if primary_category not in categories:
        raise RuntimeError(f"{prefix}[{index}] gallery_categories must include gallery_category")
    return categories


def validate_gallery_asset_type(value: Any, index: int, prefix: str = "gallery_raw.assets") -> str:
    asset_type = str(value or "").strip()
    if asset_type.lower() in {"item_record", "inventory_record"}:
        raise RuntimeError(f"{prefix}[{index}] invalid type: {asset_type}; use item or prop with gallery_category")
    return asset_type


def validate_gallery_canvas_spec_scope(asset: dict[str, Any], index: int, prefix: str = "gallery_raw.assets") -> None:
    if not isinstance(asset.get("canvas_spec"), dict):
        return
    asset_type = str(asset.get("type") or "").strip().lower()
    category = str(asset.get("gallery_category") or "").strip().lower()
    if asset_type in {"character", "npc", "monster", "portrait", "cg"} or category in {"character", "cg"}:
        raise RuntimeError(f"{prefix}[{index}] canvas_spec is not allowed for character or cg assets")
