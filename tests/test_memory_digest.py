import json
from copy import deepcopy

from trpg_orchestrator.memory_selector import build_director_memory_digest, select_memory_for_director


def _memory() -> dict:
    return {
        "campaign_profile.json": {
            "campaign_id": "digest_campaign",
            "title": "雾门测试",
            "name": "雾门测试",
            "genre": "mystery",
            "tone": "quiet dread",
            "premise": "主角在雾中寻找失踪路线。",
            "core_concept": "迷雾会改变记忆中的路。",
            "opening_situation": "林间空地出现新的入口。",
            "main_conflict": "确认入口真假而不被误导。",
            "early_goals": ["确认足迹", "记录入口"],
            "known_boundaries": ["不要把未确认入口写成事实"],
            "director_setup": {"huge": "不要进入 digest" * 300},
            "mechanics": {"full": "不要进入 digest"},
            "character_attribute_schema": {"huge": "不要进入 digest"},
            "campaign_taxonomy": {"huge": "不要进入 digest"},
            "render_rules": {"huge": "不要进入 digest" * 200},
            "prompt_routing": {"huge": "不要进入 digest"},
            "setup_patch": {"huge": "不要进入 digest"},
            "custom_libraries": {"huge": "不要进入 digest" * 300},
            "protagonist_patch": {
                "name": "沈星",
                "role": "调查者",
                "summary": "擅长记录异常。",
                "background": "曾在旧林区迷路。",
                "personality": "谨慎",
                "motivation": "找回同伴",
                "abilities_and_limits": "能辨认地图标记，但无法看穿幻象。",
                "visible_unknowns_or_player_owned": ["旧指南针的真实用途"],
                "unknown_or_later": "隐藏真相不要进 player_brief",
            },
            "character_card_patch": {
                "identity": {"name": "沈星", "role": "调查者"},
                "profile": {"personality": "谨慎", "motivation": "找回同伴"},
            },
            "companion_config": {
                "companion_enabled": True,
                "companion_name": "洛",
                "companion_role": "向导",
                "companion_personality": "沉默",
                "unknown_or_later": "隐藏身份不要进 companion_brief",
            },
            "companion_patch": {
                "relationship_to_protagonist": "旧识",
                "availability_note": "只在林区边缘出现。",
                "unknown_or_later": "隐藏身份不要进 companion_brief",
            },
            "initial_assets": {
                "initial_map_canvas": {
                    "map_route": {
                        "title": "密林路线",
                        "nodes": [
                            {"id": "clearing", "label": "林间空地", "canvas_draw_instructions": "不要进入 digest"},
                            {"id": "fog_gate", "label": "迷雾入口"},
                        ],
                        "edges": [{"from": "clearing", "to": "fog_gate"}],
                    },
                    "canvas_draw_instructions": "不要进入 digest" * 200,
                },
                "initial_cg": {
                    "generation_instruction": "雾气压低，远处只有一盏灯。" * 80,
                    "cg_prompt": "不要进入 digest" * 200,
                },
                "initial_items": [
                    {
                        "item_id": "rune_pendant",
                        "name": "符文吊坠",
                        "type": "token",
                        "state": "cool",
                        "description": "表面有微弱划痕。",
                        "item_canvas_rules": "不要进入 digest",
                    }
                ],
                "visual_contract_candidates": ["不要进入 digest"],
            },
            "safety_lines": ["不写露骨暴力"],
        },
        "campaign_direction.json": {
            "campaign_id": "digest_campaign",
            "main_tension": ["入口是真的，代价未知。"],
            "theme_and_tone": ["克制", "悬疑"],
            "background_direction": ["密林会回收错误记忆。"],
            "safety_interpretation": {
                "soft_lines": ["避免突然跳吓"],
                "tone_limits": ["不转成喜剧"],
            },
            "story_blueprint_patch": {"future": "不要进入 digest"},
        },
        "recent_context.json": {
            "campaign_id": "digest_campaign",
            "turn_index": 7,
            "recent_summary": ["玩家抵达林间空地。"],
            "current_scene": {"location": "林间空地", "immediate_pressure": "雾门若隐若现"},
            "last_player_action": "观察痕迹",
            "last_outcome": "发现足迹中断。",
            "short_term_state": {"fog_density": "high"},
            "applied_writeback_hashes": ["不要进入 digest"],
        },
        "forbidden_changes.json": {
            "campaign_id": "digest_campaign",
            "global_forbidden": ["不要替玩家做决定"],
            "campaign_specific_forbidden": ["不要提前确认雾门来源"],
            "secrets_not_to_reveal": ["雾门来自同伴记忆"],
            "unconfirmed_should_not_be_written_as_fact": ["迷雾入口的真实归属"],
        },
        "story_progress.json": {
            "campaign_id": "digest_campaign",
            "current_chapter_id": "chapter_1",
            "current_phase_id": "phase_a",
            "current_node_id": "node_fog_gate",
            "pace_command": "normal",
            "turns_in_node": 2,
        },
        "story_blueprint.json": {
            "campaign_id": "digest_campaign",
            "chapters": [
                {
                    "chapter_id": "chapter_1",
                    "title": "雾起",
                    "phases": [
                        {
                            "phase_id": "phase_a",
                            "nodes": [
                                {
                                    "node_id": "node_fog_gate",
                                    "title": "迷雾入口",
                                    "goal": "让玩家确认入口存在但性质未知。",
                                    "beat_checklist": ["观察痕迹", "记录地图"],
                                    "next_nodes": ["node_follow_tracks"],
                                    "requires_deep_instruction": False,
                                    "director_notes": "不要进入 digest",
                                }
                            ],
                        }
                    ],
                },
                {
                    "chapter_id": "future_chapter",
                    "title": "未来章节",
                    "nodes": [{"node_id": "future_node", "goal": "不要进入 digest"}],
                },
            ],
            "notes": ["不要传完整 story_blueprint"],
        },
        "main_threads.json": {
            "campaign_id": "digest_campaign",
            "main_threads": [{"id": "main_mist", "summary": "雾门真相"}],
            "side_threads": [],
            "unresolved_questions": ["脚印为何中断"],
            "uncertain_or_unconfirmed": ["入口是否安全"],
            "closed_threads": ["不要进入 digest"],
            "clue_summary": ["足迹停在雾边"],
        },
    }


