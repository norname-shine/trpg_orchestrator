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
BLOCK_TYPES = {"gm_narration", "player_action", "npc_dialogue", "system_check", "choice_prompt"}
ACTOR_KINDS = {"gm", "player", "npc", "system"}


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
        raise SchemaValidationError("blocks must be a list")
    if not blocks:
        raise SchemaValidationError("blocks must contain at least one visible block")

    visible_body_count = 0
    choice_prompt_count = 0
    for index, block in enumerate(blocks, start=1):
        if not isinstance(block, dict):
            raise SchemaValidationError(f"block #{index} must be an object")
        block_type = block.get("type")
        if block_type not in BLOCK_TYPES:
            raise SchemaValidationError(f"block #{index} invalid type: {block_type}")

        tags = block.get("tags") if isinstance(block.get("tags"), list) else []
        is_legacy = "legacy" in tags
        body = str(block.get("body") or "").strip()
        choices = block.get("choices") if isinstance(block.get("choices"), list) else []

        if block_type != "choice_prompt" and body:
            visible_body_count += 1

        actor_kind = str(block.get("actor_kind") or "").strip()
        if actor_kind and actor_kind not in ACTOR_KINDS:
            raise SchemaValidationError(f"block #{index} invalid actor_kind: {actor_kind}")

        if not is_legacy:
            speaker = str(block.get("speaker") or "").strip()
            if not speaker:
                raise SchemaValidationError(f"block #{index} missing speaker")
            if block_type in {"player_action", "npc_dialogue"}:
                if not str(block.get("actor_id") or "").strip():
                    raise SchemaValidationError(f"block #{index} missing actor_id")
                if not str(block.get("avatar_key") or "").strip():
                    raise SchemaValidationError(f"block #{index} missing avatar_key")
                expected_kind = "player" if block_type == "player_action" else "npc"
                if actor_kind and actor_kind != expected_kind:
                    raise SchemaValidationError(f"block #{index} actor_kind should be {expected_kind}")
            if block_type == "system_check":
                check = block.get("check")
                if check is not None and not isinstance(check, dict):
                    raise SchemaValidationError(f"block #{index} check must be an object")

        if block_type == "choice_prompt":
            choice_prompt_count += 1
            if is_legacy and not choices:
                continue
            if not choices:
                raise SchemaValidationError(f"block #{index} choice_prompt requires choices")
            if not 2 <= len(choices) <= 4:
                raise SchemaValidationError(f"block #{index} choice_prompt choices must contain 2-4 items")
            for choice_index, choice in enumerate(choices, start=1):
                if not isinstance(choice, dict):
                    raise SchemaValidationError(f"block #{index} choice #{choice_index} must be an object")
                if not str(choice.get("id") or "").strip():
                    raise SchemaValidationError(f"block #{index} choice #{choice_index} missing id")
                if not str(choice.get("label") or choice.get("text") or "").strip():
                    raise SchemaValidationError(f"block #{index} choice #{choice_index} missing label")
                if not str(choice.get("risk") or "").strip():
                    raise SchemaValidationError(f"block #{index} choice #{choice_index} missing risk")

    if visible_body_count == 0:
        raise SchemaValidationError("blocks must include at least one non-choice narrative block")
    if choice_prompt_count > 1:
        raise SchemaValidationError("only one choice_prompt block is allowed per turn")


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
