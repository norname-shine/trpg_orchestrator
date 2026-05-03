# Encoding Rules

This repository runs on Windows. Some historical Python files may be GBK, but frontend files, prompts, JSON, Markdown, outbox files, and campaign data must be managed as UTF-8. Encoding is a stability rule, not a style preference.

## Core Principles

- Player prose, ChatGPT input, ChatGPT replies, state writeback, JSON memory, and frontend text must never contain mojibake.
- Runtime data is always written as UTF-8.
- Legacy files may be read with automatic UTF-8 / UTF-8-BOM / GBK detection, but text must be checked for mojibake before parsing.
- Do not use replacement decoding to silently swallow corruption and continue parsing, writing, or displaying text.
- The forbidden replacement-decoding pattern is any direct `errors = "replace"` / `errors = 'replace'` equivalent in runtime decoding.
- If runtime text still looks like mojibake, raise an error and stop so the source file or encoding boundary can be fixed.

## Prompt Language Policy

- Runtime prompt and rule files consumed by models must be written in English.
- Chinese translations are stored in sibling files named `<base>_CN.md`.
- Model injection must use the English main file unless a user explicitly opens a Chinese translation for reading.
- When a rule changes, update both the English file and the `_CN.md` translation package.
- Do not leave Chinese system instructions in English main prompt files except user-facing examples that are explicitly marked as content examples.

## Reading And Writing

- Ordinary text reads should use `read_text_auto(path)`.
- Runtime-critical text reads must use `read_runtime_text(path)`.
- JSON reads must use `read_json(path)`.
- Do not add direct `Path.read_text` calls with replacement decoding.
- Newly generated prompts, JSON, Markdown, HTML, CSS, JS, and outbox text must be UTF-8.
- Ordinary text writes should use `write_text_utf8(path, text)`.
- JSON writes should use `write_json(path, data)` with `ensure_ascii=False`.
- Do not copy terminal mojibake back into files.

## Backend And Frontend

- ChatGPT raw output must pass through `read_runtime_text` before parsing.
- `parse_chatgpt_output` only accepts Unicode strings already confirmed to be non-mojibake.
- Backend JSON responses must use `ensure_ascii=False` and declare `charset=utf-8`.
- The web server must send HTML, CSS, JS, JSON, and Markdown as UTF-8.
- HTML pages must keep `<meta charset="utf-8">`.
- The frontend only displays decoded Unicode returned by the backend. It must not guess GBK versus UTF-8.

## Validation

- After encoding-related changes run Python compilation for backend files and `node --check trpg_orchestrator/web/app.js`.
- Check at least one campaign-scoped outbox file and the global outbox mirror to confirm Chinese content is not mojibake.
- Run `python -m trpg_orchestrator.cli validate-encoding` before and after Codex changes that touch source, prompts, JSON, Markdown, HTML, CSS, JS, or runtime text pipelines.
- Use `python scripts/normalize_encoding.py` only as a manual migration tool. It rewrites decodable text files to UTF-8 without BOM and LF newlines, but skips files that already look mojibake so humans can repair them.
- Never copy terminal mojibake back into source, prompt, JSON, outbox, or frontend files. If the terminal display is suspicious, inspect bytes or read through the encoding utilities.
- Prompt files, JSON memory, outbox runtime files, and frontend responses must be UTF-8 end to end.
