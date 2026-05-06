# Actor Prompt Pruned Fields Archive

This archive documents fields intentionally removed from actor-layer prompts. The actor layer writes story prose and structured writeback only; backend and director scheduling details remain outside its prompt.

## capability_plan

- `prompt_modules`: Local module selection debug. Backend-owned; safe to recover in admin debug only.
- `memory_refs`: Local memory selection debug. Backend-owned; safe to recover in admin debug only.
- `warnings`: Prompt/module loading diagnostics. Backend-owned; not useful for prose.
- `loaded_capabilities`: Raw routing capability list. Replaced by a compact visible capability subset.
- `missing_capabilities`: Payload gap diagnostics. Backend/director-only.
- `output_requests`: Director/backend trigger routing. Actor receives only the resulting prose-relevant requirements.

## pressure_pack

- `output_requests`: Backend update triggers for story progress, map, visual assets, gallery, inventory, and dossier. Actor receives only required narrative/writeback targets.
- `payloads`: Structured backend payload container. Actor receives only selected visible payload summaries.
- `map_canvas`: Canvas drawing coordinates, points, routes, hazards, and rendering hints. Backend-only map renderer input.
- `map_route`: Backend/player map topology. Actor may receive a short location/route summary only when relevant.
- `story_topology`: Backend story graph support. Actor receives only current progress control.
- `visual_assets`: Image and gallery generation requests. Backend/director asset pipeline input.
- `image_prompt`, `positive_prompt`, `negative_prompt`, `canvas_spec`, `quality`, `style_preset`: Image-generation prompt fields. Actor prose must not spend context on renderer instructions.
- `trigger_image_generation`: Backend image pass trigger. Actor should not schedule image generation.
- `public_think`: Player-facing waiting status. It is UI progress text, not story prose material.
- `protocol_warnings`, `warnings`, `debug`, `audit`, `diagnostics`: Validation and debug material. Backend/audit only.
- Empty strings, empty arrays, empty objects, and null values: No actor-layer business meaning; removed recursively.

## memory

- Hidden or future-planning keys such as `hidden_truth`, `hidden_motive`, `future_nodes`, `forbidden_reveals`, and `director_notes`: Director/audit-only knowledge.
- Cache, manifest, asset metadata, and local file paths: Backend asset lifecycle data, not prose instructions.
- Duplicate strings and duplicate JSON fragments: Removed to save context length while preserving one semantic copy.

## payloads

- `canvas_style`, `icon_rules`, `coordinates`, `points`, `edges`, `routes`, `legend`, `ascii`: Local visualization details.
- `source_object_id`, `asset_key`, `cached_url`, `created_at`, `generator_version`: Local asset identity/cache fields.
- `mode`, `trigger`, `reason` under backend request containers: Routing metadata. Actor receives the visible effect, not scheduling metadata.
