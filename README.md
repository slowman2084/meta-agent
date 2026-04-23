# Meta-Agent：小团队的 Agent 进化神器

**中文** | [English](README_EN.md)

AI 帮你定义理想态、生成测试用例、制定评分规则，然后自动迭代优化提示词——**你定标准，AI 自己进化**。

> 在 AI IDE（Cursor / CodeBuddy / Claude Code）中打开项目，说一句 `创建 Agent` 就能开始。

### Demo 演示

观看完整的创建→测试→迭代优化流程演示：

https://github.com/slowman2084/meta-agent/raw/main/demo.mp4

> 该视频演示了使用歌词金句 Agent 走完 Meta-Agent 的全流程。想亲手体验？试试 [5 分钟快速体验指南](README_FORCLAW.md)。

---

## 30 秒理解 Meta-Agent

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   你给 Meta-Agent 的                Meta-Agent 还你的   │
│   ─────────────                     ──────────────      │
│   ● 一段理想态描述                  ● 生产级提示词      │
│   ● 或一个提示词草稿                ● 完整测试用例集    │
│   ● 或几条测试用例                  ● 原子化评分标准    │
│   ● 或一段 LLM 对话记录            ● 达标的 Agent      │
│                                                         │
│              你定标准，AI 自己进化                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**最简体验**：在 IDE 中打开项目 → 输入 `创建 Agent` → AI 引导你完成一切。

```bash
git clone <your-repo-url> && cd meta-agent
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./venv/bin/python scripts/install.py          # 分发 Agent 和 Skill
# 打开 IDE，对话框输入：创建 Agent
```

> 想要手把手体验完整流程？试试 [5 分钟快速体验指南](README_FORCLAW.md)——用歌词金句 demo 走完创建→测试→迭代全流程。

---

## 为什么需要 Meta-Agent？

### 理想态之伤

构建一个"能用"的 Agent 很简单，但构建一个"好用"的 Agent 极其困难。核心瓶颈在**理想态**：

- **不懂行，定义不了理想态** —— 不懂运维的写不出运维 Agent 的最佳实践，不懂翻译的定义不了翻译质量标准。但即使懂，也难以系统化表达：就像你总以为自己懂得很多，却无法教给自己小孩。
- **小团队，哪有人力制定理想态** —— Google 和 OpenAI 上百人的专业团队来做评估体系，小团队把工程跑通就已经顶天了。
- **理想态定义了，落地更难** —— 需要将理想态拆解为提示词、测试用例、评分标准（Rubric），然后反复迭代优化。人力成本巨大。

### 我们的核心思想

**用 AI 来解决 AI 的问题。** 这也是项目命名"Meta-Agent"（元 Agent）的原因。

利用自指性（Self-reference），我们用一组核心 Meta Skills 和 Sub Agents 构建了从**初始化 → 测评 → 调优**的完整闭环。**核心编排器是 `meta-plan`**，它充当所有命令（`test`、`create`、`iterate` 等）的路由入口，负责协调其他 Meta Skills：

```
                       编排层（meta-plan 路由）
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
            初始化阶段      测试阶段      迭代优化阶段
                │             │             │
                ├─meta-ideal-state         │
                ├─meta-prompt-engineer     │
                ├─meta-testcase-gen        ├─meta-eval-judge
                ├─meta-rubric-gen          ├─meta-prompt-engineer
                │                          ├─meta-iterate
                │                          └─meta-retrospective
                │
                └─meta-reviewer
                └─meta-debug（校准诊断）
```

**工作流特点**：
- **中心路由**：`meta-plan` 接收用户命令，生成任务计划，协调下游组件
- **分阶段执行**：初始化（定义理想态、生成提示词、测试用例、评分标准）→ 测试 → 优化 → 复盘
- **自动化工具集成**：`context_tool.py`、`learnings_tool.py`、`status_tool.py` 已内置于编排流程中，无需手动调用

---

## 核心能力

