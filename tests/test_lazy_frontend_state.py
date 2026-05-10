from trpg_orchestrator import web_server
from trpg_orchestrator.frontend_module_state import build_frontend_modules
from trpg_orchestrator.json_utils import write_json


class FakeStore:
    def load_registry(self):
        return {"active_campaign": "demo", "campaigns": {"demo": {"name": "Demo"}}}

    def resolve_campaign_id(self, campaign_id=None):
        return campaign_id or "demo"


def test_frontend_state_does_not_return_full_assets(monkeypatch):
    monkeypatch.setattr(web_server, "MemoryStore", lambda: FakeStore())
    monkeypatch.setattr(web_server, "campaign_state", lambda campaign_id: {"title": "Demo", "recent": {}})
    monkeypatch.setattr(web_server, "output_payload", lambda campaign_id, require_parse_ready=False: {"campaign_id": campaign_id, "turn_id": "demo:1", "parsed": {"blocks": [{"body": "heavy"}], "summary": "s"}, "pressure_pack": {}})
    monkeypatch.setattr(web_server, "asset_list", lambda campaign_id, kind="": {"ok": True, "assets": [{"key": "asset"}]})
    payload = web_server.frontend_state_response("demo")
    assert "assets" not in payload
    assert payload["output"]["parsed"]["blocks"] == []
    assert payload["output"]["blocks_deferred"] is True
    assert payload["output"]["turn_id"] == "demo:1"
    assert "turn_id=demo_1" in payload["frontend_state"]["modules"]["story_log"]["payload_ref"]


def test_frontend_state_points_gallery_to_raw_endpoint(monkeypatch):
    monkeypatch.setattr(web_server, "MemoryStore", lambda: FakeStore())
    monkeypatch.setattr(web_server, "campaign_state", lambda campaign_id: {"title": "Demo", "recent": {}})
    monkeypatch.setattr(web_server, "output_payload", lambda campaign_id, require_parse_ready=False: {"campaign_id": campaign_id, "parsed": {"blocks": []}, "pressure_pack": {}})
    monkeypatch.setattr(web_server, "asset_list", lambda campaign_id, kind="": {"ok": True, "assets": []})
    payload = web_server.frontend_state_response("demo")
    assert payload["frontend_state"]["gallery"]["raw_payload_ref"].startswith("/api/extensions/gallery")
    assert payload["frontend_state"]["modules"]["gallery"]["state"] == "removed"
    assert payload["frontend_state"]["modules"]["gallery"]["payload_ref"] == ""


def test_output_payload_reads_persisted_blocks_without_state_writeback_duplication(tmp_path, monkeypatch):
    outbox = tmp_path / "outbox"
    outbox.mkdir()
    monkeypatch.setattr(web_server, "MemoryStore", lambda: FakeStore())
    monkeypatch.setattr(web_server, "resolve_outbox_dir", lambda campaign_id: outbox)
    monkeypatch.setattr(web_server, "outbox_campaign_id", lambda path: "")

    write_json(outbox / "pressure_pack.json", {"campaign_id": "demo"})
    write_json(outbox / "state_writeback.json", {
        "short_term_state": {},
        "long_term_memory": {},
        "new_open_threads": [],
        "closed_threads": [],
    })
    write_json(outbox / "chatgpt_blocks.json", {
        "blocks": [
            {"type": "player_action", "actor_kind": "player", "actor_id": "pc", "avatar_key": "player:pc", "body": "查看公告栏"},
            {"type": "gm_narration", "actor_kind": "gm", "body": "公告栏上贴着一张旧楼层图。"},
        ],
        "summary": "玩家查看了公告栏。",
    })

    payload = web_server.output_payload("demo")

    assert payload["stage"] == "parsed"
    assert payload["source"] == "chatgpt_blocks.json"
    assert payload["turn_id"].startswith("demo:")
    module_payload = web_server.module_payload_response("story-log", "demo")
    assert module_payload["payload"]["turn_id"] == payload["turn_id"]
    assert payload["parsed"]["blocks"][1]["body"] == "公告栏上贴着一张旧楼层图。"


def test_legacy_gallery_module_api_is_removed(monkeypatch):
    monkeypatch.setattr(web_server, "MemoryStore", lambda: FakeStore())
    monkeypatch.setattr(web_server, "campaign_state", lambda campaign_id: {"title": "Demo", "recent": {}})
    monkeypatch.setattr(web_server, "output_payload", lambda campaign_id, require_parse_ready=False: {"campaign_id": campaign_id, "parsed": {"blocks": []}, "pressure_pack": {}})
    monkeypatch.setattr(web_server, "asset_list", lambda campaign_id, kind="": {"ok": True, "assets": []})
    payload = web_server.module_payload_response("gallery", "demo", cursor="1", limit="1")
    assert payload["ok"] is False
    assert "legacy gallery module removed" in payload["error"]


def test_map_module_keeps_cached_map_image_asset():
    modules = build_frontend_modules(
        "demo",
        {"asset_seed": "seed", "module_refs": {}},
        {"output_requests": {"map": {"mode": "keep_previous", "trigger": "none", "reason": ""}}},
        [{"kind": "map_image", "url": "/campaign-assets/demo/maps/opening.png"}],
        {},
    )

    assert modules["map_panel"]["state"] == "cached"
    assert modules["map_panel"]["payload_ref"].endswith("opening.png")
