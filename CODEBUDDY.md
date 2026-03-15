# Agent Factory — 项目全局规则

本文件是 Agent Factory 项目的全局规则配置。`CLAUDE.md`（Claude Code）和 `CODEBUDDY.md`（CodeBuddy CLI）内容相同，由 `install.py` 自动同步。

## 项目概述

本项目是一个 **Agent 工厂**，用于创建、测试、迭代优化 Sub Agent。核心流程由触发词驱动：

- `create_agent`（或"创建 Agent"）：创建新 Sub Agent
- `create_testcases`（或"生成用例"）：为已有 Agent 生成测试用例
- `test_agent`（或"测试 Agent"）：测试并评估 Agent 质量
- `evo_looper`（或"迭代优化"）：循环测试+优化直到达标
- `calibrate`（或"校准"、"调试"、"debug"、"诊断评估体系"）：调试三元组（提示词/理想态/rubrics）一致性，输出结构化诊断报告供人工决策

## 目录结构

```
source/[AgentName]/
├── prompt.md          # Agent 提示词（所有 IDE 同步源）
├── agent.json         # Agent 元数据（description + tools），供安装脚本使用
├── ideal_state.md     # 理想态描述
├── testcases.yaml     # 测试用例（Input/ExpectedOutput/Judge）
├── changelog.md       # 全生命周期变更日志（创建/用例/优化/手动变更均追加记录）
├── .mcp.json          # 该 Agent 的 MCP 服务配置（安装时合并到根 .mcp.json）
├── skills/            # 该 Agent 专属的平台 skill 源文件
├── bak/               # 历史备份
└── tmp/               # 测试/迭代中间产物

source/rules/          # IDE 规则文件源（.mdc），install.py 分发到各 IDE rules 目录

scripts/
├── install.py         # Agent 安装脚本（source → 所有 IDE 目录）
├── scaffold.py        # Agent 目录脚手架创建（支持 @platform 命名）
├── setup_mcp.py       # MCP 配置辅助脚本（快速配置 API 密钥）
├── platform_test.py   # 平台批量测试脚本（替代 platform_observable_tester）
├── prepare_config.py  # 平台测试配置占位符替换

.claude/agents/        # Claude Code Agent 文件
.claude/rules/         # Claude Code 规则文件（本文件所在目录）
.codebuddy/agents/     # CodeBuddy IDE Agent 文件
.codebuddy/rules/      # CodeBuddy IDE 规则文件
.cursor/agents/        # Cursor IDE Agent 文件
.cursor/rules/         # Cursor IDE 规则文件
AGENTS.md              # Codex Agent 配置文件
CLAUDE.md              # Claude Code 项目级全局规则（与 CODEBUDDY.md 同步）
CODEBUDDY.md           # CodeBuddy CLI 项目级全局规则（与 CLAUDE.md 同步）
```

## Python 运行环境

本项目使用 `venv/` 虚拟环境（Python 3.14.0）。所有 Python 命令必须使用虚拟环境中的解释器：
- `./venv/bin/python` 替代 `python`
- `./venv/bin/python3` 替代 `python3`
- `./venv/bin/pip` 替代 `pip` / `pip3`

禁止使用系统级 Python 解释器。

## 核心约束

1. **同步约束**：任何对 Agent 提示词的修改，必须通过 `./venv/bin/python scripts/install.py [AgentName]` 同步到全部四个目标（Cursor / CodeBuddy / Claude Code / Codex）。**严禁由 AI 手动逐文件同步**。
2. **备份约束**：修改 Agent 提示词、YAML 用例、理想态文件前，必须先备份到 `source/[AgentName]/bak/`。
3. **反作弊约束**：迭代优化中，严禁将测试集的 `ExpectedOutput` 内容直接写入提示词。
4. **Source 优先**：所有提示词修改先在 `source/[AgentName]/prompt.md` 中进行，再运行 `./venv/bin/python scripts/install.py` 同步到各 IDE 目录。`create_agent` 只写 source，不直接写 IDE 目录。
5. **MCP 归属**：每个 Agent 的 MCP 配置存放在 `source/[AgentName]/.mcp.json` 中，`scripts/install.py` 负责合并到根 `.mcp.json`。配置 MCP 密钥时，推荐使用 `scripts/setup_mcp.py` 辅助脚本。
6. **Skills 归属**：每个 Agent 的 skills 存放在 `source/[AgentName]/skills/` 中，`scripts/install.py` 负责复制到各 IDE skills 目录。根目录下不再保留 `skills/` 目录。
7. **Changelog 约束**：`changelog.md` 记录 Agent 全生命周期变更。`create_agent`（初始创建）、`create_testcases`（用例补充）、`evo_looper`（每轮优化）、手动修改，均须追加记录，不得覆盖。
8. **日志完整性**：IDE 模式下每条用例调用完毕后，必须当场保存 `actual_output.txt`。平台模式下 `run_log.json` 每轮迭代都必须生成，不得跳过日志转换步骤直接评估。
9. **读取用例规范**：在读取测试用例时，禁止一次性读取整个大型 `testcases.yaml` 文件。使用 `scripts/yaml_tool.py` 按需读取。示例：`./venv/bin/python scripts/yaml_tool.py get source/[AgentName]/testcases.yaml 0 --fields Input,Judge`。

## 可用 Sub Agent（基础组件）

| Agent 名称 | 职责 |
|-----------|------|
| `meta-prompt-engineer` | 编写和优化 Agent 提示词 |
| `meta-testcase-gen` | 生成 YAML 测试用例（Input 为主，Judge/ExpectedOutput 留空） |
| `meta-rubric-gen` | 为每条测试用例的 Input 生成任务专属、可判定、可去偏的 Judge 评分标准 |
| `meta-eval-judge` | 评估 Agent 输出质量（0-100 分） |
| `meta-debug` | 评估体系调试（`calibrate`）：诊断三元组（提示词/理想态/rubrics）一致性，输出 `calibration_report.json` 供人工决策 |
| `meta-retrospective` | 迭代优化全局复盘（`evo_looper` 专用）：分析多轮提示词迭代历史，识别反模式和劣化主线，输出 `forced_new_directions` |
| `meta-ideal-state` | 生成理想态文档 |
| `meta-log-converter` | 平台日志转换器（stdout → ShareGPT） |

## 可用 Sub Agent（业务 Agent）

<!-- 业务 Agent（如 my-agent）请在本地通过 install.py 添加，不纳入版本控制 -->

## 平台测试模式

`test_agent` 和 `evo_looper` 支持通过外部平台（而非 IDE Sub Agent）执行测试。Agent 名称含 `@` 时自动切换为平台模式。

平台版本通过 `@` 后缀标识（如 `my-agent@platform`），拥有独立的 `source/` 目录、独立的 prompt 迭代和测试用例。

组件：
- `scripts/platform_test.py`：批量测试脚本，读取 `platform.yaml` + `prompt.md` → 调用 `react_agent_runner.py`
- `meta-log-converter`：日志转换 Sub Agent
- `meta-eval-judge` / `meta-prompt-engineer`：评估和优化 Sub Agent（与 IDE 模式共用）

## 完整规则参考

详细的流程规则请参见各 IDE 的 rules 目录（`.claude/rules/`、`.codebuddy/rules/`、`.cursor/rules/`）。
