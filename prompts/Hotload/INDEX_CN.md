# 热更新 Prompt 索引

热更新文件支持运行时 Prompt 选择、能力注入、输出契约和演员层输入裁剪。

## 运行时模块

- `lazy_context_rules.md`：导演/审计懒加载上下文。
- `output_contract_rules.md`：导演/审计输出契约边界。

## 演员层裁剪归档

- `actor_prompt_pruned_fields.md`：演员层 Prompt 裁剪策略和无裁决权清单。

## Prompt 根目录机器文件

- `../prompt_modules.json`：运行时模块注册表。
- `../prompt_rules_index.json`：机器可读层级索引。
- `../prompt_language_sync.json`：双语 Prompt 同步基线。

## 引用规则

- 演员层 Prompt 接收精简可见能力、当前剧情位置、场景简报，以及允许的证据/检定区域。
- 原始 `Capability Plan`、`Scene Control Pack`、路由元数据、debug 字段和空占位不进入演员层剧情 Prompt。

