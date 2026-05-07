from types import SimpleNamespace

from trpg_orchestrator import web_server
from trpg_orchestrator.services import assets, frontend_state, writeback_review
from trpg_orchestrator.json_utils import write_json


def test_assets_load_empty_manifest_returns_compatible_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path / "campaigns")

    manifest = assets.load_asset_manifest("demo")

    assert manifest["campaign_id"] == "demo"
    assert manifest["asset_seed"]
    assert manifest["assets"] == {}


def test_assets_normalize_legacy_kind_keeps_compatibility():
    assert assets.normalize_asset_kind("npc") == "npc_portrait"
    assert assets.normalize_asset_kind("monster_image") == "monster_image"
    assert assets.normalize_asset_kind("document") == "item_icon"
    assert assets.normalize_asset_kind("map") == "map_image"


def test_frontend_state_service_returns_core_payload_without_impl(monkeypatch):
    class FakeStore:
        def load_registry(self):
            return {"active_campaign": "", "campaigns": {}}

    fake_ws = SimpleNamespace(
        JOB=SimpleNamespace(snapshot=lambda: {"running": False}),
        campaign_list=lambda registry: [],
        streaming_preview_enabled=lambda: False,
        empty_output_payload=lambda campaign_id, warning="": {"campaign_id": campaign_id, "warning": warning},
    )
    monkeypatch.setattr(frontend_state, "MemoryStore", lambda: FakeStore())
    monkeypatch.setattr(frontend_state, "_web_server", lambda: fake_ws)

    payload = frontend_state.frontend_state_response("")

    assert isinstance(payload, dict)
    for key in ("ok", "active_campaign", "campaign_state", "frontend_state", "output", "job"):
        assert key in payload
    assert not hasattr(fake_ws, "_frontend_state_response_impl")


def test_frontend_state_campaign_state_reads_files_without_impl(tmp_path, monkeypatch):
    root = tmp_path / "campaigns" / "demo"
    root.mkdir(parents=True)
    write_json(root / "campaign_profile.json", {
        "title": "Demo",
        "genre": "fantasy",
        "tone": "quiet",
        "safety_lines": ["no gore"],
    })
    write_json(root / "recent_context.json", {"current_scene": {"time": "night"}})
    fake_ws = SimpleNamespace(
        CAMPAIGNS_DIR=tmp_path / "campaigns",
        normalize_story_config=lambda value: {"story_length": "medium"},
        summarize_model_config=lambda value: {"provider": ""},
        list_payload=lambda value: list(value or []),
    )
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path / "campaigns")
    monkeypatch.setattr(frontend_state, "_web_server", lambda: fake_ws)

    payload = frontend_state.campaign_state("demo")

    assert payload["title"] == "Demo"
    assert payload["genre"] == "fantasy"
    assert payload["recent"]["current_scene"]["time"] == "night"
    assert not hasattr(fake_ws, "_campaign_state_impl")


def test_frontend_state_response_active_campaign_missing_outbox_does_not_crash(tmp_path, monkeypatch):
    class FakeStore:
        def load_registry(self):
            return {
                "active_campaign": "demo",
                "campaigns": {"demo": {"name": "Demo", "status": "ready"}},
            }

        def resolve_campaign_id(self, campaign_id=None):
            return campaign_id or "demo"

    root = tmp_path / "campaigns" / "demo"
    root.mkdir(parents=True)
    write_json(root / "campaign_profile.json", {"title": "Demo"})
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path / "campaigns")
    monkeypatch.setattr(frontend_state, "MemoryStore", lambda: FakeStore())
    monkeypatch.setattr(web_server, "MemoryStore", lambda: FakeStore())

    payload = frontend_state.frontend_state_response("demo")

    assert payload["ok"] is True
    assert payload["active_campaign"] == "demo"
    assert payload["campaign_state"]["title"] == "Demo"
    assert "frontend_state" in payload


def test_writeback_review_service_missing_outbox_files_returns_compatible_state(tmp_path, monkeypatch):
    class FakeStore:
        def resolve_campaign_id(self, campaign_id=None):
            return campaign_id or "demo"

        def load_campaign_memory(self, campaign_id):
            return {
                "recent_context.json": {"applied_writeback_hashes": []},
                "story_blueprint.json": {},
                "story_progress.json": {},
            }

    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path / "campaigns")
    monkeypatch.setattr(web_server, "MemoryStore", lambda: FakeStore())
    monkeypatch.setattr(web_server, "resolve_outbox_dir", lambda campaign_id: tmp_path / "outbox")

    payload = writeback_review.writeback_review_payload("demo")

    assert payload["ok"] is True
    assert payload["campaign_id"] == "demo"
    assert payload["decision"] == "not_audited"
    assert payload["approved_writeback"] == {}
    assert isinstance(payload["warnings"], list)


def test_web_server_asset_wrapper_calls_service(monkeypatch):
    monkeypatch.setattr(assets, "asset_list", lambda campaign_id, kind="": {"ok": True, "campaign_id": campaign_id, "kind": kind, "assets": []})

    assert web_server.asset_list("demo", "npc") == {"ok": True, "campaign_id": "demo", "kind": "npc", "assets": []}


def test_web_server_frontend_state_wrapper_calls_service(monkeypatch):
    monkeypatch.setattr(frontend_state, "frontend_state_response", lambda campaign_id="": {"ok": True, "active_campaign": campaign_id})

    assert web_server.frontend_state_response("demo") == {"ok": True, "active_campaign": "demo"}


def test_web_server_writeback_review_wrapper_calls_service(monkeypatch):
    monkeypatch.setattr(writeback_review, "writeback_review_payload", lambda campaign_id="": {"ok": True, "campaign_id": campaign_id})

    assert web_server.writeback_review_payload("demo") == {"ok": True, "campaign_id": "demo"}
