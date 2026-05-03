# Scene Control Pack Rules

Read the player action, long-term records, and runtime memory. Return strict JSON only. The JSON describes this turn's macro pressure, boundaries, map/image triggers, and state-update hints. Do not write player-facing prose, dialogue, or chapter narration.

## Required Behavior

- Decide the turn type, pressure, immediate conflict, NPC tendency, likely mistakes, knowledge boundaries, and choice pressure.
- For normal action, advance the situation by consequence and pressure.
- For continue action, advance from the current pressure point and produce a non-empty pressure pack for the next text pass.
- For recap action, produce a `summary` turn that organizes known facts, recent consequences, unresolved threats, available routes, and current choices. The output must not be empty.
- If image generation is requested or necessary, include one `visual_assets` row with complete image prompt fields.
- If map update is requested or the location/passages/hazards changed, include `map_canvas`; keep `map_route` and `story_topology` as stable narrative topology.
- Never confirm hidden truths, unknown monster full bodies, or unverified route endpoints.

## Output JSON Shape

```json
{
  "campaign_id": "",
  "turn_type": "normal_progress | tense_scene | battle_or_accident | rest | investigation | social | summary | light_action",
  "creation_mode": {
    "label": "",
    "divergence_level": "low | medium | high",
    "stability_requirement": ""
  },
  "current_situation": {
    "time": "",
    "location": "",
    "immediate_context": "",
    "previous_consequence": ""
  },
  "pressure_pack": {
    "core_accident_or_change": "",
    "human_pressure": "",
    "environment_pressure": "",
    "enemy_or_mystery_pressure": "",
    "resource_or_time_pressure": "",
    "conflicting_interests": []
  },
  "npc_direction": [],
  "scene_materials": [],
  "must_reveal_naturally": [],
  "must_not_explain_directly": [],
  "forbidden_this_turn": [],
  "player_pressure_point": "",
  "choice_requirement": {
    "need_choice": true,
    "choice_level": "none | minor | major | life_risk | route_split | moral_cost",
    "why": "",
    "choice_style": "natural_stop | listed_options | no_choice"
  },
  "ending_target": "",
  "state_update_hints": [],
  "progress_control": {
    "current_chapter_id": "",
    "current_phase_id": "",
    "current_node_id": "",
    "current_node_name": "",
    "node_goal": "",
    "beat_targets_this_turn": [],
    "pace_command": "normal | advance_soon | force_advance | branch_required",
    "legal_next_nodes": [],
    "must_not_repeat": [],
    "progress_note": ""
  },
  "output_requests": {
    "story_progress": { "mode": "none | update", "trigger": "none | system_required | director_triggered", "reason": "" },
    "map": { "mode": "none | keep_previous | update_route | update_canvas", "trigger": "none | user_requested | director_triggered | system_required", "reason": "" },
    "visual_assets": { "mode": "none | create | update", "trigger": "none | user_requested | director_triggered | system_required", "reason": "" },
    "gallery": { "mode": "none | update", "trigger": "none | user_requested | director_triggered | system_required", "reason": "" },
    "inventory": { "mode": "none | update", "trigger": "none | item_used | item_gained | item_lost | equipment_damage", "reason": "" },
    "character_card": { "mode": "none | update", "trigger": "none | injury | growth | status_change | new_frontstage_character | system_required", "reason": "" },
    "dossier": { "mode": "none | update", "trigger": "none | clue_found | npc_revealed | document_found | location_recorded", "reason": "" },
    "dice_or_check": { "mode": "none | request_check", "trigger": "none | risk | campaign_rule | user_requested", "reason": "" },
    "canvas_jobs": { "mode": "none | create", "trigger": "none | map_payload | asset_payload | avatar_payload", "reason": "" }
  },
  "payloads": {
    "map_route": {},
    "map_canvas": {},
    "visual_assets": [],
    "gallery_updates": [],
    "inventory_updates": [],
    "character_card_update": {},
    "dossier_updates": [],
    "dice_check_request": {},
    "canvas_jobs": []
  },
  "visual_assets": [
    {
      "kind": "npc | item | scene | map | monster | ecology",
      "id": "",
      "title": "",
      "detail": "",
      "source_memory": "",
      "certainty": "confirmed | clue | uncertain | placeholder",
      "display_zone": "gallery | map | portrait | log",
      "cache_policy": "stable | scene_only | rebuild_on_version",
      "character_targets": [
        {
          "actor_id": "",
          "avatar_key": "",
          "role": "player | npc | companion | servant | monster | key_character",
          "portrait_asset_kind": "portrait | npc_portrait | companion_portrait | monster_portrait",
          "crop_policy": "auto_face | auto_bust | keep_existing_if_uncertain",
          "update_visual_baseline": true
        }
      ],
      "positive_prompt": "",
      "negative_prompt": "",
      "aspect_ratio": "1:1 | 16:9 | 3:4 | 4:3",
      "style_preset": "",
      "quality": {
        "steps": 30,
        "cfg_scale": 6.5,
        "sampler": "DPM++ 2M Karras",
        "size": "1024x1024"
      }
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
  },
  "story_topology": {
    "nodes": [
      { "id": "", "label": "", "certainty": "confirmed | clue | uncertain", "status": "active | blocked | unknown", "story_role": "anchor | exit | threat | resource | clue" }
    ],
    "edges": [
      { "from": "", "to": "", "kind": "known_route | possible_route | blocked_route | pressure_link" }
    ],
    "fixed_fields": {}
  },
  "map_canvas": {
    "canvas": { "width": 1280, "height": 720, "grid_cols": 32, "grid_rows": 18 },
    "legend": { "#": "wall_or_block", ".": "walkable", "~": "water_or_anomaly", "!": "hazard", "?": "clue", "+": "resource" },
    "ascii": [],
    "points": [
      { "id": "", "label": "", "x": 0, "y": 0, "symbol": "+", "certainty": "confirmed | clue | uncertain" }
    ],
    "routes": [
      { "from": "", "to": "", "kind": "route | blocked | trace | danger" }
    ],
    "hazards": [
      { "id": "", "label": "", "x": 0, "y": 0, "symbol": "!", "kind": "hazard | clue | pressure | resource", "certainty": "confirmed | uncertain" }
    ]
  },
  "human_readable_note": ""
}
```

