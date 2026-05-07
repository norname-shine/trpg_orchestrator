import pytest

from trpg_orchestrator import web_server
from trpg_orchestrator.web_server import campaign_initialization_frontend_payload, validate_v4_campaign_setup


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
            "three": [{"key": "body", "label": "Body"}, {"key": "mind", "label": "Mind"}, {"key": "bond", "label": "Bond"}],
            "six": [
                {"key": "str", "label": "Str"},
                {"key": "dex", "label": "Dex"},
                {"key": "con", "label": "Con"},
                {"key": "int", "label": "Int"},
                {"key": "sense", "label": "Sense"},
                {"key": "will", "label": "Will"},
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
            "map_generation_instruction": "Create the opening area map.",
            "map_canvas": {"canvas": {"width": 1280, "height": 720}, "points": [{"id": "camp", "label": "Camp"}]},
            "map_route": {"title": "Opening Route", "nodes": [{"id": "camp", "label": "Camp"}], "edges": [], "markers": []},
            "initial_items": [{"id": "kit", "name": "Hunter kit", "category": "prop"}],
            "item_canvas_rules": {"kit": {"shape": "satchel"}},
            "cg_generation_instruction": "Create the opening CG.",
            "cg_prompt": {"positive": "hunter camp at dusk", "negative": "protected franchise"},
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


@pytest.mark.parametrize("field", ["map_generation_instruction", "map_canvas", "map_route", "initial_items", "item_canvas_rules", "cg_generation_instruction", "cg_prompt"])
def test_campaign_initial_assets_require_map_item_and_cg_contracts(field):
    payload = setup_payload()
    payload["initial_assets"][field] = {} if isinstance(payload["initial_assets"][field], dict) else []

    with pytest.raises(RuntimeError, match="initial_assets missing"):
        validate_v4_campaign_setup(payload)


def test_campaign_initial_assets_require_map_route_nodes():
    payload = setup_payload()
    payload["initial_assets"]["map_route"] = {"title": "No nodes", "nodes": []}

    with pytest.raises(RuntimeError, match="map_route.nodes"):
        validate_v4_campaign_setup(payload)


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
    profile = {"title": "Test Campaign", "asset_seed": "seed123", "initial_assets": initial_assets}
    (root / "campaign_profile.json").write_text(web_server.json.dumps(profile, ensure_ascii=False), encoding="utf-8")

    result = campaign_initialization_frontend_payload(campaign_id, {"title": "Test Campaign"}, [])

    assert result["map_panel"]["update_requested"] is True
    assert result["map_panel"]["payload"]["map_route"]["nodes"]
    kinds = {job["kind"] for job in result["canvas_jobs"]}
    assert {"map", "prop"} <= kinds
    assert "cg" not in kinds
