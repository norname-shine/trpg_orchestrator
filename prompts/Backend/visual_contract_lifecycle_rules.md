# Visual Contract Lifecycle Rules

`visual_contracts.json` is a campaign-scoped visual interpretation layer.

- It does not replace source memory. It references source memory through `binding.memory_refs`.
- Store one contract per stable `entity_key`; merge Director candidates instead of replacing the whole file.
- Keep contract fields extensible. Type-specific details belong inside nested objects such as `visual_identity.physical`, `visual_identity.actor`, `visual_identity.spatial`, or `render_intent.details`.
- Asset cache entries should store `visual_contract_key` and `visual_contract_hash`.
- Reuse cached assets when the contract hash still matches; rebuild only when the contract or renderer version changes.
- Reject empty, placeholder, debug-only, or unbound contracts.
- Canvas rendering and image-generation actors should derive their input from the same stored contract.
