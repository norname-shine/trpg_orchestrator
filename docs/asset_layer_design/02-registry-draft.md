# Registry 草案

## asset_registry.json

普通资产总账，保存 `item / prop / character` 中可进入资产层的普通资产，并引用故事结构。主玩家、副玩家、NPC 使用同骨架但分文件保存，不塞进同一个资产总账文件。

建议字段：

```jsonc
{
  "schema": "trpg.asset_registry.v1", // 协议版本
  "campaign_id": "", // 跑团 ID
  "updated_turn": 0, // 更新回合
  "taxonomy": { // 分类体系
    "core_categories": ["item", "prop", "character"], // 固定分类
    "custom_categories": [] // 本团自定义分类
  },
  "assets": [], // 普通资产列表，不含主玩家和副玩家
  "story_assets": {} // 故事结构资产引用
}
```

`taxonomy` 同时保存固定分类和本团自定义分类。自定义分类由初始化或剧情分发时根据团类型生成，数量保持 0-3 个。它属于本地资产流的一部分，不再作为孤立的前台筛选补丁存在。

单个普通资产建议字段：

```jsonc
{
  "id": "", // 资产唯一 ID
  "type": "item", // 资产类型
  "title": "", // 显示名称
  "summary": "", // 摘要
  "origin": { // 来源信息
    "phase": "initialization", // 产生阶段
    "turn": 0, // 产生或更新回合
    "source": "director_setup" // 来源
  },
  "status": "", // 当前状态摘要
  "ownership": { // 归属信息
    "kind": "player_owned", // 归属类型
    "owner_id": "" // 归属对象 ID
  },
  "visibility": { // 可见性
    "asset_layer": true, // 资产层可见
    "gallery": true, // 右侧资产夹可见
    "character_card": false // 角色卡可见
  },
  "links": { // 关联信息
    "inventory_item_id": "", // 物品状态 ID
    "visual_contract_key": "", // 视觉契约 key
    "render_asset_key": "" // 渲染产物 key
  },
  "canvas_spec": {} // Canvas 绘制协议
}
```

`origin.phase` 用于标记资产来源，例如：

- `initialization`：初始化内容。
- `story_update`：剧情推进确认的新资产。
- `player_requested_update`：玩家请求查看或更新后产生的资产状态变化。

资产本体进入 `asset_registry` 后，应当能在前端资产层看到。物品状态详情是否展示，由本轮模块请求和状态更新事件决定。资产总账不直接给 LLM；需要请求模型时，由本地代码整理成摘要。

## LLM 摘要

LLM 只读取摘要，不读取完整 registry 文件。

```jsonc
{
  "schema": "trpg.asset_digest.v1", // 协议版本
  "campaign_id": "", // 跑团 ID
  "turn": 0, // 当前回合
  "asset_summary": [], // 普通资产摘要
  "player_summary": {}, // 主玩家摘要
  "companion_summary": [], // 副玩家摘要
  "npc_summary": [], // NPC 摘要
  "clue_summary": [] // 线索摘要
}
```

## 前端派生视图

前端数据建议从 registry 派生，而不是直接读取所有本地资产：

```jsonc
{
  "schema": "trpg.asset_view.v1", // 协议版本
  "campaign_id": "", // 跑团 ID
  "turn": 0, // 当前回合
  "requested_modules": [], // 本回合请求模块
  "gallery_assets": [], // 资产层/资产夹资产
  "inventory_updates": [], // 物品状态更新
  "character_assets": [] // 角色资产
}
```

如果本轮没有请求或更新物品状态，`inventory_updates` 可以为空；但 `gallery_assets` 或资产层视图仍可包含这些已存在资产本体。

## 角色资产骨架

主玩家、副玩家和 NPC 使用同一类角色资产骨架，但规格不同，并且分文件保存。

建议文件：

```jsonc
{
  "player_asset_ref": "player_asset.json", // 主玩家资产文件
  "companion_assets_ref": "companion_assets.json", // 副玩家资产文件
  "npc_assets_ref": "npc_assets.json" // NPC 资产文件
}
```

