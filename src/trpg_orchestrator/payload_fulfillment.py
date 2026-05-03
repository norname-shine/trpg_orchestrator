# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from .memory_selector import select_memory_for_director
from .output_contract import filter_unauthorized_payloads, output_requests_to_capabilities, summarize_payload_keys
from .prompt_builder import read_prompt
from .schema_validator import validate_payload_patch, validate_payloads_against_output_requests, validate_pressure_pack


LAZY_LOADING_LIMITS = {
    "max_v4_core_passes": 1,
    "max_v4_payload_fulfillment_passes": 1,
    "max_chatgpt_actor_passes": 1,
    "max_v4_audit_passes": 1,
    "max_chatgpt_rewrite_passes": 0,
    "allow_recursive_capability_loading": False,
}

CORE_FIELDS = {
    "campaign_id",
    "turn_type",
    "creation_mode",
    "current_situation",
    "pressure_pack",
    "npc_direction",
    "scene_materials",
    "must_reveal_naturally",
    "must_not_explain_directly",
    "forbidden_this_turn",
    "player_pressure_point",
    "choice_requirement",
    "ending_target",
    "state_update_hints",
    "progress_control",
    "output_requests",
    "human_readable_note",
}


def diff_requested_capabilities(output_requests: dict[str, Any], loaded_capabilities: list[str], payloads: dict[str, Any] | None = None) -> dict[str, Any]:
    loaded = set(loaded_capabilities if isinstance(loaded_capabilities, list) else [])
    payloads = payloads if isinstance(payloads, dict) else {}
    missing: list[dict[str, Any]] = []
    warnings: list[str] = []
    for capability in output_requests_to_capabilities(output_requests):
        aliases = {capability}
        if capability == "dice_check_requested":
            aliases.add("dice_or_check")
        if capability not in loaded and not aliases.intersection(loaded):
            module = _module_for_capability(capability)
            missing.append({
                "capability": capability,
                "reason": f"output_requests.{module}.mode requested but {capability} capability was not loaded",
                "requested_by": "v4_core",
                "fulfillment_required": True,
            })
            continue
        if not _payload_present_for_capability(capability, payloads):
            module = _module_for_capability(capability)
            missing.append({
                "capability": capability,
                "reason": f"output_requests.{module}.mode requested but payload was not present in core pressure_pack",
                "requested_by": "v4_core",
                "fulfillment_required": True,
            })
    return {"missing_capabilities": missing, "warnings": warnings}


def build_payload_fulfillment_input(
    campaign_id: str,
    memory: dict[str, Any],
    core_pressure_pack: dict[str, Any],
    missing_capabilities: dict[str, Any],
    capability_plan: dict[str, Any],
) -> str:
    fulfillment_plan = deepcopy(capability_plan)
    loaded = fulfillment_plan.setdefault("loaded_capabilities", [])
    for item in missing_capabilities.get("missing_capabilities", []) if isinstance(missing_capabilities, dict) else []:
        capability = item.get("capability") if isinstance(item, dict) else ""
        if capability and capability not in loaded:
            loaded.append(capability)
    selected_memory = select_memory_for_director(memory, fulfillment_plan)
    return "\n\n".join([
        "# V4 Payload Fulfillment Input",
        read_prompt("v4_payload_fulfillment_prompt.md"),
        "## Lazy Loading Limits",
        "```json\n" + json.dumps(LAZY_LOADING_LIMITS, ensure_ascii=False, indent=2) + "\n```",
        "## Output Contract Rules",
        read_prompt("output_contract_rules.md"),
        "## Lazy Context Rules",
        read_prompt("lazy_context_rules.md"),
        "## campaign_id",
        campaign_id,
        "## Capability Plan",
        "```json\n" + json.dumps(fulfillment_plan, ensure_ascii=False, indent=2) + "\n```",
        "## Core Pressure Pack",
        "```json\n" + json.dumps(core_pressure_pack, ensure_ascii=False, indent=2) + "\n```",
        "## Missing Capabilities",
        "```json\n" + json.dumps(missing_capabilities, ensure_ascii=False, indent=2) + "\n```",
        "## Selected Memory For Payloads",
        "```json\n" + json.dumps(selected_memory, ensure_ascii=False, indent=2) + "\n```",
        "Output strict JSON only.",
    ])


