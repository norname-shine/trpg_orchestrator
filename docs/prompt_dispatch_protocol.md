# Prompt Dispatch Protocol

This document freezes the current prompt slimming and dispatch rules. It is a guardrail for future work: do not expand ordinary prompts or add new protocol fields without a separate scoped change.

## 1. Core Fields

- `output_requests`: current-turn capability authorization. Only this field can authorize map, visual assets, inventory, dossier, character card, dice/check, canvas, and similar execution capabilities.
- `actor_dispatch`: director-to-backend suggestion for current-turn actor module selection. It uses abstract module names, not real prompt file paths.
- `orchestration_forecast`: backend-only next-turn hotload hint. It only preloads rules, does not authorize assets, and must not be passed to the actor layer.

## 2. Layer Duties

Director:

- Decides current-turn direction, pressure, NPC direction, choice pressure, and `output_requests`.
- May provide `actor_dispatch`.
- May provide `orchestration_forecast`.
- Does not write player-facing prose.
- Does not write memory directly.

Backend:

- Parses `output_requests`, `actor_dispatch`, and `orchestration_forecast`.
- Maps prompt modules.
- Deduplicates, trims, validates, and filters prompt inputs.
- Controls forecast expiry.
- Ensures forecast data never enters actor input.

Actor:

- Writes only current player-visible prose.
- Uses only visible memory and scene brief.
- Writes only visible evidence candidates.
- Does not decide plot direction, hidden truth, map generation, image generation, or final persistence.

## 3. Hotload Rules

- Frequent ordinary turns use min modules.
- Deep style, long NPC voice, map, visual, dossier, inventory, dice, and other heavy modules load on demand.
- Preload capabilities only load rules. They do not authorize assets.
- Actual map, image, dossier, inventory, character card, dice/check, and canvas execution must follow current-turn `output_requests`.

## 4. Prohibitions

- Actor input must not include `orchestration_forecast`.
- Actor input must not include `hidden_reason`, `future_node`, `future_asset`, `hotload_next_turn`, or `upcoming_assets`.
- Director output must not name real prompt file paths.
- Do not reintroduce `memory_type`, `certainty`, or `ttl` writeback semantics in this prompt-dispatch branch.
- Do not keep long visual contract rules always loaded in ordinary turns.
- Do not merge small, clearly scoped modules just to save a few dozen tokens.

## 5. Current Acceptance Snapshot

From `scripts/prompt_size_report.py`:

- There are no `large_modules`.
- All actor scenarios have `contains_forecast_leak=false`.
- `normal_actor` does not load `style_core`.
- `npc_actor` does not load `npc_voice_rules`.
- `deep_npc_actor` loads `npc_voice_rules`.
- `normal_director` does not load `visual_contract_director_rules`.
- `visual_preload_director` loads `director_visual_payload_min` and `visual_contract_director_rules`.
- `map_preload_director` loads `director_map_payload_min`.

## 6. Future Extension Rules

- Check `prompt_size_report.py` first.
- Compress only `large_modules`.
- Add tests before changing triggers.
- If a change needs memory semantic routing, use a separate `memory-semantics` branch.
- If a change needs asset pre-generation, use a separate `asset-pipeline` branch.
- If a change needs frontend display work, use a separate `frontend-display` branch.

## 7. Memory Digest Rules

Memory payload compression is now part of the prompt dispatch contract. Ordinary model inputs must receive curated digest structures, not raw memory file bundles.

### Director Memory Digest

- `build_director_user_prompt()` `Selected Director Memory` must use `build_director_memory_digest()`.
- Raw memory files must not be placed wholesale into ordinary director model input.
- `select_memory_for_director()` may remain available for raw, debug, backend analysis, or audit-oriented flows, but it must not be used directly for ordinary director model input.

Director digest top-level keys are fixed:

- `campaign_brief`
- `current_story_anchor`
- `current_runtime`
- `player_brief`
- `companion_brief`
- `node_brief`
- `thread_brief`
- `asset_refs`
- `forbidden_brief`

Ordinary director input must not contain:

- `campaign_profile.json`
- `campaign_direction.json`
- `story_blueprint.json`
- `recent_context.json`
- `story_progress.json`
- `main_threads.json`
- `director_setup`
- `initial_assets`
- `initial_map_canvas`
- `canvas_draw_instructions`
- `render_rules`
- `visual_contract_candidates`
- `cg_prompt`
- `campaign_taxonomy`
- `character_attribute_schema`
- `story_blueprint_patch`
- `custom_libraries`

### Actor Visible Memory Digest

- `build_chatgpt_input()` `Visible Memory For This Turn` must use `build_actor_memory_digest()`.
- Raw actor memory files must not be placed wholesale into ordinary actor model input.
- `select_memory_for_actor()` may remain available for raw, debug, backend analysis, or audit-oriented flows, but it must not be used directly for ordinary actor model input.

Actor digest top-level keys are fixed:

- `actor_campaign_brief`
- `visible_runtime`
- `visible_player_state`
- `visible_npc_state`
- `visible_items`
- `style_brief`
- `visible_forbidden`
- `actor_visible_story_progress`

Ordinary actor input must not contain:

- `campaign_profile.json`
- `style_profile.json`
- `recent_context.json`
- `player_state.json`
- `forbidden_changes.json`
- `npc_memory.json`
- `equipment_history.json`
- `director_setup`
- `initial_assets`
- `render_rules`
- `campaign_taxonomy`
- `character_attribute_schema`
- `prompt_routing`
- `canvas_draw_instructions`
- `item_canvas_rules`
- `orchestration_forecast`
- `actor_dispatch`
- `hotload_next_turn`
- `upcoming_assets`
- `hidden_reason`
- `future_node`
- `future_asset`

### Quality Rule

- If player-facing prose becomes too thin, do not roll ordinary model input back to raw memory bundle transmission.
- Add or refine digest source fields instead, such as `visible_player_state`, `style_brief`, or `visible_forbidden`.
- Raw memory may be used only for backend work, debug views, audit-oriented flows, or local analysis. It must not enter ordinary director or actor model input.

### Acceptance Snapshot

- Director `Selected Director Memory` now uses the director memory digest.
- Actor `Visible Memory For This Turn` now uses the actor visible memory digest.
- Real two-layer prompt input has dropped from roughly the 120k-character range to roughly the 30k-character range.
- The memory payload compression phase is complete.
- Further prompt size work should open a separate `prompt-module-slim` phase for prompt module text itself.
