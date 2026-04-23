# Agent Factory — 项目全局配置

本文件是 Agent Factory 项目的全局配置。`CLAUDE.md`（Claude Code）和 `CODEBUDDY.md`（CodeBuddy CLI）内容相同，由 `install.py` 自动同步。

## 项目概述

本项目是一个 **Agent 工厂**，用于创建、测试、迭代优化 Sub Agent。核心流程由编排 Skill（meta-iterate / meta-plan 等）驱动。

触发词速查：`create agent` / `create testcases` / `test` / `iterate` / `calibrate` / `create skill` / `create platformskill` / `enrich`（为已有 Skill 补全理想态+测试用例） / `下一步`（基于状态给出建议）

## 目录结构

```
source/agents/[AgentName]/      # Agent 源文件（prompt.md / agent.json / testcases.yaml / ...）
source/agents/meta-skill-harness/ # 通用 Skill 测试壳 Agent
source/skills/[SkillName]/      # Skill 源文件（SKILL.md + skill.json + scripts/ + testcases.yaml）
scripts/                         # 工具脚本（install.py / scaffold.py / yaml_tool.py / learnings_tool.py / context_tool.py / status_tool.py）
.<ide>/agents/                   # 各 IDE 的 Agent 文件（由 install.py 自动生成）
.<ide>/skills/                   # 各 IDE 的 Skills
AGENTS.md                        # Codex Agent 配置文件
```

## Python 运行环境

本项目使用 `venv/` 虚拟环境（Python 3.14.0）。所有 Python 命令必须使用虚拟环境中的解释器：
- `./venv/bin/python` 替代 `python`
- `./venv/bin/python3` 替代 `python3`
- `./venv/bin/pip` 替代 `pip` / `pip3`

禁止使用系统级 Python 解释器。

## 核心约束

1. **同步约束**：提示词修改必须通过 `./venv/bin/python scripts/install.py [Name]` 同步。**严禁手动逐文件同步**。
2. **备份约束**：修改前必须先备份到对应目录的 `bak/`。
3. **反作弊约束**：严禁将 `ExpectedOutput` 写入提示词。
4. **Source 优先**：所有修改先在 `source/` 中进行。
5. **读取用例规范**：使用 `scripts/yaml_tool.py` 按需读取，禁止一次性读取整个大型 YAML。

## 工具脚本速查

| 脚本 | 用途 |
|------|------|
| `scripts/install.py` | Agent/Skill/Platform Skills 安装分发 |
| `scripts/scaffold.py` | Agent 目录脚手架创建 |
| `scripts/yaml_tool.py` | YAML 测试用例按需读写 |
| `scripts/learnings_tool.py` | 结构化经验 JSONL（log/search/count） |
| `scripts/context_tool.py` | 自动上下文恢复（recover/summary） |
| `scripts/status_tool.py` | Agent/Skill 状态索引（get/set/sync/summary） |
| `scripts/create_harness.py` | Skill 测试壳 Agent 创建 |
| `scripts/artifact_checker.py` | 产物完整性检查 |
| `scripts/multimodel_inject.py` | 多模型对比数据注入 HTML |
| `scripts/calibration_inject.py` | 校准诊断数据注入 HTML |

## 完整流程参考

详细的流程规则、Sub Agent 调速查表、安装子流程等请参见对应的编排 Skill（meta-iterate / meta-plan 等 SKILL.md）。
