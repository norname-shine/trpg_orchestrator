import json

from trpg_orchestrator import cli
from trpg_orchestrator.json_utils import read_json
from trpg_orchestrator.scene_action_guard import scene_action_warning_from_pressure_pack
from trpg_orchestrator.schema_validator import validate_pressure_pack


def _pressure_pack() -> dict:
    return {
        "campaign_id": "demo",
        "turn_type": "light_action",
        "creation_mode": {"mode": "scene_action_guard", "reason": "warning"},
        "current_situation": {},
        "pressure_pack": {},
        "npc_direction": [],
        "scene_materials": [],
        "must_reveal_naturally": [],
        "must_not_explain_directly": [],
        "forbidden_this_turn": [],
        "player_pressure_point": "warning",
        "choice_requirement": {"need_choice": False, "choice_level": "none", "choice_style": "no_choice"},
        "ending_target": "warning",
        "state_update_hints": [],
        "progress_control": {},
        "output_requests": {
            "story_progress": {"mode": "none", "trigger": "none", "reason": "warning"},
            "map": {"mode": "keep_previous", "trigger": "none", "reason": "warning"},
            "visual_assets": {"mode": "none", "trigger": "none", "reason": ""},
            "character_card": {"mode": "none", "trigger": "none", "reason": ""},
            "dossier": {"mode": "none", "trigger": "none", "reason": ""},
            "dice_or_check": {"mode": "none", "trigger": "none", "reason": ""},
            "canvas_jobs": {"mode": "none", "trigger": "none", "reason": ""},
        },
        "payloads": {},
        "actor_dispatch": {"modules": [], "heavy_modules": []},
        "human_readable_note": "warning",
    }


def test_scene_action_warning_is_director_protocol_not_backend_term_enum():
    payload = _pressure_pack()
    payload["scene_action_warning"] = {
        "code": "scene_action_unavailable",
        "severity": "warning",
        "route": "hallucination_warning",
        "message": "当前场景没有医院大厅、公告栏或可拍照设备；这个行动无法直接执行",
        "preserve_player_action": True,
    }

    validate_pressure_pack(payload, "demo")
    warning = scene_action_warning_from_pressure_pack(payload)

    assert warning == {
        "code": "scene_action_unavailable",
        "severity": "warning",
        "route": "hallucination_warning",
        "message": "当前场景没有医院大厅、公告栏或可拍照设备；这个行动无法直接执行",
    }


def test_scene_action_warning_absent_by_default():
    assert scene_action_warning_from_pressure_pack(_pressure_pack()) == {}


def test_scene_action_warning_turn_writes_display_blocks_and_skips_actor(tmp_path, monkeypatch):
    class FakeStore:
        logs = []

        def write_log(self, campaign_id, payload):
            self.logs.append((campaign_id, payload))

    outbox_dir = tmp_path / "campaigns" / "demo" / "outbox"
    outbox_dir.mkdir(parents=True)
    monkeypatch.setattr(cli, "MemoryStore", lambda: FakeStore())
    monkeypatch.setattr(cli, "OUTBOX_DIR", tmp_path / "global_outbox")
    monkeypatch.setattr(cli, "emit_public_job_status", lambda *_args, **_kwargs: None)

    pressure_pack = _pressure_pack()
    pressure_pack["scene_action_warning"] = {
        "code": "scene_action_unavailable",
        "severity": "warning",
        "route": "hallucination_warning",
        "message": "当前场景没有医院大厅、公告栏或可拍照设备；这个行动无法直接执行",
        "preserve_player_action": True,
    }

    written = cli.write_scene_action_warning_turn(
        "demo",
        "检查医院大厅的公告栏，拍下墙上的旧楼层图。",
        {},
        outbox_dir,
        pressure_pack,
        {"loaded_capabilities": []},
    )

    assert written is True
    assert (outbox_dir / "chatgpt_input.md").read_text(encoding="utf-8") == "Scene action warning; actor layer skipped.\n"
    blocks = read_json(outbox_dir / "chatgpt_blocks.json")["blocks"]
    assert [block["type"] for block in blocks] == ["player_action", "system_check"]
    assert blocks[0]["body"] == "检查医院大厅的公告栏，拍下墙上的旧楼层图。"
    assert blocks[1]["severity"] == "warning"
    assert blocks[1]["route"] == "hallucination_warning"
    assert blocks[1]["body"] == "当前场景没有医院大厅、公告栏或可拍照设备；这个行动无法直接执行"


def test_prepare_short_circuits_director_warning_only_pack(tmp_path, monkeypatch):
    class FakeStore:
        def resolve_campaign_id(self, campaign_id):
            return campaign_id or "demo"

        def load_campaign_memory(self, _campaign_id):
            return {}

        def write_log(self, _campaign_id, _payload):
            return None

    class FakeDeepSeekClient:
        def complete_json(self, _system_prompt, _user_prompt):
            return json.dumps({
                "campaign_id": "demo",
                "scene_action_warning": {
                    "code": "scene_action_unavailable",
                    "severity": "warning",
                    "route": "hallucination_warning",
                    "message": "当前场景没有医院大厅、公告栏或可拍照设备；这个行动无法直接执行",
                    "preserve_player_action": True,
                },
            }, ensure_ascii=False)

    monkeypatch.setattr(cli, "CAMPAIGNS_DIR", tmp_path / "campaigns")
    monkeypatch.setattr(cli, "OUTBOX_DIR", tmp_path / "global_outbox")
    monkeypatch.setattr(cli, "MemoryStore", lambda: FakeStore())
    monkeypatch.setattr(cli, "DeepSeekClient", FakeDeepSeekClient)
    monkeypatch.setattr(cli, "build_capability_plan", lambda *_args, **_kwargs: {"loaded_capabilities": []})
    monkeypatch.setattr(cli, "build_director_user_prompt", lambda *_args, **_kwargs: "director input")
    monkeypatch.setattr(cli, "emit_public_job_status", lambda *_args, **_kwargs: None)

    result = cli.cmd_prepare("检查医院大厅的公告栏，拍下墙上的旧楼层图。", "demo", offline_pressure_pack=False)

    outbox_dir = tmp_path / "campaigns" / "demo" / "outbox"
    assert result == 0
    pressure_pack = read_json(outbox_dir / "pressure_pack.json")
    assert pressure_pack["scene_action_warning"]["route"] == "hallucination_warning"
    assert (outbox_dir / "chatgpt_input.md").read_text(encoding="utf-8") == "Scene action warning; actor layer skipped.\n"
    blocks = read_json(outbox_dir / "chatgpt_blocks.json")["blocks"]
    assert blocks[0]["body"] == "检查医院大厅的公告栏，拍下墙上的旧楼层图。"
    assert blocks[1]["body"] == "当前场景没有医院大厅、公告栏或可拍照设备；这个行动无法直接执行"
