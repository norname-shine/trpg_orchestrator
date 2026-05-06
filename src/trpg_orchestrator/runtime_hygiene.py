from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


ROOT_FILE_GLOBS = (
    ".tmp_*.json",
    "*.log",
)

ROOT_DIRS = (
    "outbox",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
)

RECURSIVE_DIR_NAMES = {
    "__pycache__",
}

BLOCKED_UPLOAD_PREFIXES = (
    ".browser-profile/",
    ".runtime/",
    "outbox/",
)

BLOCKED_UPLOAD_FILES = {
    ".env",
}


def pre_upload_clean(check_only: bool = False) -> dict[str, Any]:
    root = PROJECT_ROOT.resolve()
    planned = _collect_cleanup_targets(root)
    deleted: list[str] = []

    if not check_only:
        for target in planned:
            _remove_target(target)
            deleted.append(_rel(target, root))

    git_issues = _git_upload_issues(root)
    return {
        "ok": not git_issues,
        "mode": "check_only" if check_only else "clean",
        "planned": [_rel(path, root) for path in planned],
        "deleted": deleted,
        "git_issues": git_issues,
    }


def _collect_cleanup_targets(root: Path) -> list[Path]:
    targets: list[Path] = []
    for pattern in ROOT_FILE_GLOBS:
        targets.extend(path for path in root.glob(pattern) if path.is_file())
    for name in ROOT_DIRS:
        path = root / name
        if path.exists():
            targets.append(path)
    for path in root.rglob("*"):
        if path.is_dir() and path.name in RECURSIVE_DIR_NAMES:
            targets.append(path)
    return _dedupe_paths(targets)


def _remove_target(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _git_upload_issues(root: Path) -> list[str]:
    status = _git_status(root)
    issues: list[str] = []
    for path in status:
        normalized = path.replace("\\", "/")
        if normalized in BLOCKED_UPLOAD_FILES:
            issues.append(f"blocked private file in git status: {normalized}")
        if any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in BLOCKED_UPLOAD_PREFIXES):
            issues.append(f"blocked runtime path in git status: {normalized}")
        if normalized.startswith("campaigns/") and not _allowed_campaign_path(normalized):
            issues.append(f"blocked local campaign path in git status: {normalized}")
    return issues


def _git_status(root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "-z"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return []
    entries = result.stdout.decode("utf-8").split("\0")
    paths: list[str] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[3:]
        if status.strip().startswith("R") or status.strip().startswith("C"):
            if index < len(entries):
                paths.append(entries[index])
                index += 1
            else:
                paths.append(path)
        else:
            paths.append(path)
    return paths


def _allowed_campaign_path(path: str) -> bool:
    return path == "campaigns/campaign_registry.example.json" or path.startswith("campaigns/example_campaign/")


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    rows: list[Path] = []
    for path in sorted(paths, key=lambda item: len(item.parts)):
        resolved = path.resolve()
        if any(parent in seen for parent in resolved.parents):
            continue
        if resolved not in seen:
            seen.add(resolved)
            rows.append(resolved)
    return rows


def _rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root).as_posix()
