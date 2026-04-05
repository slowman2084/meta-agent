# Meta-Agent Setup Guide (AI-Executable)

> **Target Audience**: This document is designed for AI assistants to read and execute, guiding users through the initial setup of the meta-agent project in a new environment.

---

## Document Scope & Relationship to Rules

This `SETUP.md` focuses on **one-time initialization** of a freshly cloned repository. It is distinct from the project's rule files:

| Document | Scope | When to Use |
|----------|-------|-------------|
| **SETUP.md** (this file) | Initial environment setup | First-time clone, new machine |
| `source/rules/python-env.mdc` | Python command conventions | All Python operations |
| `source/rules/agent-factory.mdc` | Agent create/test/iterate workflow | `#create_agent`, `#test_agent`, `#evo_looper` |
| `source/rules/af-skill-harness.mdc` | Skill creation via Harness Agent (Plan D) | `#create_skill` |
| `source/rules/header-format.mdc` | IDE file header formats | Creating/syncing Agent files |

**Architecture Overview**:

```
source/                          ← 唯一真相来源（Source of Truth）
├── rules/                       ← 全局规则（.mdc 格式）
│   ├── agent-factory.mdc        ← 总控编排规则
│   ├── header-format.mdc        ← 各 IDE 文件头格式映射
│   └── python-env.mdc           ← Python 虚拟环境规范
├── meta-prompt-engineer/        ← 内置 Sub Agent（提示词工程专家）
├── meta-testcase-gen/           ← 内置 Sub Agent（测试用例生成器）
├── meta-eval-judge/             ← 内置 Sub Agent（评估评分专家）
├── meta-rubric-gen/             ← 内置 Sub Agent（评分标准生成器）
├── meta-ideal-state/            ← 内置 Sub Agent（理想态文档生成器）
├── meta-retrospective/          ← 内置 Sub Agent（迭代复盘专家）
└── meta-log-converter/          ← 内置 Sub Agent（日志格式转换器）

        ┌──── install.py ────┐
        │    一键分发到各 IDE   │
        ▼                    ▼
.cursor/                 .codebuddy/              .claude/
├── rules/               ├── rules/               ├── rules/
│   ├── agent-factory.mdc│   ├── agent-factory.mdc│   ├── agent-factory.mdc
│   ├── header-format.mdc│   ├── header-format.mdc│   ├── header-format.mdc
│   └── python-env.mdc   │   └── python-env.mdc   │   └── python-env.mdc
├── agents/              ├── agents/              ├── agents/
│   ├── meta-prompt-     │   ├── meta-prompt-     │   ├── meta-prompt-
│   │   engineer.md      │   │   engineer.md      │   │   engineer.md
│   └── ...              │   └── ...              │   └── ...
└── skills/              └── skills/              └── skills/
```

**Lifecycle Summary**:
1. **SETUP.md (Steps 1-3)**: Create venv → Install deps → Run `install.py` to distribute Rules + built-in Agents
2. **agent-factory.mdc (ongoing)**: Once rules are installed, AI follows `agent-factory.mdc` for `#create_agent`, `#test_agent`, `#evo_looper` workflows
3. **install.py**: The bridge — called by SETUP.md for initial setup, then called by `agent-factory.mdc` every time an Agent is created/updated

---

## Pre-flight Checklist

Before starting, verify the following prerequisites:

| Requirement | Minimum Version | Check Command |
|-------------|-----------------|---------------|
| Python | 3.10+ | `python3 --version` |
| pip | latest | `pip3 --version` |
| Node.js | 18+ (optional, for MCP) | `node --version` |
| npm | 9+ (optional, for MCP) | `npm --version` |
| Git | any | `git --version` |

---

## Setup Workflow

Execute the following steps **in order**. Steps 1-3 are **mandatory**; Steps 4-6 are optional.

### Step 1: Create Python Virtual Environment

**Purpose**: Isolate project dependencies from system Python.

```bash
# Navigate to project root
cd <project_root>

# Create virtual environment
python3 -m venv venv

# Verify creation
ls -la venv/bin/python
```

**Success Criteria**: File `venv/bin/python` exists.

**Post-setup Note**: All subsequent Python commands MUST use `./venv/bin/python` instead of `python` or `python3`. This is enforced by `source/rules/python-env.mdc`.

---

### Step 2: Install Python Dependencies

**Purpose**: Install required packages for LangGraph, MCP integration, and utilities.

