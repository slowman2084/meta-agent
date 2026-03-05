# Agent Factory — Meta-Agent

**中文** | [English](README_EN.md)

一个多 IDE 兼容的 **Agent 工厂**，用于创建、测试、迭代优化 AI Sub Agent。

通过「一处编写，四处同步」的架构，让同一套 Agent 在 **Cursor、CodeBuddy、Claude Code、Codex** 四个 IDE 环境中无缝运行。

---

## ✨ 核心能力

| 触发词 | 功能 | 说明 |
|--------|------|------|
| `#create_agent` | 创建 Agent | 支持从提示词草稿、理想态描述、CSV 用例、LLM 对话记录四种方式创建 |
| `#create_testcases` | 生成测试用例 | 为已有 Agent 自动生成 YAML 测试用例 |
| `#test_agent` | 测试评估 | 逐条运行测试用例，调用 eval-judge 进行 0-100 分评分 |
| `#evo_looper` | 迭代优化 | 循环「测试 → 评估 → 优化提示词」，直到达标 |

---

## 🚀 快速开始

### 方式 A：AI 辅助初始化（推荐）

在支持的 IDE 中打开项目，直接让 AI 阅读 `SETUP.md` 并按步骤初始化：

```
请阅读 SETUP.md，帮我初始化这个项目
```

AI 会自动执行环境配置、依赖安装、MCP 配置等步骤。

### 方式 B：手动初始化

#### 1. 环境准备

```bash
# 克隆仓库
git clone <your-repo-url>
cd meta-agent

# 创建虚拟环境
python3 -m venv venv

# 安装依赖
./venv/bin/pip install -r requirements.txt

# 验证安装
./venv/bin/python scripts/verify_setup.py
```

#### 2. 配置 MCP 服务（可选）

如果需要使用 MCP 服务（如日志查询），需要配置 `.mcp.json`：

```bash
# 复制示例配置
cp .mcp.json.example .mcp.json

# 编辑配置，填入你的 API 密钥
vim .mcp.json
```

#### 3. 在 IDE 中使用

在支持的 IDE（Cursor / CodeBuddy / Claude Code）中打开项目，直接在对话中输入触发词：

```
#create_agent      # 创建新 Agent
#test_agent my-agent    # 测试指定 Agent
#evo_looper code-reviewer     # 迭代优化 Agent
```

#### 4. CLI 自检（可选）

```bash
./scripts/selftest.sh <agent_name> --cli claude --cases 3
```

---

## 📁 目录结构

```
meta-agent/
├── README.md                     # 本文件
├── SETUP.md                      # AI 可执行的初始化指南
├── requirements.txt              # Python 依赖
├── .mcp.json.example             # MCP 配置示例（不含密钥）
│
├── source/                       # 🔑 Agent 源文件（核心资产）
│   └── [AgentName]/
│       ├── prompt.md             #   Agent 提示词
│       ├── ideal_state.md        #   理想态描述
│       ├── testcases.yaml        #   测试用例
│       ├── changelog.md          #   变更记录
│       ├── agent.json            #   元数据
│       └── bak/                  #   历史备份
│
├── scripts/                      # 自动化脚本
│   ├── install.py                #   Agent 安装（source → IDE 目录）
│   ├── scaffold.py               #   创建 Agent 目录脚手架
│   ├── verify_setup.py           #   初始化状态验证
│   └── platform_test.py          #   平台批量测试
│
├── tools/                        # 人工辅助工具
│   └── testcase_viewer.html      #   测试用例可视化审阅工具
│
├── .cursor/                      # Cursor IDE 配置
│   ├── agents/                   #   Sub Agent 文件
│   └── rules/                    #   编排规则
│
├── .codebuddy/                   # CodeBuddy IDE 配置
│   ├── agents/                   #   Sub Agent 文件
│   └── rules/                    #   编排规则
│
├── .claude/                      # Claude Code 配置
│   ├── agents/                   #   Sub Agent 文件
│   └── rules/                    #   编排规则
│
├── AGENTS.md                     # Codex Agent 配置
├── CLAUDE.md                     # Claude Code 全局规则
└── CODEBUDDY.md                  # CodeBuddy 项目记忆
```

---

## 🤖 已注册的 Sub Agent

### 基础组件（meta-* 系列）

| Agent | 职责 |
|-------|------|
| `meta-prompt-engineer` | 提示词工程专家，编写和优化 Agent 提示词 |
| `meta-testcase-gen` | 自动生成 YAML 测试用例 |
| `meta-rubric-gen` | 为测试用例生成评分标准 |
| `meta-eval-judge` | 评估 Agent 输出质量（0-100 分） |
| `meta-retrospective` | 多轮迭代复盘分析 |
| `meta-ideal-state` | 生成 Agent 理想态文档 |
| `meta-log-converter` | 平台日志转换器 |

### 业务 Agent

<!-- 业务 Agent 需自行创建，参见下方"创建你的 Agent"章节 -->

---

## 🔧 常用命令

```bash
# 安装/同步 Agent 到所有 IDE
./venv/bin/python scripts/install.py [AgentName]

# 创建新 Agent 目录脚手架
./venv/bin/python scripts/scaffold.py [AgentName] -d "Agent 描述" -t "read,write"

# 平台批量测试
./venv/bin/python scripts/platform_test.py [AgentName]@[platform]
```

---

## 🌐 多 IDE 兼容设计

同一个 Agent 提示词在不同 IDE 中自动适配文件头格式：

| IDE | Model 配置 | MCP 声明方式 |
|-----|------------|-------------|
| Cursor | `claude-sonnet-4-5` | 不支持文件头声明 |
| CodeBuddy | `minimax-m2.5` | `mcpTools: 服务名` |
| Claude Code | `sonnet` | `mcpServers: [服务名]` |
| Codex | 无文件头 | 章节形式写入 AGENTS.md |

---

## ⚠️ 重要约束

1. **同步约束**：修改提示词必须先在 `source/` 中进行，再通过 `scripts/install.py` 同步
2. **备份约束**：修改文件前必须备份到 `bak/` 目录
3. **反作弊约束**：迭代优化中严禁将 `ExpectedOutput` 植入提示词
4. **敏感信息**：`.mcp.json` 包含 API 密钥，已加入 `.gitignore`，请勿提交

---

## 📝 贡献指南

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'Add some feature'`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

---

## 📄 License

MIT License
