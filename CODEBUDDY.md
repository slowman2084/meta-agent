# Agent Factory — 项目全局规则

本文件是 Agent Factory 项目的全局规则配置。`CLAUDE.md`（Claude Code）和 `CODEBUDDY.md`（CodeBuddy CLI）内容相同，由 `install.py` 自动同步。

## 项目概述

本项目是一个 **Agent 工厂**，用于创建、测试、迭代优化 Sub Agent。核心流程由触发词驱动，详见 `agent-factory.mdc` 规则。

触发词速查：`create agent` / `create testcases` / `test` / `iterate` / `calibrate` / `create skill` / `create platformskill`

## 目录结构

```
source/agents/[AgentName]/      # Agent 源文件（prompt.md / agent.json / testcases.yaml / ...）
source/agents/meta-skill-harness/ # 通用 Skill 测试壳 Agent
source/skills/[SkillName]/      # Skill 源文件（SKILL.md + skill.json + scripts/ + testcases.yaml）
source/rules/                    # IDE 规则文件源（.mdc）
scripts/                         # 工具脚本（install.py / scaffold.py / yaml_tool.py）
.<ide>/agents/                   # 各 IDE 的 Agent 文件（由 install.py 自动生成）
.<ide>/rules/                    # 各 IDE 的规则文件
.<ide>/skills/                   # 各 IDE 的 Skills
AGENTS.md                        # Codex Agent 配置文件
```

## Python 运行环境

本项目使用 `venv/` 虚拟环境（Python 3.14.0）。所有 Python 命令必须使用虚拟环境中的解释器：
- `./venv/bin/python` 替代 `python`
- `./venv/bin/python3` 替代 `python3`
- `./venv/bin/pip` 替代 `pip` / `pip3`

禁止使用系统级 Python 解释器。

## 核心约束（精简版，详见 agent-factory.mdc）

1. **同步约束**：提示词修改必须通过 `./venv/bin/python scripts/install.py [Name]` 同步。**严禁手动逐文件同步**。
2. **备份约束**：修改前必须先备份到对应目录的 `bak/`。
3. **反作弊约束**：严禁将 `ExpectedOutput` 写入提示词。
4. **Source 优先**：所有修改先在 `source/` 中进行。
5. **读取用例规范**：使用 `scripts/yaml_tool.py` 按需读取，禁止一次性读取整个大型 YAML。

## 完整规则参考

详细的流程规则、Sub Agent 调速查表、安装子流程等请参见 `agent-factory.mdc`（alwaysApply）及各按需加载的子规则。
