

## [格式调整] 输出格式从 JSON 改为 YAML

**时间：** 2026-03-10
**操作类型：** 提示词修改（非优化迭代，仅格式调整）
**修改原因：** 统一 testcases.yaml 中 Judge 字段的格式规范，便于直接填充
**具体变更：**
- 将输出格式从 JSON (`{"rubrics": [...]}`) 改为 YAML 列表格式
- 移除 `case_id` 和 `input_fingerprint` 字段（由调用方管理）
- 更新 Few-Shot 示例为 YAML 格式
- 更新异常处理的错误输出为 YAML 格式
- 同步更新 `ideal_state.md` 的数据结构说明

**影响范围：**
- 调用方需适配新的 YAML 输出解析（直接作为列表项追加到 testcases.yaml 的 Judge 字段）
- 核心评分逻辑、原子化原则、MECE 框架均保持不变

---

## Iteration 5.5 Optimization Log (2026-03-05)

**Major Enhancement: Tool-Assisted CoT & Context Control**

**Problem Diagnosis:**
User feedback indicated that internal CoT (just prompting the LLM to "think") is fragile and often skips steps or lacks specific knowledge (e.g., missing specific medical myths). The user requested a "Skill"-based design to enforce context control.

**Optimization Strategy:**
1.  **New Skill (`rubric_tools`)**: Created a Python module with two powerful tools:
    *   `retrieve_domain_context(domain, keywords)`: Injects specific domain risks (e.g., "Aspirin for kids", "SQL Injection") into the context *before* generation.
    *   `validate_rubric_draft(json)`: Programmatically checks for MECE coverage (Positive + Negative) and structural integrity *after* generation but *before* final output.
2.  **Prompt Refactoring**:
    *   Changed the workflow from a linear "Think -> Generate" to a "Analyze -> **Tool Call (Context)** -> Draft -> **Tool Call (Validate)** -> Finalize" loop.
    *   This forces the agent to explicitly consult external knowledge and perform self-correction.

**Key Changes:**
- **Added**: `source/meta-rubric-gen/skills/rubric_tools.py`
- **Updated**: `source/meta-rubric-gen/agent.json` (registered skill)
- **Updated**: `source/meta-rubric-gen/prompt.md` (enforced tool usage instructions)

## [优化] DSPy 自动优化 (第 N 轮)

**优化时间:** 2026-03-06T10:59:50.104171
**优化器:** bootstrap
**Few-Shot 示例数:** 0
**训练集大小:** 4
**评估阈值:** 80.0

**优化说明:**
- 使用 DSPy bootstrap 优化器自动选择最佳 Few-Shot 示例
- 自动生成推理链 (Chain-of-Thought)
- 基于测试用例数据驱动优化

## [优化] 迭代完成 (第 4 轮)

**完成时间:** 2026-03-07T22:45:10
**最终评分:** 96.0
**关键突破:**
- **原子化评分 (Atomic Rubrics)**: 成功从生成“评估维度”转型为“原子化检查点”，实现了医学事实（数值、禁忌、步骤）的直接判定。
- **负向约束机制**: 强制要求生成针对幻觉、严重错误及违规建议的负向评分项（-15 到 -30 分），显著提升了 Rubric 体系的安全性。
- **认知冷启动与隔离**: 通过强化的“任务指纹锚定”和“无记忆推理协议”，彻底解决了长文本生成中的“上下文污染”问题。

**后续建议:**
- 在更大规模的测试集上运行，验证分值权重的稳定性。
- 增加对“代码生成”等非医疗任务的复杂案例测试，进一步巩固通用性。

---

## 本次优化说明（第 4 轮）

**问题诊断：**
1. **任务漂移与缓存污染（内因/动力因缺失）**：在批量处理模式下，Agent 在 Case 15-19 发生了严重的“认知惯性”，完全重复了前序案例的输出。这表明现有的“无记忆协议”不足以对抗 LLM 的长文本自回归倾向。
2. **原子化颗粒度缺失（内因/形式因缺失）**：Agent 习惯生成“评估维度描述”（如：准确性），而非“原子化检查点”（如：是否提到按压深度为 5-6cm）。
3. **负向约束缺失（内因/目的因缺失）**：Rubric 体系中缺乏对严重错误、幻觉或违规操作的惩罚项（Negative Constraints），导致评估标准不够全面。

**CoT 抽象结论：**
- **原子化原则**：Rubric 必须是“判定式”而非“描述式”。好的 Rubric 应该让判卷者只需回答“Yes/No”，而不是进行二次主观判断。
- **事实优先原则**：在生成标准前，必须先提取任务背景下的“硬事实/行业标准”（Domain Facts），作为原子化条目的基石。
- **认知阻断机制**：通过强制提取并对比“任务指纹”，建立每一轮任务的认知边界，防止跨案例的信息渗漏。

**优化策略：**
1. **Schema 原子化重构**：将 `dimension/description` 结构合并为 `criterion`。明确要求 `criterion` 必须是包含具体数值或事实的原子判定句。
2. **强制负向评分项**：在核心行为准则中规定每个 Rubric 组必须包含至少 1-2 个负向惩罚项（`type: negative`）。
3. **事实先导型思考框架**：在 `<thinking>` 中增加“Fact-First Benchmarking”步骤，强制 Agent 先列举领域事实（如医疗指南数值、代码安全规范），再生成条目。
4. **强化上下文隔离**：引入“冷启动（Cold Start）”协议，要求在 JSON 输出中包含 `input_fingerprint` 以验证任务匹配度，并增加严厉的隔离指令。

**改动范围：**
- **思考框架**：重构为：指纹锁定 -> 事实提取 -> 原子化转化 -> 负向建模 -> 一致性校验。
- **输出格式**：更新 JSON Schema，使用 `criterion` 字段，并规范分值（正向加分，负向扣分）。
- **行为准则**：新增“原子化判定”和“负向约束”强制性条款。

**本轮优化方向标签：** CoT框架 / 输出格式 / 隔离增强

---

## 本次优化说明（第 3 轮）

**问题诊断：**
1. **上下文隔离失效（内因/动力因缺失）**：在批量任务流中，Agent 倾向于维持对话连贯性，导致前序 Case 的逻辑或关键词由于“惯性”侵入当前任务。
2. **输入端污染处理不足（外因/质料因缺失）**：当输入中混杂了历史记录或无关上下文时，Agent 缺乏“主动免疫”机制来识别并丢弃非当前任务信息。

**优化策略：**
1. **引入“认知冷启动”指令**：在提示词开头强制执行无记忆推理，声明每一轮任务都是独立存在的平行时空。
2. **实施“主体指纹锚定（Subject Fingerprinting）”**：在 `<thinking>` 模块的第一步，强制提取 `Case_ID` 或 `Task_Subject`，并作为后续每一步推理的唯一前置参照。
3. **建立“一致性网关（Consistency Gatekeeper）”**：在生成最终 JSON 前，增加一道“判别式”校验，比对当前输出与第一步提取的“指纹”是否匹配。
4. **结构化指令增强**：使用 Markdown 增强指令的层级感，明确区分“身份定义”、“推理协议”和“输出规范”。

**改动范围：**
- 修改了 `思考框架`，新增“指纹提取”和“一致性验证”步骤。
- 增加了 `核心行为准则` 中的“上下文隔离”条款。
- 在 `输出格式` 前增加了硬性的“无记忆”声明。

**本轮优化方向标签：** CoT 框架 / 边界条件 / 角色定义

