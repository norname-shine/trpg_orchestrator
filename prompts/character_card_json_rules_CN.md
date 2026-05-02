# 角色卡 JSON 规则

当 V4 或 ChatGPT 需要返回、刷新或修复角色状态、玩家卡、伙伴卡，或前端可直接使用的角色数据时，使用本规则。

如果任务涉及角色状态，回复中必须包含 `character_card` JSON 对象。除非用户明确确认，或状态写回已经审核通过，否则不得覆盖长期事实。

## 顶层结构

```json
{
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

## 模式规则

- `strict_stats`：只有当前跑团已经确认明确数值时才能使用。每个数值字段必须能追溯到记忆、规则或已审核写回。
- `narrative_status`：当跑团没有严格数值时使用。用短标签、百分比和叙事状态描述，不要假装它是精确规则值。
- `auto`：允许用于生成记忆。前端会把已确认的数字 vitals / attributes 视为严格数值，否则按叙事状态处理。

## 三维状态 / Vitals

- `vitals` 不得写死为生命、专注、体力。
- 字段名由当前团类型和导演层数据决定。
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

- 六维属性由导演层统一给出，不得在前端写死字段名。
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
