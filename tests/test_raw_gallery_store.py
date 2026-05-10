from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from trpg_orchestrator import web_server
from trpg_orchestrator.json_utils import read_json
from trpg_orchestrator.services import raw_gallery_store


def gallery_payload(campaign_id: str = "demo") -> dict:
    return {
        "schema": raw_gallery_store.RAW_GALLERY_SCHEMA,
        "campaign_id": campaign_id,
        "updated_turn": 2,
        "assets": [
            {
                "id": "map_opening",
                "type": "map",
                "title": "Opening Route Map",
                "detail": "Director-authored detail",
                "display_zone": "gallery",
                "payload": {"media": {"image": "assets/map/opening.png"}},
            },
            {
                "id": "letter_001",
                "type": "item",
                "title": "Damp Letter",
            },
        ],
    }


@pytest.fixture()
def gallery_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "campaigns"
    monkeypatch.setattr(raw_gallery_store, "CAMPAIGNS_DIR", root)
    return root


def request_json(server: ThreadingHTTPServer, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    conn = HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
    headers = {"content-type": "application/json; charset=utf-8"} if body is not None else {}
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    raw = response.read().decode("utf-8")
    conn.close()
    return response.status, json.loads(raw)


@pytest.fixture()
def gallery_server(gallery_root: Path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_server.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_load_gallery_raw_missing_returns_empty(gallery_root: Path):
    payload = raw_gallery_store.load_gallery_raw("demo")

    assert payload == {
        "schema": raw_gallery_store.RAW_GALLERY_SCHEMA,
        "campaign_id": "demo",
        "updated_turn": 0,
        "assets": [],
    }


def test_save_gallery_raw_creates_extensions_directory(gallery_root: Path):
    raw_gallery_store.save_gallery_raw("demo", gallery_payload())

    assert raw_gallery_store.gallery_extensions_dir("demo").is_dir()
    assert raw_gallery_store.gallery_raw_path("demo").exists()
    assert raw_gallery_store.gallery_index_path("demo").exists()


def test_save_gallery_raw_persists_payload_without_mutating_asset_fields(gallery_root: Path):
    payload = gallery_payload()
    expected = json.loads(json.dumps(payload, ensure_ascii=False))

    saved = raw_gallery_store.save_gallery_raw("demo", payload)
    stored = read_json(raw_gallery_store.gallery_raw_path("demo"))

    assert saved == expected
    assert payload == expected
    assert stored == expected


def test_save_gallery_raw_does_not_backfill_optional_business_fields(gallery_root: Path):
    raw_gallery_store.save_gallery_raw("demo", gallery_payload())
    stored = read_json(raw_gallery_store.gallery_raw_path("demo"))

    assert stored["assets"][1] == {"id": "letter_001", "type": "item", "title": "Damp Letter"}
    assert "category" not in stored["assets"][1]
    assert "detail" not in stored["assets"][1]
    assert "display_zone" not in stored["assets"][1]
    assert "payload" not in stored["assets"][1]


def test_build_gallery_index_groups_by_id_and_type(gallery_root: Path):
    index = raw_gallery_store.build_gallery_index(gallery_payload())

    assert index == {
        "schema": raw_gallery_store.GALLERY_INDEX_SCHEMA,
        "campaign_id": "demo",
        "by_id": {"map_opening": 0, "letter_001": 1},
        "by_type": {"map": ["map_opening"], "item": ["letter_001"]},
    }


def test_build_gallery_index_does_not_modify_raw_assets(gallery_root: Path):
    payload = gallery_payload()
    expected_assets = json.loads(json.dumps(payload["assets"], ensure_ascii=False))

    raw_gallery_store.build_gallery_index(payload)

    assert payload["assets"] == expected_assets


def test_build_gallery_index_rejects_duplicate_asset_id(gallery_root: Path):
    payload = gallery_payload()
    payload["assets"][1]["id"] = "map_opening"

    with pytest.raises(RuntimeError, match="duplicate gallery_raw asset id"):
        raw_gallery_store.build_gallery_index(payload)


def test_save_gallery_raw_rejects_campaign_id_mismatch(gallery_root: Path):
    payload = gallery_payload("other")

    with pytest.raises(RuntimeError, match="campaign_id"):
        raw_gallery_store.save_gallery_raw("demo", payload)


def test_save_gallery_raw_rejects_wrong_schema(gallery_root: Path):
    payload = gallery_payload()
    payload["schema"] = "trpg.gallery_raw.v1"

    with pytest.raises(RuntimeError, match="schema"):
        raw_gallery_store.save_gallery_raw("demo", payload)


def test_save_gallery_raw_rejects_assets_not_list(gallery_root: Path):
    payload = gallery_payload()
    payload["assets"] = {}

    with pytest.raises(RuntimeError, match="assets must be list"):
        raw_gallery_store.save_gallery_raw("demo", payload)


def test_save_gallery_raw_rejects_empty_assets(gallery_root: Path):
    payload = gallery_payload()
    payload["assets"] = []

    with pytest.raises(RuntimeError, match="gallery_raw.assets must contain at least one asset"):
        raw_gallery_store.save_gallery_raw("demo", payload)


@pytest.mark.parametrize("missing", ["id", "type", "title"])
def test_save_gallery_raw_rejects_asset_missing_required_field(gallery_root: Path, missing: str):
    payload = gallery_payload()
    payload["assets"][0].pop(missing)

    with pytest.raises(RuntimeError, match="missing required fields"):
        raw_gallery_store.save_gallery_raw("demo", payload)


@pytest.mark.parametrize("field", ["id", "type", "title"])
def test_save_gallery_raw_rejects_asset_required_field_when_not_nonempty_string(gallery_root: Path, field: str):
    payload = gallery_payload()
    payload["assets"][0][field] = 123

    with pytest.raises(RuntimeError, match="missing required fields"):
        raw_gallery_store.save_gallery_raw("demo", payload)


def test_extensions_gallery_get_returns_raw_and_index(gallery_server: ThreadingHTTPServer):
    status, payload = request_json(gallery_server, "GET", "/api/extensions/gallery?campaign_id=demo")

    assert status == 200
    assert payload["ok"] is True
    assert payload["campaign_id"] == "demo"
    assert payload["raw"] == raw_gallery_store.empty_gallery_raw("demo")
    assert payload["index"] == {
        "schema": raw_gallery_store.GALLERY_INDEX_SCHEMA,
        "campaign_id": "demo",
        "by_id": {},
        "by_type": {},
    }


def test_extensions_gallery_post_saves_raw_and_index(gallery_server: ThreadingHTTPServer):
    raw = gallery_payload()

    status, payload = request_json(gallery_server, "POST", "/api/extensions/gallery", {
        "campaign_id": "demo",
        "gallery": raw,
    })

    assert status == 200
    assert payload["ok"] is True
    assert payload["raw"] == raw
    assert payload["index"]["by_id"] == {"map_opening": 0, "letter_001": 1}
    assert read_json(raw_gallery_store.gallery_raw_path("demo")) == raw
    assert read_json(raw_gallery_store.gallery_index_path("demo")) == payload["index"]
