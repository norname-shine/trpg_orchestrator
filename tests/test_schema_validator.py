import pytest

from trpg_orchestrator.schema_validator import SchemaValidationError, validate_actor_output, validate_chatgpt_blocks, validate_pressure_pack, validate_writeback


def minimal_pressure_pack():
    return {
        "campaign_id": "demo",
        "turn_type": "normal_progress",
        "creation_mode": {},
        "current_situation": {},
        "pressure_pack": {},
        "npc_direction": [],
        "scene_materials": [],
        "must_reveal_naturally": [],
        "must_not_explain_directly": [],
        "forbidden_this_turn": [],
        "player_pressure_point": "",
        "choice_requirement": {
            "need_choice": False,
            "choice_level": "none",
            "choice_style": "no_choice",
        },
        "ending_target": "",
        "state_update_hints": [],
        "output_requests": {
            "story_progress": {"mode": "update", "trigger": "system_required", "reason": "test"},
            "map": {"mode": "keep_previous", "trigger": "none", "reason": "test"},
            "visual_assets": {"mode": "none", "trigger": "none", "reason": "test"},
            "gallery": {"mode": "none", "trigger": "none", "reason": "test"},
            "inventory": {"mode": "none", "trigger": "none", "reason": "test"},
            "character_card": {"mode": "none", "trigger": "none", "reason": "test"},
            "dossier": {"mode": "none", "trigger": "none", "reason": "test"},
            "dice_or_check": {"mode": "none", "trigger": "none", "reason": "test"},
            "canvas_jobs": {"mode": "none", "trigger": "none", "reason": "test"},
        },
        "payloads": {},
    }


def test_pressure_pack_compat_fills_missing_human_readable_note():
    data = minimal_pressure_pack()

    validate_pressure_pack(data)

    assert data["human_readable_note"] == "Pressure pack normalized from an older or incomplete director output."


def test_pressure_pack_allows_visual_contract_candidates():
    data = minimal_pressure_pack()
    data["visual_contract_candidates"] = [{
        "entity_key": "item:kit",
        "entity_type": "item",
        "display_name": "Kit",
        "visual_identity": {"physical": {"item_type": "satchel"}},
    }]

    validate_pressure_pack(data)


def test_minimal_pressure_pack_is_valid():
    validate_pressure_pack(minimal_pressure_pack())


def test_turn_type_continue_is_rejected():
    data = minimal_pressure_pack()
    data["turn_type"] = "continue"

    with pytest.raises(SchemaValidationError, match="invalid turn_type: continue"):
        validate_pressure_pack(data)


def test_output_request_module_must_be_object():
    data = minimal_pressure_pack()
    data["output_requests"]["map"] = "keep_previous"

    with pytest.raises(SchemaValidationError, match="output_requests.map must be an object"):
        validate_pressure_pack(data)


def test_choice_level_implicit_is_rejected():
    data = minimal_pressure_pack()
    data["choice_requirement"]["choice_level"] = "implicit"

    with pytest.raises(SchemaValidationError, match="invalid choice_level: implicit"):
        validate_pressure_pack(data)


def test_output_request_story_log_is_rejected():
    data = minimal_pressure_pack()
    data["output_requests"]["story_log"] = {"mode": "update", "trigger": "turn_done", "reason": "frontend refresh"}

    with pytest.raises(SchemaValidationError, match="unknown output_requests module: story_log"):
        validate_pressure_pack(data)


def test_orchestration_forecast_requires_backend_only_true():
    data = minimal_pressure_pack()
    data["orchestration_forecast"] = {"hotload_next_turn": {}}

    with pytest.raises(SchemaValidationError, match="orchestration_forecast.for_backend_only must be true"):
        validate_pressure_pack(data)


def test_removed_empty_output_request_modules_are_compat_only():
    data = minimal_pressure_pack()

    validate_pressure_pack(data)

    assert "gallery" not in data["output_requests"]
    assert "inventory" not in data["output_requests"]


