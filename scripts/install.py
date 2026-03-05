#!/usr/bin/env python3
"""
Agent 安装脚本 — 将 source/[AgentName]/ 同步到所有 IDE 目录

用法:
    ./venv/bin/python scripts/install.py                              # 安装所有 Agent（model 留空）
    ./venv/bin/python scripts/install.py my-agent                     # 安装指定 Agent
    ./venv/bin/python scripts/install.py my-agent --model gpt-4       # 指定模型（使用 prompt_gpt-4.md）
"""

import json
import os
import re
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(PROJECT_ROOT, "source")

TOOL_MAP = {
    "cursor": {
        "read": "Read",
        "write": "Write",
        "edit": "Edit",
        "search": "Glob, Grep",
        "bash": "Bash",
    },
    "codebuddy": {
        "read": "read_file",
        "write": "write_to_file",
        "edit": "replace_in_file",
        "search": "search_file, search_content",
        "bash": "execute_command, list_dir",
    },
    "claude": {
        "read": "Read",
        "write": "Write",
        "edit": "Edit",
        "search": "Glob, Grep",
        "bash": "Bash",
    },
}

IDE_TARGETS = [
    (".cursor/agents", "cursor"),
    (".codebuddy/agents", "codebuddy"),
    (".claude/agents", "claude"),
]


def expand_tools(semantic_tools, platform):
    mapping = TOOL_MAP[platform]
    parts = []
    for t in semantic_tools:
        if t in mapping:
            parts.append(mapping[t])
    return ", ".join(parts)


def read_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_text(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ── Header generators ────────────────────────────────────────────────

def gen_cursor_header(name, desc, tools, mcp_servers, model=None):
    tool_str = expand_tools(tools, "cursor")
    if not tool_str and mcp_servers:
        tool_str = "Read"
    lines = [
        "---",
        f"name: {name}",
        f"description: {desc}",
        f"model: {model or ''}",
        f"tools: {tool_str}",
        "---",
    ]
    return "\n".join(lines)


def gen_codebuddy_header(name, desc, tools, mcp_servers, model=None):
    tool_str = expand_tools(tools, "codebuddy")
    lines = [
        "---",
        f"name: {name}",
        f"description: {desc}",
        f"model: {model or ''}",
        f"tools: {tool_str}",
        "agentMode: agentic",
        "enabled: true",
        "enabledAutoRun: true",
    ]
    if mcp_servers:
        lines.append(f"mcpTools: {', '.join(mcp_servers)}")
    lines.append("---")
    return "\n".join(lines)


def gen_claude_header(name, desc, tools, mcp_servers, model=None):
    lines = [
        "---",
        f"name: {name}",
        f"description: {desc}",
        f"model: {model or ''}",
    ]
    if mcp_servers:
        lines.append("mcpServers:")
        for s in mcp_servers:
            lines.append(f"  - {s}")
    else:
        tool_str = expand_tools(tools, "claude")
        lines.append(f"tools: {tool_str}")
    lines.append("---")
    return "\n".join(lines)


HEADER_GENERATORS = {
    "cursor": gen_cursor_header,
    "codebuddy": gen_codebuddy_header,
    "claude": gen_claude_header,
}


# ── AGENTS.md section management ─────────────────────────────────────

def update_agents_md(agent_name, description):
    agents_md = os.path.join(PROJECT_ROOT, "AGENTS.md")
    content = read_text(agents_md) or ""

    new_section = (
        f"## Agent: {agent_name}\n"
        f"\n"
        f"**描述**：{description}\n"
        f"\n"
        f"**提示词**：\n"
        f"\n"
        f"> 请参见 `source/{agent_name}/prompt.md`\n"
        f"\n"
        f"---"
    )

    pattern = re.compile(
        rf"^## Agent: {re.escape(agent_name)}\s*\n.*?^---",
        re.MULTILINE | re.DOTALL,
    )

    if pattern.search(content):
        content = pattern.sub(new_section, content)
    else:
        content = content.rstrip("\n") + "\n\n" + new_section + "\n"

    write_text(agents_md, content)


# ── MCP merge ────────────────────────────────────────────────────────

def merge_mcp(mcp_full_config):
    root_mcp = os.path.join(PROJECT_ROOT, ".mcp.json")
    root = read_json(root_mcp) or {}
    if "mcpServers" not in root:
        root["mcpServers"] = {}

    changed = False
    for name, cfg in mcp_full_config.items():
        if name not in root["mcpServers"]:
            root["mcpServers"][name] = cfg
            print(f"    → 新增 MCP: {name}")
            changed = True
        else:
            print(f"    → 跳过已有 MCP: {name}")

    if changed:
        write_json(root_mcp, root)


# ── Skills copy ──────────────────────────────────────────────────────

def copy_skills(skills_src):
    for ide_skills in [".cursor/skills", ".codebuddy/skills", ".claude/skills"]:
        target_root = os.path.join(PROJECT_ROOT, ide_skills)
        for skill_name in os.listdir(skills_src):
            src = os.path.join(skills_src, skill_name)
            if not os.path.isdir(src):
                continue
            dst = os.path.join(target_root, skill_name)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"    → {ide_skills}/{skill_name}/")


