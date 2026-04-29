# -*- coding: gbk -*-
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .ai_flavor_checker import check_ai_flavor
from .chatgpt_web_client import ChatGPTWebClient
from .config import OUTBOX_DIR, REGISTRY_PATH
from .deepseek_client import DeepSeekClient
from .json_utils import extract_json_object, read_json, write_json
from .memory_store import MemoryStore
from .memory_compactor import build_compaction_report
from .output_parser import parse_chatgpt_output, public_output
from .prompt_builder import build_audit_user_prompt, build_chatgpt_input, build_director_user_prompt, read_prompt
from .rewrite_manager import build_chatgpt_rewrite_input, build_v4_rewrite_user_prompt
from .schema_validator import validate_audit_result, validate_pressure_pack, validate_writeback
from .quality_gate import quality_gate, is_quality_pass
from .writeback import apply_approved_writeback, migrate_legacy_facts, writeback_hash, has_applied_writeback


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trpg")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("validate-memory")
    sub.add_parser("migrate-memory")
    sub.add_parser("rewrite-plan")
    sub.add_parser("memory-report")
    mc = sub.add_parser("memory-compact")
    mc.add_argument("--threshold", type=int, default=12)
    sub.add_parser("rewrite-send")
    sub.add_parser("promote-rewrite")
    rr = sub.add_parser("run-rewrite")
    rr.add_argument("--max-attempts", type=int, default=2)

    init = sub.add_parser("init-campaign")
    init.add_argument("--campaign-id", required=True)
    init.add_argument("--name", required=True)

    bind = sub.add_parser("set-chatgpt-binding")
    bind.add_argument("--campaign-id")
    bind.add_argument("--project-name", required=True)
    bind.add_argument("--conversation-name", required=True)

    prepare = sub.add_parser("prepare")
    prepare.add_argument("--action", required=True)
    prepare.add_argument("--campaign-id")
    prepare.add_argument("--offline-pressure-pack", action="store_true")

    send = sub.add_parser("send")
    send.add_argument("--campaign-id")

    capture = sub.add_parser("capture")
    capture.add_argument("--campaign-id")

    ingest = sub.add_parser("ingest")
    ingest.add_argument("--campaign-id")
    ingest.add_argument("--skip-v4-audit", action="store_true")

    audit = sub.add_parser("audit-writeback")
    audit.add_argument("--campaign-id")

    run_turn = sub.add_parser("run-turn")
    run_turn.add_argument("--action", required=True)
    run_turn.add_argument("--campaign-id")
    run_turn.add_argument("--offline-pressure-pack", action="store_true")
    run_turn.add_argument("--skip-v4-audit", action="store_true")
    run_turn.add_argument("--auto-rewrite", action="store_true")
    run_turn.add_argument("--rewrite-attempts", type=int, default=2)

    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            return cmd_status()
        if args.command == "validate-memory":
            return cmd_validate_memory()
        if args.command == "migrate-memory":
            return cmd_migrate_memory()
        if args.command == "rewrite-plan":
            return cmd_rewrite_plan()
        if args.command == "memory-report":
            return cmd_memory_report()
        if args.command == "memory-compact":
            return cmd_memory_compact(args.threshold)
        if args.command == "rewrite-send":
            return cmd_rewrite_send()
        if args.command == "promote-rewrite":
            return cmd_promote_rewrite()
        if args.command == "run-rewrite":
            return cmd_run_rewrite(args.max_attempts)
        if args.command == "init-campaign":
            return cmd_init_campaign(args.campaign_id, args.name)
        if args.command == "set-chatgpt-binding":
            return cmd_set_chatgpt_binding(args.campaign_id, args.project_name, args.conversation_name)
        if args.command == "prepare":
            return cmd_prepare(args.action, args.campaign_id, args.offline_pressure_pack)
        if args.command == "send":
            return cmd_send(args.campaign_id)
        if args.command == "capture":
            return cmd_capture(args.campaign_id)
        if args.command == "ingest":
            return cmd_ingest(args.campaign_id, args.skip_v4_audit)
        if args.command == "audit-writeback":
            return cmd_audit_writeback(args.campaign_id)
        if args.command == "run-turn":
            return cmd_run_turn(args.action, args.campaign_id, args.offline_pressure_pack, args.skip_v4_audit, args.auto_rewrite, args.rewrite_attempts)
    except Exception as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_status() -> int:
    registry = MemoryStore().load_registry()
    print(f"project: {REGISTRY_PATH.parents[1]}")
    print(f"active_campaign: {registry.get('active_campaign') or '(unset)'}")
    campaigns = registry.get("campaigns", {})
    print(f"campaign_count: {len(campaigns)}")
    for campaign_id, meta in campaigns.items():
        print(f"- {campaign_id}: {meta.get('name', '')} [{meta.get('status', '')}]")
    return 0


