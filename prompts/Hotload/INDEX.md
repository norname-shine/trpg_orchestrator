# Hotload Prompt Index

Hotload files support runtime prompt selection, capability injection, output contracts, and actor-input pruning.

## Runtime Modules

- `lazy_context_rules.md`: director/audit lazy context loading.
- `output_contract_rules.md`: director/audit output contract boundary.
- `director_actor_dispatch_rules.md` / `director_actor_dispatch_rules_CN.md`: director-side `actor_dispatch` backend dispatch rules.
- `director_forecast_rules.md` / `director_forecast_rules_CN.md`: backend-only `orchestration_forecast` next-turn hotload rules.

## Actor-Pruning Archive

- `actor_prompt_pruned_fields.md`: actor prompt pruning policy and non-authority list.

## Machine Files In Prompt Root

- `../prompt_modules.json`: runtime module registry.
- `../prompt_rules_index.json`: machine-readable layer index.
- `../prompt_language_sync.json`: bilingual prompt sync baseline.

## Reference Rules

- Actor prompts receive compact visible capability summaries, current story position, scene brief, and allowed evidence/check areas.
- Raw `Capability Plan`, `Scene Control Pack`, routing metadata, debug fields, and empty placeholders remain out of actor story prompts.
