import json
import re
from copy import deepcopy

from trpg_orchestrator.memory_selector import build_actor_memory_digest, select_memory_for_actor
from trpg_orchestrator.prompt_builder import build_chatgpt_input


def _plan(capabilities: list[str] | None = None) -> dict:
    return {
        "loaded_capabilities": capabilities or ["base_actor", "npc_present", "inventory"],
        "prompt_modules": {"director": [], "actor": [], "audit": [], "excluded": []},
        "memory_refs": {"director": [], "actor_visible": [], "audit": []},
        "warnings": [],
    }


def _pressure_pack() -> dict:
    return {
        "progress_control": {
            "current_chapter_id": "chapter_1",
            "current_phase_id": "phase_a",
            "current_node_id": "node_fog",
            "current_node_name": "迷雾入口",
            "node_goal": "确认入口存在但不揭示来源。",
            "beat_targets_this_turn": ["observe_tracks"],
            "pace_command": "normal",
            "legal_next_nodes": ["node_follow_tracks"],
            "must_not_repeat": ["不要重复发现同一枚脚印"],
        },
        "output_requests": {},
    }


def _memory() -> dict:
    return {
        "campaign_profile.json": {
            "campaign_id": "actor_digest_campaign",
            "title": "雾门测试",
            "name": "雾门测试",
            "genre": "mystery",
            "tone": "quiet dread",
            "premise": "玩家在密林中确认一个会移动的入口。" * 30,
            "protagonist_patch": {
                "name": "沈星",
                "role": "调查者",
                "visible_summary": "习惯把异常写进地图边注。",
                "hidden_truth": "不要进入 digest",
            },
            "companion_config": {
                "companion_enabled": True,
                "companion_name": "洛",
                "companion_role": "向导",
                "companion_personality": "沉默",
                "secret_identity": "不要进入 digest",
            },
            "director_setup": {"huge": "不要进入 digest" * 300},
            "setup_patch": {"huge": "不要进入 digest"},
            "prompt_routing": {"huge": "不要进入 digest"},
            "story_memory_seed": {"huge": "不要进入 digest" * 200},
            "initial_assets": {
                "initial_map_canvas": {
                    "canvas_draw_instructions": "不要进入 digest" * 200,
                },
                "initial_cg": {
                    "generation_instruction": "低雾压住树线。",
                    "cg_prompt": "不要进入 digest",
                },
                "initial_items": [
                    {
                        "item_id": "rune_pendant",
                        "title": "符文吊坠",
                        "type": "token",
                        "state": "cool",
                        "description": "表面有微弱划痕。",
                        "item_canvas_rules": "不要进入 digest",
                    }
                ],
                "visual_contract_candidates": ["不要进入 digest"],
            },
            "render_rules": {"huge": "不要进入 digest"},
            "campaign_taxonomy": {"huge": "不要进入 digest"},
            "character_attribute_schema": {"huge": "不要进入 digest"},
            "custom_libraries": {"huge": "不要进入 digest" * 200},
            "mechanics": {"full": "不要进入 digest"},
            "safety_lines": ["不写露骨暴力"],
            "tone_limits": ["克制"],
        },
        "style_profile.json": {
            "language": "zh-CN",
            "prose_tone": "冷静、低压",
            "narration_style": "短句推进",
            "dialogue_style": "少量对白",
            "avoid": ["夸张吐槽"],
            "long_style_archive": "不要进入 digest" * 200,
        },
        "recent_context.json": {
            "campaign_id": "actor_digest_campaign",
            "turn_index": 8,
            "recent_summary": ["玩家来到林间空地。"],
            "current_scene": {
                "location": "林间空地",
                "active_npcs": [{"npc_id": "luo", "name": "洛", "visible_status": "在雾边等待"}],
                "immediate_pressure": "雾门忽明忽暗。",
            },
            "last_player_action": "观察痕迹",
            "last_outcome": "脚印在雾边中断。",
            "short_term_state": {"fog_density": "high"},
            "visible_relationship_summary": "洛认识这片林子，但不愿主动解释。",
            "last_visible_dialogue_summary": "洛提醒玩家不要踩进雾线。",
            "orchestration_forecast": {"future_node": "不要进入 digest"},
            "actor_dispatch": {"hotload_next_turn": "不要进入 digest"},
            "upcoming_assets": [{"future_asset": "不要进入 digest", "hidden_reason": "不要进入 digest"}],
            "applied_writeback_hashes": ["不要进入 digest"],
        },
        "player_state.json": {
            "identity": {"name": "沈星", "role": "调查者"},
            "current_condition": "警觉",
            "visible_status": ["鞋底沾有湿泥"],
            "equipment_summary": "地图、铅笔、符文吊坠",
            "known_items": [
                {
                    "item_id": "rune_pendant",
                    "title": "符文吊坠",
                    "type": "token",
                    "state": "cool",
                    "visible_description": "表面有微弱划痕。",
                    "asset_key": "不要进入 digest",
                    "image_prompt": "不要进入 digest",
                }
            ],
            "current_location": "林间空地",
            "visible_flags": ["发现雾门"],
            "player_owned_unknowns": ["吊坠用途未明"],
            "hidden_motive": "不要进入 digest",
            "director_notes": "不要进入 digest",
            "future_nodes": ["不要进入 digest"],
        },
        "forbidden_changes.json": {
            "global_forbidden": ["不要替玩家做决定"],
            "campaign_specific_forbidden": ["不要确认雾门来源"],
            "unconfirmed_should_not_be_written_as_fact": ["雾门是否安全"],
            "tone_limits": ["不要转成喜剧"],
            "safety_lines": ["不写露骨暴力"],
            "secrets_not_to_reveal": ["雾门来自同伴记忆"],
            "forbidden_reveals": ["不要进入 digest"],
        },
        "npc_memory.json": {
            "visible_relationship_summary": "洛和主角像旧识。",
            "last_visible_dialogue_summary": "洛说雾里有路。",
            "hidden_motive": "不要进入 digest",
            "npc_knowledge_boundaries": {"secret": "不要进入 digest"},
        },
        "equipment_history.json": {
            "known_items": [
                {
                    "item_id": "chalk",
                    "name": "白色粉笔",
                    "type": "tool",
                    "state": "usable",
                    "description": "可在树皮上留下记号。",
                    "canvas": "不要进入 digest",
                    "icon_rules": "不要进入 digest",
                }
            ],
            "render_rules": "不要进入 digest",
        },
    }


