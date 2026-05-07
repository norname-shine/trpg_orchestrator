import json

import pytest

from trpg_orchestrator import cli
from trpg_orchestrator.chatgpt_web_client import sha256_file
from trpg_orchestrator.encoding_utils import write_text_utf8
from trpg_orchestrator.memory_store import default_memory


class FakeStore:
    wrote_updates = False

    def resolve_campaign_id(self, campaign_id):
        return campaign_id or "demo"

    def load_campaign_memory(self, campaign_id):
        return default_memory(campaign_id)

    def write_memory_updates(self, campaign_id, updates):
        FakeStore.wrote_updates = True
        return []


def install_ingest_fakes(monkeypatch, outbox_dir):
    FakeStore.wrote_updates = False
    monkeypatch.setattr(cli, "MemoryStore", lambda: FakeStore())
    monkeypatch.setattr(cli, "campaign_outbox_dir", lambda campaign_id: outbox_dir)
    monkeypatch.setattr(cli, "sync_global_reply_if_newer", lambda outbox: None)


def write_evidence(outbox_dir, **overrides):
    raw_path = outbox_dir / "chatgpt_raw_output.md"
    payload = {
        "ok": True,
        "mode": "text",
        "campaign_id": "demo",
        "input_hash": "input",
        "output_hash": sha256_file(raw_path),
        "markers_ok": True,
        "blocked_reason": "",
        "error": "",
    }
    payload.update(overrides)
    write_text_utf8(outbox_dir / "browser_evidence.json", json.dumps(payload, ensure_ascii=False))


def test_missing_browser_evidence_stops_ingest_before_writeback(tmp_path, monkeypatch):
    outbox_dir = tmp_path / "outbox"
    outbox_dir.mkdir()
    write_text_utf8(outbox_dir / "chatgpt_raw_output.md", "not model output")
    install_ingest_fakes(monkeypatch, outbox_dir)

    with pytest.raises(RuntimeError, match="browser evidence missing"):
        cli.cmd_ingest("demo", skip_v4_audit=True)

    assert FakeStore.wrote_updates is False


def test_false_browser_evidence_stops_ingest_before_writeback(tmp_path, monkeypatch):
    outbox_dir = tmp_path / "outbox"
    outbox_dir.mkdir()
    write_text_utf8(outbox_dir / "chatgpt_raw_output.md", "Please log in")
    write_evidence(outbox_dir, ok=False, markers_ok=False, blocked_reason="login", error="Blocked browser state detected: login")
    install_ingest_fakes(monkeypatch, outbox_dir)

    with pytest.raises(RuntimeError, match="browser evidence blocked ingest"):
        cli.cmd_ingest("demo", skip_v4_audit=True)

    assert FakeStore.wrote_updates is False


def test_true_browser_evidence_with_markers_allows_ingest_gate(tmp_path):
    outbox_dir = tmp_path / "outbox"
    outbox_dir.mkdir()
    raw_path = outbox_dir / "chatgpt_raw_output.md"
    write_text_utf8(raw_path, "【正文】\n雨还在下。\n【选择点】\n无\n【回合摘要】\n雨夜继续。\n【状态回写_BEGIN】\n{}\n【状态回写_END】")
    write_evidence(outbox_dir)

    cli.verify_browser_evidence_before_ingest(raw_path, "demo")
