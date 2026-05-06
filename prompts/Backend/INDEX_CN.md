# 后台层 Prompt 索引

后台层 Prompt 文档定义本地工程、前端、持久化、编码、资产和 QA 行为。它们不注入演员层正文回合。

## 架构与边界

- `codex_system_architecture_rules.md`：本地系统架构。
- `model_layer_contract_rules.md`：模型层职责边界。
- `codex_computer_use_prompt.md`：浏览器自动化边界。

## 运行时安全与体验

- `encoding_rules.md`：UTF-8 与双语 Prompt 策略。
- `campaign_data_lifecycle_rules.md`：跑团持久化生命周期。
- `frontend_interaction_rules.md`：前端展示与交互规则。

## 资产与 QA

- `asset_cache_lifecycle_rules.md`：资产缓存生命周期。
- `canvas_asset_generation_rules.md`：本地 Canvas 资产生成。
- `gallery_asset_rules.md`：图库分类与卡片策略。
- `ai_flavor_check_rules.md`：正文 QA 与重写触发。

## 引用规则

- 后台规则可以提及本地文件、缓存、渲染、自动化和校验。
- 不得把后台实现规则注入演员层剧情 Prompt。
- `_CN.md` 中文包必须与英文文件放在同一目录。

