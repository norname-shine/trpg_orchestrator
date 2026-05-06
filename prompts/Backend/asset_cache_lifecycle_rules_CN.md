# 资产缓存生命周期规则

本规则约束地图、头像、物品和线索等本地 PNG 缓存文件。它属于 Codex 本地工程层规则，不应注入 ChatGPT 演员层。

## Manifest

- 每个跑团的缓存资产保存在 `campaigns/<campaign_id>/assets/`。
- 清单文件为 `campaigns/<campaign_id>/assets/manifest.json`。
- manifest 条目应包含：
  - `key`
  - `path`
  - `kind`
  - `seed`
  - `style`
  - `generator_version`
  - `created_at`
  - 可选 `metadata`

## 版本控制

- 前端常量 `ASSET_GENERATOR_VERSION` 控制缓存失效。
- 当绘制逻辑变化，并且旧图需要被替换时，必须递增版本号。
- 普通轮询时，如果 campaign id、object id 和 generator version 没有变化，不要重复生成可见地图。

## 重建与删除

- `/api/rebuild-assets` 可以删除缓存 PNG 和对应 manifest 条目。
- `DELETE /api/asset` 可以删除单个缓存 PNG 及其 manifest 条目。
- 这些操作绝不能修改 campaign memory、logs、prompts 或 state writeback。
- 只能删除当前选中跑团 `assets` 目录内的 PNG 文件。

## Metadata

- metadata 应保留资产在前端中的语义：
  - `title`
  - `detail`
  - `meta`
  - `source`
  - `object_id`
- 如果 metadata 缺失，UI 仍可使用 manifest key 和 kind 展示资产。

## 职责边界

- V4 只判断是否需要视觉提示和地图更新。
- ChatGPT 不负责本地 Canvas、PNG 缓存或 manifest。
- Codex / 前端负责根据结构化数据生成、复用、删除和重建缓存资产。