| 触发词 | 功能 | 说明 |
|--------|------|------|
| `create agent` | 创建 Agent | 支持从提示词草稿、理想态描述、YAML 用例、LLM 对话记录四种方式创建 |
| `create testcases` | 生成测试用例 | 为已有 Agent 自动生成 YAML 测试用例和评分标准 |
| `test` | 测试评估 | 逐条运行测试用例，调用 eval-judge 进行 0-100 分评分 |
| `test --models a,b --runs N` | 多模型对比测试 | 多模型×多次运行 → 对比 HTML → 选择 ExpectedOutput → Rubrics 校准 |
| `iterate` | 迭代优化 | 4 阶段分层策略自动迭代（热身→基线→抽样→验证），直到达标 |
| `iterate --models a,b` | 多模型并发优化 | 为每个模型各自迭代优化 → 交叉测试 → 生成跨模型 robust 版本 |
| `calibrate` | 校准诊断 | 诊断三元组（提示词 / 理想态 / 评分标准）的一致性问题 |
| `enrich` | 补全工程化资产 | 为已有 Skill/Agent 逆向补全理想态 + 测试用例 + Judge，支持外部路径和批量模式 |
| `下一步` / `next` | 状态建议 | 基于所有 Agent/Skill 的状态和规划文件，给出下一步操作建议 |
| `create skill` | 创建 Skill | 创建可测试的 Skill，自动套壳 meta-skill-harness |
| `create platformskill` | 创建平台 Skill | 创建新的 Platform Skill 执行环境封装 |

---

## 工具脚本速查

### 核心工具

```bash
# Agent/Skill 安装分发
./venv/bin/python scripts/install.py                     # 安装全部
./venv/bin/python scripts/install.py my-agent            # 安装指定 Agent/Skill
./venv/bin/python scripts/install.py --platform-skills   # 安装 Platform Skills

# Agent 目录脚手架
./venv/bin/python scripts/scaffold.py my-agent -d "描述" -t "read,write"

# YAML 测试用例读写
./venv/bin/python scripts/yaml_tool.py count source/agents/my-agent/testcases.yaml
./venv/bin/python scripts/yaml_tool.py get source/agents/my-agent/testcases.yaml 0
./venv/bin/python scripts/yaml_tool.py get source/agents/my-agent/testcases.yaml 0-4 --fields Input,Judge
```

### 辅助工具

```bash
# Skill 测试壳 Agent 创建
./venv/bin/python scripts/create_harness.py [skill-name]

# 产物完整性检查（检查 plan 中各步骤的产物是否存在）
./venv/bin/python scripts/artifact_checker.py [target_dir]

# 平台输出校验
./venv/bin/python scripts/validate_platform_outputs.py [output_dir]

# 临时文件清理
./venv/bin/python scripts/cleanup_tool.py [target_dir]

# 触发测试执行
./venv/bin/python scripts/trigger_test.py [target] [--cases 0-4]
```

### 多模型对比工具

```bash
# 将 manifest.json + 各 result.md 注入到 HTML 对比页面
./venv/bin/python scripts/multimodel_inject.py [multimodel_dir]
# → 生成 multimodel_compare_data.html，在浏览器中打开对比选择

# 将 calibration_report.json 注入到校准决策页面
./venv/bin/python scripts/calibration_inject.py [calibration_report.json]
# → 生成 calibration_review_data.html，在浏览器中逐条决策
```

### Learnings 经验管理

借鉴 gstack 的组织记忆设计，每个 Agent/Skill 维护独立的 `learnings.jsonl`，支持置信度衰减和读时去重。

```bash
# 记录一条经验
./venv/bin/python scripts/learnings_tool.py log source/agents/cls-log-agent \
    --type pitfall \
    --key "missing-sampling-rate" \
    --insight "Agent forgets to set SamplingRate when timerange > 24h" \
    --confidence 8 \
    --source observed \
    --skill meta-retrospective \
    --iteration 3 \
    --tags "tool-calling,parameter"

# 搜索经验（自动去重 + 置信度衰减）
./venv/bin/python scripts/learnings_tool.py search source/agents/cls-log-agent
./venv/bin/python scripts/learnings_tool.py search source/agents/cls-log-agent --type pitfall --top 5
./venv/bin/python scripts/learnings_tool.py search source/agents/cls-log-agent --query "sampling" --json

# 统计
./venv/bin/python scripts/learnings_tool.py count source/agents/cls-log-agent
```

**Learnings 类型**：`pitfall`（踩坑）、`pattern`（模式）、`optimization`（优化方向）、`preference`（偏好）、`rubric-fix`（评分修正）

**来源与衰减**：`observed`/`inferred` 每 30 天置信度 -1，`user-stated` 永不衰减。

### 上下文恢复

新会话启动时自动扫描 Agent 目录，恢复最新状态（plan、baseline、learnings、changelog、测试结果）。

