# Meta-Agent: Agent Evolution Engine for Small Teams

[中文](README.md) | **English**

AI defines the ideal state, generates test cases, creates scoring rubrics, then auto-iterates to optimize prompts — **you set the standard, AI evolves itself.**

> Open the project in an AI IDE (Cursor / CodeBuddy / Claude Code), say `create_agent` and go.

---

## Why Meta-Agent?

### The Ideal State Problem

Building an Agent that "works" is easy. Building one that's "good" is extremely hard. The bottleneck is the **Ideal State** — a precise description of what perfect output looks like:

- **Domain expertise required** — You can't define an ideal ops Agent without ops knowledge, or an ideal translation Agent without translation expertise. Even experts struggle to systematically articulate what they know.
- **Small teams lack resources** — Google and OpenAI have hundreds of specialists building evaluation systems. Small teams are stretched just getting the engineering to work.
- **Execution is harder than definition** — Even with an ideal state defined, you still need to decompose it into prompts, test cases, and scoring rubrics, then iterate repeatedly. The human cost is enormous.

### Our Core Idea

**Use AI to solve AI's problems.** That's why it's called "Meta-Agent" — an Agent about Agents.

Through self-reference, we built a complete closed loop from **initialization → evaluation → optimization** using a team of Meta Agents:

```
                         Initialization Phase
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  Ideal State / Draft     meta-ideal-state               │
  │        │                      │                         │
  │        ▼                      ▼                         │
  │   meta-prompt-engineer  →  Generate Prompt              │
  │        │                                                │
  │        ▼                                                │
  │   meta-testcase-gen  →  Generate Test Cases             │
  │        │                                                │
  │        ▼                                                │
  │   meta-rubric-gen  →  Generate Scoring Rubrics          │
  │                                                         │
  └───────────────┬─────────────────────────────────────────┘
                  │
                  ▼
  ┌─────────────────────────────────────────────────────────┐
  │          Iterative Optimization (evo_looper)            │
  │                                                         │
  │   Test Agent  →  meta-eval-judge scores  →  Pass?       │
  │       ▲                                    │            │
  │       │              NO                    │ YES        │
  │       │◄───────────────────────────────────┘            │
  │       │                                    │            │
  │  meta-prompt-engineer optimizes            ▼            │
  │  meta-retrospective reviews           Done/Deploy       │
  │                                                         │
  └─────────────────────────────────────────────────────────┘
```

You only need to:
1. **Describe what kind of Agent you want** (ideal state, prompt draft, conversation logs, or just test cases)
2. **AI handles the rest** — generates prompts, test cases, rubrics, then loops testing and optimization until your target score is reached

---

## Core Capabilities

| Trigger | Function | Description |
|---------|----------|-------------|
| `create_agent` | Create Agent | Create from prompt draft, ideal state, YAML test cases, or LLM conversation logs |
| `create_testcases` | Generate Test Cases | Auto-generate YAML test cases and scoring rubrics for existing Agents |
| `test_agent` | Test & Evaluate | Run test cases, score outputs (0-100) via eval-judge |
| `evo_looper` | Iterative Optimization | Loop "test → evaluate → optimize prompts" until target score (default 98) |

---

## The Seven Meta Agents

Meta-Agent consists of 7 specialized Sub Agents forming a complete pipeline:

| Agent | Purpose | Role in Pipeline |
|-------|---------|-----------------|
| `meta-ideal-state` | Transforms business descriptions into structured ideal state documents | Init: define "what good looks like" |
| `meta-prompt-engineer` | Converts ideal state into executable Agent prompts using CoT, few-shot, etc. | Init + Iteration |
| `meta-testcase-gen` | Infers user personas, generates multi-scenario YAML test cases | Init |
| `meta-rubric-gen` | Generates atomic, decidable scoring rubrics for each test case | Init |
| `meta-eval-judge` | Strictly scores Agent output against rubrics (0-100) | Test + Iteration |
| `meta-retrospective` | Analyzes iteration history, identifies degradation patterns, suggests new directions | Iteration review |
| `meta-log-converter` | Converts platform execution logs to unified ShareGPT format | Test support |

---

## Quick Start

### Option A: AI-Assisted Setup (Recommended)

Open the project in a supported IDE and ask AI to initialize:

```
Please read SETUP.md and help me initialize this project
```

AI will automatically handle environment setup, dependency installation, and rule/agent distribution.

