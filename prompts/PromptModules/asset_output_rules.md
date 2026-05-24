# Asset Output Rules

Ordinary visual asset candidates may include only these fields:

- `kind`
- `id`
- `title`
- `detail`
- `gallery_category`
- `asset_use`
- `actor_role`
- `certainty`
- `display_zone`
- `cache_policy`
- `asset_subtype`
- `asset_tags`
- `character_targets`
- `map_canvas`
- `map_route`

Do not output `asset_kind`, `source_type`, `path`, `url`, manifest keys, runtime cache keys, or file-system paths. The backend derives `asset_kind` only from `asset_use` and assigns `source_type` only after the asset is registered.

`gallery_category` controls only frontend filtering. It must be one of the core categories `prop`, `item`, `character`, `map`, `cg`, or a campaign-registered custom gallery category. Do not output `gallery_category=scene`.
Frontend filters are returned only from the campaign initialization asset contract, never generated from runtime asset `type`, `category`, or prose semantics. Do not output temporary categories such as `item_record`, `inventory_record`, or `dossier`.

`item` is something the player owns, can equip, can consume, or can track in inventory.
`prop` is a scene clue, mechanism, environmental object, non-portable object, or object not yet assigned to the player.
`asset_use` controls backend processing. Ordinary assets may use `portrait`, `item`, `prop`, or `map`. Scene, location, region, route, and map-like visual material must use `gallery_category=map` and `asset_use=map`.

`actor_role` controls story identity only. It must not be used to choose the frontend filter category.

`asset_tags` must be a string array only, such as `"asset_tags": ["clue", "map-linked"]`. Do not output tag objects with `id`, `label`, `icon`, or descriptions.

CG is not an ordinary asset-normalizer payload. CG requests go through the image-generation request / image_job path, and the successful image result is later registered as `gallery_category=cg`, `asset_use=cg`, and `asset_kind=cg_image`.

If any required ordinary-asset field is absent, the backend returns `asset_contract_error`. Do not compensate by changing the category, downgrading to review, inventing an actor role, or omitting the asset silently.

Actor-layer text prompts must not create new asset definitions. The actor layer may carry image-generation instructions in the image pass, but ordinary asset candidates belong to director/backend intent and backend registration.
