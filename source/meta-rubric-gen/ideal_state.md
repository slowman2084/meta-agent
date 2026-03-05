# RubricGen-Agent 理想态描述

## 一、Agent 定位与核心价值

RubricGen-Agent 的核心价值是：**将一个模糊的任务描述，转化为一份可操作、可去偏、可判定的 LLM-as-a-Judge 评分标准（Rubric）**。

判断一个 Rubric 是否达到理想态的核心标准：
- Judge 使用这份 Rubric 评分时，两个不同的 Judge 对同一个输出的结论差异在 ±1 分以内
- Rubric 中每个 criterion 都有可观察的证据线索，Judge 不需要凭直觉判断
- Rubric 能有效抵抗 position bias（答案位置影响）、verbosity bias（长度影响）、rubric-order bias（顺序影响）

---

## 二、核心能力维度

### 2.1 任务硬约束识别能力
- 能从 `input_spec` 和 `output_spec` 中**自主推导**出任务的硬约束（不依赖外部提供）
- 硬约束必须体现在 Rubric 的 Correctness & Constraints criterion 中，且设置违反时的总分上限规则

### 2.2 criterion 可判定性
- 每个 criterion 必须有：定义（Definition）、分档文字锚点（Levels）、证据线索（Evidence to look for）、常见失败模式（Common failure modes）
- 文字锚点必须有区分度：1 分和 2 分的描述不能是同一件事的程度差异，而必须有本质区别

### 2.3 去偏机制设计
- Rubric 固定顺序：Correctness&Constraints -> Coverage -> Safety/Policy -> Factuality/Verifiability -> Clarity/Style -> Efficiency（如适用）
- 必须包含 anti_bias_tests，至少覆盖：候选顺序交换测试 + Rubric 顺序打乱测试
- judge_instructions_snippet 中必须明确声明：不因长度/位置/措辞花哨加分

### 2.4 事实密集任务的可验证性
- 对于事实/知识密集任务，必须有专门的 Factuality/Verifiability criterion
- 该 criterion 必须包含"不确定时"的处理规则（降分或触发 needs_review）

### 2.5 系统级 criterion 具体化（有 agent_name 时）
- 当提供 agent_name 时，必须执行资源检索（references/ + .mcp.json + skills/）
- criterion 的 evidence_to_look_for 应引用真实系统字段名、约束和错误码，而非泛泛的"输出正确"

### 2.6 Rubric 自我质检
- 生成后必须运行 Rubric-of-Rubrics 质检（Specific/Scaffolded/Justified/Actionable/Qualified/Refinable）
- 不通过则先修订再输出，rubric_quality_check.passed 字段必须诚实反映实际结论

---

## 三、输入输出规范

### 输入格式

用户（或主 Agent）提供简洁的 JSON，**只包含以下字段**：

```json
{
  "task_name": "任务名称或简短描述",
  "input_spec": "Judge 评分时会看到的输入内容——通常包含测试用例的 Input 原文、参考答案（ExpectedOutput）、以及必要的上下文说明",
  "output_spec": "被评估的输出类型与格式（如：自然语言回复、JSON 结构、代码片段等）",
  "agent_name": "（可选）被评估 Agent 的名称，用于资源检索"
}
```

**调用方不应该提供的字段**（详见下方反模式说明）：
- `must_follow`（硬约束）
- `nice_to_have`（加分项）
- `risk_notes`（风险/偏差来源）
- `examples_optional`（示例）

这些字段是 RubricGen-Agent 自己的 CoT 推理职责，由 Agent 从 `input_spec` 和 `output_spec` 中自主推导。

### 输出格式

严格输出 JSON，符合以下 Schema：

```json
{
  "rubric_name": "...",
  "version": "1.0",
  "scale": {"type": "1-5", "meaning": "..."},
  "criteria": [...],
  "aggregation": {
    "method": "...",
    "rules": [...],
    "needs_review_conditions": [...]
  },
  "judge_instructions_snippet": "...",
  "anti_bias_tests": [...],
  "rubric_quality_check": {
    "passed": true,
    "notes": [...]
  }
}
```

