# Frontend Interaction Rules

These rules define expected user interactions in the local TRPG web console.

## Job Buttons

- Disable run, send, ingest, and rewrite actions while a backend job is running.
- Do not disable collapse buttons or modal close buttons during a job.
- Show command output in the log panel.

## Gallery

- Filter buttons must update the visible gallery immediately.
- The full gallery modal uses the same active filter as the side gallery.
- NPC and item rows can be cited into the player action input.
- Scene, map, monster, and ecology rows are view-only by default.

## Campaign Picker

- Selecting a campaign changes `active_campaign` through `/api/select-campaign`.
- Do not create a new ChatGPT conversation automatically.
- If a campaign has no ChatGPT binding, the frontend may show it, but send/capture should still rely on backend safety checks.

## Maps

- The visible left map is an image sourced from cached PNG.
- Hidden Canvas is allowed only as a generation source.
- Normal refresh must not visually redraw the map unless campaign, location, or generator version changes.
