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
    ):
        if not isinstance(data.get(key), list):
            raise SchemaValidationError(f"{key} must be a list")


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

