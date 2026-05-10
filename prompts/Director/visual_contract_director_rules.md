# Director Visual Contract Rules

Director-layer visual output is campaign-bound visual intent, not final renderer instructions.

- Use `visual_contract_candidates` when a player-visible or initialization-required entity needs stable visual identity.
- `entity_type` is closed: use only `player`, `companion`, `character`, `map`, `cg`, `item`, or `prop`.
- The protagonist must use `entity_type="player"`. Companions must use `entity_type="companion"`.
- NPCs, monsters, enemies, and key characters must use `entity_type="character"` with `actor_role="npc"`, or `actor_role="key_character"`.
- Maps and locations must use `entity_type="map"`. Opening/story scene images must use `entity_type="cg"`.
- Do not output `entity_type="player_character"`, `entity_type="npc"`, `entity_type="scene"`, or `entity_type="location"`.
- For NPC portraits, use `render_intent.primary="character_portrait"` with `actor_role="npc"`; never output `npc_portrait`.
- Do not hard-code renderer-only implementation fields. Coordinates are allowed only when they are story/spatial facts such as map points, route nodes, hazards, or landmarks.
- Do not finalize hidden identities, unrevealed monster forms, secret NPC appearances, or player-owned details before they are confirmed.
- Each candidate should include `entity_key`, `entity_type`, `display_name`, `memory_refs`, `visual_identity`, `render_intent`, `style_constraints`, `negative_constraints`, and `update_policy` when known. Character candidates for NPCs, monsters, or key characters should also include `actor_role`.
- Treat `visual_identity` as what the entity is in this campaign. Treat `render_intent` as how it may be shown. Treat `style_constraints` as campaign style guidance.
- Backend validates and merges candidates into campaign `visual_contracts.json`; the Director must not assume a candidate directly creates an image.
- Actor text prompts should only receive visible summaries. Image generation actors may receive render-ready prompts derived from the stored contract.
