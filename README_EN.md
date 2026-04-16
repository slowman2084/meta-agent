# Meta-Agent: Agent Evolution Engine for Small Teams

[中文](README.md) | **English**

AI defines the ideal state, generates test cases, creates scoring rubrics, then auto-iterates to optimize prompts — **you set the standard, AI evolves itself.**

> Open the project in an AI IDE (Cursor / CodeBuddy / Claude Code), say `create agent` and go.

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

**Simplest experience**: Open the project in IDE → type `create agent` → AI guides you through everything.
Up and running in 5 lines:

```bash
git clone <your-repo-url> && cd meta-agent
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./venv/bin/python scripts/install.py          # Distribute Agents and Skills
# Open IDE, type in chat: create agent
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

Through self-reference, we built a complete closed loop from **initialization → evaluation → optimization** using a team of 11 Core Meta Skills orchestrated by a central router:

```
                    Orchestration Layer (meta-plan router)
                              │
                ┌─────────────┼─────────────┐
                │             │             │
                ▼             ▼             ▼
          Initialization    Testing      Optimization
                │             │             │
                ├─meta-ideal-state         │
                ├─meta-prompt-engineer     ├─meta-eval-judge
                ├─meta-testcase-gen        ├─meta-prompt-engineer
                ├─meta-rubric-gen          ├─meta-iterate
                │                          ├─meta-reviewer
                ├─meta-reviewer            └─meta-retrospective
                └─meta-debug

                    11 Core Meta Skills + 1 Central Orchestrator
```

**Workflow characteristics**:
- **Central Router**: `meta-plan` receives user commands, generates task plans, coordinates downstream components
- **Phased Execution**: Initialization (define ideal state, generate prompts, test cases, rubrics) → Testing → Optimization → Review
- **Automated Tool Integration**: `context_tool.py`, `learnings_tool.py`, `status_tool.py` are built into the orchestration workflow, no manual invocation needed

---

## Core Capabilities

| Trigger | Function | Description |
|---------|----------|-------------|
| `create agent` | Create Agent | Create from prompt draft, ideal state, YAML test cases, or LLM conversation logs |
| `create testcases` | Generate Test Cases | Auto-generate YAML test cases and scoring rubrics for existing Agents |
| `test` | Test & Evaluate | Run test cases, score outputs (0-100) via eval-judge |
| `iterate` | Iterative Optimization | 4-stage hierarchical optimization (warmup → baseline → sampling → verification), iterate until target score (default 98) |
| `calibrate` | Calibration & Diagnosis | Diagnose consistency issues in the triplet (prompt / ideal state / rubrics) |
| `create skill` | Create Skill | Create, test, and iterate Skills via Harness Agent pattern (SKILL.md + scripts) |
| `create platformskill` | Create Platform Skill | Create new Platform Skill execution environment wrappers |

---

## 11 Core Meta Skills

Meta-Agent consists of 11 core Meta Skills working together to form a complete pipeline:

| Skill Name | Purpose | Role in Pipeline |
|-----------|---------|-----------------|
| `meta-plan` | Central router receiving user commands, generating task plans, coordinating downstream components | Core: Entry point for all `test`/`create`/`iterate` commands |
| `meta-ideal-state` | Transforms business descriptions into structured ideal state documents | Initialization: define "what good looks like" |
| `meta-prompt-engineer` | Converts ideal state into executable Agent prompts using CoT, few-shot, etc. | Initialization + Iteration |
| `meta-testcase-gen` | Infers user personas, generates multi-scenario YAML test cases | Initialization |
| `meta-rubric-gen` | Generates atomic, decidable scoring rubrics for each test case | Initialization |
| `meta-eval-judge` | Strictly scores Agent output against rubrics (0-100) | Testing + Iteration |
| `meta-iterate` | Executes 4-stage hierarchical optimization strategy (warmup → baseline → sampling → verification), manages convergence and degradation signals | Iterative optimization core |
| `meta-reviewer` | Independently reviews prompts for cheating (copying ExpectedOutput) or overfitting | Iteration (separating generation from review) |
| `meta-retrospective` | Analyzes iteration history, identifies degradation patterns, suggests new optimization directions | Iteration review |
| `meta-debug` | Diagnoses triplet consistency issues, outputs calibration_report.json | Calibration & debugging |
| `meta-log-converter` | Transforms LLM conversation logs into structured test cases | Initialization support |

**Key characteristics**:
- **meta-plan** is the entry point and orchestrator for all commands
- **meta-iterate** manages the optimization lifecycle and state tracking
- All Skills are located in `source/skills/meta-*/`, not `source/agents/`

---

## Skill Harness Pattern

`meta-skill-harness` is a generic test harness Agent for testing and iteratively optimizing Skills. When you use `test` or `iterate` commands to test a Skill:

1. **Auto-Wrapping**: The system automatically creates a corresponding test harness Agent for the Skill
2. **SKILL.md as Optimization Target**: Iterative optimization targets the Skill's `SKILL.md`, not prompt.md
3. **Unified Workflow**: Skills reuse all Agent workflows (context recovery, testing, iteration, status sync)
4. **No Manual Creation**: You don't need to manually create the harness Agent — the system handles it automatically

For example:
```
test cls-query-skill           # Auto-wrap with meta-skill-harness to test
iterate cls-query-skill        # Auto-optimize SKILL.md, generate optimization history
```

This pattern ensures Skill testing and optimization is completely consistent with Agents, lowering the learning curve.

---

## Tool Scripts Quick Reference

### Core Tools

```bash
# Agent/Skill installation and distribution
./venv/bin/python scripts/install.py                     # Install all
./venv/bin/python scripts/install.py my-agent            # Install specific Agent/Skill
./venv/bin/python scripts/install.py --platform-skills   # Install Platform Skills

