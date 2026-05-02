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
- The NPC gallery must exclude the main player character and companion/sub-player names. The main player uses `portrait` assets only; companions use `companion` or `companion_portrait` assets. They must never create `gallery_npc`, `npc_portrait`, separate `player_portrait`, or campaign-specific universal assets such as `palico` for the actor type.
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
