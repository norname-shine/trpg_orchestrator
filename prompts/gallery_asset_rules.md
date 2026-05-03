# Gallery Asset Rules

These rules define how the local web console treats the right-side gallery. They are runtime rules for Codex and the frontend.

## Asset Types

- `cg` is for formal story CGs, generated scene images, and player-viewable large image assets.
- `npc` and `item` are usable in the player action input.
- `scene`, `map`, `monster`, and `ecology` are view-only unless the user explicitly asks to act on them.
- Monster and ecology rows may represent traces, uncertainty, or pressure. Do not present them as confirmed facts unless memory confirms them.

## Fixed Category ID Rules

- Gallery categories must not be randomly added during play. When a campaign is created, its gallery filter categories must be assigned once.
- Every category must have one stable unique ID. Frontend JSON rendering, backend output, and cached asset reuse must align to that ID set.
- Only content matching the fixed ID allowlist may become a gallery card. Visual assets, temporary records, and system notes outside the allowlist must not create cards.
- `cg` is a universal fixed filter and should be present for every campaign type. Formal generated story images must enter the CG category.
- Fate-style campaigns default to: `cg`, `master`, `servant`, `npc`, `scene` / `map` (displayed as scene), and `item`.
- Monster Hunter, wasteland, COC, DND, and other campaign types may use different startup category ID configs, but the underlying rule is the same: fixed IDs, allowlist admission, no random expansion.
- `all` is only a frontend aggregate filter. It is not an asset category ID, and backend rows must never use `all` as `kind`.

## Citation Input

- NPC citation format: `@NPC_NAME:`
- Item citation format: `Inspect item "ITEM_NAME":`
- Do not insert scene, monster, ecology, or map citations into the action input by default.
- A citation only prepares player input; it does not decide the player's action.

## Display Rules

- Gallery cards should show title, short detail, and a type label.
- Do not show raw JSON.
- Details should be concise and should prefer confirmed memory facts.
- The same physical item must appear as one card even if its state changes. Merge state changes into the card detail instead of creating new cards for adjectives, damage, glow, temperature, signal, or contamination states.
- Use stable item identity before state text. Examples: `heated_well_box` and `glowing_well_box` are still `well_box`; `phone completely has no signal` is still `phone`.
- When an item, scene, or character status changes, reuse the existing card and update its status, detail, thumbnail, or text in place instead of creating duplicate cards of the same type.
- Ordinary visual assets must not be split into new gallery cards by themselves. An asset may enter the gallery only when it maps to a fixed category ID and a stable entity.
- Formal CG is separate from scene/map: CG goes to `cg`; maps and locations go to `scene`.
- Empty states must explain that the current filter has no visible assets.
- Filtering must work without rebuilding assets.

## Cache Rules

- Gallery thumbnails are local Canvas PNG assets cached through `/api/asset`.
- Cached assets may be listed through `/api/assets`.
- Asset cache records should preserve title, detail, type label, source, and generator version when available.
- Deleting or rebuilding assets only affects cached PNGs and the asset manifest; it must not alter campaign memory.
