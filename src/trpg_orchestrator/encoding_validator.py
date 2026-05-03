from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from .encoding_utils import looks_mojibake


SCAN_DIRS = (
    "src",
    "prompts",
    "web",
    "scripts",
    "campaigns/example_campaign",
)

SKIP_DIRS = {
    ".git",
    ".browser-profile",
    "node_modules",
    "outbox",
    "logs",
    "backups",
    "assets",
    "__pycache__",
}

BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".zip",
    ".sqlite",
    ".db",
    ".pyc",
    ".pyo",
    ".exe",
    ".dll",
    ".bin",
    ".ico",
    ".woff",
    ".woff2",
}

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".json",
    ".html",
    ".css",
    ".js",
    ".mjs",
    ".txt",
    ".bat",
    ".ps1",
    ".toml",
    ".yaml",
    ".yml",
}

COMMON_MOJIBAKE_MARKERS = tuple(
    chr(code)
    for code in (
        0x951B,
        0x9366,
        0x6D93,
        0x9428,
        0x00C3,
        0x00C2,
    )
)

FORBIDDEN_REPLACE_TOKENS = (
    "errors=" + '"replace"',
    "errors=" + "'replace'",
)


def validate_repository_encoding(root: Path) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    checked_files = 0
    root = root.resolve()

    for path in _iter_candidate_files(root):
        checked_files += 1
        rel = _rel(path, root)
        text, read_error = _decode_text(path)
        if read_error:
            issues.append({"path": rel, "type": "mojibake", "detail": read_error})
            continue

        assert text is not None
        if looks_mojibake(text):
            issues.append({"path": rel, "type": "mojibake", "detail": "looks_mojibake() returned true"})
        if "\ufffd" in text:
            issues.append({"path": rel, "type": "mojibake", "detail": "contains replacement character"})
        marker_hits = [marker for marker in COMMON_MOJIBAKE_MARKERS if marker in text]
        if marker_hits:
            issues.append({
                "path": rel,
                "type": "mojibake",
                "detail": "contains common mojibake marker(s): " + ", ".join(marker_hits),
            })

        for token in FORBIDDEN_REPLACE_TOKENS:
            if token in text:
                issues.append({"path": rel, "type": "forbidden_replace", "detail": token})

        if path.suffix.lower() == ".py":
            _validate_python_file(path, rel, text, issues)

        if path.suffix.lower() == ".json":
            try:
                json.loads(text)
            except json.JSONDecodeError as exc:
                issues.append({"path": rel, "type": "json_error", "detail": str(exc)})

    return {
        "ok": not issues,
        "checked_files": checked_files,
        "issues": issues,
    }


def _iter_candidate_files(root: Path):
    for scan_dir in SCAN_DIRS:
        base = root / scan_dir
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            parts = set(path.relative_to(root).parts)
            if parts & SKIP_DIRS:
                continue
            suffix = path.suffix.lower()
            if suffix in BINARY_SUFFIXES:
                continue
            if suffix and suffix not in TEXT_SUFFIXES:
                continue
            yield path


def _decode_text(path: Path) -> tuple[str | None, str | None]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(encoding), None
        except UnicodeDecodeError:
            continue
    return None, "unable to decode as utf-8-sig, utf-8, or gbk"


def _validate_python_file(path: Path, rel: str, text: str, issues: list[dict[str, str]]) -> None:
    gbk_header = "# -*- coding: " + "gbk -*-"
    if gbk_header in text:
        issues.append({"path": rel, "type": "gbk_header", "detail": "gbk coding header"})

    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        issues.append({"path": rel, "type": "json_error", "detail": f"python syntax error: {exc}"})
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _is_builtin_open(node.func):
            if not _has_keyword(node, "encoding"):
                issues.append({
                    "path": rel,
                    "type": "raw_open",
                    "detail": f"line {node.lineno}: open() without encoding",
                })
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "read_text":
                issues.append({
                    "path": rel,
                    "type": "raw_read_text",
                    "detail": f"line {node.lineno}: use read_text_auto() or read_runtime_text()",
                })
            if node.func.attr == "write_text":
                issues.append({
                    "path": rel,
                    "type": "raw_write_text",
                    "detail": f"line {node.lineno}: use write_text_utf8()",
                })


def _is_builtin_open(func: ast.expr) -> bool:
    return isinstance(func, ast.Name) and func.id == "open"


def _has_keyword(node: ast.Call, name: str) -> bool:
    return any(keyword.arg == name for keyword in node.keywords)


def _rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root).as_posix()
