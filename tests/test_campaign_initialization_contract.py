import pytest

from trpg_orchestrator import web_server
from trpg_orchestrator.encoding_utils import looks_mojibake
from trpg_orchestrator.memory_store import default_memory
from trpg_orchestrator.visual_contracts import build_initial_visual_contract_candidates, merge_visual_contracts
from trpg_orchestrator.web_server import campaign_initialization_frontend_payload, validate_v4_campaign_setup


def write_default_campaign(root, campaign_id="campaign_test", name="Test Campaign"):
    root.mkdir(parents=True, exist_ok=True)
    for filename, content in default_memory(campaign_id, name).items():
        (root / filename).write_text(web_server.json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")


def setup_payload(custom_categories=None):
    return {
        "public_think": [{"stage": "init", "text": "ready"}],
        "analysis": {"genre": "hunt", "tone": "tense", "premise": "A local hunt begins."},
        "campaign_taxonomy": {
            "asset_categories": [
                {"id": "prop", "label": "Prop"},
                {"id": "item", "label": "Item"},
                {"id": "character", "label": "Character"},
                {"id": "scene", "label": "Scene"},
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
    assert {row["id"] for row in result["campaign_taxonomy"]["asset_categories"]} == {"prop", "item", "character", "scene", "cg"}


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


def test_fixed_asset_categories_do_not_count_against_campaign_categories():
    payload = setup_payload([{"id": "rumor", "label": "Rumor"}, {"id": "relic", "label": "Relic"}])
    payload["campaign_taxonomy"]["asset_categories"] = [
        {"id": "prop", "label": "Prop"},
        {"id": "item", "label": "Item"},
        {"id": "character", "label": "Character"},
        {"id": "scene", "label": "Scene"},
        {"id": "cg", "label": "CG"},
    ]

    result = validate_v4_campaign_setup(payload)

    assert [row["id"] for row in result["campaign_taxonomy"]["campaign_categories"]] == ["rumor", "relic"]
    assert {row["id"] for row in result["campaign_taxonomy"]["asset_categories"]} == {"prop", "item", "character", "scene", "cg"}


@pytest.mark.parametrize("field", ["initial_items", "item_canvas_rules"])
def test_campaign_initial_assets_require_map_item_and_cg_contracts(field):
    payload = setup_payload()
    payload["initial_assets"][field] = {} if isinstance(payload["initial_assets"][field], dict) else []

    with pytest.raises(RuntimeError, match="initial_assets missing"):
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


def test_legacy_initial_assets_convert_to_split_contracts():
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

    result = validate_v4_campaign_setup(payload)

    assert result["initial_assets"]["initial_map_canvas"]["map_route"]["title"] == "Legacy Route"
    assert result["initial_assets"]["initial_map_canvas"]["canvas_draw_instructions"]["nodes"][0]["id"] == "camp"
    assert result["initial_assets"]["initial_cg"]["cg_prompt"]["positive"] == "camp"


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


def test_asset_list_keeps_valid_cached_map_after_payload_url_materialized(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path)
    campaign_id = "campaign_test"
    root = tmp_path / campaign_id
    map_file = root / "assets" / "maps" / "opening_map.png"
    map_file.parent.mkdir(parents=True)
    map_file.write_bytes(b"\x89PNG\r\n\x1a\n")
    manifest = {
        "campaign_id": campaign_id,
        "asset_seed": "seed123",
        "assets": {
            "campaign_test:seed123:map:opening:default:v19": {
                "campaign_id": campaign_id,
                "key": "campaign_test:seed123:map:opening:default:v19",
                "path": "assets/maps/opening_map.png",
                "kind": "map_image",
                "asset_seed": "seed123",
                "metadata": {
                    "title": "Opening Map",
                    "source": "map_route",
                    "gallery_category": "scene",
                    "map_route": {"title": "Opening Map", "nodes": [{"id": "camp", "label": "Camp"}]},
                },
            }
        },
    }
    (root / "assets" / "manifest.json").write_text(web_server.json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    result = web_server.asset_list(campaign_id)

    assert len(result["assets"]) == 1
    assert result["assets"][0]["kind"] == "map_image"
    assert result["assets"][0]["url"].endswith("/maps/opening_map.png")


def test_legacy_map_cached_as_npc_is_hidden_by_manifest_migration():
    manifest = {
        "campaign_id": "campaign_test",
        "assets": {
            "campaign_test:seed123:map_image:npc_Opening_Map:default:v19": {
                "kind": "npc_portrait",
                "path": "assets/maps/map_image_seed_npc_Opening_Map_v19.png",
                "metadata": {
                    "title": "Opening Map",
                    "display_name": "Opening Map",
                    "kind": "scene",
                    "source": "gallery",
                    "entity_key": "npc:Opening_Map",
                    "gallery_category": "npc",
                    "visible_in_gallery": True,
                },
            }
        },
    }

    migrated = web_server.migrateAssetKinds(manifest, {})
    entry = migrated["assets"]["campaign_test:seed123:map_image:npc_Opening_Map:default:v19"]

    assert entry["visible_in_gallery"] is False
    assert entry["debug_only"] is True
    assert entry["metadata"]["not_in_gallery_filters"] is True
    assert entry["metadata"]["migration_reason"] == "legacy_map_cached_as_npc_without_route"


def test_apply_smart_config_stores_finalized_content_not_raw_user_input(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path)
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


def test_visual_contract_candidates_are_accepted_and_generic():
    payload = setup_payload()
    payload["visual_contract_candidates"] = [{
        "entity_key": "scene:opening_board",
        "entity_type": "scene",
        "display_name": "Opening Board",
        "memory_refs": ["campaign_direction.json"],
        "visual_identity": {"details": {"weather": "dusk"}},
        "render_intent": {"primary": "scene_image"},
    }]

    result = validate_v4_campaign_setup(payload)

    assert result["visual_contract_candidates"][0]["entity_key"] == "scene:opening_board"
