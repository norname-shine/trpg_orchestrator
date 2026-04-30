# Visual Asset Protocol

This protocol describes structured visual hints that V4, Codex, or future parsers may pass to the frontend. V4 gives constraints and source hints; the local frontend draws the assets.

## Suggested JSON Shape

```json
{
  "visual_assets": [
    {
      "kind": "npc | item | scene | map | monster | ecology",
      "id": "",
      "title": "",
      "detail": "",
      "source_memory": "",
      "certainty": "confirmed | clue | uncertain | placeholder",
      "display_zone": "gallery | map | portrait | log",
      "cache_policy": "stable | scene_only | rebuild_on_version"
    }
  ],
  "map_route": {
    "title": "",
    "nodes": [
      { "id": "", "label": "", "certainty": "confirmed | clue | inferred" }
    ],
    "edges": [
      { "from": "", "to": "", "kind": "route | blocked | trace | danger" }
    ],
    "markers": [
      { "label": "", "kind": "clue | pressure | hazard | resource", "certainty": "confirmed | uncertain" }
    ]
  }
}
```

## Boundaries

- Do not draw or describe exact visuals for unconfirmed canon details.
- Use `certainty: clue` for suspicious traces, unverified monster signs, rumor, inference, or player speculation.
- Use stable ids for recurring NPCs, items, locations, and clues.
- Do not let a visual hint create new memory facts by itself.
- If a hint conflicts with `forbidden_changes.json`, ignore the hint and keep the memory boundary.

## Map Hints

- `map_route.nodes` should use confirmed or obvious local anchors.
- `map_route.markers` may include pressure, damage, traces, blocked paths, weather, time pressure, and resource points.
- The frontend should prefer readable route diagrams over realistic maps.
- Labels must be short enough for a small 16:9 map panel.
