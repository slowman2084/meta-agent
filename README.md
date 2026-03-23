# Meta-Agent：小团队的 Agent 进化神器

**中文** | [English](README_EN.md)

AI 帮你定义理想态、生成测试用例、制定评分规则，然后自动迭代优化提示词——**你定标准，AI 自己进化**。

> 在 AI IDE（Cursor / CodeBuddy / Claude Code）中打开项目，说一句 `创建 Agent` 就能开始。

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
五句话就能跑起来：

```bash
git clone <your-repo-url> && cd meta-agent
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./venv/bin/python scripts/install.py          # 分发规则和内置 Agent
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
  │              迭代优化阶段（evo_looper）                  │
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

你只需要：
1. **描述你想要什么样的 Agent**（理想态、提示词草稿、现有对话记录，甚至只是一组测试用例）
2. **AI 自动完成剩下的一切** —— 生成提示词、测试用例、评分标准，然后循环测试和优化，直到达到你设定的分数

---

## 理想态：为什么它是一切的起点

> **理想态是选择，是责任，是核心竞争力。**

理想态描述了我们对 AI 输出结果的期望最优状态。但这不是"最好"的问题，而是"合适"的问题：

- **选择** —— Agent 是多与人交互还是静默执行？用表格呈现数据还是用图？严格执行还是多做一步？没有对错，只有选择
- **责任** —— 为用户做出选择，就是为用户承担责任。给用户过多自由就会产生认知负担，这就是"产品"的价值：通过理想态收敛这些负担
- **核心竞争力** —— 理想态就是 AI 时代的产品力。有理想态，才能定义出高质量的评分标准，才能迭代出高质量的提示词。不然一切都是空的

Meta-Agent 的全部设计都围绕这个理念：**让定义和落地理想态的成本降到足够低，低到小团队也能做。**

---

## 核心能力

| 触发词 | 功能 | 说明 |
|--------|------|------|
| `create_agent` | 创建 Agent | 支持从提示词草稿、理想态描述、YAML 用例、LLM 对话记录四种方式创建 |
| `create_testcases` | 生成测试用例 | 为已有 Agent 自动生成 YAML 测试用例和评分标准 |
| `test_agent` | 测试评估 | 逐条运行测试用例，调用 eval-judge 进行 0-100 分评分 |
| `evo_looper` | 迭代优化 | 循环「测试 → 评估 → 优化提示词」，直到达标（默认 98 分） |

---

## 七个 Meta Agent 的协作

Meta-Agent 由 7 个专职 Sub Agent 组成，形成完整的流水线：

| Agent | 职责 | 在流程中的位置 |
|-------|------|--------------|
| `meta-ideal-state` | 将业务描述转化为结构化理想态文档 | 初始化：定义"什么是好" |
| `meta-prompt-engineer` | 将理想态转化为可执行的 Agent 提示词，运用 CoT、few-shot 等工程技法 | 初始化 + 迭代优化 |
| `meta-testcase-gen` | 推断用户画像，生成覆盖多场景的 YAML 测试用例 | 初始化 |
| `meta-rubric-gen` | 为每条用例生成原子化、可判定的评分标准 | 初始化 |
| `meta-eval-judge` | 根据评分标准对 Agent 输出进行严格评分（0-100） | 测试 + 迭代 |
| `meta-retrospective` | 分析多轮迭代历史，识别劣化模式，提出新优化方向 | 迭代复盘 |
| `meta-log-converter` | 将各平台执行日志转换为统一的 ShareGPT 格式 | 测试辅助 |

---

## 快速开始

### 方式 A：AI 辅助初始化（推荐）

在支持的 IDE 中打开项目，直接让 AI 初始化：

```
请阅读 SETUP.md，帮我初始化这个项目
```

AI 会自动完成环境配置、依赖安装、规则和 Agent 分发。

### 方式 B：手动初始化

```bash
# 1. 克隆并安装
git clone <your-repo-url>
cd meta-agent
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 2. 分发规则和内置 Agent 到所有 IDE 目录
./venv/bin/python scripts/install.py

