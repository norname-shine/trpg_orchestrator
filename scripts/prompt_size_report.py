# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import re
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trpg_orchestrator.capability_resolver import build_capability_plan
from trpg_orchestrator.config import PROMPTS_DIR
from trpg_orchestrator.encoding_utils import read_runtime_text, write_text_utf8
from trpg_orchestrator.memory_store import default_memory
from trpg_orchestrator.prompt_builder import build_chatgpt_input, build_director_user_prompt
from trpg_orchestrator.prompt_module_registry import load_prompt_module_registry, select_prompt_modules


FORECAST_LEAK_MARKERS = (
    "orchestration_forecast",
    "hotload_next_turn",
    "upcoming_assets",
    "hidden_reason",
    "future_node",
    "future_asset",
)

SECTION_KEYS = (
    "selected_prompt_modules",
    "selected_memory",
    "visible_memory",
    "scene_brief",
    "current_story_position",
    "campaign_setup_controls",
    "capability_plan",
    "other",
)

SECTION_HEADING_MAP = {
    "## Campaign Setup Controls": "campaign_setup_controls",
    "## Current Story Anchor": "current_story_position",
    "## Capability Plan": "capability_plan",
    "## Selected Director Prompt Modules": "selected_prompt_modules",
    "## Selected Director Memory": "selected_memory",
    "## Selected Actor Prompt Modules": "selected_prompt_modules",
    "## Available Story Tools": "capability_plan",
    "## Visible Memory For This Turn": "visible_memory",
    "## Current Story Position": "current_story_position",
    "## Scene Brief For This Turn": "scene_brief",
}

HEADING_PATTERN = re.compile(r"(?m)^## .*$")


def output_requests(story_progress: str = "none") -> dict[str, dict[str, str]]:
    return {
        "story_progress": {"mode": story_progress, "trigger": "system_required" if story_progress != "none" else "none", "reason": "size report"},
        "map": {"mode": "keep_previous", "trigger": "none", "reason": "size report"},
        "visual_assets": {"mode": "none", "trigger": "none", "reason": "size report"},
        "gallery": {"mode": "none", "trigger": "none", "reason": "size report"},
        "inventory": {"mode": "none", "trigger": "none", "reason": "size report"},
        "character_card": {"mode": "none", "trigger": "none", "reason": "size report"},
        "dossier": {"mode": "none", "trigger": "none", "reason": "size report"},
        "dice_or_check": {"mode": "none", "trigger": "none", "reason": "size report"},
        "canvas_jobs": {"mode": "none", "trigger": "none", "reason": "size report"},
    }


def pressure_pack(**extra: Any) -> dict[str, Any]:
    data = {
        "campaign_id": "size_report",
        "current_situation": {"location": "test room", "immediate_context": "prompt size report"},
        "pressure_pack": {"core_accident_or_change": "continue safely"},
        "output_requests": output_requests(),
        "payloads": {},
    }
    data.update(extra)
    return data


def capability_plan(capabilities: list[str], campaign_id: str = "size_report") -> dict[str, Any]:
    memory = default_memory(campaign_id)
    plan = build_capability_plan(campaign_id, "继续", memory)
    plan["loaded_capabilities"] = list(capabilities)
    plan["prompt_modules"] = {"director": [], "actor": [], "audit": [], "excluded": []}
    return plan


def forecast_memory(modules: dict[str, list[str]]) -> dict[str, Any]:
    memory = default_memory("size_report")
    memory["recent_context.json"]["turn_index"] = 1
    memory["recent_context.json"]["orchestration_forecast"] = {
        "for_backend_only": True,
        "source_turn": 1,
        "expires_at_turn": 3,
        "valid_until_node_id": "",
        "hotload_next_turn": modules,
        "upcoming_assets": [{"id": "future_asset", "hidden_reason": "size report should not leak"}],
    }
    return memory


def module_char_counts(module_ids: list[str]) -> dict[str, int]:
    registry = load_prompt_module_registry()
    counts: dict[str, int] = {}
    for module_id in module_ids:
        config = registry.get(module_id)
        if not isinstance(config, dict):
            continue
        path = PROMPTS_DIR / str(config.get("path") or "")
        if path.exists():
            counts[module_id] = len(read_runtime_text(path))
    return counts


def section_char_counts(prompt: str) -> dict[str, int]:
    sections = {key: 0 for key in SECTION_KEYS}
    matches = [match for match in HEADING_PATTERN.finditer(prompt) if match.group(0).strip() in SECTION_HEADING_MAP]
    recognized_chars = 0

    for index, match in enumerate(matches):
        heading = match.group(0).strip()
        section_key = SECTION_HEADING_MAP[heading]
        end = matches[index + 1].start() if index + 1 < len(matches) else len(prompt)
        chars = end - match.start()
        sections[section_key] += chars
        recognized_chars += chars

    sections["other"] = max(0, len(prompt) - recognized_chars)
    return sections