# ── Install one agent ────────────────────────────────────────────────

def resolve_prompt(agent_dir, model=None):
    """Determine which prompt file to use. Copy from prompt.md if model variant doesn't exist."""
    if model:
        variant = os.path.join(agent_dir, f"prompt_{model}.md")
        base = os.path.join(agent_dir, "prompt.md")
        if not os.path.exists(variant):
            if not os.path.exists(base):
                return None, None
            shutil.copy2(base, variant)
            print(f"  📋 已从 prompt.md 复制 → prompt_{model}.md")
        return variant, read_text(variant)
    else:
        path = os.path.join(agent_dir, "prompt.md")
        return path, read_text(path)


def install_agent(agent_name, model=None):
    agent_dir = os.path.join(SOURCE_DIR, agent_name)

    meta = read_json(os.path.join(agent_dir, "agent.json"))
    if meta is None:
        print(f"  ⚠️  跳过：缺少 agent.json")
        return False

    prompt_path, prompt = resolve_prompt(agent_dir, model)
    if prompt is None:
        print(f"  ⚠️  跳过：缺少 prompt.md")
        return False

    if model:
        print(f"  🎯 模型：{model} → 使用 {os.path.basename(prompt_path)}")

    desc = meta["description"]
    tools = meta.get("tools", ["read"])

    mcp_data = read_json(os.path.join(agent_dir, ".mcp.json")) or {}
    mcp_servers_cfg = mcp_data.get("mcpServers", {})
    mcp_names = list(mcp_servers_cfg.keys())

    for ide_dir, platform in IDE_TARGETS:
        header = HEADER_GENERATORS[platform](agent_name, desc, tools, mcp_names, model=model)
        target = os.path.join(PROJECT_ROOT, ide_dir, f"{agent_name}.md")
        os.makedirs(os.path.join(PROJECT_ROOT, ide_dir), exist_ok=True)
        write_text(target, header + "\n" + prompt)
        print(f"  ✅ {ide_dir}/{agent_name}.md")

    update_agents_md(agent_name, desc)
    print(f"  ✅ AGENTS.md（{agent_name} 章节）")

    if mcp_servers_cfg:
        merge_mcp(mcp_servers_cfg)
        print(f"  ✅ .mcp.json（MCP 合并）")

    skills_dir = os.path.join(agent_dir, "skills")
    if os.path.isdir(skills_dir) and os.listdir(skills_dir):
        copy_skills(skills_dir)
        print(f"  ✅ skills 已同步")

    return True


# ── Main ─────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent 安装脚本")
    parser.add_argument("agents", nargs="*", help="Agent 名称（不指定则安装全部）")
    parser.add_argument("--model", "-m", default=None,
                        help="指定模型（使用 prompt_[model].md，不存在时自动从 prompt.md 复制）")
    args = parser.parse_args()

    if args.agents:
        agents = args.agents
    else:
        agents = sorted(
            d for d in os.listdir(SOURCE_DIR)
            if os.path.isdir(os.path.join(SOURCE_DIR, d))
            and not d.startswith(".")
        )

    model_info = f"（model: {args.model}）" if args.model else ""
    print(f"🔧 安装 Agent → 所有 IDE 目录{model_info}\n")

    ok, fail = 0, 0
    for name in agents:
        if not os.path.isdir(os.path.join(SOURCE_DIR, name)):
            print(f"❌ {name}：source 目录不存在")
            fail += 1
            continue

        print(f"📦 {name}")
        if install_agent(name, model=args.model):
            ok += 1
        else:
            fail += 1
        print()

    print(f"{'='*40}")
    print(f"✅ 完成：{ok} 成功, {fail} 失败")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
