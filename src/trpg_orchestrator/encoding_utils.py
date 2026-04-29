from __future__ import annotations

from pathlib import Path


MOJIBAKE_MARKERS = ("\ufffd", "\u951f", "\u9534", "\u956d", "\u95c2")


def looks_mojibake(text: str) -> bool:
    return any(marker in text for marker in MOJIBAKE_MARKERS)


def read_text_auto(path: Path) -> str:
    candidates: list[str] = []
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            text = path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        if not looks_mojibake(text):
            return text
        candidates.append(text)

    try:
        text = path.read_text(encoding="gbk")
        if not looks_mojibake(text):
            return text
        candidates.append(text)
    except UnicodeDecodeError:
        pass

    if candidates:
        return candidates[0]
    return path.read_text(encoding="utf-8", errors="replace")
