# Canvas Asset Generation Rules

These rules describe how the local frontend generates visual assets. They are runtime rules for Codex and the web console, not instructions for ChatGPT to generate images.

## General Boundary

- Canvas assets are generated locally by the frontend.
- ChatGPT must not generate image prompts unless the user explicitly asks for image generation.
- Visual assets are derived from confirmed local memory, current scene state, V4 pressure pack, and visible campaign records.
- Do not invent unconfirmed character appearance, monster full body, map locations, route endpoints, equipment ownership, or item facts.
- If the source data is uncertain, label the asset as a clue, trace, unknown ecology, or current-scene placeholder.

## Cache Rules

- All generated assets must be cached through `/api/asset`.
- Save generated images as PNG data URLs only.
- Use stable cache keys based on campaign id, asset kind, object id, and generator version.
- Increment `ASSET_GENERATOR_VERSION` when drawing rules change.
- Do not repeatedly redraw or overwrite the same visible map during polling if the campaign id, object id, and generator version are unchanged.
- Cache paths:
  - maps: `campaigns/<campaign_id>/assets/maps/`
  - portraits: `campaigns/<campaign_id>/assets/portraits/`
  - items and ecology clues: `campaigns/<campaign_id>/assets/items/`

## Area Map Rules

- The area map displayed in the left panel must be shown as a cached PNG image.
- The frontend may use a hidden canvas as the PNG generation source, but the visible element must be an image.
- The visible area map must use a 16:9 ratio.
- Do not expose a manual redraw or refresh button for the area map.
- The map should be generated once for the current campaign/location/generator version and then loaded from cache.
- Map labels must be readable in a small panel. Use larger source-PNG text than normal UI text.
- Keep route nodes and labels inside the image bounds.
- Prefer a readable route diagram over a fully realistic terrain map.
- Use confirmed scene/location data first. If route data is missing, infer only generic local anchors such as start point, current scene, far point, and current pressure.
- If the scene contains traces, mud, medicine bottles, wagon damage, migration, monster signs, or ecological pressure, show them as clue markers instead of confirmed monster facts.

## Gallery Map Thumbnail Rules

- Gallery map thumbnails may use the same map generator but must use more compact labels than the area map.
- Thumbnail text should be readable but must not overflow the gallery card.
- Thumbnail generation must also be cached as PNG.

## NPC Portrait Rules

- NPC portrait assets must be locally generated and cached.
- NPC portraits must use stable names or ids as seeds.
- The NPC gallery must exclude the main player character and companion/sub-player names. The main player uses `portrait` assets only; companions use `companion` or `companion_portrait` assets. They must never create `gallery_npc`, separate `player_portrait`, or campaign-specific universal assets such as `palico` for the actor type. NPC gallery cards reuse `npc_portrait`.
- Companion/sub-player drawing must be selected by `archetype`, `species`, or `kind`: for example `palico` for Monster Hunter, `servant` for FATE, and `companion` for a generic fallback.
- NPC portraits must be visually distinct. Vary at least several of:
  - hair shape
  - headgear or side ornaments
  - facial hair or mouth shape
  - clothing color
  - accent color
  - background tone
- Do not use one generic face with only small color changes.
- Do not fix unconfirmed detailed canon appearance. Treat the portrait as an interface token unless the campaign memory explicitly confirms appearance.
- Player and NPC message blocks should reuse stable `avatar_key` values so portraits stay consistent.

## Portrait Override From Formal Generated Images

- First Canvas portraits are default placeholders and fallbacks, not permanent visual sources.
- When a formal generated scene image contains existing named entities with explicit portrait slots, automatically identify and crop the matching portrait from the generated image first.
- Save cropped results by director-provided role and portrait slot. Do not infer a campaign-specific semantic class from the creature, enemy, or threat name alone.
- For multi-character scene images, attempt to match each recognizable character separately. Do not treat the whole scene image as the only gallery asset.
- A successfully matched crop should replace the old Canvas portrait. If matching confidence is not reliable, keep the previous portrait and do not overwrite it.
- When replacing a portrait, update that character's dedicated visual baseline: face shape, facial feature style, hairstyle, clothing tone, primary colors, style mood, distinctive identifiers, and anti-drift constraints.
- Later avatar, portrait, bust, or full-body generation for the same character must read this visual baseline so the face and style stay consistent.
- This rule is campaign-agnostic. Do not hard-code Fate, Monster Hunter, COC, DND, wasteland, or original campaign branches; match by role, asset type, and stable `actor_id` / `avatar_key`.

## Item And Clue Icon Rules

- Item and clue icons must be generated from local memory rows, recent scene resources, equipment history, and confirmed writeback facts.
- The same item in different states must remain one card/entity. Update the latest status in the detail text and entity metadata; do not create separate cards such as `well_box`, `glowing_well_box`, and `heated_well_box`.
- Item semantic analysis must identify the physical object first, then its state. For example, `phone completely has no signal` is a `phone` device with a no-signal state, not a generic document or an item named `no_signal`.
- Recurring item assets must use stable entity ids such as `well_box`, `phone`, `switch_axe`, and update metadata/details instead of changing asset identity every turn.
- Split long resource strings into separate clauses before generating cards.
- Do not show raw JSON objects in the UI.
- Each card should have a short title, optional detail, and a type label.
- Use icon families based on keywords:
  - mud, trace, footprint, stain: mud or claw-mark icon
  - medicine, bottle, liquid: bottle icon
  - axe, weapon, equipment: weapon icon
  - registration, board, sign, record: signboard icon
  - feather, scale, material, shard: material shard icon
  - supply, satchel, bag: satchel icon
