from trpg_orchestrator.json_utils import read_json
from trpg_orchestrator.memory_store import default_memory
from trpg_orchestrator.services import inventory_state_store, raw_gallery_store
from trpg_orchestrator.writeback import apply_approved_writeback, has_applied_writeback, writeback_hash
import pytest


def approved_writeback():
    return {
        "short_term_state": {
            "player": "Lee 站在门口。",
            "npcs": {},
            "location": "小卖部",
            "quest": "确认屋内是否安全",
            "resources": "",
            "injury_or_damage": "",
        },
        "long_term_memory": {},
        "new_open_threads": [],
        "closed_threads": [],
        "summary_for_recent_context": "Lee 检查了小卖部门口。",
    }


def test_approved_writeback_updates_recent_context():
    memory = default_memory("demo")

    updates = apply_approved_writeback(memory, approved_writeback())

    recent = updates["recent_context.json"]
    assert recent["last_outcome"] == "Lee 检查了小卖部门口。"
    assert recent["current_scene"]["location"] == "小卖部"
    assert recent["turn_index"] == 1


def test_writeback_hash_is_not_recorded_twice():
    memory = default_memory("demo")
    writeback = approved_writeback()
    digest = writeback_hash(writeback)

    updates = apply_approved_writeback(memory, writeback, extra_hashes=[digest])
    memory.update(updates)
    updates = apply_approved_writeback(memory, writeback, extra_hashes=[digest])

    applied = updates["recent_context.json"]["applied_writeback_hashes"]
    assert applied.count(digest) == 1
    assert has_applied_writeback({"recent_context.json": updates["recent_context.json"]}, digest)


def test_scalar_long_term_writeback_keeps_legacy_raw_entry():
    memory = default_memory("demo")
    writeback = approved_writeback()
    writeback["long_term_memory"] = {
        "world_state_updates": {
            "memory_type": "confirmed_fact",
            "certainty": "confirmed",
            "source": "audit",
            "ttl": "permanent",
            "value": "小卖部已经停电。",
        }
    }

    updates = apply_approved_writeback(memory, writeback)

    world_updates = updates["world_state.json"]["world_updates"]
    assert world_updates[0]["field"] == "world_state_updates"
    assert world_updates[0]["value"] == writeback["long_term_memory"]["world_state_updates"]
    assert "clue_history.json" not in updates


def test_observed_clue_metadata_does_not_route_to_clue_history_in_this_branch():
    memory = default_memory("demo")
    writeback = approved_writeback()
    writeback["long_term_memory"] = {
        "world_state_updates": {
            "memory_type": "observed_clue",
            "certainty": "uncertain",
            "value": "门缝里有黑水痕迹。",
        }
    }

    updates = apply_approved_writeback(memory, writeback)

    assert updates["world_state.json"]["world_updates"][0]["value"]["memory_type"] == "observed_clue"
    assert "clue_history.json" not in updates


def test_npc_memory_update_keeps_legacy_facts_bucket():
    memory = default_memory("demo")
    writeback = approved_writeback()
    writeback["long_term_memory"] = {
        "npc_memory_updates": {
            "老周": {
                "memory_type": "npc_claim",
                "certainty": "uncertain",
                "value": "他说仓库里没有人。",
            }
        }
    }

    updates = apply_approved_writeback(memory, writeback)

    npc = updates["npc_memory.json"]["npcs"]["老周"]
    assert npc["facts"][0]["value"]["memory_type"] == "npc_claim"
    assert npc["uncertain"] == []


def test_short_term_scene_metadata_does_not_create_writeback_observations():
    memory = default_memory("demo")
    writeback = approved_writeback()
    writeback["long_term_memory"] = {
        "world_state_updates": {
            "memory_type": "short_term_scene",
            "certainty": "uncertain",
            "value": "雨声让对话断断续续。",
        }
    }

    updates = apply_approved_writeback(memory, writeback)

    assert updates["world_state.json"]["world_updates"][0]["value"]["memory_type"] == "short_term_scene"
    assert "clue_history.json" not in updates
    assert "writeback_observations" not in updates["recent_context.json"]


