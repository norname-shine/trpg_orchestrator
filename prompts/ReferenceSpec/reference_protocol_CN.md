# Prompt 引用规范

本文件夹定义 Prompt 文件的引用位置、注入方式和维护规则。

## 引用位置

- 运行时模块引用位于 `prompts/prompt_modules.json`。
- 人类维护的层级引用位于 `prompts/prompt_rules_index.md` 和各层 `INDEX.md`。
- 双语成对状态位于 `prompts/prompt_language_sync.json`。
- 代码可以按文件名请求 Prompt；`read_prompt()` 会先解析根路径，再递归搜索子目录。

## 引用方式

- 使用相对 `prompts/` 的路径，例如 `Actor/chatgpt_host_prompt.md`。
- 英文文件与 `_CN.md` 中文文件必须位于同一目录。
- 新文档或 JSON 不得继续引用已经移动的根目录旧路径。
- 运行时注入的 Prompt 必须在 `prompt_modules.json` 中声明准确路径。

## 更新规则

- 移动 Prompt 文件时，同步更新 `prompt_modules.json`、`prompt_rules_index.json`、主索引和目标层 `INDEX.md`。
- 修改双语 Prompt 的一侧时，必须同步修改同目录的另一侧。
- Prompt 修改后运行 `sync-prompts --apply`、`sync-prompts --check` 和 `validate-encoding`。

