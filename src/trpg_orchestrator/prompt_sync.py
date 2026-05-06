from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

from .config import PROMPTS_DIR
from .encoding_utils import read_runtime_text, write_text_utf8
from .json_utils import read_json, write_json


SYNC_MANIFEST = PROMPTS_DIR / "prompt_language_sync.json"
STANDALONE_MD = {"rules_CN.md", "tasks_CN.md"}
EXCLUDED_DIRS = {"TEST"}


def prompt_sync_report(apply: bool = False) -> dict[str, Any]:
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest()
    old_pairs = manifest.get("pairs", {}) if isinstance(manifest.get("pairs"), dict) else {}
    issues: list[dict[str, str]] = []
    actions: list[dict[str, str]] = []
    pairs: dict[str, dict[str, Any]] = {}

    for english_path in sorted(_english_prompt_files()):
        chinese_path = english_path.with_name(f"{english_path.stem}_CN.md")
        pair_key = english_path.relative_to(PROMPTS_DIR).as_posix()
        if not chinese_path.exists():
            if apply:
                _create_counterpart(chinese_path, english_path, "zh")
                actions.append({"type": "created_counterpart", "path": chinese_path.relative_to(PROMPTS_DIR).as_posix()})
            else:
                issues.append({"path": pair_key, "type": "missing_cn", "detail": chinese_path.relative_to(PROMPTS_DIR).as_posix()})
                continue
        pairs[pair_key] = _pair_state(english_path, chinese_path, old_pairs.get(pair_key, {}))

    for chinese_path in sorted(PROMPTS_DIR.rglob("*_CN.md")):
        if _is_excluded(chinese_path):
            continue
        if chinese_path.name in STANDALONE_MD:
            continue
        english_path = chinese_path.with_name(chinese_path.name.removesuffix("_CN.md") + ".md")
        if english_path.exists():
            continue
        pair_key = english_path.relative_to(PROMPTS_DIR).as_posix()
        if apply:
            _create_counterpart(english_path, chinese_path, "en")
            actions.append({"type": "created_counterpart", "path": pair_key})
            pairs[pair_key] = _pair_state(english_path, chinese_path, old_pairs.get(pair_key, {}))
        else:
            issues.append({"path": chinese_path.relative_to(PROMPTS_DIR).as_posix(), "type": "missing_en", "detail": pair_key})

    for pair_key, state in pairs.items():
        changed_en = state.get("changed_en") is True
        changed_cn = state.get("changed_cn") is True
        has_baseline = state.get("has_baseline") is True
        if has_baseline and changed_en != changed_cn:
            issues.append({
                "path": pair_key,
                "type": "single_side_prompt_change",
                "detail": "English and Chinese prompt packages must be updated together.",
            })

    ok = not issues
    if apply:
        manifest = {
            "schema": "trpg_orchestrator.prompt_language_sync.v1",
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "policy": "Manual bilingual sync baseline. --check fails when only one side changes after this baseline.",
            "standalone_md": sorted(STANDALONE_MD),
            "pairs": {
                key: {
                    "english": value["english"],
                    "chinese": value["chinese"],
                    "english_sha256": value["english_sha256"],
                    "chinese_sha256": value["chinese_sha256"],
                    "last_sync_direction": value.get("last_sync_direction", "baseline"),
                }
                for key, value in sorted(pairs.items())
            },
        }
        write_json(SYNC_MANIFEST, manifest)
        actions.append({"type": "updated_manifest", "path": SYNC_MANIFEST.name})
        ok = not [issue for issue in issues if issue.get("type") != "single_side_prompt_change"]

    return {
        "ok": ok,
        "apply": apply,
        "pair_count": len(pairs),
        "issue_count": len(issues),
        "issues": issues,
        "actions": actions,
    }


def _english_prompt_files() -> list[Path]:
    return [
        path for path in PROMPTS_DIR.rglob("*.md")
        if path.name not in STANDALONE_MD and not path.name.endswith("_CN.md") and not _is_excluded(path)
    ]


def _is_excluded(path: Path) -> bool:
    try:
        relative = path.relative_to(PROMPTS_DIR)
    except ValueError:
        return False
    return bool(relative.parts and relative.parts[0] in EXCLUDED_DIRS)


def _load_manifest() -> dict[str, Any]:
    if not SYNC_MANIFEST.exists():
        return {}
    try:
        data = read_json(SYNC_MANIFEST)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _pair_state(english_path: Path, chinese_path: Path, baseline: dict[str, Any]) -> dict[str, Any]:
    english_hash = _sha256_text(read_runtime_text(english_path))
    chinese_hash = _sha256_text(read_runtime_text(chinese_path))
    old_en = str(baseline.get("english_sha256") or "")
    old_cn = str(baseline.get("chinese_sha256") or "")
    has_baseline = bool(old_en and old_cn)
    return {
        "english": english_path.relative_to(PROMPTS_DIR).as_posix(),
        "chinese": chinese_path.relative_to(PROMPTS_DIR).as_posix(),
        "english_sha256": english_hash,
        "chinese_sha256": chinese_hash,
        "has_baseline": has_baseline,
        "changed_en": has_baseline and english_hash != old_en,
        "changed_cn": has_baseline and chinese_hash != old_cn,
        "last_sync_direction": "baseline",
    }


def _create_counterpart(target: Path, source: Path, language: str) -> None:
    source_text = read_runtime_text(source).strip()
    if language == "zh":
        title = f"# {source.stem} 中文同步占位"
        note = "此文件由 sync-prompts --apply 创建。请人工翻译并保持与英文包同步。"
    else:
        title = f"# {source.name.removesuffix('_CN.md')} English Sync Placeholder"
        note = "Created by sync-prompts --apply. Translate manually and keep it synchronized with the Chinese package."
    text = f"{title}\n\n{note}\n\n```text\n{source_text}\n```\n"
    write_text_utf8(target, text)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
