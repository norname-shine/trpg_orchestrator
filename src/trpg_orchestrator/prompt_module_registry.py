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

ACTOR_DISPATCH_MODULES = {
    "style_min": "actor_style_min",
    "npc_voice_min": "actor_npc_voice_min",
    "npc_voice_deep": "npc_voice_rules",
    "choice_pressure": "actor_choice_pressure",
    "recap": "actor_recap_rules",
    "progress": "actor_progress_rules",
    "inventory": "actor_inventory_rules",
    "dossier": "actor_dossier_rules",
    "map": "actor_map_rules",
    "dice": "actor_dice_rules",
}


def load_prompt_module_registry() -> dict[str, Any]:
    return read_json(REGISTRY_PATH)


def validate_prompt_module_registry(registry: dict[str, Any] | None = None) -> list[str]:
    data = registry if registry is not None else load_prompt_module_registry()
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["prompt module registry must be an object"]

    for module_id, config in data.items():
        prefix = str(module_id)
        if not isinstance(config, dict):
            errors.append(f"{prefix}: config must be an object")
            continue
        if not str(config.get("path") or "").strip():
            errors.append(f"{prefix}: missing path")

        layers = config.get("layers")
        if not isinstance(layers, list):
            errors.append(f"{prefix}: layers must be an array")
            layers = []

        responsibility = config.get("responsibility")
        if not isinstance(responsibility, str) or not responsibility.strip():
            errors.append(f"{prefix}: missing responsibility")

        allowed_outputs = config.get("allowed_outputs")
        if not isinstance(allowed_outputs, list):
            errors.append(f"{prefix}: allowed_outputs must be an array")
            allowed_outputs = []

        must_not = config.get("must_not")
        if not isinstance(must_not, list):
            errors.append(f"{prefix}: must_not must be an array")
            must_not = []

        if config.get("always") is not True and not isinstance(config.get("triggers"), list):
            errors.append(f"{prefix}: non-always module must define triggers array")

        layer_set = set(str(layer) for layer in layers)
        output_set = set(str(item) for item in allowed_outputs)
        must_not_text = " ".join(str(item) for item in must_not)
        if layer_set == {"director"}:
            if "blocks" in output_set:
                errors.append(f"{prefix}: director-only allowed_outputs must not include blocks")
            if "写玩家可见正文" not in must_not_text:
                errors.append(f"{prefix}: director-only must_not must forbid writing player-facing prose")
        if layer_set == {"actor"}:
            if "pressure_pack" in output_set:
                errors.append(f"{prefix}: actor-only allowed_outputs must not include pressure_pack")
            if not any(token in must_not_text for token in ("直接落盘记忆", "直接写入记忆")):
                errors.append(f"{prefix}: actor-only must_not must forbid direct memory persistence")
        if layer_set == {"audit"}:
            if "blocks" in output_set:
                errors.append(f"{prefix}: audit-only allowed_outputs must not include blocks")
            if "turn_title" in output_set:
                errors.append(f"{prefix}: audit-only allowed_outputs must not include turn_title")

    return errors


def select_prompt_modules(
    capability_plan: dict[str, Any],
    layer: str,
    pressure_pack: dict[str, Any] | None = None,
) -> list[str]:
    global _LAST_WARNINGS
    _LAST_WARNINGS = []
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
    if layer == "actor" and isinstance(pressure_pack, dict):
        for module_id in _actor_dispatch_module_ids(pressure_pack.get("actor_dispatch")):
            if module_id in registry and module_id not in selected:
                selected.append(module_id)
            if module_id in excluded:
                excluded.remove(module_id)
    if isinstance(capability_plan, dict):
        prompt_modules = capability_plan.setdefault("prompt_modules", {"director": [], "actor": [], "audit": [], "excluded": []})
        if isinstance(prompt_modules, dict):
            prompt_modules[layer] = selected
            existing = prompt_modules.get("excluded", [])
            if not isinstance(existing, list):
                existing = []
            prompt_modules["excluded"] = sorted(set(existing).union(excluded))
    return selected


def _actor_dispatch_module_ids(dispatch: Any) -> list[str]:
    if not isinstance(dispatch, dict):
        return []
    selected: list[str] = []
    for bucket in ("modules", "heavy_modules"):
        raw_modules = dispatch.get(bucket)
        if not isinstance(raw_modules, list):
            continue
        for raw in raw_modules:
            name = str(raw or "").strip()
            if not name:
                continue
            module_id = ACTOR_DISPATCH_MODULES.get(name)
            if not module_id:
                _LAST_WARNINGS.append(f"unknown actor_dispatch module ignored: {name}")
                continue
            if module_id not in selected:
                selected.append(module_id)
    return selected


def load_prompt_modules(module_ids: list[str]) -> str:
    global _LAST_WARNINGS
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
