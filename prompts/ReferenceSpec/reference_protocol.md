# Prompt Reference Protocol

This folder defines how prompt files are referenced, injected, and maintained.

## Reference Locations

- Runtime module references live in `prompts/prompt_modules.json`.
- Human layer references live in `prompts/prompt_rules_index.md` and each layer `INDEX.md`.
- Bilingual pair state lives in `prompts/prompt_language_sync.json`.
- Code may request a prompt by filename; `read_prompt()` resolves the root path first and then searches subdirectories.

## Reference Style

- Use paths relative to `prompts/`, for example `Actor/chatgpt_host_prompt.md`.
- Keep English and `_CN.md` files in the same directory.
- Do not reference moved files by stale root-level paths in new docs or JSON.
- If a prompt is runtime-injected, declare the exact path in `prompt_modules.json`.

## Update Rules

- When moving a prompt file, update `prompt_modules.json`, `prompt_rules_index.json`, the master index, and the target layer `INDEX.md`.
- When changing one side of a bilingual prompt pair, update the counterpart in the same directory.
- After prompt edits, run `sync-prompts --apply`, `sync-prompts --check`, and `validate-encoding`.

