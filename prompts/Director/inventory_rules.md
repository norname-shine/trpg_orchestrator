# Inventory Rules

Write inventory business changes only through `state_writeback.inventory_items`.

- Do not invent item gains, losses, or equipment changes without scene evidence.
- Keep equipment changes factual and reversible if evidence is uncertain.
- Do not treat inspected but unconfirmed items as fully identified.
- Do not output `output_requests.inventory`, `payloads.inventory_updates`, or inventory-related `optional_writebacks`.
- New item records must come from `state_writeback.inventory_items`. Do not create new item records from prose-only facts, resource text, injury text, or background object descriptions.
- Existing items must use their stable `item_id`; the backend will not guess identity from title, type, or description similarity.
- Accepted items must be related to the player or companion. Items owned by NPCs, locations, scenes, or unknown owners must not enter inventory records.
- Each item update must be a complete inventory item payload with at least `item_id` and `title`.
