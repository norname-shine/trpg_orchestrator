# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import hashlib
import time
from pathlib import Path
from typing import Any

from ..json_utils import read_json, write_json


def _web_server():
    from .. import web_server

    return web_server


ROLE_PRIORITY = {
    "player": 10,
    "companion": 20,
    "master": 30,
    "npc": 40,
    "item": 50,
    "scene": 60,
}

ROLE_ASSET_KIND = {
    "player": "player_portrait",
    "companion": "companion_portrait",
    "master": "master_portrait",
    "npc": "npc_portrait",
    "key_character": "npc_portrait",
    "item": "item_icon",
    "prop": "item_icon",
    "scene": "scene_image",
    "map": "map_image",
    "monster": "monster_image",
    "cg": "cg_image",
}

GALLERY_VISIBLE_KINDS = {
    "companion_portrait",
    "master_portrait",
    "npc_portrait",
    "item_icon",
    "scene_image",
    "map_image",
    "monster_image",
    "cg_image",
    "gallery_image",
}


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
    raw = str(kind or "").lower()
    metadata = metadata or {}
    if "attribute_star" in raw or "attribute_star" in str(key).lower():
        return "attribute_star"
    role = infer_asset_role({"kind": raw, "key": key, "metadata": metadata})
    if role in ROLE_ASSET_KIND:
        return ROLE_ASSET_KIND[role]
    if raw in ROLE_ASSET_KIND.values():
        return raw
    if raw in {"portrait"}:
        return "player_portrait"
    if raw in {"companion"}:
        return "companion_portrait"
    if raw in {"npc", "character"} or "npc" in raw:
        return "npc_portrait"
    if raw in {"item", "weapon", "supply", "material", "ritual_tool", "equipment", "document", "clue"}:
        return "item_icon"
    if raw in {"prop", "tool", "anomaly", "quest"}:
        return "item_icon"
    if raw in {"scene", "location"}:
        return "scene_image"
    if raw == "map" or "gallery_map" in raw:
        return "map_image"
    if "monster" in raw or "ecology" in raw:
        return "monster_image"
    if "cg" in raw or "gallery_image" in raw or "formal_cg" in raw:
        return "cg_image" if "cg" in raw else "gallery_image"
    return raw


def infer_asset_role(asset: dict[str, Any]) -> str:
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    explicit = str(metadata.get("role") or metadata.get("entity_role") or asset.get("role") or "").lower()
    if explicit in ROLE_PRIORITY:
        return explicit
    entity_key = str(metadata.get("entity_key") or asset.get("entity_key") or "")
    if ":" in entity_key:
        prefix = entity_key.split(":", 1)[0].lower()
        if prefix in ROLE_PRIORITY:
            return prefix
    text = " ".join(
        str(value or "")
        for value in (
            asset.get("kind"),
            asset.get("key"),
            metadata.get("kind"),
            metadata.get("title"),
            metadata.get("display_name"),
            metadata.get("detail"),
            metadata.get("object_id"),
        )
    ).lower()
    if any(token in text for token in ("companion", "浼欎即", "鍚岃")):
        return "companion"
    if any(token in text for token in ("master", "寰′富")):
        return "master"
    kind = str(asset.get("kind") or "").lower()
    if "attribute_star" in kind or "attribute_star" in str(asset.get("key") or "").lower():
        return ""
    if kind in {"portrait", "player_portrait"}:
        return "player"
    if kind in {"item", "item_icon", "weapon", "supply", "material", "ritual_tool", "equipment"}:
        return "item"
    if kind in {"map", "map_image"}:
        return "map"
    if kind in {"scene", "scene_image", "location"}:
        return "scene"
    if "monster" in kind:
        return "monster"
    if "cg" in kind:
        return "cg"
    if "npc" in kind or "portrait" in kind:
        return "npc"
    return ""


def asset_display_name(asset: dict[str, Any]) -> str:
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    return str(
        metadata.get("display_name")
        or metadata.get("title")
        or asset.get("display_name")
        or asset.get("title")
        or ""
    ).strip()


def entity_key_for_asset(asset: dict[str, Any]) -> str:
    metadata = asset.get("metadata") if isinstance(asset.get("metadata"), dict) else {}
    existing = str(metadata.get("entity_key") or asset.get("entity_key") or "").strip()
    if existing:
        return existing
    role = infer_asset_role(asset) or "item"
    name = asset_display_name(asset) or metadata.get("object_id") or asset.get("key") or role
    return f"{role}:{_web_server().safe_segment(str(name).lower())}"


