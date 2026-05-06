# Campaign Data Lifecycle And Multi-Campaign Rules

These rules govern local campaign data, ChatGPT inputs and outputs, entity archives, and frontend assets. They apply to Monster Hunter style campaigns, Fate, COC, DnD, and original campaigns.

## Multi-Campaign Isolation

- Every campaign must use `campaign_id` as the primary isolation key and `asset_seed` as the auxiliary seed for reproducible visual assets.
- Inputs, outputs, logs, assets, and entity archives must not depend only on the global `outbox/` directory.
- The global `outbox/` is only a mirror and compatibility entry for manual ChatGPT workflows. It must not become the long-term source of truth.
- Standard paths include campaign-scoped outbox files, `logs/*_turn.json`, and `assets/manifest.json`.

## Turn Records

- Every turn must leave a traceable local record.
- Store at least `campaign_id`, `turn_index`, `asset_seed`, `player_action`, `pressure_pack`, ChatGPT input/output paths, parsed blocks, state writeback, audit result, and generated or updated entities.
- `logs/*_turn.json` is the audit record. `run_records.json` is a lightweight index for the frontend and future compaction.

## Local Entity Archives

- NPCs, companions, servants, monsters, items, clues, map nodes, locations, and quests should all enter local entity archives.
- Recommended generic fields: `id`, `kind`, `display_name`, `campaign_id`, `asset_key`, `status`, first/last seen turn, `confirmed`, `uncertain`, `personality`, `background`, `relationships`, and `update_policy`.
- NPC archives must support personality, motivation, background, speech boundaries, knowledge boundaries, relationship changes, and frontend portrait assets.
- Companions, sub-players, and servants must be saved separately from NPC archives because their abilities, injuries, trust, true names, contracts, or hidden identities can evolve during the story.

## Dynamic Entity Updates

- Fate servants, Monster Hunter palicos, DnD party allies, and COC assistant investigators are all covered by the same abstract concept: companion or sub-player.
- Core objects and companions are not one-off items or static NPCs. Confirmed facts go into `confirmed`; unconfirmed material goes into `uncertain`; visual changes go into asset metadata; state changes go into `status` or dedicated fields.
- Do not hardcode long-term facts in the frontend or drawing layer.

## Visual Assets And Writeback

- Visible entities should have stable `asset_key` values derived from campaign id, entity id, asset kind, and generator version.
- Canvas is only the hidden generation source. The visible frontend must use cached PNG images.
- ChatGPT may propose state changes through `state_writeback`, but long-term memory writes require V4 audit or local validation.
- Speculation, player-unselected actions, and hidden facts must not be written as confirmed memory.