```bash
# 完整上下文摘要（人类可读）
./venv/bin/python scripts/context_tool.py recover source/agents/cls-log-agent

# JSON 格式（供编排 Skill 程序化消费）
./venv/bin/python scripts/context_tool.py recover source/agents/cls-log-agent --json

# 一行摘要
./venv/bin/python scripts/context_tool.py summary source/agents/cls-log-agent
```

输出示例：

```
=== Session Context: cls-log-agent (agent) ===

[Plan] status=running, phase=phase3_sampling, iter=5/10, target=98
[Baseline] avg=69.7, cases=40
[Learnings] 3 relevant:
  1. [pitfall] missing-sampling-rate (conf:8): Agent forgets SamplingRate...
  2. [optimization] cot-format (conf:6): Adding CoT chain improves...
  3. [pattern] cascade-query (conf:5): Cross-topic needs explicit...
[Changelog] last 3:
  - [优化] 第5轮迭代优化 (2026-03-21)
  - [优化] 第4轮迭代优化 (2026-03-20)
  - [调试] calibrate 修复rubric (2026-03-19)
[Latest Test] evalooper_iter_5_subagent/ — avg=82.3
```

### Agent/Skill 状态索引

每个 Agent/Skill 维护 `status.json`，提供快速查询和全局概览。

```bash
# 查看单个 Agent 状态
./venv/bin/python scripts/status_tool.py get source/agents/cls-log-agent
./venv/bin/python scripts/status_tool.py get source/agents/cls-log-agent --field phase

# 手动更新字段
./venv/bin/python scripts/status_tool.py set source/agents/cls-log-agent phase iterate

# 从磁盘产物自动同步状态
./venv/bin/python scripts/status_tool.py sync source/agents/cls-log-agent

# 全局概览
./venv/bin/python scripts/status_tool.py summary
```

全局概览输出示例：

```
=== Agent/Skill Status Summary ===

 Name                     Type    Phase         Score   Base Iters Learn  Last Activity
 ──────────────────────── ─────── ──────────── ────── ────── ───── ─────  ────────────────
 cls-log-agent            agent   iterate       90.7   69.7    11     5  2026-03-21
 cls-query-skill          skill   test          46.8    —       0     0  2026-04-09
 meta-eval-judge          agent   created         —      —      0     0  2026-02-28
```

### 工具自动化集成

这三个脚本已经内建于编排流程中，**在 `meta-plan` 和 `meta-iterate` 的生命周期内自动运行**：

- `meta-plan`
  - 在 `test` / `calibrate` 前自动执行 `context_tool.py recover`
  - 在 `评估报告.md` 生成后自动执行 `status_tool.py sync`
- `meta-iterate`
  - 启动时自动恢复最近上下文
  - 每轮 / 每阶段后自动执行 `context_tool.py summary`
  - 将关键收敛结论、退化信号写入 `learnings.jsonl`
  - 在 warmup / baseline / sampling / verify 后自动执行 `status_tool.py sync`
- `meta-retrospective`
  - 复盘结束后把高价值反模式 / 优化方向沉淀到 `learnings.jsonl`
  - 随后自动同步 `status.json`

**这意味着**：
- 新会话直接 `test xxx` / `iterate xxx`，会自动带上最近状态
- 迭代过程中产生的经验，不再只停留在报告里
- `status.json` 会随着流程推进持续刷新，而不是依赖手工维护
- **大多数情况下，用户无需手动调用这些工具**（除非调试或补记特殊经验）

---

## 使用场景

### 场景 1：从零创建一个 Agent

```
# 在 IDE 对话框中
create agent

# AI 会问你选择创建方式：
# a. 从提示词草稿创建
# b. 从理想态描述创建
# c. 从 YAML 测试用例创建
# d. 从 LLM 对话记录创建
```

### 场景 2：测试一个已有 Agent

```bash
# 单模型测试（默认）
test cls-log-agent

# 只测试前 3 条
test cls-log-agent top 3

# 在 CodeBuddy CLI 平台上测试
test cls-log-agent on codebuddycli

# 多模型对比测试：2 个模型各跑 2 次，产出对比 HTML
test cls-log-agent --models claude-sonnet-4,gpt-4o --runs 2
```

单模型测试会自动做两件事：
1. 开始前执行 `context_tool.py recover`，优先续跑未完成 plan，并带上最近 baseline / test / changelog / learnings
2. `评估报告.md` 生成后执行 `status_tool.py sync`，把最新分数和计划状态写入 `status.json`

