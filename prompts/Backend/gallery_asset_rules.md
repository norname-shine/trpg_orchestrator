# Gallery Asset Rules

These rules define how the local web console treats the right-side gallery. They are runtime rules for Codex and the frontend.

## Asset Types

- `cg` is for formal story CGs, generated scene images, and player-viewable large image assets.
- Fixed gallery categories are only `prop`, `item`, `character`, `scene`, and `cg`.
- Gallery categories are asset display slots only. They do not decide campaign-specific story semantics.
- Use an explicit director-provided `gallery_category` when a campaign-specific entity should be visible in one of the fixed slots.
- Maps and locations enter `scene` only when they are visual scene/map assets.
- Clue/document-like objects enter `item` or `prop`; they must not create `clue` or `document` filters.
- Player, sub-player, and companion portraits stay in independent character-card/avatar slots and must not enter gallery filters.
- Campaign-specific long-term details belong in director-declared custom libraries, not backend fixed library names.

## Fixed Category ID Rules

- Gallery categories must not be randomly added during play. When a campaign is created, its gallery filter categories must be assigned once.
- Every category must have one stable unique ID. Frontend JSON rendering, backend output, and cached asset reuse must align to that ID set.
- Only content matching the fixed ID allowlist may become a gallery card. Visual assets, temporary records, and system notes outside the allowlist must not create cards.
- `cg` is a universal fixed filter and should be present for every campaign type. Formal generated story images must enter the CG category.
- The startup baseline is always `prop`, `item`, `character`, `scene`, and `cg`.
- Director setup may add 0-3 story-specific custom gallery filters in `campaign_categories`. Four or more must be rejected locally.
- Campaign-specific resources should use director-declared custom libraries, custom categories, or explicit fixed-slot asset links, not new fixed category IDs.
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
