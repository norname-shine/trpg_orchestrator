from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..config import CAMPAIGNS_DIR, PROJECT_ROOT
from ..json_utils import read_json, write_json


CONTRACT_PATH = PROJECT_ROOT / "src" / "trpg_orchestrator" / "contracts" / "asset_contract.json"

ASSET_USE_TO_KIND = {
    "portrait": "character_portrait",
    "item": "item_icon",
    "prop": "prop_icon",
    "map": "map_image",
    "cg": "cg_image",
}


def safe_segment(value: Any) -> str:
    cleaned = "".join(ch if (ch.isalnum() or ch in "_.-") else "_" for ch in str(value or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.strip("._") or "asset"


def load_asset_contract() -> dict[str, Any]:
    data = read_json(CONTRACT_PATH)
    if not isinstance(data, dict):
        raise RuntimeError("asset_contract.json must contain an object")
    return data


def core_gallery_categories() -> list[dict[str, Any]]:
    rows = load_asset_contract().get("core_gallery_categories", [])
    return [dict(row) for row in rows if isinstance(row, dict) and row.get("id")]


def core_gallery_category_ids() -> set[str]:
    return {str(row.get("id") or "") for row in core_gallery_categories()}


def default_asset_presentation() -> dict[str, Any]:
    return {"custom_gallery_categories": []}


def asset_presentation_path(campaign_id: str) -> Path:
    return CAMPAIGNS_DIR / safe_segment(campaign_id) / "asset_presentation.json"


def validate_custom_gallery_categories(rows: Any) -> tuple[list[dict[str, str]], list[str]]:
    contract = load_asset_contract()
    max_rows = int(contract.get("max_custom_gallery_categories") or 3)
    blocked = core_gallery_category_ids() | {"all", "hidden", "player", "companion", "scene"}
    warnings: list[str] = []
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    if not isinstance(rows, list):
        return [], ["custom_gallery_categories must be a list"]
    if len(rows) > max_rows:
        warnings.append(f"custom_gallery_categories may contain at most {max_rows} rows")
    for row in rows:
        if len(normalized) >= max_rows:
            break
        if not isinstance(row, dict):
            warnings.append("custom_gallery_categories row must be an object")
            continue
        if "maps_to" in row:
            warnings.append("custom_gallery_categories must not use maps_to")
            continue
        category_id = safe_segment(str(row.get("id") or ""))
        category_key = category_id.casefold()
        if not category_id or category_key in blocked or category_key in seen:
            warnings.append(f"invalid custom gallery category id: {category_id or '<empty>'}")
            continue
        seen.add(category_key)
        normalized.append({
            "id": category_id,
            "label": str(row.get("label") or category_id).strip() or category_id,
            "source": "campaign",
        })
    return normalized, warnings


def ensure_asset_presentation(campaign_id: str) -> dict[str, Any]:
    path = asset_presentation_path(campaign_id)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, default_asset_presentation())
        return default_asset_presentation()
    data = read_json(path)
    if not isinstance(data, dict):
        data = default_asset_presentation()
    rows, warnings = validate_custom_gallery_categories(data.get("custom_gallery_categories", []))
    result = {"custom_gallery_categories": rows}
    if warnings:
        result["warnings"] = warnings
    if result != data:
        write_json(path, result)
    return result


def campaign_gallery_categories(campaign_id: str) -> list[dict[str, Any]]:
    presentation = ensure_asset_presentation(campaign_id)
    return core_gallery_categories() + [
        dict(row) for row in presentation.get("custom_gallery_categories", [])
        if isinstance(row, dict) and row.get("id")
    ]


def gallery_category_ids(campaign_id: str) -> set[str]:
    return {str(row.get("id") or "") for row in campaign_gallery_categories(campaign_id)}


def asset_kind_for_use(asset_use: str) -> str:
    return ASSET_USE_TO_KIND.get(str(asset_use or "").strip().lower(), "")


def asset_contract_payload(campaign_id: str = "") -> dict[str, Any]:
    contract = load_asset_contract()
    presentation = ensure_asset_presentation(campaign_id) if campaign_id else default_asset_presentation()
    return {
        "core_gallery_categories": core_gallery_categories(),
        "custom_gallery_categories": presentation.get("custom_gallery_categories", []),
        "max_custom_gallery_categories": int(contract.get("max_custom_gallery_categories") or 3),
    }
