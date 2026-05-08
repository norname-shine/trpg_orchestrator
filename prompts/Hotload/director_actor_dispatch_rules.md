# Director Actor Dispatch Rules

- Include `actor_dispatch` for the backend to choose this turn's actor modules.
- Use abstract module names, not file names.
- Use `heavy_modules` only for complex dialogue, climax, recap, map, dossier, inventory, or similarly heavy scenes.
- `actor_dispatch` chooses actor prompt support only; it does not authorize extra payloads.