def ratio_for(chars: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(chars / total, 3)


def infer_layer_from_prompt(prompt: str) -> str:
    if "## Selected Director Prompt Modules" in prompt or "## Selected Director Memory" in prompt:
        return "director"
    if "## Selected Actor Prompt Modules" in prompt or "## Visible Memory For This Turn" in prompt:
        return "actor"
    return "unknown"


def report_row(scenario: str, layer: str, loaded_capabilities: list[str], selected_modules: list[str], prompt: str) -> dict[str, Any]:
    counts = module_char_counts(selected_modules)
    prompt_chars = len(prompt)
    section_chars = section_char_counts(prompt)
    memory_chars = section_chars["selected_memory"] if layer == "director" else section_chars["visible_memory"]
    prompt_module_chars = section_chars["selected_prompt_modules"]
    memory_ratio = ratio_for(memory_chars, prompt_chars)
    prompt_module_ratio = ratio_for(prompt_module_chars, prompt_chars)
    large_modules = [
        {
            "module_id": module_id,
            "chars": chars,
            "recommendation": "candidate_for_next_compression",
        }
        for module_id, chars in sorted(counts.items(), key=lambda item: item[1], reverse=True)
        if chars >= 3000
    ]
    row: dict[str, Any] = {
        "scenario": scenario,
        "layer": layer,
        "loaded_capabilities": loaded_capabilities,
        "selected_modules": selected_modules,
        "prompt_chars": prompt_chars,
        "estimated_tokens": round(prompt_chars / 2),
        "module_count": len(selected_modules),
        "section_chars": section_chars,
        "memory_chars": memory_chars,
        "memory_ratio": memory_ratio,
        "prompt_module_chars": prompt_module_chars,
        "prompt_module_ratio": prompt_module_ratio,
        "contains_deep_style": "Actor Deep Style Rules" in prompt,
        "contains_long_npc_rules": "NPC Performance Rules" in prompt,
        "contains_forecast_leak": layer == "actor" and any(marker in prompt for marker in FORECAST_LEAK_MARKERS),
    }
    if large_modules:
        row["large_modules"] = large_modules
    if memory_ratio >= 0.5:
        row["memory_recommendation"] = "candidate_for_memory_digest"
    if prompt_module_ratio >= 0.5:
        row["prompt_module_recommendation"] = "candidate_for_prompt_module_compression"
    return row


def actor_scenario(scenario: str, capabilities: list[str], pack: dict[str, Any] | None = None) -> dict[str, Any]:
    memory = default_memory("size_report")
    plan = capability_plan(capabilities)
    pack = deepcopy(pack or pressure_pack())
    selected = select_prompt_modules(plan, "actor", pack)
    prompt = build_chatgpt_input("size_report", "继续", memory, pack, plan)
    return report_row(scenario, "actor", list(plan.get("loaded_capabilities", [])), selected, prompt)


def director_scenario(scenario: str, memory: dict[str, Any]) -> dict[str, Any]:
    plan = build_capability_plan("size_report", "继续", memory)
    selected = select_prompt_modules(plan, "director")
    prompt = build_director_user_prompt("size_report", "继续", memory, plan)
    return report_row(scenario, "director", list(plan.get("loaded_capabilities", [])), selected, prompt)


def build_report() -> dict[str, Any]:
    deep_npc_pack = pressure_pack(actor_dispatch={"modules": [], "heavy_modules": ["npc_voice_deep"]})
    visual_memory = forecast_memory({"director_modules": ["director_visual_payload_min"], "actor_modules": [], "payload_modules": []})
    map_memory = forecast_memory({"director_modules": [], "actor_modules": [], "payload_modules": ["director_map_payload_min"]})
    normal_director_memory = default_memory("size_report")

    scenarios = [
        actor_scenario("normal_actor", ["base_actor"]),
        actor_scenario("npc_actor", ["base_actor", "npc_present"]),
        actor_scenario("deep_npc_actor", ["base_actor"], deep_npc_pack),
        director_scenario("normal_director", normal_director_memory),
        director_scenario("visual_preload_director", visual_memory),
        director_scenario("map_preload_director", map_memory),
        actor_scenario("inventory_turn", ["base_actor", "inventory"]),
    ]
    return {
        "schema": "trpg_orchestrator.prompt_size_report.v1",
        "rough_token_estimate": "estimated_tokens is prompt_chars / 2; no external tokenizer is used",
        "scenarios": scenarios,
    }


def build_input_report(input_path: Path) -> dict[str, Any]:
    prompt = read_runtime_text(input_path)
    layer = infer_layer_from_prompt(prompt)
    row = report_row(input_path.name, layer, [], [], prompt)
    row["input_path"] = str(input_path)
    return {
        "schema": "trpg_orchestrator.prompt_size_report.v1",
        "rough_token_estimate": "estimated_tokens is prompt_chars / 2; no external tokenizer is used",
        "scenarios": [row],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Report prompt composition size for common TRPG Orchestrator scenarios.")
    parser.add_argument("--input", help="Optional prompt input file to analyze instead of building default scenarios")
    parser.add_argument("--output", help="Optional JSON output path, for example outbox/prompt_size_report.json")
    args = parser.parse_args()

    report = build_input_report(Path(args.input)) if args.input else build_report()
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_text_utf8(path, text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
