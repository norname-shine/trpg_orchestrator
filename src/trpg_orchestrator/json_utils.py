from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .encoding_utils import read_runtime_text, write_text_utf8


def read_json(path: Path) -> Any:
    return json.loads(read_runtime_text(path))


def write_json(path: Path, data: Any) -> None:
    write_text_utf8(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def extract_json_object(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return json.loads(stripped)