多模型对比测试会额外做：
3. 对每份输出自动评分，生成 `manifest.json`
4. 注入数据到对比 HTML，打开浏览器供用户并排查看 Input / Output / Tools 调用过程
5. 用户选择最佳 ExpectedOutput → 可选触发 Rubrics 校准

> **推荐**：初次生成 testcases 和 rubrics 后，先跑一次 `test --models --runs`，通过对比选择来校准评估体系，再进入迭代优化。

### 场景 3：自动迭代优化直到达标

```bash
# 单模型迭代（默认）：4 阶段优化（热身 → 基线 → 抽样迭代 → 全量验证）
iterate cls-log-agent

# 从上次中断处续跑（自动查找最新 plan 文件）
iterate cls-log-agent

# 多模型并发优化：为每个模型各自迭代 → 交叉测试 → 生成 robust 版本
iterate cls-log-agent --models claude-sonnet-4,gpt-4o,gemini-2.5-pro
```

iterate 主流程内建了这套闭环：
1. 启动先 `recover`
2. 每轮 test / compare 后跑 `summary`
3. 将有效方向、退化信号、反模式写入 `learnings.jsonl`
4. 每个阶段结束后 `status_tool.py sync`

所以一次 `iterate xxx` 已经不只是"跑分"，而是"恢复上下文 → 执行 → 沉淀经验 → 刷新状态"的完整工作流。

多模型并发优化（`--models`）则会为每个模型独立迭代，最终通过智能采样交叉测试，产出跨模型得分最高的 `prompt_robust.md` / `SKILL_robust.md`。

### 场景 4：迭代过程中积累和使用经验

```bash
# 手动补记一条经验（可选，大多数情况下不需要）
./venv/bin/python scripts/learnings_tool.py log source/agents/cls-log-agent \
    --type pitfall --key "n-plus-one-api-calls" \
    --insight "Agent makes separate API calls for each topic instead of batching" \
    --confidence 9 --source observed --iteration 5

# 查看下次启动时会恢复到什么上下文
./venv/bin/python scripts/context_tool.py recover source/agents/cls-log-agent --json
```

在默认工作流里，很多经验已经会自动沉淀：
- `meta-iterate` 会把每轮关键收敛结论 / 退化信号写入 learning
- `meta-retrospective` 会把高价值反模式和下一轮建议写入 learning
- 下一次 `test` / `iterate` 启动时，`context_tool` 会自动把这些经验带回来

手动 `log` 更适合补记用户明确偏好或流程外观察。

### 场景 5：校准评估体系

```
# 首次 test 后，运行 calibrate 诊断评估体系
calibrate cls-log-agent

# 诊断四类问题：
# - Rubric 自身设计问题
# - Rubric ↔ 理想态矛盾
# - 理想态 ↔ 提示词矛盾
# - 用户价值视角洞察
```

### 场景 6：查看所有 Agent 的整体状态

```bash
# 一个命令看全貌
./venv/bin/python scripts/status_tool.py summary

# 批量同步状态（从磁盘产物推断）
for dir in source/agents/*/; do
    ./venv/bin/python scripts/status_tool.py sync "$dir"
done
```

### 场景 7：测试一个 Skill

```
# Skill 自动套壳 meta-skill-harness，无需手动创建壳 Agent
test cls-query-skill

# 迭代优化 Skill（优化目标是 SKILL.md 而非 prompt.md）
iterate cls-query-skill
```

对 Skill 也一样适用：
- `test cls-query-skill` 前会自动恢复上下文
- `iterate cls-query-skill` 会自动把阶段状态和 learnings 写回 `source/skills/cls-query-skill/`
- 优化目标仍然是 `SKILL.md`，但恢复 / 经验 / 状态链路与 Agent 已统一

### 场景 8：为已有 Skill 补全工程化资产（enrich）

```bash
# 为单个 Skill 补全理想态 + 测试用例 + Judge
enrich my-skill

# 为外部项目中的 Skill 补全（支持任意路径）
enrich /path/to/external-project/skills/my-skill

# 批量补全一个目录下所有含 SKILL.md 的子目录
enrich /path/to/skills-dir --all
```

`enrich` 适用于：
- 手写的 Skill，从未经过 meta-agent 流程
- 外部项目中的 Skills（不在 meta-agent source 目录内）
- 批量补全整个 Skills 目录

