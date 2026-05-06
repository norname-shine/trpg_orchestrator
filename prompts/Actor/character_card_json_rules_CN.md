# 角色卡 JSON 规则

当需要初始化、返回、刷新或修复角色状态、玩家卡、伙伴卡，或前端可直接使用的角色数据时，使用本规则。正文输出不参与角色数值变化判定。

如果任务涉及角色状态，回复中必须包含 `character_card` JSON 对象。除非用户明确确认，或状态写回已经审核通过，否则不得覆盖长期事实。

## 生命周期与固定触发状态

角色卡 JSON 存在两种固定触发更新的状态。两者都必须全程本地缓存、前端与本地运行时联动刷新，且逻辑统一可复用，适配所有类型跑团。

### 一、开局生成初始化角色卡

- 新建跑团、开局拟定完人物设定后，系统自动生成完整 `character_card` JSON 结构化属性数据。
- 生成后的角色卡自动做本地持久缓存，作为本局初始角色基底数据。
- 前台直接加载缓存 JSON 渲染叙事卡、三维状态、六维属性、标签、成长进度、进度条、伙伴卡等模块。
- 初始化缓存是后续状态控制更新的基线。除非玩家明确要求重建角色，否则不得从正文重新生成覆盖。

### 二、游戏对局中动态更新角色卡

- 对局流程里，只有状态控制流程可以判断角色三维属性、六维数值、状态优势、标签特质、成长进度或伙伴状态是否发生变更。
- 如果判定有属性变动，输出新版 `character_card` JSON，或兼容的角色卡 patch。
- 运行时把新 JSON 下发到前端。
- 前端接收后覆盖当前跑团本地角色卡缓存。
- 页面所有角色卡 UI 自动刷新：进度条、三维状态、六维图、状态标签、成长进度、伙伴数据和头像 metadata 同步渲染最新状态。
- 正文可以演绎后果，但不能自行决定数值或结构化角色卡变更。

### 固定链路

永远遵循：

1. 初始化缓存角色卡
2. 对局中由状态控制流程判定角色变更
3. 状态控制流程输出新 JSON
4. 运行时下发 JSON
5. 前端覆写本地缓存
6. 前端刷新角色卡 UI

这条链路必须被 COC、DnD、Fate、怪物团和原创团复用。核心逻辑不得按团类型写死字段。

## 顶层结构

```json
{
  "character_card_update": {
    "trigger": "initial_generation | v4_runtime_update",
    "changed": true,
    "cache_action": "create_initial_cache | overwrite_campaign_cache | no_change",
    "reason": ""
  },
  "character_card": {
    "mode": "auto | strict_stats | narrative_status",
    "identity": {
      "name": "",
      "gender": "",
      "age": "",
      "ancestry": "",
      "origin": "",
      "class_or_role": "",
      "level_or_stage": "",
      "motivation": "",
      "personality": "",
      "weakness": "",
      "companion": ""
    },
    "visual_seed": "",
    "progression": {
      "label": "",
      "current": null,
      "max": null,
      "percent": null,
      "text": ""
    },
    "vitals": [],
    "conditions": [],
    "attributes": [],
    "equipment": [],
    "companion": {
      "name": "",
      "kind": "",
      "archetype": "",
      "species": "",
      "personality": "",
      "visual_seed": "",
      "vitals": [],
      "conditions": [],
      "equipment": []
    }
  }
}
```

## 更新元信息

- `character_card_update.trigger` 必须说明本次为什么返回角色卡。
- `initial_generation` 只用于新建跑团后的开局人物设定。
- `v4_runtime_update` 只用于对局事件已经改变角色状态的情况。
- 开局基线使用 `cache_action: create_initial_cache`，确认的对局更新使用 `overwrite_campaign_cache`。
- 如果检查后判定角色卡无需更新，返回 `changed: false` 与 `cache_action: no_change`，不要为了复述旧数据而输出新角色卡。
- 运行时必须按 campaign ID / seed 分开存储角色卡缓存。不同跑团之间不得共用角色卡缓存。

## 模式规则

- `strict_stats`：只有当前跑团已经确认明确数值时才能使用。每个数值字段必须能追溯到记忆、规则或已审核写回。
- `narrative_status`：当跑团没有严格数值时使用。用短标签、百分比和叙事状态描述，不要假装它是精确规则值。
- `auto`：允许用于生成记忆。前端会把已确认的数字 vitals / attributes 视为严格数值，否则按叙事状态处理。

## 三维状态 / Vitals

- `vitals` 不得写死为生命、专注、体力。
- 字段名由当前团类型和状态控制数据决定。
- 每个条目建议包含：
  - `key`
  - `label`
  - `current`
  - `max`
  - `percent`
  - `state`
  - `tone`
- 前端使用双层进度条：底层表示总量，上层表示当前值。

## 六维属性 / Attributes

- 六维属性由状态控制数据统一给出，不得在前端写死字段名。
- 每个条目建议包含：
  - `key`
  - `label`
  - `short`
  - `value`
  - `max`
  - `text`
- `short` 可以是 2 到 3 个字或短缩写，用于六芒星图展示。
- 如果当前团不使用严格数值，可以用百分比或叙事等级模拟展示。

## 标签 / Conditions

- `conditions` 本质是状态标签。
- 标签内容随跑团类型变化，例如伤势、恐惧、令咒、异常同步、疲劳、任务压力、灵感、资源紧张等。
- 标签必须短，适合角色卡展示。
- 不要把未经确认的推测写成已确认标签。

## 伙伴 / Companion

- 伙伴不是固定种类。
- 怪物猎人团可以是 `palico`，Fate 团可以是 `servant`，根据团类型划分，COC或者DND这种不需要伙伴身份的就不生成伙伴。
- 伙伴卡必须独立于 NPC 档案，因为伙伴会随剧情推进更新能力、伤势、信任、契约或隐藏身份。
- 伙伴头像使用 `companion` 或 `companion_portrait` 资产，不得混入 NPC 头像。

## 写回边界

- 角色卡可以反映本回合已经发生且可确认的状态。
- 未确认推测放入不确定字段或短期状态，不得写入长期事实。
- 如果角色卡会覆盖既有长期设定，必须经过审核写回。
- 角色属性变更决策权只归状态控制流程。
- 正文输出只负责剧情演绎，不参与属性数值修改判定。