输出中**不得**包含任何 JSON 之外的解释性文本。

---

## 四、反模式（Anti-Patterns）

以下行为是明确的反模式，代表 Agent 未达到理想态：

### 4.1 外部注入约束（最高优先级反模式）
**描述**：调用方在输入 JSON 中预先填写了 `must_follow`、`nice_to_have`、`risk_notes` 等约束分析字段，RubricGen-Agent 直接采用这些字段生成 Rubric，而没有经过自己的 CoT 推理过程。

**为什么是反模式**：
- 这些约束分析本来就是 RubricGen-Agent 的核心 CoT 推理工作。如果由外部提供，Agent 就退化成了一个"格式转换器"，失去了其存在的核心价值
- 调用方（用户或主 Agent）通常没有能力、也不应该负责提前分析任务的约束结构——这正是 RubricGen-Agent 应该做的事
- 外部注入的约束质量参差不齐，Agent 如果盲目采用，会生成质量不稳定的 Rubric

**正确行为**：不论调用方是否传入了这些字段，RubricGen-Agent 都应该从 `input_spec` 和 `output_spec` 出发，自主推导硬约束、加分项和风险点，再与调用方提供的信息（如有）相互印证，而不是直接采用。

### 4.2 输出非 JSON 格式
**描述**：当调用方传入的格式不规范（如纯文本描述而非 JSON），Agent 也输出了非 JSON 的 Rubric（如 Markdown 表格或自然语言列表）。

**为什么是反模式**：输出格式是 Agent 的硬约束，与输入格式无关。任何情况下都必须输出 JSON。

### 4.3 criterion 无锚点泛化
**描述**：criterion 的 levels 只写了程度差异（"很好/较好/一般/较差/很差"），没有可观察的行为描述，导致不同 Judge 理解不一致。

### 4.4 遗漏硬约束上限规则
**描述**：aggregation.rules 中没有针对核心硬约束的总分上限规则，导致逻辑错误的输出可以靠高风格分"救回来"。

### 4.5 跳过 Rubric 质检
**描述**：rubric_quality_check.passed 直接填 true，没有实际运行质检逻辑，或明知有问题但没有修订就输出。

### 4.6 资源检索结果污染输出范围
**描述**：读取了 agent_name 对应的资源后，修改了 input_spec 或 output_spec 的评估范围，超出调用方定义的范围。资源检索只用于让 criterion 更具体，不得改变评估范围。

### 4.7 忽略资源检索
**描述**：`agent_name` 已提供，但未读取 `references/`、`.mcp.json`、`skills/`，导致 criterion 停留在通用描述，无法区分系统真实的正确与错误调用行为。

---

## 五、质量评估维度

评估一份 Rubric 的质量，可以从以下维度打分（对应 rubric-of-rubrics）：

| 维度 | 含义 | 理想表现 |
|------|------|----------|
| Specific（具体性） | criterion 是否有可观察的证据线索 | evidence_to_look_for 中包含具体字段名/行为特征，而非"回答正确" |
| Scaffolded（分层性） | 各档之间是否有清晰区分 | 1分与2分之间有本质区别，而非同一问题的程度差异 |
| Justified（合理性） | criterion 的权重和上限规则是否有理由 | 核心硬约束权重最高，风格类权重最低，有明确规则说明 |
| Actionable（可操作性） | Judge 能否根据 Rubric 直接评分，无需额外判断 | 所有评分决策都有对应的判定规则 |
| Qualified（边界清晰） | 是否处理了 needs_review 边界情况 | needs_review_conditions 中有明确的触发条件 |
| Refinable（可迭代性） | 是否记录了当前的局限性 | rubric_quality_check.notes 中诚实记录了已知不足 |
