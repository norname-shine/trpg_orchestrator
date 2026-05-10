# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


REQUIRED_MARKERS = [
    "【正文】",
    "【选择点】",
    "【回合摘要】",
    "【状态回写_BEGIN】",
    "【状态回写_END】",
]


@dataclass(frozen=True)
class ParsedOutput:
    body: str
    choices: str
    summary: str
    writeback: dict
    blocks: list[dict[str, Any]]


VISIBLE_PROSE_BLOCK_TYPES = {"gm_narration", "player_action", "npc_dialogue", "system_check", "choice_prompt", "cg_image"}


def visible_prose_chars(blocks: Any) -> int:
    """Count player-visible prose characters from structured ChatGPT blocks."""
    if not isinstance(blocks, list):
        return 0
    total = 0
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if str(block.get("type") or "") not in VISIBLE_PROSE_BLOCK_TYPES:
            continue
        total += len(str(block.get("body") or ""))
    return total


def missing_markers(text: str) -> list[str]:
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("```"):
        try:
            parsed = _parse_json_output(stripped)
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        else:
            if parsed.blocks and isinstance(parsed.writeback, dict):
                return []
    return [marker for marker in REQUIRED_MARKERS if marker not in text]


def parse_chatgpt_output(text: str) -> ParsedOutput:
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("```"):
        try:
            return _parse_json_output(stripped)
        except (json.JSONDecodeError, TypeError):
            pass
        except ValueError as exc:
            if "state_writeback" in str(exc):
                raise
            pass

    missing = missing_markers(text)
    if missing:
        raise ValueError(f"ChatGPT 输出缺少格式标记: {', '.join(missing)}")

    body = _section(text, "【正文】", "【选择点】").strip()
    choices = _section(text, "【选择点】", "【回合摘要】").strip()
    summary = _section(text, "【回合摘要】", "【状态回写_BEGIN】").strip()
    writeback_text = _section(text, "【状态回写_BEGIN】", "【状态回写_END】")
    try:
        writeback = json.loads(writeback_text.strip())
    except json.JSONDecodeError as exc:
        raise ValueError(f"状态回写 JSON 解析失败: {exc}") from exc
    return ParsedOutput(body=body, choices=choices, summary=summary, writeback=writeback, blocks=_legacy_blocks(body, choices))


def parse_chatgpt_output_for_display(text: str) -> ParsedOutput:
    """Parse JSON actor output for display even when writeback is missing."""
    data = _loads_json_payload(text)
    if not isinstance(data, dict):
        raise ValueError("ChatGPT JSON output must be an object")
    blocks = _normalize_blocks(data.get("blocks") or data.get("narrative_blocks") or [])
    if not blocks:
        raise ValueError("ChatGPT JSON output must include non-empty blocks")
    body = str(data.get("body") or _join_blocks(blocks, {"gm_narration", "npc_dialogue", "system_check", "cg_image"})).strip()
    choices = str(data.get("choices") or _choices_text(blocks)).strip()
    summary = str(data.get("summary") or data.get("turn_summary") or "").strip()
    writeback = data.get("state_writeback") if isinstance(data.get("state_writeback"), dict) else {}
    return ParsedOutput(body=body, choices=choices, summary=summary, writeback=writeback, blocks=blocks)


def public_output(parsed: ParsedOutput) -> str:
    return f"【正文】\n{parsed.body}\n\n【选择点】\n{parsed.choices}\n"


def _section(text: str, start: str, end: str) -> str:
    pattern = re.compile(re.escape(start) + r"(.*?)" + re.escape(end), re.S)
    match = pattern.search(text)
    if not match:
        raise ValueError(f"无法提取区段: {start} -> {end}")
    return match.group(1)