# 3. 验证
./venv/bin/python scripts/verify_setup.py
```

### 开始使用

在 IDE 对话中直接输入触发词即可：

```
创建 Agent                    # 开始创建流程，AI 会引导你选择方式
测试 Agent my-agent           # 测试指定 Agent
迭代优化 my-agent             # 循环优化直到达标
```

> 也支持英文触发词：`create_agent`、`test_agent`、`evo_looper`

### 配置 MCP 服务（可选）

如果 Agent 需要调用外部服务（如日志查询），配置 MCP：

```bash
# 使用辅助脚本快速配置
./venv/bin/python scripts/setup_mcp.py my-agent --template cls \
    --env CLS_SECRET_ID=AKIDxxxxx --env CLS_SECRET_KEY=xxxxx

# 或手动配置
cp .mcp.json.example .mcp.json && vim .mcp.json
```

---

## 目录结构

```
meta-agent/
├── source/                       # 🔑 唯一真相来源（Source of Truth）
│   ├── rules/                    #   全局编排规则（.mdc）
│   └── [AgentName]/              #   每个 Agent 的完整源文件
│       ├── prompt.md             #     提示词
│       ├── ideal_state.md        #     理想态描述
│       ├── testcases.yaml        #     测试用例（Input / ExpectedOutput / Judge）
│       ├── agent.json            #     元数据（描述 + 工具语义）
│       ├── changelog.md          #     全生命周期变更记录
│       └── bak/                  #     历史备份
│
├── scripts/                      # 自动化脚本
│   ├── install.py                #   Agent 安装（source → 四个 IDE 目录）
│   ├── scaffold.py               #   创建 Agent 目录脚手架
│   ├── setup_mcp.py              #   MCP 快速配置
│   ├── verify_setup.py           #   初始化验证
│   └── platform_test.py          #   平台批量测试
│
├── tools/                        # 人工辅助工具
│   └── testcase_viewer.html      #   测试用例可视化审阅
│
├── .cursor/                      # ┐
├── .codebuddy/                   # ├─ 由 install.py 自动生成，勿手动修改
├── .claude/                      # │  （agents/ + rules/ + skills/）
├── AGENTS.md                     # ┘
│
├── SETUP.md                      # AI 可执行的初始化指南
├── CLAUDE.md                     # Claude Code 全局规则
└── CODEBUDDY.md                  # CodeBuddy 项目记忆
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

```bash
# 安装/同步指定 Agent
./venv/bin/python scripts/install.py [AgentName]

# 安装全部 Agent
./venv/bin/python scripts/install.py
```

---

## 关键设计约束

| 约束 | 说明 | 为什么 |
|------|------|--------|
| **Source 优先** | 所有修改在 `source/` 中进行，通过 `install.py` 同步 | 保证四个 IDE 一致性 |
| **必须备份** | 修改前备份到 `bak/` 目录 | 支持迭代回退和复盘 |
| **反作弊** | 严禁将 `ExpectedOutput` 植入提示词 | 防止过拟合，确保泛化能力 |
| **Changelog 追加** | 创建、用例、优化、手动变更均追加记录 | 迭代历史可追溯 |
| **敏感信息隔离** | `.mcp.json`、`.env`、`platform.yaml` 已加入 `.gitignore` | 不泄露 API 密钥 |

---

## 常用命令速查

```bash
# 创建 Agent 目录脚手架
./venv/bin/python scripts/scaffold.py [AgentName] -d "描述" -t "read,write"

# 安装/同步 Agent 到所有 IDE
./venv/bin/python scripts/install.py [AgentName]

# 平台批量测试（用 @ 后缀标识平台版本）
./venv/bin/python scripts/platform_test.py [AgentName]@[platform]

# CLI 自检
./scripts/selftest.sh <agent_name> --cli claude --cases 3

# 初始化验证
./venv/bin/python scripts/verify_setup.py
```

---

## 贡献指南

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## License

MIT License