```jsonc
{
  "id": "", // 角色资产唯一 ID
  "type": "character", // 资产类型
  "role": "player", // 角色身份
  "tier": "player", // 规格层级
  "title": "", // 显示名称
  "identity": {}, // 身份信息
  "profile": {}, // 角色资料
  "personality": {}, // 个性信息
  "memory_refs": [], // 记忆引用
  "visual": { // 视觉信息
    "visual_contract_key": "", // 视觉契约 key
    "portrait_asset_key": "" // 头像/立绘资产 key
  }
}
```

`tier` 建议值：

- `player`：主玩家，规格最高。
- `companion`：副玩家/伙伴，规格次之。
- `npc`：普通 NPC，规格较简。
- `special_npc`：隐藏角色、BOSS、关键特殊角色，规格高于普通 NPC。

角色资产不保存 `stats`、`status`、`relationships` 等运行态字段。主玩家的属性状态沿用 `player_state.json.character_card`；副玩家和 NPC 的状态或关系如需长期记录，应留在各自 profile/memory 文件，不放进角色资产骨架。

个性字段规则：

- `player`：不固化系统个性。`personality` 应为空或只保存玩家明确确认的公开标签。
- `companion`：必须保存稳定个性，包括性格、说话方式、关系倾向、长期变化。
- `npc`：默认简化，只保存必要语气、动机和关系，不强制完整个性。
- `special_npc`：保存高规格个性，可接近副玩家规格。

字段来源：

- 主玩家引用 `player_state.json.character_card`。
- 副玩家引用 `companion_profiles.json` 和前端 `companion_card` 派生结构。
- NPC 引用 `npc_profiles.json`、`npc_memory.json` 和 `visual_contracts.json`。

## clue_history.json

线索是本地数据，但不是资产。线索不进入资产夹，也不进入 `asset_registry.assets`。

```jsonc
{
  "schema": "trpg.clue_history.v1", // 协议版本
  "campaign_id": "", // 跑团 ID
  "updated_turn": 0, // 更新回合
  "clues": [] // 线索列表
}
```

单个线索：

```jsonc
{
  "id": "", // 线索唯一 ID
  "title": "", // 线索名称
  "summary": "", // 线索摘要
  "source_turn": 0, // 出现回合
  "source_text": "", // 来源文本
  "status": "open", // 线索状态
  "upgrade": { // 升级信息
    "upgraded": false, // 是否已升级为资产
    "asset_id": "", // 升级后的资产 ID
    "asset_type": "" // 升级后的资产类型
  }
}
```

不是所有线索都会升级为资产。只有剧情确认、玩家验证或系统判定需要长期展示时，线索才升级为 `item` 或 `prop` 等正式资产。

## story_assets

故事大纲作为结构资产引用现有代码结构。

```jsonc
{
  "story_assets": { // 故事结构资产引用
    "blueprint_ref": "story_blueprint.json", // 故事大纲文件引用
    "progress_ref": "story_progress.json", // 故事进度文件引用
    "current_chapter_id": "", // 当前章节 ID
    "current_node_id": "" // 当前剧情节点 ID
  }
}
```

`story_blueprint.json` 与 `story_progress.json` 不需要重写。资产层只建立引用和摘要，具体校验、进度计算继续沿用现有 `story_progress.py`。

## map_registry.json

地图本体和地图历史。

建议字段：

```jsonc
{
  "schema": "trpg.map_registry.v1", // 协议版本
  "campaign_id": "", // 跑团 ID
  "current_map_id": "", // 当前地图 ID
  "maps": {} // 地图记录
}
```

地图记录保存 `trpg.map_asset_protocol.v1`，并维护当前地图、历史地图和渲染缓存的关系。

## cg_registry.json

CG 生成记录和展示记录。

建议字段：

```jsonc
{
  "schema": "trpg.cg_registry.v1", // 协议版本
  "campaign_id": "", // 跑团 ID
  "records": [] // CG 记录
}
```

CG 记录应保存触发原因、剧情位置、生图任务、生成结果，不进入普通资产分类。
