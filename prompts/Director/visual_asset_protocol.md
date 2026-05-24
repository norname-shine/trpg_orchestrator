# Visual Asset Protocol

This protocol describes structured visual and map data that V4, Codex, or future parsers may pass to the frontend. V4 owns semantic layout and image intent; the backend owns canvas defaults, coordinate normalization, cache keys, and renderer-specific fallback values.

## Production Custom Canvas Scope

- Local custom Canvas gallery assets are limited to `map`, `item`, and `prop`.
- Do not use this gallery Canvas protocol for player, sub-player, companion, NPC, monster, character, portrait, or CG assets.
- `item` means a player-held, equippable, or consumable object.
- `prop` means a scene clue, mechanism, environmental object, non-portable object, or unowned object.
- New map Canvas data should prefer `schema: "trpg.map_asset_protocol.v1"`.
- `trpg.map_asset_protocol.v1` uses semantic `layers`; allowed layer types are only `area`, `route`, `site`, and `overlay`.
- Map protocol overlays should attach local effects to `target_site` with a small `radius` when possible. Avoid oversized free-floating glows unless the whole map state is affected.
- Canvas specs are declarative JSON only. Do not output JavaScript, raw Canvas commands, SVG, function bodies, or renderer-specific drawing code.

## Suggested JSON Shape

```json
{
  "visual_assets": [
    {
      "kind": "prop | item | character | scene | cg",
      "id": "",
      "title": "",
      "gallery_category": "prop | item | character | map | cg | registered_custom_filter_id",
      "detail": "",
      "source_memory": "",
      "certainty": "confirmed | clue | uncertain | placeholder",
      "display_zone": "gallery | map | portrait | log",
      "cache_policy": "stable | scene_only | rebuild_on_version",
      "canvas_spec": {
        "schema": "item_canvas_spec.v1 | actor_canvas_spec.v1",
        "archetype": "pendant | device | document | fragment | weapon | relic_box | custom",
        "silhouette": "triangle | round | rectangle | shard | blade | custom",
        "materials": ["silver", "purple_crystal"],
        "palette": { "base": "#c9c2b7", "accent": "#8c62d6", "glow": "#b892ff" },
        "parts": [
          { "kind": "chain" },
          { "kind": "gem", "shape": "round", "position": "center" },
          { "kind": "runes", "density": "medium" }
        ],
        "state_effects": [
          { "kind": "glow", "target": "gem", "intensity": 0.45 }
        ],
        "marks": ["ancient_runes"],
        "features": ["hooded", "masked", "scholar", "scarred"],
        "role_archetype": "guide | merchant | guard | scholar | monster | custom"
      },
      "character_targets": [
        {
          "actor_id": "",
          "avatar_key": "",
          "role": "player | npc | companion | servant | monster | key_character",
          "portrait_asset_kind": "portrait | npc_portrait | companion_portrait | monster_portrait",
          "crop_policy": "auto_face | auto_bust | keep_existing_if_uncertain",
          "update_visual_baseline": true
        }
      ],
      "positive_prompt": "",
      "negative_prompt": "",
      "aspect_ratio": "1:1 | 16:9 | 3:4 | 4:3",
      "style_preset": "",
      "quality": {
        "steps": 30,
        "cfg_scale": 6.5,
        "sampler": "DPM++ 2M Karras",
        "size": "1024x1024"
      }
    }
  ],
  "map_route": {
    "title": "",
    "nodes": [
      { "id": "", "label": "", "certainty": "confirmed | clue | inferred" }
    ],
    "edges": [
      { "from": "", "to": "", "kind": "route | blocked | trace | danger" }
    ],
    "markers": [
      { "label": "", "kind": "clue | pressure | hazard | resource", "certainty": "confirmed | uncertain" }
    ]
  },
  "story_topology": {
    "nodes": [
      { "id": "", "label": "", "certainty": "confirmed | clue | uncertain", "status": "active | blocked | unknown", "story_role": "anchor | exit | threat | resource | clue" }
    ],
    "edges": [
      { "from": "", "to": "", "kind": "known_route | possible_route | blocked_route | pressure_link" }
    ],
    "fixed_fields": {}
  },
  "map_canvas": {
    "canvas": { "width": 1280, "height": 720, "grid_cols": 32, "grid_rows": 18 },
    "legend": { "#": "wall_or_block", ".": "walkable", "~": "water_or_anomaly", "!": "hazard", "?": "clue", "+": "resource" },
    "ascii": [],
    "points": [
      { "id": "", "label": "", "x": 0, "y": 0, "symbol": "+", "certainty": "confirmed | clue | uncertain" }
    ],
    "routes": [
      { "from": "", "to": "", "kind": "route | blocked | trace | danger" }
    ],
    "hazards": [
      { "id": "", "label": "", "x": 0, "y": 0, "symbol": "!", "kind": "hazard | clue | pressure | resource", "certainty": "confirmed | uncertain" }
    ]
  }
}
```

## Boundaries

