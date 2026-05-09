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
- Gallery filters show the fixed baseline `prop`, `item`, `character`, `map`, and `cg`, plus at most 3 director-initialized custom categories. Temporary visual assets must not introduce new filters or card categories during play.
- The frontend should render only cards whose kind maps to the fixed category ID allowlist. Unknown kinds, undefined IDs, backend notes, and temporary visual records must not create standalone gallery cards.
- `cg` is a universal filter. Formal story CGs, generated scene images, and player-viewable large image assets go to `cg`.
- Fixed gallery filters are display slots only. Campaign-specific semantics must come from director-declared custom libraries or explicit `gallery_category`, not backend guessing.
- Clue/document-like visible objects use `item` or `prop`; they must not create fixed `clue` or `document` filters.
- CG is separate from maps/scenes: CG uses `cg`; maps and locations use `map`.
- Status changes for the same character, item, or scene should update the existing card in place instead of creating duplicate cards.
- NPC and item rows can be cited into the player action input.
- Scene/map rows are view-only by default. Campaign-specific long-term details are shown through explicit asset links or custom story-library views.
- Every newly visible item-like asset must be semantically analyzed before display.
- Item-like assets include inventory rows, `visual_assets` items, clue objects, documents, relics, materials, supplies, weapons, and scene-only props that appear as gallery cards.
- The frontend must use that semantic analysis to draw a local Canvas PNG once, save it into the current campaign asset manifest, and then display the saved PNG in the UI.
- Do not reuse a generic item icon when the text identifies a specific object class. For example, a Monster Hunter bone switch axe, a mud armor fragment, and a Fate relic box must use different Canvas drawing branches and different cached PNG assets.
- Canvas is only the hidden generation source; normal display should use the cached PNG asset.

## Campaign Picker

- Selecting a campaign changes `active_campaign` through `/api/select-campaign`.
- Do not create a new ChatGPT conversation automatically.
- If a campaign has no ChatGPT binding, the frontend may show it, but send/capture should still rely on backend safety checks.

## Story Feed

- Within the current frontend browser session, the story feed must append newly generated turn blocks instead of fully replacing the previous visible prose on every refresh.
- Keep exactly the most recent 10 TRPG story turns in the visible accumulated feed. Drop older turns automatically.
- Polling the same backend blocks must not append duplicates; use a turn content signature or equivalent dedupe mechanism.
- When the frontend page is reopened, do not reload the accumulated browser-session queue. Show only the latest backend story segment.
- Story CG blocks must display the title as exactly `CG`; do not append scene names, aspect ratios, device labels, or generation-stage prefixes.
- The note below a story CG should contain only a short player-facing scene description. Do not show technical remarks such as 16:9, PC, 9:16, composition preview, formal icon, formal deep image, portrait feedback, cache, crop, or safe area.
- Story CG images and gallery CG cards must be clickable and open a dedicated large-screen CG viewer. The viewer shows only the large image, `CG` title, and a short scene caption.

## Maps

- The visible left map is an image sourced from cached PNG.
- Hidden Canvas is allowed only as a generation source.
- Normal refresh must not visually redraw the map unless campaign, location, or generator version changes.

## Frontend map_canvas Display Constraints

- Regional maps prefer cached PNGs generated from `map_canvas`; old `map_route` is fallback only when drawing data is absent.
- The player frontend must not display raw ASCII, grid lines, legends, compasses, tactical coordinates, or backend explanation panels.
- Visible maps keep only the map body, rooms/furniture, point icons, label chips, and necessary route/block expressions.
- If `pressure_pack` has updated but prose is still not synchronized, the map panel may still read the latest `map_canvas` for structured map refresh; it must not expose director-layer prose to the player.
- When cached PNG manifest metadata differs from the latest `map_canvas`, the frontend must redraw and overwrite the cache instead of reusing an old image by key alone.
- Map display defaults to 16:9; text and icons must remain readable in the sidebar size.
