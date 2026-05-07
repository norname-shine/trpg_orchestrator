from __future__ import annotations

from typing import Any


PRESSURE_PACK_KEYS = {
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
    "human_readable_note",
    "progress_control",
    "output_requests",
}

TURN_TYPES = {
    "normal_progress",
    "tense_scene",
    "battle_or_accident",
    "rest",
    "investigation",
    "social",
    "summary",
    "light_action",
}

OUTPUT_REQUEST_MODULES = {
    "story_progress": {"none", "update"},
    "map": {"none", "keep_previous", "update_route", "update_canvas"},
    "visual_assets": {"none", "create", "update"},
    "gallery": {"none", "update"},
    "inventory": {"none", "update"},
    "character_card": {"none", "update"},
    "dossier": {"none", "update"},
    "dice_or_check": {"none", "request_check"},
    "canvas_jobs": {"none", "create"},
}

PROGRESS_NODE_STATUSES = {"active", "resolved", "skipped", "failed", "merged"}
PROGRESS_BEAT_STATUSES = {"touched", "resolved", "failed", "blocked"}
TRANSITION_TYPES = {"stay", "advance", "branch", "skip", "fail_forward", "merge"}
CANVAS_JOB_KINDS = {
    "map",
    "portrait",
    "player_portrait",
    "companion_portrait",
    "character_portrait",
    "npc_portrait",
    "monster_portrait",
    "item",
    "prop",
    "gallery_scene",
}
CANVAS_JOB_TRIGGERS = {"user_requested", "director_triggered", "system_required"}
CANVAS_CACHE_POLICIES = {"stable", "scene_only", "rebuild_on_version"}
PAYLOAD_PATCH_FORBIDDEN_KEYS = {
    "pressure_pack",
    "npc_direction",
    "choice_requirement",
    "progress_control",
    "turn_type",
    "player_facing_prose",
    "state_writeback",
    "blocks",
}
FORBIDDEN_PROGRESS_FIELDS = {
    "overall_progress",
    "chapter_progress",
    "node_progress",
    "percent",
    "percentage",
    "calculated_progress",
}

CHOICE_LEVELS = {"none", "minor", "major", "life_risk", "route_split", "moral_cost"}
CHOICE_STYLES = {"natural_stop", "listed_options", "no_choice"}
AUDIT_DECISIONS = {"accept", "revise", "reject"}
CHATGPT_BLOCK_TYPES = {"gm_narration", "player_action", "npc_dialogue", "system_check", "choice_prompt", "cg_image", "backend_note"}
CHATGPT_ACTOR_KINDS = {"gm", "player", "npc", "system", ""}


class SchemaValidationError(ValueError):
    pass


def validate_pressure_pack(data: dict[str, Any], expected_campaign_id: str | None = None, require_payloads: bool = True) -> None:
    if not isinstance(data, dict):
        raise SchemaValidationError("pressure pack must be a JSON object")
    data = normalize_pressure_pack_compat(data)
    missing = sorted(PRESSURE_PACK_KEYS - set(data))
    if missing:
        raise SchemaValidationError(f"pressure pack missing keys: {', '.join(missing)}")
    if expected_campaign_id and data.get("campaign_id") != expected_campaign_id:
        raise SchemaValidationError("pressure pack campaign_id does not match active campaign")
    if data.get("turn_type") not in TURN_TYPES:
        raise SchemaValidationError(f"invalid turn_type: {data.get('turn_type')}")

    _require_object(data, "creation_mode")
    _require_object(data, "current_situation")
    _require_object(data, "pressure_pack")
    _require_object(data, "choice_requirement")

    choice = data["choice_requirement"]
    if not isinstance(choice.get("need_choice"), bool):
        raise SchemaValidationError("choice_requirement.need_choice must be boolean")
    if choice.get("choice_level") not in CHOICE_LEVELS:
        raise SchemaValidationError(f"invalid choice_level: {choice.get('choice_level')}")
    if choice.get("choice_style") not in CHOICE_STYLES:
        raise SchemaValidationError(f"invalid choice_style: {choice.get('choice_style')}")

    for key in (
        "npc_direction",
        "scene_materials",
        "must_reveal_naturally",
        "must_not_explain_directly",
        "forbidden_this_turn",
        "state_update_hints",
    ):
        if not isinstance(data.get(key), list):
            raise SchemaValidationError(f"{key} must be a list")
    _require_object(data, "progress_control")
    validate_output_requests(data["output_requests"])
    if require_payloads:
        validate_payloads_against_output_requests(data.get("payloads", {}), data["output_requests"])
    if "visual_assets" in data and not isinstance(data.get("visual_assets"), list):
        raise SchemaValidationError("visual_assets must be a list")
    if "map_route" in data and not isinstance(data.get("map_route"), dict):
        raise SchemaValidationError("map_route must be an object")
    if "map_canvas" in data and not isinstance(data.get("map_canvas"), dict):
        raise SchemaValidationError("map_canvas must be an object")
    if "story_topology" in data and not isinstance(data.get("story_topology"), dict):
        raise SchemaValidationError("story_topology must be an object")
    if "visual_contract_candidates" in data and not isinstance(data.get("visual_contract_candidates"), list):
        raise SchemaValidationError("visual_contract_candidates must be a list")


