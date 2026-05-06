from trpg_orchestrator.prompt_builder import build_actor_scene_control, build_chatgpt_image_input, build_chatgpt_input
from trpg_orchestrator.prompt_module_registry import select_prompt_modules


def capability_plan():
    return {
        "loaded_capabilities": [
            "base_actor",
            "map",
            "inventory",
            "dossier",
            "dice",
            "story_progress",
            "base_director",
        ],
        "prompt_modules": {"director": [], "actor": [], "audit": [], "excluded": []},
        "memory_refs": {"director": ["secret"]},
        "output_contract": {"raw": True},
        "frontend_refresh": {"raw": True},
        "warnings": ["debug only"],
    }


def memory():
    return {
        "campaign_profile.json": {
            "name": "怪物猎人",
            "language": "zh",
            "rules_config": {"dice_enabled": True, "dice_type": "d20", "roll_mode": "visible"},
        },
        "recent_context.json": {"summary": "营地外有抓痕。"},
        "player_state.json": {"name": "猎人"},
        "story_progress.json": {"current_node_id": "n1", "current_chapter_id": "c1"},
    }


def pressure_pack():
    return {
        "campaign_id": "mh",
        "current_situation": "猎人站在雾中的旧营地边缘。",
        "pressure_pack": {
            "human_pressure": "同伴在催促。",
            "environment_pressure": "雾里有拖拽声。",
            "empty_json": {},
        },
        "npc_direction": "守林人压低声音，不直接解释答案。",
        "choice_requirements": ["必须给玩家留下继续追踪或撤回营地的余地。"],
        "progress_control": {
            "current_chapter_id": "c1",
            "current_node_id": "n1",
            "current_node_name": "雾中营地",
            "node_goal": "确认第一处异常。",
            "legal_next_nodes": ["n2"],
            "beat_targets_this_turn": ["b1"],
        },
        "output_requests": {
            "story_progress": {"mode": "update", "trigger": "system_required", "reason": "raw scheduling reason"},
            "map": {"mode": "update_route", "trigger": "scene_changed", "reason": "raw map reason"},
            "visual_assets": {"mode": "create", "trigger": "scene_changed", "reason": "raw image reason"},
        "inventory": {"mode": "update", "trigger": "item_changed", "reason": "raw inventory reason"},
        "dossier": {"mode": "none", "trigger": "none", "reason": "raw dossier reason"},
        "dice_or_check": {"mode": "request_check", "trigger": "risk", "reason": "raw check reason"},
        "canvas_jobs": {"mode": "update", "trigger": "scene_changed", "reason": "raw canvas reason"},
        },
        "payloads": {
            "map_route": {"nodes": [{"id": "camp"}]},
            "visual_assets": [{"id": "cg"}],
            "inventory_updates": [],
            "state_update_hints": ["脚印方向被确认。"],
            "empty": {},
        },
        "map_canvas": {"points": [{"x": 1, "y": 2}]},
        "map_route": {"nodes": [{"id": "legacy"}]},
        "story_topology": {"nodes": ["hidden"]},
        "visual_assets": [{"id": "legacy"}],
        "human_readable_note": "debug note",
        "public_think": ["debug"],
    }


def test_actor_scene_control_converts_raw_control_to_scene_brief():
    scene = build_actor_scene_control(pressure_pack())

    assert "scene_pressure" in scene
    assert "current_situation" in scene
    assert "allowed_state_updates" in scene
    assert scene["allowed_state_updates"] == [
        "dice/check handling when allowed",
        "inventory evidence for review",
        "story progress evidence for review",
    ]
    text = str(scene)
    for forbidden in (
        "output_requests",
        "payloads",
        "trigger",
        "mode",
        "reason",
        "map_canvas",
        "map_route",
        "story_topology",
        "visual_assets",
        "human_readable_note",
        "required_writeback_targets",
    ):
        assert forbidden not in text


def test_actor_prompt_uses_actor_facing_sections_and_filters_control_terms():
    prompt = build_chatgpt_input("mh", "检查雾里的脚印", memory(), pressure_pack(), capability_plan())

    for expected in (
        "## Available Story Tools",
        "## Current Story Position",
        "## Scene Brief For This Turn",
        "检查雾里的脚印",
        "猎人站在雾中的旧营地边缘。",
        "story progress evidence for review",
    ):
        assert expected in prompt

    for forbidden in (
        "## Capability Plan",
        "## Visible Capability Summary",
        "## Visible Story Progress Control",
        "## Actor Scene Control",
        "Scene Control Pack",
        "output_requests",
        "payloads",
        "trigger",
        "mode",
        "reason",
        "director layer",
        "backend",
        "V4",
        "map_canvas",
        "map_route",
        "story_topology",
        "visual_assets",
        "human_readable_note",
        "required_writeback_targets",
        "lazy_context_rules",
        "output_contract_rules",
    ):
        assert forbidden not in prompt


def test_actor_image_prompt_keeps_image_instruction_but_filters_routing_terms():
    image_input = build_chatgpt_image_input(
        "mh",
        "inspect the fog trail",
        pressure_pack(),
        [
            {
                "id": "fog_trail_cg",
                "title": "Fog trail at the old camp",
                "positive_prompt": "A hunter kneels by fresh claw marks in pale forest fog.",
                "negative_prompt": "watermark, text, blurry",
                "aspect_ratio": "16:9",
                "style_preset": "cinematic dark fantasy wilderness",
                "quality": {"size": "2304x2304", "steps": 30},
                "trigger": "scene_changed",
                "reason": "raw image routing",
                "mode": "create",
                "payloads": {"debug": True},
            }
        ],
    )

    for expected in (
        "# Actor Image Generation Pass",
        "Actor image instruction",
        "Visible scene brief for image context",
        "A hunter kneels by fresh claw marks",
        "cinematic dark fantasy wilderness",
        "inspect the fog trail",
    ):
        assert expected in image_input

    for forbidden in (
        "Reference control pack",
        "output_requests",
        "payloads",
        "trigger",
        "mode",
        "reason",
        "map_canvas",
        "map_route",
        "story_topology",
        "human_readable_note",
    ):
        assert forbidden not in image_input


def test_prompt_module_selection_splits_actor_from_control_modules():
    actor_plan = capability_plan()
    actor_modules = select_prompt_modules(actor_plan, "actor", pressure_pack())
    assert "actor_context_rules" in actor_modules
    assert "actor_writeback_rules" in actor_modules
    assert "actor_map_rules" in actor_modules
    assert "actor_inventory_rules" in actor_modules
    assert "character_card_rules" not in actor_modules
    assert "lazy_context_rules" not in actor_modules
    assert "output_contract_rules" not in actor_modules
    assert "map_rules" not in actor_modules
    assert "inventory_rules" not in actor_modules

    director_plan = capability_plan()
    director_modules = select_prompt_modules(director_plan, "director", pressure_pack())
    assert "lazy_context_rules" in director_modules
    assert "output_contract_rules" in director_modules
    assert "map_rules" in director_modules
    assert "actor_context_rules" not in director_modules
    assert "actor_map_rules" not in director_modules
