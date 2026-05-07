from __future__ import annotations

from copy import deepcopy
from typing import Any


NODE_STATUSES = {"locked", "available", "active", "resolved", "failed", "skipped", "merged"}
BEAT_UPDATE_STATUSES = {"touched", "resolved", "failed", "blocked"}
TRANSITION_TYPES = {"stay", "advance", "branch", "skip", "fail_forward", "merge"}


def find_chapter(blueprint: dict[str, Any], chapter_id: str) -> dict[str, Any] | None:
    for chapter in _chapters(blueprint):
        if str(chapter.get("chapter_id") or "") == str(chapter_id or ""):
            return chapter
    return None


def find_node(blueprint: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for chapter in _chapters(blueprint):
        for node in _nodes(chapter):
            if str(node.get("node_id") or "") == str(node_id or ""):
                return node
    return None


def find_current_node(blueprint: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any] | None:
    return find_node(blueprint, str(progress.get("current_node_id") or ""))


def validate_story_blueprint(blueprint: dict[str, Any]) -> None:
    if not isinstance(blueprint, dict):
        raise ValueError("story_blueprint must be an object")
    chapters = blueprint.get("chapters", [])
    if not isinstance(chapters, list):
        raise ValueError("story_blueprint.chapters must be a list")
    if not chapters:
        raise ValueError("story_blueprint requires at least one chapter with at least one node")
    chapter_ids: set[str] = set()
    node_ids: set[str] = set()
    beat_ids: set[str] = set()
    next_refs: list[tuple[str, str]] = []
    has_node = False
    for chapter in chapters:
        if not isinstance(chapter, dict):
            raise ValueError("chapter must be an object")
        chapter_id = str(chapter.get("chapter_id") or "").strip()
        _validate_weight(chapter, "chapter", chapter_id or "?")
        if chapter_id:
            if chapter_id in chapter_ids:
                raise ValueError(f"duplicate chapter_id: {chapter_id}")
            chapter_ids.add(chapter_id)
        if not isinstance(chapter.get("nodes", []), list):
            raise ValueError(f"chapter {chapter_id or '?'} nodes must be a list")
        for node in _nodes(chapter):
            has_node = True
            node_id = str(node.get("node_id") or "").strip()
            if not node_id:
                raise ValueError("node_id must be non-empty")
            if node_id in node_ids:
                raise ValueError(f"duplicate node_id: {node_id}")
            node_ids.add(node_id)
            _validate_weight(node, "node", node_id)
            for int_key in ("target_chars", "max_turns"):
                if int_key in node and node.get(int_key) not in (None, ""):
                    value = node.get(int_key)
                    if not isinstance(value, int) or value < 0:
                        raise ValueError(f"node {node_id} {int_key} must be a non-negative integer")
            next_nodes = node.get("next_nodes", [])
            if next_nodes in (None, ""):
                next_nodes = []
            if not isinstance(next_nodes, list):
                raise ValueError(f"node {node_id} next_nodes must be a list")
            for next_node_id in next_nodes:
                ref = str(next_node_id or "").strip()
                if ref:
                    next_refs.append((node_id, ref))
            if not isinstance(node.get("beat_checklist", []), list):
                raise ValueError(f"node {node_id} beat_checklist must be a list")
            for beat in _beats(node):
                beat_id = str(beat.get("beat_id") or "").strip()
                if not beat_id:
                    raise ValueError(f"node {node_id} has empty beat_id")
                if beat_id in beat_ids:
                    raise ValueError(f"duplicate beat_id: {beat_id}")
                beat_ids.add(beat_id)
                _validate_weight(beat, "beat", beat_id)
    if not has_node:
        raise ValueError("story_blueprint requires at least one chapter with at least one node")
    for node_id, ref in next_refs:
        if ref not in node_ids:
            raise ValueError(f"node {node_id} next_nodes references missing node_id: {ref}")


def build_backend_progress_control(
    blueprint: dict[str, Any],
    progress: dict[str, Any],
    pressure_pack_progress_control: dict[str, Any] | None = None,
) -> dict[str, Any]:
    warnings: list[str] = []
    incoming = pressure_pack_progress_control if isinstance(pressure_pack_progress_control, dict) else {}
    control: dict[str, Any] = {}
    if not _has_blueprint(blueprint):
        control.update({
            "current_chapter_id": "",
            "current_phase_id": "",
            "current_node_id": "",
            "current_node_name": "",
            "node_goal": "",
            "beat_targets_this_turn": [],
            "pace_command": "normal",
            "legal_next_nodes": [],
            "must_not_repeat": _string_list(incoming.get("must_not_repeat")),
            "progress_note": str(incoming.get("progress_note") or ""),
            "protocol_warnings": ["story_blueprint empty; progress_control disabled"],
        })
        return control
    try:
        validate_story_blueprint(blueprint)
    except ValueError as exc:
        warnings.append(f"invalid story_blueprint: {exc}")
    current_id = str(progress.get("current_node_id") or "").strip()
    node = find_node(blueprint, current_id) if current_id else None
    if not node:
        if current_id:
            warnings.append(f"story_progress current_node_id missing in blueprint: {current_id}")
        node = _first_node(blueprint)
        current_id = str(node.get("node_id") or "") if node else ""
    chapter_id = _chapter_id_for_node(blueprint, current_id)
    legal_next = [str(item) for item in (node.get("next_nodes", []) if isinstance(node, dict) else []) if str(item)]
    incoming_node = str(incoming.get("current_node_id") or "").strip()
    if incoming_node and incoming_node != current_id:
        warnings.append(f"director progress_control current_node_id ignored: {incoming_node}")
    incoming_legal = _string_list(incoming.get("legal_next_nodes"))
    illegal_legal = [item for item in incoming_legal if item not in legal_next]
    if illegal_legal:
        warnings.append("director progress_control legal_next_nodes filtered: " + ", ".join(illegal_legal))
    valid_beats = {str(beat.get("beat_id") or "") for beat in _beats(node or {})}
    beat_targets = []
    for beat_id in _string_list(incoming.get("beat_targets_this_turn")):
        if beat_id in valid_beats:
            beat_targets.append(beat_id)
        else:
            warnings.append(f"director progress_control beat target filtered: {beat_id}")
    if not beat_targets and valid_beats:
        beat_targets = [str(beat.get("beat_id") or "") for beat in _beats(node or {})[:1] if str(beat.get("beat_id") or "")]
    pace = _pace_command(node, progress) if node else "normal"
    requires_deep = bool((node or {}).get("requires_deep_instruction"))
    progress_note = str(incoming.get("progress_note") or "")
    if requires_deep:
        progress_note = "chapter_first_node_deep_instruction_required" if not progress_note else f"{progress_note}; chapter_first_node_deep_instruction_required"
    return {
        "current_chapter_id": chapter_id,
        "current_phase_id": str(progress.get("current_phase_id") or ""),
        "current_node_id": current_id,
        "current_node_name": _public_name(node, ""),
        "node_goal": str((node or {}).get("goal") or (node or {}).get("node_goal") or (node or {}).get("description") or ""),
        "beat_targets_this_turn": beat_targets,
        "pace_command": pace,
        "legal_next_nodes": legal_next,
        "must_not_repeat": _string_list(incoming.get("must_not_repeat")),
        "progress_note": progress_note,
        "requires_deep_instruction": requires_deep,
        "protocol_warnings": _dedupe_tail(warnings),
    }


def validate_progress_writeback_against_blueprint(
    blueprint: dict[str, Any],
    progress: dict[str, Any],
    progress_writeback: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if not _has_blueprint(blueprint):
        return warnings
    current_node = find_current_node(blueprint, progress)
    if not current_node:
        current_id = str(progress.get("current_node_id") or "")
        if current_id:
            warnings.append(f"current node not found in blueprint: {current_id}")
        return warnings
    valid_beats = {str(beat.get("beat_id")) for beat in _beats(current_node)}
    for update in progress_writeback.get("beat_updates", []) if isinstance(progress_writeback.get("beat_updates"), list) else []:
        beat_id = str(update.get("beat_id") or "")
        if beat_id and beat_id not in valid_beats:
            warnings.append(f"illegal beat_update ignored: {beat_id}")
    warnings.extend(_transition_warnings(current_node, progress, progress_writeback.get("transition_request") or {}, blueprint))
    return warnings


def apply_progress_writeback(
    blueprint: dict[str, Any],
    progress: dict[str, Any],
    progress_writeback: dict[str, Any],
    prose_chars_delta: int = 0,
) -> dict[str, Any]:
    updated = _default_progress(progress)
    warnings = list(updated.get("protocol_warnings") or [])
    updated["turns_in_node"] = int(updated.get("turns_in_node") or 0) + 1
    updated["chars_in_node"] = int(updated.get("chars_in_node") or 0) + max(0, int(prose_chars_delta or 0))
    updated["total_chars"] = int(updated.get("total_chars") or 0) + max(0, int(prose_chars_delta or 0))

    if not _has_blueprint(blueprint):
        warnings.append("story_blueprint empty; structured story progress disabled")
        updated["calculated_progress"] = {"overall": 0, "chapter": 0, "node": 0, "updated_by": "backend"}
        updated["pace_command"] = "normal"
        updated["protocol_warnings"] = _dedupe_tail(warnings)
        return updated

    try:
        validate_story_blueprint(blueprint)
    except ValueError as exc:
        warnings.append(f"invalid story_blueprint: {exc}")
        updated["calculated_progress"] = {"overall": 0, "chapter": 0, "node": 0, "updated_by": "backend"}
        updated["protocol_warnings"] = _dedupe_tail(warnings)
        return updated

    if not updated.get("current_node_id"):
        seed_node = _first_node(blueprint)
        if seed_node:
            updated["current_node_id"] = seed_node.get("node_id", "")
            updated["current_chapter_id"] = _chapter_id_for_node(blueprint, updated["current_node_id"])

    current_node = find_current_node(blueprint, updated)
    if not current_node:
        warnings.append(f"current node not found in blueprint: {updated.get('current_node_id', '')}")
        updated["calculated_progress"] = _calculated(blueprint, updated)
        updated["protocol_warnings"] = _dedupe_tail(warnings)
        return updated

    incoming_node_id = str(progress_writeback.get("current_node_id") or "").strip()
    if incoming_node_id and incoming_node_id != updated.get("current_node_id"):
        warnings.append(f"progress_writeback current_node_id ignored: {incoming_node_id}")

    beat_status = deepcopy(updated.get("beat_status") if isinstance(updated.get("beat_status"), dict) else {})
    valid_beats = {str(beat.get("beat_id")) for beat in _beats(current_node)}
    for beat_update in progress_writeback.get("beat_updates", []) if isinstance(progress_writeback.get("beat_updates"), list) else []:
        beat_id = str(beat_update.get("beat_id") or "").strip()
        status = str(beat_update.get("status") or "").strip()
        evidence = str(beat_update.get("evidence") or "").strip()
        if beat_id not in valid_beats:
            warnings.append(f"illegal beat_update ignored: {beat_id}")
            continue
        if status not in BEAT_UPDATE_STATUSES:
            warnings.append(f"illegal beat status ignored: {beat_id}:{status}")
            continue
        beat_status[beat_id] = {"status": status, "evidence": evidence}
    updated["beat_status"] = beat_status

    pre_transition_pace = _pace_command(current_node, updated)
    transition = progress_writeback.get("transition_request") if isinstance(progress_writeback.get("transition_request"), dict) else {}
    transition_warnings = _transition_warnings(current_node, updated, transition, blueprint)
    warnings.extend(transition_warnings)
    node_status = str(progress_writeback.get("node_status") or "").strip()
    has_completion_evidence = _has_progress_evidence(progress_writeback)
    if node_status == "resolved" and not has_completion_evidence:
        warnings.append("resolved_without_evidence_kept_active")
        node_status = "active"
    if pre_transition_pace == "force_advance" and (not transition or transition.get("type") == "stay"):
        warnings.append("force_advance_without_transition")
    if not transition_warnings and has_completion_evidence and node_status in {"resolved", "skipped", "failed", "merged"}:
        _append_unique(updated.setdefault("completed_node_ids", []), updated.get("current_node_id", ""))
    if not transition_warnings and transition and transition.get("type") != "stay":
        to_node_id = str(transition.get("to_node_id") or "").strip()
        if to_node_id:
            updated["last_transition"] = {
                "type": transition.get("type", ""),
                "from_node_id": updated.get("current_node_id", ""),
                "to_node_id": to_node_id,
                "reason": transition.get("reason", ""),
            }
            updated["current_node_id"] = to_node_id
            updated["current_chapter_id"] = _chapter_id_for_node(blueprint, to_node_id)
            updated["turns_in_node"] = 0
            updated["chars_in_node"] = 0

    updated["pace_command"] = _pace_command(find_current_node(blueprint, updated), updated)
    updated["calculated_progress"] = _calculated(blueprint, updated)
    updated["protocol_warnings"] = _dedupe_tail(warnings)
    return updated


def calculate_node_progress(node: dict[str, Any] | None, beat_status: dict[str, Any]) -> int:
    if not node:
        return 0
    beats = _beats(node)
    if not beats:
        return 0
    weights = _normalized_weights(beats)
    total = 0.0
    for beat, weight in zip(beats, weights):
        status = beat_status.get(str(beat.get("beat_id") or ""), {})
        state = status.get("status") if isinstance(status, dict) else status
        total += weight * _beat_value(str(state or ""))
    return _pct(total)


def calculate_chapter_progress(blueprint: dict[str, Any], progress: dict[str, Any]) -> int:
    chapter = find_chapter(blueprint, str(progress.get("current_chapter_id") or ""))
    if not chapter:
        node = find_current_node(blueprint, progress)
        chapter = find_chapter(blueprint, _chapter_id_for_node(blueprint, str(node.get("node_id") if node else "")))
    if not chapter:
        return 0
    nodes = _nodes(chapter)
    if not nodes:
        return 0
    weights = _normalized_weights(nodes, "weight")
    completed = set(progress.get("completed_node_ids") if isinstance(progress.get("completed_node_ids"), list) else [])
    total = 0.0
    current_id = str(progress.get("current_node_id") or "")
    for node, weight in zip(nodes, weights):
        node_id = str(node.get("node_id") or "")
        if node_id in completed:
            total += weight
        elif node_id == current_id:
            total += weight * (calculate_node_progress(node, progress.get("beat_status", {})) / 100)
    return _pct(total)


def calculate_overall_progress(blueprint: dict[str, Any], progress: dict[str, Any]) -> int:
    chapters = _chapters(blueprint)
    if not chapters:
        return 0
    weights = _normalized_weights(chapters, "weight")
    current_chapter_id = str(progress.get("current_chapter_id") or "")
    total = 0.0
    for chapter, weight in zip(chapters, weights):
        chapter_id = str(chapter.get("chapter_id") or "")
        chapter_progress = calculate_chapter_progress(blueprint, {**progress, "current_chapter_id": chapter_id})
        if chapter_id == current_chapter_id:
            total += weight * (chapter_progress / 100)
        elif _chapter_complete(chapter, progress):
            total += weight
    return _pct(total)


def build_frontend_story_progress(blueprint: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    if not _has_blueprint(blueprint):
        return {"enabled": False, "status_text": "未启用结构化故事进度"}
    node = find_current_node(blueprint, progress)
    chapter = find_chapter(blueprint, str(progress.get("current_chapter_id") or "")) or (
        find_chapter(blueprint, _chapter_id_for_node(blueprint, str(node.get("node_id") if node else ""))) if node else None
    )
    calculated = progress.get("calculated_progress") if isinstance(progress.get("calculated_progress"), dict) else {}
    node_progress = int(calculated.get("node") if calculated.get("node") is not None else calculate_node_progress(node, progress.get("beat_status", {})))
    chapter_progress = int(calculated.get("chapter") if calculated.get("chapter") is not None else calculate_chapter_progress(blueprint, progress))
    overall = int(calculated.get("overall") if calculated.get("overall") is not None else calculate_overall_progress(blueprint, progress))
    total_node_count = sum(len(_nodes(chapter_item)) for chapter_item in _chapters(blueprint))
    completed_node_ids = progress.get("completed_node_ids") if isinstance(progress.get("completed_node_ids"), list) else []
    current_chapter_name = _public_name(chapter, "当前章节")
    current_node_name = _public_name(node, "当前节点")
    chapter_nodes = _nodes(chapter) if chapter else []
    beat_status = progress.get("beat_status", {}) if isinstance(progress.get("beat_status"), dict) else {}
    node_beats = _frontend_beat_checklist(node, beat_status)
    next_nodes = _frontend_next_nodes(blueprint, node)
    return {
        "enabled": True,
        "story_length": blueprint.get("story_length", "medium"),
        "current_chapter": {
            "id": str(chapter.get("chapter_id") if chapter else ""),
            "name": current_chapter_name,
            "summary": str((chapter or {}).get("summary") or (chapter or {}).get("goal") or (chapter or {}).get("description") or ""),
            "progress": chapter_progress,
            "node_count": len(chapter_nodes),
            "completed_node_count": len([
                node_id for node_id in completed_node_ids
                if any(str(item.get("node_id") or "") == str(node_id) for item in chapter_nodes)
            ]),
        },
        "current_node": {
            "id": str(node.get("node_id") if node else ""),
            "name": current_node_name,
            "goal": str((node or {}).get("goal") or (node or {}).get("summary") or (node or {}).get("description") or ""),
            "target_chars": _safe_int((node or {}).get("target_chars")),
            "turns_in_node": _safe_int(progress.get("turns_in_node")),
            "chars_in_node": _safe_int(progress.get("chars_in_node")),
            "beat_checklist": node_beats,
            "next_nodes": next_nodes,
            "progress": node_progress,
        },
        "overall_progress": overall,
        "chapter_progress": chapter_progress,
        "node_progress": node_progress,
        "node_count": len(chapter_nodes),
        "beat_checklist": node_beats,
        "next_nodes": next_nodes,
        "pace_command": progress.get("pace_command", "normal"),
        "progress_label": f"{current_chapter_name} / {current_node_name}" if node or chapter else "",
        "status_text": _status_text(progress.get("pace_command", "normal")),
        "completed_node_count": len(completed_node_ids),
        "total_node_count": total_node_count,
    }


def _frontend_beat_checklist(node: dict[str, Any] | None, beat_status: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    raw_beats = node.get("beat_checklist") if isinstance(node, dict) else []
    if not isinstance(raw_beats, list):
        return rows
    for index, beat in enumerate(raw_beats, start=1):
        if isinstance(beat, dict):
            beat_id = str(beat.get("beat_id") or beat.get("id") or f"beat_{index}")
            text = str(beat.get("label") or beat.get("title") or beat.get("text") or beat.get("description") or beat_id)
        else:
            beat_id = f"beat_{index}"
            text = str(beat or "").strip()
        if not text:
            continue
        rows.append({
            "id": beat_id,
            "text": text,
            "status": str(beat_status.get(beat_id) or "pending"),
        })
    return rows


def _frontend_next_nodes(blueprint: dict[str, Any], node: dict[str, Any] | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    raw_next = node.get("next_nodes") if isinstance(node, dict) else []
    if not isinstance(raw_next, list):
        return rows
    for item in raw_next:
        node_id = str(item or "").strip()
        if not node_id:
            continue
        next_node = find_node(blueprint, node_id)
        rows.append({"id": node_id, "name": _public_name(next_node, node_id) if next_node else node_id})
    return rows


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _calculated(blueprint: dict[str, Any], progress: dict[str, Any]) -> dict[str, Any]:
    node = find_current_node(blueprint, progress)
    return {
        "overall": calculate_overall_progress(blueprint, progress),
        "chapter": calculate_chapter_progress(blueprint, progress),
        "node": calculate_node_progress(node, progress.get("beat_status", {})),
        "updated_by": "backend",
    }


def _transition_warnings(node: dict[str, Any], progress: dict[str, Any], transition: dict[str, Any], blueprint: dict[str, Any] | None = None) -> list[str]:
    if not transition:
        return []
    warnings: list[str] = []
    transition_type = str(transition.get("type") or "stay")
    if transition_type not in TRANSITION_TYPES:
        return [f"illegal transition type ignored: {transition_type}"]
    from_node_id = str(transition.get("from_node_id") or "")
    current_node_id = str(progress.get("current_node_id") or "")
    if from_node_id and from_node_id != current_node_id:
        warnings.append(f"illegal transition from_node_id ignored: {from_node_id}")
    if transition_type == "stay":
        return warnings
    to_node_id = str(transition.get("to_node_id") or "").strip()
    if not to_node_id:
        warnings.append("illegal transition missing to_node_id")
        return warnings
    legal_next = {str(item) for item in node.get("next_nodes", []) if str(item)}
    if to_node_id not in legal_next:
        warnings.append(f"illegal transition to_node_id ignored: {to_node_id}")
    if blueprint and not find_node(blueprint, to_node_id):
        warnings.append(f"illegal transition missing blueprint node ignored: {to_node_id}")
    return warnings


def _pace_command(node: dict[str, Any] | None, progress: dict[str, Any]) -> str:
    if not node:
        return "normal"
    turns = int(progress.get("turns_in_node") or 0)
    chars = int(progress.get("chars_in_node") or 0)
    max_turns = int(node.get("max_turns") or 0)
    target_chars = int(node.get("target_chars") or 0)
    force = (max_turns and turns > max_turns) or (target_chars and chars > target_chars)
    soon = (max_turns and turns >= max(1, max_turns - 1)) or (target_chars and chars >= int(target_chars * 0.85))
    if force:
        return "force_advance"
    if soon:
        return "advance_soon"
    return "normal"


def _default_progress(progress: dict[str, Any]) -> dict[str, Any]:
    data = deepcopy(progress if isinstance(progress, dict) else {})
    data.setdefault("current_chapter_id", "")
    data.setdefault("current_phase_id", "")
    data.setdefault("current_node_id", "")
    data.setdefault("turns_in_node", 0)
    data.setdefault("chars_in_node", 0)
    data.setdefault("total_chars", 0)
    data.setdefault("completed_node_ids", [])
    data.setdefault("beat_status", {})
    data.setdefault("pace_command", "normal")
    data.setdefault("last_transition", {})
    data.setdefault("protocol_warnings", [])
    data.setdefault("calculated_progress", {"overall": 0, "chapter": 0, "node": 0, "updated_by": "backend"})
    return data


def _chapters(blueprint: dict[str, Any]) -> list[dict[str, Any]]:
    chapters = blueprint.get("chapters", []) if isinstance(blueprint, dict) else []
    return [chapter for chapter in chapters if isinstance(chapter, dict)]


def _nodes(chapter: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = chapter.get("nodes", []) if isinstance(chapter, dict) else []
    return [node for node in nodes if isinstance(node, dict)]


def _beats(node: dict[str, Any]) -> list[dict[str, Any]]:
    beats = node.get("beat_checklist", []) if isinstance(node, dict) else []
    return [beat for beat in beats if isinstance(beat, dict)]


def _has_blueprint(blueprint: dict[str, Any]) -> bool:
    return isinstance(blueprint, dict) and any(_nodes(chapter) for chapter in _chapters(blueprint))


def _first_node(blueprint: dict[str, Any]) -> dict[str, Any] | None:
    for chapter in _chapters(blueprint):
        nodes = _nodes(chapter)
        if nodes:
            return nodes[0]
    return None


def _chapter_id_for_node(blueprint: dict[str, Any], node_id: str) -> str:
    for chapter in _chapters(blueprint):
        for node in _nodes(chapter):
            if str(node.get("node_id") or "") == str(node_id or ""):
                return str(chapter.get("chapter_id") or "")
    return ""


def _normalized_weights(items: list[dict[str, Any]], key: str = "weight") -> list[float]:
    if not items:
        return []
    raw = [float(item.get(key) or 0) for item in items]
    if sum(raw) <= 0:
        return [1 / len(items)] * len(items)
    total = sum(raw)
    return [value / total for value in raw]


def _validate_weight(item: dict[str, Any], label: str, item_id: str) -> None:
    if "weight" not in item or item.get("weight") in (None, ""):
        return
    value = item.get("weight")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} {item_id} weight must be a non-negative number")


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _has_progress_evidence(progress_writeback: dict[str, Any]) -> bool:
    evidence = progress_writeback.get("progress_evidence")
    if isinstance(evidence, list):
        for item in evidence:
            if isinstance(item, dict):
                if str(item.get("evidence") or item.get("text") or item.get("reason") or "").strip():
                    return True
            elif str(item or "").strip():
                return True
    transition = progress_writeback.get("transition_request")
    if isinstance(transition, dict) and str(transition.get("reason") or "").strip():
        return True
    for item in progress_writeback.get("beat_updates", []) if isinstance(progress_writeback.get("beat_updates"), list) else []:
        if isinstance(item, dict) and str(item.get("evidence") or "").strip():
            return True
    return False


def _beat_value(status: str) -> float:
    if status == "resolved":
        return 1.0
    if status == "touched":
        return 0.35
    if status == "blocked":
        return 0.15
    return 0.0


def _pct(value: float) -> int:
    return max(0, min(100, round(value * 100)))


def _chapter_complete(chapter: dict[str, Any], progress: dict[str, Any]) -> bool:
    completed = set(progress.get("completed_node_ids") if isinstance(progress.get("completed_node_ids"), list) else [])
    nodes = _nodes(chapter)
    return bool(nodes) and all(str(node.get("node_id") or "") in completed for node in nodes)


def _append_unique(items: list[Any], value: Any) -> None:
    if value and value not in items:
        items.append(value)


def _dedupe_tail(items: list[Any], limit: int = 50) -> list[Any]:
    result: list[Any] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result[-limit:]


def _public_name(item: dict[str, Any] | None, fallback: str) -> str:
    if not item:
        return ""
    return str(item.get("public_name") or item.get("name") or item.get("title") or fallback)


def _status_text(pace_command: str) -> str:
    if pace_command == "force_advance":
        return "当前节点已超出建议篇幅，需要尽快推进。"
    if pace_command == "advance_soon":
        return "当前节点接近推进点。"
    return "故事进度正常。"
