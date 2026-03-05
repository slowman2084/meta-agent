# Rubric生成助手 Changelog

## 2026-03-01 手动优化（提示词 + 理想态）

**问题**：输入 Schema 设计错误——`must_follow`、`nice_to_have`、`risk_notes` 等约束分析字段要求调用方预填，导致 Agent CoT 被绕过，输出非 JSON 格式 Rubric。

**修改内容**：

`prompt.md`：
- 输入章节：移除 `must_follow`、`nice_to_have`、`risk_notes`、`examples_optional` 字段，只保留 `task_name`、`input_spec`、`output_spec`、`agent_name`（可选）4 个字段，并明确标注调用方不应预填约束分析字段
- CoT 步骤：原步骤 B 改为 B（解读 input_spec）+ C（解读 output_spec）+ D（自主推导硬约束/加分项/风险点），后续步骤 E-K 顺延
- Few-shot 示例：两个示例的 INPUT 侧均移除约束分析字段，只保留 3 个核心字段；示例 1 保留完整 OUTPUT；示例 2 替换为 SQL 生成场景（更能体现可验证性 criterion 设计）

`ideal_state.md`：
- 重构为新格式（定位与核心价值 / 核心能力维度 / 输入输出规范 / 反模式 / 质量评估维度）
- 输入格式章节：重写为 4 字段简洁 JSON，增加"调用方不应该提供的字段"说明
- 新增反模式 4.1「外部注入约束」（最高优先级）：说明 must_follow/risk_notes 外部注入是反模式、原因及正确行为
- 新增质量评估维度表（Specific/Scaffolded/Justified/Actionable/Qualified/Refinable）

