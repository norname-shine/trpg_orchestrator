# Director Visual Payload Min

- Use this only to decide whether the current turn may request visual payload preparation.
- Do not generate assets directly.
- Real execution still depends on this turn's `output_requests`.
- `user_requested` requires an explicit player image request.
- `director_triggered` requires a concrete visible reason, such as first appearance of an important NPC, item, creature trace, or scene image.
- Keep payload details minimal; full image structure belongs to heavier visual rules.
