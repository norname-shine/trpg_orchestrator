# Actor Evidence Writeback Rules

Write only player-visible evidence candidates. `state_writeback` is reviewed before persistence; it is still the actor layer's responsibility to structure visible facts that future turns may need.

- `state_writeback` must always include `short_term_state`, `long_term_memory`, `new_open_threads`, `closed_threads`, `gallery_assets`, and `inventory_items`.
- If no new open thread exists, output `new_open_threads: []`.
- If no thread closed, output `closed_threads: []`.
- If no gallery fact changed, output `gallery_assets: []`.
- If no inventory item changed, output `inventory_items: []`.
- Empty evidence objects are allowed only for the two required containers: `short_term_state: {}` and `long_term_memory: {}`.
- `long_term_memory` may record only facts or changes already visible in this turn's prose.
- Story progress writeback may record only visible progress evidence from this turn; final node completion or transition is judged after validation.
- Do not write empty placeholder objects.
- Do not include scheduling fields, local routing notes, admin diagnostics, forecast data, hidden causes, or future nodes.
- `blocks` are display-only; `system_check` shows check results only. Durable facts belong in `state_writeback`.

## Global Gallery Writeback

Use `state_writeback.gallery_assets` whenever this turn creates or updates player-known, displayable, reviewable material. This includes but is not limited to clue, map note, location record, character record, item record, document, symbol record, monster/enemy observation, and environmental anomaly.

- Each `gallery_assets` entry must include non-empty string `id`, `type`, and `title`.
- Recommended fields: `category`, `display_zone`, `detail`, `source`, `payload`.
- When updating an existing asset, use the stable `asset.id` and return the complete asset. The runtime replaces the whole row by exact id; it does not shallow-merge and does not guess by title.
- Do not use removed gallery transport fields, removed gallery request modules, dossier update transports, or prose-only dossier text as the gallery fact source.
- `visual_assets` is media/image/canvas request data only; it is not gallery persistence.

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
    "gallery_assets": [
      {
        "id": "stable_visible_fact_id",
        "type": "clue",
        "title": "Visible clue title",
        "detail": "What the player observed, read, or confirmed this turn."
      }
    ],
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