# Agent directory scaffolding
./venv/bin/python scripts/scaffold.py my-agent -d "description" -t "read,write"

# YAML test case read/write
./venv/bin/python scripts/yaml_tool.py count source/agents/my-agent/testcases.yaml
./venv/bin/python scripts/yaml_tool.py get source/agents/my-agent/testcases.yaml 0
./venv/bin/python scripts/yaml_tool.py get source/agents/my-agent/testcases.yaml 0-4 --fields Input,Judge
```

### Learnings Management

Inspired by gstack's organizational memory design, each Agent/Skill maintains independent `learnings.jsonl` supporting confidence decay and read-time deduplication.

```bash
# Log an experience
./venv/bin/python scripts/learnings_tool.py log source/agents/cls-log-agent \
    --type pitfall \
    --key "missing-sampling-rate" \
    --insight "Agent forgets to set SamplingRate when timerange > 24h" \
    --confidence 8 \
    --source observed \
    --skill meta-retrospective \
    --iteration 3 \
    --tags "tool-calling,parameter"

# Search experiences (auto-dedup + confidence decay)
./venv/bin/python scripts/learnings_tool.py search source/agents/cls-log-agent
./venv/bin/python scripts/learnings_tool.py search source/agents/cls-log-agent --type pitfall --top 5
./venv/bin/python scripts/learnings_tool.py search source/agents/cls-log-agent --query "sampling" --json

# Statistics
./venv/bin/python scripts/learnings_tool.py count source/agents/cls-log-agent
```

**Learning types**: `pitfall` (pitfall), `pattern` (pattern), `optimization` (optimization direction), `preference` (preference), `rubric-fix` (rubric fix)

**Source and decay**: `observed`/`inferred` confidence decreases by 1 every 30 days, `user-stated` never decays.

### Context Recovery

New sessions automatically scan the Agent directory and restore latest state (plan, baseline, learnings, changelog, test results).

```bash
# Full context summary (human-readable)
./venv/bin/python scripts/context_tool.py recover source/agents/cls-log-agent

