# Asset Cache Lifecycle Rules

These rules govern local PNG cache files for maps, portraits, items, and clues.

## Manifest

- Each campaign stores cached assets under `campaigns/<campaign_id>/assets/`.
- The manifest is `campaigns/<campaign_id>/assets/manifest.json`.
- Manifest entries should include:
  - `key`
  - `path`
  - `kind`
  - `seed`
  - `style`
  - `generator_version`
  - `created_at`
  - optional `metadata`

## Versioning

- The frontend constant `ASSET_GENERATOR_VERSION` controls cache invalidation.
- Increment the version when drawing logic changes in a way that should replace existing images.
- Do not regenerate visible maps during normal polling when the campaign id, object id, and version have not changed.

## Rebuild And Delete

- `/api/rebuild-assets` may remove cached PNGs and matching manifest entries.
- `DELETE /api/asset` may remove one cached PNG and its manifest entry.
- These operations must never edit campaign memory, logs, prompts, or state writeback.
- Only PNG files inside the selected campaign's `assets` directory may be removed.

## Metadata

- Metadata should preserve the frontend meaning of an asset:
  - `title`
  - `detail`
  - `meta`
  - `source`
  - `object_id`
- If metadata is missing, the UI may still display the asset using the manifest key and kind.