def cmd_init_campaign(campaign_id: str, name: str) -> int:
    paths = MemoryStore().init_campaign(campaign_id, name)
    print(f"initialized campaign: {campaign_id}")
    print(paths.root)
    return 0


def cmd_set_chatgpt_binding(campaign_id: str | None, project_name: str, conversation_name: str) -> int:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id)
    store.update_chatgpt_binding(resolved, project_name, conversation_name)
    print(f"updated ChatGPT binding: {resolved}")
    return 0


def cmd_prepare(action: str, campaign_id: str | None, offline_pressure_pack: bool = False) -> int:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id)
    memory = store.load_campaign_memory(resolved)
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    (OUTBOX_DIR / "last_player_action.txt").write_text(action, encoding="utf-8")
    if offline_pressure_pack:
        pressure_pack = _offline_pressure_pack(resolved, action, memory)
    else:
        client = DeepSeekClient()
        pressure_pack = extract_json_object(client.complete_json(
            read_prompt("v4_director_prompt.md"),
            build_director_user_prompt(resolved, action, memory),
        ))
    validate_pressure_pack(pressure_pack, resolved)
    write_json(OUTBOX_DIR / "pressure_pack.json", pressure_pack)
    (OUTBOX_DIR / "chatgpt_input.md").write_text(
        build_chatgpt_input(resolved, action, memory, pressure_pack),
        encoding="utf-8",
        newline="\n",
    )
    print("wrote pressure_pack.json and chatgpt_input.md")
    return 0


def web_client(campaign_id: str | None = None) -> ChatGPTWebClient:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id)
    memory = store.load_campaign_memory(resolved)
    return ChatGPTWebClient(memory["campaign_profile.json"])


def cmd_send(campaign_id: str | None) -> int:
    web_client(campaign_id).send_and_capture(OUTBOX_DIR / "chatgpt_input.md", OUTBOX_DIR / "chatgpt_raw_output.md")
    print("sent chatgpt_input.md and captured chatgpt_raw_output.md")
    return 0


def cmd_capture(campaign_id: str | None) -> int:
    web_client(campaign_id).capture_latest(OUTBOX_DIR / "chatgpt_raw_output.md")
    print("captured latest assistant reply")
    return 0


def cmd_rewrite_send() -> int:
    web_client(None).send_file_and_capture(OUTBOX_DIR / "chatgpt_rewrite_input.md", OUTBOX_DIR / "chatgpt_raw_output_rewrite.md")
    print("sent rewrite input and captured chatgpt_raw_output_rewrite.md")
    return 0



def cmd_run_rewrite(max_attempts: int = 2) -> int:
    max_attempts = max(1, min(max_attempts, 2))
    store = MemoryStore()
    resolved = store.resolve_campaign_id(None)
    memory = store.load_campaign_memory(resolved)
    raw_path = OUTBOX_DIR / "chatgpt_raw_output.md"
    original_raw = raw_path.read_text(encoding="utf-8") if raw_path.exists() else ""
    working_raw = original_raw
    for attempt in range(1, max_attempts + 1):
        print(f"rewrite attempt {attempt}/{max_attempts}")
        if working_raw:
            raw_path.write_text(working_raw, encoding="utf-8", newline="\n")
        cmd_rewrite_plan()
        web_client(None).send_file_and_capture(OUTBOX_DIR / "chatgpt_rewrite_input.md", OUTBOX_DIR / "chatgpt_raw_output_rewrite.md")
        rewritten = (OUTBOX_DIR / "chatgpt_raw_output_rewrite.md").read_text(encoding="utf-8")
        gate = quality_gate(rewritten, memory.get("forbidden_changes.json", {}), OUTBOX_DIR, prefix=f"rewrite_{attempt}_")
        severity = gate["flavor_report"].get("severity")
        print(f"rewrite attempt severity: {severity}")
        if is_quality_pass(gate["flavor_report"]):
            shutil.copy2(OUTBOX_DIR / "chatgpt_raw_output_rewrite.md", raw_path)
            print("rewrite accepted and promoted")
            return 0
        working_raw = rewritten
    if original_raw:
        raw_path.write_text(original_raw, encoding="utf-8", newline="\n")
    raise RuntimeError("rewrite attempts exhausted; latest rewrite saved as chatgpt_raw_output_rewrite.md but not promoted")

