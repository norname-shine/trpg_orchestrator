import time

import pytest

from trpg_orchestrator import config as app_config
from trpg_orchestrator import memory_store
from trpg_orchestrator import web_server
from trpg_orchestrator.encoding_utils import looks_mojibake
from trpg_orchestrator.memory_store import default_memory
from trpg_orchestrator.services import asset_rules
from trpg_orchestrator.services import raw_gallery_store
from trpg_orchestrator.visual_contracts import build_initial_visual_contract_candidates, merge_visual_contracts
from trpg_orchestrator.web_server import campaign_initialization_frontend_payload, validate_v4_campaign_setup


def write_default_campaign(root, campaign_id="campaign_test", name="Test Campaign"):
    root.mkdir(parents=True, exist_ok=True)
    for filename, content in default_memory(campaign_id, name).items():
        (root / filename).write_text(web_server.json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")


def smart_campaign_config(setup):
    return {
        "name": "Test Campaign",
        "template": "custom",
        "user_prompt": "player raw input should not be stored",
        "analysis": setup["analysis"],
        "routing": {"director_rules": [], "actor_rules": []},
        "model_config": {},
        "rules_config": {"character_card_enabled": True, "stat_visibility": "numeric", "attribute_config": {"enabled": True}, "dice_enabled": False, "rules_strictness": "light"},
        "story_config": {"story_length": "short", "target_total_chars": 30000, "target_chapters": 3, "target_nodes": 9},
        "character_card": {
            "identity": {"name": "Hero", "role": "Scout", "title": "", "summary": ""},
            "profile": {"background": "", "motivation": "", "personality": ""},
            "attributes": {
                "enabled": True,
                "visible": True,
                "cap": 20,
                "float_ratio": 1.2,
                "float_cap": 24,
                "three": {"items": [{"value": 12}, {"value": 13}, {"value": 14}]},
                "six": {"items": [{"value": 10}, {"value": 11}, {"value": 12}, {"value": 13}, {"value": 14}, {"value": 15}]},
            },
        },
        "companion_config": {"companion_enabled": False},
        "safety_lines": [],
        "v4_setup": setup,
    }


def smart_create_payload(name: str = "Smart Gallery Test") -> dict:
    return {
        "name": name,
        "template": "custom",
        "user_prompt": "A grounded opening premise for the test campaign.",
        "protagonist_name": "Hero",
        "protagonist_role": "Scout",
        "protagonist_background": "A field scout with a clear local history.",
        "protagonist_motivation": "Protect the camp.",
        "protagonist_personality": "Careful and direct.",
        "companion_enabled": False,
        "character_card_enabled": True,
        "attribute_enabled": True,
        "rules_strictness": "light",
        "story_length": "short",
    }


def patch_campaign_runtime(monkeypatch, tmp_path):
    registry_path = tmp_path / "campaign_registry.json"
    monkeypatch.setattr(app_config, "CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr(app_config, "REGISTRY_PATH", registry_path)
    monkeypatch.setattr(memory_store, "CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr(memory_store, "REGISTRY_PATH", registry_path)
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr(raw_gallery_store, "CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr(web_server, "schedule_opening_turn_once", lambda campaign_id: {"scheduled": False, "reason": "test"})


def assert_gallery_extensions_written(root, campaign_id: str, setup: dict):
    stored_raw = web_server.read_json(root / "extensions" / "gallery_raw.json")
    stored_index = web_server.read_json(root / "extensions" / "gallery_index.json")
    assert stored_raw["schema"] == "trpg.gallery_raw.v2"
    assert stored_raw["campaign_id"] == campaign_id
    assert stored_raw["assets"] == setup["gallery_raw"]["assets"]
    assert stored_index["campaign_id"] == campaign_id
    assert stored_index["by_id"] == {"opening_map": 0, "kit": 1}


def setup_payload(custom_categories=None):
    return {
        "public_think": [{"stage": "init", "text": "ready"}],
        "analysis": {"genre": "hunt", "tone": "tense", "premise": "A local hunt begins."},
        "campaign_taxonomy": {
            "asset_categories": [
                {"id": "prop", "label": "Prop"},
                {"id": "item", "label": "Item"},
                {"id": "character", "label": "Character"},
                {"id": "map", "label": "Map"},
                {"id": "cg", "label": "CG"},
            ],
            "campaign_categories": custom_categories or [],
            "visual_style": {"medium": "original hunt archive", "palette": ["moss"], "composition": ["dual panel"], "mood": ["tense"]},
        },
        "character_attribute_schema": {
            "three": [{"key": "vigor", "label": "Vigor"}, {"key": "insight", "label": "Insight"}, {"key": "bond", "label": "Bond"}],
            "six": [
                {"key": "force", "label": "Force"},
                {"key": "grace", "label": "Grace"},
                {"key": "grit", "label": "Grit"},
                {"key": "lore", "label": "Lore"},
                {"key": "sense", "label": "Sense"},
                {"key": "nerve", "label": "Nerve"},
            ],
        },
        "render_rules": {
            "player_portrait": {"style": "player portrait"},
            "companion_portrait": {"style": "companion portrait"},
            "character_portrait": {"style": "npc portrait"},
            "map": {"style": "semantic map"},
            "item": {"style": "item icon"},
            "prop": {"style": "prop icon"},
            "cg": {"style": "opening cg"},
        },
        "initial_assets": {
            "initial_map_canvas": {
                "map_route": {"title": "Opening Route", "nodes": [{"id": "camp", "label": "Camp"}], "edges": [], "markers": []},
                "canvas_draw_instructions": {
                    "style": "hunter field map",
                    "background": "forest camp",
                    "nodes": [{"id": "camp", "label": "Camp"}],
                    "routes": [],
                    "labels": [],
                    "hazards": [],
                    "legend": [],
                },
            },
            "initial_cg": {
                "generation_instruction": "Create the opening CG.",
                "cg_prompt": {"positive": "hunter camp at dusk", "negative": "protected franchise"},
            },
            "initial_items": [{"id": "kit", "name": "Hunter kit", "category": "prop"}],
            "item_canvas_rules": {"kit": {"shape": "satchel"}},
        },
        "gallery_raw": {
            "schema": "trpg.gallery_raw.v2",
            "campaign_id": "",
            "updated_turn": 0,
            "assets": [
                {
                    "id": "opening_map",
                    "type": "map",
                    "title": "Opening Route",
                    "gallery_category": "map",
                    "detail": "Director-authored map card",
                    "display_zone": "gallery",
                    "payload": {"media": {"image": "assets/map/opening.png"}},
                },
                {
                    "id": "kit",
                    "type": "item",
                    "title": "Hunter kit",
                    "gallery_category": "item",
                },
            ],
        },
        "story_memory_seed": {
            "custom_libraries": [
                {
                    "id": "campaign_specific_slot",
                    "label": "Campaign Slot",
                    "purpose": "Store campaign-specific state.",
                    "fields": [],
                    "display_hint": {},
                    "asset_links": [],
                }
            ],
        },
        "campaign_direction": {
            "core_concept": "Hunt the boss.",
            "opening_situation": "The party reaches camp.",
            "main_conflict": "A major threat is near.",
            "early_goals": [],
            "known_boundaries": [],
            "secrets_not_to_reveal_early": [],
            "director_notes": [],
        },
        "story_blueprint_patch": {"notes": [], "chapter_seeds": [], "chapters": [{"chapter_id": "c1", "nodes": [{"node_id": "n1", "beat_checklist": [{"beat_id": "b1"}]}]}]},
        "protagonist_patch": {"confirmed_identity": "hero", "confirmed_background": "hunter", "personality_and_voice": "steady", "abilities_and_limits": "limited", "growth_direction": "learn", "unknown_or_player_owned": []},
        "character_card_patch": {"identity": {}, "profile": {}, "badges": []},
        "companion_patch": {"enabled": False, "unknown_or_later": []},
        "safety_interpretation": {"hard_lines": [], "soft_lines": [], "tone_limits": []},
        "initial_memory_notes": {
            "world_facts": [],
            "npc_seeds": [],
            "location_seeds": [],
            "quest_seeds": [],
            "item_state_seeds": [],
            "map_state_seeds": [],
            "custom_rule_slots": [],
            "custom_libraries": [],
            "unresolved_questions": [],
        },
    }


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_campaign_custom_gallery_categories_allow_zero_to_three(count):
    payload = setup_payload([{"id": f"custom_{index}", "label": f"Custom {index}"} for index in range(count)])

    result = validate_v4_campaign_setup(payload)

    assert len(result["campaign_taxonomy"]["campaign_categories"]) == count
    assert {row["id"] for row in result["campaign_taxonomy"]["asset_categories"]} == {"prop", "item", "character", "map", "cg"}


def test_campaign_custom_gallery_categories_reject_four_or_more():
    payload = setup_payload([{"id": f"custom_{index}", "label": f"Custom {index}"} for index in range(4)])

    with pytest.raises(RuntimeError, match="0-3"):
        validate_v4_campaign_setup(payload)


def test_character_attribute_schema_is_required_and_director_defined():
    payload = setup_payload()
    payload.pop("character_attribute_schema")

    with pytest.raises(RuntimeError, match="character_attribute_schema"):
        validate_v4_campaign_setup(payload)


def test_character_attribute_schema_does_not_require_legacy_keys():
    result = validate_v4_campaign_setup(setup_payload())

    assert [row["key"] for row in result["character_attribute_schema"]["three"]] == ["vigor", "insight", "bond"]
    assert [row["key"] for row in result["character_attribute_schema"]["six"]] == ["force", "grace", "grit", "lore", "sense", "nerve"]


def test_character_card_badges_must_be_string_array():
    payload = setup_payload()
    payload["character_card_patch"]["badges"] = [{"id": "hero", "label": "Hero"}]

    with pytest.raises(RuntimeError, match=r"character_card_patch.badges\[1\] must be string"):
        validate_v4_campaign_setup(payload)


def test_frontend_tags_keep_strings_and_drop_objects():
    assert web_server.normalize_frontend_tags(["失忆", {"label": "不应显示"}], ["备用"]) == ["失忆"]


def test_frontend_tags_do_not_infer_legacy_object_strings():
    legacy = "{'id': 'memory_loss', 'label': '失忆', 'icon': 'brain'}"

    assert web_server.normalize_frontend_tags([legacy], ["备用"]) == [legacy]


def test_fixed_asset_categories_do_not_count_against_campaign_categories():
    payload = setup_payload([{"id": "rumor", "label": "Rumor"}, {"id": "relic", "label": "Relic"}])
    payload["campaign_taxonomy"]["asset_categories"] = [
        {"id": "prop", "label": "Prop"},
        {"id": "item", "label": "Item"},
        {"id": "character", "label": "Character"},
        {"id": "map", "label": "Map"},
        {"id": "cg", "label": "CG"},
    ]

    result = validate_v4_campaign_setup(payload)

    assert [row["id"] for row in result["campaign_taxonomy"]["campaign_categories"]] == ["rumor", "relic"]
    assert {row["id"] for row in result["campaign_taxonomy"]["asset_categories"]} == {"prop", "item", "character", "map", "cg"}


@pytest.mark.parametrize("field", ["initial_items", "item_canvas_rules"])
def test_campaign_initial_assets_require_initial_items_and_item_canvas_rules_fields(field):
    payload = setup_payload()
    payload["initial_assets"].pop(field)

    with pytest.raises(RuntimeError, match="initial_assets missing"):
        validate_v4_campaign_setup(payload)


def test_campaign_initial_assets_allow_empty_initial_items_and_item_canvas_rules():
    payload = setup_payload()
    payload["initial_assets"]["initial_items"] = []
    payload["initial_assets"]["item_canvas_rules"] = {}

    result = validate_v4_campaign_setup(payload)

    assert result["initial_assets"]["initial_items"] == []
    assert result["initial_assets"]["item_canvas_rules"] == {}


def test_campaign_initial_assets_reject_wrong_initial_items_type():
    payload = setup_payload()
    payload["initial_assets"]["initial_items"] = {}

    with pytest.raises(RuntimeError, match="initial_assets.initial_items must be list"):
        validate_v4_campaign_setup(payload)


def test_campaign_initial_assets_reject_wrong_item_canvas_rules_type():
    payload = setup_payload()
    payload["initial_assets"]["item_canvas_rules"] = []

    with pytest.raises(RuntimeError, match="initial_assets.item_canvas_rules must be object"):
        validate_v4_campaign_setup(payload)


def test_campaign_initial_assets_require_map_route_nodes():
    payload = setup_payload()
    payload["initial_assets"]["initial_map_canvas"]["map_route"] = {"title": "No nodes", "nodes": []}

    with pytest.raises(RuntimeError, match="map_route.nodes"):
        validate_v4_campaign_setup(payload)


def test_campaign_initial_assets_require_split_cg_contract():
    payload = setup_payload()
    payload["initial_assets"]["initial_cg"]["cg_prompt"] = {}

    with pytest.raises(RuntimeError, match="initial_cg.cg_prompt"):
        validate_v4_campaign_setup(payload)


def test_campaign_initial_assets_require_canvas_draw_instructions():
    payload = setup_payload()
    payload["initial_assets"]["initial_map_canvas"]["canvas_draw_instructions"] = {}

    with pytest.raises(RuntimeError, match="canvas_draw_instructions"):
        validate_v4_campaign_setup(payload)


def test_campaign_initial_items_accept_label_as_name_alias():
    payload = setup_payload()
    payload["initial_assets"]["initial_items"] = [{"id": "old_letter", "label": "Old Letter"}]

    result = validate_v4_campaign_setup(payload)

    assert result["initial_assets"]["initial_items"][0]["name"] == "Old Letter"


def test_validate_v4_campaign_setup_requires_gallery_raw():
    payload = setup_payload()
    payload.pop("gallery_raw")

    with pytest.raises(RuntimeError, match="gallery_raw must be object"):
        validate_v4_campaign_setup(payload)


def test_validate_v4_campaign_setup_requires_non_empty_gallery_raw_assets():
    payload = setup_payload()
    payload["gallery_raw"]["assets"] = []

    with pytest.raises(RuntimeError, match="gallery_raw.assets must contain at least one asset"):
        validate_v4_campaign_setup(payload)


def test_campaign_setup_gallery_raw_example_does_not_show_empty_assets():
    hint = web_server.campaign_setup_schema_hint()

    assert hint["gallery_raw"]["assets"]
    assert '"assets": []' not in web_server.json.dumps(hint, ensure_ascii=False)


def test_campaign_setup_prompt_defines_custom_gallery_semantics():
    prompt = web_server.build_campaign_director_setup_prompt(smart_create_payload())

    assert "少量、跨回合复用" in prompt
    assert "本团专属资料维度" in prompt
    assert "不是地点、章节、角色、物品、道具、地图或CG的同义词" in prompt
    assert "没有强需求就返回 []" in prompt
    assert "不得把地图区域、地点名称、章节阶段或场景名作为自定义资料夹筛选" in prompt
    assert "不得输出等同于固定筛选的分类" in prompt


def test_campaign_setup_prompt_defines_item_and_prop_boundary():
    prompt = web_server.build_campaign_director_setup_prompt(smart_create_payload())

    assert "`item` 是玩家持有、可装备、可消耗或可纳入物品栏追踪的物" in prompt
    assert "`prop` 是场景线索、机关器物、环境物、不可携带物或尚未归属给玩家的物" in prompt


@pytest.mark.parametrize("forbidden", ["gallery_updates", "inventory_updates"])
def test_validate_v4_campaign_setup_rejects_legacy_gallery_payload_keys(forbidden: str):
    payload = setup_payload()
    payload["gallery_raw"]["assets"][0][forbidden] = []

    with pytest.raises(RuntimeError, match=forbidden):
        validate_v4_campaign_setup(payload)


def test_validate_v4_campaign_setup_rejects_npc_portrait_map_placeholder_id():
    payload = setup_payload()
    payload["gallery_raw"]["assets"][0]["id"] = "npc_portrait_opening_map"

    with pytest.raises(RuntimeError, match="npc_portrait_"):
        validate_v4_campaign_setup(payload)


def test_gallery_raw_asset_extra_fields_are_preserved():
    payload = setup_payload()
    asset = payload["gallery_raw"]["assets"][0]
    asset["category"] = "custom_map"
    asset["payload"]["director_only"] = {"nested": ["keep", "as", "is"]}

    result = validate_v4_campaign_setup(payload)

    assert result["gallery_raw"]["assets"][0] is asset
    assert result["gallery_raw"]["assets"][0]["category"] == "custom_map"
    assert result["gallery_raw"]["assets"][0]["payload"]["director_only"] == {"nested": ["keep", "as", "is"]}


def test_legacy_initial_assets_keys_are_rejected():
    payload = setup_payload()
    payload["initial_assets"] = {
        "map_generation_instruction": "Draw a field map.",
        "map_canvas": {"canvas": {"width": 1280, "height": 720}, "points": [{"id": "camp", "label": "Camp"}]},
        "map_route": {"title": "Legacy Route", "nodes": [{"id": "camp", "label": "Camp"}], "edges": [], "markers": []},
        "initial_items": [{"id": "kit", "name": "Hunter kit", "category": "prop"}],
        "item_canvas_rules": {"kit": {"shape": "satchel"}},
        "cg_generation_instruction": "Create CG.",
        "cg_prompt": {"positive": "camp", "negative": "brand"},
    }

    with pytest.raises(RuntimeError, match="legacy initial_assets keys"):
        validate_v4_campaign_setup(payload)


@pytest.mark.parametrize("legacy_key", [
    "MapCanvas",
    "map_instruction",
    "cg_instruction",
    "opening_cg_prompt",
    "image_prompt",
    "items",
    "props",
    "item_canvas",
    "canvas_rules",
])
def test_legacy_initial_asset_alias_keys_are_rejected(legacy_key):
    payload = setup_payload()
    payload["initial_assets"][legacy_key] = {"legacy": True}

    with pytest.raises(RuntimeError, match="legacy initial_assets keys"):
        validate_v4_campaign_setup(payload)


def test_initial_assets_must_be_object():
    payload = setup_payload()
    payload["initial_assets"] = []

    with pytest.raises(RuntimeError, match="initial_assets must be object"):
        validate_v4_campaign_setup(payload)


def test_initial_map_does_not_generate_npc_portrait_contract():
    setup = validate_v4_campaign_setup(setup_payload())

    contracts = build_initial_visual_contract_candidates(
        "campaign_test",
        {"campaign_id": "campaign_test", "title": "Test Campaign", "asset_seed": "seed123", "render_rules": setup["render_rules"]},
        {},
        {},
        setup["initial_assets"],
        setup["campaign_taxonomy"],
        setup,
    )
    map_contracts = [row for row in contracts if row.get("entity_type") == "map"]

    assert map_contracts
    assert all(row["entity_key"].startswith("map:") for row in map_contracts)
    assert all(row.get("render_intent", {}).get("primary") != "npc_portrait" for row in map_contracts)
    assert not [row for row in contracts if row.get("entity_type") == "npc" or str(row.get("entity_key", "")).startswith("npc:")]


def test_visual_contract_entity_type_npc_is_rejected():
    with pytest.raises(RuntimeError, match="unknown visual contract entity_type: npc"):
        merge_visual_contracts(
            {},
            [{
                "entity_key": "npc:guide",
                "entity_type": "npc",
                "display_name": "Guide",
                "render_intent": {"primary": "npc_portrait"},
            }],
            "campaign_test",
            "test",
        )


@pytest.mark.parametrize("entity_type", ["player_character", "npc", "scene"])
def test_v4_setup_rejects_forbidden_visual_contract_entity_types(entity_type):
    payload = setup_payload()
    payload["visual_contract_candidates"] = [{
        "entity_key": f"{entity_type}:sample",
        "entity_type": entity_type,
        "display_name": "Sample",
        "render_intent": {"primary": "character_portrait"},
    }]

    with pytest.raises(RuntimeError, match=f"unknown visual contract entity_type: {entity_type}"):
        validate_v4_campaign_setup(payload)


@pytest.mark.parametrize("entity_type", ["player", "companion", "character", "map", "cg", "item", "prop"])
def test_v4_setup_accepts_allowed_visual_contract_entity_types(entity_type):
    payload = setup_payload()
    render_primary = "character_portrait" if entity_type in {"player", "companion", "character"} else f"{entity_type}_image"
    payload["visual_contract_candidates"] = [{
        "entity_key": f"{entity_type}:sample",
        "entity_type": entity_type,
        "display_name": "Sample",
        "render_intent": {"primary": render_primary},
    }]
    if entity_type == "character":
        payload["visual_contract_candidates"][0]["actor_role"] = "npc"

    result = validate_v4_campaign_setup(payload)

    assert result["visual_contract_candidates"][0]["entity_type"] == entity_type


def test_visual_contract_character_actor_role_npc_is_preserved():
    contracts = merge_visual_contracts(
        {},
        [{
            "entity_key": "character:guide",
            "entity_type": "character",
            "actor_role": "npc",
            "display_name": "Guide",
            "render_intent": {"primary": "character_portrait"},
        }],
        "campaign_test",
        "test",
    )

    guide = contracts["contracts"]["character:guide"]
    assert guide["entity_type"] == "character"
    assert guide["actor_role"] == "npc"
    assert guide["render_intent"]["primary"] == "character_portrait"


def test_visual_contract_npc_portrait_render_intent_is_rejected():
    with pytest.raises(RuntimeError, match="character_portrait with actor_role=npc"):
        merge_visual_contracts(
            {},
            [{
                "entity_key": "character:guide",
                "entity_type": "character",
                "actor_role": "npc",
                "display_name": "Guide",
                "render_intent": {"primary": "npc_portrait"},
            }],
            "campaign_test",
            "test",
        )


@pytest.mark.parametrize("entity_type", ["map", "cg", "item", "prop"])
def test_non_character_visual_contracts_cannot_use_portrait_render_intent(entity_type):
    with pytest.raises(RuntimeError, match=f"{entity_type} visual contract cannot use portrait"):
        merge_visual_contracts(
            {},
            [{
                "entity_key": f"{entity_type}:sample",
                "entity_type": entity_type,
                "display_name": "Sample",
                "render_intent": {"primary": "character_portrait"},
            }],
            "campaign_test",
            "test",
        )


def test_initial_visual_contracts_ignore_legacy_initial_asset_fields():
    payload = setup_payload()
    initial_assets = {
        "map_route": {"title": "Legacy Route", "nodes": [{"id": "legacy"}]},
        "map_canvas": {"points": [{"id": "legacy"}]},
        "cg_prompt": {"positive": "legacy cg"},
        "map_generation_instruction": "legacy map instruction",
        "cg_generation_instruction": "legacy cg instruction",
        "initial_items": [],
        "item_canvas_rules": {},
    }

    contracts = build_initial_visual_contract_candidates(
        "campaign_test",
        {"campaign_id": "campaign_test", "title": "Test Campaign", "asset_seed": "seed123", "render_rules": payload["render_rules"]},
        {},
        {},
        initial_assets,
        payload["campaign_taxonomy"],
        payload,
    )

    assert not [row for row in contracts if row.get("entity_type") in {"map", "cg"}]


def test_campaign_render_rules_fill_required_defaults_when_missing():
    payload = setup_payload()
    payload.pop("render_rules")

    result = validate_v4_campaign_setup(payload)

    assert set(result["render_rules"]) >= set(web_server.REQUIRED_RENDER_RULE_KEYS)
    assert all(result["render_rules"][key] for key in web_server.REQUIRED_RENDER_RULE_KEYS)


def test_campaign_render_rules_preserve_custom_map_and_fill_others():
    payload = setup_payload()
    payload["render_rules"] = {"map": {"subject": "custom hex crawl map", "style": "inked route map"}}

    result = validate_v4_campaign_setup(payload)

    assert set(result["render_rules"]) >= set(web_server.REQUIRED_RENDER_RULE_KEYS)
    assert result["render_rules"]["map"]["subject"] == "custom hex crawl map"
    assert result["render_rules"]["map"]["style"] == "inked route map"
    assert result["render_rules"]["player_portrait"]["subject"] == web_server.DEFAULT_RENDER_RULES["player_portrait"]["subject"]


def test_chinese_setup_prompt_text_stays_readable():
    config = web_server.normalize_new_campaign_payload({
        "name": "中文测试团",
        "template": "custom",
        "story_length": "short",
        "user_prompt": "主角在雾雨港收到一封匿名信，要求避开血腥描写。",
        "protagonist_name": "林远",
        "protagonist_role": "考古学者",
        "protagonist_background": "整理祖父遗物时发现旧地图。",
        "protagonist_motivation": "寻找失落图书馆。",
        "protagonist_personality": "谨慎、好奇",
        "character_card_enabled": True,
        "attribute_enabled": True,
        "rules_strictness": "light",
        "companion_enabled": True,
        "companion_mode": "auto",
        "safety_lines": ["避免血腥", "不出现真实政治事件"],
        "custom_rules": [{"content": "节奏克制，优先探索。", "enabled": True, "target_layer": "both"}],
    })

    prompt = web_server.build_campaign_director_setup_prompt(config)

    assert "雾雨港" in prompt
    assert "节奏克制" in prompt
    assert "避免血腥" in prompt
    assert not looks_mojibake(prompt)


def test_custom_libraries_validate_generic_shape_only():
    result = validate_v4_campaign_setup(setup_payload())

    libraries = result["initial_memory_notes"]["custom_libraries"]
    assert libraries[0]["id"] == "campaign_specific_slot"
    assert set(libraries[0]) == {"id", "label", "purpose", "fields", "display_hint", "asset_links"}


def test_initialization_payload_materializes_map_and_item_jobs_without_cg_canvas(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path)
    campaign_id = "campaign_test"
    root = tmp_path / campaign_id
    root.mkdir(parents=True)
    initial_assets = validate_v4_campaign_setup(setup_payload())["initial_assets"]
    setup = validate_v4_campaign_setup(setup_payload())
    contracts = merge_visual_contracts(
        {},
        build_initial_visual_contract_candidates(
            campaign_id,
            {"campaign_id": campaign_id, "title": "Test Campaign", "asset_seed": "seed123", "render_rules": setup["render_rules"]},
            {},
            {},
            setup["initial_assets"],
            setup["campaign_taxonomy"],
            setup,
        ),
        campaign_id,
        "test",
    )
    profile = {"campaign_id": campaign_id, "title": "Test Campaign", "asset_seed": "seed123", "initial_assets": initial_assets}
    (root / "campaign_profile.json").write_text(web_server.json.dumps(profile, ensure_ascii=False), encoding="utf-8")
    (root / "visual_contracts.json").write_text(web_server.json.dumps(contracts, ensure_ascii=False), encoding="utf-8")

    result = campaign_initialization_frontend_payload(campaign_id, {"title": "Test Campaign"}, [])

    assert result["map_panel"]["update_requested"] is True
    assert result["map_panel"]["payload"]["map_route"]["nodes"]
    assert result["map_panel"]["payload"]["canvas_draw_instructions"]["nodes"]
    assert "cg_prompt" not in result["map_panel"]["payload"]
    assert result["map_panel"]["payload"]["visual_contract_key"].startswith("map:")
    kinds = {job["kind"] for job in result["canvas_jobs"]}
    assert {"map", "prop", "cg"} <= kinds
    assert all("visual_contract_hash" in job for job in result["canvas_jobs"])
    cg_job = next(job for job in result["canvas_jobs"] if job["kind"] == "cg")
    assert cg_job["renderer"] == "pixel_cg"
    assert cg_job["cg_prompt"]["positive"] == "hunter camp at dusk"
    assert result["cg_contract"]["cg_prompt"]["positive"] == "hunter camp at dusk"


def test_frontend_map_panel_accepts_map_asset_protocol_without_legacy_points():
    output = {
        "pressure_pack": {
            "output_requests": {
                "map": {"mode": "update_canvas", "reason": "protocol map update"},
            },
            "payloads": {
                "map_canvas": {
                    "schema": "trpg.map_asset_protocol.v1",
                    "title": "Protocol Map",
                    "layers": [
                        {"id": "terrain", "type": "area", "features": [{"id": "clearing", "title": "Clearing"}]},
                    ],
                },
            },
        },
    }

    result = web_server.frontend_map_panel("campaign_test", {"location": "Clearing"}, output, [])

    assert result["mode"] == "update"
    assert result["update_requested"] is True
    assert result["payload"]["map_canvas"]["schema"] == "trpg.map_asset_protocol.v1"


def test_initialization_payload_materializes_gallery_raw_canvas_jobs(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr(raw_gallery_store, "CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr(asset_rules, "CAMPAIGNS_DIR", tmp_path)
    campaign_id = "campaign_test"
    root = tmp_path / campaign_id
    root.mkdir(parents=True)
    profile = {
        "campaign_id": campaign_id,
        "title": "Canvas Gallery Test",
        "asset_seed": "seed123",
        "initial_assets": validate_v4_campaign_setup(setup_payload())["initial_assets"],
    }
    (root / "campaign_profile.json").write_text(web_server.json.dumps(profile, ensure_ascii=False), encoding="utf-8")
    (root / "asset_presentation.json").write_text(web_server.json.dumps({
        "custom_gallery_categories": [{"id": "clue_archive", "label": "Clue Archive", "source": "campaign"}],
    }, ensure_ascii=False), encoding="utf-8")
    raw_gallery_store.save_gallery_raw(campaign_id, {
        "schema": raw_gallery_store.RAW_GALLERY_SCHEMA,
        "campaign_id": campaign_id,
        "updated_turn": 1,
        "assets": [
            {
                "id": "moon_tree_mark",
                "type": "prop",
                "title": "Moon Tree Mark",
                "gallery_category": "clue_archive",
                "detail": "A reusable clue dimension entry.",
                "display_zone": "gallery",
                "canvas_spec": {
                    "schema": "item_canvas_spec.v1",
                    "archetype": "carved bark clue",
                    "materials": ["bark", "moon-silver pigment"],
                    "marks": ["crescent rune"],
                },
            }
        ],
    })

    result = campaign_initialization_frontend_payload(campaign_id, {"title": "Canvas Gallery Test"}, [])

    job = next(job for job in result["canvas_jobs"] if job["job_id"] == "gallery_moon_tree_mark")
    assert job["source"] == "gallery_raw"
    assert job["kind"] == "prop"
    assert job["gallery_category"] == "clue_archive"
    assert job["canvas_spec"]["archetype"] == "carved bark clue"
    assert job["subject_key"] == "gallery:moon_tree_mark"


def test_initialization_payload_rebuilds_legacy_gallery_scene_canvas_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr(raw_gallery_store, "CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr(asset_rules, "CAMPAIGNS_DIR", tmp_path)
    campaign_id = "campaign_test"
    root = tmp_path / campaign_id
    root.mkdir(parents=True)
    profile = {
        "campaign_id": campaign_id,
        "title": "Canvas Gallery Test",
        "asset_seed": "seed123",
        "initial_assets": validate_v4_campaign_setup(setup_payload())["initial_assets"],
    }
    (root / "campaign_profile.json").write_text(web_server.json.dumps(profile, ensure_ascii=False), encoding="utf-8")
    raw_gallery_store.save_gallery_raw(campaign_id, {
        "schema": raw_gallery_store.RAW_GALLERY_SCHEMA,
        "campaign_id": campaign_id,
        "updated_turn": 1,
        "assets": [
            {
                "id": "old_woods",
                "type": "location_record",
                "title": "Old Woods",
                "gallery_category": "map",
                "detail": "Scene spec must rebuild old cached output.",
                "display_zone": "gallery",
                "canvas_spec": {"schema": "scene_canvas_spec.v1", "scene": "old_forest", "subjects": ["giant_trees"]},
            }
        ],
    })
    legacy_cached_assets = [{
        "url": "/campaign-assets/campaign_test/map/old.png",
        "exists": True,
        "subject_key": "gallery:old_woods",
        "gallery_category": "map",
    }]

    result = campaign_initialization_frontend_payload(campaign_id, {"title": "Canvas Gallery Test"}, legacy_cached_assets)

    job = next(job for job in result["canvas_jobs"] if job["job_id"] == "gallery_old_woods")
    assert job["renderer_version"] == web_server.GALLERY_RAW_SCENE_RENDERER_VERSION


def test_asset_list_keeps_valid_cached_map_after_payload_url_materialized(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr("trpg_orchestrator.services.assets.CAMPAIGNS_DIR", tmp_path)
    campaign_id = "campaign_test"
    root = tmp_path / campaign_id
    map_file = root / "assets" / "maps" / "opening_map.png"
    map_file.parent.mkdir(parents=True)
    map_file.write_bytes(b"\x89PNG\r\n\x1a\n")
    manifest = {
        "manifest_schema": "trpg_asset_manifest",
        "manifest_version": 1,
        "campaign_id": campaign_id,
        "asset_seed": "seed123",
        "assets": {
            "campaign_test:seed123:map:opening:default:v19": {
                "key": "campaign_test:seed123:map:opening:default:v19",
                "path": "assets/maps/opening_map.png",
                "asset_kind": "map_image",
                "asset_use": "map",
                "gallery_category": "map",
                "display_zone": "map",
                "actor_role": "unknown",
                "display_name": "Opening Map",
                "certainty": "confirmed",
                "cache_policy": "stable",
                "source_type": "server_canvas",
            }
        },
    }
    (root / "assets" / "manifest.json").write_text(web_server.json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    result = web_server.asset_list(campaign_id)

    assert len(result["assets"]) == 1
    assert result["assets"][0]["asset_kind"] == "map_image"
    assert result["assets"][0]["campaign_id"] == campaign_id
    assert result["assets"][0]["asset_seed"] == "seed123"
    assert result["assets"][0]["url"].endswith("/maps/opening_map.png")


def test_apply_smart_config_stores_finalized_content_not_raw_user_input(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr(raw_gallery_store, "CAMPAIGNS_DIR", tmp_path)
    campaign_id = "campaign_test"
    root = tmp_path / campaign_id
    write_default_campaign(root, campaign_id)
    setup = validate_v4_campaign_setup(setup_payload())
    config = {
        "name": "Test Campaign",
        "template": "custom",
        "user_prompt": "玩家原始输入：不要把这句入库",
        "analysis": setup["analysis"],
        "routing": {"director_rules": [], "actor_rules": []},
        "model_config": {},
        "rules_config": {"character_card_enabled": True, "stat_visibility": "numeric", "attribute_config": {"enabled": True}, "dice_enabled": False, "rules_strictness": "light"},
        "story_config": {"story_length": "short", "target_total_chars": 30000, "target_chapters": 3, "target_nodes": 9},
        "character_card": {
            "identity": {"name": "Hero", "role": "Scout", "title": "", "summary": ""},
            "profile": {"background": "", "motivation": "", "personality": ""},
            "attributes": {
                "enabled": True,
                "visible": True,
                "cap": 20,
                "float_ratio": 1.2,
                "float_cap": 24,
                "three": {"items": [{"value": 12}, {"value": 13}, {"value": 14}]},
                "six": {"items": [{"value": 10}, {"value": 11}, {"value": 12}, {"value": 13}, {"value": 14}, {"value": 15}]},
            },
        },
        "companion_config": {"companion_enabled": False},
        "safety_lines": [],
        "v4_setup": setup,
    }

    web_server.apply_smart_campaign_config(root, config)

    profile = web_server.read_json(root / "campaign_profile.json")
    player = web_server.read_json(root / "player_state.json")
    equipment = web_server.read_json(root / "equipment_history.json")
    frontend_items = web_server.frontend_inventory({"equipment": equipment})

    assert profile["user_prompt"] == ""
    assert profile["initial_prompt"] == ""
    assert "玩家原始输入" not in web_server.json.dumps(profile, ensure_ascii=False)
    assert profile["finalized_ai_content"]["premise"] == setup["analysis"]["premise"]
    assert player["character_card"]["attributes"]["three"]["items"][0]["key"] == "vigor"
    assert frontend_items[0]["short_name"] == "Hunter kit"


def test_apply_smart_config_persists_gallery_raw_without_mutation(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr(raw_gallery_store, "CAMPAIGNS_DIR", tmp_path)
    campaign_id = "campaign_test"
    root = tmp_path / campaign_id
    write_default_campaign(root, campaign_id)
    setup = validate_v4_campaign_setup(setup_payload())
    expected_assets = web_server.json.loads(web_server.json.dumps(setup["gallery_raw"]["assets"], ensure_ascii=False))
    config = smart_campaign_config(setup)

    web_server.apply_smart_campaign_config(root, config)

    stored_raw = web_server.read_json(root / "extensions" / "gallery_raw.json")
    stored_index = web_server.read_json(root / "extensions" / "gallery_index.json")
    assert stored_raw["schema"] == "trpg.gallery_raw.v2"
    assert stored_raw["campaign_id"] == campaign_id
    assert stored_raw["assets"] == expected_assets
    assert setup["gallery_raw"]["campaign_id"] == ""
    assert stored_index["by_id"] == {"opening_map": 0, "kit": 1}
    assert stored_index["by_type"] == {"map": ["opening_map"], "item": ["kit"]}


def test_apply_smart_config_persists_semantic_custom_gallery_filters(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr(raw_gallery_store, "CAMPAIGNS_DIR", tmp_path)
    campaign_id = "campaign_test"
    root = tmp_path / campaign_id
    write_default_campaign(root, campaign_id)
    setup = validate_v4_campaign_setup(setup_payload([
        {"id": "线索档案", "label": "线索档案"},
        {"id": "势力档案", "label": "势力档案"},
        {"id": "异常记录", "label": "异常记录"},
    ]))

    web_server.apply_smart_campaign_config(root, smart_campaign_config(setup))

    presentation = web_server.read_json(root / "asset_presentation.json")
    assert presentation["custom_gallery_categories"] == [
        {"id": "线索档案", "label": "线索档案", "source": "campaign"},
        {"id": "势力档案", "label": "势力档案", "source": "campaign"},
        {"id": "异常记录", "label": "异常记录", "source": "campaign"},
    ]


def test_create_campaign_smart_payload_persists_gallery_raw(tmp_path, monkeypatch):
    patch_campaign_runtime(monkeypatch, tmp_path)
    setup = validate_v4_campaign_setup(setup_payload())
    monkeypatch.setattr(web_server, "call_v4_campaign_setup", lambda config: setup)

    result = web_server.create_campaign_smart_payload(smart_create_payload("Smart Gallery Sync"))

    assert result["ok"] is True
    campaign_id = result["campaign_id"]
    assert_gallery_extensions_written(tmp_path / campaign_id, campaign_id, setup)


def test_create_campaign_smart_start_job_persists_gallery_raw(tmp_path, monkeypatch):
    patch_campaign_runtime(monkeypatch, tmp_path)
    setup = validate_v4_campaign_setup(setup_payload())
    monkeypatch.setattr(web_server, "call_v4_campaign_setup", lambda config: setup)

    start = web_server.start_create_campaign_smart_job(smart_create_payload("Smart Gallery Async"))
    deadline = time.time() + 5
    progress = {}
    while time.time() < deadline:
        progress = web_server.new_campaign_progress_payload(start["job_id"])
        if progress.get("done"):
            break
        time.sleep(0.05)

    assert progress.get("done") is True
    assert progress.get("error") in ("", None)
    campaign_id = progress["campaign_id"]
    assert_gallery_extensions_written(tmp_path / campaign_id, campaign_id, setup)


def test_visual_contract_candidates_are_accepted_and_generic():
    payload = setup_payload()
    payload["visual_contract_candidates"] = [{
        "entity_key": "cg:opening_board",
        "entity_type": "cg",
        "display_name": "Opening Board",
        "memory_refs": ["campaign_direction.json"],
        "visual_identity": {"details": {"weather": "dusk"}},
        "render_intent": {"primary": "cg_image"},
    }]

    result = validate_v4_campaign_setup(payload)

    assert result["visual_contract_candidates"][0]["entity_key"] == "cg:opening_board"
