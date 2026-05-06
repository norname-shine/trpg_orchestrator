from pathlib import Path

from trpg_orchestrator import runtime_hygiene


def test_collect_cleanup_targets_ignores_campaign_data(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_hygiene, "PROJECT_ROOT", tmp_path)
    (tmp_path / ".tmp_frontend_state.json").write_text("{}", encoding="utf-8")
    (tmp_path / "outbox").mkdir()
    (tmp_path / "outbox" / "pressure_pack.json").write_text("{}", encoding="utf-8")
    campaign_file = tmp_path / "campaigns" / "local_campaign" / "outbox" / "pressure_pack.json"
    campaign_file.parent.mkdir(parents=True)
    campaign_file.write_text("{}", encoding="utf-8")

    root = tmp_path.resolve()
    targets = {path.relative_to(root).as_posix() for path in runtime_hygiene._collect_cleanup_targets(root)}

    assert ".tmp_frontend_state.json" in targets
    assert "outbox" in targets
    assert "campaigns/local_campaign/outbox/pressure_pack.json" not in targets


def test_pre_upload_clean_deletes_root_runtime_files_but_not_campaign(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime_hygiene, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(runtime_hygiene, "_git_upload_issues", lambda root: [])
    tmp_file = tmp_path / ".tmp_gallery.json"
    tmp_file.write_text("{}", encoding="utf-8")
    outbox_file = tmp_path / "outbox" / "chatgpt_input.md"
    outbox_file.parent.mkdir()
    outbox_file.write_text("runtime", encoding="utf-8")
    campaign_file = tmp_path / "campaigns" / "demo" / "outbox" / "chatgpt_input.md"
    campaign_file.parent.mkdir(parents=True)
    campaign_file.write_text("local", encoding="utf-8")

    report = runtime_hygiene.pre_upload_clean()

    assert report["ok"]
    assert not tmp_file.exists()
    assert not outbox_file.exists()
    assert campaign_file.exists()


def test_git_upload_issues_blocks_private_campaigns_but_allows_example(monkeypatch, tmp_path):
    monkeypatch.setattr(
        runtime_hygiene,
        "_git_status",
        lambda root: [
            ".env",
            "campaigns/private_campaign/player_state.json",
            "campaigns/example_campaign/player_state.json",
            "outbox/pressure_pack.json",
        ],
    )

    issues = runtime_hygiene._git_upload_issues(tmp_path)

    assert "blocked private file in git status: .env" in issues
    assert "blocked local campaign path in git status: campaigns/private_campaign/player_state.json" in issues
    assert "blocked runtime path in git status: outbox/pressure_pack.json" in issues
    assert all("campaigns/example_campaign/player_state.json" not in issue for issue in issues)
