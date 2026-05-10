import importlib.util
import json
import subprocess
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "prompt_size_report.py"
SPEC = importlib.util.spec_from_file_location("prompt_size_report", SCRIPT_PATH)
prompt_size_report = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(prompt_size_report)
build_report = prompt_size_report.build_report


def _scenarios() -> dict[str, dict]:
    return {row["scenario"]: row for row in build_report()["scenarios"]}


def test_prompt_size_report_actor_module_expectations():
    rows = _scenarios()

    assert "style_core" not in rows["normal_actor"]["selected_modules"]
    assert "npc_voice_rules" not in rows["npc_actor"]["selected_modules"]
    assert "npc_voice_rules" in rows["deep_npc_actor"]["selected_modules"]


def test_prompt_size_report_director_preload_module_expectations():
    rows = _scenarios()

    assert "visual_contract_director_rules" not in rows["normal_director"]["selected_modules"]
    assert "director_visual_payload_min" in rows["visual_preload_director"]["selected_modules"]
    assert "visual_contract_director_rules" in rows["visual_preload_director"]["selected_modules"]
    assert "director_map_payload_min" in rows["map_preload_director"]["selected_modules"]


def test_prompt_size_report_actor_prompts_do_not_leak_forecast_fields():
    rows = _scenarios()
    actor_rows = [row for row in rows.values() if row["layer"] == "actor"]

    assert actor_rows
    assert all(row["contains_forecast_leak"] is False for row in actor_rows)


def test_prompt_size_report_rows_include_section_stats():
    rows = _scenarios()
    required_keys = {
        "selected_prompt_modules",
        "selected_memory",
        "visible_memory",
        "scene_brief",
        "current_story_position",
        "campaign_setup_controls",
        "capability_plan",
        "other",
    }

    for row in rows.values():
        assert required_keys <= set(row["section_chars"])
        assert isinstance(row["memory_ratio"], float)
        assert 0 <= row["memory_ratio"] <= 1
        assert isinstance(row["prompt_module_ratio"], float)
        assert 0 <= row["prompt_module_ratio"] <= 1


def test_prompt_size_report_memory_sections_are_counted():
    rows = _scenarios()

    assert rows["normal_director"]["section_chars"]["selected_memory"] > 0
    assert rows["normal_director"]["memory_chars"] == rows["normal_director"]["section_chars"]["selected_memory"]
    assert rows["normal_actor"]["section_chars"]["visible_memory"] > 0
    assert rows["normal_actor"]["memory_chars"] == rows["normal_actor"]["section_chars"]["visible_memory"]


def test_prompt_size_report_marks_memory_digest_candidate():
    prompt = "\n".join(
        [
            "brief",
            "## Selected Director Memory",
            "记忆" * 200,
            "## Capability Plan",
            "small",
        ]
    )

    row = prompt_size_report.report_row("memory_heavy", "director", [], [], prompt)

    assert row["memory_ratio"] >= 0.5
    assert row["memory_recommendation"] == "candidate_for_memory_digest"


def test_prompt_size_report_input_file_mode(tmp_path):
    input_file = tmp_path / "chatgpt_input.md"
    input_file.write_text(
        "\n".join(
            [
                "## Selected Actor Prompt Modules",
                "actor rules",
                "## Visible Memory For This Turn",
                "visible memory",
                "## Scene Brief For This Turn",
                "scene brief",
            ]
        ),
        encoding="utf-8",
    )

    data = prompt_size_report.build_input_report(input_file)
    row = data["scenarios"][0]

    assert row["scenario"] == "chatgpt_input.md"
    assert row["layer"] == "actor"
    assert row["section_chars"]["visible_memory"] > 0
    assert row["memory_chars"] == row["section_chars"]["visible_memory"]


def test_prompt_size_report_writes_output_file(tmp_path):
    output = tmp_path / "prompt_size_report.json"

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert output.exists()
    data = json.loads(output.read_text(encoding="utf-8"))
    stdout_data = json.loads(result.stdout)
    assert data["schema"] == "trpg_orchestrator.prompt_size_report.v1"
    assert stdout_data["schema"] == data["schema"]
    assert any(row["scenario"] == "normal_actor" for row in data["scenarios"])
