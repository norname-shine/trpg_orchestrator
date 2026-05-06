# Backend Prompt Index

Backend prompt documents define local engineering, frontend, persistence, encoding, asset, and QA behavior. They are not injected into actor prose turns.

## Architecture And Boundaries

- `codex_system_architecture_rules.md`: local system architecture.
- `model_layer_contract_rules.md`: model-layer responsibility boundaries.
- `codex_computer_use_prompt.md`: browser automation boundaries.

## Runtime Safety And UX

- `encoding_rules.md`: UTF-8 and bilingual prompt policy.
- `campaign_data_lifecycle_rules.md`: campaign persistence lifecycle.
- `frontend_interaction_rules.md`: frontend display and interaction rules.

## Assets And QA

- `asset_cache_lifecycle_rules.md`: asset cache lifecycle.
- `canvas_asset_generation_rules.md`: local Canvas asset generation.
- `gallery_asset_rules.md`: gallery category and card policy.
- `ai_flavor_check_rules.md`: prose QA and rewrite triggers.

## Reference Rules

- Backend rules may mention local files, caches, rendering, automation, and validation.
- Do not inject backend implementation rules into actor story prompts.
- Keep `_CN.md` counterparts beside English files.