def test_legacy_npc_memory_update_goes_to_facts():
    memory = default_memory("demo")
    writeback = approved_writeback()
    writeback["long_term_memory"] = {"npc_memory_updates": {"老周": "他说仓库里没有人。"}}

    updates = apply_approved_writeback(memory, writeback)

    npc = updates["npc_memory.json"]["npcs"]["老周"]
    assert npc["facts"][0]["value"] == "他说仓库里没有人。"
    assert npc["uncertain"] == []
    assert npc["notes"] == []
def test_state_writeback_gallery_and_inventory_use_extension_stores(tmp_path, monkeypatch):
    root = tmp_path / "campaigns"
    monkeypatch.setattr(raw_gallery_store, "CAMPAIGNS_DIR", root)
    monkeypatch.setattr(inventory_state_store, "CAMPAIGNS_DIR", root)
    memory = default_memory("demo")
    writeback = approved_writeback()
    writeback["campaign_id"] = "demo"
    writeback["gallery_assets"] = [{"id": "letter_art", "type": "item", "title": "Damp Letter", "gallery_category": "item"}]
    writeback["inventory_items"] = [{"item_id": "letter_001", "title": "Damp Letter", "state": {"status": "sealed"}}]

    updates = apply_approved_writeback(memory, writeback)

    assert "equipment_history.json" not in updates
    gallery_raw = read_json(raw_gallery_store.gallery_raw_path("demo"))
    inventory_state = read_json(inventory_state_store.inventory_state_path("demo"))
    assert gallery_raw["assets"] == writeback["gallery_assets"]
    assert inventory_state["items"][0]["item_id"] == "letter_001"


def test_director_visual_assets_persist_without_actor_gallery_writeback(tmp_path, monkeypatch):
    root = tmp_path / "campaigns"
    monkeypatch.setattr(raw_gallery_store, "CAMPAIGNS_DIR", root)
    memory = default_memory("demo")
    writeback = approved_writeback()
    writeback["campaign_id"] = "demo"
    writeback["gallery_assets"] = []
    pressure_pack = {
        "payloads": {
            "visual_assets": [
                {
                    "id": "opening_map",
                    "title": "开场地图",
                    "kind": "map",
                    "gallery_category": "map",
                    "detail": "林间空地地图。",
                    "display_zone": "gallery",
                    "canvas_spec": {"schema": "map_canvas_spec.v1", "area": "clearing"},
                }
            ]
        }
    }

    apply_approved_writeback(memory, writeback, pressure_pack=pressure_pack)

    gallery_raw = read_json(raw_gallery_store.gallery_raw_path("demo"))
    assert gallery_raw["assets"][0]["id"] == "opening_map"
    assert gallery_raw["assets"][0]["type"] == "map"
    assert gallery_raw["assets"][0]["canvas_spec"]["area"] == "clearing"


def test_pressure_pack_ignores_actor_gallery_assets_and_uses_director_payload(tmp_path, monkeypatch):
    root = tmp_path / "campaigns"
    monkeypatch.setattr(raw_gallery_store, "CAMPAIGNS_DIR", root)
    memory = default_memory("demo")
    writeback = approved_writeback()
    writeback["campaign_id"] = "demo"
    writeback["gallery_assets"] = [
        {"id": "actor_fake_card", "type": "prop", "title": "演员层假卡", "gallery_category": "prop"}
    ]
    pressure_pack = {
        "payloads": {
            "visual_assets": [
                {
                    "id": "director_real_card",
                    "title": "导演层真实卡",
                    "kind": "prop",
                    "gallery_category": "prop",
                    "display_zone": "gallery",
                    "detail": "导演层下发的真实资产。",
                    "canvas_spec": {"schema": "item_canvas_spec.v1", "archetype": "token"},
                }
            ]
        }
    }

    apply_approved_writeback(memory, writeback, pressure_pack=pressure_pack)

    gallery_raw = read_json(raw_gallery_store.gallery_raw_path("demo"))
    assert [asset["id"] for asset in gallery_raw["assets"]] == ["director_real_card"]


