# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import PROMPTS_DIR
from .json_utils import read_json
from .encoding_utils import read_runtime_text
from .output_contract import output_requests_to_capabilities


REGISTRY_PATH = PROMPTS_DIR / "prompt_modules.json"
_LAST_WARNINGS: list[str] = []


def load_prompt_module_registry() -> dict[str, Any]:
    return read_json(REGISTRY_PATH)


def select_prompt_modules(
    capability_plan: dict[str, Any],
    layer: str,
    pressure_pack: dict[str, Any] | None = None,
) -> list[str]:
    registry = load_prompt_module_registry()
    capabilities = set(capability_plan.get("loaded_capabilities", []) if isinstance(capability_plan, dict) else [])
    if layer == "actor" and isinstance(pressure_pack, dict):
        capabilities.update(output_requests_to_capabilities(pressure_pack.get("output_requests", {})))
    selected: list[str] = []
    excluded: list[str] = []
    for module_id, config in registry.items():
        if not isinstance(config, dict):
            continue
        layers = config.get("layers", [])
        if layer not in layers:
            continue
        always = config.get("always") is True
        triggers = set(config.get("triggers", []) if isinstance(config.get("triggers"), list) else [])
        if always or triggers.intersection(capabilities):
            selected.append(module_id)
        else:
            excluded.append(module_id)
    if isinstance(capability_plan, dict):
        prompt_modules = capability_plan.setdefault("prompt_modules", {"director": [], "actor": [], "audit": [], "excluded": []})
        if isinstance(prompt_modules, dict):
            prompt_modules[layer] = selected
            existing = prompt_modules.get("excluded", [])
            if not isinstance(existing, list):
                existing = []
            prompt_modules["excluded"] = sorted(set(existing).union(excluded))
    return selected


def load_prompt_modules(module_ids: list[str]) -> str:
    global _LAST_WARNINGS
    _LAST_WARNINGS = []
    registry = load_prompt_module_registry()
    parts: list[str] = []
    for module_id in module_ids:
        config = registry.get(module_id)
        if not isinstance(config, dict):
            _LAST_WARNINGS.append(f"prompt module missing from registry: {module_id}")
            continue
        path = PROMPTS_DIR / str(config.get("path") or "")
        if not path.exists():
            message = f"prompt module file missing: {module_id} -> {path.name}"
            if config.get("always") is True:
                raise FileNotFoundError(message)
            _LAST_WARNINGS.append(message)
            continue
        parts.append(f"## Prompt Module: {module_id}\n\n{read_runtime_text(path)}")
    return "\n\n".join(parts)


def get_prompt_module_warnings() -> list[str]:
    return list(_LAST_WARNINGS)
