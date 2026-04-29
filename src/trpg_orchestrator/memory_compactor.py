# -*- coding: gbk -*-
from __future__ import annotations

from typing import Any


COMPACT_BUCKETS = [
    ("player_state.json", "growth_log"),
    ("world_state.json", "world_updates"),
    ("location_history.json", "location_updates"),
    ("quest_history.json", "quest_updates"),
    ("enemy_or_monster_ecology.json", "mystery_updates"),
    ("equipment_history.json", "equipment_updates"),
]


def build_compaction_report(memory: dict[str, Any], threshold: int = 12) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for filename, bucket in COMPACT_BUCKETS:
        data = memory.get(filename, {})
        items = data.get(bucket, [])
        if isinstance(items, list):
            files.append({
                "file": filename,
                "bucket": bucket,
                "count": len(items),
                "needs_compaction": len(items) > threshold,
                "suggested_keep_recent": min(6, len(items)),
                "suggested_archive_count": max(0, len(items) - 6),
            })
    npc_data = memory.get("npc_memory.json", {}).get("npcs", {})
    npc_rows = []
    if isinstance(npc_data, dict):
        for name, npc in npc_data.items():
            facts = npc.get("facts", []) if isinstance(npc, dict) else []
            npc_rows.append({
                "npc": name,
                "facts": len(facts),
                "needs_compaction": len(facts) > threshold,
            })
    threads = memory.get("main_threads.json", {})
    thread_report = {
        "main_threads": len(threads.get("main_threads", [])) if isinstance(threads.get("main_threads"), list) else 0,
        "side_threads": len(threads.get("side_threads", [])) if isinstance(threads.get("side_threads"), list) else 0,
        "closed_threads": len(threads.get("closed_threads", [])) if isinstance(threads.get("closed_threads"), list) else 0,
    }
    return {
        "threshold": threshold,
        "files": files,
        "npcs": npc_rows,
        "threads": thread_report,
        "needs_any_compaction": any(row["needs_compaction"] for row in files) or any(row["needs_compaction"] for row in npc_rows),
    }
