import pytest

from trpg_orchestrator.output_parser import parse_chatgpt_output


def valid_json_output():
    return {
        "turn_title": "开场",
        "blocks": [
            {
                "type": "player_action",
                "actor_kind": "player",
                "actor_id": "Lee",
                "avatar_key": "Lee",
                "speaker": "Lee",
                "body": "我检查门口。",
            },
            {
                "type": "gm_narration",
                "actor_kind": "gm",
                "speaker": "GM",
                "body": "门缝里有雨水和泥。",
            },
        ],
        "summary": "Lee 检查了门口。",
        "state_writeback": {
            "short_term_state": {},
            "long_term_memory": {},
            "new_open_threads": [],
            "closed_threads": [],
            "gallery_assets": [],
            "inventory_items": [],
        },
    }


def test_parse_structured_json_output():
    import json

    parsed = parse_chatgpt_output(json.dumps(valid_json_output(), ensure_ascii=False))

    assert parsed.summary == "Lee 检查了门口。"
    assert parsed.blocks[0]["type"] == "player_action"
    assert parsed.writeback["short_term_state"] == {}


def test_parse_structured_json_defaults_player_action_identity():
    import json

    payload = valid_json_output()
    payload["blocks"][0].pop("actor_id")
    payload["blocks"][0].pop("avatar_key")

    parsed = parse_chatgpt_output(json.dumps(payload, ensure_ascii=False))

    assert parsed.blocks[0]["actor_id"] == "player"
    assert parsed.blocks[0]["avatar_key"] == "player"


def test_parse_structured_json_missing_state_writeback_fails():
    import json

    payload = valid_json_output()
    payload.pop("state_writeback")

    with pytest.raises(ValueError):
        parse_chatgpt_output(json.dumps(payload, ensure_ascii=False))


def test_parse_structured_json_system_check_missing_state_writeback_fails():
    import json

    payload = valid_json_output()
    payload["blocks"].append({
        "type": "system_check",
        "actor_kind": "system",
        "speaker": "System",
        "body": "Check result: success.",
    })
    payload.pop("state_writeback")

    with pytest.raises(ValueError, match="state_writeback"):
        parse_chatgpt_output(json.dumps(payload, ensure_ascii=False))
