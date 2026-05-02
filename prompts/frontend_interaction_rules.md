# Frontend Interaction Rules

These rules define expected user interactions in the local TRPG web console.

Before changing frontend behavior, read `codex_system_architecture_rules.md`.
All UI changes must be implemented through reusable multi-campaign structures first, then adapted per campaign type.

## Job Buttons

- Disable run, send, ingest, and rewrite actions while a backend job is running.
- Do not disable collapse buttons or modal close buttons during a job.
- Show command output in the log panel.

## Gallery

- Filter buttons must update the visible gallery immediately.
- The full gallery modal uses the same active filter as the side gallery.
- NPC and item rows can be cited into the player action input.
- Scene, map, monster, and ecology rows are view-only by default.
- Every newly visible item-like asset must be semantically analyzed before display.
- Item-like assets include inventory rows, `visual_assets` items, clue objects, documents, relics, materials, supplies, weapons, and scene-only props that appear as gallery cards.
- The frontend must use that semantic analysis to draw a local Canvas PNG once, save it into the current campaign asset manifest, and then display the saved PNG in the UI.
- Do not reuse a generic item icon when the text identifies a specific object class. For example, a Monster Hunter bone switch axe, a mud armor fragment, and a Fate relic box must use different Canvas drawing branches and different cached PNG assets.
- Canvas is only the hidden generation source; normal display should use the cached PNG asset.

## Campaign Picker

- Selecting a campaign changes `active_campaign` through `/api/select-campaign`.
- Do not create a new ChatGPT conversation automatically.
- If a campaign has no ChatGPT binding, the frontend may show it, but send/capture should still rely on backend safety checks.

## Maps

- The visible left map is an image sourced from cached PNG.
- Hidden Canvas is allowed only as a generation source.
- Normal refresh must not visually redraw the map unless campaign, location, or generator version changes.
