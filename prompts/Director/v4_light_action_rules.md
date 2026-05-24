# V4 Light Action Rules

Use this rule only for fixed lightweight player operations:

- Observe surroundings
- Talk to NPC
- Inspect item
- View dossier/material for a named item
- Recap/review

For these operations, return the lightweight JSON response directly. Continue is not a lightweight operation; it must use the normal text turn path.

## Output Style

- Keep the output short, clear, and operational.
- Do not use ornate prose, long atmosphere, or chapter-style narration.
- Prefer concrete findings, immediate usable information, and concise prompts for the player.
- Only add a `choice_prompt` when the situation truly requires a next decision.
- Do not reveal hidden truths that the current character should not know.
- "Observe surroundings" and "recap/review" use a `system_check` system verdict block. Keep it short, clear, and actionable.
- For actions such as "view material for item" or "inspect item", prefer a short `system_check` system verdict block, not GM narration. Write `state_writeback.inventory_items` only when a new visible state, use, depletion, activation sign, or ownership change is confirmed.
- When an item check updates state, use this body pattern: `资料状态被更新：这枚符文吊坠已确认存在激活迹象，紫色水晶的微光趋于稳定，触碰时会产生可感知的暖流脉动。符文仍未完全解读，但你已经获得了可记录的基础信息。`
- If the player repeatedly checks the same item within a short span, and the scene is not at a critical point, the item has no new reaction, and no new trigger is present, only report that there is no new change or that the known state remains. Do not repeat the same `inventory_items` writeback and do not create new `gallery_assets`.
- "Talk to NPC" uses `npc_dialogue`. Generate 1-2 interactive dialogue blocks from the current scene, pressure pack, recent memory, and the NPC's personality. The dialogue should include voice, attitude, hesitation, probing, emotion, or small action beats that enrich player experience; it must not merely deliver information.
- NPC dialogue may provide clues, warnings, or relationship movement, but it must do so through character voice. Do not make the NPC sound like a quest giver, system prompt, or encyclopedia entry.

## JSON Contract

Return strict JSON only:

```json
{
  "blocks": [],
  "summary": "",
  "state_writeback": {}
}
```

The JSON must be compatible with the normal frontend story log parser:

- `blocks` uses the same block schema as actor-layer output.
- Valid block `type` values are `player_action`, `system_check`, `npc_dialogue`, and `choice_prompt`. Do not use `text`. Observe, recap, and item checks default to `system_check`; NPC dialogue defaults to `npc_dialogue`.
- `state_writeback` uses the same writeback schema as actor-layer output.
- Keep writeback minimal. If the light action only observes existing information, return an empty writeback object or a no-change writeback; do not create long-term facts.
- Item state updates must use `state_writeback.inventory_items`; the frontend will display that state on the gallery item card. Do not create extra `gallery_assets` just to sync the gallery.

## Boundary

- Update state only when the light action confirms a real change.
- Keep this path short and operational.
