# Director Map Payload Min

- Use this only to decide whether the current turn may request map payload preparation.
- Do not update the map unless this turn's `output_requests.map` authorizes it.
- Keep route and map decisions grounded in visible movement or explicit request.
- `user_requested` requires an explicit map/route request.
- `director_triggered` requires visible location, route, hazard, boundary, or access change.
- Keep payload details minimal; full map drawing rules belong to heavier map rules.
- If `map.mode` is `update_canvas`, `payloads.map_canvas` may use either legacy `render_token: "map_canvas.v1"` drawing data or the structured map asset protocol `schema: "trpg.map_asset_protocol.v1"`.
- Prefer `trpg.map_asset_protocol.v1` for new maps. It must include `id`, `title`, `scale`, `palette`, and `layers`.
- `trpg.map_asset_protocol.v1.layers` must use only these layer types: `area`, `route`, `site`, `overlay`.
- Map protocol features are semantic data, not drawing code. Do not output JavaScript, Canvas commands, SVG, image prompts, or renderer-specific instructions.
- Map protocol coordinates are normalized numbers from `0` to `1`.
- Overlay `pulse` should attach to `target_site` and use a small `radius` such as `0.06` to `0.12`; avoid large background glows unless the whole map state is meant to be affected.
- Legacy `map_canvas.v1` remains readable for old campaigns, but new director output should not rely on ASCII unless precise grid layout is required.
- Prefer source-backed `initial_map_canvas` and current visible scene anchors. Do not invent geography just to make the map look fuller.
- `map_canvas` is consumed by the runtime renderer; it is not a prose description and must not be a placeholder.
