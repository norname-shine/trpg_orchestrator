from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from ..config import CAMPAIGNS_DIR
from ..json_utils import read_json, write_json
from .asset_rules import safe_segment


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


def save_gallery_raw(campaign_id: str, payload: Any) -> dict[str, Any]:
    resolved = safe_segment(campaign_id)
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
        for key in ("id", "type", "title"):
            required_asset_string(asset, key, index, prefix="gallery_assets")
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
    raw = load_gallery_raw(resolved)
    index_path = gallery_index_path(resolved)
    if index_path.exists():
        index = read_json(index_path)
    else:
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
        for key in ("id", "type", "title"):
            required_asset_string(asset, key, index)
    build_gallery_index(payload)
    # Keep this function validation-only. Do not normalize, infer, or backfill
    # asset business fields; gallery_raw is the director-authored source.


def required_asset_string(asset: dict[str, Any], key: str, index: int, prefix: str = "gallery_raw.assets") -> str:
    value = asset.get(key)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{prefix}[{index}] missing required fields: {key}")
    return value
