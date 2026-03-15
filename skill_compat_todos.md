# skill-creator 借鉴 & Skill 兼容改造 TODO

> 基于 [create_skillVSmeta_agent.md](./create_skillVSmeta_agent.md) 的分析落地
>
> **范围说明**：本文件聚焦 skill-creator 借鉴带来的新能力，不重复 [TODOS.md](./TODOS.md) 中已规划的校准诊断相关内容。

---

## 背景：Agent vs Skill 的区别

| 维度 | Sub Agent | Skill |
|------|-----------|-------|
| 触发方式 | `Agent` tool 显式调用 | 用户意图自动触发（`/skill-name`）|
| 文件格式 | `agent.json` + `prompt.md` | `SKILL.md`（含 name + description + 正文）|
| 运行方式 | 独立子进程，自主完成任务 | 注入到主对话 context，辅助主模型 |
| 触发判定 | 编排者主动选择 | IDE 根据 description 语义匹配 |
| 已有支持 | ✅ meta-agent 完整支持 | ❌ 当前不支持 |

**兼容目标**：meta-agent 在保留现有 Agent 工厂能力的同时，新增 Skill 的全生命周期管理（创建 / 测试 / 迭代）。

---

## TODO 列表

### T1. `create_skill` 创建模式 `[P0]`

**目标**：支持创建 Skill（SKILL.md）而非 Sub Agent。

**核心差异点**：
- 产物是 `SKILL.md`（name + description + 正文），无 `agent.json`
- 需要 **intent interview**（见 T3），因为 Skill 的触发范围比 Agent 更难定义
- description 是核心资产（直接决定触发准确率），需要在创建时就认真设计
- 安装路径：`.claude/skills/`、`.codebuddy/skills/`、`.cursor/skills/`

**工作项**：

1. **新增触发词** `create_skill`（自然语言："创建 Skill"、"新建 Skill"）
2. **新增 `create_skill` 流程** 到 `agent-factory.mdc`：
   - Step 1: Intent Interview（见 T3）
   - Step 2: 写 `source/[SkillName]/SKILL.md`（name + description + 正文）
   - Step 3: 写 `source/[SkillName]/ideal_state.md`（Skill 理想输出态）
   - Step 4: 调用 `meta-testcase-gen` 生成测试用例
   - Step 5: 调用 `meta-rubric-gen` 生成 Judge
   - Step 6: 运行 description 触发率测试（见 T2）
   - Step 7: 安装同步
3. **修改 `scripts/scaffold.py`**：增加 `--type skill` 参数，生成 `SKILL.md` 模板而非 `agent.json + prompt.md`
4. **修改 `scripts/install.py`**：识别 Skill 目录（有 `SKILL.md` 无 `agent.json`），走 skill 安装路径

**涉及文件**：
- `source/rules/agent-factory.mdc`（新增 `create_skill` 节）
- `CLAUDE.md`（触发词表同步）
- `scripts/scaffold.py`
- `scripts/install.py`

---

### T2. Description 触发率测试 `[P0]`

**背景**：skill-creator 明确指出 description 决定触发准确率，需专项测试。当前 meta-agent 创建完 Agent/Skill 后，description 是否准确触发完全未验证。

**目标**：在 `create_agent` / `create_skill` 完成后，自动测试 description 的触发准确率，不达标则迭代 description。

**设计**：

触发率测试作为一个独立步骤（`test_description`），也可作为 `create_agent` / `create_skill` 末尾的可选步骤。

测试逻辑：
```
输入：description 文本 + 用户提供（或自动生成）的查询列表
            ↓
  正例 query（应触发）× 10 条
  负例 query（不应触发）× 10 条
            ↓
  对每条 query，判断："给定此 description，该 query 是否应该触发？"
            ↓
  统计：正例命中率 / 负例误触发率
            ↓
  若正例命中率 < 90% 或 负例误触发率 > 10%
            ↓
  调用 meta-prompt-engineer 优化 description（传入失败案例）
            ↓
  重复直到达标（最多 3 轮）
```

**工作项**：

1. **新增触发词** `test_description`（自然语言："测试触发率"、"优化 description"）
2. **新增 `test_description` 流程** 到 `agent-factory.mdc`
3. **修改 `meta-prompt-engineer`**：增加 `模式 C：description 优化`，专门接收触发率测试结果，迭代 description
4. **在 `create_agent` / `create_skill` 末尾**：加提示，建议用户执行 `test_description`

**注意**：
- 正例/负例 query 可由总控自动生成（基于 use case / anti-case），也可由用户补充
- 触发判定本身由 LLM 判断（模拟 IDE 的 description 匹配逻辑），非真实 IDE 调用

**涉及文件**：
- `source/rules/agent-factory.mdc`
- `source/meta-prompt-engineer/prompt.md`（增加 description 优化模式）
- `CLAUDE.md`

---

### T3. Intent Interview（需求澄清结构化） `[P1]`

**背景**：skill-creator 的第一步是结构化采访，收集 use case / anti-case / examples，再动笔写。当前 `create_agent` 缺乏这个环节，方向容易不准。

**目标**：在 `create_agent` / `create_skill` 开始时，通过结构化问卷收集需求，提升初始提示词的方向准确率。

**Interview 模板**：

