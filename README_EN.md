# Agent Factory — Meta-Agent

[中文](README.md) | **English**

A multi-IDE compatible **Agent Factory** for creating, testing, and iteratively optimizing AI Sub Agents.

With a "write once, sync everywhere" architecture, the same Agent runs seamlessly across **Cursor, CodeBuddy, Claude Code, and Codex**.

---

## ✨ Core Capabilities

| Trigger | Function | Description |
|---------|----------|-------------|
| `#create_agent` | Create Agent | Create from prompt draft, ideal state, CSV test cases, or LLM conversation logs |
| `#create_testcases` | Generate Test Cases | Auto-generate YAML test cases for existing Agents |
| `#test_agent` | Test & Evaluate | Run test cases and score outputs (0-100) via eval-judge |
| `#evo_looper` | Iterative Optimization | Loop "test → evaluate → optimize" until target score is reached |

---

## 🚀 Quick Start

### Option A: AI-Assisted Setup (Recommended)

Open the project in a supported IDE and ask AI to initialize:

```
Please read SETUP.md and help me initialize this project
```

AI will automatically execute environment setup, dependency installation, and MCP configuration.

### Option B: Manual Setup

#### 1. Environment Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd meta-agent

# Create virtual environment
python3 -m venv venv

# Install dependencies
./venv/bin/pip install -r requirements.txt

# Verify installation
./venv/bin/python scripts/verify_setup.py
```

#### 2. Configure MCP Services (Optional)

If you need MCP services (e.g., log queries), configure `.mcp.json`:

```bash
# Copy example config
cp .mcp.json.example .mcp.json

# Edit and fill in your API keys
vim .mcp.json
```

#### 3. Use in IDE

Open the project in a supported IDE (Cursor / CodeBuddy / Claude Code), then type triggers in the chat:

```
#create_agent              # Create new Agent
#test_agent my-agent       # Test specified Agent
#evo_looper my-agent       # Iteratively optimize Agent
```

---

## 📁 Directory Structure

```
meta-agent/
├── README.md                     # Chinese documentation
├── README_EN.md                  # English documentation (this file)
├── SETUP.md                      # AI-executable initialization guide
├── requirements.txt              # Python dependencies
├── .mcp.json.example             # MCP config template (no secrets)
│
├── source/                       # 🔑 Agent source files (core assets)
│   └── [AgentName]/
│       ├── prompt.md             #   Agent prompt
│       ├── ideal_state.md        #   Ideal state description
│       ├── testcases.yaml        #   Test cases
│       ├── changelog.md          #   Change log
│       ├── agent.json            #   Metadata
│       └── bak/                  #   Historical backups
│
├── scripts/                      # Automation scripts
│   ├── install.py                #   Install Agent (source → IDE dirs)
│   ├── scaffold.py               #   Create Agent directory scaffold
│   ├── verify_setup.py           #   Setup verification script
│   └── platform_test.py          #   Platform batch testing
│
├── tools/                        # Human-assisted tools
│   └── testcase_viewer.html      #   Test case visual reviewer
│
├── .cursor/                      # Cursor IDE config
├── .codebuddy/                   # CodeBuddy IDE config
├── .claude/                      # Claude Code config
├── AGENTS.md                     # Codex Agent config
└── CLAUDE.md                     # Claude Code global rules
```

---

## 🤖 Registered Sub Agents

### Core Components (meta-* series)

| Agent | Purpose |
|-------|---------|
| `meta-prompt-engineer` | Prompt engineering expert - writes and optimizes Agent prompts |
| `meta-testcase-gen` | Auto-generates YAML test cases |
| `meta-rubric-gen` | Generates scoring rubrics for test cases |
| `meta-eval-judge` | Evaluates Agent output quality (0-100 score) |
| `meta-retrospective` | Multi-round iteration retrospective analysis |
| `meta-ideal-state` | Generates Agent ideal state documents |
| `meta-log-converter` | Platform log converter |

---

## 🔧 Common Commands

```bash
# Install/sync Agent to all IDEs
./venv/bin/python scripts/install.py [AgentName]

# Create new Agent directory scaffold
./venv/bin/python scripts/scaffold.py [AgentName] -d "Agent description" -t "read,write"

# Platform batch testing
./venv/bin/python scripts/platform_test.py [AgentName]@[platform]
```

---

## 🌐 Multi-IDE Compatibility

The same Agent prompt auto-adapts to different IDE header formats:

| IDE | Model Config | MCP Declaration |
|-----|--------------|-----------------|
| Cursor | `claude-sonnet-4-5` | Not supported in header |
| CodeBuddy | `minimax-m2.5` | `mcpTools: service-name` |
| Claude Code | `sonnet` | `mcpServers: [service-name]` |
| Codex | No header | Section format in AGENTS.md |

---

## ⚠️ Important Constraints

1. **Sync Constraint**: Modify prompts in `source/` first, then sync via `scripts/install.py`
2. **Backup Constraint**: Backup files to `bak/` before modification
3. **Anti-cheat Constraint**: Never embed `ExpectedOutput` into prompts during optimization
4. **Sensitive Info**: `.mcp.json` contains API keys, already in `.gitignore`

---

## 🤝 Contributing

1. Fork this repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m 'Add some feature'`
4. Push branch: `git push origin feature/your-feature`
5. Submit Pull Request

---

## 📄 License

MIT License