```bash
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

**Verification**:
```bash
./venv/bin/python -c "import langchain_core; import langgraph; import mcp; print('✅ Core dependencies OK')"
```

**Success Criteria**: No import errors, prints "✅ Core dependencies OK".

---

### Step 3: Distribute Rules & Built-in Agents ⭐

**Purpose**: Run `install.py` to distribute all content from `source/` to the IDE directories where the AI can discover and use them.

This step does two things:
1. **Rules distribution**: Copies `source/rules/*.mdc` → `.cursor/rules/` and `.codebuddy/rules/`, enabling the AI to follow project conventions (`agent-factory.mdc`, `python-env.mdc`, `header-format.mdc`)
2. **Agent distribution**: Generates platform-specific agent files for all 7 built-in `meta-*` Sub Agents, writing them to `.cursor/agents/`, `.codebuddy/agents/`, `.claude/agents/`, and `AGENTS.md`

```bash
./venv/bin/python scripts/install.py
```

**Verification**:
```bash
# Check rules are distributed
ls .cursor/rules/*.mdc .codebuddy/rules/*.mdc .claude/rules/*.mdc

# Check agents are distributed
ls .cursor/agents/meta-*.md .codebuddy/agents/meta-*.md .claude/agents/meta-*.md
```

**Success Criteria**:
- 3 `.mdc` rule files exist in `.cursor/rules/`, `.codebuddy/rules/`, and `.claude/rules/`
- 7 `meta-*.md` agent files exist in each of the 3 IDE agent directories

**What this enables**: After this step, the AI can:
- Follow `agent-factory.mdc` for `#create_agent`, `#test_agent`, `#evo_looper` workflows
- Call built-in Sub Agents (`meta-prompt-engineer`, `meta-eval-judge`, etc.) as defined in the workflow
- Use `python-env.mdc` to enforce correct Python command conventions

> **Note**: This is a one-time setup step. After initial setup, `install.py` is called automatically by `agent-factory.mdc` workflows whenever an Agent is created or updated (see Section "Ongoing Usage" below).

---

### Step 4: Configure Environment Variables (Optional but Recommended)

> **Recommended** for DSPy optimization and platform testing.

**Purpose**: Set up API keys and sensitive configuration securely.

#### 4.1 Create Environment File

Create `.env` at project root based on the example template:

```bash
cp .env.example .env
```

#### 4.2 Configure API Keys

Edit `.env` and fill in your actual API keys:

```bash
# DSPy Configuration (for prompt optimization)
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# Optional: Specify DSPy model
DSPY_MODEL=openai/gpt-4
```

**Important Security Notes**:
- ⚠️ **NEVER commit `.env` to Git** - it's in `.gitignore` for a reason
- Each team member should maintain their own `.env` file locally
- Use `.env.example` as a template to share configuration structure
- API keys should be treated as secrets and rotated regularly

**User Prompt Template**:
```
请提供以下信息以配置环境变量：
1. OpenAI API Key：
2. API Base URL（默认：https://api.openai.com/v1）：
```

**Verification**:
```bash
# Check .env file exists
ls .env

# Test loading (Python)
./venv/bin/python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('✅ OPENAI_API_KEY:', 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET')"
```

**Success Criteria**: `.env` file exists and contains non-placeholder values.

---

### Step 5: Configure MCP Services (Optional)

> **Skip this step** if the user does not need MCP services (e.g., CLS log queries).

**Purpose**: Set up Model Context Protocol servers for external service integration.

#### 5.1 Create MCP Configuration

Create `.mcp.json` at project root based on the example template:

```bash
cp .mcp.json.example .mcp.json
```

#### 5.2 Edit Configuration

Open `.mcp.json` and replace placeholder values with your MCP server configuration:

```json
{
  "mcpServers": {
    "your-mcp-server": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "your-mcp-server@latest"],
      "env": {
        "TRANSPORT": "stdio",
        "API_KEY": "<REPLACE_WITH_YOUR_API_KEY>",
        "API_SECRET": "<REPLACE_WITH_YOUR_API_SECRET>"
      },
      "disabled": false
    }
  }
}
```

**User Prompt Template**:
```
请提供以下信息以配置 MCP 服务：
1. MCP 服务名称：
2. API Key：
3. API Secret：
```

**Verification** (if Node.js installed):
```bash
# Test your MCP server installation
npx -y your-mcp-server@latest --help 2>/dev/null && echo "✅ MCP server available" || echo "⚠️ MCP server not available (optional)"
```

**Important**: The `.mcp.json` file is in `.gitignore` and will NOT be committed. This is intentional for security.

---

### Step 6: Configure DSPy Optimization (Optional)

> **Skip this step** if you don't plan to use DSPy for prompt optimization.

**Purpose**: Configure DSPy for data-driven prompt optimization.

#### 6.1 Prerequisites

- ✅ DSPy installed (via Step 2: `pip install -r requirements.txt`)
- ✅ `.env` configured with `OPENAI_API_KEY` (from Step 4)

#### 6.2 Verify DSPy Setup

```bash
# Test DSPy with environment variables
./venv/bin/python -c "
import os
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
print('✅ DSPy Ready' if api_key and api_key != 'your-openai-api-key-here' else '❌ Configure OPENAI_API_KEY in .env')
"
```

#### 6.3 Using DSPy Optimization

Once configured, you can use DSPy in two ways:

**Option A: Standalone Optimization**
```bash
# Basic optimization
./venv/bin/python scripts/dspy_optimizer.py --agent meta-rubric-gen

# Advanced optimization with custom model
./venv/bin/python scripts/dspy_optimizer.py \
  --agent meta-rubric-gen \
  --model openai/gpt-4 \
  --optimizer bootstrap \
  --max-demos 4
```

**Option B: Integrated in evo_looper**

During iterative optimization, say:
```
"对 [agent-name] 进行迭代优化，使用 DSPy 模式"
```

The AI will automatically:
1. Load environment variables from `.env`
2. Run DSPy optimization
3. Test and evaluate the optimized prompt

**Documentation**: See `scripts/DSPY_INTEGRATION.md` for detailed usage guide.

---

### Step 7: Configure Platform Testing (Optional)

> **Skip this step** if the user does not need platform-based Agent testing.

**Purpose**: Set up configuration for running Agent tests against external LLM platforms.

#### 5.1 Create Platform Agent Directory

Use the scaffold script to create the directory structure:

```bash
./venv/bin/python scripts/scaffold.py <AgentName>@<platform> -d "Agent description"
```

Example:
```bash
./venv/bin/python scripts/scaffold.py my-agent@observable -d "My custom agent for observable platform"
```

#### 5.2 Configure Platform YAML

Edit `source/<AgentName>@<platform>/platform.yaml`:

```yaml
llm:
  model: "<your-model-name>"
  api_key: "<your-api-key>"
  base_url: "<your-platform-url>/v1"
  temperature: 0.7

prompts:
  custom_system_prompt: |
    {{PROMPT}}
```

**User Prompt Template**:
```
请提供平台测试配置：
1. 模型名称（如 gpt-4, claude-3）：
2. API Key：
3. API Base URL：
```

**Important**: The `platform.yaml` file is in `.gitignore` and will NOT be committed.

---

### Step 8: Create Your First Agent (Optional)

> **Skip this step** if the user already has Agent prompts to use, or wants to use `#create_agent` workflow (which is governed by `agent-factory.mdc`, now installed in Step 3).

**Purpose**: Create a new Agent using the scaffold system.

#### 6.1 Run Scaffold Script

```bash
./venv/bin/python scripts/scaffold.py <AgentName> -d "Agent description" -t "read,write"
```

**Parameters**:
- `<AgentName>`: Name of the agent (lowercase, hyphens allowed)
- `-d`: One-line description
- `-t`: Tool semantics, comma-separated. Options: `read`, `write`, `edit`, `search`, `bash`

**Example**:
```bash
./venv/bin/python scripts/scaffold.py code-reviewer -d "Code review assistant" -t "read,search"
```

#### 6.2 Populate Agent Files

After scaffold, manually create these files in `source/<AgentName>/`:

| File | Purpose | Required |
|------|---------|----------|
| `prompt.md` | Agent system prompt | ✅ Yes |
| `ideal_state.md` | Expected behavior description | ✅ Yes |
| `testcases.yaml` | Test cases (Input/ExpectedOutput/Judge) | Optional |

#### 6.3 Install Agent to IDEs

Sync the agent to all IDE directories:

```bash
./venv/bin/python scripts/install.py <AgentName>
```

**Verification**:
```bash
ls -la .cursor/agents/<AgentName>.md
ls -la .codebuddy/agents/<AgentName>.md
ls -la .claude/agents/<AgentName>.md
```

**Success Criteria**: Agent files exist in all three IDE directories.

---

## Configuration Files Summary

| File | Git Status | Contains Secrets | Action Required |
|------|------------|------------------|-----------------|
| `source/rules/*.mdc` | ✅ Tracked | ❌ No | Distributed by `install.py` (Step 3) |
| `source/meta-*/` | ✅ Tracked | ❌ No | Distributed by `install.py` (Step 3) |
| `.cursor/rules/`, `.codebuddy/rules/` | 🚫 Ignored | ❌ No | Generated by `install.py` |
| `.cursor/agents/`, `.codebuddy/agents/`, `.claude/agents/` | 🚫 Ignored | ❌ No | Generated by `install.py` |
| `.env` | 🚫 Ignored | ✅ Yes | Create from `.env.example` (Step 4) |
| `.env.example` | ✅ Tracked | ❌ No | Template only (no real keys) |
| `.mcp.json` | 🚫 Ignored | ✅ Yes | Create from `.mcp.json.example` (Step 5) |
| `source/*/.mcp.json` | 🚫 Ignored | ✅ Yes | Create per-agent if needed |
| `**/platform.yaml` | 🚫 Ignored | ✅ Yes | Create for platform agents |
| `venv/` | 🚫 Ignored | ❌ No | Create via `python3 -m venv venv` |

---

## Quick Verification Script

Use the built-in verification script to check setup status:

```bash
# Human-readable output
./venv/bin/python scripts/verify_setup.py

