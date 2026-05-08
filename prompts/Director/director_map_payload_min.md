# Director Map Payload Min

- Use this only to decide whether the current turn may request map payload preparation.
- Do not update the map unless this turn's `output_requests.map` authorizes it.
- Keep route and map decisions grounded in visible movement or explicit request.
- `user_requested` requires an explicit map/route request.
- `director_triggered` requires visible location, route, hazard, boundary, or access change.
- Keep payload details minimal; full map drawing rules belong to heavier map rules.