def validate_writeback(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise SchemaValidationError("state writeback must be a JSON object")
    _reject_forbidden_progress_fields(data, "state_writeback")
    for key in ("short_term_state", "long_term_memory", "new_open_threads", "closed_threads"):
        if key not in data:
            raise SchemaValidationError(f"state writeback missing key: {key}")
    if not isinstance(data["short_term_state"], dict):
        raise SchemaValidationError("short_term_state must be an object")
    if not isinstance(data["long_term_memory"], dict):
        raise SchemaValidationError("long_term_memory must be an object")
    if not isinstance(data["new_open_threads"], list):
        raise SchemaValidationError("new_open_threads must be a list")
    if not isinstance(data["closed_threads"], list):
        raise SchemaValidationError("closed_threads must be a list")
    if "progress_writeback" in data:
        validate_progress_writeback(data["progress_writeback"])


def validate_output_requests(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise SchemaValidationError("output_requests must be an object")
    for module, allowed_modes in OUTPUT_REQUEST_MODULES.items():
        item = data.get(module)
        if not isinstance(item, dict):
            raise SchemaValidationError(f"output_requests.{module} must be an object")
        for key in ("mode", "trigger", "reason"):
            if key not in item:
                raise SchemaValidationError(f"output_requests.{module} missing {key}")
            if not isinstance(item.get(key), str):
                raise SchemaValidationError(f"output_requests.{module}.{key} must be a string")
        if item.get("mode") not in allowed_modes:
            raise SchemaValidationError(f"invalid output_requests.{module}.mode: {item.get('mode')}")


def validate_payloads_against_output_requests(payloads: dict[str, Any], output_requests: dict[str, Any]) -> None:
    if payloads in (None, {}):
        return
    if not isinstance(payloads, dict):
        raise SchemaValidationError("payloads must be an object")
    map_mode = output_requests["map"]["mode"]
    map_route = payloads.get("map_route")
    map_canvas = payloads.get("map_canvas")
    if map_mode in {"none", "keep_previous"} and (_has_payload(map_route) or _has_payload(map_canvas)):
        raise SchemaValidationError("map payload present without map update request")
    if map_mode == "update_route" and not _valid_map_route(map_route):
        raise SchemaValidationError("payloads.map_route must be non-empty for update_route")
    if map_mode == "update_canvas" and not (_valid_map_canvas(map_canvas) or _valid_map_route(map_route)):
        raise SchemaValidationError("payloads.map_canvas or payloads.map_route must be non-empty for update_canvas")

    _validate_payload_mode(output_requests, payloads, "visual_assets", "visual_assets", list)
    _validate_payload_mode(output_requests, payloads, "gallery", "gallery_updates", list)
    _validate_payload_mode(output_requests, payloads, "inventory", "inventory_updates", list)
    _validate_payload_mode(output_requests, payloads, "character_card", "character_card_update", dict)
    _validate_payload_mode(output_requests, payloads, "dossier", "dossier_updates", list)
    _validate_payload_mode(output_requests, payloads, "dice_or_check", "dice_check_request", dict)
    _validate_payload_mode(output_requests, payloads, "canvas_jobs", "canvas_jobs", list)
    if _has_payload(payloads.get("canvas_jobs")):
        validate_canvas_jobs(payloads["canvas_jobs"])
    if _has_payload(payloads.get("inventory_updates")):
        validate_inventory_updates(payloads["inventory_updates"])


def _inventory_owner_allowed(owner: str, owner_ref: str, evidence: str) -> bool:
    value = str(owner or "").strip().lower()
    if value in {"player", "companion"}:
        return True
    if value != "party":
        return False
    relation = f"{owner_ref} {evidence}".lower()
    return any(token in relation for token in ("player", "protagonist", "companion", "主角", "玩家", "伙伴", "同伴", "随身", "携带", "持有", "共用"))


def validate_inventory_updates(items: Any) -> None:
    if not isinstance(items, list):
        raise SchemaValidationError("inventory_updates must be a list")
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise SchemaValidationError(f"inventory_updates[{index}] must be an object")
        prefix = f"inventory_updates[{index}]"
        for key in ("id", "name", "item_type", "status", "owner", "short_description", "simple_prompt", "certainty", "source_evidence"):
            _require_nonempty_string(item, key, prefix)
        if item.get("status") not in {"confirmed", "limited", "damaged", "uncertain"}:
            raise SchemaValidationError(f"{prefix}.status invalid: {item.get('status')}")
        if item.get("certainty") not in {"confirmed", "clue", "uncertain"}:
            raise SchemaValidationError(f"{prefix}.certainty invalid: {item.get('certainty')}")
        if not _inventory_owner_allowed(str(item.get("owner") or ""), str(item.get("owner_ref") or ""), str(item.get("source_evidence") or "")):
            raise SchemaValidationError(f"{prefix}.owner must be player/companion, or party clearly tied to player/companion")
        if "canvas_style" not in item or not isinstance(item.get("canvas_style"), dict):
            raise SchemaValidationError(f"{prefix}.canvas_style must be an object")
        if len(str(item.get("simple_prompt") or "")) > 260:
            raise SchemaValidationError(f"{prefix}.simple_prompt too long")


def validate_payload_patch(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise SchemaValidationError("payload patch must be an object")
    for key in data:
        if key in PAYLOAD_PATCH_FORBIDDEN_KEYS:
            raise SchemaValidationError(f"payload patch forbidden key: {key}")
    _require_nonempty_string(data, "campaign_id", "payload_patch")
    patch = data.get("payload_patch")
    if not isinstance(patch, dict):
        raise SchemaValidationError("payload_patch must be an object")
    payloads = patch.get("payloads", {})
    if not isinstance(payloads, dict):
        raise SchemaValidationError("payload_patch.payloads must be an object")
    for key in patch:
        if key != "payloads":
            raise SchemaValidationError(f"payload_patch may only contain payloads, got: {key}")
    if "warnings" in data and not isinstance(data.get("warnings"), list):
        raise SchemaValidationError("payload_patch warnings must be a list")
    if "canvas_jobs" in payloads and _has_payload(payloads.get("canvas_jobs")):
        validate_canvas_jobs(payloads["canvas_jobs"])


def validate_canvas_jobs(jobs: Any) -> None:
    if not isinstance(jobs, list):
        raise SchemaValidationError("canvas_jobs must be a list")
    for index, job in enumerate(jobs, start=1):
        if not isinstance(job, dict):
            raise SchemaValidationError(f"canvas_jobs[{index}] must be an object")
        prefix = f"canvas_jobs[{index}]"
        for key in ("job_id", "kind", "renderer", "trigger", "input_ref", "asset_key", "cache_policy"):
            _require_nonempty_string(job, key, prefix)
        if job.get("kind") not in CANVAS_JOB_KINDS:
            raise SchemaValidationError(f"{prefix} invalid kind: {job.get('kind')}")
        if job.get("trigger") not in CANVAS_JOB_TRIGGERS:
            raise SchemaValidationError(f"{prefix} invalid trigger: {job.get('trigger')}")
        if job.get("cache_policy") not in CANVAS_CACHE_POLICIES:
            raise SchemaValidationError(f"{prefix} invalid cache_policy: {job.get('cache_policy')}")
        text = " ".join(str(job.get(key) or "").lower() for key in ("job_id", "input_ref", "asset_key"))
        if "placeholder" in text or "todo" in text or "tbd" in text:
            raise SchemaValidationError(f"{prefix} placeholder job forbidden")


def validate_progress_writeback(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise SchemaValidationError("progress_writeback must be an object")
    _reject_forbidden_progress_fields(data, "progress_writeback")
    allowed = {
        "current_chapter_id",
        "current_node_id",
        "node_status",
        "beat_updates",
        "transition_request",
        "progress_evidence",
        "next_pace_instruction",
    }
    for key in data:
        if key in FORBIDDEN_PROGRESS_FIELDS:
            raise SchemaValidationError(f"progress_writeback forbidden field: {key}")
        if key not in allowed:
            raise SchemaValidationError(f"progress_writeback unknown field: {key}")
    if str(data.get("node_status") or "active") not in PROGRESS_NODE_STATUSES:
        raise SchemaValidationError(f"invalid progress_writeback.node_status: {data.get('node_status')}")
    if not isinstance(data.get("beat_updates", []), list):
        raise SchemaValidationError("progress_writeback.beat_updates must be a list")
    for index, item in enumerate(data.get("beat_updates", []), start=1):
        if not isinstance(item, dict):
            raise SchemaValidationError(f"progress_writeback.beat_updates[{index}] must be an object")
        _require_nonempty_string(item, "beat_id", f"progress_writeback.beat_updates[{index}]")
        if item.get("status") not in PROGRESS_BEAT_STATUSES:
            raise SchemaValidationError(f"invalid progress beat status: {item.get('status')}")
        _require_nonempty_string(item, "evidence", f"progress_writeback.beat_updates[{index}]")
    transition = data.get("transition_request", {})
    if not isinstance(transition, dict):
        raise SchemaValidationError("progress_writeback.transition_request must be an object")
    transition_allowed = {"type", "from_node_id", "to_node_id", "reason"}
    for key in transition:
        if key not in transition_allowed:
            raise SchemaValidationError(f"transition_request unknown field: {key}")
    transition_type = str(transition.get("type") or "stay")
    if transition_type not in TRANSITION_TYPES:
        raise SchemaValidationError(f"invalid transition_request.type: {transition_type}")
    if transition_type != "stay" and not str(transition.get("to_node_id") or "").strip():
        raise SchemaValidationError("transition_request.to_node_id required unless type is stay")
    if "from_node_id" in transition and not isinstance(transition.get("from_node_id"), str):
        raise SchemaValidationError("transition_request.from_node_id must be a string")
    if "progress_evidence" in data and not isinstance(data.get("progress_evidence"), list):
        raise SchemaValidationError("progress_writeback.progress_evidence must be a list")
    node_status = str(data.get("node_status") or "active")
    if node_status in {"resolved", "failed", "skipped", "merged"}:
        has_progress_evidence = any(str(item or "").strip() for item in data.get("progress_evidence", []) if not isinstance(item, dict)) or any(
            str(item.get("evidence") or item.get("text") or item.get("reason") or "").strip()
            for item in data.get("progress_evidence", [])
            if isinstance(item, dict)
        )
        has_transition_reason = bool(str(transition.get("reason") or "").strip())
        has_beat_evidence = any(
            isinstance(item, dict) and str(item.get("evidence") or "").strip()
            for item in data.get("beat_updates", [])
        )
        if not (has_progress_evidence or has_transition_reason or has_beat_evidence):
            raise SchemaValidationError(f"progress_writeback.node_status {node_status} requires evidence")


def normalize_pressure_pack_compat(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        return data
    normalized = data
    normalized.setdefault("human_readable_note", "Pressure pack normalized from an older or incomplete director output.")
    if "progress_control" not in normalized:
        normalized["progress_control"] = {
            "current_chapter_id": "",
            "current_phase_id": "",
            "current_node_id": "",
            "current_node_name": "",
            "node_goal": "",
            "beat_targets_this_turn": [],
            "pace_command": "normal",
            "legal_next_nodes": [],
            "must_not_repeat": [],
            "progress_note": "",
        }
    if "output_requests" not in normalized:
        normalized["output_requests"] = default_output_requests("compatibility default")
    else:
        output_requests = normalized["output_requests"]
        if isinstance(output_requests, dict):
            defaults = default_output_requests("compatibility default")
            for key, value in defaults.items():
                output_requests.setdefault(key, value)
    normalized.setdefault("payloads", {})
    payloads = normalized["payloads"] if isinstance(normalized.get("payloads"), dict) else {}
    output_requests = normalized.get("output_requests", {})
    if isinstance(payloads, dict) and isinstance(output_requests, dict):
        if output_requests.get("map", {}).get("mode") in {"update_route", "update_canvas"} and _has_payload(normalized.get("map_route")):
            payloads.setdefault("map_route", normalized.get("map_route"))
        if output_requests.get("visual_assets", {}).get("mode") in {"create", "update"} and _has_payload(normalized.get("visual_assets")):
            payloads.setdefault("visual_assets", normalized.get("visual_assets"))
    normalized["payloads"] = payloads
    return normalized


def default_output_requests(reason: str) -> dict[str, dict[str, str]]:
    return {
        "story_progress": {"mode": "update", "trigger": "system_required", "reason": reason},
        "map": {"mode": "keep_previous", "trigger": "none", "reason": reason},
        "visual_assets": {"mode": "none", "trigger": "none", "reason": reason},
        "gallery": {"mode": "none", "trigger": "none", "reason": reason},
        "inventory": {"mode": "none", "trigger": "none", "reason": reason},
        "character_card": {"mode": "none", "trigger": "none", "reason": reason},
        "dossier": {"mode": "none", "trigger": "none", "reason": reason},
        "dice_or_check": {"mode": "none", "trigger": "none", "reason": reason},
        "canvas_jobs": {"mode": "none", "trigger": "none", "reason": reason},
    }


def validate_chatgpt_blocks(blocks: list[dict[str, Any]]) -> None:
    if not isinstance(blocks, list):
        raise SchemaValidationError("ChatGPT blocks must be a list")
    if not blocks:
        raise SchemaValidationError("ChatGPT blocks must not be empty")
    first_type = str((blocks[0] or {}).get("type") or "").strip() if isinstance(blocks[0], dict) else ""
    first_actor = str((blocks[0] or {}).get("actor_kind") or "").strip() if isinstance(blocks[0], dict) else ""
    if first_type != "player_action" or first_actor != "player":
        raise SchemaValidationError("blocks[0] must be the submitted player_action with actor_kind=player")

    narrative_count = 0
    choice_prompt_count = 0
    for index, block in enumerate(blocks, start=1):
        if not isinstance(block, dict):
            raise SchemaValidationError(f"block {index} must be an object")
        block_type = str(block.get("type") or "").strip()
        if block_type not in CHATGPT_BLOCK_TYPES:
            raise SchemaValidationError(f"block {index} invalid type: {block_type}")
        actor_kind = str(block.get("actor_kind") or "").strip()
        if actor_kind not in CHATGPT_ACTOR_KINDS:
            raise SchemaValidationError(f"block {index} invalid actor_kind: {actor_kind}")
        body = str(block.get("body") or "").strip()
        choices = block.get("choices") if isinstance(block.get("choices"), list) else []
        if not body and not choices:
            raise SchemaValidationError(f"block {index} must contain body or choices")

        if block_type in {"gm_narration", "player_action", "npc_dialogue", "system_check", "cg_image"} and body:
            narrative_count += 1
        if block_type in {"player_action", "npc_dialogue"}:
            _require_nonempty_string(block, "actor_id", f"block {index}")
            _require_nonempty_string(block, "avatar_key", f"block {index}")
        if block_type == "system_check" and block.get("check") not in (None, {}) and not isinstance(block.get("check"), dict):
            raise SchemaValidationError(f"block {index} check must be an object")
        if block_type == "choice_prompt":
            choice_prompt_count += 1
            validate_choice_prompt(block, index)

    if narrative_count == 0:
        raise SchemaValidationError("ChatGPT output must include at least one narrative block")
    if choice_prompt_count > 1:
        raise SchemaValidationError("ChatGPT output must not include more than one choice_prompt block")


def validate_choice_prompt(block: dict[str, Any], index: int) -> None:
    choices = block.get("choices")
    if choices in (None, []):
        return
    if not isinstance(choices, list):
        raise SchemaValidationError(f"block {index} choices must be a list")
    if not 2 <= len(choices) <= 4:
        raise SchemaValidationError(f"block {index} choices must contain 2-4 choices")
    seen_ids: set[str] = set()
    for choice_index, choice in enumerate(choices, start=1):
        if not isinstance(choice, dict):
            raise SchemaValidationError(f"block {index} choice {choice_index} must be an object")
        _require_nonempty_string(choice, "id", f"block {index} choice {choice_index}")
        _require_nonempty_string(choice, "label", f"block {index} choice {choice_index}")
        _require_nonempty_string(choice, "risk", f"block {index} choice {choice_index}")
        choice_id = str(choice.get("id") or "").strip()
        if choice_id in seen_ids:
            raise SchemaValidationError(f"block {index} duplicate choice id: {choice_id}")
        seen_ids.add(choice_id)


def validate_audit_result(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise SchemaValidationError("audit result must be a JSON object")
    for key in ("decision", "reason", "approved_writeback", "memory_files_to_update", "warnings"):
        if key not in data:
            raise SchemaValidationError(f"audit result missing key: {key}")
    if data["decision"] not in AUDIT_DECISIONS:
        raise SchemaValidationError(f"invalid audit decision: {data['decision']}")
    if not isinstance(data["approved_writeback"], dict):
        raise SchemaValidationError("approved_writeback must be an object")
    if not isinstance(data["memory_files_to_update"], list):
        raise SchemaValidationError("memory_files_to_update must be a list")
    if not isinstance(data["warnings"], list):
        raise SchemaValidationError("warnings must be a list")


def _require_object(data: dict[str, Any], key: str) -> None:
    if not isinstance(data.get(key), dict):
        raise SchemaValidationError(f"{key} must be an object")


def _require_nonempty_string(data: dict[str, Any], key: str, prefix: str) -> None:
    if not isinstance(data.get(key), str) or not data.get(key, "").strip():
        raise SchemaValidationError(f"{prefix} missing non-empty {key}")


def _reject_forbidden_progress_fields(data: Any, path: str) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in FORBIDDEN_PROGRESS_FIELDS:
                raise SchemaValidationError(f"{path} forbidden progress field: {key}")
            _reject_forbidden_progress_fields(value, f"{path}.{key}")
    elif isinstance(data, list):
        for index, item in enumerate(data):
            _reject_forbidden_progress_fields(item, f"{path}[{index}]")


def _has_payload(value: Any) -> bool:
    if value in (None, "", [], {}):
        return False
    if isinstance(value, dict):
        return any(_has_payload(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_payload(item) for item in value)
    return True


def _valid_map_route(value: Any) -> bool:
    return isinstance(value, dict) and (
        bool(value.get("nodes")) or bool(value.get("edges")) or bool(value.get("markers"))
    )


def _valid_map_canvas(value: Any) -> bool:
    return isinstance(value, dict) and (
        bool(value.get("ascii")) or bool(value.get("points")) or bool(value.get("routes")) or bool(value.get("hazards"))
    )


def _validate_payload_mode(
    output_requests: dict[str, Any],
    payloads: dict[str, Any],
    module: str,
    payload_key: str,
    expected_type: type,
) -> None:
    mode = output_requests[module]["mode"]
    payload = payloads.get(payload_key)
    has_payload = _has_payload(payload)
    if mode == "none":
        if has_payload:
            raise SchemaValidationError(f"payloads.{payload_key} present without {module} update request")
        return
    if not has_payload:
        raise SchemaValidationError(f"payloads.{payload_key} required for {module} update request")
    if not isinstance(payload, expected_type):
        raise SchemaValidationError(f"payloads.{payload_key} has invalid type")
