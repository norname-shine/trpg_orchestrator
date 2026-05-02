# Codex Local System Architecture Rules

This file is the local rule Codex must follow before changing this repository. It governs the engineering design of the TRPG console, not a single campaign's story rules.

## General Principles

- Do not only fix the immediate bug. First consider the whole multi-campaign TRPG system.
- Code must be reusable, extensible, and reproducible.
- The console must support COC, DnD, Fate, Monster Hunter style campaigns, original campaigns, and future modules.
- Define generic protocols, data structures, and rendering paths before adding campaign-specific adapters.
- Components, values, UI, and logic must not be hardcoded for one campaign.
- If an implementation appears to serve only one campaign, turn it into configuration, an adapter, a registry entry, or a fallback.

## Model Responsibility Layers

- DeepSeek V4, ChatGPT, and Codex must have independent backend responsibilities. Rules are injected by role and must not mix logic.
- Fixed campaign chain: player input -> DeepSeek V4 director layer -> ChatGPT actor layer -> backend closeout -> frontend refresh.
- DeepSeek V4 is the director layer: macro plot direction, pressure pack, image-trigger decisions, map-update decisions, NPC direction, and knowledge boundaries.
- ChatGPT is the actor layer: player-readable prose, concrete dialogue, scene detail, and structured state writeback based on the V4 pressure pack.
- Codex is the local engineering layer: code, rules, APIs, parsing, asset generation, cache, QA, writeback, and persistence.
- Codex does not participate in the real director/actor story chain.
- V4 output must not be shown directly to the normal player frontend. It must pass through ChatGPT and backend parsing first.
- Image, map, and main-plot decisions are made by V4. The local system executes structured results.

## Unified Data Protocol First

- The frontend should prefer `/api/frontend-state`.
- New frontend modules must declare consumed fields before UI work.
- Multi-campaign input/output, parse results, and writeback review must be scoped to `campaigns/<campaign_id>/outbox/`; global `outbox/` is only a manual mirror.
- Text I/O must follow `prompts/encoding_rules.md`.
- The backend normalizes campaign memory, campaign profile, V4 pressure pack, ChatGPT blocks, state writeback, and the asset manifest.
- The frontend displays normalized structures and must not guess long-term facts.

## Multi-Campaign Adaptation

- Campaign differences must be expressed through config, profile, schema, adapter, or registry.
- Do not hardcode campaign-specific fields in core UI.
- Gallery filters, character-card fields, checks, item categories, map markers, and companion types must be switchable.
- Default examples may differ by campaign type, but core logic must keep a fallback.

## Character Status And Narrative Card

- Character cards must support strict numeric stats and loose narrative status.
- The frontend must not hardcode health, focus, stamina, strength, dexterity, or similar field names.
- Three core status values, six attributes, tags, and progress bars must come from unified structures or fallback config.
- Player, companion, and NPC portraits must use distinct asset kinds.
- NPC lists must not duplicate the main player or companion portrait.
- Companion type must not be hardcoded as palico; Fate may use servant, original campaigns may use familiar, drone, spirit, or other types.

## Assets, Maps, Items, And Gallery

- Every campaign must have stable `campaign_id` and `asset_seed`.
- Visual asset keys and filenames must include or derive from current campaign identity.
- Do not reuse same-name assets across campaigns.
- Canvas is only for hidden PNG generation; visible frontend uses cached PNG images.
- New visible items must go through semantic analysis before drawing. Do not draw all items as generic objects.
- The same physical item in different states remains one card; update the detail and metadata instead of creating duplicates.
- Maps prefer V4 structured `map_route` and `visual_assets`, with distinct styles for nodes, routes, blocked paths, clues, danger, and resources.

## Player-Facing And Admin-Facing Content

- Normal player UI keeps logs, summaries, immersion, story, and execution status.
- Director output, writeback audit, prompt inspection, and debug information belong to admin pages.
- Every turn should keep raw input, pressure pack, ChatGPT raw output, parsed blocks, writeback, audit, and final updates locally.
- NPCs, companions, items, clues, maps, locations, and quests must enter local archives or placeholder archives, not only DOM state.

## Modification Checklist

- Does this change only serve one campaign? If yes, can it become config or an adapter?
- Did it add hardcoded field names, filters, item types, or companion types?
- Does it still follow `/api/frontend-state`?
- Are assets and cache isolated by `campaign_id / asset_seed`?
- Are player, companion, and NPC assets kept separate?
- Does a rule document need an update?
- Does `ASSET_GENERATOR_VERSION` need to change?
- Should at least two campaign types be checked?

## XI. Verification Requirements

- After frontend JS changes, run:
  - `node --check trpg_orchestrator/web/app.js`
- After backend Python changes, run:
  - `python -m py_compile trpg_orchestrator/src/trpg_orchestrator/web_server.py`
- When multiple campaigns are involved, traverse and check local data.
- When assets are involved, check the manifest for consistency of `asset_seed`, key, path, and metadata.