def test_removed_nonempty_output_request_modules_fail():
    data = minimal_pressure_pack()
    data["output_requests"]["inventory"] = {"mode": "update", "trigger": "item_changed", "reason": "legacy write"}

    with pytest.raises(SchemaValidationError, match="output_requests.inventory removed"):
        validate_pressure_pack(data)


def test_removed_empty_payload_keys_are_compat_only():
    data = minimal_pressure_pack()
    data["payloads"]["inventory_updates"] = []

    validate_pressure_pack(data)

    assert "inventory_updates" not in data["payloads"]


def test_removed_nonempty_payload_keys_fail():
    data = minimal_pressure_pack()
    data["payloads"]["gallery_updates"] = [{"id": "cg_001"}]

    with pytest.raises(SchemaValidationError, match="payloads.gallery_updates removed"):
        validate_pressure_pack(data)


def test_invalid_chatgpt_blocks_fail():
    with pytest.raises(SchemaValidationError):
        validate_chatgpt_blocks([
            {"type": "gm_narration", "actor_kind": "gm", "speaker": "GM", "body": "missing player action echo"}
        ])


def test_writeback_metadata_is_not_interpreted_by_this_branch():
    validate_writeback({
        "short_term_state": {},
        "long_term_memory": {"world_state_updates": {"memory_type": "truth", "value": "legacy-compatible"}},
        "new_open_threads": [],
        "closed_threads": [],
        "gallery_assets": [],
        "inventory_items": [],
    })


def test_writeback_accepts_gallery_assets_and_inventory_items():
    validate_writeback({
        "short_term_state": {},
        "long_term_memory": {},
        "new_open_threads": [],
        "closed_threads": [],
        "gallery_assets": [{"id": "letter_art", "type": "item", "title": "Damp Letter", "asset_tags": ["clue"]}],
        "inventory_items": [{"item_id": "letter_001", "title": "Damp Letter"}],
    })


def test_writeback_rejects_invalid_global_gallery_and_inventory_shapes():
    with pytest.raises(SchemaValidationError, match="state_writeback.gallery_assets must be a list"):
        validate_writeback({
            "short_term_state": {},
            "long_term_memory": {},
            "new_open_threads": [],
            "closed_threads": [],
            "gallery_assets": {},
            "inventory_items": [],
        })

    with pytest.raises(SchemaValidationError, match="state_writeback.gallery_assets\\[1\\] missing non-empty type"):
        validate_writeback({
            "short_term_state": {},
            "long_term_memory": {},
            "new_open_threads": [],
            "closed_threads": [],
            "gallery_assets": [{"id": "trace", "title": "Trace"}],
            "inventory_items": [],
        })

    with pytest.raises(SchemaValidationError, match="state_writeback.inventory_items must be a list"):
        validate_writeback({
            "short_term_state": {},
            "long_term_memory": {},
            "new_open_threads": [],
            "closed_threads": [],
            "gallery_assets": [],
            "inventory_items": {},
        })

    with pytest.raises(SchemaValidationError, match="state_writeback.inventory_items\\[1\\] missing non-empty title"):
        validate_writeback({
            "short_term_state": {},
            "long_term_memory": {},
            "new_open_threads": [],
            "closed_threads": [],
            "gallery_assets": [],
            "inventory_items": [{"item_id": "rune_pendant"}],
        })

    with pytest.raises(SchemaValidationError, match="duplicate state_writeback.inventory_items item_id"):
        validate_writeback({
            "short_term_state": {},
            "long_term_memory": {},
            "new_open_threads": [],
            "closed_threads": [],
            "gallery_assets": [],
            "inventory_items": [
                {"item_id": "rune_pendant", "title": "Rune Pendant"},
                {"item_id": "rune_pendant", "title": "Rune Pendant"},
            ],
        })


