from trpg_orchestrator import cli
from trpg_orchestrator.output_parser import ParsedOutput


def test_run_turn_pipeline_calls_stages_in_order(monkeypatch):
    calls = []

    monkeypatch.setattr(cli, "is_light_director_action", lambda action: False)
    monkeypatch.setattr(cli, "prepare_turn", lambda action, campaign_id, offline_pressure_pack: calls.append(("prepare", action, campaign_id, offline_pressure_pack)) or 0)
    monkeypatch.setattr(cli, "send_actor_turn", lambda campaign_id: calls.append(("send", campaign_id)) or 0)
    monkeypatch.setattr(cli, "ingest_actor_turn", lambda campaign_id, skip_v4_audit: calls.append(("ingest", campaign_id, skip_v4_audit)) or 0)
    monkeypatch.setattr(cli, "run_rewrite_if_needed", lambda campaign_id, auto_rewrite, rewrite_attempts: calls.append(("rewrite", campaign_id, auto_rewrite, rewrite_attempts)) or 0)
    monkeypatch.setattr(cli, "run_image_if_needed", lambda campaign_id: calls.append(("image", campaign_id)) or 0)

    result = cli.run_turn_pipeline(
        "继续调查",
        "campaign-a",
        offline_pressure_pack=True,
        skip_v4_audit=True,
        auto_rewrite=False,
        rewrite_attempts=2,
    )

    assert result == 0
    assert calls == [
        ("prepare", "继续调查", "campaign-a", True),
        ("send", "campaign-a"),
        ("ingest", "campaign-a", True),
        ("rewrite", "campaign-a", False, 2),
        ("image", "campaign-a"),
    ]


def test_run_turn_pipeline_disables_auto_rewrite_before_rewrite_stage(monkeypatch):
    calls = []

    monkeypatch.setattr(cli, "is_light_director_action", lambda action: False)
    monkeypatch.setattr(cli, "prepare_turn", lambda action, campaign_id, offline_pressure_pack: 0)
    monkeypatch.setattr(cli, "send_actor_turn", lambda campaign_id: 0)
    monkeypatch.setattr(cli, "ingest_actor_turn", lambda campaign_id, skip_v4_audit: 0)
    monkeypatch.setattr(cli, "run_rewrite_if_needed", lambda campaign_id, auto_rewrite, rewrite_attempts: calls.append((auto_rewrite, rewrite_attempts)) or 0)
    monkeypatch.setattr(cli, "run_image_if_needed", lambda campaign_id: 0)

    result = cli.run_turn_pipeline("继续调查", "campaign-a", False, False, True, 3)

    assert result == 0
    assert calls == [(False, 3)]


def test_run_turn_pipeline_stops_after_prepare_failure(monkeypatch):
    calls = []

    monkeypatch.setattr(cli, "is_light_director_action", lambda action: False)
    monkeypatch.setattr(cli, "prepare_turn", lambda action, campaign_id, offline_pressure_pack: calls.append("prepare") or 7)
    monkeypatch.setattr(cli, "send_actor_turn", lambda campaign_id: calls.append("send") or 0)
    monkeypatch.setattr(cli, "ingest_actor_turn", lambda campaign_id, skip_v4_audit: calls.append("ingest") or 0)
    monkeypatch.setattr(cli, "run_rewrite_if_needed", lambda campaign_id, auto_rewrite, rewrite_attempts: calls.append("rewrite") or 0)
    monkeypatch.setattr(cli, "run_image_if_needed", lambda campaign_id: calls.append("image") or 0)

    result = cli.run_turn_pipeline("继续调查", "campaign-a", False, False, False, 2)

    assert result == 7
    assert calls == ["prepare"]


def test_run_turn_pipeline_stops_after_send_failure(monkeypatch):
    calls = []

    monkeypatch.setattr(cli, "is_light_director_action", lambda action: False)
    monkeypatch.setattr(cli, "prepare_turn", lambda action, campaign_id, offline_pressure_pack: calls.append("prepare") or 0)
    monkeypatch.setattr(cli, "send_actor_turn", lambda campaign_id: calls.append("send") or 7)
    monkeypatch.setattr(cli, "ingest_actor_turn", lambda campaign_id, skip_v4_audit: calls.append("ingest") or 0)
    monkeypatch.setattr(cli, "run_rewrite_if_needed", lambda campaign_id, auto_rewrite, rewrite_attempts: calls.append("rewrite") or 0)
    monkeypatch.setattr(cli, "run_image_if_needed", lambda campaign_id: calls.append("image") or 0)

    result = cli.run_turn_pipeline("继续调查", "campaign-a", False, False, False, 2)

    assert result == 7
    assert calls == ["prepare", "send"]