流程：
1. **Locate** — 定位 SKILL.md，读取并理解 Skill 功能
2. **Ideal State** — 调用 meta-ideal-state，从 SKILL.md 逆向推导理想态
3. **Test Cases** — 调用 meta-testcase-gen，生成测试用例
4. **Rubric** — 调用 meta-rubric-gen，为每条用例生成 Judge
5. **Review** — 展示汇总，请用户确认质量
6. **Write Back** — 将 `ideal_state.md` + `testcases.yaml` 写入 Skill 目录

### 场景 9：Rubrics 迭代校准（推荐流程）

测试用例和 Rubrics 生成后，建议通过**多模型多次测试 → 对比选择 → 迭代更新 Rubrics** 来校准评估体系：

```bash
# 1. 多模型各跑 2 次，产出对比数据
test my-agent --models claude-sonnet-4,gpt-4o --runs 2

# 2. 用对比工具审查，选择最佳 ExpectedOutput
#    → 打开 scripts/multimodel_compare.html
#    → 并排查看 Input / Output，包括 tools 调用过程
#    → 为每条用例选择最佳输出 → 导出 selections.json

# 3. AI 读取 selections.json
#    → 若用户选了低分输出，触发反思流程
#    → 自动调整 Rubrics / 理想态 / 提示词
```

**对比工具的展示要求**：
- **Input 与 Output 分区展示**：每条用例清晰分开 Input（用户输入）和 Output（模型输出）
- **多轮 Tools 调用对比**：若 Agent 在执行中调用了多个 tools，对比工具中应逐步骤展示每次 tool 调用的参数和返回值，方便发现不同模型在 tool 使用策略上的差异
- **评分维度拆分**：各 Rubric 维度的得分独立展示，一眼看出哪个维度拉低了总分

---

## 11 个核心 Meta Skills

Meta-Agent 由 11 个核心 Meta Skills 和专职编排器组成，共同形成完整的流水线：

| Skill 名称 | 职责 | 在流程中的位置 |
|-----------|------|--------------|
| `meta-plan` | 中心路由器，接收用户命令，生成任务计划，协调下游组件 | 最核心：所有 `test`/`create`/`iterate` 命令的入口 |
| `meta-ideal-state` | 将业务描述转化为结构化理想态文档 | 初始化：定义"什么是好" |
| `meta-prompt-engineer` | 将理想态转化为可执行的 Agent 提示词，运用 CoT、few-shot 等工程技法 | 初始化 + 迭代优化 |
| `meta-testcase-gen` | 推断用户画像，生成覆盖多场景的 YAML 测试用例 | 初始化 |
| `meta-rubric-gen` | 为每条用例生成原子化、可判定的评分标准 | 初始化 |
| `meta-eval-judge` | 根据评分标准对 Agent 输出进行严格评分（0-100） | 测试 + 迭代 |
| `meta-iterate` | 执行 4 阶段分层优化策略（热身→基线→抽样→验证），管理收敛性和退化信号 | 迭代优化核心 |
| `meta-reviewer` | 独立审查提示词是否存在作弊（抄袭 ExpectedOutput）或过拟合 | 迭代优化（生成与审查分离） |
| `meta-retrospective` | 分析多轮迭代历史，识别劣化模式，提出新优化方向 | 迭代复盘 |
| `meta-debug` | 诊断三元组一致性问题，输出 calibration_report.json | 校准调试 |
| `meta-log-converter` | 将 LLM 对话记录转化为结构化测试用例 | 初始化辅助 |

**关键特点**：
- **meta-plan** 是所有命令的入口点和编排器
- **meta-iterate** 管理优化的生命周期和状态跟踪
- 所有 Skills 位于 `source/skills/meta-*/`，而不是 `source/agents/`

---

## Skill Harness 模式

`meta-skill-harness` 是一个通用壳 Agent，用于测试和迭代优化 Skills。当你使用 `test` 或 `iterate` 命令测试 Skill 时：

1. **自动套壳**：系统自动为 Skill 创建一个对应的测试壳 Agent
2. **SKILL.md 作为优化目标**：迭代优化的对象是 Skill 的 `SKILL.md`，而不是 prompt.md
3. **统一工作流**：Skill 复用所有 Agent 的工作流（恢复、测试、迭代、状态同步）
4. **无需手动创建**：你无需手动创建壳 Agent，系统自动处理

