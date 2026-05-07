from types import SimpleNamespace

from trpg_orchestrator import web_server
from trpg_orchestrator.services import assets, frontend_state, writeback_review


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


def test_frontend_state_service_returns_core_payload(monkeypatch):
    monkeypatch.setattr(frontend_state, "_web_server", lambda: SimpleNamespace(
        _frontend_state_response_impl=lambda campaign_id="": {
            "ok": True,
            "active_campaign": campaign_id,
            "campaign_state": {},
            "frontend_state": {},
            "output": {},
            "job": {},
        }
    ))

    payload = frontend_state.frontend_state_response("demo")

    assert isinstance(payload, dict)
    for key in ("ok", "active_campaign", "campaign_state", "frontend_state", "output", "job"):
        assert key in payload


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
