from __future__ import annotations

from pathlib import Path


MOJIBAKE_MARKERS = (
    "\ufffd",
    "锛",
    "锘",
    "涓",
    "浣",
    "鍦",
    "闄",
    "绾",
    "鐨",
    "瑙",
    "蹇",
    "莽",
    "Ã",
    "Â",
)


def looks_mojibake(text: str) -> bool:
    if "\ufffd" in text:
        return True
    marker_hits = sum(text.count(marker) for marker in MOJIBAKE_MARKERS if marker != "\ufffd")
    if marker_hits >= 3:
        return True
    sample = text[:4000]
    if not sample:
        return False
    suspicious = sum(sample.count(marker) for marker in MOJIBAKE_MARKERS if marker != "\ufffd")
    cjk = sum(1 for char in sample if "\u4e00" <= char <= "\u9fff")
    return cjk >= 20 and suspicious / max(cjk, 1) > 0.08


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


def assert_not_mojibake(text: str, source: str | Path = "text") -> str:
    if looks_mojibake(text):
        raise UnicodeError(f"mojibake detected in {source}; stop parsing and fix file encoding before continuing")
    return text


def read_runtime_text(path: Path) -> str:
    return assert_not_mojibake(read_text_auto(path), path)


def write_text_utf8(path: Path, text: str, newline: str = "\n") -> None:
    assert_not_mojibake(text, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline=newline)