例如：
```
test cls-query-skill           # 自动套壳 meta-skill-harness 来测试
iterate cls-query-skill        # 自动优化 SKILL.md，产生优化历史
```

这种模式让 Skill 的测试和优化与 Agent 完全一致，降低了学习成本。

---

## 目录结构

```
meta-agent/
├── source/                       # 唯一真相来源（Source of Truth）
│   ├── agents/                   #   业务 Agent 源文件目录
│   │   ├── [AgentName]/          #     每个 Agent 的完整源文件
│   │   │   ├── prompt.md         #       提示词
│   │   │   ├── ideal_state.md    #       理想态描述
│   │   │   ├── testcases.yaml    #       测试用例（Input / ExpectedOutput / Judge）
│   │   │   ├── agent.json        #       元数据（描述 + 工具语义 + benefits_from）
│   │   │   ├── changelog.md      #       全生命周期变更记录
│   │   │   ├── learnings.jsonl   #       结构化经验记录（追加写入）
│   │   │   ├── status.json       #       当前状态索引
│   │   │   ├── .mcp.json         #       MCP 服务配置
│   │   │   ├── references/       #       领域参考资源
│   │   │   ├── skills/           #       专属 Skill
│   │   │   ├── bak/              #       历史备份
│   │   │   └── tmp/              #       运行时产物（plan / test results / baseline）
│   │   ├── meta-skill-harness/   #     通用 Skill 测试壳 Agent
│   │   └── 歌词生成系统/          #     Sample：走完创建→测试→迭代全流程的 Demo
│   │
│   ├── skills/                   #   Skills 源文件目录（包括所有 meta-* Skills）
│   │   ├── meta-plan/            #     中心编排器 Skill
│   │   │   ├── SKILL.md          #       Skill 指令文档
│   │   │   ├── skill.json        #       元数据
│   │   │   └── ...
│   │   ├── meta-iterate/         #     4 阶段迭代优化 Skill
│   │   ├── meta-prompt-engineer/ #     提示词生成和优化 Skill
│   │   ├── meta-eval-judge/      #     评分判定 Skill
│   │   ├── [SkillName]/          #     业务 Skill 源文件
│   │   │   ├── SKILL.md          #       Skill 指令文档（迭代优化目标）
│   │   │   ├── skill.json        #       元数据（trigger_keywords + tools）
│   │   │   ├── scripts/          #       实现脚本
│   │   │   └── ...               #       （其余同 Agent 结构）
│   │   └── ...
│   │
│   └── platform-skills/          #   平台 Skill 源目录（执行环境封装，TODO: 提供脱敏 Sample）
│
├── scripts/                      # 自动化脚本
│   ├── install.py                #   Agent + Skill + Platform Skills 安装
│   ├── scaffold.py               #   创建 Agent 目录脚手架
│   ├── yaml_tool.py              #   YAML 用例读写工具（按需读取）
│   ├── learnings_tool.py         #   经验管理（log / search / count）
│   ├── context_tool.py           #   上下文恢复（recover / summary）
│   ├── status_tool.py            #   状态索引（get / set / sync / summary）
│   ├── setup_mcp.py              #   MCP 快速配置
│   ├── verify_setup.py           #   初始化验证
│   ├── create_harness.py         #   Skill 测试壳 Agent 创建
│   ├── artifact_checker.py       #   产物完整性检查
│   ├── trigger_test.py           #   触发测试执行
│   ├── cleanup_tool.py           #   临时文件清理
│   ├── validate_platform_outputs.py # 平台输出校验
│   ├── multimodel_compare.html   #   多模型输出对比选择工具
│   ├── multimodel_inject.py      #   manifest + results → HTML 数据注入
│   ├── calibration_review.html   #   校准诊断可视化决策工具
│   └── calibration_inject.py     #   calibration JSON → HTML 数据注入
│
├── tools/                        # 人工辅助工具（浏览器中使用）
│   ├── testcase_viewer.html      #   测试用例可视化审阅 + 批注导出
│   └── calibration_viewer.html   #   校准诊断报告可视化 + 决策选择
│
├── tests/                        # 单元测试
│
├── .cursor/                      # ┐
├── .codebuddy/                   # ├─ 由 install.py 自动生成，勿手动修改
├── .claude/                      # │  （agents/ + skills/）
├── AGENTS.md                     # ┘
│
├── SETUP.md                      # AI 可执行的初始化指南
├── CLAUDE.md                     # Claude Code 全局配置
└── CODEBUDDY.md                  # CodeBuddy 项目配置
```

