# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..capability_resolver import build_capability_plan
from ..deepseek_client import DeepSeekClient
from ..encoding_utils import read_runtime_text
from ..json_utils import extract_json_object, read_json, write_json
from ..memory_store import MemoryStore
from ..output_parser import parse_chatgpt_output, visible_prose_chars
from ..prompt_builder import build_audit_user_prompt, read_prompt
from ..schema_validator import normalize_pressure_pack_compat, validate_audit_result, validate_writeback
from ..writeback import apply_approved_writeback, has_applied_writeback, writeback_hash


def _web_server():
    from .. import web_server

    return web_server


def _resolve_outbox_dir(campaign_id: str = "") -> Path:
    ws = _web_server()
    # TODO: move resolve_outbox_dir out of web_server.py once writeback service dependencies are fully split.
    return ws.resolve_outbox_dir(campaign_id)


def _require_outbox_campaign(outbox_dir: Path, campaign_id: str) -> None:
    ws = _web_server()
    return ws.require_outbox_campaign(outbox_dir, campaign_id)


def _read_web_capability_plan(outbox_dir: Path, campaign_id: str, memory: dict[str, Any]) -> dict[str, Any]:
    path = outbox_dir / "capability_plan.json"
    if path.exists():
        data = read_json(path)
        if isinstance(data, dict):
            return data
    action_path = outbox_dir / "last_player_action.txt"
    action = read_runtime_text(action_path) if action_path.exists() else ""
    return build_capability_plan(campaign_id, action, memory)


def _visual_contract_updates_from_pressure(memory: dict[str, Any], pressure_pack: dict[str, Any], campaign_id: str) -> dict[str, Any]:
    ws = _web_server()
    # TODO: move visual_contract_updates_from_pressure out of web_server.py once visual contract update flow is service-owned.
    return ws.visual_contract_updates_from_pressure(memory, pressure_pack, campaign_id)


def _status_payload() -> dict[str, Any]:
    ws = _web_server()
    # TODO: move status_payload construction out of web_server.py when service boundaries are cleaner.
    return ws.status_payload()


def _current_writeback(campaign_id: str = "") -> dict[str, Any]:
    outbox_dir = _resolve_outbox_dir(campaign_id)
    _require_outbox_campaign(outbox_dir, campaign_id)
    path = outbox_dir / "state_writeback.json"
    if path.exists():
        data = read_json(path)
        validate_writeback(data)
        return data
    raw_path = outbox_dir / "chatgpt_raw_output.md"
    if not raw_path.exists():
        raise FileNotFoundError("missing outbox/state_writeback.json or chatgpt_raw_output.md")
    parsed = parse_chatgpt_output(read_runtime_text(raw_path))
    validate_writeback(parsed.writeback)
    write_json(path, parsed.writeback)
    return parsed.writeback


def _current_visible_prose_chars(campaign_id: str = "") -> int:
    outbox_dir = _resolve_outbox_dir(campaign_id)
    blocks_path = outbox_dir / "chatgpt_blocks.json"
    if blocks_path.exists():
        data = read_json(blocks_path)
        blocks = data.get("blocks") if isinstance(data, dict) else []
        return visible_prose_chars(blocks)
    raw_path = outbox_dir / "chatgpt_raw_output.md"
    if raw_path.exists():
        parsed = parse_chatgpt_output(read_runtime_text(raw_path))
        return visible_prose_chars(parsed.blocks)
    return 0


def writeback_review_payload(campaign_id: str = "") -> dict[str, Any]:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id or None)
    memory = store.load_campaign_memory(resolved)
    writeback: dict[str, Any] = {}
    audit_result: dict[str, Any] = {}
    pending_updates: dict[str, Any] = {}
    warnings: list[str] = []
    outbox_dir = _resolve_outbox_dir(resolved)
    try:
        _require_outbox_campaign(outbox_dir, resolved)
        writeback = _current_writeback(resolved)
    except Exception as exc:
        warnings.append(str(exc))
    audit_path = outbox_dir / "v4_audit_result.json"
    if audit_path.exists():
        try:
            audit_result = read_json(audit_path)
            validate_audit_result(audit_result)
        except Exception as exc:
            warnings.append(f"invalid audit result: {exc}")
            audit_result = {}
    decision = audit_result.get("decision", "not_audited")
    approved = audit_result.get("approved_writeback") or writeback
    if decision in {"accept", "revise"} and approved:
        pressure_path = outbox_dir / "pressure_pack.json"
        pressure_pack = normalize_pressure_pack_compat(read_json(pressure_path)) if pressure_path.exists() else {}
        raw_digest = writeback_hash(writeback)
        approved_digest = writeback_hash(approved)
        for digest in (raw_digest, approved_digest):
            if digest and has_applied_writeback(memory, digest):
                warnings.append(f"duplicate writeback already applied: {digest[:12]}")
        pending_updates = apply_approved_writeback(
            memory,
            approved,
            extra_hashes=[raw_digest],
            pressure_pack=pressure_pack,
            prose_chars_delta=_current_visible_prose_chars(resolved),
        )
        pending_updates.update(_visual_contract_updates_from_pressure(memory, pressure_pack, resolved))
    return {
        "ok": True,
        "campaign_id": resolved,
        "writeback": writeback,
        "audit_result": audit_result,
        "decision": decision,
        "approved_writeback": approved if decision in {"accept", "revise"} else {},
        "memory_files_to_update": sorted(pending_updates.keys()),
        "pending_updates": pending_updates,
        "warnings": warnings + list(audit_result.get("warnings", [])),
    }


