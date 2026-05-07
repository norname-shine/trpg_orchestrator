# Director Visual Contract Rules

Director-layer visual output is campaign-bound visual intent, not final renderer instructions.

- Use `visual_contract_candidates` when a player-visible or initialization-required entity needs stable visual identity.
- Candidates may describe player, companion, item, map, scene, monster, CG, or campaign-specific entity types.
- Do not hard-code renderer-only implementation fields. Coordinates are allowed only when they are story/spatial facts such as map points, route nodes, hazards, or landmarks.
- Do not finalize hidden identities, unrevealed monster forms, secret NPC appearances, or player-owned details before they are confirmed.
- Each candidate should include `entity_key`, `entity_type`, `display_name`, `memory_refs`, `visual_identity`, `render_intent`, `style_constraints`, `negative_constraints`, and `update_policy` when known.
- Treat `visual_identity` as what the entity is in this campaign. Treat `render_intent` as how it may be shown. Treat `style_constraints` as campaign style guidance.
- Backend validates and merges candidates into campaign `visual_contracts.json`; the Director must not assume a candidate directly creates an image.
- Actor text prompts should only receive visible summaries. Image generation actors may receive render-ready prompts derived from the stored contract.
