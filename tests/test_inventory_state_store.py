from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from trpg_orchestrator import web_server
from trpg_orchestrator.json_utils import read_json
from trpg_orchestrator.services import inventory_state_store


def item_payload(item_id: str = "letter_001", title: str = "Damp Letter", **extra: object) -> dict:
    payload = {
        "item_id": item_id,
        "title": title,
        "state": {"status": "sealed"},
        "payload": {"detail": "Director-authored note"},
    }
    payload.update(extra)
    return payload


@pytest.fixture()
def inventory_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "campaigns"
    monkeypatch.setattr(inventory_state_store, "CAMPAIGNS_DIR", root)
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
def inventory_server(inventory_root: Path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_server.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_load_inventory_state_and_events_missing_return_empty(inventory_root: Path):
    assert inventory_state_store.load_inventory_state("demo") == {
        "schema": inventory_state_store.INVENTORY_STATE_SCHEMA,
        "campaign_id": "demo",
        "updated_turn": 0,
        "items": [],
    }
    assert inventory_state_store.load_inventory_events("demo") == {
        "schema": inventory_state_store.INVENTORY_EVENTS_SCHEMA,
        "campaign_id": "demo",
        "events": [],
    }


def test_apply_inventory_payload_rejects_missing_item_id(inventory_root: Path):
    payload = item_payload()
    payload.pop("item_id")

    with pytest.raises(RuntimeError, match="item_id"):
        inventory_state_store.apply_inventory_payload("demo", payload)


def test_apply_inventory_payload_rejects_missing_title(inventory_root: Path):
    payload = item_payload()
    payload.pop("title")

    with pytest.raises(RuntimeError, match="title"):
        inventory_state_store.apply_inventory_payload("demo", payload)


def test_new_item_id_creates_item_card(inventory_root: Path):
    inventory_state_store.apply_inventory_payload("demo", item_payload())

    state = read_json(inventory_state_store.inventory_state_path("demo"))
    assert state["items"] == [item_payload()]


def test_classify_inventory_change_returns_explicit_actions(inventory_root: Path):
    current = inventory_state_store.empty_inventory_state("demo")
    assert inventory_state_store.classify_inventory_change(current, item_payload("coin_001", "Coin"))["action"] == "create_new"

    current["items"].append(item_payload("coin_001", "Coin"))
    assert inventory_state_store.classify_inventory_change(current, item_payload("coin_001", "Coin"))["action"] == "update_existing"
    assert inventory_state_store.classify_inventory_change(current, item_payload("coin_split", "Split Coin", source_item_id="coin_001"))["action"] == "create_derived"


def test_existing_item_id_updates_original_item(inventory_root: Path):
    inventory_state_store.apply_inventory_payload("demo", item_payload(state={"status": "sealed", "charges": 1}))

    inventory_state_store.apply_inventory_payload("demo", {
        "item_id": "letter_001",
        "title": "Damp Letter",
        "state": {"status": "opened"},
        "payload": {"detail": "Opened by the player"},
        "condition": "wet",
    })

    state = inventory_state_store.load_inventory_state("demo")
    assert len(state["items"]) == 1
    item = state["items"][0]
    assert item["title"] == "Damp Letter"
    assert item["state"] == {"status": "opened", "charges": 1}
    assert item["payload"] == {"detail": "Opened by the player"}
    assert item["condition"] == "wet"


def test_state_field_uses_shallow_merge(inventory_root: Path):
    inventory_state_store.apply_inventory_payload("demo", item_payload("coin_001", "Coin", state={"count": 1, "status": "fresh"}))

    inventory_state_store.apply_inventory_payload("demo", item_payload("coin_001", "Coin", state={"status": "spent", "note": None}))

    item = inventory_state_store.load_inventory_state("demo")["items"][0]
    assert item["state"] == {"count": 1, "status": "spent", "note": None}


def test_payload_field_uses_shallow_merge(inventory_root: Path):
    inventory_state_store.apply_inventory_payload("demo", item_payload("coin_001", "Coin", payload={"detail": "old", "rarity": "low"}))

    inventory_state_store.apply_inventory_payload("demo", item_payload("coin_001", "Coin", payload={"detail": "new", "flag": None}))

    item = inventory_state_store.load_inventory_state("demo")["items"][0]
    assert item["payload"] == {"detail": "new", "rarity": "low", "flag": None}


def test_remove_fields_deletes_explicit_top_level_field(inventory_root: Path):
    inventory_state_store.apply_inventory_payload("demo", item_payload("coin_001", "Coin", condition="wet"))

    inventory_state_store.apply_inventory_payload("demo", item_payload("coin_001", "Coin", remove_fields=["condition"]))

    item = inventory_state_store.load_inventory_state("demo")["items"][0]
    assert "condition" not in item


def test_source_item_id_hit_creates_derived_item(inventory_root: Path):
    inventory_state_store.apply_inventory_payload("demo", item_payload("ore_001", "Silver Ore"))

    inventory_state_store.apply_inventory_payload("demo", item_payload(
        "ingot_001",
        "Refined Ingot",
        source_item_id="ore_001",
        state={"status": "refined"},
    ))

    state = inventory_state_store.load_inventory_state("demo")
    assert [item["item_id"] for item in state["items"]] == ["ore_001", "ingot_001"]
    assert state["items"][1]["source_item_id"] == "ore_001"


def test_source_item_id_missing_is_rejected(inventory_root: Path):
    with pytest.raises(RuntimeError, match="source_item_id not found"):
        inventory_state_store.apply_inventory_payload("demo", item_payload("ingot_001", "Refined Ingot", source_item_id="ore_404"))


def test_duplicate_item_id_in_state_is_rejected(inventory_root: Path):
    state = inventory_state_store.empty_inventory_state("demo")
    state["items"] = [
        item_payload("coin_001", "Coin"),
        item_payload("coin_001", "Coin Copy"),
    ]

    with pytest.raises(RuntimeError, match="duplicate inventory item_id"):
        inventory_state_store.save_inventory_state("demo", state)


def test_title_similarity_does_not_merge_items(inventory_root: Path):
    inventory_state_store.apply_inventory_payload("demo", item_payload("letter_a", "Damp Letter"))
    inventory_state_store.apply_inventory_payload("demo", item_payload("letter_b", "Damp Letter"))

    state = inventory_state_store.load_inventory_state("demo")
    assert [item["item_id"] for item in state["items"]] == ["letter_a", "letter_b"]


def test_category_or_type_guessing_does_not_merge_items(inventory_root: Path):
    inventory_state_store.apply_inventory_payload("demo", item_payload("key_a", "Iron Key", category="key", type="tool"))
    inventory_state_store.apply_inventory_payload("demo", item_payload("key_b", "Another Key", category="key", type="tool"))

    state = inventory_state_store.load_inventory_state("demo")
    assert [item["item_id"] for item in state["items"]] == ["key_a", "key_b"]


def test_update_writes_inventory_events(inventory_root: Path):
    inventory_state_store.apply_inventory_payload("demo", item_payload("coin_001", "Coin"))
    inventory_state_store.apply_inventory_payload("demo", item_payload("coin_001", "Coin", state={"status": "spent"}))

    events = inventory_state_store.load_inventory_events("demo")
    assert [event["action"] for event in events["events"]] == ["create_new", "update_existing"]
    assert events["events"][1]["item_id"] == "coin_001"
    assert "created_at" in events["events"][1]


def test_extensions_inventory_get_returns_state_and_events(inventory_server: ThreadingHTTPServer):
    status, payload = request_json(inventory_server, "GET", "/api/extensions/inventory?campaign_id=demo")

    assert status == 200
    assert payload["ok"] is True
    assert payload["campaign_id"] == "demo"
    assert payload["state"] == inventory_state_store.empty_inventory_state("demo")
    assert payload["events"] == inventory_state_store.empty_inventory_events("demo")


def test_extensions_inventory_post_apply_creates_item(inventory_server: ThreadingHTTPServer):
    status, payload = request_json(inventory_server, "POST", "/api/extensions/inventory/apply", {
        "campaign_id": "demo",
        "item": item_payload("coin_001", "Coin", state={"count": 1}),
    })

    assert status == 200
    assert payload["state"]["items"][0]["item_id"] == "coin_001"


def test_extensions_inventory_post_apply_updates_item(inventory_server: ThreadingHTTPServer):
    request_json(inventory_server, "POST", "/api/extensions/inventory/apply", {
        "campaign_id": "demo",
        "item": item_payload("coin_001", "Coin", state={"count": 1}),
    })

    status, payload = request_json(inventory_server, "POST", "/api/extensions/inventory/apply", {
        "campaign_id": "demo",
        "item": item_payload("coin_001", "Coin", state={"count": 2}),
    })

    assert status == 200
    assert payload["state"]["items"][0]["state"]["count"] == 2
    assert [event["action"] for event in payload["events"]["events"]] == ["create_new", "update_existing"]
