# Actor Evidence Writeback Rules

Write evidence candidates only when the scene brief lists that evidence area as allowed and the player-facing prose contains clear evidence. Do not make final persistence, inventory, dossier, character-card, dice, map, visual, or story-node judgments.

- Story progress writeback may record only visible progress evidence that happened in this turn; final node completion or transition is judged after validation.
- Inventory, character-card, and dossier entries are evidence candidates, not final accepted updates.
- Dice/check handling may request or report a visible `system_check` when allowed, but must not fabricate random results or persist long-term consequences by itself.
- Do not create map, visual, gallery, canvas, or renderer data in actor output.
- Do not include scheduling fields, local routing notes, admin diagnostics, or empty placeholder objects.
