from copy import deepcopy

from trpg_orchestrator import prompt_module_registry
from trpg_orchestrator.prompt_module_registry import load_prompt_module_registry, select_prompt_modules, validate_prompt_module_registry


def test_current_prompt_module_registry_is_valid():
    assert validate_prompt_module_registry() == []


def base_registry():
    return {
        "director_core": {
            "path": "Director/v4_director_prompt.md",
            "always": True,
            "layers": ["director"],
            "responsibility": "只决定本回合方向、压力、边界、output_requests",
            "allowed_outputs": ["pressure_pack", "output_requests"],
            "must_not": ["写玩家可见正文", "生成最终 blocks", "直接写入记忆"],
        },
        "actor_core": {
            "path": "Actor/chatgpt_host_prompt.md",
            "always": True,
            "layers": ["actor"],
            "responsibility": "只写玩家可见正文和有限 writeback",
            "allowed_outputs": ["turn_title", "blocks", "summary", "state_writeback"],
            "must_not": ["覆盖 pressure_pack", "直接落盘记忆"],
        },
        "audit_core": {
            "path": "Director/v4_audit_prompt.md",
            "always": True,
            "layers": ["audit"],
            "responsibility": "只审查是否越权、是否写回可信",
            "allowed_outputs": ["audit_result", "approved_writeback", "warnings"],
            "must_not": ["生成玩家可见正文", "直接落盘记忆"],
        },
    }


def test_missing_responsibility_returns_error():
    registry = base_registry()
    registry["actor_core"].pop("responsibility")

    errors = validate_prompt_module_registry(registry)

    assert any("actor_core" in error and "responsibility" in error for error in errors)


def test_missing_allowed_outputs_returns_error():
    registry = base_registry()
    registry["actor_core"].pop("allowed_outputs")

    errors = validate_prompt_module_registry(registry)

    assert any("actor_core" in error and "allowed_outputs" in error for error in errors)


def test_missing_must_not_returns_error():
    registry = base_registry()
    registry["actor_core"].pop("must_not")

    errors = validate_prompt_module_registry(registry)

    assert any("actor_core" in error and "must_not" in error for error in errors)


def test_director_only_blocks_returns_error():
    registry = base_registry()
    registry["director_core"]["allowed_outputs"].append("blocks")

    errors = validate_prompt_module_registry(registry)

    assert any("director_core" in error and "blocks" in error for error in errors)


def test_actor_only_pressure_pack_returns_error():
    registry = base_registry()
    registry["actor_core"]["allowed_outputs"].append("pressure_pack")

    errors = validate_prompt_module_registry(registry)

    assert any("actor_core" in error and "pressure_pack" in error for error in errors)


def test_audit_only_blocks_returns_error():
    registry = base_registry()
    registry["audit_core"]["allowed_outputs"].append("blocks")

    errors = validate_prompt_module_registry(registry)

    assert any("audit_core" in error and "blocks" in error for error in errors)


def test_select_prompt_modules_keeps_trigger_compatibility(monkeypatch):
    registry = deepcopy(load_prompt_module_registry())
    monkeypatch.setattr(prompt_module_registry, "load_prompt_module_registry", lambda: registry)
    capability_plan = {
        "loaded_capabilities": ["base_actor", "map", "inventory", "base_director"],
        "prompt_modules": {"director": [], "actor": [], "audit": [], "excluded": []},
    }
    pressure_pack = {
        "output_requests": {
            "map": {"mode": "update_route"},
            "inventory": {"mode": "update"},
            "visual_assets": {"mode": "none"},
            "story_progress": {"mode": "update"},
            "gallery": {"mode": "none"},
            "character_card": {"mode": "none"},
            "dossier": {"mode": "none"},
            "dice_or_check": {"mode": "none"},
            "canvas_jobs": {"mode": "none"},
        }
    }

    actor_modules = select_prompt_modules(capability_plan, "actor", pressure_pack)
    director_modules = select_prompt_modules(capability_plan, "director", pressure_pack)

    assert "actor_context_rules" in actor_modules
    assert "actor_map_rules" in actor_modules
    assert "actor_inventory_rules" in actor_modules
    assert "map_rules" in director_modules
    assert "inventory_rules" in director_modules