def merge_payload_patch(core_pack: dict[str, Any], payload_patch: dict[str, Any]) -> dict[str, Any]:
    validate_payload_patch(payload_patch)
    final_pack = deepcopy(core_pack)
    warnings = list(final_pack.get("protocol_warnings", []) if isinstance(final_pack.get("protocol_warnings"), list) else [])
    for key in payload_patch:
        if key in CORE_FIELDS or key in {"pressure_pack", "state_writeback", "progress_control", "choice_requirement"}:
            warnings.append(f"payload_patch attempted to modify core field: {key}")
    patch = payload_patch.get("payload_patch", {})
    payloads = patch.get("payloads", {}) if isinstance(patch, dict) else {}
    filtered, filter_warnings = filter_unauthorized_payloads(payloads, final_pack.get("output_requests", {}))
    warnings.extend(filter_warnings)
    merged_payloads = deepcopy(final_pack.get("payloads", {}) if isinstance(final_pack.get("payloads"), dict) else {})
    merged_payloads.update(filtered)
    final_pack["payloads"] = merged_payloads
    final_pack["protocol_warnings"] = warnings
    _defer_unfulfilled_requests(final_pack)
    validate_payloads_against_output_requests(final_pack["payloads"], final_pack["output_requests"])
    validate_pressure_pack(final_pack, final_pack.get("campaign_id"))
    return final_pack


def finalize_capability_plan(preflight_plan: dict[str, Any], final_pressure_pack: dict[str, Any]) -> dict[str, Any]:
    plan = deepcopy(preflight_plan)
    loaded = plan.setdefault("loaded_capabilities", [])
    for capability in output_requests_to_capabilities(final_pressure_pack.get("output_requests", {})):
        if capability not in loaded:
            loaded.append(capability)
    plan["payload_summary"] = summarize_payload_keys(final_pressure_pack)
    plan["lazy_loading_limits"] = LAZY_LOADING_LIMITS
    return plan


def skipped_payload_patch(reason: str) -> dict[str, Any]:
    return {"skipped": True, "reason": reason, "payload_patch": {"payloads": {}}, "warnings": []}


def defer_unfulfilled_requests(pressure_pack: dict[str, Any], reason: str) -> dict[str, Any]:
    final_pack = deepcopy(pressure_pack)
    warnings = list(final_pack.get("protocol_warnings", []) if isinstance(final_pack.get("protocol_warnings"), list) else [])
    warnings.append(reason)
    final_pack["protocol_warnings"] = warnings
    _defer_unfulfilled_requests(final_pack)
    return final_pack


def _module_for_capability(capability: str) -> str:
    mapping = {
        "map": "map",
        "visual_assets": "visual_assets",
        "gallery": "gallery",
        "inventory": "inventory",
        "character_card": "character_card",
        "dossier": "dossier",
        "dice_check_requested": "dice_or_check",
        "dice_or_check": "dice_or_check",
        "canvas_jobs": "canvas_jobs",
    }
    return mapping.get(capability, capability)


def _payload_present_for_capability(capability: str, payloads: dict[str, Any]) -> bool:
    mapping = {
        "map": ("map_route", "map_canvas"),
        "visual_assets": ("visual_assets",),
        "gallery": ("gallery_updates",),
        "inventory": ("inventory_updates",),
        "character_card": ("character_card_update",),
        "dossier": ("dossier_updates",),
        "dice_or_check": ("dice_check_request",),
        "dice_check_requested": ("dice_check_request",),
        "canvas_jobs": ("canvas_jobs",),
    }
    keys = mapping.get(capability, ())
    return any(payloads.get(key) not in (None, "", [], {}) for key in keys)


def _defer_unfulfilled_requests(pressure_pack: dict[str, Any]) -> None:
    output_requests = pressure_pack.get("output_requests", {}) if isinstance(pressure_pack.get("output_requests"), dict) else {}
    payloads = pressure_pack.get("payloads", {}) if isinstance(pressure_pack.get("payloads"), dict) else {}
    warnings = pressure_pack.setdefault("protocol_warnings", [])
    if not isinstance(warnings, list):
        warnings = []
        pressure_pack["protocol_warnings"] = warnings
    requirements = {
        "map": ("map_route", "map_canvas"),
        "visual_assets": ("visual_assets",),
        "gallery": ("gallery_updates",),
        "inventory": ("inventory_updates",),
        "character_card": ("character_card_update",),
        "dossier": ("dossier_updates",),
        "dice_or_check": ("dice_check_request",),
        "canvas_jobs": ("canvas_jobs",),
    }
    for module, keys in requirements.items():
        request = output_requests.get(module)
        if not isinstance(request, dict):
            continue
        mode = str(request.get("mode") or "none")
        if mode in {"none", "keep_previous"}:
            continue
        if any(payloads.get(key) not in (None, "", [], {}) for key in keys):
            continue
        warnings.append(f"{module} request deferred because payload fulfillment did not provide a valid payload")
        request["reason"] = (request.get("reason") or "") + " | deferred: missing payload"
        if module == "map":
            request["mode"] = "keep_previous"
        else:
            request["mode"] = "none"