# JSON format (for orchestration Skills to programmatically consume)
./venv/bin/python scripts/context_tool.py recover source/agents/cls-log-agent --json

# One-line summary
./venv/bin/python scripts/context_tool.py summary source/agents/cls-log-agent
```

Example output:

```
=== Session Context: cls-log-agent (agent) ===

[Plan] status=running, phase=phase3_sampling, iter=5/10, target=98
[Baseline] avg=69.7, cases=40
[Learnings] 3 relevant:
  1. [pitfall] missing-sampling-rate (conf:8): Agent forgets SamplingRate...
  2. [optimization] cot-format (conf:6): Adding CoT chain improves...
  3. [pattern] cascade-query (conf:5): Cross-topic needs explicit...
[Changelog] last 3:
  - [Optimization] Iteration round 5 (2026-03-21)
  - [Optimization] Iteration round 4 (2026-03-20)
  - [Debug] calibrate fixed rubric (2026-03-19)
[Latest Test] evalooper_iter_5_subagent/ — avg=82.3
```

### Agent/Skill Status Index

Each Agent/Skill maintains `status.json` for quick queries and global overview.

```bash
# View single Agent status
./venv/bin/python scripts/status_tool.py get source/agents/cls-log-agent
./venv/bin/python scripts/status_tool.py get source/agents/cls-log-agent --field phase

# Manual field update
./venv/bin/python scripts/status_tool.py set source/agents/cls-log-agent phase iterate

# Auto-sync status from disk artifacts
./venv/bin/python scripts/status_tool.py sync source/agents/cls-log-agent

# Global overview
./venv/bin/python scripts/status_tool.py summary
```

Global overview output example:

```
=== Agent/Skill Status Summary ===

 Name                     Type    Phase         Score   Base Iters Learn  Last Activity
 ──────────────────────── ─────── ──────────── ────── ────── ───── ─────  ────────────────
 cls-log-agent            agent   iterate       90.7   69.7    11     5  2026-03-21
 cls-query-skill          skill   test          46.8    —       0     0  2026-04-09
 meta-eval-judge          agent   created         —      —      0     0  2026-02-28
```

### Tool Automation Integration

These three scripts are built into the orchestration workflow, running automatically during `meta-plan` and `meta-iterate` lifecycle:

- `meta-plan`
  - Automatically executes `context_tool.py recover` before `test` / `calibrate`
  - Automatically executes `status_tool.py sync` after `evaluation_report.md` is generated
- `meta-iterate`
  - Automatically restores latest context on startup
  - Automatically executes `context_tool.py summary` after each round/stage
  - Writes key convergence conclusions and degradation signals to `learnings.jsonl`
  - Automatically executes `status_tool.py sync` after warmup / baseline / sampling / verify
- `meta-retrospective`
  - Distills high-value anti-patterns / optimization directions to `learnings.jsonl` after review
  - Then automatically syncs `status.json`

**This means**:
- New session: directly `test xxx` / `iterate xxx`, automatically brings latest state
- Experiences generated during iteration no longer stay just in reports
- `status.json` continuously refreshes as the workflow progresses, not dependent on manual maintenance
- **In most cases, you don't need to manually call these tools** (except for debugging or supplementing special experiences)

---

## Usage Scenarios

### Scenario 1: Create an Agent from Zero

```
# In IDE chat
create agent

# AI will ask you to choose a creation method:
# a. From prompt draft
# b. From ideal state description
# c. From YAML test cases
# d. From LLM chat log
```

### Scenario 2: Test an Existing Agent

```
# Test all cases
test cls-log-agent

# Test only first 3
test cls-log-agent top 3

