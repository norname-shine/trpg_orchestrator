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
    "visual_assets",
    "map_route",
}

TURN_TYPES = {
    "normal_progress",
    "tense_scene",
    "battle_or_accident",
    "rest",
    "investigation",
    "social",
    "summary",
}

CHOICE_LEVELS = {"none", "minor", "major", "life_risk", "route_split", "moral_cost"}
CHOICE_STYLES = {"natural_stop", "listed_options", "no_choice"}
AUDIT_DECISIONS = {"accept", "revise", "reject"}
CHATGPT_BLOCK_TYPES = {"gm_narration", "player_action", "npc_dialogue", "system_check", "choice_prompt"}
CHATGPT_ACTOR_KINDS = {"gm", "player", "npc", "system", ""}


class SchemaValidationError(ValueError):
    pass


def validate_pressure_pack(data: dict[str, Any], expected_campaign_id: str | None = None) -> None:
    if not isinstance(data, dict):
        raise SchemaValidationError("pressure pack must be a JSON object")
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
        "visual_assets",
    ):
        if not isinstance(data.get(key), list):
            raise SchemaValidationError(f"{key} must be a list")
    if not isinstance(data.get("map_route"), dict):
        raise SchemaValidationError("map_route must be an object")


def validate_writeback(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise SchemaValidationError("state writeback must be a JSON object")
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


def validate_chatgpt_blocks(blocks: list[dict[str, Any]]) -> None:
    if not isinstance(blocks, list):
        raise SchemaValidationError("ChatGPT blocks must be a list")
    if not blocks:
        raise SchemaValidationError("ChatGPT blocks must not be empty")

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

        if block_type in {"gm_narration", "player_action", "npc_dialogue", "system_check"} and body:
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
