from trpg_orchestrator.capability_resolver import build_capability_plan
from trpg_orchestrator.memory_selector import select_memory_for_actor
from trpg_orchestrator.memory_store import default_memory
from trpg_orchestrator.prompt_builder import build_actor_capability_view, build_chatgpt_input, build_director_user_prompt
from trpg_orchestrator.prompt_module_registry import get_prompt_module_warnings, select_prompt_modules
from trpg_orchestrator.writeback import apply_approved_writeback


def _output_requests() -> dict:
    return {
        "story_progress": {"mode": "update", "trigger": "system_required", "reason": "test"},
        "map": {"mode": "keep_previous", "trigger": "none", "reason": "test"},
        "visual_assets": {"mode": "none", "trigger": "none", "reason": "test"},
        "gallery": {"mode": "none", "trigger": "none", "reason": "test"},
        "inventory": {"mode": "none", "trigger": "none", "reason": "test"},
        "character_card": {"mode": "none", "trigger": "none", "reason": "test"},
        "dossier": {"mode": "none", "trigger": "none", "reason": "test"},
        "dice_or_check": {"mode": "none", "trigger": "none", "reason": "test"},
        "canvas_jobs": {"mode": "none", "trigger": "none", "reason": "test"},
    }


def _plan(capabilities: list[str] | None = None) -> dict:
    return {
        "loaded_capabilities": capabilities or ["base_actor", "base_director"],
        "prompt_modules": {"director": [], "actor": [], "audit": [], "excluded": []},
        "memory_refs": {"director": [], "actor_visible": [], "audit": []},
        "warnings": [],
    }


def _pressure_pack(**extra) -> dict:
    return {"output_requests": _output_requests(), **extra}


def _writeback() -> dict:
    return {
        "summary_for_recent_context": "继续推进。",
        "short_term_state": {"location": "村口"},
        "long_term_memory": {},
        "new_open_threads": [],
        "closed_threads": [],
    }


def test_build_actor_prompt_uses_min_style_and_turn_title_contract():
    memory = default_memory("demo")
    prompt = build_chatgpt_input("demo", "继续", memory, _pressure_pack(), _plan(["base_actor"]))

    assert "## Prompt Module: actor_style_min" in prompt
    assert "Actor Deep Style Rules" not in prompt
    assert "Output strict JSON only: turn_title, blocks, summary, and state_writeback. No text outside JSON." in prompt


def test_build_actor_prompt_uses_min_npc_voice_without_long_voice_for_npc_present():
    memory = default_memory("demo")
    prompt = build_chatgpt_input("demo", "和守林人交谈", memory, _pressure_pack(), _plan(["base_actor", "npc_present"]))

    assert "## Prompt Module: actor_npc_voice_min" in prompt
    assert "NPC Performance Rules" not in prompt


def test_build_actor_prompt_loads_long_npc_voice_only_for_deep_dispatch():
    memory = default_memory("demo")
    pressure_pack = _pressure_pack(actor_dispatch={"modules": [], "heavy_modules": ["npc_voice_deep"]})
    prompt = build_chatgpt_input("demo", "继续对峙", memory, pressure_pack, _plan(["base_actor"]))

    assert "## Prompt Module: npc_voice_rules" in prompt
    assert "NPC Performance Rules" in prompt


def test_actor_modules_without_dispatch_keep_existing_trigger_logic():
    modules = select_prompt_modules(_plan(["base_actor", "inventory"]), "actor", _pressure_pack())

    assert "actor_context_rules" in modules
    assert "actor_inventory_rules" in modules
    assert "actor_style_min" in modules
    assert "style_core" not in modules


def test_npc_present_uses_min_voice_without_long_voice_rules():
    modules = select_prompt_modules(_plan(["base_actor", "npc_present"]), "actor", _pressure_pack())

    assert "actor_npc_voice_min" in modules
    assert "npc_voice_rules" not in modules