def test_run_turn_pipeline_stops_after_ingest_failure(monkeypatch):
    calls = []

    monkeypatch.setattr(cli, "is_light_director_action", lambda action: False)
    monkeypatch.setattr(cli, "prepare_turn", lambda action, campaign_id, offline_pressure_pack: calls.append("prepare") or 0)
    monkeypatch.setattr(cli, "send_actor_turn", lambda campaign_id: calls.append("send") or 0)
    monkeypatch.setattr(cli, "ingest_actor_turn", lambda campaign_id, skip_v4_audit: calls.append("ingest") or 7)
    monkeypatch.setattr(cli, "run_rewrite_if_needed", lambda campaign_id, auto_rewrite, rewrite_attempts: calls.append("rewrite") or 0)
    monkeypatch.setattr(cli, "run_image_if_needed", lambda campaign_id: calls.append("image") or 0)

    result = cli.run_turn_pipeline("继续调查", "campaign-a", False, False, False, 2)

    assert result == 7
    assert calls == ["prepare", "send", "ingest"]


def test_run_turn_pipeline_stops_after_rewrite_failure(monkeypatch):
    calls = []

    monkeypatch.setattr(cli, "is_light_director_action", lambda action: False)
    monkeypatch.setattr(cli, "prepare_turn", lambda action, campaign_id, offline_pressure_pack: calls.append("prepare") or 0)
    monkeypatch.setattr(cli, "send_actor_turn", lambda campaign_id: calls.append("send") or 0)
    monkeypatch.setattr(cli, "ingest_actor_turn", lambda campaign_id, skip_v4_audit: calls.append("ingest") or 0)
    monkeypatch.setattr(cli, "run_rewrite_if_needed", lambda campaign_id, auto_rewrite, rewrite_attempts: calls.append("rewrite") or 7)
    monkeypatch.setattr(cli, "run_image_if_needed", lambda campaign_id: calls.append("image") or 0)

    result = cli.run_turn_pipeline("继续调查", "campaign-a", False, False, False, 2)

    assert result == 7
    assert calls == ["prepare", "send", "ingest", "rewrite"]


def test_run_turn_pipeline_returns_image_stage_failure(monkeypatch):
    calls = []

    monkeypatch.setattr(cli, "is_light_director_action", lambda action: False)
    monkeypatch.setattr(cli, "prepare_turn", lambda action, campaign_id, offline_pressure_pack: calls.append("prepare") or 0)
    monkeypatch.setattr(cli, "send_actor_turn", lambda campaign_id: calls.append("send") or 0)
    monkeypatch.setattr(cli, "ingest_actor_turn", lambda campaign_id, skip_v4_audit: calls.append("ingest") or 0)
    monkeypatch.setattr(cli, "run_rewrite_if_needed", lambda campaign_id, auto_rewrite, rewrite_attempts: calls.append("rewrite") or 0)
    monkeypatch.setattr(cli, "run_image_if_needed", lambda campaign_id: calls.append("image") or 7)

    result = cli.run_turn_pipeline("继续调查", "campaign-a", False, False, False, 2)

    assert result == 7
    assert calls == ["prepare", "send", "ingest", "rewrite", "image"]


def test_cmd_run_turn_passes_arguments_to_pipeline(monkeypatch):
    captured = {}

    def fake_pipeline(action, campaign_id, offline_pressure_pack, skip_v4_audit, auto_rewrite, rewrite_attempts):
        captured.update({
            "action": action,
            "campaign_id": campaign_id,
            "offline_pressure_pack": offline_pressure_pack,
            "skip_v4_audit": skip_v4_audit,
            "auto_rewrite": auto_rewrite,
            "rewrite_attempts": rewrite_attempts,
        })
        return 0

    monkeypatch.setattr(cli, "run_turn_pipeline", fake_pipeline)

    result = cli.cmd_run_turn("继续调查", "campaign-a", True, True, True, 4)

    assert result == 0
    assert captured == {
        "action": "继续调查",
        "campaign_id": "campaign-a",
        "offline_pressure_pack": True,
        "skip_v4_audit": True,
        "auto_rewrite": True,
        "rewrite_attempts": 4,
    }


def test_preserve_submitted_player_action_replaces_actor_polish():
    parsed = ParsedOutput(
        body="正文",
        choices="",
        summary="摘要",
        writeback={"short_term_state": {}, "long_term_memory": {}, "new_open_threads": [], "closed_threads": []},
        blocks=[
            {
                "type": "player_action",
                "actor_kind": "player",
                "speaker": "艾琳",
                "actor_id": "player_ailin",
                "avatar_key": "player_main",
                "body": "艾琳压低呼吸，沿着林间空地边缘慢慢观察。",
            },
            {"type": "gm_narration", "actor_kind": "gm", "speaker": "GM", "body": "草叶上的露水还没有散。"},
        ],
    )

    result = cli.preserve_submitted_player_action(
        parsed,
        "我观察林间空地四周，重点查看小径、迷雾入口和地面上有没有近期活动留下的痕迹。",
    )

    assert result.blocks[0]["body"] == "我观察林间空地四周，重点查看小径、迷雾入口和地面上有没有近期活动留下的痕迹。"
    assert result.blocks[1]["body"] == "草叶上的露水还没有散。"
    assert parsed.blocks[0]["body"] == "艾琳压低呼吸，沿着林间空地边缘慢慢观察。"