def _json_after_heading(prompt: str, heading: str) -> dict:
    heading_index = prompt.find(heading)
    assert heading_index >= 0
    match = re.search(r"```json\n(.*?)\n```", prompt[heading_index:], re.S)
    assert match
    return json.loads(match.group(1))


def test_actor_memory_digest_returns_top_level_keys():
    digest = build_actor_memory_digest(_memory(), _plan(), _pressure_pack())

    assert set(digest) == {
        "actor_campaign_brief",
        "visible_runtime",
        "visible_player_state",
        "visible_npc_state",
        "visible_items",
        "style_brief",
        "visible_forbidden",
        "actor_visible_story_progress",
    }


def test_actor_memory_digest_excludes_heavy_fields_and_forecast():
    digest_text = json.dumps(build_actor_memory_digest(_memory(), _plan(), _pressure_pack()), ensure_ascii=False)

    for forbidden in (
        "director_setup",
        "initial_assets",
        "initial_map_canvas",
        "render_rules",
        "visual_contract_candidates",
        "cg_prompt",
        "campaign_taxonomy",
        "character_attribute_schema",
        "story_blueprint_patch",
        "custom_libraries",
        "prompt_routing",
        "canvas_draw_instructions",
        "item_canvas_rules",
        "orchestration_forecast",
        "actor_dispatch",
        "hotload_next_turn",
        "upcoming_assets",
        "hidden_reason",
        "future_node",
        "future_asset",
        "applied_writeback_hashes",
        "hidden_motive",
        "director_notes",
    ):
        assert forbidden not in digest_text
    assert "雾门来自同伴记忆" not in digest_text


