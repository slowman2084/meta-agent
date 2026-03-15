# skill-creator vs meta-agent 对比分析

> 参考来源：https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md
> 分析日期：2026-03-12

---

## 相似之处

两者都是 **"Agent/Skill 工厂"** 的概念：

- 都有 创建 → 测试 → 评估 → 迭代 的核心循环
- 都用子 Agent 分工（skill-creator 也 spawn subagents 做并行测试）
- 都关注评估质量（定性 + 定量）

---

## skill-creator 的优势 / 可借鉴点

### 1. "Pushy Description" 触发优化

skill-creator 有专门的**描述优化步骤**：用真实用户 query 测试触发准确率，迭代 description 直到触发率达标。

meta-agent 的缺口：Agent 写完后，`agent.json` 的 description 是否能被 IDE 准确触发，目前没有验证机制。

---

### 2. 盲测对比（Blind Comparison）

skill-creator 默认跑 with-skill vs without-skill 的**控制组对比**，让用户直观看到 skill 带来的提升。

meta-agent 的缺口：只有单向评估（打分），没有 baseline 对照组的概念，无法量化 prompt 的真实增益。

---

### 3. 渐进式披露（Progressive Disclosure）

skill-creator 强调 **"keep SKILL.md under 500 lines"**，采用三层加载：

| 层级 | 内容 | 加载时机 |
|------|------|----------|
| 元数据 | name + description | 始终在 context |
| SKILL.md 正文 | 核心规则 | 触发时加载 |
| 捆绑资源 | 参考材料、示例 | 按需加载 |

meta-agent 的缺口：Agent prompt 没有明确的长度控制和层级加载机制，部分 Agent 提示词偏长。

---

### 4. "Explain the why" 而非硬规则

skill-creator 建议用**解释性指令**替代 ALWAYS/NEVER，让 LLM 理解意图而不是死记规则，减少对边缘 case 的误判。

meta-agent 的参考：CLAUDE.md 里的硬约束（禁止、严禁）在规则文件层面是对的，但在 Agent prompt 本身里，可以更多用解释性语言，增强泛化能力。

---

### 5. 用户访谈（Intent Capture）

skill-creator 第一步是结构化地采访用户，收集：
- 核心 use cases（正例）
- anti-cases（反例，不应触发的场景）
- 具体 examples

再动笔写 skill，方向更准确。

meta-agent 的缺口：`create_agent` 流程是否有足够的"需求澄清"环节？如果直接进入写作，可能方向不准。

---

## meta-agent 的优势

### 1. 更完整的质量保障体系

| 组件 | 职责 |
|------|------|
| `meta-rubric-gen` | 生成任务专属、可判定的评分标准 |
| `meta-debug` | 三元组（提示词/理想态/rubrics）一致性诊断 |
| `meta-retrospective` | 多轮迭代反模式识别，输出 forced_new_directions |

skill-creator 的评估更依赖人工定性 review，meta-agent 的体系更系统化、可量化。

---

### 2. 多 IDE 同步机制

skill-creator 是单目标的。meta-agent 的 `install.py` 能同步到 4 个 IDE（Cursor / CodeBuddy / Claude Code / Codex），是独有的工程优势。

---

### 3. 理想态（ideal_state）文档

meta-agent 有专门的 `ideal_state.md` + `meta-ideal-state` Agent，形成清晰的"目标态"基准。skill-creator 没有这个概念，评估标准较主观。

---

### 4. 防作弊机制

meta-agent 的反作弊约束（禁止将 ExpectedOutput 写入提示词）是 AutoPrompt 领域的重要工程实践，防止过拟合测试集。skill-creator 没有明确处理这个问题。

---

### 5. 平台模式（@platform）

支持外部平台测试（通过 `@` 后缀标识），不绑定 IDE Sub Agent，更灵活，适应更多部署场景。

---

## 改进建议

| 优先级 | 借鉴点 | 改造方向 |
|--------|--------|----------|
| 高 | Description 触发优化 | 在 `create_agent` 末尾加一步：用 5-10 条真实 query 测试 `agent.json` description 的触发准确率，不达标则迭代 description |
| 中 | Blind comparison | `test_agent` 加可选的 baseline 模式：无 prompt 情况下跑同一批用例，计算提升幅度，量化 prompt 真实收益 |
| 中 | 用户访谈结构化 | `create_agent` 入口加结构化问卷（use case / anti-case / examples），需求澄清完再进入 prompt 生成 |
| 低 | Progressive disclosure | 为长 prompt 的 Agent 拆分"核心规则"段和"参考材料"段，控制 context 消耗 |