```
1. 核心功能（必填）
   "这个 Agent/Skill 的核心任务是什么？一句话描述。"

2. 典型使用场景（必填，≥3 个）
   "列出 3 个最常见的使用场景（Input 示例），每个一行。"

3. 反例场景（推荐，≥2 个）
   "哪些情况不应该触发这个 Agent/Skill？（用于定义 description 边界）"

4. 输出期望（必填）
   "理想的输出是什么样的？（格式、风格、详细程度）"

5. 已有参考（可选）
   "是否有现成的提示词草稿、参考文档或同类 Agent？"
```

**工作项**：

1. **修改 `agent-factory.mdc` 的 `create_agent` / `create_skill` 流程**：Step 0 改为 Intent Interview
2. **Interview 结果作为结构化输入**传给 `meta-prompt-engineer` 和 `meta-testcase-gen`（当前两者只接收"理想态"，可扩展接收 interview 结果）
3. **对于快速创建（用户已提供充分信息）**：跳过 interview，直接进入生成

**涉及文件**：
- `source/rules/agent-factory.mdc`（`create_agent` Step 0）

---

### T4. Baseline 对比模式 `[P1]`

**背景**：skill-creator 的 with vs without 对比，让用户直观看到 Skill/Agent 的实际增益。当前 meta-agent 只有单向评估，无法量化 prompt 的真实价值。

**目标**：`test_agent` 支持可选的 `--baseline` 模式，在无提示词的情况下跑同一批测试用例，对比打分差值。

**设计**：

```
test_agent --baseline 模式：

  baseline 运行（无 prompt，裸模型）  ←→  正常运行（有 prompt）
              ↓                                    ↓
    case_[N]_baseline_output.txt        case_[N]_actual_output.txt
              ↓                                    ↓
    eval-judge 评分（baseline）          eval-judge 评分（正常）
              ↓                                    ↓
              └──────────── 差值分析 ──────────────┘
                                ↓
                      baseline_report.json
                      （展示每条用例的 Δscore，总体增益）
```

**工作项**：

1. **新增 `--baseline` 选项** 到 `test_agent` 触发词（自然语言："含基线测试"、"测试增益"）
2. **新增 baseline 运行步骤** 到 `agent-factory.mdc` 的 `test_agent` 流程
3. **新增 `baseline_report.json` 格式定义**（含 per-case Δscore + 总体 prompt 增益率）
4. **扩展 `tools/calibration_viewer.html`**（或新建 `tools/baseline_viewer.html`）可视化对比

**注意**：
- baseline 模式运行时传入相同的 Input，但 system prompt 为空或替换为最小化描述
- 不强制 Skill，对 Agent 同样适用
- 建议作为 `create_agent` 首次测试时的可选步骤，而非常规测试

**涉及文件**：
- `source/rules/agent-factory.mdc`（`test_agent` 节）
- `tools/calibration_viewer.html` 或新建 `tools/baseline_viewer.html`

---

### T5. Progressive Disclosure 规范（长提示词拆分） `[P2]`

**背景**：skill-creator 强调"keep SKILL.md under 500 lines"，分层加载减少 context 消耗。meta-agent 部分 Agent 提示词偏长，核心规则和参考材料混在一起。

**目标**：为长提示词（>300 行）建立拆分规范，分离"核心规则"和"参考材料"。

**设计**：

```
source/[AgentName]/
├── prompt.md          # 核心规则（目标 ≤300 行）
├── references/        # 参考材料（按需附加）
│   ├── examples.md    # 示例集
│   ├── schema.md      # 格式定义
│   └── faq.md         # 边界 case 说明
```

使用时，总控在调用 Sub Agent 时，根据具体用例的复杂度，决定是否附加 `references/` 内容。

**工作项**：

1. **修改 `agent-factory.mdc`**：在 `create_agent` 流程中，当 prompt 超过 300 行时，建议拆分 references
2. **修改 `meta-prompt-engineer`**：增加"prompt 过长时提醒拆分"的建议
3. **修改 `scripts/scaffold.py`**：默认创建 `references/` 目录（已有，确认）
4. **（可选）审查现有长提示词**：`meta-eval-judge`、`meta-rubric-gen` 是否需要拆分

**涉及文件**：
- `source/rules/agent-factory.mdc`
- `source/meta-prompt-engineer/prompt.md`

---

## 实施优先级汇总

| ID | 标题 | 优先级 | 依赖 | 工作量估算 |
|----|------|--------|------|-----------|
| T1 | `create_skill` 创建模式 | P0 | 无 | 2 天 |
| T2 | Description 触发率测试 | P0 | T1（Skill 也需要）| 1.5 天 |
| T3 | Intent Interview 结构化 | P1 | 无 | 0.5 天 |
| T4 | Baseline 对比模式 | P1 | 无 | 1.5 天 |
| T5 | Progressive Disclosure 规范 | P2 | 无 | 0.5 天 |

**建议执行顺序**：T1 → T2 → T3 → T4 → T5

与 TODOS.md 中的 P0 任务（eval-judge 单条约束、校准诊断机制）可并行推进，无冲突。

---

## 不做的事（明确排除）

- **不**将 skill-creator 的 HTML 评审 viewer 复制进来（meta-agent 的 `calibration_viewer.html` 已在 TODOS.md 规划，功能更完整）
- **不**引入 skill-creator 的"盲评"UI（meta-agent 的评分体系是结构化 rubric，不需要人工盲评）
- **不**修改现有 Agent 的提示词风格（"explain the why" 是建议，不是强制迁移工作）