**核心原则**：
- `source/` 是唯一真相来源，所有修改在此进行
- **所有 meta-* 组件位于 `source/skills/meta-*/` 中**，而不是 `source/agents/`
- `source/agents/` 用于业务 Agent（target/business agents）
- `source/skills/` 包含所有 Skills，包括 meta-skills 和业务 Skills
- 通过 `scripts/install.py` 一键同步到 Cursor / CodeBuddy / Claude Code / Codex 四个平台

---

## 多 IDE 兼容

同一个 Agent 提示词自动适配四种 IDE 的文件头格式：

| IDE | Agent 文件位置 | MCP 声明方式 |
|-----|--------------|-------------|
| Cursor | `.cursor/agents/` | 不支持文件头声明 |
| CodeBuddy | `.codebuddy/agents/` | `mcpTools: 服务名` |
| Claude Code | `.claude/agents/` | `mcpServers: [服务名]` |
| Codex | `AGENTS.md` 章节 | 不涉及 |

### 安装范围

```bash
# 项目级安装（默认）——安装到当前项目的 .cursor/ .codebuddy/ .claude/ 目录
./venv/bin/python scripts/install.py <target>

# 用户级安装——自动探测已安装的 IDE，安装到 ~/.cursor/ ~/.codebuddy/ ~/.claude/
./venv/bin/python scripts/install.py <target> --scope user

# 用户级 + 指定模型版本
./venv/bin/python scripts/install.py <target> --scope user --model gpt-4o
```

---

## 多模型兼容工作流

Meta-Agent 支持在测试、迭代优化的全流程中兼容不同模型，最终产出跨模型鲁棒的提示词。

**`test` vs `iterate` 的分工**：

| 命令 | 用途 | 触发条件 |
|------|------|---------|
| `test xxx` | 单模型单次测试 | 默认（无 `--models`/`--runs`） |
| `test xxx --models a,b --runs 2` | **多模型对比测试** → 对比 HTML → 选择 ExpectedOutput → Rubrics 校准 | 有 `--models` 或 `--runs > 1` |
| `iterate xxx` | 单模型迭代优化 | 默认 |
| `iterate xxx --models a,b` | **多模型并发优化** → 各自迭代 → 交叉测试 → robust 版本 | 有 `--models` |

### 模型版本管理

**命名规范**：
- Agent：`prompt_<model>.md`（如 `prompt_claude-sonnet-4.md`、`prompt_gpt-4o.md`）
- Skill：`SKILL_<model>.md`（如 `SKILL_claude-sonnet-4.md`、`SKILL_gpt-4o.md`）
- 鲁棒版本：`prompt_robust.md` / `SKILL_robust.md`（跨模型得分最高的版本）

**安装时版本选择优先级**：
| 情况 | 选择的文件 |
|------|-----------|
| `--model gpt-4o` 且变体存在 | `prompt_gpt-4o.md` / `SKILL_gpt-4o.md` |
| `--model robust` | `prompt_robust.md` / `SKILL_robust.md` |
| 不指定且 `_robust` 版本存在 | **自动使用 robust 版本** |
| 不指定且无 robust | `prompt.md` / `SKILL.md`（默认）|

**Agent vs Skill 安装差异**：
- Agent：sub agent header 中可以指定 `model` 字段 → 运行时由 IDE 选择模型执行
- Skill：安装时将选中的 `SKILL_<model>.md` 内容安装为 `SKILL.md` → 运行时用已安装的版本

### 多模型测试执行

```bash
# 单模型跑 3 次（得到 3 份输出供对比选择）
test <target> --runs 3

# 3 个模型各跑 1 次
test <target> --models claude-sonnet-4,gpt-4o,gemini-2.5-pro

# 2 个模型各跑 2 次
test <target> --models claude-sonnet-4,gpt-4o --runs 2
```

每次执行产出标准化文件：
```
<target>/tmp/multimodel_<timestamp>/
├── <model>_run<N>_case<M>_sharegpt.json   # ShareGPT 格式对话记录
├── <model>_run<N>_case<M>_result.md       # Markdown 格式最终输出
└── manifest.json                           # 元信息索引 + 自动评分
```

### 人工选择 + 自动评估闭环

