import json
import re

from trpg_orchestrator.capability_resolver import build_capability_plan
from trpg_orchestrator.config import PROMPTS_DIR
from trpg_orchestrator.encoding_utils import read_runtime_text
from trpg_orchestrator.memory_selector import select_memory_for_actor, select_memory_for_director
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


def _director_digest_memory() -> dict:
    memory = default_memory("demo")
    memory["campaign_profile.json"].update({
        "genre": "mystery",
        "tone": "quiet",
        "premise": "Investigate a shifting fog entrance.",
        "director_setup": {"heavy": "director_setup should not be sent"},
        "campaign_taxonomy": {"heavy": "campaign_taxonomy should not be sent"},
        "character_attribute_schema": {"heavy": "character_attribute_schema should not be sent"},
        "render_rules": {"heavy": "render_rules should not be sent"},
        "custom_libraries": {"heavy": "custom_libraries should not be sent"},
        "initial_assets": {
            "initial_map_canvas": {
                "map_route": {
                    "title": "Fog Path",
                    "nodes": [{"label": "Clearing", "canvas_draw_instructions": "should not be sent"}],
                },
                "canvas_draw_instructions": "should not be sent",
            },
            "initial_cg": {
                "generation_instruction": "A low fog line under dark trees.",
                "cg_prompt": "should not be sent",
            },
            "visual_contract_candidates": ["should not be sent"],
        },
    })
    memory["campaign_direction.json"].update({
        "story_blueprint_patch": {"future": "should not be sent"},
    })
    memory["story_progress.json"].update({
        "current_chapter_id": "chapter_1",
        "current_phase_id": "phase_1",
        "current_node_id": "node_fog",
        "turns_in_node": 2,
    })
    memory["story_blueprint.json"].update({
        "chapters": [
            {
                "chapter_id": "chapter_1",
                "title": "Fog Chapter",
                "nodes": [
                    {
                        "node_id": "node_fog",
                        "title": "Fog Entrance",
                        "goal": "Confirm the entrance without revealing its source.",
                        "beat_checklist": ["observe", "mark_map"],
                        "next_nodes": ["node_tracks"],
                        "requires_deep_instruction": False,
                    }
                ],
            }
        ],
    })
    return memory


def _json_after_heading(prompt: str, heading: str) -> dict:
    heading_index = prompt.find(heading)
    assert heading_index >= 0, f"missing heading {heading}"
    match = re.search(r"```json\n(.*?)\n```", prompt[heading_index:], re.S)
    assert match, f"missing JSON section after {heading}"
    return json.loads(match.group(1))


WRITEBACK_SEMANTIC_TERMS = (
    "memory_type",
    "certainty",
    "ttl",
    "confirmed_fact",
    "observed_clue",
    "npc_claim",
)


def test_actor_writeback_rules_do_not_request_memory_semantic_fields():
    text = read_runtime_text(PROMPTS_DIR / "Actor" / "actor_writeback_rules.md")

    for term in WRITEBACK_SEMANTIC_TERMS:
        assert term not in text


def test_build_actor_prompt_does_not_request_memory_semantic_fields():
    memory = default_memory("demo")
    prompt = build_chatgpt_input("demo", "继续", memory, _pressure_pack(), _plan(["base_actor"]))

    for term in WRITEBACK_SEMANTIC_TERMS:
        assert term not in prompt


def test_build_actor_prompt_uses_min_style_and_turn_title_contract():
    memory = default_memory("demo")
    prompt = build_chatgpt_input("demo", "继续", memory, _pressure_pack(), _plan(["base_actor"]))

    assert "## Prompt Module: actor_style_min" in prompt
    assert "Actor Deep Style Rules" not in prompt
    assert "Output strict JSON only: turn_title, blocks, summary, and state_writeback. No text outside JSON." in prompt
    assert "`state_writeback` must always be a JSON object with these required keys" in prompt
    assert "`new_open_threads`: array. Use `[]` if no new open thread was visibly introduced." in prompt
    assert "`closed_threads`: array. Use `[]` if no thread was visibly closed." in prompt
    assert '"new_open_threads": []' in prompt
    assert '"closed_threads": []' in prompt
    assert "every choice must be an object with id, label, and risk strings, never a plain string" in prompt
    assert '"choices": [' in prompt
    assert '"risk":' in prompt


def test_actor_writeback_rules_require_thread_arrays():
    text = read_runtime_text(PROMPTS_DIR / "Actor" / "actor_writeback_rules.md")

    assert "`state_writeback` must always include `short_term_state`, `long_term_memory`, `new_open_threads`, and `closed_threads`." in text
    assert "output `new_open_threads: []`" in text
    assert "output `closed_threads: []`" in text


