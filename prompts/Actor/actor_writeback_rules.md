# Actor Evidence Writeback Rules

Write evidence candidates only when the scene brief lists that evidence area as allowed and the player-facing prose contains clear evidence. Do not make final persistence, inventory, dossier, character-card, dice, map, visual, or story-node judgments.

- Story progress writeback may record only visible progress evidence that happened in this turn; final node completion or transition is judged after validation.
- Inventory, character-card, and dossier entries are evidence candidates, not final accepted updates.
- Dice/check handling may request or report a visible `system_check` when allowed, but must not fabricate random results or persist long-term consequences by itself.
- Do not create map, visual, gallery, canvas, or renderer data in actor output.
- Do not include scheduling fields, local routing notes, admin diagnostics, or empty placeholder objects.

Every long-term writeback entry and optional_writebacks entry should include:

```json
{
  "memory_type": "confirmed_fact | observed_clue | npc_claim | short_term_scene | progress_update",
  "certainty": "confirmed | likely | uncertain",
  "source": "actor",
  "ttl": "scene | session | permanent",
  "value": ""
}
```

Use the types conservatively:

- `confirmed_fact`: only facts visibly confirmed by player-facing prose or approved campaign memory.
- `observed_clue`: clues the player observed; clues are not the hidden truth.
- `npc_claim`: an NPC statement or belief; it represents that NPC's knowledge, not world truth.
- `short_term_scene`: temporary scene state, mood, positioning, pressure, or transient description.
- `progress_update`: visible main-thread, node, or beat progress evidence.

If uncertain, use `observed_clue`, `npc_claim`, or `short_term_scene` instead of `confirmed_fact`.
