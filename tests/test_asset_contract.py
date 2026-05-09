from __future__ import annotations

import base64
from pathlib import Path

from trpg_orchestrator.services.asset_normalizer import normalize_regular_asset
from trpg_orchestrator.services.asset_rules import ASSET_USE_TO_KIND, asset_contract_payload
from trpg_orchestrator.services.assets import load_asset_manifest, register_regular_asset


PNG_1X1 = "data:image/png;base64," + base64.b64encode(
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\xe2$\xb5"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
    + (b"\0" * 128)
).decode("ascii")


def test_asset_use_is_only_kind_mapping() -> None:
    assert ASSET_USE_TO_KIND == {
        "portrait": "character_portrait",
        "item": "item_icon",
        "prop": "prop_icon",
        "map": "map_image",
        "cg": "cg_image",
    }


def test_missing_fields_return_asset_contract_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)
    result = normalize_regular_asset({"id": "broken"}, "campaign_test")
    assert result["ok"] is False
    assert result["error_type"] == "asset_contract_error"
    assert "asset_use" in result["missing_fields"]
    assert "gallery_category" in result["missing_fields"]


def test_cg_routes_to_image_job(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)
    result = normalize_regular_asset({"kind": "cg", "id": "cg_1", "asset_use": "cg"}, "campaign_test")
    assert result["ok"] is False
    assert result["route_to"] == "image_job"


def test_register_regular_asset_writes_new_manifest_only(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr("trpg_orchestrator.services.assets.CAMPAIGNS_DIR", tmp_path)
    payload = {
        "campaign_id": "campaign_test",
        "key": "asset_test",
        "kind": "map",
        "id": "current_area",
        "title": "Current Area",
        "gallery_category": "map",
        "asset_use": "map",
        "certainty": "confirmed",
        "display_zone": "map",
        "cache_policy": "stable",
        "source_type": "server_canvas",
        "data_url": PNG_1X1,
    }
    saved = register_regular_asset(payload, "seed")
    assert saved["ok"] is True
    manifest = load_asset_manifest("campaign_test", "seed")
    entry = manifest["assets"]["asset_test"]
    assert manifest["manifest_schema"] == "trpg_asset_manifest"
    assert entry["asset_kind"] == "map_image"
    assert entry["asset_use"] == "map"
    assert entry["gallery_category"] == "map"
    for old_field in ("kind", "role", "entity_key", "metadata", "visible_in_gallery", "debug_only"):
        assert old_field not in entry


def test_asset_contract_payload_uses_map_not_scene(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)
    payload = asset_contract_payload("campaign_test")
    ids = {row["id"] for row in payload["core_gallery_categories"]}
    assert ids == {"prop", "item", "character", "map", "cg"}
    assert "scene" not in ids
