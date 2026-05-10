from pathlib import Path

import pytest

from trpg_orchestrator.encoding_utils import assert_valid_user_text
from trpg_orchestrator.encoding_validator import validate_repository_encoding
from trpg_orchestrator.web_server import default_rule_bundle


def test_default_rule_bundle_chinese_text_is_not_placeholder_mojibake():
    bundle = default_rule_bundle()

    for category in bundle["categories"]:
        for key in ("title_zh", "desc_zh"):
            value = category[key]
            assert "???" not in value
            assert any("\u4e00" <= char <= "\u9fff" for char in value)


def test_encoding_validator_rejects_repeated_question_marks_in_zh_fields(tmp_path):
    root = tmp_path
    source = root / "src" / "bad.py"
    source.parent.mkdir()
    source.write_text('DATA = {"title_zh": "??????"}\n', encoding="utf-8")

    result = validate_repository_encoding(root)

    assert not result["ok"]
    assert result["issues"] == [
        {
            "path": "src/bad.py",
            "type": "mojibake",
            "detail": "line 1: title_zh contains repeated question marks",
        }
    ]


def test_user_action_rejects_replacement_question_mark_payload():
    with pytest.raises(UnicodeError, match="corrupt user input detected"):
        assert_valid_user_text("????????????????", "player action")


def test_user_action_allows_normal_chinese_question():
    action = "我观察林间空地四周，重点查看小径、迷雾入口和地面上有没有近期活动留下的痕迹。"

    assert assert_valid_user_text(action, "player action") == action
