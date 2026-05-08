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
