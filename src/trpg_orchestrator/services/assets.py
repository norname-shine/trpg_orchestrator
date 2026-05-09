from __future__ import annotations

import base64
import hashlib
import time
from pathlib import Path
from typing import Any

from ..config import CAMPAIGNS_DIR, REGISTRY_PATH
from ..json_utils import read_json, write_json
from .asset_normalizer import normalize_regular_asset
from .asset_rules import ASSET_USE_TO_KIND, safe_segment


MANIFEST_SCHEMA = "trpg_asset_manifest"
MANIFEST_VERSION = 1
PNG_PREFIX = "data:image/png;base64,"
ASSET_USE_SUBDIR = {
    "portrait": "character",
    "item": "item",
    "prop": "prop",
    "map": "map",
    "cg": "cg",
}

# Media-only manifest normalization for existing PNG files. Not a gallery
# business source; gallery cards come from extensions/gallery_raw.json.
ROLE_PRIORITY = {
    "player": 10,
    "companion": 20,
    "master": 30,
    "npc": 40,
    "item": 50,
    "map": 60,
}

# Media-only manifest normalization for existing PNG files. Not a gallery
# business source; gallery cards come from extensions/gallery_raw.json.
ROLE_ASSET_KIND = {
    "player": "character_portrait",
    "companion": "character_portrait",
    "master": "character_portrait",
    "npc": "character_portrait",
    "key_character": "character_portrait",
    "item": "item_icon",
    "prop": "prop_icon",
    "scene": "map_image",
    "map": "map_image",
    "monster": "character_portrait",
    "cg": "cg_image",
}

# Media-only manifest normalization for existing PNG files. Not a gallery
# business source; gallery cards come from extensions/gallery_raw.json.
GALLERY_VISIBLE_KINDS = {
    "character_portrait",
    "item_icon",
    "prop_icon",
    "map_image",
    "cg_image",
}


def campaign_asset_seed(campaign_id: str) -> str:
    root = CAMPAIGNS_DIR / safe_segment(campaign_id)
    profile_path = root / "campaign_profile.json"
    if profile_path.exists():
        try:
            profile = read_json(profile_path)
            if profile.get("asset_seed"):
                return str(profile["asset_seed"])
        except Exception:
            pass
    if REGISTRY_PATH.exists():
        try:
            registry = read_json(REGISTRY_PATH)
            seed = registry.get("campaigns", {}).get(campaign_id, {}).get("asset_seed")
            if seed:
                return str(seed)
        except Exception:
            pass
    return hashlib.sha256(f"trpg-assets:{campaign_id}".encode("utf-8")).hexdigest()[:16]


def scoped_asset_key(campaign_id: str, kind: str, object_id: Any, variant: str = "default", generator_version: int = 17) -> str:
    resolved = safe_segment(campaign_id)
    seed = campaign_asset_seed(resolved)
    obj = safe_segment(str(object_id or "unknown"))
    return f"{resolved}:{seed}:{safe_segment(kind)}:{obj}:{safe_segment(variant)}:v{generator_version}"


def normalize_asset_kind(kind: Any, metadata: dict[str, Any] | None = None, key: str = "") -> str:
    """Media-only manifest normalization; not a gallery business source."""
    value = str(kind or "").lower()
    if value in ASSET_USE_TO_KIND:
        return ASSET_USE_TO_KIND[value]
    if value in ASSET_USE_TO_KIND.values():
        return value
    if value in {"scene", "location", "map", "scene_image", "map_image"}:
        return "map_image"
    if value in {"item", "item_icon"}:
        return "item_icon"
    if value in {"prop", "prop_icon"}:
        return "prop_icon"
    if "cg" in value:
        return "cg_image"
    if "portrait" in value or value in {"npc", "character", "monster"}:
        return "character_portrait"
    return value