# JSON output (for AI parsing)
./venv/bin/python scripts/verify_setup.py --json

# Attempt auto-fix for some issues
./venv/bin/python scripts/verify_setup.py --fix
```

**Sample JSON Output**:
```json
{
  "results": [...],
  "summary": {
    "total": 8,
    "pass": 7,
    "fail": 0,
    "warn": 1,
    "skip": 0,
    "all_pass": true
  }
}
```

**AI Usage**: Call `verify_setup.py --json` and parse the output to determine which steps need attention.

---

## Ongoing Usage: How SETUP.md and agent-factory.mdc Work Together

After initial setup, the following lifecycle applies:

```
┌─────────────────────────────────────────────────────────────────────┐
│  SETUP.md (one-time)                                                │
│  Step 1: venv → Step 2: deps → Step 3: install.py (rules + agents) │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  agent-factory.mdc (ongoing, loaded by IDE from .cursor/rules/)     │
│                                                                     │
│  #create_agent  → scaffold.py → write prompt/ideal/testcases        │
│                  → install.py [AgentName]  (distribute new agent)    │
│                                                                     │
│  #test_agent    → install.py [AgentName]  (ensure latest version)   │
│                  → run tests → generate report                      │
│                                                                     │
│  #evo_looper    → install.py [AgentName]  (after each optimization) │
│                  → test → optimize → install → repeat               │
└─────────────────────────────────────────────────────────────────────┘
```

**Key distinction**:
- `SETUP.md` runs `install.py` **without arguments** → installs ALL rules + ALL agents (bootstrapping)
- `agent-factory.mdc` runs `install.py [AgentName]` → installs ONLY the specified agent (incremental update)

---

## Troubleshooting

### Issue: `python3 -m venv venv` fails

**Cause**: Missing `python3-venv` package on some Linux distributions.

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-venv

# Then retry
python3 -m venv venv
```

