# V4 Light Action Rules

Use this rule only for fixed lightweight player operations:

- Observe surroundings
- Talk to NPC
- Inspect item

For these operations, return the lightweight JSON response directly. Recap/review and continue are not lightweight operations; they must use the normal text turn path.

## Output Style

- Keep the output short, clear, and operational.
- Do not use ornate prose, long atmosphere, or chapter-style narration.
- Prefer concrete findings, immediate usable information, and concise prompts for the player.
- Only add a `choice_prompt` when the situation truly requires a next decision.
- Do not reveal hidden truths that the current character should not know.

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
- Valid block `type` values are `gm_narration`, `player_action`, `npc_dialogue`, `system_check`, and `choice_prompt`. Do not use `text`.
- `state_writeback` uses the same writeback schema as actor-layer output.
- Keep writeback minimal. If the light action only observes existing information, return an empty writeback object or a no-change writeback; do not create long-term facts.

## Boundary

- Update state only when the light action confirms a real change.
- Keep this path short and operational.
