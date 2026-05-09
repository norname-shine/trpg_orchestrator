# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from ..config import PROJECT_ROOT
from ..encoding_utils import read_runtime_text
from ..frontend_module_state import build_frontend_modules
from ..json_utils import read_json
from ..memory_store import MemoryStore
from ..schema_validator import normalize_pressure_pack_compat
from ..visual_contracts import CONTRACT_FILE, contract_public_payload
from .assets import asset_list, campaign_asset_seed
from .asset_rules import asset_contract_payload


def _web_server():
    from .. import web_server

    return web_server


def frontend_state_response(campaign_id: str = "") -> dict[str, Any]:
    ws = _web_server()
    store = MemoryStore()
    registry = store.load_registry()
    resolved = store.resolve_campaign_id(campaign_id or None) if (campaign_id or registry.get("active_campaign")) else ""
    if not resolved:
        job = ws.JOB.snapshot()
        return {
            "ok": True,
            "project_root": str(PROJECT_ROOT),
            "active_campaign": "",
            "campaigns": registry.get("campaigns", {}),
            "campaign_list": ws.campaign_list(registry),
            "campaign_state": {},
            "chatgpt_project": "",
            "chatgpt_conversation": "",
            "job": job,
            "streaming_preview": ws.streaming_preview_enabled(),
            "pipeline": {},
            "output": ws.empty_output_payload("", "no active campaign"),
            "frontend_state": {},
        }

    campaigns = registry.get("campaigns", {})
    current = campaigns.get(resolved, {})
    state = campaign_state(resolved)
    # Legacy migration point: output parsing/pipeline status still lives in web_server.py
    # because it is shared by several HTTP endpoints. Move it into a service next.
    output = ws.output_payload(resolved, require_parse_ready=True)
    # Media-only PNG registry. This is not a gallery business source; raw
    # gallery cards are loaded by the frontend from /api/extensions/gallery.
    assets = asset_list(resolved).get("assets", [])
    frontend = build_frontend_state(resolved, current, state, output, assets)
    output_shell = lightweight_output_shell(output)
    job = ws.JOB.snapshot()
    return {
        "ok": True,
        "project_root": str(PROJECT_ROOT),
        "active_campaign": resolved,
        "campaigns": campaigns,
        "campaign_list": ws.campaign_list(registry),
        "campaign_state": state,
        "chatgpt_project": current.get("chatgpt_project_name", ""),
        "chatgpt_conversation": current.get("chatgpt_conversation_name", ""),
        "job": job,
        "streaming_preview": ws.streaming_preview_enabled(),
        "pipeline": ws.frontend_pipeline_status(resolved, output, job),
        "output": output_shell,
        "frontend_state": frontend,
    }


def campaign_state(campaign_id: str) -> dict[str, Any]:
    if not campaign_id:
        return {}
    ws = _web_server()
    root = ws.CAMPAIGNS_DIR / campaign_id

    def maybe(name: str) -> dict[str, Any]:
        path = root / name
        return read_json(path) if path.exists() else {}

    profile = maybe("campaign_profile.json")
    return {
        "title": profile.get("title") or campaign_id,
        "template": profile.get("template", "custom"),
        "genre": profile.get("genre", ""),
        "tone": profile.get("tone", ""),
        "mechanics": profile.get("mechanics", {}),
        "rules_config": profile.get("rules_config", {}),
        "story_config": ws.normalize_story_config(profile.get("story_config", {})),
        "companion_config": profile.get("companion_config", {}),
        "model_config": ws.summarize_model_config(profile.get("model_config", {})),
        "safety_lines": ws.list_payload(profile.get("safety_lines")),
        "campaign_direction": maybe("campaign_direction.json"),
        "style_profile": maybe("style_profile.json"),
        "image_profile": maybe("image_profile.json"),
        "player": maybe("player_state.json"),
        "character_prompt": maybe("character_prompt.json"),
        "recent": maybe("recent_context.json"),
        "quests": maybe("quest_history.json"),
        "equipment": maybe("equipment_history.json"),
        "locations": maybe("location_history.json"),
        "world": maybe("world_state.json"),
        "ecology": maybe("enemy_or_monster_ecology.json"),
        "npcs": maybe("npc_memory.json"),
        "threads": maybe("main_threads.json"),
    }


def lightweight_output_shell(output: dict[str, Any]) -> dict[str, Any]:
    parsed = output.get("parsed") if isinstance(output.get("parsed"), dict) else {}
    return {
        "campaign_id": output.get("campaign_id", ""),
        "source": output.get("source", ""),
        "parsed": {
            "body": "",
            "choices": "",
            "summary": parsed.get("summary", ""),
            "blocks": [],
        },
        "pressure_pack": output.get("pressure_pack", {}) if isinstance(output.get("pressure_pack"), dict) else {},
        "audit_result": output.get("audit_result", {}) if isinstance(output.get("audit_result"), dict) else {},
        "ai_flavor_report": output.get("ai_flavor_report", {}) if isinstance(output.get("ai_flavor_report"), dict) else {},
        "image_job": output.get("image_job", {}) if isinstance(output.get("image_job"), dict) else {},
        "stage": output.get("stage", ""),
        "warning": output.get("warning", ""),
    }