def _safe_asset_read_path(campaign_id: str, rel_path: str) -> Path:
    ws = _web_server()
    if not rel_path:
        raise RuntimeError("asset path is empty")
    root = (ws.CAMPAIGNS_DIR / ws.safe_segment(campaign_id) / "assets").resolve()
    target = (ws.CAMPAIGNS_DIR / ws.safe_segment(campaign_id) / rel_path).resolve()
    if root not in target.parents and target != root:
        raise RuntimeError("asset path escapes campaign assets")
    if target.suffix.lower() != ".png":
        raise RuntimeError("only PNG assets are readable")
    return target


def _safe_asset_target(campaign_id: str, rel_path: str) -> Path:
    ws = _web_server()
    if not rel_path:
        raise RuntimeError("asset path is empty")
    root = (ws.CAMPAIGNS_DIR / ws.safe_segment(campaign_id) / "assets").resolve()
    target = (ws.CAMPAIGNS_DIR / ws.safe_segment(campaign_id) / rel_path).resolve()
    if root not in target.parents and target != root:
        raise RuntimeError("asset path escapes campaign assets")
    if target.suffix.lower() != ".png":
        raise RuntimeError("only PNG assets can be removed")
    return target


def _normalized_asset_entry(campaign_id: str, key: str, entry: dict[str, Any]) -> dict[str, Any]:
    ws = _web_server()
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    normalized = {**entry, "key": str(entry.get("key") or key), "metadata": metadata}
    role = infer_asset_role(normalized)
    kind = normalize_asset_kind(entry.get("kind", ""), metadata, key)
    entity_key = str(metadata.get("entity_key") or entry.get("entity_key") or entity_key_for_asset({**normalized, "kind": kind}))
    display_name = asset_display_name({**normalized, "kind": kind})
    visible = entry.get("visible_in_gallery", metadata.get("visible_in_gallery", True))
    debug_only = bool(entry.get("debug_only") or metadata.get("debug_only"))
    runtime_role = str(metadata.get("runtime_role") or role or "").lower()
    gallery_category = str(metadata.get("gallery_category") or ws.normalize_frontend_gallery_kind(kind) or "").lower()
    not_in_filters = bool(metadata.get("not_in_gallery_filters") or entry.get("not_in_gallery_filters"))
    if runtime_role in {"player", "companion"} or gallery_category == "hidden" or not_in_filters:
        visible = False
    return {
        **entry,
        "campaign_id": str(entry.get("campaign_id") or campaign_id),
        "asset_seed": str(entry.get("asset_seed") or campaign_asset_seed(campaign_id)),
        "key": str(entry.get("key") or key),
        "kind": kind,
        "role": role,
        "runtime_role": runtime_role,
        "entity_key": entity_key,
        "display_name": display_name,
        "visible_in_gallery": bool(visible) and not debug_only,
        "gallery_category": gallery_category,
        "not_in_gallery_filters": not_in_filters,
        "portrait_asset_kind": str(metadata.get("portrait_asset_kind") or kind),
        "render_tier": str(metadata.get("render_tier") or ""),
        "debug_only": debug_only,
        "metadata": {
            **metadata,
            "role": metadata.get("role") or role,
            "runtime_role": runtime_role or metadata.get("role") or role,
            "entity_key": entity_key,
            "display_name": metadata.get("display_name") or display_name,
            "visible_in_gallery": bool(visible) and not debug_only,
            "gallery_category": gallery_category,
            "not_in_gallery_filters": not_in_filters,
            "portrait_asset_kind": metadata.get("portrait_asset_kind") or kind,
            "render_tier": metadata.get("render_tier") or "",
            "debug_only": debug_only,
        },
    }


