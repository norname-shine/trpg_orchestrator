from pathlib import Path


APP_JS = Path("web/app.js")


def test_frontend_tag_rendering_is_string_only():
    source = APP_JS.read_text(encoding="utf-8")
    normalize_conditions = source.split("function normalizeConditions", 1)[1].split("function normalizeAttributes", 1)[0]
    render_badges = source.split("function renderConditionBadges", 1)[1].split("function renderAttributes", 1)[0]

    assert 'typeof item === "string"' in normalize_conditions
    assert 'typeof label === "string"' in render_badges
    assert "item.label || item.name" not in normalize_conditions
    assert "normalizeCondition(" not in source


def test_prompt_tag_examples_do_not_use_object_tags():
    prompt_paths = [
        Path("prompts/Actor/character_card_json_rules.md"),
        Path("prompts/Actor/character_card_json_rules_CN.md"),
        Path("prompts/Hotload/output_contract_rules.md"),
        Path("prompts/Hotload/output_contract_rules_CN.md"),
        Path("prompts/PromptModules/asset_output_rules.md"),
        Path("prompts/PromptModules/asset_output_rules_CN.md"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in prompt_paths)

    assert '"conditions": ["失忆"]' in combined
    assert '"badges": ["主角", "医疗相关"]' in combined
    assert '{"id":"memory_loss"' not in combined
    assert '"icon":"brain"' not in combined


def test_frontend_progress_fails_idle_empty_result():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'pipeline.stage === "idle" && output.stage === "empty"' in source
    assert "failRunProgress();" in source


def test_director_prompt_forbids_continue_turn_type():
    prompt = Path("prompts/Director/v4_director_prompt.md").read_text(encoding="utf-8")

    assert "`turn_type` is a closed enum" in prompt
    assert "Never output `continue`" in prompt
    assert 'turn_type="normal_progress"' in prompt
    assert "`creation_mode`, `current_situation`, `pressure_pack`" in prompt
    assert "must be JSON objects, never strings" in prompt
    assert 'never write `"map": "keep_previous"`' in prompt
    assert "`choice_requirement.choice_level` is a closed enum" in prompt
    assert "Never output `implicit`" in prompt
    assert "`output_requests` module names are closed" in prompt
    assert "Do not output `story_log`" in prompt
    assert '`orchestration_forecast` is optional' in prompt
    assert '"for_backend_only": true' in prompt
    assert "Minimal valid object skeleton" in prompt
    assert '"creation_mode": {' in prompt
    assert '"output_requests": {' in prompt
    assert '"actor_dispatch": {' in prompt
    assert "Preserve the submitted player action. Do not rewrite it to fit the current story node." in prompt
    assert '"scene_action_warning": {' in prompt
    assert '"route": "hallucination_warning"' in prompt


def test_frontend_renders_system_warning_as_red_card():
    source = APP_JS.read_text(encoding="utf-8")
    css = Path("web/app.css").read_text(encoding="utf-8")

    assert 'card.classList.add("systemWarning")' in source
    assert 'card.classList.contains("systemWarning") ? "!"' in source
    assert 'if (["warning", "error"].includes(severity)) return null;' in source
    assert ".msg.system.systemWarning" in css
    assert "#b73333" in css