# Test on CodeBuddy CLI platform
test cls-log-agent on codebuddycli
```

This workflow now automatically does two things:
1. Executes `context_tool.py recover` before starting, prioritizing incomplete plans and bringing latest baseline / test / changelog / learnings
2. After `evaluation_report.md` is generated, executes `status_tool.py sync`, writing latest scores and plan status to `status.json`

### Scenario 3: Auto-iterate Until Target Score

```
# Auto 4-stage optimization (warmup → baseline → sampling → verification)
iterate cls-log-agent

# Default target score 98
iterate cls-log-agent

# Resume from last interruption (auto-finds latest plan file)
iterate cls-log-agent
```

The iterate main workflow now has this built-in loop:
1. Startup: `recover`
2. After each test / compare: run `summary`
3. Write valid directions, degradation signals, anti-patterns to `learnings.jsonl`
4. After each stage: `status_tool.py sync`

So one `iterate xxx` is no longer just "scoring", but a complete workflow: "restore context → execute → distill experience → refresh status".

### Scenario 4: Accumulate and Use Experiences During Iteration

```bash
# Manually supplement an experience (optional, usually not needed)
./venv/bin/python scripts/learnings_tool.py log source/agents/cls-log-agent \
    --type pitfall --key "n-plus-one-api-calls" \
    --insight "Agent makes separate API calls for each topic instead of batching" \
    --confidence 9 --source observed --iteration 5

# See what context will be restored on next startup
./venv/bin/python scripts/context_tool.py recover source/agents/cls-log-agent --json
```

In the default workflow, many experiences are already auto-distilled:
- `meta-iterate` writes each round's key convergence conclusions / degradation signals to learnings
- `meta-retrospective` writes high-value anti-patterns and next-round suggestions to learnings
- Next `test` / `iterate` startup, `context_tool` automatically brings these experiences back

Manual `log` is better for supplementing explicit user preferences or out-of-workflow observations.

### Scenario 5: Calibrate Evaluation System

```
# After first test, run calibrate to diagnose evaluation system
calibrate cls-log-agent

# Diagnose four types of issues:
# - Rubric design problems
# - Rubric ↔ Ideal state contradiction
# - Ideal state ↔ Prompt contradiction
# - User value perspective insight
```

### Scenario 6: View Overall Status of All Agents

```bash
# See everything at a glance
./venv/bin/python scripts/status_tool.py summary

