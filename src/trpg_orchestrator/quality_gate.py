# -*- coding: gbk -*-
from __future__ import annotations

from pathlib import Path
from typing import Any

from .ai_flavor_checker import check_ai_flavor
from .json_utils import write_json
from .output_parser import parse_chatgpt_output
from .schema_validator import validate_writeback


def quality_gate(raw_output: str, forbidden_changes: dict[str, Any], outbox_dir: Path, prefix: str = "") -> dict[str, Any]:
    parsed = parse_chatgpt_output(raw_output)
    validate_writeback(parsed.writeback)
    report = check_ai_flavor(raw_output, forbidden_changes)
    report_name = f"{prefix}ai_flavor_report.json" if prefix else "ai_flavor_report.json"
    write_json(outbox_dir / report_name, report)
    return {"parsed": parsed, "flavor_report": report}


def is_quality_pass(report: dict[str, Any]) -> bool:
    return report.get("severity") == "pass"
