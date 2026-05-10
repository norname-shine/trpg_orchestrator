from __future__ import annotations

from typing import Any


SCENE_ACTION_WARNING_CODES = {"scene_action_unavailable"}
SCENE_ACTION_WARNING_SEVERITIES = {"warning", "error"}
SCENE_ACTION_WARNING_ROUTES = {"hallucination_warning"}


def scene_action_warning_from_pressure_pack(pressure_pack: dict[str, Any]) -> dict[str, str]:
    if not isinstance(pressure_pack, dict):
        return {}
    warning = pressure_pack.get("scene_action_warning")
    if not isinstance(warning, dict):
        return {}
    return {
        "code": str(warning.get("code") or "").strip(),
        "severity": str(warning.get("severity") or "").strip(),
        "route": str(warning.get("route") or "").strip(),
        "message": str(warning.get("message") or "").strip(),
    }
