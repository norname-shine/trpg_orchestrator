from trpg_orchestrator.story_progress import build_backend_progress_control


def blueprint():
    return {
        "chapters": [
            {
                "chapter_id": "c1",
                "nodes": [
                    {"node_id": "n1", "name": "Start", "goal": "Begin", "next_nodes": ["n2"], "beat_checklist": [{"beat_id": "b1"}]},
                    {"node_id": "n2", "name": "Next", "next_nodes": [], "beat_checklist": [{"beat_id": "b2"}]},
                ],
            }
        ]
    }


def test_empty_v4_progress_control_backend_fills():
    control = build_backend_progress_control(blueprint(), {"current_node_id": "n1", "current_chapter_id": "c1"}, {})
    assert control["current_node_id"] == "n1"
    assert control["current_node_name"] == "Start"
    assert control["node_goal"] == "Begin"
    assert control["legal_next_nodes"] == ["n2"]


def test_wrong_v4_current_node_overwritten_by_story_progress():
    control = build_backend_progress_control(
        blueprint(),
        {"current_node_id": "n1", "current_chapter_id": "c1"},
        {"current_node_id": "n2"},
    )
    assert control["current_node_id"] == "n1"
    assert any("current_node_id ignored" in item for item in control["protocol_warnings"])


def test_illegal_legal_next_nodes_filtered():
    control = build_backend_progress_control(
        blueprint(),
        {"current_node_id": "n1", "current_chapter_id": "c1"},
        {"legal_next_nodes": ["n2", "missing"], "beat_targets_this_turn": ["b1", "b2"]},
    )
    assert control["legal_next_nodes"] == ["n2"]
    assert control["beat_targets_this_turn"] == ["b1"]
    assert any("legal_next_nodes filtered" in item for item in control["protocol_warnings"])
    assert any("beat target filtered" in item for item in control["protocol_warnings"])
