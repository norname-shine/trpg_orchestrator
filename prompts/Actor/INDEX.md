# Actor Prompt Index

Actor prompts perform player-facing prose, dialogue, visible checks, evidence candidates, and the separate actor image pass. Actor text prompts must not receive raw director/backend scheduling metadata.

## Runtime Core

- `chatgpt_host_prompt.md`: actor story JSON contract.
- `chatgpt_style_rules.md`: prose style.
- `chatgpt_npc_voice_rules.md`: NPC dialogue.
- `chatgpt_image_rules.md`: actor-side image pass boundary.

## Actor Lazy Modules

- `actor_context_rules.md`: visible-context discipline.
- `actor_writeback_rules.md`: evidence writeback boundary.
- `actor_dice_check_rules.md`: visible system-check handling.
- `actor_inventory_rules.md`: inventory evidence candidates.
- `actor_dossier_rules.md`: dossier evidence candidates.
- `actor_map_rules.md`: player-visible map narration boundary.
- `actor_character_evidence_rules.md`: character-status evidence candidates.

## Archived Actor-Control Files

- `character_card_json_rules.md`: character-card control/output rules; not injected into normal actor prose prompts.
- `chatgpt_monster_rules.md`: legacy monster-oriented actor prose rules; keep archived until a runtime trigger is reintroduced.

## Reference Rules

- Actor text prompts receive scene brief and evidence/check labels, not raw `output_requests` or `payloads`.
- Actor image prompts may receive sanitized image instructions and visible scene context.
- Keep `_CN.md` counterparts beside English files.