def infer_asset_role(asset: dict[str, Any]) -> str:
    """Media-only manifest normalization; not a gallery business source."""
    if not isinstance(asset, dict):
        return ""
    role = str(asset.get("actor_role") or asset.get("role") or "").lower()
    if role:
        return role
    asset_use = str(asset.get("asset_use") or "").lower()
    if asset_use == "portrait":
        return "unknown"
    if asset_use in {"item", "prop", "map", "cg"}:
        return asset_use
    return ""


def asset_display_name(asset: dict[str, Any]) -> str:
    return str(asset.get("display_name") or asset.get("title") or "").strip()


def entity_key_for_asset(asset: dict[str, Any]) -> str:
    """Media-only manifest normalization; not a gallery business source."""
    return str(asset.get("subject_key") or asset.get("key") or "").strip()


def asset_manifest_path(campaign_id: str) -> Path:
    return CAMPAIGNS_DIR / safe_segment(campaign_id) / "assets" / "manifest.json"


def default_manifest(campaign_id: str, asset_seed: str = "") -> dict[str, Any]:
    return {
        "manifest_schema": MANIFEST_SCHEMA,
        "manifest_version": MANIFEST_VERSION,
        "campaign_id": campaign_id,
        "asset_seed": asset_seed or campaign_asset_seed(campaign_id),
        "assets": {},
    }


def load_asset_manifest(campaign_id: str, asset_seed: str = "") -> dict[str, Any]:
    path = asset_manifest_path(campaign_id)
    if not path.exists():
        return default_manifest(campaign_id, asset_seed)
    try:
        data = read_json(path)
    except Exception:
        return default_manifest(campaign_id, asset_seed)
    if not isinstance(data, dict) or data.get("manifest_schema") != MANIFEST_SCHEMA:
        return default_manifest(campaign_id, asset_seed)
    data["manifest_schema"] = MANIFEST_SCHEMA
    data["manifest_version"] = MANIFEST_VERSION
    data["campaign_id"] = campaign_id
    data.setdefault("asset_seed", asset_seed or campaign_asset_seed(campaign_id))
    if not data.get("asset_seed"):
        data["asset_seed"] = asset_seed or campaign_asset_seed(campaign_id)
    data.setdefault("assets", {})
    if not isinstance(data["assets"], dict):
        data["assets"] = {}
    return data


def write_asset_manifest(campaign_id: str, manifest: dict[str, Any]) -> None:
    path = asset_manifest_path(campaign_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, manifest)


def _decode_png(data_url: str) -> bytes:
    if not data_url.startswith(PNG_PREFIX):
        raise RuntimeError("asset data_url must be a PNG data URL")
    raw = base64.b64decode(data_url[len(PNG_PREFIX):], validate=True)
    if len(raw) < 128:
        raise RuntimeError("empty PNG assets must not be saved")
    return raw


def _safe_asset_target(campaign_id: str, rel_path: str) -> Path:
    root = (CAMPAIGNS_DIR / safe_segment(campaign_id) / "assets").resolve()
    target = (CAMPAIGNS_DIR / safe_segment(campaign_id) / rel_path).resolve()
    if root not in target.parents and target != root:
        raise RuntimeError("asset path escapes campaign assets")
    if target.suffix.lower() != ".png":
        raise RuntimeError("only PNG assets are supported")
    return target


def _asset_key(payload: dict[str, Any], normalized: dict[str, Any]) -> str:
    key = str(payload.get("key") or "").strip()
    if key:
        return key
    return f"{normalized['asset_use']}_{safe_segment(normalized['id'])}_{int(time.time() * 1000)}"


def _filename(payload: dict[str, Any], key: str) -> str:
    filename = str(payload.get("filename") or key).strip()
    if filename.lower().endswith(".png"):
        filename = filename[:-4]
    return safe_segment(filename) + ".png"


