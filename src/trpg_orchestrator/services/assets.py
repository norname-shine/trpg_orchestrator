# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..json_utils import read_json, write_json


def _web_server():
    from .. import web_server

    return web_server


def asset_manifest_path(campaign_id: str) -> Path:
    ws = _web_server()
    return ws.CAMPAIGNS_DIR / ws.safe_segment(campaign_id) / "assets" / "manifest.json"


def campaign_asset_seed(campaign_id: str) -> str:
    ws = _web_server()
    root = ws.CAMPAIGNS_DIR / ws.safe_segment(campaign_id)
    profile_path = root / "campaign_profile.json"
    if profile_path.exists():
        try:
            profile = read_json(profile_path)
            if profile.get("asset_seed"):
                return str(profile["asset_seed"])
        except Exception:
            pass
    registry_path = ws.CAMPAIGNS_DIR / "campaign_registry.json"
    if registry_path.exists():
        try:
            registry = read_json(registry_path)
            seed = registry.get("campaigns", {}).get(campaign_id, {}).get("asset_seed")
            if seed:
                return str(seed)
        except Exception:
            pass
    return hashlib.sha256(f"trpg-assets:{campaign_id}".encode("utf-8")).hexdigest()[:16]


def load_asset_manifest(campaign_id: str) -> dict[str, Any]:
    path = asset_manifest_path(campaign_id)
    fallback = {"campaign_id": campaign_id, "asset_seed": campaign_asset_seed(campaign_id), "assets": {}}
    if not path.exists():
        return fallback
    try:
        data = read_json(path)
        if isinstance(data, dict):
            data.setdefault("campaign_id", campaign_id)
            data.setdefault("asset_seed", campaign_asset_seed(campaign_id))
            data.setdefault("assets", {})
            ws = _web_server()
            migrated = ws.migrateAssetKinds(data, ws.build_actor_identity_context(campaign_id))
            if migrated.get("_migration_changed"):
                migrated.pop("_migration_changed", None)
                write_asset_manifest(campaign_id, migrated)
                return migrated
            return data
    except Exception:
        pass
    return fallback


def write_asset_manifest(campaign_id: str, manifest: dict[str, Any]) -> None:
    data = manifest if isinstance(manifest, dict) else {}
    data.setdefault("campaign_id", campaign_id)
    data.setdefault("asset_seed", campaign_asset_seed(campaign_id))
    data.setdefault("assets", {})
    write_json(asset_manifest_path(campaign_id), data)


def scoped_asset_key(campaign_id: str, kind: str, object_id: Any, variant: str = "default", generator_version: int = 17) -> str:
    ws = _web_server()
    resolved = ws.safe_segment(campaign_id or ws.MemoryStore().resolve_campaign_id(None))
    seed = campaign_asset_seed(resolved)
    obj = ws.safe_segment(str(object_id or "unknown"))
    return f"{resolved}:{seed}:{ws.safe_segment(kind)}:{obj}:{ws.safe_segment(variant)}:v{generator_version}"


def normalize_asset_kind(kind: Any, metadata: dict[str, Any] | None = None, key: str = "") -> str:
    return _web_server()._normalize_asset_kind_impl(kind, metadata, key)


def infer_asset_role(asset: dict[str, Any]) -> str:
    return _web_server()._infer_asset_role_impl(asset)


def asset_list(campaign_id: str, kind: str = "") -> dict[str, Any]:
    return _web_server()._asset_list_impl(campaign_id, kind)


def asset_lookup(campaign_id: str, key: str) -> dict[str, Any]:
    return _web_server()._asset_lookup_impl(campaign_id, key)


def save_asset(payload: dict[str, Any]) -> dict[str, Any]:
    return _web_server()._save_asset_impl(payload)


def delete_asset(payload: dict[str, Any]) -> dict[str, Any]:
    return _web_server()._delete_asset_impl(payload)


def rebuild_assets(payload: dict[str, Any]) -> dict[str, Any]:
    return _web_server()._rebuild_assets_impl(payload)
