# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from .ai_flavor_checker import check_ai_flavor
from .capability_resolver import build_capability_plan
from .chatgpt_web_client import ChatGPTWebClient, browser_evidence_path, sha256_file
from .config import CAMPAIGNS_DIR, OUTBOX_DIR, PROJECT_ROOT, REGISTRY_PATH
from .deepseek_client import DeepSeekClient
from .encoding_utils import assert_valid_user_text, read_runtime_text, write_text_utf8
from .encoding_validator import validate_repository_encoding
from .json_utils import extract_json_object, read_json, write_json
from .memory_store import MemoryStore
from .memory_compactor import build_compaction_report
from .output_parser import parse_chatgpt_output, public_output, visible_prose_chars
from .output_contract import summarize_payload_keys
from .payload_fulfillment import build_payload_fulfillment_input, defer_unfulfilled_requests, diff_requested_capabilities, finalize_capability_plan, merge_payload_patch, skipped_payload_patch
from .prompt_builder import build_audit_user_prompt, build_chatgpt_image_input, build_chatgpt_input, build_director_user_prompt, build_v4_light_action_user_prompt, read_prompt, selected_memory_debug, selected_prompt_modules_debug
from .prompt_sync import prompt_sync_report
from .rewrite_manager import build_chatgpt_rewrite_input, build_v4_rewrite_user_prompt
from .runtime_hygiene import pre_upload_clean
from .schema_validator import normalize_pressure_pack_compat, validate_audit_result, validate_chatgpt_blocks, validate_payload_patch, validate_pressure_pack, validate_writeback
from .scene_action_guard import scene_action_warning_from_pressure_pack
from .story_progress import build_backend_progress_control, validate_story_blueprint
from .quality_gate import quality_gate, is_quality_pass
from .writeback import apply_approved_writeback, migrate_legacy_facts, writeback_hash, has_applied_writeback


OUTBOX_FILE_NAMES = {
    "last_player_action.txt",
    "capability_plan.json",
    "selected_prompt_modules.json",
    "selected_director_memory.json",
    "selected_actor_memory.json",
    "pressure_pack_core.json",
    "missing_capabilities.json",
    "payload_fulfillment_input.md",
    "payload_patch.json",
    "pressure_pack.json",
    "pressure_pack_normalized.json",
    "chatgpt_input.md",
    "chatgpt_raw_output.md",
    "chatgpt_image_input.md",
    "chatgpt_image_raw_output.md",
    "chatgpt_image_raw_output.png",
    "image_job.json",
    "chatgpt_clean_output.md",
    "chatgpt_blocks.json",
    "state_writeback.json",
    "v4_audit_result.json",
    "ai_flavor_report.json",
    "chatgpt_rewrite_input.md",
    "chatgpt_raw_output_rewrite.md",
    "rewrite_instruction.md",
    "v4_rewrite_correction.json",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trpg")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("validate-memory")
    sub.add_parser("validate-encoding")
    pre_upload = sub.add_parser("pre-upload-clean")
    pre_upload.add_argument("--check-only", action="store_true")
    sync_prompts = sub.add_parser("sync-prompts")
    sync_mode = sync_prompts.add_mutually_exclusive_group(required=True)
    sync_mode.add_argument("--check", action="store_true")
    sync_mode.add_argument("--apply", action="store_true")
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

    image_send = sub.add_parser("send-image")
    image_send.add_argument("--campaign-id")

    import_cg = sub.add_parser("import-cg")
    import_cg.add_argument("--campaign-id")
    import_cg.add_argument("--image-path", required=True)
    import_cg.add_argument("--title", default="CG")
    import_cg.add_argument("--detail", default="本回合剧情 CG。")
    import_cg.add_argument("--mode", choices=["dual-preview", "single"], default="dual-preview")

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
        if args.command == "validate-encoding":
            return cmd_validate_encoding()
        if args.command == "pre-upload-clean":
            return cmd_pre_upload_clean(args.check_only)
        if args.command == "sync-prompts":
            return cmd_sync_prompts(args.apply)
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
        if args.command == "send-image":
            return cmd_send_image(args.campaign_id)
        if args.command == "import-cg":
            return cmd_import_cg(args.campaign_id, args.image_path, args.title, args.detail, args.mode)
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


def cmd_sync_prompts(apply: bool = False) -> int:
    report = prompt_sync_report(apply=apply)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


def cmd_pre_upload_clean(check_only: bool = False) -> int:
    report = pre_upload_clean(check_only=check_only)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


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


def safe_campaign_segment(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value).strip("_") or "campaign"


def campaign_outbox_dir(campaign_id: str) -> Path:
    path = CAMPAIGNS_DIR / safe_campaign_segment(campaign_id) / "outbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def preserve_submitted_player_action(parsed: Any, player_action: str) -> Any:
    action = str(player_action or "").strip()
    if not action:
        return parsed
    blocks = [dict(block) if isinstance(block, dict) else block for block in (getattr(parsed, "blocks", []) or [])]
    if blocks and isinstance(blocks[0], dict) and blocks[0].get("type") == "player_action":
        blocks[0]["body"] = action
    return parsed.__class__(
        body=getattr(parsed, "body", ""),
        choices=getattr(parsed, "choices", ""),
        summary=getattr(parsed, "summary", ""),
        writeback=getattr(parsed, "writeback", {}),
        blocks=blocks,
    )


def mirror_to_global_outbox(outbox_dir: Path, filenames: list[str] | None = None) -> None:
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    names = filenames or sorted(OUTBOX_FILE_NAMES)
    for name in names:
        source = outbox_dir / name
        if source.exists():
            shutil.copy2(source, OUTBOX_DIR / name)


def sync_global_reply_if_newer(outbox_dir: Path) -> None:
    global_raw = OUTBOX_DIR / "chatgpt_raw_output.md"
    scoped_raw = outbox_dir / "chatgpt_raw_output.md"
    if not global_raw.exists():
        return
    if not scoped_raw.exists() or global_raw.stat().st_mtime > scoped_raw.stat().st_mtime:
        shutil.copy2(global_raw, scoped_raw)


def anchor_progress_control(pressure_pack: dict, memory: dict) -> dict:
    if not isinstance(pressure_pack, dict):
        return pressure_pack
    control = build_backend_progress_control(
        memory.get("story_blueprint.json", {}),
        memory.get("story_progress.json", {}),
        pressure_pack.get("progress_control") if isinstance(pressure_pack.get("progress_control"), dict) else {},
    )
    warnings = control.pop("protocol_warnings", [])
    pressure_pack["progress_control"] = control
    if warnings:
        pressure_pack.setdefault("protocol_warnings", [])
        if isinstance(pressure_pack["protocol_warnings"], list):
            for warning in warnings:
                if warning not in pressure_pack["protocol_warnings"]:
                    pressure_pack["protocol_warnings"].append(warning)
    return pressure_pack


def emit_public_job_status(stage: str, label: str, percent: int | None = None, public_think: list | None = None) -> None:
    payload = {"stage": stage, "label": label}
    if percent is not None:
        payload["percent"] = percent
    if public_think:
        payload["public_think"] = public_think
    print("TRPG_WORKER_STATUS " + json.dumps(payload, ensure_ascii=False), flush=True)


def cmd_prepare(action: str, campaign_id: str | None, offline_pressure_pack: bool = False) -> int:
    action = assert_valid_user_text(action, "player action").strip()
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id)
    memory = store.load_campaign_memory(resolved)
    outbox_dir = campaign_outbox_dir(resolved)
    write_text_utf8(outbox_dir / "last_player_action.txt", action)
    capability_plan = build_capability_plan(resolved, action, memory)
    write_json(outbox_dir / "capability_plan.json", capability_plan)
    director_user_prompt = build_director_user_prompt(resolved, action, memory, capability_plan)
    write_text_utf8(outbox_dir / "v4_director_input.md", director_user_prompt)
    emit_public_job_status("director_turn", "导演层正在判断本回合局势", 18)
    if offline_pressure_pack:
        core_pressure_pack = _offline_pressure_pack(resolved, action, memory)
    else:
        client = DeepSeekClient()
        core_pressure_pack = extract_json_object(client.complete_json(
            read_prompt("v4_director_prompt.md"),
            director_user_prompt,
        ))
    emit_public_job_status(
        "director_turn",
        str(core_pressure_pack.get("human_readable_note") or "导演层已生成本回合压力包"),
        30,
        core_pressure_pack.get("public_think") if isinstance(core_pressure_pack.get("public_think"), list) else None,
    )
    core_pressure_pack = normalize_pressure_pack_compat(core_pressure_pack)
    if scene_action_warning_from_pressure_pack(core_pressure_pack):
        validate_pressure_pack(core_pressure_pack, resolved, require_payloads=False)
        if write_scene_action_warning_turn(resolved, action, memory, outbox_dir, core_pressure_pack, capability_plan):
            return 0
    anchor_progress_control(core_pressure_pack, memory)
    validate_pressure_pack(core_pressure_pack, resolved, require_payloads=False)
    write_json(outbox_dir / "pressure_pack_core.json", core_pressure_pack)
    missing = diff_requested_capabilities(core_pressure_pack.get("output_requests", {}), capability_plan.get("loaded_capabilities", []), core_pressure_pack.get("payloads", {}))
    write_json(outbox_dir / "missing_capabilities.json", missing)
    if missing.get("missing_capabilities"):
        fulfillment_input = build_payload_fulfillment_input(resolved, memory, core_pressure_pack, missing, capability_plan)
        write_text_utf8(outbox_dir / "payload_fulfillment_input.md", fulfillment_input)
        if offline_pressure_pack:
            payload_patch = skipped_payload_patch("offline pressure pack skips model payload fulfillment")
        else:
            payload_patch = extract_json_object(DeepSeekClient().complete_json(read_prompt("v4_payload_fulfillment_prompt.md"), fulfillment_input))
        if not payload_patch.get("skipped"):
            validate_payload_patch(payload_patch)
            pressure_pack = merge_payload_patch(core_pressure_pack, payload_patch)
        else:
            pressure_pack = defer_unfulfilled_requests(core_pressure_pack, str(payload_patch.get("reason") or "payload fulfillment skipped"))
    else:
        payload_patch = skipped_payload_patch("no missing capabilities")
        write_text_utf8(outbox_dir / "payload_fulfillment_input.md", "")
        pressure_pack = core_pressure_pack
    write_json(outbox_dir / "payload_patch.json", payload_patch)
    pressure_pack = normalize_pressure_pack_compat(pressure_pack)
    anchor_progress_control(pressure_pack, memory)
    validate_pressure_pack(pressure_pack, resolved)
    capability_plan = finalize_capability_plan(capability_plan, pressure_pack)
    write_json(outbox_dir / "pressure_pack.json", pressure_pack)
    write_json(outbox_dir / "pressure_pack_normalized.json", pressure_pack)
    debug_memory = selected_memory_debug(resolved, action, memory, pressure_pack, capability_plan)
    write_json(outbox_dir / "selected_director_memory.json", debug_memory["director"])
    write_json(outbox_dir / "selected_actor_memory.json", debug_memory["actor_visible"])
    write_json(outbox_dir / "selected_prompt_modules.json", selected_prompt_modules_debug(capability_plan, pressure_pack))
    write_json(outbox_dir / "capability_plan.json", capability_plan)
    if write_scene_action_warning_turn(resolved, action, memory, outbox_dir, pressure_pack, capability_plan):
        return 0
    write_text_utf8(
        outbox_dir / "chatgpt_input.md",
        build_chatgpt_input(resolved, action, memory, pressure_pack, capability_plan),
    )
    emit_public_job_status("actor_waiting", "演员层正在生成正文", 42)
    mirror_to_global_outbox(outbox_dir, ["last_player_action.txt", "capability_plan.json", "selected_prompt_modules.json", "selected_director_memory.json", "selected_actor_memory.json", "v4_director_input.md", "pressure_pack_core.json", "missing_capabilities.json", "payload_fulfillment_input.md", "payload_patch.json", "pressure_pack.json", "pressure_pack_normalized.json", "chatgpt_input.md"])
    print(f"wrote {outbox_dir / 'pressure_pack.json'} and {outbox_dir / 'chatgpt_input.md'}")
    return 0