def audit_writeback_payload(campaign_id: str = "") -> dict[str, Any]:
    try:
        store = MemoryStore()
        resolved = store.resolve_campaign_id(campaign_id or None)
        memory = store.load_campaign_memory(resolved)
        outbox_dir = _resolve_outbox_dir(resolved)
        _require_outbox_campaign(outbox_dir, resolved)
        writeback = _current_writeback(resolved)
        pressure_path = outbox_dir / "pressure_pack.json"
        pressure_pack = read_json(pressure_path) if pressure_path.exists() else {}
        capability_plan = _read_web_capability_plan(outbox_dir, resolved, memory)
        audit_result = extract_json_object(
            DeepSeekClient().complete_json(
                read_prompt("v4_audit_prompt.md"),
                build_audit_user_prompt(resolved, memory, pressure_pack, writeback, capability_plan),
            )
        )
        validate_audit_result(audit_result)
        if audit_result.get("decision") in {"accept", "revise"}:
            validate_writeback(audit_result.get("approved_writeback") or writeback)
        write_json(outbox_dir / "v4_audit_result.json", audit_result)
        return writeback_review_payload(resolved)
    except Exception as exc:
        return {"ok": False, "campaign_id": campaign_id, "error": str(exc)}


def apply_writeback_payload(campaign_id: str = "") -> dict[str, Any]:
    store = MemoryStore()
    resolved = store.resolve_campaign_id(campaign_id or None)
    memory = store.load_campaign_memory(resolved)
    outbox_dir = _resolve_outbox_dir(resolved)
    _require_outbox_campaign(outbox_dir, resolved)
    writeback = _current_writeback(resolved)
    audit_path = outbox_dir / "v4_audit_result.json"
    if not audit_path.exists():
        raise RuntimeError("missing V4 audit result; run audit first")
    audit_result = read_json(audit_path)
    validate_audit_result(audit_result)
    decision = audit_result.get("decision")
    if decision == "reject":
        raise RuntimeError(f"V4 rejected writeback: {audit_result.get('reason', '')}")
    if decision not in {"accept", "revise"}:
        raise RuntimeError(f"invalid V4 audit decision: {decision}")
    approved = audit_result.get("approved_writeback") or writeback
    validate_writeback(approved)
    pressure_path = outbox_dir / "pressure_pack.json"
    pressure_pack = normalize_pressure_pack_compat(read_json(pressure_path)) if pressure_path.exists() else {}
    raw_digest = writeback_hash(writeback)
    approved_digest = writeback_hash(approved)
    for digest in (raw_digest, approved_digest):
        if has_applied_writeback(memory, digest):
            raise RuntimeError(f"duplicate writeback already applied: {digest[:12]}")
    updates = apply_approved_writeback(
        memory,
        approved,
        extra_hashes=[raw_digest],
        pressure_pack=pressure_pack,
        prose_chars_delta=_current_visible_prose_chars(resolved),
    )
    updates.update(_visual_contract_updates_from_pressure(memory, pressure_pack, resolved))
    touched = list(updates.keys())
    if touched:
        store.backup_files(resolved, touched)
        store.write_memory_updates(resolved, updates)
    raw_path = outbox_dir / "chatgpt_raw_output.md"
    flavor_path = outbox_dir / "ai_flavor_report.json"
    image_job_path = outbox_dir / "image_job.json"
    action_path = outbox_dir / "last_player_action.txt"
    store.write_log(
        resolved,
        {
            "player_action": read_runtime_text(action_path) if action_path.exists() else "",
            "v4_pressure_pack": pressure_pack,
            "chatgpt_raw_output": read_runtime_text(raw_path) if raw_path.exists() else "",
            "ai_flavor_report": read_json(flavor_path) if flavor_path.exists() else {},
            "v4_audit_result": audit_result,
            "final_write": updates,
        },
    )
    return {"ok": True, "campaign_id": resolved, "updated_files": touched, "status": _status_payload()}
