from __future__ import annotations

import base64
from pathlib import Path

from trpg_orchestrator.services.asset_normalizer import asset_contract_error, normalize_regular_asset
from trpg_orchestrator.json_utils import write_json
from trpg_orchestrator.services.asset_rules import ASSET_USE_TO_KIND, asset_contract_payload, validate_custom_gallery_categories
from trpg_orchestrator.services.assets import load_asset_manifest, register_canvas_map_asset, register_cg_asset, register_regular_asset, save_asset


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
    assert result["invalid_fields"] == []


def test_asset_contract_error_keeps_legacy_extra_position_compatible() -> None:
    result = asset_contract_error("bad_asset", ["gallery_category"], {"invalid_fields": ["gallery_category"]})

    assert result["missing_fields"] == []
    assert result["invalid_fields"] == ["gallery_category"]


def test_cg_routes_to_image_job(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)
    result = normalize_regular_asset({"kind": "cg", "id": "cg_1", "asset_use": "cg"}, "campaign_test")
    assert result["ok"] is False
    assert result["route_to"] == "image_job"


def test_asset_tags_reject_object_entries(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)
    result = normalize_regular_asset({
        "kind": "item",
        "id": "letter",
        "title": "Letter",
        "gallery_category": "item",
        "asset_use": "item",
        "certainty": "confirmed",
        "display_zone": "gallery",
        "cache_policy": "stable",
        "asset_tags": [{"id": "clue", "label": "Clue"}],
    }, "campaign_test")

    assert result["ok"] is False
    assert "asset_tags" in result["invalid_fields"]


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
    for old_field in ("kind", "role", "entity_key", "runtime_role", "portrait_asset_kind", "visible_in_gallery", "metadata", "debug_only"):
        assert old_field not in entry


def test_asset_contract_payload_uses_map_not_scene(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)
    payload = asset_contract_payload("campaign_test")
    ids = {row["id"] for row in payload["core_gallery_categories"]}
    assert ids == {"prop", "item", "character", "map", "cg"}
    assert "scene" not in ids


def test_custom_gallery_categories_are_limited_and_do_not_map_or_shadow_core() -> None:
    rows, warnings = validate_custom_gallery_categories([
        {"id": "monster", "label": "怪物", "source": "campaign"},
        {"id": "map", "label": "地图复写", "source": "campaign"},
        {"id": "relic", "label": "神器", "maps_to": "prop"},
        {"id": "faction", "label": "阵营", "source": "campaign"},
        {"id": "rumor", "label": "传闻", "source": "campaign"},
    ])

    assert [row["id"] for row in rows] == ["monster", "faction", "rumor"]
    assert any("maps_to" in warning for warning in warnings)
    assert any("map" in warning for warning in warnings)
    assert any("at most 3" in warning for warning in warnings)


def test_normalizer_success_path_for_character_portrait(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)

    result = normalize_regular_asset({
        "kind": "character",
        "id": "scaled_merchant",
        "title": "鳞甲商人",
        "gallery_category": "character",
        "asset_use": "portrait",
        "actor_role": "npc",
        "certainty": "confirmed",
        "display_zone": "gallery",
        "cache_policy": "stable",
    }, "campaign_test")

    assert result["ok"] is True
    normalized = result["normalized"]
    assert normalized["asset_kind"] == "character_portrait"
    assert normalized["asset_use"] == "portrait"
    assert normalized["gallery_category"] == "character"
    assert normalized["actor_role"] == "npc"


def test_custom_gallery_category_must_be_registered_before_use(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)
    payload = {
        "kind": "monster",
        "id": "scale_beast",
        "title": "鳞兽",
        "gallery_category": "monster",
        "asset_use": "portrait",
        "actor_role": "enemy",
        "certainty": "confirmed",
        "display_zone": "gallery",
        "cache_policy": "stable",
    }

    failed = normalize_regular_asset(payload, "campaign_test")
    assert failed["ok"] is False
    assert "gallery_category" in failed["invalid_fields"]
    assert "gallery_category" not in failed["missing_fields"]

    root = tmp_path / "campaign_test"
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "asset_presentation.json", {
        "custom_gallery_categories": [
            {"id": "monster", "label": "怪物", "source": "campaign"},
        ],
    })
    succeeded = normalize_regular_asset(payload, "campaign_test")
    assert succeeded["ok"] is True
    assert succeeded["normalized"]["gallery_category"] == "monster"


