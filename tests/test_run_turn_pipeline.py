from trpg_orchestrator import cli


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