### Option B: Manual Setup

```bash
# 1. Clone and install
git clone <your-repo-url>
cd meta-agent
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 2. Distribute rules and built-in Agents to all IDE directories
./venv/bin/python scripts/install.py

# 3. Verify
./venv/bin/python scripts/verify_setup.py
```

### Start Using

Type triggers directly in the IDE chat:

```
create_agent                  # Start creation flow, AI guides you
test_agent my-agent           # Test specified Agent
evo_looper my-agent           # Iterate until target score
```

### Configure MCP Services (Optional)

If your Agent needs external services (e.g., log queries):

```bash
# Quick config with helper script
./venv/bin/python scripts/setup_mcp.py my-agent --template cls \
    --env CLS_SECRET_ID=AKIDxxxxx --env CLS_SECRET_KEY=xxxxx

# Or manual config
cp .mcp.json.example .mcp.json && vim .mcp.json
```

---

## Directory Structure

```
meta-agent/
├── source/                       # 🔑 Source of Truth
│   ├── rules/                    #   Global orchestration rules (.mdc)
│   └── [AgentName]/              #   Complete source files per Agent
│       ├── prompt.md             #     Prompt
│       ├── ideal_state.md        #     Ideal state description
│       ├── testcases.yaml        #     Test cases (Input / ExpectedOutput / Judge)
│       ├── agent.json            #     Metadata (description + tool semantics)
│       ├── changelog.md          #     Full lifecycle change log
│       └── bak/                  #     Historical backups
│
├── scripts/                      # Automation scripts
│   ├── install.py                #   Install Agent (source → 4 IDE directories)
│   ├── scaffold.py               #   Create Agent directory scaffold
│   ├── setup_mcp.py              #   MCP quick config
│   ├── verify_setup.py           #   Setup verification
│   └── platform_test.py          #   Platform batch testing
│
├── tools/                        # Human-assisted tools
│   └── testcase_viewer.html      #   Test case visual reviewer
│
├── .cursor/                      # ┐
├── .codebuddy/                   # ├─ Auto-generated by install.py, do not edit
├── .claude/                      # │  (agents/ + rules/ + skills/)
├── AGENTS.md                     # ┘
│
├── SETUP.md                      # AI-executable initialization guide
├── CLAUDE.md                     # Claude Code global rules
└── CODEBUDDY.md                  # CodeBuddy project memory
```

**Core principle**: `source/` is the single source of truth. All modifications happen there, then `scripts/install.py` syncs to Cursor / CodeBuddy / Claude Code / Codex.

---

## Multi-IDE Compatibility

The same Agent prompt auto-adapts to four IDE header formats:

| IDE | Agent File Location | MCP Declaration |
|-----|-------------------|-----------------|
| Cursor | `.cursor/agents/` | Not supported in header |
| CodeBuddy | `.codebuddy/agents/` | `mcpTools: service-name` |
| Claude Code | `.claude/agents/` | `mcpServers: [service-name]` |
| Codex | `AGENTS.md` sections | N/A |

```bash
# Install/sync specific Agent
./venv/bin/python scripts/install.py [AgentName]

# Install all Agents
./venv/bin/python scripts/install.py
```

---

## Key Design Constraints

| Constraint | Description | Why |
|-----------|-------------|-----|
| **Source First** | All modifications in `source/`, sync via `install.py` | Consistency across 4 IDEs |
| **Must Backup** | Backup to `bak/` before modification | Supports rollback and retrospective |
| **Anti-cheat** | Never embed `ExpectedOutput` into prompts | Prevent overfitting, ensure generalization |
| **Append Changelog** | Create, testcase, optimize, manual changes all appended | Traceable iteration history |
| **Secrets Isolation** | `.mcp.json`, `.env`, `platform.yaml` in `.gitignore` | No API key leakage |

---

## Common Commands

```bash
# Create Agent directory scaffold
./venv/bin/python scripts/scaffold.py [AgentName] -d "description" -t "read,write"

# Install/sync Agent to all IDEs
./venv/bin/python scripts/install.py [AgentName]

# Platform batch testing (@ suffix for platform version)
./venv/bin/python scripts/platform_test.py [AgentName]@[platform]

# CLI self-test
./scripts/selftest.sh <agent_name> --cli claude --cases 3

# Setup verification
./venv/bin/python scripts/verify_setup.py
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT License