def _manifest_entry(key: str, rel_path: Path, normalized: dict[str, Any]) -> dict[str, Any]:
    optional = {
        "asset_subtype": normalized.get("asset_subtype", ""),
        "asset_tags": normalized.get("asset_tags", []),
        "subject_key": normalized.get("subject_key", ""),
        "detail": normalized.get("detail", ""),
        "visual_contract_key": normalized.get("visual_contract_key", ""),
        "visual_contract_hash": normalized.get("visual_contract_hash", ""),
    }
    entry = {
        "key": key,
        "path": rel_path.as_posix(),
        "asset_kind": normalized["asset_kind"],
        "asset_use": normalized["asset_use"],
        "gallery_category": normalized["gallery_category"],
        "display_zone": normalized["display_zone"],
        "actor_role": normalized.get("actor_role") or "unknown",
        "display_name": normalized["display_name"],
        "certainty": normalized["certainty"],
        "cache_policy": normalized["cache_policy"],
        "source_type": normalized["source_type"],
        "is_placeholder": False,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    for name, value in optional.items():
        if value:
            entry[name] = value
    return entry


def register_regular_asset(payload: dict[str, Any], asset_seed: str = "") -> dict[str, Any]:
    campaign_id = str(payload.get("campaign_id") or "").strip()
    if not campaign_id:
        raise RuntimeError("campaign_id is required")
    normalized_result = normalize_regular_asset(payload, campaign_id)
    if not normalized_result.get("ok"):
        return normalized_result
    normalized = normalized_result["normalized"]
    key = _asset_key(payload, normalized)
    raw = _decode_png(str(payload.get("data_url") or ""))
    subdir = ASSET_USE_SUBDIR[normalized["asset_use"]]
    rel_path = Path("assets") / subdir / _filename(payload, key)
    target = _safe_asset_target(campaign_id, rel_path.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)

    manifest = load_asset_manifest(campaign_id, asset_seed)
    manifest["asset_seed"] = asset_seed or manifest.get("asset_seed", "")
    manifest["assets"][key] = _manifest_entry(key, rel_path, normalized)
    write_asset_manifest(campaign_id, manifest)
    return asset_lookup(campaign_id, key)


def save_asset(payload: dict[str, Any]) -> dict[str, Any]:
    campaign_id = str(payload.get("campaign_id") or "").strip()
    seed = str(payload.get("asset_seed") or campaign_asset_seed(campaign_id))
    if str(payload.get("asset_use") or "").strip().lower() == "cg" or str(payload.get("kind") or "").strip().lower() == "cg":
        return register_cg_asset(payload, seed)
    return register_regular_asset(payload, seed)


def register_cg_asset(payload: dict[str, Any], asset_seed: str = "") -> dict[str, Any]:
    payload = dict(payload)
    display_zone = str(payload.get("display_zone") or "gallery").strip() or "gallery"
    certainty = str(payload.get("certainty") or "confirmed").strip() or "confirmed"
    cache_policy = str(payload.get("cache_policy") or "scene_only").strip() or "scene_only"
    payload.update({
        "kind": "cg",
        "id": payload.get("id") or payload.get("key") or "cg",
        "title": payload.get("title") or payload.get("display_name") or "CG",
        "gallery_category": "cg",
        "asset_use": "cg",
        "actor_role": "unknown",
        "certainty": certainty,
        "display_zone": display_zone,
        "cache_policy": cache_policy,
        "source_type": "image_job",
    })
    campaign_id = str(payload.get("campaign_id") or "").strip()
    raw = _decode_png(str(payload.get("data_url") or ""))
    key = str(payload.get("key") or f"cg_{safe_segment(payload.get('id'))}_{int(time.time() * 1000)}")
    rel_path = Path("assets") / "cg" / _filename(payload, key)
    target = _safe_asset_target(campaign_id, rel_path.as_posix())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    normalized = {
        "asset_kind": ASSET_USE_TO_KIND["cg"],
        "asset_use": "cg",
        "gallery_category": "cg",
        "display_zone": display_zone,
        "actor_role": "unknown",
        "display_name": str(payload.get("display_name") or payload.get("title") or "CG"),
        "certainty": certainty,
        "cache_policy": cache_policy,
        "source_type": "image_job",
        "asset_subtype": "cg",
        "asset_tags": payload.get("asset_tags", []),
        "subject_key": str(payload.get("subject_key") or ""),
        "detail": str(payload.get("detail") or ""),
    }
    manifest = load_asset_manifest(campaign_id, asset_seed)
    manifest["asset_seed"] = asset_seed or manifest.get("asset_seed", "")
    manifest["assets"][key] = _manifest_entry(key, rel_path, normalized)
    write_asset_manifest(campaign_id, manifest)
    return asset_lookup(campaign_id, key)


def register_canvas_map_asset(payload: dict[str, Any], asset_seed: str = "") -> dict[str, Any]:
    """
    Register an already-rendered map PNG.
    This does not render map_canvas/map_route JSON yet.
    map_canvas/map_route -> PNG belongs to the later map_renderer phase.
    """
    payload = dict(payload)
    payload.update({
        "kind": payload.get("kind") or "map",
        "gallery_category": "map",
        "asset_use": "map",
        "actor_role": "unknown",
        "display_zone": payload.get("display_zone") or "map",
        "certainty": payload.get("certainty") or "confirmed",
        "cache_policy": payload.get("cache_policy") or "stable",
        "source_type": "server_canvas",
    })
    return register_regular_asset(payload, asset_seed)


def frontend_asset_view(campaign_id: str, key: str, entry: dict[str, Any]) -> dict[str, Any]:
    rel_path = str(entry.get("path") or "")
    url_path = rel_path.replace("\\", "/")
    exists = False
    if rel_path:
        try:
            exists = _safe_asset_target(campaign_id, rel_path).exists()
        except Exception:
            exists = False
    if url_path.startswith("assets/"):
        url_path = url_path[len("assets/"):]
    return {
        "key": key,
        "url": f"/campaign-assets/{safe_segment(campaign_id)}/{url_path}" if rel_path else "",
        "title": entry.get("display_name") or key,
        "asset_kind": entry.get("asset_kind", ""),
        "asset_use": entry.get("asset_use", ""),
        "gallery_category": entry.get("gallery_category", ""),
        "display_zone": entry.get("display_zone", ""),
        "actor_role": entry.get("actor_role", "unknown"),
        "asset_subtype": entry.get("asset_subtype", ""),
        "asset_tags": entry.get("asset_tags", []),
        "subject_key": entry.get("subject_key", ""),
        "certainty": entry.get("certainty", ""),
        "cache_policy": entry.get("cache_policy", ""),
        "source_type": entry.get("source_type", ""),
        "detail": entry.get("detail", ""),
        "created_at": entry.get("created_at", ""),
        "exists": exists,
        "visual_contract_key": entry.get("visual_contract_key", ""),
        "visual_contract_hash": entry.get("visual_contract_hash", ""),
    }


def asset_lookup(campaign_id: str, key: str, asset_seed: str = "") -> dict[str, Any]:
    manifest = load_asset_manifest(campaign_id, asset_seed)
    entry = manifest.get("assets", {}).get(key)
    if not isinstance(entry, dict):
        return {"ok": True, "exists": False}
    view = frontend_asset_view(campaign_id, key, entry)
    return {"ok": True, "exists": bool(view.get("exists")), "key": key, "entry": view, "url": view.get("url", ""), **view}


def asset_list(campaign_id: str, scope: str = "", asset_seed: str = "") -> dict[str, Any]:
    manifest = load_asset_manifest(campaign_id, asset_seed)
    rows = []
    for key, entry in manifest.get("assets", {}).items():
        if not isinstance(entry, dict):
            continue
        view = frontend_asset_view(campaign_id, key, entry)
        if not view.get("exists"):
            continue
        if scope and scope != "all" and scope not in {
            view.get("gallery_category"),
            view.get("asset_use"),
            view.get("display_zone"),
            view.get("asset_kind"),
        }:
            continue
        rows.append(view)
    rows.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return {"ok": True, "campaign_id": campaign_id, "assets": rows}


def delete_asset(payload: dict[str, Any], asset_seed: str = "") -> dict[str, Any]:
    campaign_id = str(payload.get("campaign_id") or "").strip()
    asset_seed = asset_seed or campaign_asset_seed(campaign_id)
    key = str(payload.get("key") or "").strip()
    manifest = load_asset_manifest(campaign_id, asset_seed)
    entry = manifest.get("assets", {}).pop(key, None)
    removed_file = False
    warnings: list[str] = []
    if isinstance(entry, dict) and entry.get("path"):
        try:
            target = _safe_asset_target(campaign_id, str(entry.get("path") or ""))
            if target.exists():
                target.unlink()
                removed_file = True
        except Exception as exc:
            warnings.append(str(exc))
    write_asset_manifest(campaign_id, manifest)
    return {"ok": True, "campaign_id": campaign_id, "key": key, "removed_file": removed_file, "warnings": warnings}


def rebuild_assets(payload: dict[str, Any], asset_seed: str = "") -> dict[str, Any]:
    campaign_id = str(payload.get("campaign_id") or "").strip()
    asset_seed = asset_seed or campaign_asset_seed(campaign_id)
    scope = str(payload.get("scope") or payload.get("kind") or "all").strip() or "all"
    dry_run = bool(payload.get("dry_run", True))
    manifest = load_asset_manifest(campaign_id, asset_seed)
    matched: list[str] = []
    warnings: list[str] = []
    for key, entry in list(manifest.get("assets", {}).items()):
        if not isinstance(entry, dict):
            continue
        fields = {
            "all",
            str(entry.get("asset_kind") or ""),
            str(entry.get("asset_use") or ""),
            str(entry.get("gallery_category") or ""),
            str(entry.get("display_zone") or ""),
            str(entry.get("source_type") or ""),
        }
        if scope not in fields:
            continue
        matched.append(key)
        if dry_run:
            continue
        try:
            if entry.get("path"):
                target = _safe_asset_target(campaign_id, str(entry.get("path") or ""))
                if target.exists():
                    target.unlink()
        except Exception as exc:
            warnings.append(f"{key}: {exc}")
        manifest.get("assets", {}).pop(key, None)
    if not dry_run:
        write_asset_manifest(campaign_id, manifest)
    orphans = cleanup_orphan_asset_files(campaign_id, dry_run=dry_run)
    return {"ok": True, "campaign_id": campaign_id, "scope": scope, "dry_run": dry_run, "matched": matched, "orphan_files": orphans.get("orphans", []), "warnings": warnings + orphans.get("warnings", [])}


def cleanup_orphan_asset_files(campaign_id: str, dry_run: bool = True) -> dict[str, Any]:
    manifest = load_asset_manifest(campaign_id)
    root = CAMPAIGNS_DIR / safe_segment(campaign_id) / "assets"
    known = {str(entry.get("path") or "").replace("\\", "/") for entry in manifest.get("assets", {}).values() if isinstance(entry, dict)}
    orphans: list[str] = []
    warnings: list[str] = []
    if not root.exists():
        return {"ok": True, "orphans": [], "warnings": []}
    for path in root.rglob("*.png"):
        rel = path.relative_to(CAMPAIGNS_DIR / safe_segment(campaign_id)).as_posix()
        if rel in known:
            continue
        orphans.append(rel)
        if not dry_run:
            try:
                path.unlink()
            except Exception as exc:
                warnings.append(f"{rel}: {exc}")
    return {"ok": True, "orphans": orphans, "warnings": warnings}
