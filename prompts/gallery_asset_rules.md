# Gallery Asset Rules

These rules define how the local web console treats the right-side gallery. They are runtime rules for Codex and the frontend.

## Asset Types

- `npc` and `item` are usable in the player action input.
- `scene`, `map`, `monster`, and `ecology` are view-only unless the user explicitly asks to act on them.
- Monster and ecology rows may represent traces, uncertainty, or pressure. Do not present them as confirmed facts unless memory confirms them.

## Citation Input

- NPC citation format: `@NPC名称：`
- Item citation format: `查看物品「物品名称」：`
- Do not insert scene, monster, ecology, or map citations into the action input by default.
- A citation only prepares player input; it does not decide the player's action.

## Display Rules

- Gallery cards should show title, short detail, and a type label.
- Do not show raw JSON.
- Details should be concise and should prefer confirmed memory facts.
- Empty states must explain that the current filter has no visible assets.
- Filtering must work without rebuilding assets.

## Cache Rules

- Gallery thumbnails are local Canvas PNG assets cached through `/api/asset`.
- Cached assets may be listed through `/api/assets`.
- Asset cache records should preserve title, detail, type label, source, and generator version when available.
- Deleting or rebuilding assets only affects cached PNGs and the asset manifest; it must not alter campaign memory.
