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

利用自指性（Self-reference），我们用一组 Meta Agent 构建了从**初始化 → 测评 → 调优**的完整闭环：

```
                            初始化阶段
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  理想态/提示词/用例    meta-ideal-state    生成理想态    │
  │        │                    │                           │
  │        ▼                    ▼                           │
  │   meta-prompt-engineer  →  生成提示词                   │
  │        │                                                │
  │        ▼                                                │
  │   meta-testcase-gen  →  生成测试用例                    │
  │        │                                                │
  │        ▼                                                │
  │   meta-rubric-gen  →  生成评分标准                      │
  │                                                         │
  └───────────────┬─────────────────────────────────────────┘
                  │
                  ▼
  ┌─────────────────────────────────────────────────────────┐
  │              迭代优化阶段（iterate）                      │
  │                                                         │
  │   测试 Agent  →  meta-eval-judge 评分  →  达标？        │
  │       ▲                                    │            │
  │       │              NO                    │ YES        │
  │       │◄───────────────────────────────────┘            │
  │       │                                    │            │
  │  meta-prompt-engineer 优化提示词           ▼            │
  │  meta-retrospective 复盘分析          完成/上线         │
  │                                                         │
  └─────────────────────────────────────────────────────────┘
```

---

## 核心能力

| 触发词 | 功能 | 说明 |
|--------|------|------|
| `create agent` | 创建 Agent | 支持从提示词草稿、理想态描述、YAML 用例、LLM 对话记录四种方式创建 |
| `create testcases` | 生成测试用例 | 为已有 Agent 自动生成 YAML 测试用例和评分标准 |
| `test` | 测试评估 | 逐条运行测试用例，调用 eval-judge 进行 0-100 分评分 |
| `iterate` | 迭代优化 | 4 阶段分层策略自动迭代（热身→基线→抽样→验证），直到达标 |
| `calibrate` | 校准诊断 | 诊断三元组（提示词 / 理想态 / 评分标准）的一致性问题 |
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

### 这三个脚本已经接入主流程

现在不只是“可以手动调用工具”，而是已经写进主编排 Skill：

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

这意味着：
- 新会话直接 `test xxx` / `iterate xxx`，会自动带上最近状态
- 迭代过程中产生的经验，不再只停留在报告里
- `status.json` 会随着流程推进持续刷新，而不是依赖手工维护

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

```
# 测试全部用例
test cls-log-agent

# 只测试前 3 条
test cls-log-agent top 3

# 在 CodeBuddy CLI 平台上测试
test cls-log-agent on codebuddycli
```

现在这条链路会自动做两件事：
1. 开始前执行 `context_tool.py recover`，优先续跑未完成 plan，并带上最近 baseline / test / changelog / learnings
2. `评估报告.md` 生成后执行 `status_tool.py sync`，把最新分数和计划状态写入 `status.json`

### 场景 3：自动迭代优化直到达标

```
# 自动 4 阶段优化（热身 → 基线 → 抽样迭代 → 全量验证）
iterate cls-log-agent

# 指定目标分数
iterate cls-log-agent  # 默认目标 98 分

# 从上次中断处续跑（自动查找最新 plan 文件）
iterate cls-log-agent
```

现在 iterate 主流程内建了这套闭环：
1. 启动先 `recover`
2. 每轮 test / compare 后跑 `summary`
3. 将有效方向、退化信号、反模式写入 `learnings.jsonl`
4. 每个阶段结束后 `status_tool.py sync`

所以一次 `iterate xxx` 已经不只是“跑分”，而是“恢复上下文 → 执行 → 沉淀经验 → 刷新状态”的完整工作流。

### 场景 4：迭代过程中积累和使用经验

```bash
# 手动补记一条经验（可选）
./venv/bin/python scripts/learnings_tool.py log source/agents/cls-log-agent \
    --type pitfall --key "n-plus-one-api-calls" \
    --insight "Agent makes separate API calls for each topic instead of batching" \
    --confidence 9 --source observed --iteration 5

# 查看下次启动时会恢复到什么上下文
./venv/bin/python scripts/context_tool.py recover source/agents/cls-log-agent --json
```

但在默认工作流里，很多经验已经会自动沉淀：
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

---

## 八个 Meta Agent 的协作

Meta-Agent 由 8 个专职 Sub Agent 组成，形成完整的流水线：