LIGHT_DIRECTOR_ACTIONS = {"观察周围", "与npc对话", "检查物品"}


def is_light_director_action(action: str) -> bool:
    normalized = re.sub(r"\s+", "", str(action or "")).lower()
    return normalized in LIGHT_DIRECTOR_ACTIONS


def cmd_v4_light_action(action: str, campaign_id: str | None, skip_v4_audit: bool = True) -> int:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id)
    memory = store.load_campaign_memory(resolved)
    outbox_dir = campaign_outbox_dir(resolved)
    write_text_utf8(outbox_dir / "last_player_action.txt", action)
    capability_plan = build_capability_plan(resolved, action, memory)
    write_json(outbox_dir / "capability_plan.json", capability_plan)
    user_prompt = build_v4_light_action_user_prompt(resolved, action, memory)
    write_text_utf8(outbox_dir / "v4_director_input.md", user_prompt)
    pressure_pack = _light_action_pressure_pack(resolved, action)
    write_json(outbox_dir / "pressure_pack.json", pressure_pack)
    raw_output = DeepSeekClient().complete_json(
        read_prompt("v4_light_action_rules.md"),
        user_prompt,
    )
    write_text_utf8(outbox_dir / "chatgpt_raw_output.md", raw_output)
    parsed = parse_chatgpt_output(raw_output)
    parsed = preserve_submitted_player_action(parsed, action)
    validate_chatgpt_blocks(parsed.blocks)
    writeback = normalize_light_writeback(parsed.writeback)
    validate_writeback(writeback)
    write_text_utf8(outbox_dir / "chatgpt_clean_output.md", public_output(parsed))
    write_json(outbox_dir / "chatgpt_blocks.json", {
        "blocks": parsed.blocks,
        "body": parsed.body,
        "choices": parsed.choices,
        "summary": parsed.summary,
    })
    write_json(outbox_dir / "state_writeback.json", writeback)
    if skip_v4_audit:
        audit_result = {"decision": "accept", "reason": "director light action direct path", "approved_writeback": writeback, "memory_files_to_update": [], "warnings": ["actor layer skipped for fixed light action"]}
    else:
        audit_result = extract_json_object(DeepSeekClient().complete_json(
            read_prompt("v4_audit_prompt.md"),
            build_audit_user_prompt(resolved, memory, pressure_pack, writeback, capability_plan),
        ))
    validate_audit_result(audit_result)
    if audit_result.get("decision") in {"accept", "revise"}:
        validate_writeback(audit_result.get("approved_writeback") or writeback)
    write_json(outbox_dir / "v4_audit_result.json", audit_result)
    approved = audit_result.get("approved_writeback") or parsed.writeback
    raw_digest = writeback_hash(writeback)
    approved_digest = writeback_hash(approved)
    for digest in (raw_digest, approved_digest):
        if has_applied_writeback(memory, digest):
            raise RuntimeError(f"duplicate writeback already applied: {digest[:12]}")
    validate_writeback(approved)
    updates = apply_approved_writeback(memory, approved, extra_hashes=[raw_digest], pressure_pack=pressure_pack, prose_chars_delta=visible_prose_chars(parsed.blocks))
    run_records = append_run_record(
        memory.get("run_records.json", {}),
        resolved,
        action,
        parsed,
        outbox_dir,
        pressure_pack,
        audit_result,
        updates,
    )
    updates["run_records.json"] = run_records
    touched = list(updates.keys())
    if touched:
        store.backup_files(resolved, touched)
        store.write_memory_updates(resolved, updates)
    log_path = store.write_log(resolved, _log_payload(action, pressure_pack, raw_output, {"severity": "pass", "path": "director_light_action"}, audit_result, updates, outbox_dir, capability_plan=capability_plan))
    mirror_to_global_outbox(outbox_dir)
    print(f"director light action path: {action}")
    print(f"updated files: {', '.join(touched) if touched else '(none)'}")
    print(f"log: {log_path}")
    print("\n" + public_output(parsed))
    return 0


