# -*- coding: gbk -*-
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


REQUIRED_MARKERS = [
    "????",
    "?????",
    "??????",
    "?????_BEGIN?",
    "?????_END?",
]


@dataclass(frozen=True)
class ParsedOutput:
    body: str
    choices: str
    summary: str
    writeback: dict
    blocks: list[dict[str, Any]]


def missing_markers(text: str) -> list[str]:
    return [marker for marker in REQUIRED_MARKERS if marker not in text]


def parse_chatgpt_output(text: str) -> ParsedOutput:
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("```"):
        try:
            return _parse_json_output(stripped)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    missing = missing_markers(text)
    if missing:
        raise ValueError(f"ChatGPT ????????: {', '.join(missing)}")

    body = _section(text, "????", "?????").strip()
    choices = _section(text, "?????", "??????").strip()
    summary = _section(text, "??????", "?????_BEGIN?").strip()
    writeback_text = _section(text, "?????_BEGIN?", "?????_END?")
    try:
        writeback = json.loads(writeback_text.strip())
    except json.JSONDecodeError as exc:
        raise ValueError(f"???? JSON ????: {exc}") from exc
    return ParsedOutput(body=body, choices=choices, summary=summary, writeback=writeback, blocks=_legacy_blocks(body, choices))


def public_output(parsed: ParsedOutput) -> str:
    return f"????\n{parsed.body}\n\n?????\n{parsed.choices}\n"


def _section(text: str, start: str, end: str) -> str:
    pattern = re.compile(re.escape(start) + r"(.*?)" + re.escape(end), re.S)
    match = pattern.search(text)
    if not match:
        raise ValueError(f"??????: {start} -> {end}")
    return match.group(1)


def _parse_json_output(text: str) -> ParsedOutput:
    data = _loads_json_payload(text)
    if not isinstance(data, dict):
        raise ValueError("ChatGPT JSON output must be an object")
    blocks = _normalize_blocks(data.get("blocks") or data.get("narrative_blocks") or [])
    writeback = data.get("state_writeback") or data.get("writeback") or data.get("memory_patch") or {}
    if not isinstance(writeback, dict):
        raise ValueError("state_writeback must be an object")
    body = str(data.get("body") or _join_blocks(blocks, {"gm_narration", "npc_dialogue", "system_check", "player_action"})).strip()
    choices = str(data.get("choices") or _choices_text(blocks)).strip()
    summary = str(data.get("summary") or data.get("turn_summary") or "").strip()
    return ParsedOutput(body=body, choices=choices, summary=summary, writeback=writeback, blocks=blocks)


def _loads_json_payload(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return json.loads(stripped)


def _normalize_blocks(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError("blocks must be a list")
    normalized: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if isinstance(row, str):
            row = {"type": "gm_narration", "speaker": "GM ??", "body": row}
        if not isinstance(row, dict):
            continue
        block_type = str(row.get("type") or "gm_narration").strip() or "gm_narration"
        body = str(row.get("body") or row.get("text") or "").strip()
        choices = row.get("choices") if isinstance(row.get("choices"), list) else []
        if not body and not choices:
            continue
        normalized.append({
            "id": str(row.get("id") or f"block_{index + 1}"),
            "type": block_type,
            "speaker": str(row.get("speaker") or _default_speaker(block_type)),
            "body": body,
            "time": str(row.get("time") or ""),
            "avatar_key": str(row.get("avatar_key") or ""),
            "actor_id": str(row.get("actor_id") or ""),
            "actor_kind": str(row.get("actor_kind") or ""),
            "check": row.get("check") if isinstance(row.get("check"), dict) else {},
            "choices": choices,
            "tags": row.get("tags") if isinstance(row.get("tags"), list) else [],
        })
    return normalized


def _default_speaker(block_type: str) -> str:
    return {
        "gm_narration": "GM ??",
        "player_action": "??",
        "npc_dialogue": "NPC",
        "system_check": "????",
        "choice_prompt": "????",
        "summary": "????",
    }.get(block_type, "??")


def _join_blocks(blocks: list[dict[str, Any]], allowed: set[str]) -> str:
    return "\n\n".join(str(block.get("body", "")).strip() for block in blocks if block.get("type") in allowed and block.get("body"))


def _choices_text(blocks: list[dict[str, Any]]) -> str:
    for block in blocks:
        if block.get("type") == "choice_prompt":
            rows = [str(block.get("body") or "").strip()]
            for choice in block.get("choices") or []:
                if isinstance(choice, dict):
                    cid = str(choice.get("id") or "").strip()
                    label = str(choice.get("label") or choice.get("text") or "").strip()
                    if label:
                        rows.append(f"{cid}. {label}" if cid else label)
            return "\n".join(row for row in rows if row)
    return ""


def _legacy_blocks(body: str, choices: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, part in enumerate([part.strip() for part in re.split(r"\n{2,}", body) if part.strip()]):
        blocks.append({
            "id": f"legacy_body_{index + 1}",
            "type": "gm_narration",
            "speaker": "GM ??",
            "body": part,
            "time": "",
            "avatar_key": "",
            "actor_id": "",
            "actor_kind": "",
            "check": {},
            "choices": [],
            "tags": [],
        })
    if choices:
        blocks.append({
            "id": "legacy_choices",
            "type": "choice_prompt",
            "speaker": "????",
            "body": choices,
            "time": "",
            "avatar_key": "",
            "actor_id": "",
            "actor_kind": "",
            "check": {},
            "choices": [],
            "tags": [],
        })
    return blocks