def _plan() -> dict:
    return {"loaded_capabilities": ["base_director", "map_preload", "inventory", "dossier", "investigation"]}


def test_director_memory_digest_returns_top_level_keys():
    digest = build_director_memory_digest(_memory(), _plan())

    assert set(digest) == {
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


def test_director_memory_digest_excludes_heavy_fields():
    digest_text = json.dumps(build_director_memory_digest(_memory(), _plan()), ensure_ascii=False)

    for forbidden in (
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
        assert forbidden not in digest_text
    assert "applied_writeback_hashes" not in digest_text
    assert "future_chapter" not in digest_text


def test_director_memory_digest_keeps_decision_context():
    digest = build_director_memory_digest(_memory(), _plan())

    assert digest["campaign_brief"]["genre"] == "mystery"
    assert digest["campaign_brief"]["tone"] == "quiet dread"
    assert digest["campaign_brief"]["premise"] == "主角在雾中寻找失踪路线。"
    assert digest["current_story_anchor"]["current_node_id"] == "node_fog_gate"
    assert digest["node_brief"]["goal"] == "让玩家确认入口存在但性质未知。"
    assert digest["asset_refs"]["existing_map_summary"]
    assert digest["asset_refs"]["known_items"][0]["item_id"] == "rune_pendant"
    assert digest["forbidden_brief"]["global_forbidden"] == ["不要替玩家做决定"]


def test_director_memory_digest_is_smaller_than_raw_director_memory():
    memory = _memory()
    plan = _plan()

    digest = build_director_memory_digest(memory, plan)
    raw_selected = select_memory_for_director(deepcopy(memory), deepcopy(plan))

    digest_chars = len(json.dumps(digest, ensure_ascii=False))
    raw_chars = len(json.dumps(raw_selected, ensure_ascii=False))
    assert digest_chars < raw_chars * 0.5


def test_select_memory_for_director_keeps_existing_behavior():
    memory = _memory()
    plan = _plan()

    selected = select_memory_for_director(memory, plan)

    assert "campaign_profile.json" in selected
    assert "story_blueprint.json" in selected
    assert selected["story_blueprint.json"] == memory["story_blueprint.json"]
    assert "director_memory_digest" not in selected