# Batch sync status (infer from disk artifacts)
for dir in source/agents/*/; do
    ./venv/bin/python scripts/status_tool.py sync "$dir"
done
```

### Scenario 7: Test a Skill

```
# Skill auto-wraps with meta-skill-harness, no manual harness creation needed
test cls-query-skill

# Iterative optimize Skill (optimization target is SKILL.md not prompt.md)
iterate cls-query-skill
```

Applies equally to Skills:
- Before `test cls-query-skill`, context is automatically restored
- During `iterate cls-query-skill`, stage status and learnings automatically written back to `source/skills/cls-query-skill/`
- Optimization target is still `SKILL.md`, but recovery / experience / status workflow now unified with Agents

---

## Directory Structure

```
meta-agent/
├── source/                       # Single source of truth
│   ├── agents/                   #   Business Agent source directory
│   │   └── [AgentName]/          #     Complete source files per Agent
│   │       ├── prompt.md         #       Prompt
│   │       ├── ideal_state.md    #       Ideal state description
│   │       ├── testcases.yaml    #       Test cases (Input / ExpectedOutput / Judge)
│   │       ├── agent.json        #       Metadata (description + tool semantics + benefits_from)
│   │       ├── changelog.md      #       Full lifecycle changelog
│   │       ├── learnings.jsonl   #       Structured experience record (append-only)
│   │       ├── status.json       #       Current state index
│   │       ├── .mcp.json         #       MCP service configuration
│   │       ├── references/       #       Domain reference resources
│   │       ├── skills/           #       Agent-specific Skill
│   │       ├── bak/              #       Historical backups
│   │       └── tmp/              #       Runtime artifacts (plan / test results / baseline)
│   │
│   ├── skills/                   #   Skills source directory (includes all meta-* Skills)
│   │   ├── meta-plan/            #     Central orchestrator Skill
│   │   │   ├── SKILL.md          #       Skill instruction document
│   │   │   ├── skill.json        #       Metadata
│   │   │   └── ...
│   │   ├── meta-iterate/         #     4-stage iterative optimization Skill
│   │   ├── meta-prompt-engineer/ #     Prompt generation and optimization Skill
│   │   ├── meta-eval-judge/      #     Scoring and judgment Skill
│   │   ├── [SkillName]/          #     Business Skill source files
│   │   │   ├── SKILL.md          #       Skill instruction document (iterative optimization target)
│   │   │   ├── skill.json        #       Metadata (trigger_keywords + tools)
│   │   │   ├── scripts/          #       Implementation scripts
│   │   │   └── ...               #       (rest of structure same as Agent)
│   │   └── ...
│   │
│   └── platform-skills/          #   Platform Skill source directory (execution environment wrappers)
│
├── scripts/                      # Automation scripts
│   ├── install.py                #   Agent + Skill + Platform Skills installation
│   ├── scaffold.py               #   Create Agent directory scaffolding
│   ├── yaml_tool.py              #   YAML test case read/write tool (on-demand)
│   ├── learnings_tool.py         #   Experience management (log / search / count)
│   ├── context_tool.py           #   Context recovery (recover / summary)
│   ├── status_tool.py            #   Status index (get / set / sync / summary)
│   ├── setup_mcp.py              #   MCP quick config
│   └── verify_setup.py           #   Setup verification
│
├── tools/                        # Human-assisted tools (browser-based)
│   ├── testcase_viewer.html      #   Test case visual reviewer + annotation export
│   └── calibration_viewer.html   #   Calibration report viewer + decision selection
│
├── .cursor/                      # ┐
├── .codebuddy/                   # ├─ Auto-generated by install.py, do not edit
├── .claude/                      # │  (agents/ + skills/)
├── AGENTS.md                     # ┘
│
├── SETUP.md                      # AI-executable initialization guide
├── CLAUDE.md                     # Claude Code global configuration
└── CODEBUDDY.md                  # CodeBuddy project configuration
```

**Core principles**:
- `source/` is the single source of truth, all modifications happen here
- **All meta-* components are located in `source/skills/meta-*/`**, not `source/agents/`
- `source/agents/` is for business/target Agents only
- `source/skills/` contains all Skills, including meta-skills and business Skills
- Sync to Cursor / CodeBuddy / Claude Code / Codex via `scripts/install.py`

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
| **Must Backup** | Backup to `bak/` before modification | Supports rollback and review |
| **Anti-cheat** | Never embed `ExpectedOutput` into prompts | Prevent overfitting, ensure generalization |
| **Append Changelog** | Create, testcase, optimize, manual changes all appended | Traceable iteration history |
| **Append Learnings** | Experiences append-only, deduplicated at read-time with decay | Audit-friendly, outdated experiences naturally fade |
| **Secrets Isolation** | `.mcp.json`, `.env`, `platform.yaml` in `.gitignore` | No API key leakage |

---

## Quick Start

### Option A: AI-Assisted Setup (Recommended)

Open the project in a supported IDE and ask AI to initialize:

```
Please read SETUP.md and help me initialize this project
```

AI will automatically handle environment setup, dependency installation, and Agent/Skill distribution.

### Option B: Manual Setup

```bash
# 1. Clone and install
git clone <your-repo-url>
cd meta-agent
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# 2. Distribute Agents and Skills to all IDE directories
./venv/bin/python scripts/install.py

# 3. Verify
./venv/bin/python scripts/verify_setup.py
```

### Start Using

Type triggers directly in the IDE chat:

```
create agent                     # Start creation flow, AI guides you
test my-agent                    # Test specified Agent
iterate my-agent                 # Iteratively optimize until target score
calibrate my-agent               # Calibrate evaluation system
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT License
