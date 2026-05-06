# Actor Prompt Pruned Fields Archive

This archive documents fields intentionally removed from actor-layer prompts. The actor layer writes story prose and structured writeback only; backend and director scheduling details remain outside its prompt.

## Layer separation policy

- Actor prompts use actor-specific context, writeback, map, inventory, dossier, and dice rules.
- Actor prompts provide evidence candidates; they do not decide final persistence or UI/control updates.
- Shared director/backend rules may still mention scheduling, payload, routing, validation, and runtime details, but those rules are not injected into actor prompts.
- Actor prompt headings use player-facing concepts such as available story tools, current story position, and scene brief.
- Terms such as `director layer`, `backend`, `V4`, raw `Capability Plan`, and raw `Scene Control Pack` are excluded from actor inputs.

## capability_plan

- `prompt_modules`: Local module selection debug. Backend-owned; safe to recover in admin debug only.
- `memory_refs`: Local memory selection debug. Backend-owned; safe to recover in admin debug only.
- `warnings`: Prompt/module loading diagnostics. Backend-owned; not useful for prose.
- `loaded_capabilities`: Raw routing capability list. Replaced by a compact visible capability subset.
- `missing_capabilities`: Payload gap diagnostics. Backend/director-only.
- `output_requests`: Director/backend trigger routing. Actor receives only the resulting prose-relevant requirements.
- `output_contract`, `frontend_refresh`, and audit/control warnings: Runtime orchestration and UI refresh details. Actor receives no direct scheduling contract.

## pressure_pack

- `output_requests`: Backend update triggers for story progress, map, visual assets, gallery, inventory, and dossier. Actor receives only required narrative/writeback targets.
- `payloads`: Structured backend payload container. Actor receives only selected visible payload summaries.
- `human_readable_note`: Compatibility/debug note. It is not actor instruction material.
- `progress_control`: Raw director authorization object. Actor receives only a sanitized current story position.
- `map_canvas`: Canvas drawing coordinates, points, routes, hazards, and rendering hints. Backend-only map renderer input.
- `map_route`: Backend/player map topology. Actor may receive a short location/route summary only when relevant.
- `story_topology`: Backend story graph support. Actor receives only current progress control.
- `visual_assets`: Removed from the actor text/story pass. A separate actor image pass may receive one sanitized image instruction with prompt fields and visible scene context.
- `image_prompt`, `positive_prompt`, `negative_prompt`, `canvas_spec`, `quality`, `style_preset`: Image-generation prompt fields. Actor prose must not spend context on renderer instructions.
- `trigger_image_generation`: Runtime image-pass trigger. Actor text/story output should not schedule image generation; the actor image pass only consumes the prepared image instruction.
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

## actor scene brief

- Raw scene-control JSON is not shown to the actor.
- Empty placeholders are removed recursively before prompt injection.
- Non-prose modules such as map rendering, visual assets, gallery, and canvas jobs do not become actor writeback targets.
- Allowed actor areas are converted to plain labels such as story progress evidence, inventory evidence, character status evidence, dossier evidence, and dice/check handling.

## actor non-authority list

- Inventory: actor does not decide official gains, losses, consumption, damage, equipment state, or long-term item records.
- Dossier: actor does not decide official clue, NPC, location, document, faction, or mystery archive entries.
- Character card: actor does not decide numeric/stat changes, growth, permanent conditions, companion-card changes, cache overwrite, or portrait metadata.
- Dice/checks: actor may request or report visible `system_check` entries when campaign rules and the scene brief allow it, but must not invent mechanics, fabricate random results, or persist long-term consequences by itself.
- Map/visual/gallery/canvas: actor does not create renderer or asset payloads.
- Image generation: actor image pass is valid and must receive sanitized prompt fields, but it must not receive raw routing metadata or continue story/state writeback.
- Story progress: actor records visible evidence only; final node completion, branch, skip, merge, or failure is validated later.
