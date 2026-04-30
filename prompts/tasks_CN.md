# TRPG 自动主持任务清单

## 一、目前已完成任务

### 基础跑团链路

- 已建立本地 `trpg_orchestrator` 项目结构。
- 已支持多跑团注册表 `campaign_registry.json`。
- 已支持 `active_campaign` 读取与切换。
- 已支持本地记忆 JSON 读取、备份、写入。
- 已支持 DeepSeek 导演层压力包生成。
- 已支持 ChatGPT 网页客户端输入生成与网页自动发送 / 抓取。
- 已支持 ChatGPT 输出解析：
  - 正文
  - 选择点
  - 回合摘要
  - 状态回写
- 已支持 AI 味机械检查。
- 已支持 V4 状态回写审核。
- 已支持完整日志保存。

### 前端控制台

- 已建立本地 Web 控制台。
- 已支持玩家行动输入。
- 已支持运行一回合、只生成输入、发送到 ChatGPT、抓取回复、解析写回、执行重写。
- 已支持顶部状态、跑团切换、正文展示、选择展示、导演信息、日志、摘要。
- 已支持右侧资料夹展示。
- 已支持资料夹筛选：
  - 全部
  - 怪物 / 生态
  - NPC
  - 场景
  - 物品
- 已支持资料夹弹窗查看详情。
- 已支持 NPC / 物品引用到行动输入。
- 已把“规则”查看入口放到页面右上角。
- 已移除用户侧删除素材、重建缓存素材入口。

### Canvas / PNG 可视化

- 已支持本地 Canvas 生成区域地图、头像、物品图标、怪物 / 生态线索图标。
- 区域地图可缓存为 PNG。
- 左侧区域地图以 16:9 图片展示。
- 普通刷新不会重复重绘同一张地图。
- NPC 头像已做差异化。
- 地图文字已增大，适合小框展示。
- 资料夹素材缓存已接入 `/api/assets`。

### 规则与接口

- 已新增规则读取接口：
  - `GET /api/rules`
  - `GET /api/rules?name=<规则文件名>`
- 已新增素材接口：
  - `GET /api/assets`
  - `GET /api/asset`
  - `POST /api/asset`
- 后端保留开发用素材删除 / 重建接口，但前端不暴露给用户。
- 已新增状态回写审核接口：
  - `GET /api/writeback-review`
  - `POST /api/audit-writeback`
  - `POST /api/apply-writeback`
- 已新增跑团管理接口：
  - `POST /api/init-campaign`
  - `POST /api/set-chatgpt-binding`
- 已把跑团新建和固定对话绑定放入“选择跑团故事”弹窗。

### V4 visual_assets / map_route 协议

- V4 压力包已新增：
  - `visual_assets`
  - `map_route`
- schema 已校验这两个字段。
- 离线开发压力包已补空结构。
- 前端地图已读取 `map_route.nodes / markers / title`。
- 资料夹已读取 `pressure_pack.visual_assets` 并转成可视资产卡片。

## 二、待建任务

### 高优先级

- 状态回写 UI 继续优化：
  - 显示旧记忆与新记忆差异。
  - 对 `accept / revise / reject` 使用更明显的视觉状态。
  - 对 V4 修正版与 ChatGPT 原始回写做并排对比。
- 跑团设置继续完善：
  - 支持编辑 campaign_profile 基础字段。
  - 支持查看当前绑定的 Project / 固定对话安全提示。
  - 支持跑团归档 / 恢复，但不删除跑团。
- visual_assets / map_route 深接入：
  - V4 输出视觉提示后，前端优先使用结构化路线，而不是文本推断。
  - 为地图节点、路线、阻断、线索、危险分别绘制不同样式。
  - 支持把视觉提示缓存 metadata 写入 manifest。

### 中优先级

- 完整导出：
  - 导出记忆 JSON。
  - 导出日志。
  - 导出 outbox。
  - 导出素材 PNG。
- 记忆报告 UI：
  - 当前各记忆文件条目数。
  - 最近写入摘要。
  - 未确认内容列表。
  - 可压缩建议。
- 跑团初始化模板：
  - 原创奇幻
  - 现代悬疑
  - 怪猎风格
  - 末日
  - 科幻
  - Fate 风格
- 规则浏览 UI：
  - 规则目录。
  - 单文件查看。
  - 搜索规则关键词。

### 低优先级

- 前端截图导出。
- 素材调试模式。
- 本地 Git 同步按钮。
- 更多 Canvas 图标类型。
- 移动端布局进一步优化。
