# Character Card JSON Rules

Use this rule when a character card needs to be initialized, returned, refreshed, or repaired. Prose output must not decide character numeric changes.

The response must include a `character_card` JSON object when the task asks for character status, player card, companion card, or UI-ready character data. Do not replace long-term facts unless the user or approved writeback confirms them.

## Lifecycle And Update Triggers

Character card JSON has two fixed update states. Both are locally cached, synchronized to the frontend, and reusable across all campaign types.

### 1. Opening Initialization

- After a new campaign is created and the opening character concept is confirmed, the system generates a complete `character_card` JSON object.
- The generated card becomes the initial local persistent cache for this campaign.
- The frontend loads this cached JSON directly to render the narrative card, vitals, attributes, tags, progression bars, companion card, and related UI modules.
- The initial cache is the baseline for later state-control updates. Do not regenerate it from prose unless the player explicitly rebuilds the character.

### 2. Dynamic In-Game Updates

- During play, only the state-control pass decides whether character vitals, attributes, advantages, conditions, tags, growth progress, or companion status have changed.
- If a change occurred, output a new `character_card` JSON object or a compatible character-card patch.
- The runtime sends the new JSON to the frontend.
- The frontend overwrites the local character-card cache for the current campaign and refreshes all character UI: progress bars, vitals, attribute chart, status tags, companion data, growth progress, and portrait metadata.
- Prose may narrate consequences, but it must not decide numeric or structural character-card changes.

### Fixed Chain

Always follow this chain:

1. initialize cached character card
2. state-control pass judges in-game changes
3. state-control pass outputs new JSON
4. runtime delivers the JSON
5. frontend overwrites the local cache
6. frontend refreshes character-card UI

This chain must be shared by COC, DnD, Fate, Monster Hunter style campaigns, and original campaigns. Do not hardcode campaign-specific character fields in the core logic.

## Top-Level Shape

```json
{
  "character_card_update": {
    "trigger": "initial_generation | v4_runtime_update",
    "changed": true,
    "cache_action": "create_initial_cache | overwrite_campaign_cache | no_change",
    "reason": ""
  },
  "character_card": {
    "mode": "auto | strict_stats | narrative_status",
    "identity": {
      "name": "",
      "gender": "",
      "age": "",
      "ancestry": "",
      "origin": "",
      "class_or_role": "",
      "level_or_stage": "",
      "motivation": "",
      "personality": "",
      "weakness": "",
      "companion": ""
    },
    "visual_seed": "",
    "progression": {
      "label": "",
      "current": null,
      "max": null,
      "percent": null,
      "text": ""
    },
    "vitals": [],
    "conditions": ["Memory loss"],
    "attributes": [],
    "equipment": [],
    "companion": {
      "name": "",
      "kind": "",
      "archetype": "",
      "species": "",
      "personality": "",
      "visual_seed": "",
      "vitals": [],
      "conditions": ["Injured"],
      "equipment": []
    }
  }
}
```

## Update Metadata

- `character_card_update.trigger` must identify why the card is being returned.
- Use `initial_generation` only for new-campaign opening character setup.
- Use `v4_runtime_update` only when in-game events changed character state.
- Use `cache_action: create_initial_cache` for the opening baseline and `overwrite_campaign_cache` for confirmed runtime updates.
- If no update is needed, return `changed: false` and `cache_action: no_change`. Do not emit a new card merely to restate existing data.
- The runtime stores character-card cache per campaign ID/seed. Never share a character-card cache across campaigns.

## Mode Rules

- `strict_stats`: use only when the campaign has confirmed numeric values. Each numeric field must have clear provenance from memory, rules, or approved writeback.
- `narrative_status`: use when the campaign does not have strict numbers. Describe state with short labels, percentages, and narrative text without pretending they are exact rules.
- `auto`: allowed in generated memory; the frontend will treat confirmed numeric vitals/attributes as strict and otherwise use narrative status.

## Vitals

Strict example:

```json
{
  "key": "health",
  "label": "Health",
  "current": 28,
  "max": 34,
  "tone": "red"
}
```

Narrative example:

```json
{
  "key": "stamina",
  "label": "Stamina",
  "state": "Spent but still able to act",
  "percent": 72,
  "tone": "green"
}
```

## Attributes

Strict example:

```json
{
  "key": "str",
  "label": "Strength",
  "short": "STR",
  "value": 11,
  "modifier": "+0"
}
```

Narrative example:

```json
{
  "key": "survival",
  "label": "Survival Judgment",
  "short": "RET",
  "text": "Cautious retreat and preparation first"
}
```

## Companion

- Companion types are not fixed.
- Monster Hunter campaigns may use `palico`, Fate campaigns may use `servant`, determined by campaign type. COC or DND campaigns that do not need companion identity should not generate companions.
- Companion cards must be independent from NPC archives, because companions will update abilities, injuries, trust, contracts, or hidden identities as the story progresses.
- Companion portraits use `companion` or `companion_portrait` assets and must not be mixed with NPC portraits.

## Visual Asset Rules

- `visual_seed` must be stable. Use confirmed name or ID, not a changing description.
- Do not invent exact appearance as canon unless it already exists in memory.
- Frontend will use `visual_seed` to generate and cache a local PNG portrait. The UI should display the cached PNG through `img`, not a visible canvas.
- Companion/NPC portraits use their own stable `visual_seed`.
- Companion/sub-player cards must describe their campaign-specific type with `archetype`, `species`, or `kind`. Examples: Monster Hunter `palico`, FATE `servant`, generic fantasy `familiar`, sci-fi `drone`.
- Do not assume every companion is a palico. The frontend treats `palico` as one drawing archetype, not as the universal companion asset type.

## Compatibility Rules

- If a field is unknown, use an empty string, `null`, or an empty list. Do not fabricate.
- All tag/chip/badge fields are string arrays only. Use `"conditions": ["Memory loss"]` and `"badges": ["Protagonist", "medical background"]`; never use object tags with id, label, icon, or description metadata.
- Keep labels short enough for compact UI.
- Return no more than 6 attributes and no more than 6 conditions for the default status panel.
- Equipment should include only confirmed items or current clues.
- Character stat change authority belongs only to the state-control pass.
- Prose output only performs story consequences and must not change character-card values by itself.
