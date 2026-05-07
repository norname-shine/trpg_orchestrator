import base64
from pathlib import Path
from types import SimpleNamespace

from trpg_orchestrator import web_server
from trpg_orchestrator.json_utils import read_json, write_json
from trpg_orchestrator.services import assets, frontend_state, writeback_review


def _png_data_url() -> str:
    return "data:image/png;base64," + base64.b64encode(b"x" * 256).decode("ascii")


def _campaign_root(tmp_path: Path) -> Path:
    root = tmp_path / "campaigns" / "demo"
    (root / "assets").mkdir(parents=True, exist_ok=True)
    return root


def _asset_key(campaign_id: str) -> str:
    return assets.scoped_asset_key(campaign_id, "npc_portrait", "npc:keeper")


def _write_asset_entry(tmp_path: Path, *, kind: str = "npc_portrait", metadata: dict | None = None) -> str:
    campaign_root = _campaign_root(tmp_path)
    campaign_id = "demo"
    key = _asset_key(campaign_id)
    rel_path = Path("assets") / kind / "keeper.png"
    target = campaign_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"x" * 256)
    write_json(campaign_root / "assets" / "manifest.json", {
        "campaign_id": campaign_id,
        "asset_seed": assets.campaign_asset_seed(campaign_id),
        "assets": {
            key: {
                "campaign_id": campaign_id,
                "key": key,
                "path": rel_path.as_posix(),
                "kind": kind,
                "asset_seed": assets.campaign_asset_seed(campaign_id),
                "style": "canvas_pixel",
                "generator_version": 17,
                "created_at": "2026-05-08T00:00:00Z",
                "metadata": metadata or {"display_name": "守门人", "entity_key": "npc:keeper", "visible_in_gallery": True},
            }
        },
    })
    return key


def test_assets_load_empty_manifest_returns_compatible_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path / "campaigns")
    monkeypatch.setattr(web_server, "_load_asset_manifest_impl", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("should not be used")), raising=False)

    manifest = assets.load_asset_manifest("demo")

    assert manifest["campaign_id"] == "demo"
    assert manifest["asset_seed"]
    assert manifest["assets"] == {}


def test_assets_normalize_legacy_kind_keeps_compatibility_without_web_impl(monkeypatch):
    monkeypatch.setattr(web_server, "_normalize_asset_kind_impl", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("should not be used")), raising=False)

    assert assets.normalize_asset_kind("npc") == "npc_portrait"
    assert assets.normalize_asset_kind("monster_image") == "monster_image"
    assert assets.normalize_asset_kind("document") == "item_icon"
    assert assets.normalize_asset_kind("map") == "map_image"


def test_assets_infer_role_without_web_impl(monkeypatch):
    monkeypatch.setattr(web_server, "_infer_asset_role_impl", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("should not be used")), raising=False)

    role = assets.infer_asset_role({"kind": "npc", "metadata": {"display_name": "守门人"}})

    assert role == "npc"


def test_assets_infer_role_uses_utf8_companion_keywords():
    role = assets.infer_asset_role({"kind": "portrait", "metadata": {"title": "同行伙伴"}})

    assert role == "companion"


def test_assets_infer_role_uses_utf8_master_keywords():
    role = assets.infer_asset_role({"kind": "portrait", "metadata": {"title": "御主立绘"}})

    assert role == "master"


def test_asset_list_runs_from_service_without_web_impl(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path / "campaigns")
    monkeypatch.setattr(web_server, "_asset_list_impl", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("should not be used")), raising=False)
    key = _write_asset_entry(tmp_path)

    payload = assets.asset_list("demo")

    assert payload["ok"] is True
    assert payload["campaign_id"] == "demo"
    assert payload["assets"][0]["key"] == key
    assert payload["assets"][0]["metadata"]["display_name"] == "守门人"
    assert payload["assets"][0]["url"].endswith("/npc_portrait/keeper.png")


def test_asset_lookup_runs_from_service_without_web_impl(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path / "campaigns")
    monkeypatch.setattr(web_server, "_asset_lookup_impl", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("should not be used")), raising=False)
    key = _write_asset_entry(tmp_path)

    payload = assets.asset_lookup("demo", key)

    assert payload["ok"] is True
    assert payload["exists"] is True
    assert payload["key"] == key
    assert payload["entry"]["display_name"] == "守门人"
    assert payload["url"].endswith("/npc_portrait/keeper.png")