def cmd_promote_rewrite() -> int:
    source = OUTBOX_DIR / "chatgpt_raw_output_rewrite.md"
    if not source.exists():
        raise FileNotFoundError("missing outbox/chatgpt_raw_output_rewrite.md")
    parsed = parse_chatgpt_output(source.read_text(encoding="utf-8"))
    validate_writeback(parsed.writeback)
    shutil.copy2(source, OUTBOX_DIR / "chatgpt_raw_output.md")
    print("promoted rewrite output to chatgpt_raw_output.md")
    return 0


def cmd_ingest(campaign_id: str | None, skip_v4_audit: bool = False) -> int:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id)
    memory = store.load_campaign_memory(resolved)
    raw_path = OUTBOX_DIR / "chatgpt_raw_output.md"
    if not raw_path.exists():
        raise FileNotFoundError("missing outbox/chatgpt_raw_output.md")
    raw_output = raw_path.read_text(encoding="utf-8")
    gate = quality_gate(raw_output, memory.get("forbidden_changes.json", {}), OUTBOX_DIR)
    parsed = gate["parsed"]
    flavor_report = gate["flavor_report"]
    (OUTBOX_DIR / "chatgpt_clean_output.md").write_text(public_output(parsed), encoding="utf-8", newline="\n")
    write_json(OUTBOX_DIR / "state_writeback.json", parsed.writeback)

    if flavor_report.get("severity") != "pass":
        correction = maybe_v4_rewrite_correction(raw_output, flavor_report, memory)
        rewrite_input = build_chatgpt_rewrite_input(raw_output, flavor_report, correction)
        (OUTBOX_DIR / "chatgpt_rewrite_input.md").write_text(rewrite_input, encoding="utf-8", newline="\n")
        if flavor_report.get("rewrite_instruction"):
            (OUTBOX_DIR / "rewrite_instruction.md").write_text(flavor_report["rewrite_instruction"], encoding="utf-8", newline="\n")
    if flavor_report["severity"] == "heavy":
        raise RuntimeError("AI flavor check is heavy; run: python -m trpg_orchestrator.cli run-rewrite")

    pressure_pack = read_json(OUTBOX_DIR / "pressure_pack.json") if (OUTBOX_DIR / "pressure_pack.json").exists() else {}
    if skip_v4_audit:
        audit_result = {"decision": "accept", "reason": "skip-v4-audit enabled", "approved_writeback": parsed.writeback, "memory_files_to_update": [], "warnings": ["audit skipped"]}
    else:
        audit_result = extract_json_object(DeepSeekClient().complete_json(
            read_prompt("v4_audit_prompt.md"),
            build_audit_user_prompt(resolved, memory, pressure_pack, parsed.writeback),
        ))
    validate_audit_result(audit_result)
    write_json(OUTBOX_DIR / "v4_audit_result.json", audit_result)
    decision = audit_result.get("decision")
    if decision == "reject":
        store.write_log(resolved, _log_payload(action_text(), pressure_pack, raw_output, flavor_report, audit_result, {}))
        raise RuntimeError(f"V4 rejected writeback: {audit_result.get('reason', '')}")
    if decision not in {"accept", "revise"}:
        raise RuntimeError(f"invalid V4 audit decision: {decision}")

    approved = audit_result.get("approved_writeback") or parsed.writeback
    raw_digest = writeback_hash(parsed.writeback)
    approved_digest = writeback_hash(approved)
    for digest in (raw_digest, approved_digest):
        if has_applied_writeback(memory, digest):
            raise RuntimeError(f"duplicate writeback already applied: {digest[:12]}")
    updates = apply_approved_writeback(memory, approved, extra_hashes=[raw_digest])
    touched = list(updates.keys())
    if touched:
        store.backup_files(resolved, touched)
        store.write_memory_updates(resolved, updates)
    log_path = store.write_log(resolved, _log_payload(action_text(), pressure_pack, raw_output, flavor_report, audit_result, updates))
    print(f"updated files: {', '.join(touched) if touched else '(none)'}")
    print(f"log: {log_path}")
    print("\n" + public_output(parsed))
    return 0


