from trpg_orchestrator.memory_store import default_memory
from trpg_orchestrator.writeback import apply_approved_writeback, has_applied_writeback, normalize_writeback_entry, writeback_hash


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


def test_normalize_writeback_entry_wraps_legacy_string():
    entry = normalize_writeback_entry("门口有水迹")

    assert entry["value"] == "门口有水迹"
    assert entry["memory_type"] == "short_term_scene"
    assert entry["certainty"] == "uncertain"
    assert entry["source"] == "actor"
    assert entry["ttl"] == "scene"


def test_normalize_writeback_entry_fills_safe_defaults_and_fallbacks():
    entry = normalize_writeback_entry({"value": "门口有水迹", "memory_type": "truth", "certainty": "sure", "ttl": "forever"})

    assert entry["value"] == "门口有水迹"
    assert entry["memory_type"] == "short_term_scene"
    assert entry["certainty"] == "uncertain"
    assert entry["source"] == "actor"
    assert entry["ttl"] == "scene"


def test_confirmed_fact_confirmed_enters_long_term_fact_memory():
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
    assert world_updates[0]["value"]["value"] == "小卖部已经停电。"
    assert "clue_history.json" not in updates


def test_observed_clue_goes_to_clue_history_not_long_term_fact():
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

    assert "world_state.json" not in updates
    assert updates["clue_history.json"]["notes"][0]["value"]["memory_type"] == "observed_clue"


def test_npc_claim_does_not_enter_npc_facts():
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
    assert npc["facts"] == []
    assert npc["uncertain"][0]["value"]["memory_type"] == "npc_claim"


def test_short_term_scene_only_updates_recent_context():
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

    assert "world_state.json" not in updates
    assert "clue_history.json" not in updates
    assert updates["recent_context.json"]["writeback_observations"][0]["value"]["memory_type"] == "short_term_scene"


def test_legacy_npc_memory_update_goes_to_notes_not_facts():
    memory = default_memory("demo")
    writeback = approved_writeback()
    writeback["long_term_memory"] = {"npc_memory_updates": {"老周": "他说仓库里没有人。"}}

    updates = apply_approved_writeback(memory, writeback)

    npc = updates["npc_memory.json"]["npcs"]["老周"]
    assert npc["facts"] == []
    assert npc["uncertain"] == []
    assert npc["notes"][0]["value"]["value"] == "他说仓库里没有人。"
