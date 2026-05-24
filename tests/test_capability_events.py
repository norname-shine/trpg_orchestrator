from trpg_orchestrator import capability_resolver
from trpg_orchestrator.capability_events import detect_capability_events
from trpg_orchestrator.capability_resolver import build_capability_plan


def _memory() -> dict:
    return {
        "recent_context.json": {"current_scene": {}},
        "campaign_profile.json": {"mechanics": {}},
    }


def _capabilities(action: str, *, frontend_flags: dict | None = None) -> set[str]:
    plan = build_capability_plan("demo", action, _memory(), frontend_flags=frontend_flags)
    return set(plan["loaded_capabilities"])


def test_keyword_map_request_still_triggers_map():
    assert "map" in _capabilities("查看地图")


def test_legacy_keyword_requests_still_trigger_capabilities():
    assert "visual_assets" in _capabilities("给这个 NPC 生图")
    assert "dossier" in _capabilities("查看资料夹档案")
    assert "inventory" in _capabilities("打开背包检查装备")
    assert "dice_check_requested" in _capabilities("投骰进行检定")


def test_start_game_asset_request_triggers_map_and_visual_assets():
    plan = build_capability_plan("demo", "开始游戏，请为我返回地图/CG/和所有资产夹内容都返回一组新数据", _memory())

    assert "map" in plan["loaded_capabilities"]
    assert "visual_assets" in plan["loaded_capabilities"]
    assert plan["output_contract"]["allow_map_payload"] is True
    assert plan["output_contract"]["allow_visual_assets"] is True


def test_image_negated_does_not_trigger_visual_assets():
    plan = build_capability_plan("demo", "不要生图，只继续剧情", _memory())

    assert "visual_assets" not in plan["loaded_capabilities"]
    assert plan["output_contract"]["allow_visual_assets"] is False
    assert "allow_gallery_update" not in plan["output_contract"]
    assert "allow_inventory_update" not in plan["output_contract"]
    assert plan["frontend_refresh"]["gallery"] == "extension_store"
    assert "visual_assets_disabled_by_player_request" in plan["warnings"]


def test_item_obtained_event_triggers_inventory():
    assert "inventory" in _capabilities("捡起地上的钥匙")


def test_item_inspected_event_triggers_inventory_without_dossier_fact_route():
    capabilities = _capabilities("仔细检查刚获得的徽章")

    assert "inventory" in capabilities
    assert "dossier" not in capabilities


def test_location_changed_event_triggers_map():
    assert "map" in _capabilities("沿着小路进入废弃仓库")


def test_clue_observed_event_does_not_trigger_dossier_old_channel():
    assert "dossier" not in _capabilities("注意到墙上的血色符号")


def test_status_changed_keyword_and_event_triggers_character_card():
    assert "character_card" in _capabilities("我受伤了，查看状态")


def test_dice_request_triggers_dice_check_requested():
    assert "dice_check_requested" in _capabilities("进行一次检定")


def test_frontend_gallery_update_cannot_override_image_negation():
    plan = build_capability_plan("demo", "不要生图，只继续剧情", _memory(), frontend_flags={"gallery": "update"})

    assert "visual_assets" not in plan["loaded_capabilities"]
    assert plan["output_contract"]["allow_visual_assets"] is False
    assert plan["frontend_refresh"]["gallery"] == "extension_store"


def test_capability_plan_keeps_compatible_top_level_shape():
    plan = build_capability_plan("demo", "查看地图", _memory())

    for key in (
        "schema",
        "campaign_id",
        "turn_intent",
        "loaded_capabilities",
        "prompt_modules",
        "memory_refs",
        "output_contract",
        "frontend_refresh",
        "warnings",
    ):
        assert key in plan


def test_event_detector_reports_supported_events():
    events = detect_capability_events("捡起钥匙，进入仓库，注意到符号，但不要生图", _memory())
    names = {event["event"] for event in events}

    assert {"item_obtained", "location_changed", "clue_observed", "image_negated"}.issubset(names)


def test_low_confidence_events_only_write_warnings(monkeypatch):
    monkeypatch.setattr(
        capability_resolver,
        "detect_capability_events",
        lambda *_args, **_kwargs: [{
            "event": "clue_observed",
            "capability": "gallery_assets",
            "reason": "ambiguous clue wording",
            "confidence": "low",
        }],
    )

    plan = capability_resolver.build_capability_plan("demo", "看了看周围", _memory())

    assert "dossier" not in plan["loaded_capabilities"]
    assert "possible_clue_observed_detected_but_low_confidence" in plan["warnings"]
