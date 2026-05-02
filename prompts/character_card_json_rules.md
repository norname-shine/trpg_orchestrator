# Character Card JSON Rules

Use this rule when V4 or ChatGPT needs to return, refresh, or repair a character card.

The response must include a `character_card` JSON object when the task asks for character status, player card, companion card, or UI-ready character data. Do not replace long-term facts unless the user or approved writeback confirms them.

## Top-Level Shape

```json
{
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
    "conditions": [],
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
      "conditions": [],
      "equipment": []
    }
  }
}
```

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
- Keep labels short enough for compact UI.
- Return no more than 6 attributes and no more than 6 conditions for the default status panel.
- Equipment should include only confirmed items or current clues.