def web_client(campaign_id: str | None = None) -> ChatGPTWebClient:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id)
    memory = store.load_campaign_memory(resolved)
    return ChatGPTWebClient(memory["campaign_profile.json"], memory)


def cmd_send(campaign_id: str | None) -> int:
    resolved = MemoryStore().resolve_campaign_id(campaign_id)
    outbox_dir = campaign_outbox_dir(resolved)
    ensure_chatgpt_input_current(outbox_dir)
    emit_public_job_status("actor_waiting", "等待 ChatGPT 常驻浏览器返回", 48)
    web_client(resolved).send_and_capture(outbox_dir / "chatgpt_input.md", outbox_dir / "chatgpt_raw_output.md")
    emit_public_job_status("parsing", "正文已返回，正在解析结构化输出", 72)
    mirror_to_global_outbox(outbox_dir, ["chatgpt_input.md", "chatgpt_raw_output.md"])
    print(f"sent {outbox_dir / 'chatgpt_input.md'} and captured {outbox_dir / 'chatgpt_raw_output.md'}")
    return 0


def ensure_chatgpt_input_current(outbox_dir: Path) -> None:
    input_path = outbox_dir / "chatgpt_input.md"
    pressure_path = outbox_dir / "pressure_pack.json"
    action_path = outbox_dir / "last_player_action.txt"
    if not input_path.exists():
        raise RuntimeError("chatgpt_input.md missing; run prepare before send")
    input_mtime = input_path.stat().st_mtime
    freshness_sources = [path for path in (pressure_path, action_path) if path.exists()]
    stale_sources = [path.name for path in freshness_sources if input_mtime + 0.001 < path.stat().st_mtime]
    if stale_sources:
        raise RuntimeError(f"chatgpt_input.md stale relative to: {', '.join(stale_sources)}; rerun prepare")
    action = read_runtime_text(action_path).strip() if action_path.exists() else ""
    text = read_runtime_text(input_path)
    if action and action not in text:
        raise RuntimeError("chatgpt_input.md does not contain current player action; rerun prepare")
    if text.strip() == "Scene action warning; actor layer skipped.":
        raise RuntimeError("scene action warning turn must not be sent to actor layer")


def cmd_capture(campaign_id: str | None) -> int:
    resolved = MemoryStore().resolve_campaign_id(campaign_id)
    outbox_dir = campaign_outbox_dir(resolved)
    web_client(resolved).capture_latest(outbox_dir / "chatgpt_raw_output.md")
    mirror_to_global_outbox(outbox_dir, ["chatgpt_raw_output.md"])
    print(f"captured latest assistant reply into {outbox_dir / 'chatgpt_raw_output.md'}")
    return 0


def cmd_send_image(campaign_id: str | None) -> int:
    resolved = MemoryStore().resolve_campaign_id(campaign_id)
    outbox_dir = campaign_outbox_dir(resolved)
    pressure_pack = normalize_pressure_pack_compat(read_json(outbox_dir / "pressure_pack.json")) if (outbox_dir / "pressure_pack.json").exists() else {}
    action = action_text(outbox_dir)
    assets = image_pass_assets(pressure_pack)
    if not image_pass_requested(action, pressure_pack):
        write_json(outbox_dir / "image_job.json", {"status": "skipped", "reason": "no image trigger", "visual_asset_count": len(assets)})
        print("image pass skipped: no image trigger")
        return 0
    write_text_utf8(outbox_dir / "chatgpt_image_input.md", build_chatgpt_image_input(resolved, action, pressure_pack, assets))
    write_json(outbox_dir / "image_job.json", {
        "status": "prepared",
        "campaign_id": resolved,
        "trigger": "player_action" if explicit_image_action(action) else "v4_visual_assets",
        "visual_asset_count": len(assets),
        "input_path": str(outbox_dir / "chatgpt_image_input.md"),
        "output_path": str(outbox_dir / "chatgpt_image_raw_output.md"),
        "image_artifact_path": str(outbox_dir / "chatgpt_image_raw_output.png"),
        "note": "Image generation is intentionally split from the story JSON pass.",
    })
    web_client(resolved).send_file_and_capture(outbox_dir / "chatgpt_image_input.md", outbox_dir / "chatgpt_image_raw_output.md", mode="image")
    saved_asset = save_image_artifact_asset(resolved, outbox_dir, assets)
    write_json(outbox_dir / "image_job.json", {
        "status": "captured",
        "campaign_id": resolved,
        "trigger": "player_action" if explicit_image_action(action) else "v4_visual_assets",
        "visual_asset_count": len(assets),
        "input_path": str(outbox_dir / "chatgpt_image_input.md"),
        "output_path": str(outbox_dir / "chatgpt_image_raw_output.md"),
        "image_artifact_path": str(outbox_dir / "chatgpt_image_raw_output.png"),
        "image_artifact_exists": (outbox_dir / "chatgpt_image_raw_output.png").exists(),
        "asset": saved_asset,
        "note": "Image generation completed as a separate actor image pass; backend/frontend may attach the image artifact to gallery display.",
    })
    mirror_to_global_outbox(outbox_dir, ["chatgpt_image_input.md", "chatgpt_image_raw_output.md", "chatgpt_image_raw_output.png", "image_job.json"])
    print(f"sent image pass and captured {outbox_dir / 'chatgpt_image_raw_output.md'}")
    return 0


def save_image_artifact_asset(campaign_id: str, outbox_dir: Path, assets: list[dict]) -> dict:
    artifact = outbox_dir / "chatgpt_image_raw_output.png"
    if not artifact.exists():
        return {}
    first = assets[0] if assets else {}
    key = f"generated_image:{safe_cli_segment(str(first.get('id') or first.get('title') or 'requested_image'))}"
    metadata = {
        "title": str(first.get("title") or "生图结果"),
        "detail": str(first.get("detail") or first.get("positive_prompt") or ""),
        "meta": "生图结果",
        "source": "chatgpt_image_pass",
        "object_id": key,
        "image_prompt": first.get("image_prompt") or {
            "positive_prompt": first.get("positive_prompt", ""),
            "negative_prompt": first.get("negative_prompt", ""),
            "aspect_ratio": first.get("aspect_ratio", ""),
            "style_preset": first.get("style_preset", ""),
            "quality": first.get("quality", {}),
        },
    }
    from .web_server import save_asset
    saved = save_asset({
        "campaign_id": campaign_id,
        "key": key,
        "kind": "gallery_image",
        "subdir": "generated",
        "filename": key,
        "data_url": "data:image/png;base64," + base64.b64encode(artifact.read_bytes()).decode("ascii"),
        "seed": key,
        "style": "chatgpt_image",
        "generator_version": 1,
        "metadata": metadata,
    })
    append_story_cg_block(campaign_id, outbox_dir, saved, metadata)
    return saved


