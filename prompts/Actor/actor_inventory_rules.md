# Actor Inventory Writeback Rules

Write inventory business changes only through `state_writeback.inventory_items`.

- When this turn visibly creates an item, changes an item state, consumes/loses an item, identifies an item, or derives a new item from an existing item, include an `inventory_items` entry.
- Each entry must include `item_id` and `title`.
- Use stable `item_id` for existing items.
- Derived items must include `source_item_id`.
- Do not invent item gains, losses, uses, or equipment changes without scene evidence.
- Keep uncertain items described as uncertain until identified in play.
- Inventory writeback should involve the player or a companion, not random scenery or unrelated NPC property.
- Do not create renderer style fields or local asset data for items.
- Do not use removed inventory transport fields, removed inventory request modules, or inventory-related `optional_writebacks`.
