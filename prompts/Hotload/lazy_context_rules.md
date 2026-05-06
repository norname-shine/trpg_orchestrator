# Lazy Context Rules

This project uses capability-based prompt and memory loading.

- The model must only use context that is provided in this turn.
- Missing modules are not permission to invent hidden facts.
- Heavy payloads such as maps, visual assets, gallery updates, inventory patches, dossier patches, character cards, dice requests, and canvas jobs must only appear when authorized by output_requests.
- If a capability is not loaded, do not fabricate its detailed payload.
- ChatGPT may request capability escalation only for a future turn through capability_escalation_request.
- No model may trigger recursive loading inside the same turn.
- V4 may request capabilities through output_requests, but the local backend decides whether they are available in this turn.
- ChatGPT must not override V4 output_requests.
- ChatGPT must not output optional_writebacks that were not authorized.
- The backend may fallback, defer, or warn when a requested capability is missing.