def test_actor_prompt_contains_global_gallery_and_inventory_writeback_protocol():
    memory = default_memory("demo")
    plan = build_capability_plan("demo", "观察当前地点痕迹", memory)
    prompt = build_chatgpt_input("demo", "观察当前地点痕迹", memory, _pressure_pack(), plan)

    assert "state_writeback.gallery_assets" in prompt
    assert "state_writeback.inventory_items" in prompt
    assert "Each `gallery_assets` entry must include non-empty string `id`, `type`, and `title`." in prompt
    assert "Each `inventory_items` entry must include non-empty string `item_id` and `title`." in prompt
    assert "payloads.gallery_updates" not in prompt
    assert "payloads.inventory_updates" not in prompt
    assert "dossier evidence for review" not in prompt
    assert "dossier as the gallery fact source" not in prompt
    assert "allow_gallery_update" not in repr(plan)
    assert "allow_inventory_update" not in repr(plan)


def test_global_writeback_protocol_is_visible_for_multiple_action_types():
    memory = default_memory("demo")
    actions = [
        "观察当前地点痕迹",
        "检查随身物品状态",
        "在地图上标记新发现入口",
        "阅读一张旧纸条",
    ]

    for action in actions:
        plan = build_capability_plan("demo", action, memory)
        prompt = build_chatgpt_input("demo", action, memory, _pressure_pack(), plan)
        assert "state_writeback.gallery_assets" in prompt
        assert "state_writeback.inventory_items" in prompt
        assert "allow_gallery_update" not in repr(plan)
        assert "allow_inventory_update" not in repr(plan)


def test_v4_audit_prompt_preserves_required_writeback_schema():
    text = read_runtime_text(PROMPTS_DIR / "Director" / "v4_audit_prompt.md")

    assert "`approved_writeback` must follow the same backend schema as actor `state_writeback`." in text
    assert "`new_open_threads`: array. This is an authorized core writeback field" in text
    assert "`closed_threads`: array. This is an authorized core writeback field" in text
    assert "do not delete required schema keys" in text
    assert '"new_open_threads": []' in text
    assert '"closed_threads": []' in text


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


def test_build_director_prompt_uses_memory_digest_in_selected_memory():
    memory = _director_digest_memory()
    plan = _plan(["base_director"])
    prompt = build_director_user_prompt("demo", "continue", memory, plan)
    selected_memory = _json_after_heading(prompt, "## Selected Director Memory")

    assert set(selected_memory) == {
        "campaign_brief",
        "current_story_anchor",
        "current_runtime",
        "player_brief",
        "companion_brief",
        "node_brief",
        "thread_brief",
        "asset_refs",
        "forbidden_brief",
    }
    assert selected_memory["campaign_brief"]["genre"] == "mystery"
    assert selected_memory["current_story_anchor"]["current_node_id"] == "node_fog"
    assert selected_memory["node_brief"]["goal"] == "Confirm the entrance without revealing its source."
    assert "Fog Path" in selected_memory["asset_refs"]["existing_map_summary"]


def test_build_director_prompt_digest_excludes_raw_memory_and_heavy_fields():
    memory = _director_digest_memory()
    prompt = build_director_user_prompt("demo", "continue", memory, _plan(["base_director"]))
    selected_memory_text = json.dumps(_json_after_heading(prompt, "## Selected Director Memory"), ensure_ascii=False)

    for raw_key in (
        "campaign_profile.json",
        "campaign_direction.json",
        "story_blueprint.json",
        "recent_context.json",
        "story_progress.json",
        "main_threads.json",
    ):
        assert raw_key not in selected_memory_text
    for heavy_key in (
        "director_setup",
        "initial_assets",
        "initial_map_canvas",
        "canvas_draw_instructions",
        "render_rules",
        "visual_contract_candidates",
        "cg_prompt",
        "campaign_taxonomy",
        "character_attribute_schema",
        "story_blueprint_patch",
        "custom_libraries",
    ):
        assert heavy_key not in selected_memory_text


def test_build_chatgpt_input_uses_actor_digest_without_director_digest_shape():
    memory = _director_digest_memory()
    prompt = build_chatgpt_input("demo", "continue", memory, _pressure_pack(), _plan(["base_actor"]))
    visible_memory = _json_after_heading(prompt, "## Visible Memory For This Turn")

    assert "actor_campaign_brief" in visible_memory
    assert "visible_runtime" in visible_memory
    assert "visible_player_state" in visible_memory
    assert "campaign_profile.json" not in visible_memory
    assert "campaign_brief" not in visible_memory
    assert "node_brief" not in visible_memory


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


def test_select_memory_for_director_keeps_raw_memory_shape_after_digest_switch():
    memory = _director_digest_memory()
    selected = select_memory_for_director(memory, _plan(["base_director"]))

    assert "campaign_profile.json" in selected
    assert "story_blueprint.json" in selected
    assert "campaign_brief" not in selected


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