def build_frontend_state(campaign_id: str, meta: dict[str, Any], state: dict[str, Any], output: dict[str, Any], assets: list[dict[str, Any]]) -> dict[str, Any]:
    ws = _web_server()
    recent = state.get("recent", {}) if isinstance(state.get("recent"), dict) else {}
    scene = recent.get("current_scene", {}) if isinstance(recent.get("current_scene"), dict) else {}
    setup = ws.frontend_campaign_setup(campaign_id, state)
    profile = {
        "id": campaign_id,
        "title": state.get("title") or meta.get("name") or campaign_id,
        "asset_seed": campaign_asset_seed(campaign_id),
        "genre": state.get("genre", ""),
        "tone": state.get("tone", ""),
        "template": setup["template"],
        "chapter": ws.campaign_chapter(campaign_id),
        "status": meta.get("status", ""),
        "binding": {
            "project_name": meta.get("chatgpt_project_name", ""),
            "conversation_name": meta.get("chatgpt_conversation_name", ""),
        },
        "scene": scene,
    }
    gallery_payload_ref = f"/api/extensions/gallery?campaign_id={ws.safe_segment(campaign_id)}"
    story_log_payload_ref = f"/api/module/story-log?campaign_id={ws.safe_segment(campaign_id)}&limit=20"
    gallery = {"raw_payload_ref": gallery_payload_ref, "assets": []}
    story_progress_payload = ws.frontend_story_progress_payload(campaign_id)
    visual_contracts_path = ws.CAMPAIGNS_DIR / ws.safe_segment(campaign_id) / CONTRACT_FILE
    visual_contracts = read_json(visual_contracts_path) if visual_contracts_path.exists() else {}
    initialization_payload = ws.campaign_initialization_frontend_payload(campaign_id, state, assets)
    map_panel = initialization_payload.get("map_panel") if isinstance(initialization_payload.get("map_panel"), dict) else {}
    if not map_panel:
        map_panel = ws.frontend_map_panel(campaign_id, scene, output, assets)
    visual_registry = ws.build_visual_registry(campaign_id, state, assets)
    pressure = normalize_pressure_pack_compat(output.get("pressure_pack", {}) if isinstance(output.get("pressure_pack"), dict) else {})
    action_path = ws.resolve_outbox_dir(campaign_id) / "last_player_action.txt"
    last_player_action = read_runtime_text(action_path).strip() if action_path.exists() else ""
    frontend_base = {
        "asset_seed": profile["asset_seed"],
        "module_refs": {
            "story_log": story_log_payload_ref,
            "map_panel": f"/api/module/map-panel?campaign_id={ws.safe_segment(campaign_id)}",
            "inventory": f"/api/module/inventory?campaign_id={ws.safe_segment(campaign_id)}",
            "dossier": f"/api/module/dossier?campaign_id={ws.safe_segment(campaign_id)}",
        },
        "story_log": {
            "campaign_id": output.get("campaign_id", campaign_id),
            "source": output.get("source", ""),
            "blocks": [],
            "summary": output.get("parsed", {}).get("summary", "") if isinstance(output.get("parsed"), dict) else "",
        },
        "initialization_payload": initialization_payload,
    }
    modules = build_frontend_modules(campaign_id, frontend_base, pressure, assets, story_progress_payload)
    return {
        "schema": "trpg_orchestrator.frontend_state.v1",
        "asset_seed": profile["asset_seed"],
        "campaign": profile,
        "template": setup["template"],
        "rules_config": setup["rules_config"],
        "companion_config": setup["companion_config"],
        "model_config_summary": setup["model_config_summary"],
        "safety_lines": setup["safety_lines"],
        "roll_actions": setup["roll_actions"],
        "last_player_action": last_player_action,
        "character_card": ws.frontend_character_card(campaign_id, state, setup["rules_config"]),
        "companion_card": ws.frontend_companion_card(campaign_id, state, setup["companion_config"]),
        "visual_contracts": contract_public_payload(visual_contracts),
        "asset_contract": asset_contract_payload(campaign_id),
        "map_panel": map_panel,
        "quests": ws.frontend_quests(state),
        "inventory": ws.frontend_inventory(state),
        "gallery": gallery,
        "visual_registry": visual_registry,
        "avatar_index": visual_registry.get("avatar_index", {}),
        "story_progress": story_progress_payload,
        "modules": modules,
        "story_log": {
            "campaign_id": output.get("campaign_id", campaign_id),
            "source": output.get("source", ""),
            "blocks": [],
            "summary": output.get("parsed", {}).get("summary", "") if isinstance(output.get("parsed"), dict) else "",
            "payload_ref": story_log_payload_ref,
            "record_tabs": ["story", "summary", "logs"],
            "mode_tabs": ["immersive", "story", "logs"],
            "admin_pages": {
                "director": "/director-debug.html",
                "writeback": "/writeback-review.html",
            },
        },
        "quick_actions": [
            {"id": "continue", "label": "继续", "action": "继续"},
            {"id": "observe", "label": "观察周围", "action": "观察周围"},
            {"id": "talk", "label": "与 NPC 对话", "action": "与 NPC 对话"},
            {"id": "inspect_item", "label": "检查物品", "action": "检查物品"},
            {"id": "recap", "label": "复盘", "action": "复盘"},
        ],
    }