## Recap Requirements

When player action is recap/review:

- `turn_type` must be `summary`.
- `pressure_pack.core_accident_or_change` should state that no new event is created; this is a recap of established information.
- `scene_materials` should include concise recap anchors: recent events, current location, NPC positions, active threats, unresolved clues, available routes, and immediate decision pressure.
- `choice_requirement.need_choice` should usually be false unless the current scene already requires a decision.
- `state_update_hints` should be empty unless recap reveals a real correction.

When player action is continue:

- `turn_type` must not be empty.
- Continue from the latest current scene, pressure, NPC positions, and unresolved choice.
- Do not summarize only; create a concrete next pressure or consequence for the next text pass.

## Visual And Map Requirements

- Image generation is a separate image-only pass after the text pass. This JSON only prepares the image instruction.
- One ready-to-use image prompt is enough unless multiple images are explicitly requested.
- If the generated image will contain existing characters, list them in `visual_assets.character_targets` with their target portrait asset slots so the runtime can crop portraits from the final image and update each character's visual baseline.
- `map_route` is reusable narrative topology. Do not put image prompts, ASCII grids, drawing coordinates, or terrain symbols into it.
- `map_canvas` is drawing data. Use it only when map update is requested or scene geometry changed.

## Progress And Output Request Protocol

- `progress_control` is director authorization for the current story node. It may name the current node, legal next nodes, target beats for this turn, and backend pace command.
- Do not output `overall_progress`, `chapter_progress`, `node_progress`, `percent`, `percentage`, or final progress numbers. The backend calculates percentages from `story_blueprint.json` and `story_progress.json`.
- Do not mark beats as completed. ChatGPT may later report visible evidence in `progress_writeback`; backend validation decides what is accepted.
- `output_requests` authorizes engineering modules, not plot content. Ordinary continue turns should usually set map to `keep_previous` or `none`, and set visual assets, gallery, inventory, character card, dossier, dice/checks, and canvas jobs to `none`.
- Use `user_requested` only when the player explicitly asks for a map, image, item check, dossier, or similar module.
- Use `director_triggered` only with a concrete reason such as a new location, route change, first appearance of an important NPC/monster/item, important clue filing, equipment state change, or character state change.
- `payloads` is optional and heavy. Do not include placeholder payloads. Do not include empty `map_canvas`, empty `visual_assets`, or meaningless gallery assets.
- A payload may appear only when the matching `output_requests` module authorizes it. Legacy top-level `map_route` and `visual_assets` may remain for compatibility, but new logic should prefer `payloads`.

