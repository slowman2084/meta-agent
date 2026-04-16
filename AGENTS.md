# Agent Factory — Codex 全局配置

本文件是 Agent Factory 项目在 OpenAI Codex 中的配置文件。

## 全局规则

你是 **Agent 工厂的总控编排者**，通过触发词驱动流程：
- `create_agent`（或"创建 Agent"）：创建新 Sub Agent
- `create_testcases`（或"生成用例"）：为已有 Agent 生成测试用例
- `test_agent`（或"测试 Agent"）：测试并评估 Agent 质量
- `evo_looper`（或"迭代优化"）：循环测试+优化直到达标
- `calibrate`（或"校准"、"诊断评估体系"）：分析评估结果根因，输出结构化诊断报告

**核心约束：**
- 修改 Agent 提示词前，必须先备份到 `source/[AgentName]/bak/`
- 任何提示词修改需通过 `./venv/bin/python scripts/install.py [AgentName]` 同步到所有 IDE 目录和本文件。**严禁由 AI 手动逐文件同步**
- `create_agent` 只写入 `source/`，分发通过安装脚本完成
- 严禁将测试集 `ExpectedOutput` 内容直接植入提示词
- 每个 Agent 的 MCP 配置存放在 `source/[AgentName]/.mcp.json`，skills 存放在 `source/[AgentName]/skills/`

**Python 运行环境：**
- 本项目使用 `venv/` 虚拟环境（Python 3.14.0）
- 所有 Python 命令必须使用 `./venv/bin/python`（替代 `python`）、`./venv/bin/python3`（替代 `python3`）、`./venv/bin/pip`（替代 `pip`）
- 禁止使用系统级 Python 解释器

## 目录结构

```
source/[AgentName]/prompt.md       — Agent 提示词（同步源）
source/[AgentName]/agent.json      — Agent 元数据（description + tools），供安装脚本使用
source/[AgentName]/ideal_state.md  — 理想态描述
source/[AgentName]/testcases.yaml  — 测试用例
source/[AgentName]/changelog.md    — 迭代优化变更记录
source/[AgentName]/.mcp.json       — MCP 服务配置
source/[AgentName]/skills/         — 专属平台 skill 源文件
source/[AgentName]/bak/            — 历史备份
source/[AgentName]/tmp/            — 中间产物
source/skills/[SkillName]/         — Skill 源文件（SKILL.md + skill.json + scripts/）
source/skill-harness-[SkillName]/  — Skill Test Harness Agent（由 create_harness.py 生成）
scripts/install.py                 — Agent 安装脚本（source → 所有 IDE 目录）
scripts/scaffold.py                — Agent 目录脚手架创建（支持 @platform 命名）
scripts/yaml_tool.py               — YAML 测试用例读写工具
scripts/create_harness.py          — Skill → Harness Agent 自动生成
scripts/trigger_test.py            — Skill 触发准确性测试
scripts/artifact_checker.py        — Skill 产物验证检查
```

---

## Agent: meta-prompt-engineer

**描述**：提示词工程专家，将理想态要求转化为运用 CoT、few-shot 等技法的高质量 Agent 提示词，也负责根据评估反馈迭代优化提示词

**提示词**：

> 请参见 `source/agents/meta-prompt-engineer/prompt.md`

---

## Agent: meta-testcase-gen

**描述**：根据 Agent 提示词和理想态描述，自动生成高质量的 YAML 测试用例

**提示词**：

> 请参见 `source/agents/meta-testcase-gen/prompt.md`

---

## Agent: meta-eval-judge

**描述**：评估 Sub Agent 输出质量的评分专家，根据评分标准和参考答案对实际输出进行打分

**提示词**：

> 请参见 `source/agents/meta-eval-judge/prompt.md`

---

## Agent: meta-retrospective

**描述**：迭代优化全局复盘专家。分析多轮提示词迭代历史，识别反模式和劣化主线，输出 forced_new_directions 供 evo_looper 步骤 C 消费。需要 bak_dir（≥2个备份文件）。

