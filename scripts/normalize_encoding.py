from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from trpg_orchestrator.encoding_utils import looks_mojibake  # noqa: E402


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


def main() -> int:
    changed: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    for path in iter_candidate_files(PROJECT_ROOT):
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        raw = path.read_bytes()
        decoded = decode_text(raw)
        if decoded is None:
            failed.append(f"{rel}: unable to decode as utf-8-sig, utf-8, or gbk")
            continue
        text, encoding = decoded
        if looks_mojibake(text):
            skipped.append(f"{rel}: looks mojibake; needs manual repair")
            continue
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        if path.suffix.lower() == ".py":
            gbk_header = "# -*- coding: " + "gbk -*-"
            normalized = normalized.replace(gbk_header, "# -*- coding: utf-8 -*-", 1)
        new_raw = normalized.encode("utf-8")
        if raw != new_raw or encoding == "utf-8-sig":
            path.write_bytes(new_raw)
            changed.append(rel)

    print_section("changed", changed)
    print_section("skipped", skipped)
    print_section("failed", failed)
    return 1 if failed or skipped else 0


def iter_candidate_files(root: Path):
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


def decode_text(raw: bytes) -> tuple[str, str] | None:
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return None


def print_section(name: str, rows: list[str]) -> None:
    print(f"{name}: {len(rows)}")
    for row in rows:
        print(f"- {row}")


if __name__ == "__main__":
    raise SystemExit(main())