def test_actor_dispatch_min_modules_select_min_prompt_modules():
    modules = select_prompt_modules(
        _plan(["base_actor"]),
        "actor",
        _pressure_pack(actor_dispatch={"modules": ["style_min", "npc_voice_min"], "heavy_modules": []}),
    )

    assert "actor_style_min" in modules
    assert "actor_npc_voice_min" in modules


def test_actor_dispatch_heavy_npc_voice_selects_long_rules_only_when_requested():
    light_modules = select_prompt_modules(
        _plan(["base_actor", "npc_present", "npc_voice"]),
        "actor",
        _pressure_pack(actor_dispatch={"modules": ["npc_voice_min"], "heavy_modules": []}),
    )
    heavy_modules = select_prompt_modules(
        _plan(["base_actor"]),
        "actor",
        _pressure_pack(actor_dispatch={"modules": [], "heavy_modules": ["npc_voice_deep"]}),
    )

    assert "npc_voice_rules" not in light_modules
    assert "actor_npc_voice_min" in light_modules
    assert "npc_voice_rules" in heavy_modules


def test_preload_capabilities_select_min_director_payload_modules():
    visual_modules = select_prompt_modules(_plan(["base_director", "visual_preload"]), "director", _pressure_pack())
    map_modules = select_prompt_modules(_plan(["base_director", "map_preload"]), "director", _pressure_pack())

    assert "director_visual_payload_min" in visual_modules
    assert "director_map_payload_min" in map_modules


def test_orchestration_forecast_writeback_preloads_next_turn_capability():
    memory = default_memory("demo")
    memory["recent_context.json"]["turn_index"] = 3
    pressure_pack = _pressure_pack(orchestration_forecast={
        "for_backend_only": True,
        "expires_after_turns": 2,
        "valid_until_node_id": "",
        "hotload_next_turn": {
            "director_modules": ["director_visual_payload_min"],
            "actor_modules": ["npc_voice_deep"],
            "payload_modules": ["director_map_payload_min"],
        },
        "upcoming_assets": [{"id": "future", "hidden_reason": "secret"}],
    })

    updates = apply_approved_writeback(memory, _writeback(), pressure_pack=pressure_pack)
    memory.update(updates)
    plan = build_capability_plan("demo", "继续", memory)

    assert "visual_preload" in plan["loaded_capabilities"]
    assert "map_preload" in plan["loaded_capabilities"]
    assert "dialogue_heavy_preload" in plan["loaded_capabilities"]
    forecast = updates["recent_context.json"]["orchestration_forecast"]
    assert forecast["source_turn"] == 4
    assert forecast["expires_at_turn"] == 6
    assert "hidden_reason" not in forecast["upcoming_assets"][0]
    assert "visual_assets" not in plan["loaded_capabilities"]
    assert "map" not in plan["loaded_capabilities"]
    assert plan["output_contract"]["allow_visual_assets"] is False
    assert plan["output_contract"]["allow_map_payload"] is False


def test_build_actor_prompt_does_not_leak_forecast_fields():
    memory = default_memory("demo")
    memory["recent_context.json"]["orchestration_forecast"] = {
        "for_backend_only": True,
        "hotload_next_turn": {"actor_modules": ["npc_voice_deep"]},
        "upcoming_assets": [{"id": "x", "future_asset": "secret"}],
        "hidden_reason": "backend only",
        "future_node": "node_secret",
    }

    prompt = build_chatgpt_input("demo", "继续", memory, _pressure_pack(), _plan(["base_actor"]))

    for forbidden in (
        "orchestration_forecast",
        "hotload_next_turn",
        "upcoming_assets",
        "hidden_reason",
        "future_node",
        "future_asset",
    ):
        assert forbidden not in prompt