- If the item fact is uncertain, display it as clue or damage, not as confirmed inventory.

## Frontend Layout Rules

- The left column must be wide enough to support the 16:9 area map without crowding the character, task, and memory panels.
- Long location names in panel headers must ellipsize.
- Gallery card titles should clamp to two lines.
- Gallery type labels should stay aligned at the bottom of the card.
- Buttons that imply regenerating cached assets should be hidden unless the user explicitly enters a debug or rebuild mode.

## Current Generator Version Note

- Current frontend generator version: `ASSET_GENERATOR_VERSION = 9`.
- Version 9 strengthens the Monster Hunter `palico` archetype so companion portraits visibly read as a palico: large cat ears, inner ears, cat nose, whiskers, goggles, and a small mantle.

## Player And Companion Portraits

- Player portraits must be higher-spec than ordinary NPC portraits and must function as stable main-character identifiers.
- Companion and sub-player portraits must be cached separately from NPC portraits and must never enter the NPC gallery.
- Companion drawing must first resolve an open-ended `visual_profile` from current campaign memory, companion raw setup, personality, species/form, equipment, and campaign style.
- `companion_type_raw` is an open string and must be preserved. It is not a whitelist, not a gallery category, and not a reason to turn the companion into an NPC.
- `companion_type_preset` may add visual rules for common hints such as palico, servant, familiar, construct, or vehicle, but missing a preset must fall back to a custom companion profile rather than the player or NPC template.
- Companion Canvas metadata must include `runtime_role: companion`, `gallery_category: hidden`, `visible_in_gallery: false`, `not_in_gallery_filters: true`, `render_tier: companion`, `companion_type_raw`, `companion_type_preset`, and `visual_profile`.
- If `visual_profile.certainty` is not `confirmed`, the generated portrait is only a UI token and must not confirm long-term appearance facts.

## map_canvas Scene Map Canvas Algorithm

- When `map_canvas` exists, the map generator must use the semantic map algorithm; use `map_route` only as fallback.
- Do not reproduce ASCII cell by cell. Do not draw raw grid lines, tactical coordinates, legends, compasses, side explanation panels, or in-image title bars.
- Fixed drawing order: background -> main map plane -> room structures/walls/floors -> furniture -> special regions -> routes/blocks -> point icons -> label chips.
- The grid only infers spatial structure: rooms, partitions, passages, merged liquid areas, threat zones, resources, unknowns, and character points.
- Consecutive `~` symbols must be merged into a single abnormal-fluid region instead of separate wave cells.
- Draw `#` as thick walls/structural boundaries, `.` as walkable floor, `+` as a unified interaction icon, `!` as a unified hazard icon, and `?` as a unified unknown icon.
- Icons and labels must be separated using a consistent `[icon] [rounded label chip]` pattern. Labels must not sit on top of icons or cover key geometry.
- Label chip colors should follow semantics: neutral objects light cream, water light blue, danger light pink, unknown light purple, characters light neutral with a matching accent.
- Campaign type changes palette and mood only; Fate, COC, DND, wasteland, Monster Hunter, and original campaigns use the same structural protocol.
- The result should feel like a visual-novel scene record or archive map, not a horror tactical map, realistic photo, poster illustration, or raw character-grid reproduction.
- All generated maps must be saved through `/api/asset` into the current campaign `assets/maps/`; manifest metadata should preserve the original `map_canvas` for redraw decisions.


## Unified Portrait Naming And VCG Locking

- Avatar assets use one role-specific portrait reference per character. NPC gallery cards reuse `npc_portrait`; do not generate `gallery_npc`.
- Keep the traditional portrait filename stem and append only the version tag: numeric versions use `_v1`, `_v2`, ..., `_v16`; formal CG feedback uses `_VCG`.
- Example: `npc_portrait_<asset_seed>_<actor_name>_v16.png` and `npc_portrait_<asset_seed>_<actor_name>_VCG.png`.
- Manifest keys follow the same version rule: numeric `:v16`, formal CG feedback `:VCG`.
- If a character has a `VCG` portrait asset, automatic Canvas portrait iteration must stop for that character. The latest nearby numeric version remains only as stable fallback.
- Formal CG feedback may update or replace the `VCG` asset, but ordinary refreshes must not replace it with a new random Canvas portrait.
- This applies to player characters, NPCs, companions, servants, monsters, and key characters across all campaign types.

## Fixed Gallery Category Admission

- A Canvas asset may enter the gallery only after it maps to the current campaign's `gallery_taxonomy` allowlist.
- `gallery_taxonomy.core_categories` are system-stable and fixed to `prop`, `item`, `character`, `scene`, and `cg`.
- `gallery_taxonomy.campaign_categories` are 0-3 campaign-defined extensions from director setup.
- `all` is a frontend aggregate filter only; it is not a gallery category ID.
- `companion` is not a gallery category. Current player and current bound companion/sub-player assets default to `gallery_category: hidden`.
- Fixed gallery categories are display slots only. Use explicit `gallery_category` when an asset should be visible in one of them; clue/document-like visible objects use `item` or `prop`.
- CG is separate from maps/scenes: CG assets use `cg`; map and location thumbnails use `scene`.
- Undefined kinds, temporary visual records, backend system notes, and ordinary visual assets that cannot map to a stable entity must not create gallery cards merely because a PNG exists.
- When a card already exists for the same character, item, or scene, the new Canvas PNG may update that card's thumbnail, status, or detail, but must not create a duplicate card.
