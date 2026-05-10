from __future__ import annotations

from typing import Any

from .asset_rules import ASSET_USE_TO_KIND, gallery_category_ids, load_asset_contract


REQUIRED_FIELDS = [
    "kind",
    "id",
    "title",
    "gallery_category",
    "asset_use",
    "certainty",
    "display_zone",
    "cache_policy",
]


def asset_contract_error(
    asset_id: str,
    missing_fields: list[str] | None = None,
    invalid_fields: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(invalid_fields, dict) and extra is None:
        legacy_extra = invalid_fields
        legacy_invalid = legacy_extra.get("invalid_fields")
        extra = legacy_extra
        invalid_fields = legacy_invalid if isinstance(legacy_invalid, list) else None
        if invalid_fields and list(missing_fields or []) == invalid_fields:
            missing_fields = []
    payload: dict[str, Any] = {
        "ok": False,
        "error_type": "asset_contract_error",
        "asset_id": asset_id,
        "missing_fields": list(missing_fields or []),
        "invalid_fields": list(invalid_fields or []),
        "repair_instruction": {
            "required_fields": list(REQUIRED_FIELDS),
        },
    }
    if extra:
        payload.update(extra)
    return payload


def route_to_image_job(asset_id: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error_type": "route_to",
        "route_to": "image_job",
        "asset_id": asset_id,
    }


def normalize_regular_asset(payload: dict[str, Any], campaign_id: str) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    asset_id = str(payload.get("id") or payload.get("key") or "").strip()
    raw_kind = str(payload.get("kind") or "").strip().lower()
    asset_use = str(payload.get("asset_use") or "").strip().lower()
    if raw_kind == "cg" or asset_use == "cg":
        return route_to_image_job(asset_id)

    missing = [field for field in REQUIRED_FIELDS if not str(payload.get(field) or "").strip()]
    if asset_use == "portrait" and not str(payload.get("actor_role") or "").strip():
        missing.append("actor_role")
    if missing:
        return asset_contract_error(asset_id, missing)

    contract = load_asset_contract()
    allowed_uses = {"portrait", "item", "prop", "map"}
    allowed_categories = gallery_category_ids(campaign_id)
    allowed_certainty = {str(item) for item in contract.get("certainty_values", [])}
    allowed_zones = {str(item) for item in contract.get("display_zones", [])}
    allowed_policies = {str(item) for item in contract.get("cache_policies", [])}
    allowed_roles = {str(item) for item in contract.get("actor_roles", [])}
    allowed_sources = {str(item) for item in contract.get("source_types", [])}

    gallery_category = str(payload.get("gallery_category") or "").strip().lower()
    certainty = str(payload.get("certainty") or "").strip().lower()
    display_zone = str(payload.get("display_zone") or "").strip().lower()
    cache_policy = str(payload.get("cache_policy") or "").strip().lower()
    actor_role = str(payload.get("actor_role") or "unknown").strip().lower()

    invalid: list[str] = []
    if gallery_category not in allowed_categories:
        invalid.append("gallery_category")
    if asset_use not in allowed_uses:
        invalid.append("asset_use")
    if certainty not in allowed_certainty:
        invalid.append("certainty")
    if display_zone not in allowed_zones:
        invalid.append("display_zone")
    if cache_policy not in allowed_policies:
        invalid.append("cache_policy")
    if asset_use == "portrait" and actor_role not in allowed_roles:
        invalid.append("actor_role")
    source_type = str(payload.get("source_type") or "image_api").strip() or "image_api"
    if source_type not in allowed_sources:
        invalid.append("source_type")
    asset_tags = payload.get("asset_tags", [])
    if not isinstance(asset_tags, list) or any(not isinstance(item, str) for item in asset_tags):
        invalid.append("asset_tags")
    if invalid:
        return asset_contract_error(asset_id, invalid_fields=invalid)

    asset_kind = ASSET_USE_TO_KIND[asset_use]
    return {
        "ok": True,
        "normalized": {
            "id": asset_id,
            "title": str(payload.get("title") or "").strip(),
            "asset_kind": asset_kind,
            "asset_use": asset_use,
            "gallery_category": gallery_category,
            "display_zone": display_zone,
            "actor_role": actor_role,
            "asset_subtype": str(payload.get("asset_subtype") or "").strip(),
            "asset_tags": [item.strip() for item in asset_tags if item.strip()],
            "subject_key": str(payload.get("subject_key") or "").strip(),
            "display_name": str(payload.get("display_name") or payload.get("title") or "").strip(),
            "certainty": certainty,
            "cache_policy": cache_policy,
            "source_type": source_type,
            "is_placeholder": False,
            "detail": str(payload.get("detail") or "").strip(),
            "visual_contract_key": str(payload.get("visual_contract_key") or "").strip(),
            "visual_contract_hash": str(payload.get("visual_contract_hash") or "").strip(),
        },
    }
