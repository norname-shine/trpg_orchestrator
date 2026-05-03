# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from typing import Any


V4_REWRITE_SCHEMA = {
    "rewrite_instruction": "",
    "must_preserve": [],
    "must_remove_or_avoid": [],
    "state_writeback_policy": "",
}


def build_v4_rewrite_user_prompt(
    raw_output: str,
    flavor_report: dict[str, Any],
    pressure_pack: dict[str, Any],
    forbidden_changes: dict[str, Any],
) -> str:
    return "\n\n".join(
        [
            "You are not writing TRPG prose. Produce JSON-only correction instructions for ChatGPT rewriting.",
            "Return exactly this JSON shape: " + json.dumps(V4_REWRITE_SCHEMA, ensure_ascii=False),
            "Mechanical AI-flavor report:",
            json.dumps(flavor_report, ensure_ascii=False, indent=2),
            "Pressure pack:",
            json.dumps(pressure_pack, ensure_ascii=False, indent=2),
            "Forbidden changes:",
            json.dumps(forbidden_changes, ensure_ascii=False, indent=2),
            "ChatGPT raw output to correct:",
            raw_output,
        ]
    )


def build_chatgpt_rewrite_input(
    raw_output: str,
    flavor_report: dict[str, Any],
    correction: dict[str, Any] | None = None,
) -> str:
    correction = correction or {}
    instruction = correction.get("rewrite_instruction") or flavor_report.get("rewrite_instruction", "")
    must_preserve = correction.get("must_preserve", [])
    must_avoid = correction.get("must_remove_or_avoid", [])
    state_policy = correction.get("state_writeback_policy") or "Keep state writeback factually consistent. Do not add unconfirmed facts."

    return "\n\n".join(
        [
            "# TRPG Rewrite Request",
            "Rewrite the previous response according to the correction instructions below.",
            "Do not reveal chain of thought. Output only the standard four sections:",
            "【正文】\n【选择点】\n【回合摘要】\n【状态回写_BEGIN】...【状态回写_END】",
            "## Correction Instructions",
            instruction or "Polish the prose while preserving all facts and state writeback.",
            "## Must Preserve",
            json.dumps(must_preserve, ensure_ascii=False, indent=2),
            "## Must Remove Or Avoid",
            json.dumps(must_avoid, ensure_ascii=False, indent=2),
            "## State Writeback Policy",
            state_policy,
            "## Mechanical Report",
            json.dumps(flavor_report, ensure_ascii=False, indent=2),
            "## Previous Output",
            raw_output,
        ]
    )
