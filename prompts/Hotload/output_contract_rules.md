# Output Contract Rules

The pressure pack uses output_requests as the only authorization source for heavy payloads.

- output_requests are lightweight control declarations.
- payloads are heavy structured outputs.
- If output_requests.<module>.mode is none, payloads for that module must not appear.
- If output_requests.<module>.mode is keep_previous, no new payload should be generated.
- Empty placeholders are forbidden.
- Payloads must have concrete trigger reasons.
- `output_requests.gallery`, `output_requests.inventory`, `payloads.gallery_updates`, and `payloads.inventory_updates` are removed.
- Gallery business changes go only to `state_writeback.gallery_assets`.
- Inventory business changes go only to `state_writeback.inventory_items`.
- `visual_assets` is media-only. It may request image/canvas work, but it is not a gallery write.
- Existing gallery assets must use a stable `asset.id`; existing inventory items must use a stable `item_id`.
- The backend will not merge gallery assets or inventory items by title, type, or description similarity.
- ChatGPT state_writeback optional_writebacks must follow output_requests for remaining optional modules.
- Story progress writeback is lightweight and may appear when story_progress mode is update.
- Percentages for story progress are backend-calculated only.
- AI must not output overall_progress, chapter_progress, node_progress, percent, or percentage.
- All UI tag/chip/badge fields must be `string[]` only. Use examples like `"conditions": ["失忆"]`, `"badges": ["主角", "医疗相关"]`, `"asset_tags": ["线索"]`; never output object tags with `id`, `label`, `icon`, or explanatory metadata.
