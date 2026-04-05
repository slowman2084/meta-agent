# Meta-Agent: Agent Evolution Engine for Small Teams

[中文](README.md) | **English**

AI defines the ideal state, generates test cases, creates scoring rubrics, then auto-iterates to optimize prompts — **you set the standard, AI evolves itself.**

> Open the project in an AI IDE (Cursor / CodeBuddy / Claude Code), say `create_agent` and go.

### 🎬 Demo

Watch the full create → test → iterative optimization workflow in action:

https://github.com/slowman2084/meta-agent/raw/main/demo.mp4

> 💡 This video demonstrates the complete Meta-Agent workflow using a lyrics golden-lines Agent. Want hands-on experience? Try the [5-Minute Quick Start Guide](README_FORCLAW_EN.md).

---

## Understand Meta-Agent in 30 Seconds

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   What you give Meta-Agent     What Meta-Agent gives you│
│   ─────────────────────        ─────────────────────    │
│   ● An ideal state description ● Production-grade prompt│
│   ● Or a draft prompt          ● Complete test suite    │
│   ● Or a few test cases        ● Atomic scoring rubrics │
│   ● Or an LLM chat log         ● A qualified Agent      │
│                                                         │
│            You set the standard, AI evolves itself       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Simplest experience**: Open the project in IDE → type `create_agent` → AI guides you through everything.
Up and running in 5 lines:

```bash
git clone <your-repo-url> && cd meta-agent
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./venv/bin/python scripts/install.py          # Distribute rules and built-in Agents
# Open IDE, type in chat: create_agent
```

> Want a hands-on walkthrough? Try the [5-Minute Quick Start Guide](README_FORCLAW_EN.md) — complete create → test → iterate using a lyrics golden-lines demo.

---

## Why Meta-Agent?

### The Ideal State Problem

Building an Agent that "works" is easy. Building one that's "good" is extremely hard. The bottleneck is the **Ideal State** — a precise description of what perfect output looks like:

- **Domain expertise required** — You can't define an ideal ops Agent without ops knowledge, or an ideal translation Agent without translation expertise. Even experts struggle to systematically articulate what they know — like knowing a lot but being unable to teach your own child.
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

## Ideal State: Why It's the Starting Point for Everything

> **The ideal state is a choice, a responsibility, and a core competitive advantage.**

The ideal state describes the expected optimal output from AI. But this isn't about "the best" — it's about "the right fit":

- **Choice** — Should the Agent be interactive or silent? Tables or charts? Strict execution or going the extra mile? No right or wrong, only choices
- **Responsibility** — Making choices for users means taking responsibility for them. Giving users too much freedom creates cognitive burden — this is the value of "product": converging these burdens through the ideal state
- **Core competitiveness** — The ideal state IS product capability in the AI era. With an ideal state, you can define high-quality scoring rubrics and iterate toward high-quality prompts. Without it, everything is hollow

Meta-Agent's entire design revolves around this idea: **Making the cost of defining and implementing the ideal state low enough that even small teams can do it.**

---

## Core Capabilities

| Trigger | Function | Description |
|---------|----------|-------------|
| `create_agent` | Create Agent | Create from prompt draft, ideal state, YAML test cases, or LLM conversation logs |
| `create_testcases` | Generate Test Cases | Auto-generate YAML test cases and scoring rubrics for existing Agents |
| `test_agent` | Test & Evaluate | Run test cases, score outputs (0-100) via eval-judge |
| `evo_looper` | Iterative Optimization | Loop "test → evaluate → optimize prompts" until target score (default 98) |
| `calibrate` | Calibration & Diagnosis | Diagnose consistency issues in the triplet (prompt / ideal state / rubrics) |
| `create_skill` | Create Skill | Create, test, and iterate Skills via Harness Agent pattern (SKILL.md + scripts) |
| `create_platformskill` | Create Platform Skill | Create new Platform Skill execution environment wrappers |

---

## The Eight Meta Agents

Meta-Agent consists of 8 specialized Sub Agents forming a complete pipeline:

| Agent | Purpose | Role in Pipeline |
|-------|---------|-----------------|
| `meta-ideal-state` | Transforms business descriptions into structured ideal state documents | Init: define "what good looks like" |
| `meta-prompt-engineer` | Converts ideal state into executable Agent prompts using CoT, few-shot, etc. | Init + Iteration |
| `meta-testcase-gen` | Infers user personas, generates multi-scenario YAML test cases | Init |
| `meta-rubric-gen` | Generates atomic, decidable scoring rubrics for each test case | Init |
| `meta-eval-judge` | Strictly scores Agent output against rubrics (0-100) | Test + Iteration |
| `meta-reviewer` | Independently reviews prompts for cheating (copying ExpectedOutput) or overfitting | Iteration (separating generation from review) |
| `meta-retrospective` | Analyzes iteration history, identifies degradation patterns, suggests new directions | Iteration review |
| `meta-debug` | Diagnoses triplet consistency issues, outputs calibration_report.json | Calibration & debugging |

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

> Chinese triggers are also supported: `创建 Agent`, `测试 Agent`, `迭代优化`

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
│   ├── platform-skills/          #   Platform Skill source (execution env wrappers)
│   └── [AgentName]/              #   Complete source files per Agent
│       ├── prompt.md             #     Prompt
│       ├── ideal_state.md        #     Ideal state description
│       ├── testcases.yaml        #     Test cases (Input / ExpectedOutput / Judge)
│       ├── agent.json            #     Metadata (description + tool semantics)
│       ├── changelog.md          #     Full lifecycle change log
│       ├── .mcp.json             #     MCP service configuration
│       ├── references/           #     Domain reference resources
│       ├── skills/               #     Agent-specific Skills
│       └── bak/                  #     Historical backups
│
├── scripts/                      # Automation scripts
│   ├── install.py                #   Agent + Rules + Platform Skills installation
│   ├── scaffold.py               #   Create Agent directory scaffold
│   ├── yaml_tool.py              #   YAML test case read/write tool (on-demand, export Inputs)
│   ├── setup_mcp.py              #   MCP quick config
│   ├── verify_setup.py           #   Setup verification
│   ├── batch_evaluate.py         #   Batch evaluation
│   ├── batch_platform_test.py    #   Platform batch testing
│   ├── validate_platform_outputs.py  #  Platform output validation
│   └── check_secrets.sh          #   Secrets leak detection
│
├── tools/                        # Human-assisted tools (browser-based)
│   ├── testcase_viewer.html      #   Test case visual reviewer + annotation export
│   └── calibration_viewer.html   #   Calibration report viewer + decision selection
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

# Install all Platform Skills
./venv/bin/python scripts/install.py --platform-skills

# YAML test case read/write tool
./venv/bin/python scripts/yaml_tool.py count source/[AgentName]/testcases.yaml   # Get total count
./venv/bin/python scripts/yaml_tool.py get source/[AgentName]/testcases.yaml 0   # Read single case
./venv/bin/python scripts/yaml_tool.py get source/[AgentName]/testcases.yaml 0 --fields Input,Judge  # Read specific fields

# Platform batch testing (@ suffix for platform version)
./venv/bin/python scripts/batch_platform_test.py [AgentName]@[platform]

# CLI self-test
./scripts/selftest.sh <agent_name> --cli claude --cases 3

# Setup verification
./venv/bin/python scripts/verify_setup.py

# Secrets leak detection
./scripts/check_secrets.sh
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT License
