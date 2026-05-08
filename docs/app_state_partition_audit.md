# app.js state 分区收敛记录

## 当前状态

`web/app.js` 已经按职责分为 `state.campaign`、`state.story`、`state.assets`、`state.gallery`、`state.map`、`state.character`、`state.writeback`、`state.job`、`state.ui`。

文件仍保留 `LEGACY_STATE_FIELDS` 和 `partitionLegacyState()`，用于把旧字段代理到新分区。它们是过渡保护，不再作为新代码访问口径。

## 本轮已收敛字段

本轮把以下旧字段直接访问改为分区访问：

- campaign：`campaigns`、`activeCampaign`、`selectedCampaign`、`frontendState`、`lastCampaignState`、`assetSeed`、`streamingPreview`
- assets：`assetCache`、`cachedAssets`、`modulePayloadCache`、`visualContracts`、`canvasRules`
- gallery：`galleryAssets`、`galleryFilter`、`galleryFilterIds`、`galleryTaxonomy`、`selectedGalleryKey`、`transientGalleryAsset`
- map：`renderedMapKey`、`currentMapAsset`
- story：`currentPressurePack`、`storyProgressPayload`、`storyProgressChapter`、`storyProgressNode`
- character：`characterProfileExpanded`、`characterProfileCampaign`、`latestInventoryPayload`、`latestDossierPayload`
- writeback：`writebackReview`
- job：`runProgress`、`polling`、`lastJobRunning`
- ui：`sideTab`、`activePanel`、`autoScroll`、`collapsedPanels`、`dragPanels`、`activeDragPanel`、`activeReferenceDrag`、`ruleFiles`、`selectedRule`

同时新增只读 helper：

- `currentAssetCache()`
- `currentModulePayloadCache()`
- `currentUiState()`
- `currentStoryState()`

## 仍保留 legacy proxy 的原因

`LEGACY_STATE_FIELDS` 仍用于兼容旧调用路径，避免遗漏的旧入口或浏览器缓存中的旧脚本直接崩溃。新代码应继续使用分区字段；legacy proxy 暂时只作为兼容保护保留，等连续几轮源码检查和前端验证都确认无旧字段直接访问后，再评估删除。

## campaign 切换时清理的状态

`resetCampaignScopedUiState()` 只清理 campaign 相关缓存和渲染产物：

- `map.renderedMapKey`
- `map.currentMapAsset`
- `assets.assetCache`
- `assets.cachedAssets`
- `assets.visualContracts`
- `assets.modulePayloadCache`
- `gallery.galleryAssets`
- `gallery.selectedGalleryKey`
- `gallery.transientGalleryAsset`
- `story.currentPressurePack`
- `story.storyProgressPayload`
- `story.storyProgressChapter`
- `story.storyProgressNode`
- `character.latestInventoryPayload`
- `character.latestDossierPayload`

## 不应在 campaign 切换时清理的 UI 偏好

以下 UI 偏好不应在 campaign 切换时清理：

- `ui.collapsedPanels`
- `ui.dragPanels`
- `ui.sideTab`
- `ui.activePanel`
- `ui.autoScroll`

## 下一轮建议

1. 继续检查未纳入本轮的 legacy proxy 字段，例如 `storyTurnsByCampaign`、`storyTurnSignatures` 和其他 character 辅助状态。
2. 把 gallery/map 相关渲染逻辑周边的 state 访问收口到少量局部 helper，便于后续拆组件。
3. 在确认一到两轮无旧字段直接访问后，评估删除 legacy proxy 的时机。
