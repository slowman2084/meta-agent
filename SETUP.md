# Meta-Agent Setup Guide (AI-Executable)

> **Target Audience**: This document is designed for AI assistants to read and execute, guiding users through the initial setup of the meta-agent project in a new environment.

---

## Document Scope & Relationship to Rules

This `SETUP.md` focuses on **one-time initialization** of a freshly cloned repository. It is distinct from the project's rule files:

| Document | Scope | When to Use |
|----------|-------|-------------|
| **SETUP.md** (this file) | Initial environment setup | First-time clone, new machine |
| `.cursor/rules/python-env.mdc` | Python command conventions | All Python operations |
| `.cursor/rules/agent-factory.mdc` | Agent create/test/iterate workflow | `#create_agent`, `#test_agent`, `#evo_looper` |
| `.cursor/rules/header-format.mdc` | IDE file header formats | Creating/syncing Agent files |

**Key Principle**: SETUP.md creates the environment; rule files govern ongoing development.

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

Execute the following steps **in order**. Each step has verification criteria.

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

**Post-setup Note**: All subsequent Python commands MUST use `./venv/bin/python` instead of `python` or `python3`. This is enforced by project rules.

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

### Step 3: Configure MCP Services (Optional)

> **Skip this step** if the user does not need MCP services (e.g., CLS log queries).

**Purpose**: Set up Model Context Protocol servers for external service integration.

#### 3.1 Create MCP Configuration

Create `.mcp.json` at project root based on the example template:

```bash
cp .mcp.json.example .mcp.json
```

#### 3.2 Edit Configuration

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

### Step 4: Configure Platform Testing (Optional)

> **Skip this step** if the user does not need platform-based Agent testing.

**Purpose**: Set up configuration for running Agent tests against external LLM platforms.

#### 4.1 Create Platform Agent Directory

Use the scaffold script to create the directory structure:

```bash
./venv/bin/python scripts/scaffold.py <AgentName>@<platform> -d "Agent description"
```

Example:
```bash
./venv/bin/python scripts/scaffold.py my-agent@observable -d "My custom agent for observable platform"
```

#### 4.2 Configure Platform YAML

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

### Step 5: Create Your First Agent (Optional)

> **Skip this step** if the user already has Agent prompts to use.

**Purpose**: Create a new Agent using the scaffold system.

#### 5.1 Run Scaffold Script

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

#### 5.2 Populate Agent Files

After scaffold, manually create these files in `source/<AgentName>/`:

| File | Purpose | Required |
|------|---------|----------|
| `prompt.md` | Agent system prompt | ✅ Yes |
| `ideal_state.md` | Expected behavior description | ✅ Yes |
| `testcases.yaml` | Test cases (Input/ExpectedOutput/Judge) | Optional |

#### 5.3 Install Agent to IDEs

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
| `.mcp.json` | 🚫 Ignored | ✅ Yes | Create from `.mcp.json.example` |
| `source/*/.mcp.json` | 🚫 Ignored | ✅ Yes | Create per-agent if needed |
| `**/platform.yaml` | 🚫 Ignored | ✅ Yes | Create for platform agents |
| `**/observable_platform.yaml` | 🚫 Ignored | ✅ Yes | Create for observable platform |
| `venv/` | 🚫 Ignored | ❌ No | Create via `python3 -m venv venv` |
| `.env` | 🚫 Ignored | ✅ Yes | Create if using env vars |

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
    "total": 7,
    "pass": 5,
    "fail": 1,
    "warn": 1,
    "skip": 0,
    "all_pass": false
  }
}
```

**AI Usage**: Call `verify_setup.py --json` and parse the output to determine which steps need attention.

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

---

## Next Steps After Setup

Once setup is complete, the user can:

1. **Create a new Agent**: Say "创建 Agent" or `#create_agent`
2. **Test an existing Agent**: Say "测试 Agent" or `#test_agent <AgentName>`
3. **Iterate on an Agent**: Say "迭代优化" or `#evo_looper <AgentName>`

Refer to `README.md` for detailed usage instructions.

---

## AI Execution Notes

When executing this setup guide:

1. **Execute steps sequentially** - each step depends on the previous
2. **Verify each step** before proceeding to the next
3. **Prompt user for secrets** - never hardcode API keys
4. **Use provided scripts** - `scaffold.py` and `install.py` ensure consistency
5. **Respect `.gitignore`** - generated config files should match ignore patterns
6. **Report progress** - inform user after each major step completion

**Example interaction flow**:
```
AI: 我将帮助你初始化 meta-agent 项目。首先检查 Python 环境...
AI: ✅ Python 3.11 已检测到。正在创建虚拟环境...
AI: ✅ 虚拟环境创建完成。正在安装依赖...
AI: ✅ 依赖安装完成。是否需要配置 MCP 服务？(y/n)
User: y
AI: 请提供 MCP 服务的 API Key 和 Secret...
```