def cmd_import_cg(campaign_id: str | None, image_path: str, title: str, detail: str, mode: str = "dual-preview") -> int:
    resolved = MemoryStore().resolve_campaign_id(campaign_id)
    source = Path(image_path).expanduser().resolve()
    if not source.exists():
        raise RuntimeError(f"image not found: {source}")
    outbox_dir = campaign_outbox_dir(resolved)
    saved = import_cg_image_assets(resolved, source, title, detail, mode)
    append_story_cg_block(resolved, outbox_dir, saved["pc"], saved["metadata"])
    write_json(outbox_dir / "image_job.json", {
        "status": "imported",
        "campaign_id": resolved,
        "source_path": str(source),
        "assets": saved,
        "note": "Imported formal CG, cached PC 16:9 and mobile 9:16 variants, and attached PC image to latest story blocks.",
    })
    mirror_to_global_outbox(outbox_dir, ["chatgpt_blocks.json", "image_job.json"])
    print(f"imported CG into {resolved}: {saved['pc'].get('url', '')}")
    return 0


def import_cg_image_assets(campaign_id: str, source: Path, title: str, detail: str, mode: str = "dual-preview") -> dict:
    from io import BytesIO
    from PIL import Image
    from .web_server import save_asset

    image = Image.open(source).convert("RGBA")
    use_dual = mode == "dual-preview"
    pc_image, mobile_image = split_dual_preview_image(image) if use_dual else (fit_ratio(image, 16, 9), fit_ratio(image, 9, 16))
    pc_image = enhance_display_image(pc_image, brightness=1.33, contrast=1.12, color=1.06)
    mobile_image = enhance_display_image(mobile_image, brightness=1.33, contrast=1.12, color=1.06)
    base_id = safe_cli_segment(source.stem or title or "cg")
    pc_key = f"generated_cg:{base_id}:pc_16x9"
    mobile_key = f"generated_cg:{base_id}:mobile_9x16"
    metadata = {
        "title": title,
        "detail": detail,
        "meta": "正式生图 CG",
        "source": "manual_import_cg",
        "object_id": base_id,
        "layout_variants": {"pc": "16:9", "mobile": "9:16"},
        "default_variant": "pc",
        "source_path": str(source),
        "display_enhancement": {"brightness": 1.33, "contrast": 1.12, "color": 1.06, "reason": "正文展示避免暗部糊黑"},
    }
    pc_saved = save_asset({
        "campaign_id": campaign_id,
        "key": pc_key,
        "kind": "gallery_image",
        "subdir": "generated",
        "filename": f"{base_id}_pc_16x9",
        "data_url": png_data_url(pc_image),
        "seed": pc_key,
        "style": "formal_cg_pc_16x9",
        "generator_version": 1,
        "metadata": {**metadata, "aspect_ratio": "16:9", "variant": "pc"},
    })
    mobile_saved = save_asset({
        "campaign_id": campaign_id,
        "key": mobile_key,
        "kind": "gallery_image_mobile",
        "subdir": "generated",
        "filename": f"{base_id}_mobile_9x16",
        "data_url": png_data_url(mobile_image),
        "seed": mobile_key,
        "style": "formal_cg_mobile_9x16",
        "generator_version": 1,
        "metadata": {**metadata, "aspect_ratio": "9:16", "variant": "mobile", "paired_asset_key": pc_key},
    })
    return {"metadata": metadata, "pc": pc_saved, "mobile": mobile_saved}


def split_dual_preview_image(image):
    """Split the standard dark UI 16:9 / 9:16 preview board into display crops."""
    w, h = image.size
    pc_box = (
        int(w * 0.018),
        int(h * 0.145),
        int(w * 0.666),
        int(h * 0.748),
    )
    mobile_box = (
        int(w * 0.704),
        int(h * 0.050),
        int(w * 0.966),
        int(h * 0.748),
    )
    return fit_ratio(image.crop(pc_box), 16, 9), fit_ratio(image.crop(mobile_box), 9, 16)