def test_actor_memory_digest_keeps_visible_story_context():
    digest = build_actor_memory_digest(_memory(), _plan(), _pressure_pack())

    assert digest["actor_campaign_brief"]["genre"] == "mystery"
    assert digest["actor_campaign_brief"]["tone"] == "quiet dread"
    assert digest["actor_campaign_brief"]["protagonist_visible_summary"]["name"] == "沈星"
    assert digest["visible_runtime"]["current_scene"]["location"] == "林间空地"
    assert digest["visible_runtime"]["short_term_state"] == {"fog_density": "high"}
    assert digest["visible_player_state"]["current_condition"] == "警觉"
    assert digest["visible_items"][0]["item_id"] == "rune_pendant"
    assert digest["style_brief"]["prose_tone"] == "冷静、低压"
    assert digest["actor_visible_story_progress"]["current_node_id"] == "node_fog"
    assert digest["visible_npc_state"]["active_npcs"][0]["name"] == "洛"


def test_actor_memory_digest_is_smaller_than_raw_actor_memory():
    memory = _memory()
    plan = _plan()
    pressure_pack = _pressure_pack()

    digest = build_actor_memory_digest(memory, plan, pressure_pack)
    raw_selected = select_memory_for_actor(deepcopy(memory), deepcopy(plan), deepcopy(pressure_pack))

    digest_chars = len(json.dumps(digest, ensure_ascii=False))
    raw_chars = len(json.dumps(raw_selected, ensure_ascii=False))
    assert digest_chars < raw_chars * 0.6


def test_select_memory_for_actor_keeps_existing_shape():
    selected = select_memory_for_actor(_memory(), _plan(), _pressure_pack())

    assert "campaign_profile.json" in selected
    assert "style_profile.json" in selected
    assert "recent_context.json" in selected
    assert "actor_campaign_brief" not in selected


def test_build_chatgpt_input_uses_actor_digest_visible_memory():
    prompt = build_chatgpt_input("demo", "继续", _memory(), _pressure_pack(), _plan())
    visible_memory = _json_after_heading(prompt, "## Visible Memory For This Turn")

    assert set(visible_memory) == {
        "actor_campaign_brief",
        "visible_runtime",
        "visible_player_state",
        "visible_npc_state",
        "visible_items",
        "style_brief",
        "visible_forbidden",
        "actor_visible_story_progress",
    }
    assert visible_memory["actor_campaign_brief"]["genre"] == "mystery"
    assert visible_memory["visible_runtime"]["short_term_state"] == {"fog_density": "high"}
    assert visible_memory["visible_player_state"]["current_condition"]
    assert visible_memory["visible_items"][0]["item_id"] == "rune_pendant"
    assert visible_memory["style_brief"]["language"] == "zh-CN"
    assert visible_memory["actor_visible_story_progress"]["current_node_id"] == "node_fog"
    assert visible_memory["visible_npc_state"]["active_npcs"][0]["npc_id"] == "luo"


def test_build_chatgpt_input_actor_digest_excludes_raw_heavy_and_forecast_fields():
    prompt = build_chatgpt_input("demo", "继续", _memory(), _pressure_pack(), _plan())
    visible_memory_text = json.dumps(_json_after_heading(prompt, "## Visible Memory For This Turn"), ensure_ascii=False)

    for forbidden in (
        "campaign_profile.json",
        "style_profile.json",
        "recent_context.json",
        "player_state.json",
        "forbidden_changes.json",
        "npc_memory.json",
        "equipment_history.json",
        "director_setup",
        "initial_assets",
        "initial_map_canvas",
        "render_rules",
        "visual_contract_candidates",
        "cg_prompt",
        "campaign_taxonomy",
        "character_attribute_schema",
        "story_blueprint_patch",
        "custom_libraries",
        "prompt_routing",
        "canvas_draw_instructions",
        "item_canvas_rules",
        "orchestration_forecast",
        "actor_dispatch",
        "hotload_next_turn",
        "upcoming_assets",
        "hidden_reason",
        "future_node",
        "future_asset",
    ):
        assert forbidden not in visible_memory_text


def test_build_chatgpt_input_keeps_story_position_and_scene_brief_sections():
    prompt = build_chatgpt_input("demo", "继续", _memory(), _pressure_pack(), _plan())

    assert "## Current Story Position" in prompt
    assert "## Scene Brief For This Turn" in prompt
    assert "Output strict JSON only: turn_title, blocks, summary, and state_writeback." in prompt
