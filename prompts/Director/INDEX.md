# Director Prompt Index

Director prompts decide macro scene control, pacing, boundaries, and structured payload intent. They may mention routing/control concepts that must not be injected into normal actor prose prompts.

## Runtime Core

- `v4_director_prompt.md`: strict pressure-pack contract.
- `v4_campaign_context_prompt.md`: long-term director context.
- `v4_payload_fulfillment_prompt.md`: payload completion pass.
- `v4_light_action_rules.md`: lightweight fixed-action director path.
- `v4_audit_prompt.md`: audit pass for writeback approval.

## Control Modules

- `visual_asset_protocol.md`: visual and map payload protocol.
- `visual_contract_director_rules.md`: campaign-bound visual contract candidate rules.
- `chatgpt_map_rules.md`: director-side map-control boundary.
- `dice_check_rules.md`: director-side dice/check authorization.
- `inventory_rules.md`: director-side inventory update authorization.
- `dossier_rules.md`: director-side dossier update authorization.

## Reference Rules

- Runtime injection is controlled by `../prompt_modules.json`.
- Use this folder for director/audit control rules, not actor prose instructions.
- Keep `_CN.md` counterparts beside the English files.