def test_writeback_requires_thread_arrays_even_when_empty():
    with pytest.raises(SchemaValidationError, match="state writeback missing key: new_open_threads"):
        validate_writeback({
            "short_term_state": {},
            "long_term_memory": {},
            "closed_threads": [],
            "gallery_assets": [],
            "inventory_items": [],
        })

    with pytest.raises(SchemaValidationError, match="state writeback missing key: closed_threads"):
        validate_writeback({
            "short_term_state": {},
            "long_term_memory": {},
            "new_open_threads": [],
            "gallery_assets": [],
            "inventory_items": [],
        })

    validate_writeback({
        "short_term_state": {},
        "long_term_memory": {},
        "new_open_threads": [],
        "closed_threads": [],
        "gallery_assets": [],
        "inventory_items": [],
    })


def test_writeback_requires_gallery_and_inventory_arrays_even_when_empty():
    with pytest.raises(SchemaValidationError, match="state writeback missing key: gallery_assets"):
        validate_writeback({
            "short_term_state": {},
            "long_term_memory": {},
            "new_open_threads": [],
            "closed_threads": [],
            "inventory_items": [],
        })

    with pytest.raises(SchemaValidationError, match="state writeback missing key: inventory_items"):
        validate_writeback({
            "short_term_state": {},
            "long_term_memory": {},
            "new_open_threads": [],
            "closed_threads": [],
            "gallery_assets": [],
        })

    validate_writeback({
        "short_term_state": {},
        "long_term_memory": {},
        "new_open_threads": [],
        "closed_threads": [],
        "gallery_assets": [],
        "inventory_items": [],
    })


def test_actor_output_missing_state_writeback_fails_schema_validation():
    with pytest.raises(SchemaValidationError, match="actor output missing key: state_writeback"):
        validate_actor_output({
            "turn_title": "Look",
            "blocks": [
                {"type": "player_action", "actor_kind": "player", "actor_id": "pc", "avatar_key": "pc", "body": "look"},
                {"type": "gm_narration", "actor_kind": "gm", "body": "The clearing is quiet."},
            ],
            "summary": "Looked around.",
        })


def test_actor_output_system_check_without_state_writeback_fails_schema_validation():
    with pytest.raises(SchemaValidationError, match="actor output missing key: state_writeback"):
        validate_actor_output({
            "turn_title": "Check",
            "blocks": [
                {"type": "player_action", "actor_kind": "player", "actor_id": "pc", "avatar_key": "pc", "body": "inspect"},
                {"type": "system_check", "actor_kind": "system", "body": "Check result: success."},
            ],
            "summary": "Checked.",
        })


def test_actor_output_allows_empty_gallery_and_inventory_when_no_asset_changes():
    validate_actor_output({
        "turn_title": "Look",
        "blocks": [
            {"type": "player_action", "actor_kind": "player", "actor_id": "pc", "avatar_key": "pc", "body": "look"},
            {"type": "gm_narration", "actor_kind": "gm", "body": "The clearing is quiet."},
        ],
        "summary": "Looked around.",
        "state_writeback": {
            "short_term_state": {},
            "long_term_memory": {},
            "new_open_threads": [],
            "closed_threads": [],
            "gallery_assets": [],
            "inventory_items": [],
        },
    })


def test_actor_output_clue_uses_gallery_assets():
    validate_actor_output({
        "turn_title": "Trace",
        "blocks": [
            {"type": "player_action", "actor_kind": "player", "actor_id": "pc", "avatar_key": "pc", "body": "inspect traces"},
            {"type": "gm_narration", "actor_kind": "gm", "body": "A broken twig points toward the fog."},
        ],
        "summary": "Found a visible trace.",
        "state_writeback": {
            "short_term_state": {},
            "long_term_memory": {},
            "new_open_threads": [],
            "closed_threads": [],
            "gallery_assets": [{"id": "fog_trace", "type": "clue", "title": "Broken twig near the fog"}],
            "inventory_items": [],
        },
    })


def test_writeback_rejects_object_tags():
    with pytest.raises(SchemaValidationError, match=r"conditions\[1\] must be a string"):
        validate_writeback({
            "short_term_state": {"player": {"conditions": [{"id": "memory_loss", "label": "失忆"}]}},
            "long_term_memory": {},
            "new_open_threads": [],
            "closed_threads": [],
        })


