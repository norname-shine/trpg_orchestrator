from trpg_orchestrator.output_parser import visible_prose_chars
from trpg_orchestrator.schema_validator import SchemaValidationError, validate_progress_writeback
from trpg_orchestrator.story_progress import apply_progress_writeback, build_frontend_story_progress, validate_story_blueprint


def blueprint():
    return {
        "chapters": [
            {
                "chapter_id": "c1",
                "name": "Chapter",
                "nodes": [
                    {
                        "node_id": "n1",
                        "name": "Start",
                        "goal": "Open the scene",
                        "weight": 1,
                        "target_chars": 100,
                        "max_turns": 3,
                        "next_nodes": ["n2"],
                        "beat_checklist": [{"beat_id": "b1", "weight": 1}],
                    },
                    {"node_id": "n2", "name": "Next", "next_nodes": [], "beat_checklist": [{"beat_id": "b2"}]},
                ],
            }
        ]
    }


def test_empty_blueprint_disables_progress():
    payload = build_frontend_story_progress({"chapters": []}, {})
    assert payload["enabled"] is False


def test_apply_seeds_first_node():
    updated = apply_progress_writeback(blueprint(), {}, {"node_status": "active"}, prose_chars_delta=5)
    assert updated["current_node_id"] == "n1"
    assert updated["current_chapter_id"] == "c1"


def test_beat_updates_only_current_node():
    updated = apply_progress_writeback(
        blueprint(),
        {"current_node_id": "n1", "current_chapter_id": "c1"},
        {"beat_updates": [{"beat_id": "b2", "status": "resolved", "evidence": "future"}]},
    )
    assert "b2" not in updated["beat_status"]
    assert any("illegal beat_update" in item for item in updated["protocol_warnings"])


def test_invalid_beat_schema_rejected():
    try:
        validate_progress_writeback({"beat_updates": [{"beat_id": "b1", "status": "resolved"}]})
    except SchemaValidationError as exc:
        assert "evidence" in str(exc)
    else:
        raise AssertionError("expected SchemaValidationError")


def test_illegal_transition_warned_and_ignored():
    updated = apply_progress_writeback(
        blueprint(),
        {"current_node_id": "n1", "current_chapter_id": "c1"},
        {"transition_request": {"type": "advance", "to_node_id": "missing", "reason": "try"}},
    )
    assert updated["current_node_id"] == "n1"
    assert any("illegal transition" in item for item in updated["protocol_warnings"])


def test_next_nodes_typo_validated():
    data = blueprint()
    data["chapters"][0]["nodes"][0]["next_nodes"] = ["typo"]
    try:
        validate_story_blueprint(data)
    except ValueError as exc:
        assert "references missing node_id" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_resolved_without_evidence_not_completed():
    updated = apply_progress_writeback(
        blueprint(),
        {"current_node_id": "n1", "current_chapter_id": "c1"},
        {"node_status": "resolved"},
    )
    assert "n1" not in updated["completed_node_ids"]
    assert "resolved_without_evidence_kept_active" in updated["protocol_warnings"]


def test_visible_blocks_chars_increase_chars_in_node():
    blocks = [
        {"type": "gm_narration", "body": "abcd"},
        {"type": "backend_note", "body": "hidden"},
        {"type": "choice_prompt", "body": "xy"},
    ]
    updated = apply_progress_writeback(blueprint(), {}, {"node_status": "active"}, prose_chars_delta=visible_prose_chars(blocks))
    assert updated["chars_in_node"] == 6