- Do not draw or describe exact visuals for unconfirmed canon details.
- Gallery asset kinds are fixed to `prop`, `item`, `character`, `map`, and `cg`, but these are display slots only. Use explicit `gallery_category` for visible assets and put campaign-specific semantics in custom libraries.
- `gallery_category` must be copied from the Gallery Taxonomy Contract. Runtime custom filters are not inferred from prose or `kind`.
- If the same source-backed asset belongs to multiple filters, keep one stable `id`, set the primary `gallery_category`, and add `gallery_categories` with every registered filter id it belongs to. The array must include the primary category.
- When a player asks for every gallery filter, `payloads.visual_assets` may carry one candidate per allowed `gallery_category`, but only when there is a source-backed subject. Missing source means omit that filter; do not fill with invented placeholder records.
- Player, sub-player, and companion portraits are independent character-card/avatar slots and must not become gallery filters.
- Use `certainty: clue` for suspicious traces, unverified monster signs, rumor, inference, or player speculation.
- Use stable ids for recurring NPCs, items, locations, and clues.
- Do not let a visual hint create new memory facts by itself.
- If a hint conflicts with `forbidden_changes.json`, ignore the hint and keep the memory boundary.

## Map Hints

- `map_route` is pure reusable narrative topology. It should use confirmed or obvious anchors and should not be rebuilt every turn.
- `story_topology` may mirror the same pure plot graph with fixed fields for reuse.
- `map_canvas` is the drawing map. It may be generated when the user asks "更新地图" or when the scene changes location, passages, blocked routes, or hazard positions.
- `map_canvas.render_token` must be exactly `map_canvas.v1` whenever `output_requests.map.mode` is `update_canvas`.
- `map_canvas.ascii` must be a string array and match `grid_cols` and `grid_rows` after backend normalization. It is for precise Canvas layout, not prose. `points`, `routes`, and `hazards` must be arrays; `legend` must be an object.
- The backend may choose or normalize `canvas.width`, `canvas.height`, symbols, and coordinates. V4 should keep labels short and preserve semantic intent.

## Image Prompt Hints

- When the user asks "执行生图", "生图", or a redraw, output at least one complete prompt row.
- One ready-to-use prompt is enough unless the user asks for multiple images.
- The generated image must be requested in a separate second ChatGPT image turn. Do not require story JSON and an image in the same reply.
- Do not use visual prompt rows to confirm unknown canon details.
- If the generated scene image is expected to include existing player characters, NPCs, companions, servants, monsters, or key characters, `visual_assets` should list `character_targets` so the runtime can crop matching portraits from the final image.
- `character_targets` only names known characters and target asset slots. It does not confirm unknown appearance; final portrait crops depend on the generated image and runtime recognition.

## Asset Display

- `display_zone` controls where an asset should appear by default, such as gallery, map, portrait, or log.
- `cache_policy` controls cache behavior: stable assets reuse, scene-only assets may expire with the scene, and rebuild-on-version assets may be regenerated after renderer changes.
- Frontend display uses cached PNG images; Canvas is only a hidden generation source.
- Formal generated images take priority over default Canvas portraits. The runtime may split multi-character scene images into portraits and save both the crops and each character's visual baseline into the matching character configuration.
- For local Canvas assets, provide `canvas_spec` as declarative JSON only. Do not output JavaScript, raw Canvas commands, function bodies, SVG, or free-form drawing code.
- `canvas_spec` should describe distinctive visible traits: archetype, silhouette, materials, key parts, palette, markings, and current state effects. This is how two items with the same archetype remain visually different.
- If an item state changes, update `canvas_spec.state_effects`, `palette`, or `marks` on the same stable asset id instead of creating a duplicate asset.
- NPC, monster, enemy, and key-character Canvas portraits may also use `actor_canvas_spec.v1`; it should describe only player-visible traits such as silhouette, clothing palette, hair, mask, armor, scars, carried symbols, and current visible effects.
- Current player and current companion/sub-player portraits may be generated for the left-side character cards, but their cache payload must use `gallery_category: hidden` and `display_zone: hidden`; they must not create gallery filters or资料夹 cards.

## map_canvas Semantic Map Rendering Protocol

- `map_canvas` is semantic drawing data, not character art for the frontend to reproduce cell by cell.
- `ascii` is the primary layout source for scene maps. It expresses walls, walkable areas, abnormal liquid, interactables, hazards, unknown points, characters, and relative geometry. Runtime translates it into a refined, flat, readable 2D scene map.
- The director layer provides semantic intent: regions, points, passages, blocked routes, hazards, resources, unknowns, and short labels.
- Backend/frontend owns canvas size, normalization, merged regions, icon selection, label collision avoidance, and PNG caching.
- `map_route` and `story_topology` remain pure narrative topology and must not contain ASCII grids, coordinates, terrain symbols, or image prompts.
- Symbol semantics: `#` wall/boundary/partition; `.` walkable floor; `~` black water/pollution/abnormal fluid; `+` interactable/resource; `!` danger/anomaly/high risk; `?` unknown/investigable clue; `@` player/current position; `N` NPC/character.
- `points` / `hazards` labels, kind, symbol, and certainty drive semantic classification. Text labels are short UI labels, not text to be embedded cell by cell.
- Generated maps must be saved as cached PNG assets for the current campaign; the player frontend displays PNG, not raw ASCII.