| Agent | 职责 | 在流程中的位置 |
|-------|------|--------------|
| `meta-ideal-state` | 将业务描述转化为结构化理想态文档 | 初始化：定义"什么是好" |
| `meta-prompt-engineer` | 将理想态转化为可执行的 Agent 提示词，运用 CoT、few-shot 等工程技法 | 初始化 + 迭代优化 |
| `meta-testcase-gen` | 推断用户画像，生成覆盖多场景的 YAML 测试用例 | 初始化 |
| `meta-rubric-gen` | 为每条用例生成原子化、可判定的评分标准 | 初始化 |
| `meta-eval-judge` | 根据评分标准对 Agent 输出进行严格评分（0-100） | 测试 + 迭代 |
| `meta-reviewer` | 独立审查提示词是否存在作弊（抄袭 ExpectedOutput）或过拟合 | 迭代优化（生成与审查分离） |
| `meta-retrospective` | 分析多轮迭代历史，识别劣化模式，提出新优化方向 | 迭代复盘 |
| `meta-debug` | 诊断三元组一致性问题，输出 calibration_report.json | 校准调试 |

---

## 目录结构

```
meta-agent/
├── source/                       # 唯一真相来源（Source of Truth）
│   ├── agents/                   #   Agent 源文件目录
│   │   └── [AgentName]/          #     每个 Agent 的完整源文件
│   │       ├── prompt.md         #       提示词
│   │       ├── ideal_state.md    #       理想态描述
│   │       ├── testcases.yaml    #       测试用例（Input / ExpectedOutput / Judge）
│   │       ├── agent.json        #       元数据（描述 + 工具语义 + benefits_from）
│   │       ├── changelog.md      #       全生命周期变更记录
│   │       ├── learnings.jsonl   #       结构化经验记录（追加写入）
│   │       ├── status.json       #       当前状态索引
│   │       ├── .mcp.json         #       MCP 服务配置
│   │       ├── references/       #       领域参考资源
│   │       ├── skills/           #       专属 Skill
│   │       ├── bak/              #       历史备份
│   │       └── tmp/              #       运行时产物（plan / test results / baseline）
│   │
│   ├── skills/                   #   Skill 源文件目录
│   │   └── [SkillName]/          #     每个 Skill 的完整源文件
│   │       ├── SKILL.md          #       Skill 指令文档（迭代优化目标）
│   │       ├── skill.json        #       元数据（trigger_keywords + tools）
│   │       ├── scripts/          #       实现脚本
│   │       └── ...               #       （其余同 Agent 结构）
│   │
│   └── platform-skills/          #   平台 Skill 源目录（执行环境封装）
│
├── scripts/                      # 自动化脚本
│   ├── install.py                #   Agent + Skill + Platform Skills 安装
│   ├── scaffold.py               #   创建 Agent 目录脚手架
│   ├── yaml_tool.py              #   YAML 用例读写工具（按需读取）
│   ├── learnings_tool.py         #   经验管理（log / search / count）
│   ├── context_tool.py           #   上下文恢复（recover / summary）
│   ├── status_tool.py            #   状态索引（get / set / sync / summary）
│   ├── setup_mcp.py              #   MCP 快速配置
│   └── verify_setup.py           #   初始化验证
│
├── tools/                        # 人工辅助工具（浏览器中使用）
│   ├── testcase_viewer.html      #   测试用例可视化审阅 + 批注导出
│   └── calibration_viewer.html   #   校准诊断报告可视化 + 决策选择
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

**核心原则**：`source/` 是唯一真相来源，所有修改在此进行，通过 `scripts/install.py` 一键同步到 Cursor / CodeBuddy / Claude Code / Codex 四个平台。

---

## 多 IDE 兼容

同一个 Agent 提示词自动适配四种 IDE 的文件头格式：

| IDE | Agent 文件位置 | MCP 声明方式 |
|-----|--------------|-------------|
| Cursor | `.cursor/agents/` | 不支持文件头声明 |
| CodeBuddy | `.codebuddy/agents/` | `mcpTools: 服务名` |
| Claude Code | `.claude/agents/` | `mcpServers: [服务名]` |
| Codex | `AGENTS.md` 章节 | 不涉及 |

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

```
create agent                     # 开始创建流程，AI 会引导你选择方式
test my-agent                    # 测试指定 Agent
iterate my-agent                 # 循环优化直到达标
calibrate my-agent               # 校准评估体系
```

---

## 贡献指南

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## License

MIT License
