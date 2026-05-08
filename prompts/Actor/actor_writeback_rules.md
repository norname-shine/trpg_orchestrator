# Actor Evidence Writeback Rules

Write only visible evidence candidates. `state_writeback` is not final memory; it is reviewed before anything is persisted.

- `long_term_memory` may record only facts or changes already visible in this turn's prose.
- `optional_writebacks` may appear only when the scene brief or allowed state updates clearly permit that evidence area.
- Story progress writeback may record only visible progress evidence from this turn; final node completion or transition is judged after validation.
- Inventory, character-card, dossier, and dice/check entries are evidence candidates, not final accepted updates.
- Do not create map, visual, gallery, canvas, renderer, or asset-generation data in actor output.
- Do not write empty placeholder objects.
- Do not include scheduling fields, local routing notes, admin diagnostics, forecast data, hidden causes, or future nodes.

TODO: Memory semantic typing belongs to a later memory-semantics branch, not this prompt-dispatch branch.