def _asset_entry_payload(campaign_id: str, key: str, entry: dict[str, Any]) -> dict[str, Any]:
    entry = _normalized_asset_entry(campaign_id, key, entry)
    if entry.get("placeholder") or entry.get("metadata", {}).get("placeholder"):
        return {}
    rel_path = str(entry.get("path", ""))
    try:
        full = _safe_asset_read_path(campaign_id, rel_path)
    except Exception:
        full = Path()
    url_path = rel_path.replace("\\", "/")
    if url_path.startswith("assets/"):
        url_path = url_path[len("assets/"):]
    return {
        "campaign_id": campaign_id,
        "asset_seed": entry.get("asset_seed") or campaign_asset_seed(campaign_id),
        "key": key,
        "kind": entry.get("kind", ""),
        "path": rel_path,
        "exists": bool(rel_path and full.exists()),
        "url": f"/campaign-assets/{_web_server().safe_segment(campaign_id)}/{url_path}" if rel_path else "",
        "generator_version": entry.get("generator_version", 1),
        "metadata": entry.get("metadata", {}),
        "entity_key": entry.get("entity_key", ""),
        "role": entry.get("role", ""),
        "display_name": entry.get("display_name", ""),
        "visible_in_gallery": entry.get("visible_in_gallery", True),
        "debug_only": entry.get("debug_only", False),
        **entry,
    }


def asset_lookup(campaign_id: str, key: str) -> dict[str, Any]:
    ws = _web_server()
    if not campaign_id:
        campaign_id = ws.MemoryStore().resolve_campaign_id(None)
    if not key:
        raise RuntimeError("asset key is required")
    manifest = load_asset_manifest(campaign_id)
    entry = manifest.get("assets", {}).get(key)
    if not entry:
        return {"ok": True, "exists": False}
    if str(entry.get("campaign_id") or campaign_id) != campaign_id:
        return {"ok": True, "exists": False}
    rel_path = str(entry.get("path", ""))
    try:
        full = _safe_asset_read_path(campaign_id, rel_path)
    except Exception:
        return {"ok": True, "exists": False}
    if not rel_path or not full.exists():
        return {"ok": True, "exists": False}
    url_path = rel_path.replace("\\", "/")
    if url_path.startswith("assets/"):
        url_path = url_path[len("assets/"):]
    return {
        "ok": True,
        "exists": True,
        "key": key,
        "entry": _normalized_asset_entry(campaign_id, key, entry),
        "url": f"/campaign-assets/{ws.safe_segment(campaign_id)}/{url_path}",
    }


def asset_list(campaign_id: str, kind: str = "") -> dict[str, Any]:
    ws = _web_server()
    if not campaign_id:
        campaign_id = ws.MemoryStore().resolve_campaign_id(None)
    manifest = load_asset_manifest(campaign_id)
    entries = []
    for key, entry in manifest.get("assets", {}).items():
        if not isinstance(entry, dict):
            continue
        normalized = _normalized_asset_entry(campaign_id, key, entry)
        if normalized.get("campaign_id") != campaign_id:
            continue
        if normalized.get("placeholder") or normalized.get("metadata", {}).get("placeholder"):
            continue
        if ws.is_attribute_star_asset(normalized):
            continue
        if normalize_asset_kind(normalized.get("kind"), normalized.get("metadata", {}), normalized.get("key", "")) == "map_image" and not ws.is_valid_cached_map_asset(normalized):
            continue
        if kind and str(entry.get("kind", "")) != kind:
            continue
        payload = _asset_entry_payload(campaign_id, key, normalized)
        if payload:
            entries.append(payload)
    entries.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return {"ok": True, "campaign_id": campaign_id, "assets": entries}


def _is_placeholder_asset_payload(payload: dict[str, Any], metadata: dict[str, Any]) -> bool:
    text = " ".join(str(payload.get(name, "")) for name in ("key", "kind", "seed", "filename", "style"))
    text = f"{text} {metadata.get('title', '')} {metadata.get('source', '')} {metadata.get('status', '')}".lower()
    if payload.get("placeholder") or metadata.get("placeholder") or metadata.get("fallback"):
        return True
    if metadata.get("cache_policy") == "placeholder":
        return True
    if any(token in text for token in ("placeholder", "fallback", "default_trpg", "empty_map", "base_map")):
        return True
    route = metadata.get("map_route")
    if str(payload.get("kind") or "") == "map" and isinstance(route, dict) and not route.get("nodes"):
        return True
    return False


