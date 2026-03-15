#!/usr/bin/env python3
"""
MCP 配置辅助脚本 — 帮助快速配置 Agent 的 MCP 服务

用法:
    # 为 Agent 配置 MCP 服务（交互式）
    ./venv/bin/python scripts/setup_mcp.py my-agent

    # 直接指定参数配置
    ./venv/bin/python scripts/setup_mcp.py my-agent --server cls-mcp-server --command npx --args "@anthropic/mcp-cls" --env CLS_SECRET_ID=xxx --env CLS_SECRET_KEY=yyy

    # 使用模板快速配置已知 MCP 服务
    ./venv/bin/python scripts/setup_mcp.py my-agent --template cls --env CLS_SECRET_ID=xxx --env CLS_SECRET_KEY=yyy

    # 查看已有配置
    ./venv/bin/python scripts/setup_mcp.py my-agent --show

    # 初始化根目录 .mcp.json（如果不存在）
    ./venv/bin/python scripts/setup_mcp.py --init-root

场景:
    当你创建一个需要 MCP 服务的 Agent，或者拿到别人的 Agent 需要配置密钥时：
    1. 使用此脚本配置 MCP（会自动处理 source/[AgentName]/.mcp.json）
    2. 然后运行 install.py 进行安装
"""

import argparse
import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(PROJECT_ROOT, "source")

# 启用实时输出
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

# ── 预定义 MCP 模板 ──────────────────────────────────────────────────
MCP_TEMPLATES = {
    "cls": {
        "description": "腾讯云 CLS 日志服务",
        "config": {
            "command": "npx",
            "args": ["-y", "@anthropic/mcp-cls"],
            "env": {
                "CLS_SECRET_ID": "",
                "CLS_SECRET_KEY": "",
                "CLS_REGION": "ap-guangzhou"
            }
        },
        "required_env": ["CLS_SECRET_ID", "CLS_SECRET_KEY"],
        "optional_env": {"CLS_REGION": "ap-guangzhou"},
        "default_server_name": "cls-mcp-server"
    },
    "github": {
        "description": "GitHub API 集成",
        "config": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-github"],
            "env": {
                "GITHUB_PERSONAL_ACCESS_TOKEN": ""
            }
        },
        "required_env": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
        "optional_env": {},
        "default_server_name": "github-mcp-server"
    },
    "sqlite": {
        "description": "SQLite 数据库",
        "config": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-sqlite"],
            "env": {}
        },
        "required_env": [],
        "optional_env": {},
        "default_server_name": "sqlite-mcp-server"
    },
    "filesystem": {
        "description": "文件系统访问",
        "config": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem"],
            "env": {}
        },
        "required_env": [],
        "optional_env": {},
        "default_server_name": "filesystem-mcp-server"
    }
}