def fit_ratio(image, ratio_w: int, ratio_h: int):
    width, height = image.size
    target = ratio_w / ratio_h
    current = width / max(height, 1)
    if current > target:
        new_width = int(height * target)
        left = max(0, (width - new_width) // 2)
        return image.crop((left, 0, left + new_width, height))
    new_height = int(width / target)
    top = max(0, (height - new_height) // 2)
    return image.crop((0, top, width, top + new_height))


def enhance_display_image(image, brightness: float = 1.0, contrast: float = 1.0, color: float = 1.0):
    from PIL import ImageEnhance
    result = image.convert("RGB")
    result = ImageEnhance.Brightness(result).enhance(brightness)
    result = ImageEnhance.Contrast(result).enhance(contrast)
    result = ImageEnhance.Color(result).enhance(color)
    return result


def png_data_url(image) -> str:
    from io import BytesIO
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def append_story_cg_block(campaign_id: str, outbox_dir: Path, asset: dict, metadata: dict) -> None:
    if not asset or not asset.get("exists"):
        return
    blocks_path = outbox_dir / "chatgpt_blocks.json"
    payload = read_json(blocks_path) if blocks_path.exists() else {
        "campaign_id": campaign_id,
        "turn_title": metadata.get("title") or "CG",
        "blocks": [],
        "summary": "",
        "state_writeback": {},
    }
    blocks = payload.get("blocks")
    if not isinstance(blocks, list):
        blocks = []
        payload["blocks"] = blocks
    key = asset.get("key", "")
    blocks[:] = [block for block in blocks if block.get("asset_key") != key]
    scene_detail = public_cg_scene_detail(metadata)
    cg_block = {
        "id": f"cg_{safe_cli_segment(str(key))}",
        "type": "cg_image",
        "speaker": "CG",
        "body": scene_detail,
        "time": "",
        "avatar_key": "cg",
        "actor_id": "cg",
        "actor_kind": "gm",
        "check": {},
        "choices": [],
        "tags": ["cg", "image"],
        "asset_key": key,
        "cached_url": asset.get("url", ""),
        "image_title": "CG",
        "image_detail": scene_detail,
        "aspect_ratio": "16:9",
    }
    choice_index = next((index for index, block in enumerate(blocks) if block.get("type") == "choice_prompt"), len(blocks))
    blocks.insert(choice_index, cg_block)
    payload["campaign_id"] = payload.get("campaign_id") or campaign_id
    payload["summary"] = payload.get("summary") or metadata.get("detail") or ""
    write_json(blocks_path, payload)


def public_cg_scene_detail(metadata: dict) -> str:
    text = str(metadata.get("public_detail") or metadata.get("scene_detail") or metadata.get("detail") or "").strip()
    technical = re.compile(r"16\s*:\s*9|9\s*:\s*16|PC|手机|构图|预览|正式图标|正式深度图片|头像反哺|反哺|画幅|aspect|ratio|mobile|variant|crop|safe area|缓存|技术|参数", re.I)
    if not text or technical.search(text):
        text = "雨夜小卖部门口，Lee 抱紧金属盒，黑水倒影逼近。"
    text = re.split(r"[。；;]\s*(?:16\s*:\s*9|9\s*:\s*16|PC|手机|构图|预览|头像反哺|反哺|缓存|技术|参数)", text, maxsplit=1, flags=re.I)[0]
    text = re.sub(r"\s+", " ", text).strip()
    return text[:72] or "本回合剧情 CG。"


def safe_cli_segment(value: str) -> str:
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff._-]+", "_", value or "asset").strip("_")
    return text[:80] or "asset"


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
    original_raw = read_runtime_text(raw_path) if raw_path.exists() else ""
    working_raw = original_raw
    for attempt in range(1, max_attempts + 1):
        print(f"rewrite attempt {attempt}/{max_attempts}")
        if working_raw:
            write_text_utf8(raw_path, working_raw)
        cmd_rewrite_plan()
        web_client(None).send_file_and_capture(OUTBOX_DIR / "chatgpt_rewrite_input.md", OUTBOX_DIR / "chatgpt_raw_output_rewrite.md")
        rewritten = read_runtime_text(OUTBOX_DIR / "chatgpt_raw_output_rewrite.md")
        gate = quality_gate(rewritten, memory.get("forbidden_changes.json", {}), OUTBOX_DIR, prefix=f"rewrite_{attempt}_")
        severity = gate["flavor_report"].get("severity")
        print(f"rewrite attempt severity: {severity}")
        if is_quality_pass(gate["flavor_report"]):
            shutil.copy2(OUTBOX_DIR / "chatgpt_raw_output_rewrite.md", raw_path)
            print("rewrite accepted and promoted")
            return 0
        working_raw = rewritten
    if original_raw:
        write_text_utf8(raw_path, original_raw)
    raise RuntimeError("rewrite attempts exhausted; latest rewrite saved as chatgpt_raw_output_rewrite.md but not promoted")

def cmd_promote_rewrite() -> int:
    source = OUTBOX_DIR / "chatgpt_raw_output_rewrite.md"
    if not source.exists():
        raise FileNotFoundError("missing outbox/chatgpt_raw_output_rewrite.md")
    parsed = parse_chatgpt_output(read_runtime_text(source))
    validate_writeback(parsed.writeback)
    shutil.copy2(source, OUTBOX_DIR / "chatgpt_raw_output.md")
    print("promoted rewrite output to chatgpt_raw_output.md")
    return 0


def cmd_ingest(campaign_id: str | None, skip_v4_audit: bool = False) -> int:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id)
    memory = store.load_campaign_memory(resolved)
    outbox_dir = campaign_outbox_dir(resolved)
    sync_global_reply_if_newer(outbox_dir)
    raw_path = outbox_dir / "chatgpt_raw_output.md"
    if not raw_path.exists():
        raise FileNotFoundError(f"missing {outbox_dir / 'chatgpt_raw_output.md'}")
    verify_browser_evidence_before_ingest(raw_path, resolved)
    raw_output = read_runtime_text(raw_path)
    emit_public_job_status("parsing", "正在解析正文与状态回写", 76)
    gate = quality_gate(raw_output, memory.get("forbidden_changes.json", {}), outbox_dir)
    parsed = gate["parsed"]
    parsed = preserve_submitted_player_action(parsed, action_text(outbox_dir))
    validate_chatgpt_blocks(parsed.blocks)
    flavor_report = gate["flavor_report"]
    write_text_utf8(outbox_dir / "chatgpt_clean_output.md", public_output(parsed))
    write_json(outbox_dir / "chatgpt_blocks.json", {
        "blocks": parsed.blocks,
        "body": parsed.body,
        "choices": parsed.choices,
        "summary": parsed.summary,
    })
    write_json(outbox_dir / "state_writeback.json", parsed.writeback)

    if flavor_report.get("severity") != "pass":
        correction = maybe_v4_rewrite_correction(raw_output, flavor_report, memory)
        rewrite_input = build_chatgpt_rewrite_input(raw_output, flavor_report, correction)
        write_text_utf8(outbox_dir / "chatgpt_rewrite_input.md", rewrite_input)
        if flavor_report.get("rewrite_instruction"):
            write_text_utf8(outbox_dir / "rewrite_instruction.md", flavor_report["rewrite_instruction"])
    if flavor_report["severity"] == "heavy":
        raise RuntimeError("AI flavor check is heavy; run: python -m trpg_orchestrator.cli run-rewrite")

    pressure_pack = normalize_pressure_pack_compat(read_json(outbox_dir / "pressure_pack.json")) if (outbox_dir / "pressure_pack.json").exists() else {}
    capability_plan = read_capability_plan(outbox_dir, resolved, action_text(outbox_dir), memory)
    if skip_v4_audit:
        audit_result = {"decision": "accept", "reason": "skip-v4-audit enabled", "approved_writeback": parsed.writeback, "memory_files_to_update": [], "warnings": ["audit skipped"]}
    else:
        emit_public_job_status("writeback", "V4 正在审核状态写回", 84)
        audit_result = extract_json_object(DeepSeekClient().complete_json(
            read_prompt("v4_audit_prompt.md"),
            build_audit_user_prompt(resolved, memory, pressure_pack, parsed.writeback, capability_plan),
        ))
    validate_audit_result(audit_result)
    write_json(outbox_dir / "v4_audit_result.json", audit_result)
    decision = audit_result.get("decision")
    if decision == "reject":
        store.write_log(resolved, _log_payload(action_text(outbox_dir), pressure_pack, raw_output, flavor_report, audit_result, {}, outbox_dir, capability_plan=capability_plan))
        raise RuntimeError(f"Director rejected writeback: {audit_result.get('reason', '')}")
    if decision not in {"accept", "revise"}:
        raise RuntimeError(f"invalid director audit decision: {decision}")

    approved = audit_result.get("approved_writeback") or parsed.writeback
    validate_writeback(approved)
    raw_digest = writeback_hash(parsed.writeback)
    approved_digest = writeback_hash(approved)
    for digest in (raw_digest, approved_digest):
        if has_applied_writeback(memory, digest):
            raise RuntimeError(f"duplicate writeback already applied: {digest[:12]}")
    story_progress_before = memory.get("story_progress.json", {})
    updates = apply_approved_writeback(memory, approved, extra_hashes=[raw_digest], pressure_pack=pressure_pack, prose_chars_delta=visible_prose_chars(parsed.blocks))
    story_progress_after = updates.get("story_progress.json", story_progress_before)
    run_records = append_run_record(
        memory.get("run_records.json", {}),
        resolved,
        action_text(outbox_dir),
        parsed,
        outbox_dir,
        pressure_pack,
        audit_result,
        updates,
    )
    updates["run_records.json"] = run_records
    touched = list(updates.keys())
    if touched:
        emit_public_job_status("writeback", "正在写回长期记忆", 92)
        store.backup_files(resolved, touched)
        store.write_memory_updates(resolved, updates)
    log_path = store.write_log(resolved, _log_payload(action_text(outbox_dir), pressure_pack, raw_output, flavor_report, audit_result, updates, outbox_dir, story_progress_before, story_progress_after, capability_plan))
    mirror_to_global_outbox(outbox_dir)
    print(f"updated files: {', '.join(touched) if touched else '(none)'}")
    print(f"log: {log_path}")
    print("\n" + public_output(parsed))
    return 0


