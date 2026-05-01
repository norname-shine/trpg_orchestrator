# -*- coding: gbk -*-
from __future__ import annotations

from typing import Any

from .output_parser import parse_chatgpt_output


M_BODY = "\u3010\u6b63\u6587\u3011"
M_CHOICES = "\u3010\u9009\u62e9\u70b9\u3011"
M_SUMMARY = "\u3010\u56de\u5408\u6458\u8981\u3011"

FORBIDDEN_PHRASES = ["\u8fd9\u8bf4\u660e", "\u8fd9\u4ee3\u8868", "\u8fd9\u610f\u5473\u7740"]
TEMPLATE_PHRASES = ["\u4e0d\u662f", "\u800c\u662f", "\u51c6\u5907", "\u51fa\u53d1", "\u53d1\u73b0", "\u5224\u65ad", "\u9009\u62e9"]
BUTTONY_PREFIXES = ["A.", "B.", "C.", "1.", "2.", "3.", "\u9009\u9879\u4e00", "\u9009\u9879\u4e8c", "\u9009\u9879\u4e09"]
COST_TERMS = ["\u4ee3\u4ef7", "\u98ce\u9669", "\u672a\u77e5"]
LEFT_QUOTE = "\u201c"


def check_ai_flavor(text: str, forbidden_changes: dict[str, Any] | None = None) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    body, choices, summary = _public_sections(text)
    public_text = "\n".join(part for part in (body, choices, summary) if part)

    for phrase in FORBIDDEN_PHRASES:
        count = body.count(phrase)
        if count:
            issues.append({"code": "explicit_explanation_phrase", "severity": "medium", "phrase": phrase, "count": count})

    not_but_count = min(body.count("\u4e0d\u662f"), body.count("\u800c\u662f"))
    if not_but_count >= 2:
        issues.append({"code": "repeated_not_a_but_b", "severity": "medium", "count": not_but_count})

    flow_hits = [phrase for phrase in TEMPLATE_PHRASES if body.count(phrase) >= 3]
    if len(flow_hits) >= 3:
        issues.append({"code": "process_like_narration", "severity": "high", "phrases": flow_hits})

    short_dialogue_lines = [
        line.strip()
        for line in body.splitlines()
        if (LEFT_QUOTE in line or '"' in line) and len(line.strip()) <= 18
    ]
    if len(short_dialogue_lines) >= 4:
        issues.append({"code": "hard_short_dialogue", "severity": "medium", "count": len(short_dialogue_lines)})

    if any(prefix in choices for prefix in BUTTONY_PREFIXES) and not any(term in choices for term in COST_TERMS):
        issues.append({"code": "button_like_choices", "severity": "medium"})

    forbidden = forbidden_changes or {}
    forbidden_terms = []
    for key in ("global_forbidden", "campaign_specific_forbidden", "secrets_not_to_reveal"):
        value = forbidden.get(key, [])
        if isinstance(value, list):
            forbidden_terms.extend(str(item) for item in value if item)
    leaked = [term for term in forbidden_terms if term and term in public_text]
    if leaked:
        issues.append({"code": "possible_forbidden_change_violation", "severity": "high", "terms": leaked})

    severity = "pass"
    if any(issue["severity"] == "high" for issue in issues):
        severity = "heavy"
    elif issues:
        severity = "light"

    return {
        "severity": severity,
        "issues": issues,
        "recommendation": _recommendation(severity),
        "rewrite_instruction": build_rewrite_instruction(severity, issues),
    }


def build_rewrite_instruction(severity: str, issues: list[dict[str, Any]]) -> str:
    if severity == "pass":
        return ""
    lines = [
        "Rewrite only the narrative sections that triggered the mechanical AI-flavor check.",
        "Keep established facts, choices, summary, and state writeback consistent.",
        "Do not reveal hidden information or change long-term memory.",
    ]
    for issue in issues:
        code = issue.get("code")
        if code == "explicit_explanation_phrase":
            lines.append("Remove direct explanatory phrases such as this-shows/this-means; reveal through action, objects, or reactions.")
        elif code == "repeated_not_a_but_b":
            lines.append("Reduce repeated not-A-but-B rhetorical contrast.")
        elif code == "process_like_narration":
            lines.append("Break process-like narration; avoid step-by-step task flow.")
        elif code == "hard_short_dialogue":
            lines.append("Soften short functional dialogue; make speech fit fatigue, pressure, and identity.")
        elif code == "button_like_choices":
            lines.append("Rewrite choices as natural pressure points with cost, risk, or unknown information.")
        elif code == "possible_forbidden_change_violation":
            lines.append("Remove or obscure terms that violate forbidden changes or unrevealed secrets.")
    return "\n".join(lines)


def _recommendation(severity: str) -> str:
    if severity == "pass":
        return "accept"
    if severity == "light":
        return "ask_chatgpt_local_rewrite"
    return "ask_v4_for_correction_then_rewrite"


def _between(text: str, start: str, end: str) -> str:
    if start not in text or end not in text:
        return ""
    return text.split(start, 1)[1].split(end, 1)[0]


def _after(text: str, start: str) -> str:
    if start not in text:
        return ""
    return text.split(start, 1)[1]


def _public_sections(text: str) -> tuple[str, str, str]:
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("```"):
        try:
            parsed = parse_chatgpt_output(stripped)
        except Exception:
            pass
        else:
            return parsed.body, parsed.choices, parsed.summary

    body = _between(text, M_BODY, M_CHOICES) or text
    choices = _between(text, M_CHOICES, M_SUMMARY) or ""
    summary = _after(text, M_SUMMARY).split("\u3010\u72b6\u6001\u56de\u5199_BEGIN\u3011", 1)[0]
    return body, choices, summary
