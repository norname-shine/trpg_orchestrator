# -*- coding: gbk -*-
from __future__ import annotations

import json
import re
from dataclasses import dataclass


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


def missing_markers(text: str) -> list[str]:
    return [marker for marker in REQUIRED_MARKERS if marker not in text]


def parse_chatgpt_output(text: str) -> ParsedOutput:
    missing = missing_markers(text)
    if missing:
        raise ValueError(f"ChatGPT 输出缺少格式标记: {', '.join(missing)}")

    body = _section(text, "【正文】", "【选择点】")
    choices = _section(text, "【选择点】", "【回合摘要】")
    summary = _section(text, "【回合摘要】", "【状态回写_BEGIN】")
    writeback_text = _section(text, "【状态回写_BEGIN】", "【状态回写_END】")
    try:
        writeback = json.loads(writeback_text.strip())
    except json.JSONDecodeError as exc:
        raise ValueError(f"状态回写 JSON 解析失败: {exc}") from exc
    return ParsedOutput(body=body.strip(), choices=choices.strip(), summary=summary.strip(), writeback=writeback)


def public_output(parsed: ParsedOutput) -> str:
    return f"【正文】\n{parsed.body}\n\n【选择点】\n{parsed.choices}\n"


def _section(text: str, start: str, end: str) -> str:
    pattern = re.compile(re.escape(start) + r"(.*?)" + re.escape(end), re.S)
    match = pattern.search(text)
    if not match:
        raise ValueError(f"无法提取区段: {start} -> {end}")
    return match.group(1)