def _parse_json_output(text: str) -> ParsedOutput:
    data = _loads_json_payload(text)
    if not isinstance(data, dict):
        raise ValueError("ChatGPT JSON output must be an object")
    blocks = _normalize_blocks(data.get("blocks") or data.get("narrative_blocks") or [])
    if not blocks:
        raise ValueError("ChatGPT JSON output must include non-empty blocks")
    if not any(key in data for key in ("state_writeback", "writeback", "memory_patch")):
        raise ValueError("ChatGPT JSON output must include state_writeback")
    writeback = data.get("state_writeback") or data.get("writeback") or data.get("memory_patch") or {}
    if not isinstance(writeback, dict):
        raise ValueError("state_writeback must be an object")
    body = str(data.get("body") or _join_blocks(blocks, {"gm_narration", "npc_dialogue", "system_check", "cg_image"})).strip()
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
    legal_types = {"gm_narration", "player_action", "npc_dialogue", "system_check", "choice_prompt", "cg_image", "backend_note"}
    for index, row in enumerate(rows):
        if isinstance(row, str):
            row = {"type": "gm_narration", "speaker": "GM 叙述", "body": row}
        if not isinstance(row, dict):
            continue
        block_type = str(row.get("type") or "gm_narration").strip() or "gm_narration"
        if block_type not in legal_types:
            block_type = "gm_narration"
        body = str(row.get("body") or row.get("text") or row.get("content") or "").strip()
        choices = row.get("choices") if isinstance(row.get("choices"), list) else []
        if not body and not choices:
            continue
        actor_id = str(row.get("actor_id") or "").strip()
        speaker = _normalize_speaker(str(row.get("speaker") or _default_speaker(block_type)), block_type, actor_id)
        normalized_row = {
            "id": str(row.get("id") or f"block_{index + 1}"),
            "type": block_type,
            "speaker": speaker,
            "body": body,
            "time": str(row.get("time") or ""),
            "avatar_key": str(row.get("avatar_key") or ""),
            "actor_id": actor_id,
            "actor_kind": str(row.get("actor_kind") or ""),
            "check": row.get("check") if isinstance(row.get("check"), dict) else {},
            "choices": choices,
            "tags": row.get("tags") if isinstance(row.get("tags"), list) else [],
        }
        for extra_key in (
            "asset_key",
            "cached_url",
            "image_url",
            "url",
            "image_title",
            "image_detail",
            "aspect_ratio",
            "portrait_feedback_status",
            "portrait_feedback_assets",
            "mobile_asset_key",
            "mobile_cached_url",
            "severity",
            "warning_code",
            "route",
        ):
            if extra_key in row:
                normalized_row[extra_key] = row.get(extra_key)
        normalized.append(normalized_row)
    return normalized


def _normalize_speaker(speaker: str, block_type: str, actor_id: str = "") -> str:
    clean = speaker.strip()
    if block_type == "player_action":
        match = re.fullmatch(r"(?i)player\s*[?？:：-]\s*(.+)", clean)
        if match:
            clean = match.group(1).strip()
        if clean.lower() == "player" and actor_id:
            clean = actor_id
    return clean or _default_speaker(block_type)


def _default_speaker(block_type: str) -> str:
    return {
        "gm_narration": "GM 叙述",
        "player_action": "玩家",
        "npc_dialogue": "NPC",
        "system_check": "系统检定",
        "choice_prompt": "关键抉择",
        "summary": "回合摘要",
    }.get(block_type, "记录")


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
                    risk = str(choice.get("risk") or "").strip()
                    suffix = f"（风险：{risk}）" if risk else ""
                    if label:
                        rows.append(f"{label}{suffix}")
            return "\n".join(row for row in rows if row)
    return ""


def _legacy_blocks(body: str, choices: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, part in enumerate([part.strip() for part in re.split(r"\n{2,}", body) if part.strip()]):
        block_type = _guess_legacy_type(part)
        blocks.append({
            "id": f"legacy_body_{index + 1}",
            "type": block_type,
            "speaker": _default_speaker(block_type),
            "body": part,
            "time": "",
            "avatar_key": "",
            "actor_id": "",
            "actor_kind": "system" if block_type == "system_check" else "gm",
            "check": {},
            "choices": [],
            "tags": ["legacy"],
        })
    if choices:
        blocks.append({
            "id": "legacy_choices",
            "type": "choice_prompt",
            "speaker": "关键抉择",
            "body": choices,
            "time": "",
            "avatar_key": "",
            "actor_id": "",
            "actor_kind": "system",
            "check": {},
            "choices": _parse_legacy_choices(choices),
            "tags": ["legacy"],
        })
    return blocks


def _guess_legacy_type(text: str) -> str:
    head = text[:16]
    if any(token in text for token in ("d20", "检定", "DC", "难度", "成功", "失败")):
        return "system_check"
    if head.startswith(("玩家", "角色")):
        return "player_action"
    if head.startswith(("NPC", "接待员", "老猎人", "货车伙计")):
        return "npc_dialogue"
    return "gm_narration"


def _parse_legacy_choices(text: str) -> list[dict[str, str]]:
    choices: list[dict[str, str]] = []
    for match in re.finditer(r"(?:^|\n)\s*([A-D])(?:[.、．])\s*(.+)", text):
        choices.append({"id": match.group(1), "label": match.group(2).strip(), "risk": "unknown"})
    return choices
