# Output Contract Rules

The pressure pack uses output_requests as the only authorization source for heavy payloads.

- output_requests are lightweight control declarations.
- payloads are heavy structured outputs.
- If output_requests.<module>.mode is none, payloads for that module must not appear.
- If output_requests.<module>.mode is keep_previous, no new payload should be generated.
- Empty placeholders are forbidden.
- Payloads must have concrete trigger reasons.
- ChatGPT state_writeback optional_writebacks must follow output_requests.
- Story progress writeback is lightweight and may appear when story_progress mode is update.
- Percentages for story progress are backend-calculated only.
- AI must not output overall_progress, chapter_progress, node_progress, percent, or percentage.