def verify_browser_evidence_before_ingest(raw_path: Path, campaign_id: str) -> None:
    evidence_path = browser_evidence_path(raw_path)
    if not evidence_path.exists():
        raise RuntimeError(f"browser evidence missing; refusing ingest: {evidence_path}")
    evidence = read_json(evidence_path)
    if not isinstance(evidence, dict):
        raise RuntimeError(f"browser evidence invalid; refusing ingest: {evidence_path}")
    evidence_campaign_id = str(evidence.get("campaign_id") or "")
    if evidence_campaign_id != str(campaign_id):
        raise RuntimeError("browser evidence campaign_id mismatch; refusing ingest")
    mode = str(evidence.get("mode") or "")
    if mode not in {"text", "capture_only"}:
        raise RuntimeError(f"browser evidence mode is not ingest-safe: {mode or '(empty)'}")
    if evidence.get("ok") is not True:
        reason = str(evidence.get("blocked_reason") or evidence.get("error") or "browser evidence blocked ingest")
        raise RuntimeError(f"browser evidence blocked ingest: {reason}")
    if evidence.get("markers_ok") is not True:
        raise RuntimeError("browser evidence markers_ok is false; refusing ingest")
    output_hash = str(evidence.get("output_hash") or "")
    if not output_hash:
        raise RuntimeError("browser evidence output_hash missing; refusing ingest")
    actual_hash = sha256_file(raw_path)
    if output_hash != actual_hash:
        raise RuntimeError("browser evidence output_hash mismatch; refusing ingest")


def append_run_record(run_records: dict, campaign_id: str, player_action: str, parsed, outbox_dir: Path, pressure_pack: dict, audit_result: dict, final_updates: dict) -> dict:
    data = dict(run_records or {})
    data.setdefault("campaign_id", campaign_id)
    data.setdefault("scope", "run_records")
    records = list(data.get("records") or [])
    turn_index = len(records) + 1
    actors = []
    for block in getattr(parsed, "blocks", []) or []:
        if isinstance(block, dict):
            actor_id = block.get("actor_id") or block.get("speaker")
            actor_kind = block.get("actor_kind") or block.get("type")
            if actor_id:
                actors.append({"id": actor_id, "kind": actor_kind})
    records.append({
        "turn_index": turn_index,
        "campaign_id": campaign_id,
        "player_action": player_action,
        "summary": getattr(parsed, "summary", ""),
        "block_count": len(getattr(parsed, "blocks", []) or []),
        "actors": actors,
        "pressure_pack_turn_type": pressure_pack.get("turn_type", ""),
        "capabilities": read_json(outbox_dir / "capability_plan.json").get("loaded_capabilities", []) if (outbox_dir / "capability_plan.json").exists() else [],
        "output_request_modes": {key: value.get("mode", "") for key, value in (pressure_pack.get("output_requests", {}) if isinstance(pressure_pack.get("output_requests"), dict) else {}).items() if isinstance(value, dict)},
        "payload_fulfillment_used": bool(read_json(outbox_dir / "missing_capabilities.json").get("missing_capabilities", [])) if (outbox_dir / "missing_capabilities.json").exists() else False,
        "frontend_modules_changed": [],
        "story_progress_label": pressure_pack.get("progress_control", {}).get("progress_note", "") if isinstance(pressure_pack.get("progress_control"), dict) else "",
        "protocol_warning_count": len(pressure_pack.get("protocol_warnings", [])) if isinstance(pressure_pack.get("protocol_warnings"), list) else 0,
        "audit_decision": audit_result.get("decision", ""),
        "updated_files": sorted(final_updates.keys()),
        "source_paths": {
            "outbox_dir": str(outbox_dir),
            "pressure_pack": str(outbox_dir / "pressure_pack.json"),
            "chatgpt_input": str(outbox_dir / "chatgpt_input.md"),
            "chatgpt_raw_output": str(outbox_dir / "chatgpt_raw_output.md"),
            "chatgpt_blocks": str(outbox_dir / "chatgpt_blocks.json"),
            "state_writeback": str(outbox_dir / "state_writeback.json"),
            "audit_result": str(outbox_dir / "v4_audit_result.json"),
        },
    })
    data["records"] = records[-50:]
    data["last_updated_turn"] = turn_index
    data["source_files"] = [
        "outbox/pressure_pack.json",
        "outbox/chatgpt_input.md",
        "outbox/chatgpt_raw_output.md",
        "outbox/chatgpt_blocks.json",
        "outbox/state_writeback.json",
        "logs/*_turn.json",
    ]
    return data


def cmd_audit_writeback(campaign_id: str | None) -> int:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id)
    memory = store.load_campaign_memory(resolved)
    outbox_dir = campaign_outbox_dir(resolved)
    writeback_path = outbox_dir / "state_writeback.json"
    if not writeback_path.exists():
        raise FileNotFoundError(f"missing {outbox_dir / 'state_writeback.json'}")
    pressure_pack = normalize_pressure_pack_compat(read_json(outbox_dir / "pressure_pack.json")) if (outbox_dir / "pressure_pack.json").exists() else {}
    writeback = read_json(writeback_path)
    validate_writeback(writeback)
    capability_plan = read_capability_plan(outbox_dir, resolved, action_text(outbox_dir), memory)
    audit_result = extract_json_object(DeepSeekClient().complete_json(
        read_prompt("v4_audit_prompt.md"),
        build_audit_user_prompt(resolved, memory, pressure_pack, writeback, capability_plan),
    ))
    validate_audit_result(audit_result)
    write_json(outbox_dir / "v4_audit_result.json", audit_result)
    mirror_to_global_outbox(outbox_dir, ["pressure_pack.json", "state_writeback.json", "v4_audit_result.json"])
    print(f"director audit decision: {audit_result.get('decision')}")
    print(audit_result.get("reason", ""))
    return 0