### Issue: Import errors after `pip install`

**Cause**: Using system Python instead of venv.

**Solution**: Always use `./venv/bin/python` not `python`:
```bash
# Wrong
python scripts/install.py

# Correct
./venv/bin/python scripts/install.py
```

### Issue: MCP server connection fails

**Cause**: Node.js not installed or wrong credentials.

**Solution**:
1. Install Node.js 18+
2. Verify credentials in `.mcp.json`
3. Test your MCP server: `npx -y your-mcp-server@latest --help`

### Issue: Agent not appearing in IDE

**Cause**: `install.py` not run after creating/modifying agent.

**Solution**:
```bash
./venv/bin/python scripts/install.py <AgentName>
```

### Issue: Rules not loaded by IDE

**Cause**: Rules not distributed to IDE directories.

**Solution**:
```bash
./venv/bin/python scripts/install.py --rules-only
```

---

## Next Steps After Setup

Once setup is complete, the user can:

1. **Create a new Agent**: Say "创建 Agent" or `#create_agent`
2. **Test an existing Agent**: Say "测试 Agent" or `#test_agent <AgentName>`
3. **Iterate on an Agent**: Say "迭代优化" or `#evo_looper <AgentName>`

These workflows are governed by `agent-factory.mdc` (now installed to your IDE's rules directory). Refer to `README.md` for detailed usage instructions.

---

## AI Execution Notes

When executing this setup guide:

1. **Execute Steps 1-3 sequentially** - each step depends on the previous
2. **Verify each step** before proceeding to the next
3. **Step 3 is the final mandatory step** - after it, rules and built-in agents are ready
4. **Steps 4-6 are optional** - prompt user only if needed
5. **Prompt user for secrets** - never hardcode API keys
6. **Use provided scripts** - `scaffold.py` and `install.py` ensure consistency
7. **Respect `.gitignore`** - generated config files should match ignore patterns
8. **Report progress** - inform user after each major step completion

**Example interaction flow**:
```
AI: 我将帮助你初始化 meta-agent 项目。首先检查 Python 环境...
AI: ✅ Python 3.11 已检测到。正在创建虚拟环境...
AI: ✅ 虚拟环境创建完成。正在安装依赖...
AI: ✅ 依赖安装完成。正在分发 Rules 和内置 Agent 到各 IDE 目录...
AI: ✅ 3 条规则 + 7 个内置 Agent 已分发到所有 IDE 目录。
AI: 基础环境初始化完成！是否需要配置 MCP 服务？(y/n)
```
