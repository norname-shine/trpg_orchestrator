# Actor Evidence Writeback Rules

Write only player-visible evidence candidates. `state_writeback` is reviewed before persistence; it is still the actor layer's responsibility to structure visible facts that future turns may need.

- `state_writeback` must always include `short_term_state`, `long_term_memory`, `new_open_threads`, `closed_threads`, `gallery_assets`, and `inventory_items`.
- If no new open thread exists, output `new_open_threads: []`.
- If no thread closed, output `closed_threads: []`.
- Always output `gallery_assets: []`; actor-layer text never persists asset-folder cards.
- If no inventory item changed, output `inventory_items: []`.
- Empty evidence objects are allowed only for the two required containers: `short_term_state: {}` and `long_term_memory: {}`.
- `long_term_memory` may record only facts or changes already visible in this turn's prose.
- Story progress writeback may record only visible progress evidence from this turn; final node completion or transition is judged after validation.
- Do not write empty placeholder objects.
- Do not include scheduling fields, local routing notes, admin diagnostics, forecast data, hidden causes, or future nodes.
- `blocks` are display-only; `system_check` shows check results only. Durable facts belong in `state_writeback`.

## Gallery Boundary

The actor layer serves player-facing prose. It does not issue, copy, rename, categorize, or persist asset-folder cards.

- Keep `state_writeback.gallery_assets` as `[]` in normal actor output.
- Map, CG, Canvas, and asset-folder persistence happen outside the actor layer.
- Do not create gallery cards from narration, choices, map text, item observations, NPC dialogue, or director payload summaries.
- If a visible fact needs a future asset card and no director payload exists, mention it only through prose or short-term state evidence; do not fabricate a gallery row.
- Item state, identification, depletion, carried status, and inventory ownership changes belong only in `state_writeback.inventory_items`.

## Global Inventory Writeback

Use `state_writeback.inventory_items` whenever this turn creates an item, changes an item state, or derives a new item from an existing item.

- Each `inventory_items` entry must include non-empty string `item_id` and `title`.
- Derived items must include `source_item_id`.
- Use stable `item_id` for existing items. The runtime does not merge by title or description similarity.
- Do not use removed inventory transport fields or removed inventory request modules.

Required shape:

```json
{
  "state_writeback": {
    "short_term_state": {},
    "long_term_memory": {},
    "new_open_threads": [],
    "closed_threads": [],
    "gallery_assets": [],
    "inventory_items": [
      {
        "item_id": "stable_item_id",
        "title": "Item title",
        "state": {
          "status": "observed state"
        }
      }
    ]
  }
}
```

TODO: Memory semantic typing belongs to a later memory-semantics branch, not this prompt-dispatch branch.
