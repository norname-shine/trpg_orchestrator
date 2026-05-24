# 迁移计划草案

## 阶段一：协议收敛

- 从资产 contract 中移除 `display_zones`、`certainty_values`、`source_types`。
- 将 `map` 和 `cg` 从普通 gallery category 中拆出。
- 明确普通资产只保留 `item / prop / character`。
- 固定分类和自定义分类进入同一个本地资产分类系统。
- 自定义分类由团类型和本地资产流生成，只允许本团专属资料维度，不允许地点、章节、角色、地图、物品的同义词。

## 阶段二：新增本地 registry

- 新增 `asset_registry.json`。
- 新增 `map_registry.json`。
- 新增 `cg_registry.json`。
- 新增或整理 `clue_history.json` 作为线索本地数据入口。线索不是资产，只有升级后才进入资产层。
- 新增 `player_asset.json`、`companion_assets.json`、`npc_assets.json`。三者使用同一角色资产骨架，但不放在同一个文件中。
- 将 `player_state.json.character_card`、`companion_profiles.json`、`npc_profiles.json`、`npc_memory.json` 纳入角色资产引用。
- 将 `story_blueprint.json` 和 `story_progress.json` 纳入故事结构资产引用，不重造故事大纲结构。

## 阶段三：数据流迁移

- 初始化时写入 registry，而不是只写 `gallery_raw`。
- 初始化时生成主玩家资产、副玩家资产、初始 NPC 种子资产和故事结构资产引用。
- 剧情回合更新时由 LLM 返回变更建议，本地代码负责合并 registry。
- 前台资产层从 `asset_registry` 派生，本地存在的资产本体应当可见。
- 物品状态长期保存在本地；如果故事没有更新物品状态，且玩家没有请求查看或更新物品状态，前端不主动显示状态详情。
- 请求大模型时不注入完整 registry 文件，只注入由本地代码生成的摘要，包含已有资产、类型、归属和必要状态。
- 请求大模型时按角色规格注入：主玩家最高、副玩家次之、普通 NPC 简化、隐藏角色/BOSS/关键特殊角色提高规格。
- 主玩家上下文不注入系统固化个性，只注入身份、状态、经历、属性和玩家确认信息。
- 副玩家必须注入稳定个性和关系倾向。
- 普通 NPC 只注入必要动机、关系、状态和语气；特殊 NPC/BOSS 才注入高规格个性。
- 左侧地图从 `map_registry` 派生。
- CG 视图从 `cg_registry` 派生。

## 阶段四：清理旧逻辑

- 机械清理旧 `display_zone` 判断。
- 机械清理 `certainty=clue/uncertain` 进入资产夹的路径。
- 机械清理 `source_type` 作为业务判断的路径。
- 更新后台测试、前台测试、初始化 prompt、导演层 prompt。

## 风险点

- 当前前端和资产保存层大量读取 `display_zone`，不能直接删除。
- `assets/manifest.json` 仍需要保存渲染来源，但这是渲染层字段，不应上升到资产业务协议。
- 旧团存档需要迁移脚本，否则会出现新旧协议混读。