def cmd_audit_writeback(campaign_id: str | None) -> int:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id)
    memory = store.load_campaign_memory(resolved)
    writeback_path = OUTBOX_DIR / "state_writeback.json"
    if not writeback_path.exists():
        raise FileNotFoundError("missing outbox/state_writeback.json")
    pressure_pack = read_json(OUTBOX_DIR / "pressure_pack.json") if (OUTBOX_DIR / "pressure_pack.json").exists() else {}
    writeback = read_json(writeback_path)
    validate_writeback(writeback)
    audit_result = extract_json_object(DeepSeekClient().complete_json(
        read_prompt("v4_audit_prompt.md"),
        build_audit_user_prompt(resolved, memory, pressure_pack, writeback),
    ))
    validate_audit_result(audit_result)
    write_json(OUTBOX_DIR / "v4_audit_result.json", audit_result)
    print(f"V4 audit decision: {audit_result.get('decision')}")
    print(audit_result.get("reason", ""))
    return 0


def cmd_rewrite_plan() -> int:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(None)
    memory = store.load_campaign_memory(resolved)
    raw_path = OUTBOX_DIR / "chatgpt_raw_output.md"
    if not raw_path.exists():
        raise FileNotFoundError("missing outbox/chatgpt_raw_output.md")
    raw_output = raw_path.read_text(encoding="utf-8")
    flavor_report = check_ai_flavor(raw_output, memory.get("forbidden_changes.json"))
    write_json(OUTBOX_DIR / "ai_flavor_report.json", flavor_report)
    correction = maybe_v4_rewrite_correction(raw_output, flavor_report, memory)
    (OUTBOX_DIR / "chatgpt_rewrite_input.md").write_text(
        build_chatgpt_rewrite_input(raw_output, flavor_report, correction),
        encoding="utf-8",
        newline="\n",
    )
    print(f"rewrite severity: {flavor_report.get('severity')}")
    print("wrote chatgpt_rewrite_input.md")
    return 0


def maybe_v4_rewrite_correction(raw_output: str, flavor_report: dict, memory: dict) -> dict:
    if flavor_report.get("severity") != "heavy":
        return {}
    pressure_pack = read_json(OUTBOX_DIR / "pressure_pack.json") if (OUTBOX_DIR / "pressure_pack.json").exists() else {}
    correction = extract_json_object(DeepSeekClient().complete_json(
        "You produce JSON-only correction instructions for rewriting TRPG prose. Do not write prose.",
        build_v4_rewrite_user_prompt(raw_output, flavor_report, pressure_pack, memory.get("forbidden_changes.json", {})),
    ))
    write_json(OUTBOX_DIR / "v4_rewrite_correction.json", correction)
    return correction


def cmd_migrate_memory() -> int:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(None)
    updates = migrate_legacy_facts(store.load_campaign_memory(resolved))
    touched = list(updates.keys())
    if touched:
        store.backup_files(resolved, touched)
        store.write_memory_updates(resolved, updates)
    print(f"migrated structured memory: {', '.join(touched) if touched else '(none)'}")
    return 0



def cmd_run_turn(action: str, campaign_id: str | None, offline_pressure_pack: bool, skip_v4_audit: bool, auto_rewrite: bool, rewrite_attempts: int) -> int:
    cmd_prepare(action, campaign_id, offline_pressure_pack)
    cmd_send(campaign_id)
    try:
        return cmd_ingest(campaign_id, skip_v4_audit)
    except RuntimeError as exc:
        if auto_rewrite and "AI flavor check is heavy" in str(exc):
            print("auto rewrite triggered")
            cmd_run_rewrite(rewrite_attempts)
            return cmd_ingest(campaign_id, skip_v4_audit)
        raise



def cmd_memory_compact(threshold: int = 12) -> int:
    store = MemoryStore()
    cid = store.resolve_campaign_id(None)
    memory = store.load_campaign_memory(cid)
    report = build_compaction_report(memory, threshold)
    write_json(OUTBOX_DIR / "memory_compaction_report.json", report)
    print(f"memory compact dry-run: {cid}")
    print(f"needs_compaction: {report['needs_any_compaction']}")
    for row in report["files"]:
        print(f"- {row['file']}:{row['bucket']} count={row['count']} compact={row['needs_compaction']}")
    for row in report["npcs"]:
        print(f"- npc:{row['npc']} facts={row['facts']} compact={row['needs_compaction']}")
    print("wrote outbox/memory_compaction_report.json")
    return 0


