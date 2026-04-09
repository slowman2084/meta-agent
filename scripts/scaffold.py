#!/usr/bin/env python3
"""
Agent 脚手架脚本 — 创建 source/[AgentName]/ 完整目录结构

用法:
    ./venv/bin/python scripts/scaffold.py <AgentName>
    ./venv/bin/python scripts/scaffold.py <AgentName> -d "描述" -t "read,write"
"""

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(PROJECT_ROOT, "source")
AGENTS_DIR = os.path.join(PROJECT_ROOT, "source/agents")


def scaffold(agent_name, description="", tools=None):
    agent_dir = os.path.join(AGENTS_DIR, agent_name)

    if os.path.exists(agent_dir):
        print(f"⚠️  目录已存在：source/agents/{agent_name}/")
        print(f"   仅创建缺失项\n")

    subdirs = ["tmp", "bak", "skills", "references"]
    for subdir in subdirs:
        os.makedirs(os.path.join(agent_dir, subdir), exist_ok=True)

    created = []

    changelog = os.path.join(agent_dir, "changelog.md")
    if not os.path.exists(changelog):
        with open(changelog, "w", encoding="utf-8") as f:
            f.write(f"# {agent_name} Changelog\n")
        created.append("changelog.md")

    if not os.path.exists(mcp):
        with open(mcp, "w", encoding="utf-8") as f:
            json.dump({}, f)
            f.write("\n")
        created.append(".mcp.json")

    agent_json = os.path.join(agent_dir, "agent.json")
    if not os.path.exists(agent_json):
        meta = {
            "description": description or f"{agent_name} 的简要描述（请修改）",
            "tools": tools or ["read"],
        }
        with open(agent_json, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
            f.write("\n")
        created.append("agent.json")

    for name in created:
        print(f"  ✅ {name}")

    if not created:
        print("  （所有文件已存在，无需创建）")

    print(f"\n📂 source/agents/{agent_name}/ 脚手架完成")
    print(f"   待手动创建：prompt.md, ideal_state.md, testcases.csv")


PLATFORM_YAML_TEMPLATE = """\
# 平台测试配置
# 占位符 {{PROMPT}} 由 platform_test.py 自动替换为 prompt.md 内容

llm:
  model: "your-model-name"
  api_key: "your-api-key"
  base_url: "http://your-platform-url/v1"
  temperature: 0.7

prompts:
  custom_system_prompt: |
    {{PROMPT}}

mcp_servers: []

graph:
  name: "platform_test_agent"
  max_threshold_tokens: 70000
  max_summary_tokens: 20000
  recursion_limit: 256
  enable_condense: true
  enable_todolist: false
  debug: false
"""


def main():
    parser = argparse.ArgumentParser(description="创建 Agent 目录脚手架")
    parser.add_argument("agent_name", help="Agent 名称")
    parser.add_argument("--description", "-d", default="", help="Agent 简要描述")
    parser.add_argument(
        "--tools", "-t", default="read",
        help="工具语义值，逗号分隔 (read/write/edit/search/bash)",
    )
    args = parser.parse_args()

    tools = [t.strip() for t in args.tools.split(",")]

    print(f"🔧 创建 Agent 脚手架：{args.agent_name}\n")
    scaffold(args.agent_name, args.description, tools)


if __name__ == "__main__":
    main()