def test_gallery_asset_tags_must_be_strings():
    with pytest.raises(SchemaValidationError, match=r"asset_tags\[1\] must be a string"):
        validate_writeback({
            "short_term_state": {},
            "long_term_memory": {},
            "new_open_threads": [],
            "closed_threads": [],
            "gallery_assets": [{"id": "letter_art", "type": "item", "title": "Damp Letter", "asset_tags": [{"label": "clue"}]}],
        })


def test_chatgpt_block_tags_must_be_strings():
    with pytest.raises(SchemaValidationError, match=r"block 1.tags\[1\] must be a string"):
        validate_chatgpt_blocks([
            {"type": "player_action", "actor_kind": "player", "actor_id": "pc", "avatar_key": "player:pc", "body": "look", "tags": [{"label": "action"}]},
            {"type": "gm_narration", "actor_kind": "gm", "body": "The room is quiet."},
        ])


def test_system_warning_block_is_valid():
    validate_chatgpt_blocks([
        {"type": "player_action", "actor_kind": "player", "actor_id": "pc", "avatar_key": "player:pc", "body": "检查医院大厅的公告栏"},
        {"type": "system_check", "actor_kind": "system", "body": "当前场景没有医院大厅、公告栏或可拍照设备；这个行动无法直接执行", "severity": "warning"},
    ])


def test_scene_action_warning_protocol_is_validated():
    data = minimal_pressure_pack()
    data["scene_action_warning"] = {
        "code": "scene_action_unavailable",
        "severity": "warning",
        "route": "hallucination_warning",
        "message": "当前场景没有医院大厅、公告栏或可拍照设备；这个行动无法直接执行",
        "preserve_player_action": True,
    }

    validate_pressure_pack(data)

    data["scene_action_warning"]["route"] = "backend_enum_guess"
    with pytest.raises(SchemaValidationError, match="invalid scene_action_warning.route"):
        validate_pressure_pack(data)


def test_scene_action_warning_pack_can_be_warning_only():
    validate_pressure_pack({
        "campaign_id": "demo",
        "scene_action_warning": {
            "code": "scene_action_unavailable",
            "severity": "warning",
            "route": "hallucination_warning",
            "message": "当前场景没有医院大厅、公告栏或可拍照设备；这个行动无法直接执行",
            "preserve_player_action": True,
        },
    }, "demo")


def test_scene_action_warning_pack_still_requires_campaign_id():
    with pytest.raises(SchemaValidationError, match="scene action warning pack missing keys: campaign_id"):
        validate_pressure_pack({
            "scene_action_warning": {
                "code": "scene_action_unavailable",
                "severity": "warning",
                "route": "hallucination_warning",
                "message": "当前场景没有医院大厅、公告栏或可拍照设备；这个行动无法直接执行",
            },
        }, "demo")


def test_choice_prompt_choices_must_be_objects():
    with pytest.raises(SchemaValidationError, match="block 2 choice 1 must be an object"):
        validate_chatgpt_blocks([
            {"type": "player_action", "actor_kind": "player", "actor_id": "pc", "avatar_key": "player:pc", "body": "look"},
            {"type": "choice_prompt", "actor_kind": "gm", "body": "Choose.", "choices": ["Inspect the wall", "Listen"]},
        ])


def test_choice_prompt_choice_objects_are_valid():
    validate_chatgpt_blocks([
        {"type": "player_action", "actor_kind": "player", "actor_id": "pc", "avatar_key": "player:pc", "body": "look"},
        {
            "type": "choice_prompt",
            "actor_kind": "gm",
            "body": "Choose.",
            "choices": [
                {"id": "inspect_wall", "label": "Inspect the wall", "risk": "May trigger a response."},
                {"id": "listen", "label": "Listen first", "risk": "May lose time."},
            ],
        },
    ])