def test_invalid_gallery_category_scene_is_invalid_not_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)
    result = normalize_regular_asset({
        "kind": "map",
        "id": "old_scene",
        "title": "旧场景",
        "gallery_category": "scene",
        "asset_use": "map",
        "certainty": "confirmed",
        "display_zone": "map",
        "cache_policy": "stable",
    }, "campaign_test")

    assert result["ok"] is False
    assert result["error_type"] == "asset_contract_error"
    assert "gallery_category" in result["invalid_fields"]
    assert "gallery_category" not in result["missing_fields"]


def test_missing_asset_use_is_missing_not_invalid(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)
    result = normalize_regular_asset({
        "kind": "item",
        "id": "kit",
        "title": "工具包",
        "gallery_category": "item",
        "certainty": "confirmed",
        "display_zone": "gallery",
        "cache_policy": "stable",
    }, "campaign_test")

    assert result["ok"] is False
    assert "asset_use" in result["missing_fields"]
    assert result["invalid_fields"] == []


def test_cg_asset_use_routes_to_image_job(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)
    result = normalize_regular_asset({
        "kind": "image",
        "id": "opening_cg",
        "title": "开场图",
        "gallery_category": "cg",
        "asset_use": "cg",
    }, "campaign_test")

    assert result["ok"] is False
    assert result["route_to"] == "image_job"


def test_register_cg_asset_preserves_payload_fields(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.assets.CAMPAIGNS_DIR", tmp_path)
    saved = register_cg_asset({
        "campaign_id": "campaign_test",
        "key": "opening_cg",
        "id": "opening_cg",
        "title": "开场图",
        "certainty": "clue",
        "display_zone": "hidden",
        "cache_policy": "stable",
        "data_url": PNG_1X1,
    }, "seed")

    assert saved["ok"] is True
    entry = load_asset_manifest("campaign_test", "seed")["assets"]["opening_cg"]
    assert entry["certainty"] == "clue"
    assert entry["display_zone"] == "hidden"
    assert entry["cache_policy"] == "stable"


def test_save_asset_regular_requires_asset_use_and_does_not_infer_from_gallery(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr("trpg_orchestrator.services.assets.CAMPAIGNS_DIR", tmp_path)
    result = save_asset({
        "campaign_id": "campaign_test",
        "key": "bad_item",
        "kind": "item",
        "id": "bad_item",
        "title": "坏物品",
        "gallery_category": "item",
        "certainty": "confirmed",
        "display_zone": "gallery",
        "cache_policy": "stable",
        "data_url": PNG_1X1,
    })

    assert result["ok"] is False
    assert "asset_use" in result["missing_fields"]


def test_save_asset_regular_allows_registered_custom_gallery(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr("trpg_orchestrator.services.assets.CAMPAIGNS_DIR", tmp_path)
    root = tmp_path / "campaign_test"
    root.mkdir(parents=True)
    write_json(root / "asset_presentation.json", {
        "custom_gallery_categories": [
            {"id": "monster", "label": "怪物", "source": "campaign"},
        ],
    })

    saved = save_asset({
        "campaign_id": "campaign_test",
        "key": "scale_beast",
        "kind": "monster",
        "id": "scale_beast",
        "title": "鳞兽",
        "gallery_category": "monster",
        "asset_use": "portrait",
        "actor_role": "enemy",
        "certainty": "confirmed",
        "display_zone": "gallery",
        "cache_policy": "stable",
        "data_url": PNG_1X1,
    })

    assert saved["ok"] is True
    entry = load_asset_manifest("campaign_test")["assets"]["scale_beast"]
    assert entry["gallery_category"] == "monster"
    assert entry["asset_kind"] == "character_portrait"


def test_register_canvas_map_asset_registers_only_rendered_png(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("trpg_orchestrator.services.asset_rules.CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr("trpg_orchestrator.services.assets.CAMPAIGNS_DIR", tmp_path)

    saved = register_canvas_map_asset({
        "campaign_id": "campaign_test",
        "key": "current_map",
        "id": "current_map",
        "title": "当前地图",
        "data_url": PNG_1X1,
    }, "seed")

    assert saved["ok"] is True
    entry = load_asset_manifest("campaign_test", "seed")["assets"]["current_map"]
    assert entry["asset_kind"] == "map_image"
    assert entry["gallery_category"] == "map"
    assert entry["asset_use"] == "map"
    assert entry["source_type"] == "server_canvas"

    try:
        register_canvas_map_asset({
            "campaign_id": "campaign_test",
            "key": "json_only_map",
            "id": "json_only_map",
            "title": "JSON 地图",
            "map_route": {"nodes": [{"id": "a"}]},
        }, "seed")
    except RuntimeError as exc:
        assert "data_url" in str(exc)
    else:
        raise AssertionError("register_canvas_map_asset must reject missing data_url")