def save_asset(payload: dict[str, Any]) -> dict[str, Any]:
    ws = _web_server()
    campaign_id = str(payload.get("campaign_id") or "").strip() or ws.MemoryStore().resolve_campaign_id(None)
    key = str(payload.get("key") or "").strip()
    if not key:
        raise RuntimeError("asset key is required")
    asset_seed = str(payload.get("asset_seed") or campaign_asset_seed(campaign_id))
    if campaign_id not in key:
        raise RuntimeError("asset key must include campaign_id")
    if asset_seed and asset_seed not in key:
        raise RuntimeError("asset key must include asset_seed")
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    if _is_placeholder_asset_payload(payload, metadata):
        raise RuntimeError("placeholder assets must not be saved")
    data_url = str(payload.get("data_url") or "")
    prefix = "data:image/png;base64,"
    if not data_url.startswith(prefix):
        raise RuntimeError("asset data_url must be a PNG data URL")
    raw = base64.b64decode(data_url[len(prefix):], validate=True)
    if len(raw) < 128:
        raise RuntimeError("empty PNG assets must not be saved")
    subdir = ws.safe_segment(str(payload.get("subdir") or payload.get("kind") or "misc"))
    filename = ws.safe_segment(str(payload.get("filename") or key)) + ".png"
    rel_path = Path("assets") / subdir / filename
    root = ws.CAMPAIGNS_DIR / ws.safe_segment(campaign_id)
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)

    manifest = load_asset_manifest(campaign_id)
    manifest.setdefault("campaign_id", campaign_id)
    manifest.setdefault("asset_seed", campaign_asset_seed(campaign_id))
    manifest.setdefault("assets", {})[key] = {
        "campaign_id": campaign_id,
        "key": key,
        "path": rel_path.as_posix(),
        "kind": str(payload.get("kind") or subdir),
        "seed": str(payload.get("seed") or key),
        "asset_seed": asset_seed,
        "style": str(payload.get("style") or "canvas_pixel"),
        "generator_version": int(payload.get("generator_version") or 1),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if isinstance(metadata, dict):
        canonical_kind = normalize_asset_kind(payload.get("kind") or subdir, metadata, key)
        metadata.setdefault("role", infer_asset_role({"key": key, "kind": canonical_kind, "metadata": metadata}))
        metadata.setdefault("entity_key", entity_key_for_asset({"key": key, "kind": canonical_kind, "metadata": metadata}))
        if metadata.get("display_name") or metadata.get("title"):
            metadata.setdefault("visible_in_gallery", True)
        manifest["assets"][key]["metadata"] = metadata
        manifest["assets"][key]["kind"] = canonical_kind
        manifest["assets"][key]["role"] = metadata.get("role", "")
        manifest["assets"][key]["entity_key"] = metadata.get("entity_key", "")
        manifest["assets"][key]["visible_in_gallery"] = bool(metadata.get("visible_in_gallery", True))
    write_asset_manifest(campaign_id, manifest)
    return asset_lookup(campaign_id, key)


def delete_asset(payload: dict[str, Any]) -> dict[str, Any]:
    ws = _web_server()
    campaign_id = str(payload.get("campaign_id") or "").strip() or ws.MemoryStore().resolve_campaign_id(None)
    key = str(payload.get("key") or "").strip()
    if not key:
        raise RuntimeError("asset key is required")
    manifest = load_asset_manifest(campaign_id)
    entry = manifest.get("assets", {}).pop(key, None)
    removed_file = False
    warnings: list[str] = []
    if isinstance(entry, dict) and entry.get("path"):
        try:
            target = _safe_asset_target(campaign_id, str(entry.get("path", "")))
            if target.exists():
                target.unlink()
                removed_file = True
        except Exception as exc:
            warnings.append(str(exc))
    write_asset_manifest(campaign_id, manifest)
    return {"ok": True, "campaign_id": campaign_id, "key": key, "removed_file": removed_file, "warnings": warnings}


def rebuild_assets(payload: dict[str, Any]) -> dict[str, Any]:
    ws = _web_server()
    campaign_id = str(payload.get("campaign_id") or "").strip() or ws.MemoryStore().resolve_campaign_id(None)
    kind = str(payload.get("kind") or "").strip()
    manifest = load_asset_manifest(campaign_id)
    removed: list[str] = []
    warnings: list[str] = []
    for key, entry in list(manifest.get("assets", {}).items()):
        if kind and str(entry.get("kind", "")) != kind:
            continue
        if isinstance(entry, dict) and entry.get("path"):
            try:
                target = _safe_asset_target(campaign_id, str(entry.get("path", "")))
                if target.exists():
                    target.unlink()
            except Exception as exc:
                warnings.append(f"{key}: {exc}")
        manifest.get("assets", {}).pop(key, None)
        removed.append(key)
    write_asset_manifest(campaign_id, manifest)
    return {"ok": True, "campaign_id": campaign_id, "kind": kind, "removed": removed, "warnings": warnings}