def cmd_rewrite_plan() -> int:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(None)
    memory = store.load_campaign_memory(resolved)
    raw_path = OUTBOX_DIR / "chatgpt_raw_output.md"
    if not raw_path.exists():
        raise FileNotFoundError("missing outbox/chatgpt_raw_output.md")
    raw_output = read_runtime_text(raw_path)
    flavor_report = check_ai_flavor(raw_output, memory.get("forbidden_changes.json"))
    write_json(OUTBOX_DIR / "ai_flavor_report.json", flavor_report)
    correction = maybe_v4_rewrite_correction(raw_output, flavor_report, memory)
    write_text_utf8(
        OUTBOX_DIR / "chatgpt_rewrite_input.md",
        build_chatgpt_rewrite_input(raw_output, flavor_report, correction),
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



def prepare_turn(action: str, campaign_id: str | None, offline_pressure_pack: bool) -> int:
    return cmd_prepare(action, campaign_id, offline_pressure_pack)


def send_actor_turn(campaign_id: str | None) -> int:
    return cmd_send(campaign_id)


def ingest_actor_turn(campaign_id: str | None, skip_v4_audit: bool) -> int:
    return cmd_ingest(campaign_id, skip_v4_audit)


def run_rewrite_if_needed(campaign_id: str | None, auto_rewrite: bool, rewrite_attempts: int) -> int:
    _ = campaign_id
    if not auto_rewrite:
        return 0
    return cmd_run_rewrite(rewrite_attempts)


def run_image_if_needed(campaign_id: str | None) -> int:
    resolved = MemoryStore().resolve_campaign_id(campaign_id)
    outbox_dir = campaign_outbox_dir(resolved)
    pressure_pack = read_json(outbox_dir / "pressure_pack.json") if (outbox_dir / "pressure_pack.json").exists() else {}
    write_json(outbox_dir / "image_job.json", {
        "status": "skipped",
        "reason": "lazy pipeline defers image generation to canvas_jobs or explicit asset APIs",
        "visual_asset_count": len(image_pass_assets(pressure_pack)),
    })
    return 0


def run_turn_pipeline(
    action: str,
    campaign_id: str | None,
    offline_pressure_pack: bool,
    skip_v4_audit: bool,
    auto_rewrite: bool,
    rewrite_attempts: int,
) -> int:
    if is_light_director_action(action):
        return cmd_v4_light_action(action, campaign_id, skip_v4_audit=True)
    if auto_rewrite:
        print("auto rewrite disabled in lazy payload pipeline to preserve model call limits")
        auto_rewrite = False

    result = prepare_turn(action, campaign_id, offline_pressure_pack)
    if result != 0:
        return result
    if prepared_scene_action_warning(campaign_id):
        return 0
    result = send_actor_turn(campaign_id)
    if result != 0:
        return result
    result = ingest_actor_turn(campaign_id, skip_v4_audit)
    if result != 0:
        return result
    result = run_rewrite_if_needed(campaign_id, auto_rewrite, rewrite_attempts)
    if result != 0:
        return result
    return run_image_if_needed(campaign_id)


def prepared_scene_action_warning(campaign_id: str | None) -> bool:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id)
    outbox_dir = campaign_outbox_dir(resolved)
    pressure_path = outbox_dir / "pressure_pack.json"
    if not pressure_path.exists():
        return False
    return bool(scene_action_warning_from_pressure_pack(read_json(pressure_path)))


def write_scene_action_warning_turn(
    resolved: str,
    action: str,
    memory: dict,
    outbox_dir: Path,
    pressure_pack: dict,
    capability_plan: dict,
) -> bool:
    warning = scene_action_warning_from_pressure_pack(pressure_pack)
    if not warning:
        return False
    store = MemoryStore()
    writeback = {"short_term_state": {}, "long_term_memory": {}, "new_open_threads": [], "closed_threads": []}
    blocks = [
        {
            "type": "player_action",
            "actor_kind": "player",
            "speaker": "玩家",
            "actor_id": "player",
            "avatar_key": "player",
            "body": action,
        },
        {
            "type": "system_check",
            "actor_kind": "system",
            "speaker": "系统提示",
            "actor_id": "system",
            "avatar_key": "system",
            "body": warning["message"],
            "severity": warning["severity"],
            "warning_code": warning["code"],
            "route": warning["route"],
        },
    ]
    validate_chatgpt_blocks(blocks)
    validate_writeback(writeback)
    raw_output = json.dumps({
        "turn_title": "行动无法执行",
        "blocks": blocks,
        "summary": warning["message"],
        "state_writeback": writeback,
    }, ensure_ascii=False)

    write_json(outbox_dir / "pressure_pack.json", pressure_pack)
    write_json(outbox_dir / "pressure_pack_core.json", pressure_pack)
    write_json(outbox_dir / "pressure_pack_normalized.json", pressure_pack)
    write_json(outbox_dir / "missing_capabilities.json", {"missing_capabilities": [], "warnings": [warning["message"]]})
    write_json(outbox_dir / "payload_patch.json", skipped_payload_patch("scene action unavailable"))
    write_text_utf8(outbox_dir / "payload_fulfillment_input.md", "")
    write_text_utf8(outbox_dir / "chatgpt_input.md", "Scene action warning; actor layer skipped.\n")
    write_text_utf8(outbox_dir / "chatgpt_raw_output.md", raw_output)
    write_text_utf8(outbox_dir / "chatgpt_clean_output.md", f"【系统提示】\n{warning['message']}\n")
    write_json(outbox_dir / "chatgpt_blocks.json", {
        "blocks": blocks,
        "body": warning["message"],
        "choices": "",
        "summary": warning["message"],
    })
    write_json(outbox_dir / "state_writeback.json", writeback)
    audit_result = {
        "decision": "accept",
        "reason": "scene action unavailable warning; no memory write",
        "approved_writeback": writeback,
        "memory_files_to_update": [],
        "warnings": [warning["message"]],
    }
    write_json(outbox_dir / "v4_audit_result.json", audit_result)
    write_json(outbox_dir / "ai_flavor_report.json", {"severity": "pass", "issues": []})
    store.write_log(
        resolved,
        _log_payload(action, pressure_pack, raw_output, {"severity": "pass", "issues": []}, audit_result, {}, outbox_dir, capability_plan=capability_plan),
    )
    mirror_to_global_outbox(outbox_dir, [
        "last_player_action.txt",
        "capability_plan.json",
        "pressure_pack_core.json",
        "missing_capabilities.json",
        "payload_fulfillment_input.md",
        "payload_patch.json",
        "pressure_pack.json",
        "pressure_pack_normalized.json",
        "selected_director_memory.json",
        "selected_actor_memory.json",
        "selected_prompt_modules.json",
        "chatgpt_input.md",
        "chatgpt_raw_output.md",
        "chatgpt_clean_output.md",
        "chatgpt_blocks.json",
        "state_writeback.json",
        "v4_audit_result.json",
        "ai_flavor_report.json",
    ])
    emit_public_job_status("warning", warning["message"], 100)
    print(warning["message"])
    return True


def cmd_run_turn(action: str, campaign_id: str | None, offline_pressure_pack: bool, skip_v4_audit: bool, auto_rewrite: bool, rewrite_attempts: int) -> int:
    return run_turn_pipeline(
        action,
        campaign_id,
        offline_pressure_pack,
        skip_v4_audit,
        auto_rewrite,
        rewrite_attempts,
    )



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
        memory = store.load_campaign_memory(campaign_id)
        blueprint = memory.get("story_blueprint.json", {})
        if isinstance(blueprint, dict) and blueprint.get("chapters"):
            validate_story_blueprint(blueprint)
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


def cmd_validate_encoding() -> int:
    result = validate_repository_encoding(PROJECT_ROOT)
    issues = result["issues"]
    print(f"checked files: {result['checked_files']}")
    print(f"issues: {len(issues)}")
    for issue in issues:
        print(f"- {issue['path']} [{issue['type']}] {issue['detail']}")
    return 0 if result["ok"] else 1


IMAGE_ACTION_RE = re.compile(r"执行生图|生图|生成图片|画图|出图|重绘|redraw|image\s*generation", re.I)


def explicit_image_action(action: str) -> bool:
    return bool(IMAGE_ACTION_RE.search(str(action or "")))


def image_pass_assets(pressure_pack: dict) -> list[dict]:
    payloads = pressure_pack.get("payloads") if isinstance(pressure_pack, dict) else {}
    assets = payloads.get("visual_assets") if isinstance(payloads, dict) and payloads.get("visual_assets") else pressure_pack.get("visual_assets") if isinstance(pressure_pack, dict) else []
    rows = []
    for asset in assets if isinstance(assets, list) else []:
        if not isinstance(asset, dict):
            continue
        if asset.get("positive_prompt") or asset.get("image_prompt") or asset.get("trigger_image_generation") is True:
            rows.append(asset)
    return rows


