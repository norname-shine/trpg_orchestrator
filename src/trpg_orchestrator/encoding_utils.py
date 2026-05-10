from __future__ import annotations

from pathlib import Path


MOJIBAKE_MARKERS = (
    "\ufffd",
    "\u951b",
    "\u9518",
    "\u6d93",
    "\u6d63",
    "\u9366",
    "\u95c4",
    "\u7efe",
    "\u9428",
    "\u7447",
    "\u8e47",
    "\u83bd",
    "\u00c3",
    "\u00c2",
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


def looks_replacement_question_marks(text: str) -> bool:
    sample = str(text or "").strip()
    if len(sample) < 6:
        return False
    visible = sum(1 for char in sample if not char.isspace())
    if not visible:
        return False
    question_marks = sample.count("?") + sample.count("\uff1f")
    cjk = sum(1 for char in sample if "\u4e00" <= char <= "\u9fff")
    return cjk == 0 and question_marks >= 4 and question_marks / visible >= 0.4


def read_text_auto(path: Path) -> str:
    candidates: list[str] = []
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            with path.open("r", encoding=encoding, newline=None) as file:
                text = file.read()
        except UnicodeDecodeError:
            continue
        if not looks_mojibake(text):
            return text
        candidates.append(text)

    try:
        with path.open("r", encoding="gbk", newline=None) as file:
            text = file.read()
        if not looks_mojibake(text):
            return text
        candidates.append(text)
    except UnicodeDecodeError:
        pass

    if candidates:
        return candidates[0]
    raise UnicodeError(f"unable to decode {path} as utf-8-sig, utf-8, or gbk")


def assert_not_mojibake(text: str, source: str | Path = "text") -> str:
    if looks_mojibake(text):
        raise UnicodeError(f"mojibake detected in {source}; stop parsing and fix file encoding before continuing")
    return text


def assert_valid_user_text(text: str, source: str | Path = "user input") -> str:
    assert_not_mojibake(text, source)
    if looks_replacement_question_marks(text):
        raise UnicodeError(f"corrupt user input detected in {source}; check UTF-8 request encoding before continuing")
    return text


def read_runtime_text(path: Path) -> str:
    return assert_not_mojibake(read_text_auto(path), path)


def write_text_utf8(path: Path, text: str, newline: str = "\n") -> None:
    assert_not_mojibake(text, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline=newline) as file:
        file.write(text)