def cmd_memory_report() -> int:
    store = MemoryStore()
    cid = store.resolve_campaign_id(None)
    memory = store.load_campaign_memory(cid)
    print(f"memory report: {cid}")
    for filename, data in memory.items():
        facts = len(data.get("facts", [])) if isinstance(data.get("facts"), list) else 0
        migrated = data.get("legacy_facts_migrated", False)
        keys = []
        for key in ("npcs", "main_threads", "side_threads", "world_updates", "location_updates", "quest_updates", "mystery_updates", "equipment_updates", "growth_log"):
            value = data.get(key)
            if isinstance(value, dict):
                keys.append(f"{key}:{len(value)}")
            elif isinstance(value, list):
                keys.append(f"{key}:{len(value)}")
        print(f"- {filename}: facts={facts} migrated={migrated} {' '.join(keys)}")
    return 0


def cmd_validate_memory() -> int:
    store = MemoryStore()
    registry = store.load_registry()
    campaigns = registry.get("campaigns", {})
    if not campaigns:
        print("No campaigns registered.")
        return 0
    for campaign_id in campaigns:
        store.load_campaign_memory(campaign_id)
        print(f"OK memory: {campaign_id}")
    if (OUTBOX_DIR / "pressure_pack.json").exists():
        validate_pressure_pack(read_json(OUTBOX_DIR / "pressure_pack.json"))
        print("OK outbox/pressure_pack.json")
    if (OUTBOX_DIR / "state_writeback.json").exists():
        validate_writeback(read_json(OUTBOX_DIR / "state_writeback.json"))
        print("OK outbox/state_writeback.json")
    if (OUTBOX_DIR / "v4_audit_result.json").exists():
        validate_audit_result(read_json(OUTBOX_DIR / "v4_audit_result.json"))
        print("OK outbox/v4_audit_result.json")
    return 0


def action_text() -> str:
    path = OUTBOX_DIR / "last_player_action.txt"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _log_payload(player_action: str, pressure_pack: dict, raw_output: str, flavor_report: dict, audit_result: dict, final_updates: dict) -> dict:
    chatgpt_input_path = OUTBOX_DIR / "chatgpt_input.md"
    return {
        "user_input": player_action,
        "v4_pressure_pack": pressure_pack,
        "chatgpt_input": chatgpt_input_path.read_text(encoding="utf-8") if chatgpt_input_path.exists() else "",
        "chatgpt_raw_output": raw_output,
        "ai_flavor_report": flavor_report,
        "v4_audit_result": audit_result,
        "final_write": final_updates,
    }


def _offline_pressure_pack(campaign_id: str, action: str, memory: dict) -> dict:
    recent = memory.get("recent_context.json", {})
    scene = recent.get("current_scene", {})
    return {
        "campaign_id": campaign_id,
        "turn_type": "normal_progress",
        "creation_mode": {"label": "offline-dev", "divergence_level": "low", "stability_requirement": "follow existing memory; no new hard canon"},
        "current_situation": {"time": scene.get("time", ""), "location": scene.get("location", ""), "immediate_context": scene.get("immediate_pressure", ""), "previous_consequence": recent.get("last_outcome", "")},
        "pressure_pack": {"core_accident_or_change": f"small change around player action: {action}", "human_pressure": "", "environment_pressure": "", "enemy_or_mystery_pressure": "", "resource_or_time_pressure": "", "conflicting_interests": []},
        "npc_direction": [],
        "scene_materials": [],
        "must_reveal_naturally": [],
        "must_not_explain_directly": [],
        "forbidden_this_turn": memory.get("forbidden_changes.json", {}).get("global_forbidden", []),
        "player_pressure_point": "",
        "choice_requirement": {"need_choice": False, "choice_level": "none", "why": "offline development placeholder", "choice_style": "no_choice"},
        "ending_target": "",
        "state_update_hints": [],
        "human_readable_note": "offline development placeholder pressure pack; use DeepSeek V4 for formal play.",
    }


if __name__ == "__main__":
    raise SystemExit(main())
