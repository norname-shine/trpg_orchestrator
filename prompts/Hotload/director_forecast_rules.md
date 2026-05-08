# Director Forecast Rules

- `orchestration_forecast` is backend-only.
- It only affects next-turn hotloading.
- It must not be leaked to the actor layer.
- It does not authorize asset generation, map updates, or payload execution.
- It must include an expiration window.
