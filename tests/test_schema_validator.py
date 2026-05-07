import pytest

from trpg_orchestrator.schema_validator import SchemaValidationError, validate_chatgpt_blocks, validate_pressure_pack


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


def test_invalid_chatgpt_blocks_fail():
    with pytest.raises(SchemaValidationError):
        validate_chatgpt_blocks([
            {"type": "gm_narration", "actor_kind": "gm", "speaker": "GM", "body": "missing player action echo"}
        ])


def test_writeback_metadata_invalid_value_fails():
    from trpg_orchestrator.schema_validator import validate_writeback

    with pytest.raises(SchemaValidationError):
        validate_writeback({
            "short_term_state": {},
            "long_term_memory": {"world_state_updates": {"memory_type": "truth", "value": "bad"}},
            "new_open_threads": [],
            "closed_threads": [],
        })