def test_save_asset_then_lookup_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path / "campaigns")
    monkeypatch.setattr(web_server, "_save_asset_impl", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("should not be used")), raising=False)
    monkeypatch.setattr(web_server, "_asset_lookup_impl", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("should not be used")), raising=False)
    _campaign_root(tmp_path)
    key = _asset_key("demo")

    saved = assets.save_asset({
        "campaign_id": "demo",
        "key": key,
        "asset_seed": assets.campaign_asset_seed("demo"),
        "kind": "npc",
        "filename": "keeper",
        "data_url": _png_data_url(),
        "metadata": {"display_name": "守门人", "entity_key": "npc:keeper"},
    })

    manifest = read_json(tmp_path / "campaigns" / "demo" / "assets" / "manifest.json")

    assert saved["ok"] is True
    assert saved["exists"] is True
    assert saved["entry"]["kind"] == "npc_portrait"
    assert manifest["assets"][key]["kind"] == "npc_portrait"
    assert (tmp_path / "campaigns" / "demo" / "assets" / "npc" / "keeper.png").exists()


def test_delete_asset_updates_manifest_and_removes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path / "campaigns")
    monkeypatch.setattr(web_server, "_delete_asset_impl", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("should not be used")), raising=False)
    key = _write_asset_entry(tmp_path)
    target = tmp_path / "campaigns" / "demo" / "assets" / "npc_portrait" / "keeper.png"

    payload = assets.delete_asset({"campaign_id": "demo", "key": key})
    manifest = read_json(tmp_path / "campaigns" / "demo" / "assets" / "manifest.json")

    assert payload["ok"] is True
    assert payload["removed_file"] is True
    assert key not in manifest["assets"]
    assert not target.exists()


def test_rebuild_assets_removes_matching_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(web_server, "CAMPAIGNS_DIR", tmp_path / "campaigns")
    monkeypatch.setattr(web_server, "_rebuild_assets_impl", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("should not be used")), raising=False)
    key = _write_asset_entry(tmp_path, kind="npc_portrait")

    payload = assets.rebuild_assets({"campaign_id": "demo", "kind": "npc_portrait"})
    manifest = read_json(tmp_path / "campaigns" / "demo" / "assets" / "manifest.json")

    assert payload["ok"] is True
    assert payload["removed"] == [key]
    assert manifest["assets"] == {}


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


def test_web_server_asset_wrappers_call_service(monkeypatch):
    monkeypatch.setattr(assets, "asset_list", lambda campaign_id, kind="": {"ok": True, "campaign_id": campaign_id, "kind": kind, "assets": []})
    monkeypatch.setattr(assets, "asset_lookup", lambda campaign_id, key: {"ok": True, "campaign_id": campaign_id, "key": key})
    monkeypatch.setattr(assets, "save_asset", lambda payload: {"ok": True, "saved": payload["key"]})
    monkeypatch.setattr(assets, "delete_asset", lambda payload: {"ok": True, "deleted": payload["key"]})
    monkeypatch.setattr(assets, "rebuild_assets", lambda payload: {"ok": True, "kind": payload.get("kind", "")})

    assert web_server.asset_list("demo", "npc") == {"ok": True, "campaign_id": "demo", "kind": "npc", "assets": []}
    assert web_server.asset_lookup("demo", "asset:key") == {"ok": True, "campaign_id": "demo", "key": "asset:key"}
    assert web_server.save_asset({"key": "asset:key"}) == {"ok": True, "saved": "asset:key"}
    assert web_server.delete_asset({"key": "asset:key"}) == {"ok": True, "deleted": "asset:key"}
    assert web_server.rebuild_assets({"kind": "npc_portrait"}) == {"ok": True, "kind": "npc_portrait"}


def test_web_server_frontend_state_wrapper_calls_service(monkeypatch):
    monkeypatch.setattr(frontend_state, "frontend_state_response", lambda campaign_id="": {"ok": True, "active_campaign": campaign_id})

    assert web_server.frontend_state_response("demo") == {"ok": True, "active_campaign": "demo"}


def test_web_server_writeback_review_wrapper_calls_service(monkeypatch):
    monkeypatch.setattr(writeback_review, "writeback_review_payload", lambda campaign_id="": {"ok": True, "campaign_id": campaign_id})

    assert web_server.writeback_review_payload("demo") == {"ok": True, "campaign_id": "demo"}