def test_build_director_prompt_preloads_visual_and_map_rules_without_authorizing_payloads():
    memory = default_memory("demo")
    memory["recent_context.json"]["turn_index"] = 2
    memory["recent_context.json"]["orchestration_forecast"] = {
        "for_backend_only": True,
        "source_turn": 2,
        "expires_at_turn": 4,
        "valid_until_node_id": "",
        "hotload_next_turn": {
            "director_modules": ["director_visual_payload_min"],
            "payload_modules": ["director_map_payload_min"],
        },
    }

    plan = build_capability_plan("demo", "继续", memory)
    prompt = build_director_user_prompt("demo", "继续", memory, plan)

    assert "visual_preload" in plan["loaded_capabilities"]
    assert "map_preload" in plan["loaded_capabilities"]
    assert "## Prompt Module: director_visual_payload_min" in prompt
    assert "## Prompt Module: director_map_payload_min" in prompt
    assert plan["output_contract"]["allow_visual_assets"] is False
    assert plan["output_contract"]["allow_map_payload"] is False


def test_orchestration_forecast_ignored_when_expired_or_node_mismatch():
    expired = default_memory("demo")
    expired["recent_context.json"]["turn_index"] = 5
    expired["recent_context.json"]["orchestration_forecast"] = {
        "for_backend_only": True,
        "source_turn": 1,
        "expires_at_turn": 4,
        "hotload_next_turn": {"director_modules": ["director_visual_payload_min"]},
    }
    expired_plan = build_capability_plan("demo", "继续", expired)

    mismatch = default_memory("demo")
    mismatch["recent_context.json"]["turn_index"] = 2
    mismatch["story_progress.json"]["current_node_id"] = "node_a"
    mismatch["recent_context.json"]["orchestration_forecast"] = {
        "for_backend_only": True,
        "source_turn": 1,
        "expires_at_turn": 3,
        "valid_until_node_id": "node_b",
        "hotload_next_turn": {"director_modules": ["director_map_payload_min"]},
    }
    mismatch_plan = build_capability_plan("demo", "继续", mismatch)

    assert "visual_preload" not in expired_plan["loaded_capabilities"]
    assert "map_preload" not in mismatch_plan["loaded_capabilities"]


def test_actor_memory_does_not_include_forecast_fields():
    memory = default_memory("demo")
    memory["recent_context.json"]["orchestration_forecast"] = {
        "for_backend_only": True,
        "hotload_next_turn": {"actor_modules": ["npc_voice_deep"]},
        "upcoming_assets": [{"id": "x", "future_asset": "secret"}],
        "hidden_reason": "backend only",
    }
    memory["recent_context.json"]["actor_dispatch"] = {"modules": ["style_min"]}

    selected = select_memory_for_actor(memory, _plan(["base_actor"]), _pressure_pack())
    text = repr(selected)

    assert "orchestration_forecast" not in text
    assert "actor_dispatch" not in text
    assert "hotload_next_turn" not in text
    assert "upcoming_assets" not in text
    assert "future_asset" not in text
    assert "hidden_reason" not in text


def test_preload_capabilities_are_not_actor_visible_tools():
    view = build_actor_capability_view({
        "loaded_capabilities": ["base_actor", "map_preload", "dialogue_heavy_preload", "inventory"],
    })

    assert "inventory" in view["visible_capabilities"]
    assert "map_preload" not in view["visible_capabilities"]
    assert "dialogue_heavy_preload" not in view["visible_capabilities"]


def test_unknown_dispatch_and_forecast_modules_warn_without_crashing():
    plan = _plan(["base_actor"])
    modules = select_prompt_modules(
        plan,
        "actor",
        _pressure_pack(actor_dispatch={"modules": ["unknown_dispatch"], "heavy_modules": []}),
    )
    warnings = get_prompt_module_warnings()

    assert isinstance(modules, list)
    assert "unknown actor_dispatch module ignored: unknown_dispatch" in warnings

    memory = default_memory("demo")
    memory["recent_context.json"]["orchestration_forecast"] = {
        "for_backend_only": True,
        "source_turn": 1,
        "expires_at_turn": 2,
        "hotload_next_turn": {"director_modules": ["unknown_forecast"]},
    }
    capability_plan = build_capability_plan("demo", "继续", memory)

    assert "unknown orchestration_forecast module ignored: unknown_forecast" in capability_plan["warnings"]