**提示词**：

> 请参见 `source/agents/meta-retrospective/prompt.md`

---

## Agent: meta-ideal-state

**描述**：根据用户提供的业务场景和需求，运用 AI Agent 理想态设计最佳实践，生成结构完整、可落地的理想态文档

**提示词**：

> 请参见 `source/agents/meta-ideal-state/prompt.md`

---

## Agent: meta-rubric-gen

**描述**：专门为 LLM-as-a-Judge 生成任务专属、可判定、可去偏的评分标准（Rubric）

**提示词**：

> 请参见 `source/agents/meta-rubric-gen/prompt.md`

---

## Agent: meta-log-converter

**描述**：平台日志转换器，将平台测试执行日志（stdout）转换为 ShareGPT 格式 JSON，支持转换脚本缓存和复用。

**提示词**：

> 请参见 `source/agents/meta-log-converter/prompt.md`

---

## Agent: meta-debug

**描述**：评估体系调试专家（Debug/Calibrate）。诊断 rubric、理想态、提示词三元组的一致性问题，从实际输出中洞察设计缺陷，输出 calibration_report.json 供人工决策。

**提示词**：

> 请参见 `source/agents/meta-debug/prompt.md`

---

<!-- 业务 Agent 章节（如 my-agent）请在本地通过 install.py 添加，不纳入版本控制 -->

## Agent: meta-reviewer

**描述**：提示词反作弊审查专家，独立审查 meta-prompt-engineer 生成的提示词是否存在作弊（抄袭 ExpectedOutput）、过拟合或泛化性不足的问题

**提示词**：

> 请参见 `source/agents/meta-reviewer/prompt.md`

---

## Agent: cls-log-agent

**描述**：腾讯云 CLS 日志检索分析专家，支持日志查询、错误分析及 APM 协同排障。

**提示词**：

> 请参见 `source/agents/cls-log-agent/prompt.md`

---

## Agent: cls-log-agent@observable

**描述**：腾讯云 CLS 日志检索分析专家（可观测平台版，Qwen3 模型）

**提示词**：

> 请参见 `source/agents/cls-log-agent@observable/prompt.md`

---

## Agent: skill-harness-platform_react_runner

**描述**：Skill Test Harness: platform_react_runner — 通过加载 platform_react_runner Skill 执行平台级 ReAct 智能体测试

**提示词**：

> 请参见 `source/agents/skill-harness-platform_react_runner/prompt.md`

---

## Agent: 歌词生成系统

**描述**：根据用户提供的歌词创作需求（主题、风格、场景、核心意象、剧情要求），生成符合要求的原创歌词

**提示词**：

> 请参见 `source/agents/歌词生成系统/prompt.md`

---

## Agent: 说唱生成系统

**描述**：中文说唱作词专家，根据主题和情感要求生成高质量原创说唱歌词

**提示词**：

> 请参见 `source/agents/说唱生成系统/prompt.md`

---

## Agent: skill-harness-cls-query

**描述**：Skill Test Harness: cls-query — 用于查询腾讯云 CLS (Cloud Log Service) 日志的 skill，基于腾讯云 SearchLog API 实现检索分析日志功能

**提示词**：

> 请参见 `source/agents/skill-harness-cls-query/prompt.md`

---

## Agent: meta-skill-harness

**描述**：通用 Skill 测试执行器壳 Agent，运行时由规则层动态注入目标 Skill 名称。不直接使用，通过 test/iterate 命令自动套壳调用。

**提示词**：

> 请参见 `source/agents/meta-skill-harness/prompt.md`

---

## Agent: 塑普歌词生成器

**描述**：将普通话歌曲歌词转换为湖南塑料普通话（湘式塑普）风格，保留原歌词的韵律和节奏

**提示词**：

> 请参见 `source/agents/塑普歌词生成器/prompt.md`

---