def read_json(path):
    """读取 JSON 文件，不存在则返回 None"""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, data):
    """写入 JSON 文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def init_root_mcp():
    """初始化根目录的 .mcp.json"""
    root_mcp = os.path.join(PROJECT_ROOT, ".mcp.json")
    if os.path.exists(root_mcp):
        print(f"ℹ️  根目录 .mcp.json 已存在", flush=True)
        data = read_json(root_mcp)
        servers = data.get("mcpServers", {}) if data else {}
        if servers:
            print(f"   已配置的 MCP 服务: {', '.join(servers.keys())}", flush=True)
        return True
    
    print(f"✅ 创建根目录 .mcp.json", flush=True)
    write_json(root_mcp, {"mcpServers": {}})
    return True


def show_config(agent_name):
    """显示 Agent 的 MCP 配置"""
    agent_mcp = os.path.join(SOURCE_DIR, agent_name, ".mcp.json")
    
    if not os.path.exists(agent_mcp):
        print(f"ℹ️  source/{agent_name}/.mcp.json 不存在", flush=True)
        return
    
    data = read_json(agent_mcp)
    if not data or not data.get("mcpServers"):
        print(f"ℹ️  source/{agent_name}/.mcp.json 为空", flush=True)
        return
    
    print(f"📋 source/{agent_name}/.mcp.json 配置:\n", flush=True)
    print(json.dumps(data, ensure_ascii=False, indent=2), flush=True)


def list_templates():
    """列出可用的 MCP 模板"""
    print("📋 可用的 MCP 模板:\n", flush=True)
    for name, tmpl in MCP_TEMPLATES.items():
        print(f"  {name}: {tmpl['description']}", flush=True)
        if tmpl['required_env']:
            print(f"    必填环境变量: {', '.join(tmpl['required_env'])}", flush=True)
        if tmpl['optional_env']:
            print(f"    可选环境变量: {', '.join(tmpl['optional_env'].keys())}", flush=True)
        print(flush=True)


def setup_from_template(agent_name, template_name, env_vars, server_name=None):
    """使用模板配置 MCP"""
    if template_name not in MCP_TEMPLATES:
        print(f"❌ 未知模板: {template_name}", flush=True)
        print(f"   可用模板: {', '.join(MCP_TEMPLATES.keys())}", flush=True)
        return False
    
    tmpl = MCP_TEMPLATES[template_name]
    config = json.loads(json.dumps(tmpl["config"]))  # 深拷贝
    
    # 检查必填环境变量
    missing = []
    for key in tmpl["required_env"]:
        if key not in env_vars:
            missing.append(key)
    
    if missing:
        print(f"❌ 缺少必填环境变量: {', '.join(missing)}", flush=True)
        print(f"   使用 --env {missing[0]}=<value> 提供", flush=True)
        return False
    
    # 合并环境变量
    for key, value in env_vars.items():
        config["env"][key] = value
    
    # 填充默认可选值
    for key, default in tmpl["optional_env"].items():
        if key not in config["env"] or not config["env"][key]:
            config["env"][key] = default
    
    # 确定 server name
    final_server_name = server_name or tmpl["default_server_name"]
    
    return setup_mcp_config(agent_name, final_server_name, config)


def setup_mcp_config(agent_name, server_name, config):
    """写入 MCP 配置到 Agent 的 .mcp.json"""
    agent_dir = os.path.join(SOURCE_DIR, agent_name)
    agent_mcp = os.path.join(agent_dir, ".mcp.json")
    
    # 检查 Agent 目录是否存在
    if not os.path.isdir(agent_dir):
        print(f"❌ Agent 目录不存在: source/{agent_name}/", flush=True)
        print(f"   请先运行: ./venv/bin/python scripts/scaffold.py {agent_name}", flush=True)
        return False
    
    # 读取现有配置
    existing = read_json(agent_mcp) or {}
    if "mcpServers" not in existing:
        existing["mcpServers"] = {}
    
    # 检查是否已存在同名配置
    if server_name in existing["mcpServers"]:
        print(f"⚠️  MCP 服务 '{server_name}' 已存在，将覆盖", flush=True)
    
    # 写入配置
    existing["mcpServers"][server_name] = config
    write_json(agent_mcp, existing)
    
    print(f"✅ 已配置 MCP 服务: {server_name}", flush=True)
    print(f"   写入: source/{agent_name}/.mcp.json", flush=True)
    
    # 检查是否有敏感信息提示
    env = config.get("env", {})
    secret_keys = [k for k in env.keys() if any(s in k.upper() for s in ["SECRET", "KEY", "TOKEN", "PASSWORD"])]
    if secret_keys:
        print(f"\n⚠️  注意：配置中包含敏感信息（{', '.join(secret_keys)}）", flush=True)
        print(f"   .mcp.json 已在 .gitignore 中，不会被提交到 Git", flush=True)
    
    print(f"\n📝 下一步：运行 install.py 将配置合并到根 .mcp.json 并安装 Agent", flush=True)
    print(f"   ./venv/bin/python scripts/install.py {agent_name}", flush=True)
    
    return True


def setup_custom(agent_name, server_name, command, args, env_vars):
    """自定义 MCP 配置"""
    config = {
        "command": command,
        "args": args,
        "env": env_vars
    }
    return setup_mcp_config(agent_name, server_name, config)


def main():
    parser = argparse.ArgumentParser(
        description="MCP 配置辅助脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 使用模板配置 CLS MCP
  ./venv/bin/python scripts/setup_mcp.py my-agent --template cls \\
      --env CLS_SECRET_ID=AKIDxxxxx --env CLS_SECRET_KEY=xxxxx

  # 查看 Agent 已有配置
  ./venv/bin/python scripts/setup_mcp.py my-agent --show

  # 列出可用模板
  ./venv/bin/python scripts/setup_mcp.py --list-templates

  # 自定义 MCP 配置
  ./venv/bin/python scripts/setup_mcp.py my-agent --server my-mcp \\
      --command npx --args "my-mcp-server" --env API_KEY=xxx
        """
    )
    
    parser.add_argument("agent_name", nargs="?", help="Agent 名称")
    parser.add_argument("--show", action="store_true", help="显示当前 MCP 配置")
    parser.add_argument("--init-root", action="store_true", help="初始化根目录 .mcp.json")
    parser.add_argument("--list-templates", action="store_true", help="列出可用的 MCP 模板")
    
    # 模板配置
    parser.add_argument("--template", "-t", help="使用预定义模板 (cls, github, sqlite, filesystem)")
    
    # 自定义配置
    parser.add_argument("--server", "-s", help="MCP 服务名称")
    parser.add_argument("--command", "-c", help="MCP 命令 (如 npx)")
    parser.add_argument("--args", "-a", nargs="*", default=[], help="MCP 命令参数")
    parser.add_argument("--env", "-e", action="append", default=[], 
                        help="环境变量，格式: KEY=VALUE（可多次指定）")
    
    args = parser.parse_args()
    
    print("=" * 60, flush=True)
    print("MCP 配置辅助脚本", flush=True)
    print("=" * 60, flush=True)
    print(flush=True)
    
    # 处理特殊命令
    if args.list_templates:
        list_templates()
        return 0
    
    if args.init_root:
        init_root_mcp()
        return 0
    
    # 检查 agent_name
    if not args.agent_name:
        parser.print_help()
        return 1
    
    # 显示配置
    if args.show:
        show_config(args.agent_name)
        return 0
    
    # 解析环境变量
    env_vars = {}
    for env_str in args.env:
        if "=" not in env_str:
            print(f"❌ 环境变量格式错误: {env_str}（应为 KEY=VALUE）", flush=True)
            return 1
        key, value = env_str.split("=", 1)
        env_vars[key] = value
    
    # 使用模板配置
    if args.template:
        success = setup_from_template(args.agent_name, args.template, env_vars, args.server)
        return 0 if success else 1
    
    # 自定义配置
    if args.server and args.command:
        success = setup_custom(args.agent_name, args.server, args.command, args.args, env_vars)
        return 0 if success else 1
    
    # 没有提供足够参数
    print("❌ 请指定 --template 或同时指定 --server 和 --command", flush=True)
    print(flush=True)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
