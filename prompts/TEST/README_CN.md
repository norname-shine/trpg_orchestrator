# TEST Prompt 中文包

这个文件夹用于放置 V4 / GPT 的测试版 Prompt 文档。

这些文档不会被 `prompt_modules.json` 引用，也不会影响当前正在运行的跑团服务。它们只用于人工复制、调试输出、评审结构和后续合并。

## 文件说明

- `v4_campaign_setup_prompt_TEST_CN.md`
  - V4 创团初始化测试 Prompt。
  - 重点：故事背景、主角资料、伙伴资料、章节大纲、节点、beat、公开等待提示。
- `v4_director_turn_prompt_TEST_CN.md`
  - V4 正式回合导演层测试 Prompt。
  - 重点：压力包、结构化进度、物品语义、地图/视觉触发、公开 THINK 等待体验。
- `chatgpt_actor_prompt_TEST_CN.md`
  - GPT 演员层测试 Prompt。
  - 重点：玩家可见正文、JSON 输出、progress writeback、不要抢导演层决策。

## 使用方式

1. 选择一个测试 Prompt。
2. 复制给对应模型作为系统/开发指令。
3. 再复制 `examples/` 下的输入样例。
4. 对照 `expected_shape_*.md` 检查输出结构。

这些文件是测试包，不是正式运行规则。确认效果后，再单独决定是否合并进正式 Prompt。