def test_gallery_assets_upsert_by_exact_id_replaces_whole_asset(tmp_path, monkeypatch):
    root = tmp_path / "campaigns"
    monkeypatch.setattr(raw_gallery_store, "CAMPAIGNS_DIR", root)
    raw_gallery_store.save_gallery_raw("demo", {
        "schema": raw_gallery_store.RAW_GALLERY_SCHEMA,
        "campaign_id": "demo",
        "updated_turn": 0,
        "assets": [
            {
                "id": "trace_001",
                "type": "clue",
                "title": "Old Trace",
                "gallery_category": "prop",
                "detail": "old detail",
                "payload": {"old": True},
            }
        ],
    })

    raw_gallery_store.apply_gallery_assets("demo", [
        {"id": "trace_001", "type": "map_note", "title": "Updated Trace", "gallery_category": "map"}
    ])

    gallery_raw = read_json(raw_gallery_store.gallery_raw_path("demo"))
    assert gallery_raw["assets"] == [{"id": "trace_001", "type": "map_note", "title": "Updated Trace", "gallery_category": "map"}]


def test_gallery_assets_reject_duplicate_ids_in_same_batch(tmp_path, monkeypatch):
    root = tmp_path / "campaigns"
    monkeypatch.setattr(raw_gallery_store, "CAMPAIGNS_DIR", root)

    with pytest.raises(RuntimeError, match="duplicate gallery_assets id"):
        raw_gallery_store.apply_gallery_assets("demo", [
            {"id": "trace_001", "type": "clue", "title": "Trace", "gallery_category": "prop"},
            {"id": "trace_001", "type": "clue", "title": "Trace Again", "gallery_category": "prop"},
        ])


def test_inventory_items_reject_duplicate_ids_in_same_writeback(tmp_path, monkeypatch):
    root = tmp_path / "campaigns"
    monkeypatch.setattr(raw_gallery_store, "CAMPAIGNS_DIR", root)
    monkeypatch.setattr(inventory_state_store, "CAMPAIGNS_DIR", root)
    memory = default_memory("demo")
    writeback = approved_writeback()
    writeback["campaign_id"] = "demo"
    writeback["inventory_items"] = [
        {"item_id": "rune_pendant", "title": "Rune Pendant"},
        {"item_id": "rune_pendant", "title": "Rune Pendant Updated"},
    ]

    with pytest.raises(RuntimeError, match="duplicate inventory_items item_id"):
        apply_approved_writeback(memory, writeback)


@pytest.mark.parametrize(
    ("player_action", "writeback", "gallery_type", "inventory_id"),
    [
        (
            "观察当前地点痕迹",
            {
                "gallery_assets": [{
                    "id": "current_location_trace",
                    "type": "clue",
                    "title": "当前地点痕迹",
                    "gallery_category": "prop",
                    "detail": "玩家观察到地面有近期活动痕迹。",
                }]
            },
            "clue",
            "",
        ),
        (
            "检查随身物品状态",
            {
                "inventory_items": [{
                    "item_id": "rune_pendant",
                    "title": "符文吊坠",
                    "state": {"status": "微光变弱"},
                }]
            },
            "",
            "rune_pendant",
        ),
        (
            "在地图上标记新发现入口",
            {
                "gallery_assets": [{
                    "id": "mist_entrance_map_note",
                    "type": "map_note",
                    "title": "迷雾入口标记",
                    "gallery_category": "map",
                    "detail": "玩家在地图上记录新发现的迷雾入口。",
                }]
            },
            "map_note",
            "",
        ),
        (
            "阅读一张旧纸条",
            {
                "gallery_assets": [{
                    "id": "old_note_fragment",
                    "type": "document",
                    "title": "旧纸条片段",
                    "gallery_category": "item",
                    "detail": "玩家读到一段关于入口符号的文字。",
                }]
            },
            "document",
            "",
        ),
    ],
)
def test_global_writeback_protocol_persists_four_action_classes(tmp_path, monkeypatch, player_action, writeback, gallery_type, inventory_id):
    root = tmp_path / "campaigns"
    monkeypatch.setattr(raw_gallery_store, "CAMPAIGNS_DIR", root)
    monkeypatch.setattr(inventory_state_store, "CAMPAIGNS_DIR", root)
    memory = default_memory("demo")
    payload = approved_writeback()
    payload["campaign_id"] = "demo"
    payload.update(writeback)
    payload["summary_for_recent_context"] = player_action

    apply_approved_writeback(memory, payload)

    if gallery_type:
        gallery_raw = read_json(raw_gallery_store.gallery_raw_path("demo"))
        assert gallery_raw["assets"][0]["type"] == gallery_type
    if inventory_id:
        inventory_state = read_json(inventory_state_store.inventory_state_path("demo"))
        assert inventory_state["items"][0]["item_id"] == inventory_id