def image_pass_requested(action: str, pressure_pack: dict) -> bool:
    return explicit_image_action(action) or bool(image_pass_assets(pressure_pack))


def action_text(outbox_dir: Path | None = None) -> str:
    path = (outbox_dir or OUTBOX_DIR) / "last_player_action.txt"
    return read_runtime_text(path) if path.exists() else ""


def read_capability_plan(outbox_dir: Path, campaign_id: str, player_action: str, memory: dict) -> dict:
    path = outbox_dir / "capability_plan.json"
    if path.exists():
        data = read_json(path)
        if isinstance(data, dict):
            return data
    return build_capability_plan(campaign_id, player_action, memory)


def _log_payload(
    player_action: str,
    pressure_pack: dict,
    raw_output: str,
    flavor_report: dict,
    audit_result: dict,
    final_updates: dict,
    outbox_dir: Path | None = None,
    story_progress_before: dict | None = None,
    story_progress_after: dict | None = None,
    capability_plan: dict | None = None,
) -> dict:
    source_outbox = outbox_dir or OUTBOX_DIR
    chatgpt_input_path = source_outbox / "chatgpt_input.md"
    payload_summary = summarize_payload_keys(pressure_pack)
    missing_path = source_outbox / "missing_capabilities.json"
    patch_path = source_outbox / "payload_patch.json"
    missing_capabilities = read_json(missing_path) if missing_path.exists() else {}
    payload_patch = read_json(patch_path) if patch_path.exists() else {}
    optional_writebacks = {}
    approved = audit_result.get("approved_writeback") if isinstance(audit_result, dict) else {}
    if isinstance(approved, dict):
        optional_writebacks = approved.get("optional_writebacks") if isinstance(approved.get("optional_writebacks"), dict) else {}
    return {
        "user_input": player_action,
        "capability_plan": capability_plan or {},
        "loaded_capabilities": capability_plan.get("loaded_capabilities", []) if isinstance(capability_plan, dict) else [],
        "selected_prompt_modules": capability_plan.get("prompt_modules", {}) if isinstance(capability_plan, dict) else {},
        "selected_memory_file_keys": capability_plan.get("memory_refs", {}) if isinstance(capability_plan, dict) else {},
        "v4_pressure_pack": pressure_pack,
        "output_requests": pressure_pack.get("output_requests", {}),
        "payload_keys": payload_summary,
        "missing_capabilities": missing_capabilities,
        "payload_fulfillment_used": bool(missing_capabilities.get("missing_capabilities")) and not payload_patch.get("skipped", False),
        "payload_fulfillment_warnings": payload_patch.get("warnings", []) if isinstance(payload_patch, dict) else [],
        "optional_writebacks_keys": sorted(optional_writebacks.keys()),
        "capability_escalation_request": approved.get("capability_escalation_request", {}) if isinstance(approved, dict) else {},
        "outbox_dir": str(source_outbox),
        "chatgpt_input": read_runtime_text(chatgpt_input_path) if chatgpt_input_path.exists() else "",
        "chatgpt_raw_output": raw_output,
        "ai_flavor_report": flavor_report,
        "v4_audit_result": audit_result,
        "final_write": final_updates,
        "story_progress_before": story_progress_before or {},
        "story_progress_after": story_progress_after or final_updates.get("story_progress.json", {}),
        "protocol_warnings": (story_progress_after or final_updates.get("story_progress.json", {})).get("protocol_warnings", []) if isinstance(story_progress_after or final_updates.get("story_progress.json", {}), dict) else [],
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
        "progress_control": _default_progress_control(),
        "output_requests": _default_output_requests("offline fallback", story_progress_reason="offline fallback"),
        "payloads": {},
        "visual_assets": [],
        "map_route": {"title": "", "nodes": [], "edges": [], "markers": []},
        "map_canvas": {"canvas": {}, "legend": {}, "ascii": [], "points": [], "routes": [], "hazards": []},
        "story_topology": {"nodes": [], "edges": [], "fixed_fields": {}},
        "human_readable_note": "offline development placeholder pressure pack; use director layer for formal play.",
    }


def _light_action_pressure_pack(campaign_id: str, action: str) -> dict:
    return {
        "campaign_id": campaign_id,
        "turn_type": "light_action",
        "creation_mode": {
            "label": "director-direct",
            "director_only": True,
            "actor_layer_skipped": True,
            "reason": "fixed lightweight operation",
        },
        "current_situation": {
            "player_action": action,
            "mode": "fixed_light_action",
            "immediate_context": "Return concise operational information without actor-layer expansion.",
        },
        "pressure_pack": {
            "core_accident_or_change": "",
            "human_pressure": "",
            "environment_pressure": "",
            "enemy_or_mystery_pressure": "",
            "resource_or_time_pressure": "",
            "conflicting_interests": [],
        },
        "npc_direction": [],
        "scene_materials": [],
        "must_reveal_naturally": [],
        "must_not_explain_directly": [],
        "forbidden_this_turn": [],
        "player_pressure_point": "",
        "choice_requirement": {
            "need_choice": False,
            "choice_level": "none",
            "why": "light action should usually answer directly",
            "choice_style": "no_choice",
            "options": [],
        },
        "ending_target": "Answer the fixed light action briefly and update state only when a real change is confirmed.",
        "state_update_hints": [],
        "progress_control": _default_progress_control(),
        "output_requests": _default_output_requests("light action direct path", story_progress_reason="light action direct path"),
        "payloads": {},
        "visual_assets": [],
        "map_route": {"title": "", "nodes": [], "edges": [], "markers": []},
        "map_canvas": {"canvas": {}, "legend": {}, "ascii": [], "points": [], "routes": [], "hazards": []},
        "story_topology": {"nodes": [], "edges": [], "fixed_fields": {}},
        "human_readable_note": "Director light action direct path; actor layer skipped.",
    }


def normalize_light_writeback(writeback: dict) -> dict:
    data = dict(writeback or {})
    data.setdefault("short_term_state", {})
    data.setdefault("long_term_memory", {})
    data.setdefault("new_open_threads", [])
    data.setdefault("closed_threads", [])
    data.setdefault("next_turn_suggestions", "")
    data.setdefault("summary_for_recent_context", "")
    return data


def _default_progress_control() -> dict:
    return {
        "current_chapter_id": "",
        "current_phase_id": "",
        "current_node_id": "",
        "current_node_name": "",
        "node_goal": "",
        "beat_targets_this_turn": [],
        "pace_command": "normal",
        "legal_next_nodes": [],
        "must_not_repeat": [],
        "progress_note": "",
    }


def _default_output_requests(reason: str, story_progress_reason: str | None = None) -> dict:
    return {
        "story_progress": {"mode": "update", "trigger": "system_required", "reason": story_progress_reason or reason},
        "map": {"mode": "keep_previous", "trigger": "none", "reason": reason},
        "visual_assets": {"mode": "none", "trigger": "none", "reason": ""},
        "gallery": {"mode": "none", "trigger": "none", "reason": ""},
        "inventory": {"mode": "none", "trigger": "none", "reason": ""},
        "character_card": {"mode": "none", "trigger": "none", "reason": ""},
        "dossier": {"mode": "none", "trigger": "none", "reason": ""},
        "dice_or_check": {"mode": "none", "trigger": "none", "reason": ""},
        "canvas_jobs": {"mode": "none", "trigger": "none", "reason": ""},
    }


if __name__ == "__main__":
    raise SystemExit(main())