1. **对比工具**：`scripts/multimodel_compare.html` 并排展示不同模型/不同次运行的输出，带自动评分
   - **Input / Output 分区展示**：每条用例清晰分开展示用户输入和模型输出
   - **Tools 调用过程对比**：若 Agent 执行中调用了多个 tools，逐步骤展示每次 tool 调用的参数和返回值（从 ShareGPT JSON 中解析），方便发现不同模型在 tool 使用策略上的差异
   - **评分维度拆分**：各 Rubric 维度独立展示，一眼看出哪个维度拉低了总分
2. **选择 ExpectedOutput**：用户在 HTML 中为每个测试用例选择最佳输出 → 导出 `selections.json`
3. **低分选择触发反思**：AI 读取 `selections.json` 后，如果用户选了低分输出，提供两个选项：
   - **A. 反思模式**：调用 meta-debug 分析 rubrics/理想态/提示词哪里有问题 → `calibration_review.html` 让用户逐条决策
   - **B. 标准适配模式**：让 rubrics 遵循用户选择，自动优化评分标准

### 多模型并发优化

> **推荐流程**：在正式进入多模型并发优化前，先走一轮"测试用例+Rubrics 生成 → 多模型多次测试对比 → 人工选择 → 迭代更新 Rubrics"的校准循环。这可以确保评估体系本身是准确的，避免在错误的标准上优化。详见上方"场景 9：Rubrics 迭代校准"。

```bash
iterate <target> --models claude-sonnet-4,gpt-4o,gemini-2.5-pro
```

1. 为每个模型各自迭代优化，产出 `prompt_<model>.md` / `SKILL_<model>.md`
2. **智能采样交叉测试**：选 top-2 版本做定向交叉验证（非全量 N×N）
3. 跨模型均分最高的版本 → 微调生成 `prompt_robust.md` / `SKILL_robust.md`

```
📊 多模型优化报告
──────────────────────────────────────────────────────
| 版本                      | claude | gpt-4o | 跨模型均分 |
|--------------------------|--------|--------|-----------|
| prompt_claude-sonnet-4.md | 92     | 71     | 81.5      |
| prompt_gpt-4o.md          | 75     | 88     | 81.5      |
| prompt_robust.md           | 84     | 85     | 84.5 ★   |
──────────────────────────────────────────────────────
```

---

## 关键设计约束

| 约束 | 说明 | 为什么 |
|------|------|--------|
| **Source 优先** | 所有修改在 `source/` 中进行，通过 `install.py` 同步 | 保证四个 IDE 一致性 |
| **必须备份** | 修改前备份到 `bak/` 目录 | 支持迭代回退和复盘 |
| **反作弊** | 严禁将 `ExpectedOutput` 植入提示词 | 防止过拟合，确保泛化能力 |
| **Changelog 追加** | 创建、用例、优化、手动变更均追加记录 | 迭代历史可追溯 |
| **Learnings 追加** | 经验只追加不修改，读时去重+衰减 | 审计友好，过时经验自然淘汰 |
| **敏感信息隔离** | `.mcp.json`、`.env`、`platform.yaml` 已加入 `.gitignore` | 不泄露 API 密钥 |

---

## 快速开始

### 方式 A：AI 辅助初始化（推荐）

在支持的 IDE 中打开项目，直接让 AI 初始化：

```
请阅读 SETUP.md，帮我初始化这个项目
```

AI 会自动完成环境配置、依赖安装、Agent 和 Skill 分发。

### 方式 B：手动初始化

```bash
# 1. 克隆并安装
git clone <your-repo-url>
cd meta-agent
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 2. 分发 Agent 和 Skill 到所有 IDE 目录
./venv/bin/python scripts/install.py

# 3. 验证
./venv/bin/python scripts/verify_setup.py
```

### 开始使用

在 IDE 对话中直接输入触发词即可：

```bash
create agent                                          # 开始创建流程
test my-agent                                         # 单模型测试
test my-agent --models claude-sonnet-4,gpt-4o --runs 2  # 多模型对比测试 + Rubrics 校准
iterate my-agent                                      # 单模型迭代优化
iterate my-agent --models claude-sonnet-4,gpt-4o        # 多模型并发优化 → robust 版本
calibrate my-agent                                    # 校准评估体系
enrich /path/to/skills --all                          # 批量补全理想态+测试用例
下一步                                                # 基于当前状态给出下一步建议
```

---

## 贡献指南

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## License

MIT License
