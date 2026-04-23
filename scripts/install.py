#!/usr/bin/env python3
"""
Agent & Platform Skills 安装脚本 — 将 source/ 中的资源同步到所有 IDE 目录

用法:
    ./venv/bin/python scripts/install.py                              # 安装所有（Agent + Skill + Platform Skills）
    ./venv/bin/python scripts/install.py my-agent                     # 安装指定 Agent
    ./venv/bin/python scripts/install.py my-agent --model gpt-4       # 指定模型（使用 prompt_gpt-4.md）
    ./venv/bin/python scripts/install.py my-skill --model robust      # 安装 Skill 的鲁棒版本（SKILL_robust.md）
    ./venv/bin/python scripts/install.py meta-skill-harness --model GLM-5.1 --alias meta-skill-harness-GLM-5.1  # 安装多模型 harness 变体
    ./venv/bin/python scripts/install.py my-agent --scope user        # 安装到用户级 IDE 目录（~/.cursor/ 等）
    ./venv/bin/python scripts/install.py --platform-skills            # 安装所有 Platform Skills
    ./venv/bin/python scripts/install.py --platform-skill codebuddycli  # 安装指定 Platform Skill
"""

import json
import os
import re
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(PROJECT_ROOT, "source")
AGENTS_DIR = os.path.join(PROJECT_ROOT, "source/agents")
SKILLS_DIR = os.path.join(PROJECT_ROOT, "source/skills")
PLATFORM_SKILLS_DIR = os.path.join(SOURCE_DIR, "platform-skills")
PLATFORMSKILL_CREATOR_DIR = os.path.join(SOURCE_DIR, "platformskill-creator")

# source/ 下不作为 Agent 安装的目录名（旧模式回退用）
NON_AGENT_DIRS = {"platform-skills", "platformskill-creator", "hooks", "skills", "agents"}

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


def safe_write_text(path, new_content, agent_name=None, context_info=""):
    """
    安全写入文件。如果文件存在且内容不同，并且有被 IDE 侧修改的可能，则备份原文件。
    返回是否进行了写入。
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    if os.path.exists(path):
        existing_content = read_text(path)
        if existing_content == new_content:
            # 内容一致，无需写入
            return False
            
        # 内容不同，判断目标文件是否在最近被修改过 (防止静默抹除用户的修改)
        # 简单粗暴且安全的策略：只要内容不同，就将现有文件备份
        import time
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak_path = f"{path}.{ts}.bak"
        
        # 为了防止生成太多备份，如果文件存在且不是由系统生成的默认初始内容，再提示
        print(f"  ⚠️  检测到 {context_info} 内容有冲突！已将原文件备份至: {os.path.basename(bak_path)}")
        shutil.copy2(path, bak_path)

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True

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
        f"> 请参见 `source/agents/{agent_name}/prompt.md`\n"
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

def merge_mcp(mcp_full_config, agent_name=None):
    """
    将 Agent 的 MCP 配置合并到根 .mcp.json
    
    返回: (success, message)
    """
    root_mcp = os.path.join(PROJECT_ROOT, ".mcp.json")
    
    # 检查根 .mcp.json 是否存在，不存在则自动创建
    if not os.path.exists(root_mcp):
        print(f"    → 根目录 .mcp.json 不存在，自动创建...")
        write_json(root_mcp, {"mcpServers": {}})
    
    root = read_json(root_mcp)
    if root is None:
        print(f"    ⚠️  无法读取根 .mcp.json，尝试重新创建...")
        root = {"mcpServers": {}}
        write_json(root_mcp, root)
    
    if "mcpServers" not in root:
        root["mcpServers"] = {}

    # 检查 Agent MCP 配置是否有效（是否包含实际内容而非占位符）
    warnings = []
    for name, cfg in mcp_full_config.items():
        env = cfg.get("env", {})
        empty_secrets = []
        for key, value in env.items():
            # 检查敏感字段是否为空或占位符
            is_secret = any(s in key.upper() for s in ["SECRET", "KEY", "TOKEN", "PASSWORD"])
            is_empty = not value or value in ["", "your-api-key", "xxx", "YOUR_KEY_HERE"]
            if is_secret and is_empty:
                empty_secrets.append(key)
        
        if empty_secrets:
            warnings.append((name, empty_secrets))

    # 如果有未填写的敏感配置，提示用户
    if warnings:
        print(f"    ⚠️  MCP 配置中发现未填写的敏感信息：")
        for server_name, keys in warnings:
            print(f"       - {server_name}: {', '.join(keys)}")
        if agent_name:
            print(f"\n    💡 建议使用 setup_mcp.py 配置密钥：")
            print(f"       ./venv/bin/python scripts/setup_mcp.py {agent_name} --show")
            print(f"       ./venv/bin/python scripts/setup_mcp.py {agent_name} --template <模板> --env KEY=VALUE")
        print()

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


# ── Platform Skills install ──────────────────────────────────────────

IDE_SKILLS_TARGETS = [".cursor/skills", ".codebuddy/skills", ".claude/skills"]


def install_one_platform_skill(skill_name):
    """安装单个 Platform Skill 到所有 IDE skills 目录。
    
    源目录: source/platform-skills/<skill_name>/
    目标目录: .<ide>/skills/platform-<skill_name>/
    
    返回: True=成功, False=失败
    """
    src_dir = os.path.join(PLATFORM_SKILLS_DIR, skill_name)
    if not os.path.isdir(src_dir):
        print(f"  ❌ Platform Skill 目录不存在: {src_dir}")
        return False

    # 验证必要文件
    skill_json = os.path.join(src_dir, "skill.json")
    skill_md = os.path.join(src_dir, "SKILL.md")
    if not os.path.exists(skill_json):
        print(f"  ⚠️  跳过 {skill_name}：缺少 skill.json")
        return False

    for ide_skills in IDE_SKILLS_TARGETS:
        target_dir = os.path.join(PROJECT_ROOT, ide_skills, f"platform-{skill_name}")
        # 清除旧版本
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        # 复制整个 skill 目录
        shutil.copytree(src_dir, target_dir)
        print(f"  ✅ {ide_skills}/platform-{skill_name}/")

    return True


def install_platformskill_creator():
    """安装 platformskill-creator Skill 本身到所有 IDE skills 目录。
    
    源目录: source/platformskill-creator/
    目标目录: .<ide>/skills/platformskill-creator/
    
    返回: True=成功, False=失败
    """
    if not os.path.isdir(PLATFORMSKILL_CREATOR_DIR):
        print(f"  ⚠️  platformskill-creator 目录不存在，跳过")
        return False

    skill_md = os.path.join(PLATFORMSKILL_CREATOR_DIR, "SKILL.md")
    if not os.path.exists(skill_md):
        print(f"  ⚠️  platformskill-creator 缺少 SKILL.md，跳过")
        return False

    for ide_skills in IDE_SKILLS_TARGETS:
        target_dir = os.path.join(PROJECT_ROOT, ide_skills, "platformskill-creator")
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        shutil.copytree(PLATFORMSKILL_CREATOR_DIR, target_dir)
        print(f"  ✅ {ide_skills}/platformskill-creator/")

    return True


def install_platform_skills(specific_skill=None):
    """安装 Platform Skills。
    
    Args:
        specific_skill: 指定安装某个 Platform Skill，None 则安装全部。
    
    返回: (成功数, 失败数)
    """
    print(f"🔌 安装 Platform Skills\n")

    ok, fail = 0, 0

    if specific_skill:
        # 安装指定的单个 Platform Skill
        print(f"📦 platform-skills/{specific_skill}")
        if install_one_platform_skill(specific_skill):
            ok += 1
        else:
            fail += 1
        print()
    else:
        # 安装全部 Platform Skills
        if not os.path.isdir(PLATFORM_SKILLS_DIR):
            print(f"  ⚠️  source/platform-skills/ 不存在，跳过")
            return 0, 0

        # 读取 registry.json 获取已注册的 Skills 列表
        registry_path = os.path.join(PLATFORM_SKILLS_DIR, "registry.json")
        if os.path.exists(registry_path):
            registry = read_json(registry_path)
            skill_names = list(registry.get("platforms", {}).keys())
        else:
            # 如果没有 registry，扫描目录
            skill_names = sorted(
                d for d in os.listdir(PLATFORM_SKILLS_DIR)
                if os.path.isdir(os.path.join(PLATFORM_SKILLS_DIR, d))
            )

        if not skill_names:
            print(f"  ⚠️  无 Platform Skills 可安装")
            return 0, 0

        print(f"  发现 {len(skill_names)} 个 Platform Skills: {', '.join(skill_names)}\n")

        for name in skill_names:
            # subagent 是内置模式，只有 SKILL.md 没有 scripts，也安装用于文档参考
            src = os.path.join(PLATFORM_SKILLS_DIR, name)
            if not os.path.isdir(src):
                print(f"  ⚠️  跳过 {name}：目录不存在（仅在注册表中）")
                fail += 1
                continue

            print(f"📦 platform-skills/{name}")
            if install_one_platform_skill(name):
                ok += 1
            else:
                fail += 1
            print()

        # 安装 platformskill-creator Skill
        print(f"📦 platformskill-creator (Skill 创建工具)")
        if install_platformskill_creator():
            ok += 1
        else:
            fail += 1
        print()

        # 复制 registry.json 到各 IDE skills 根目录（供编排器查询）
        if os.path.exists(registry_path):
            for ide_skills in IDE_SKILLS_TARGETS:
                target = os.path.join(PROJECT_ROOT, ide_skills, "platform-skills-registry.json")
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(registry_path, target)
            print(f"  ✅ registry.json → 各 IDE skills 目录\n")

    print(f"  Platform Skills 安装完成：{ok} 成功, {fail} 失败\n")
    return ok, fail



# ── CLAUDE.md ↔ CODEBUDDY.md sync ────────────────────────────────────

def sync_project_memory():
    """同步 CLAUDE.md 和 CODEBUDDY.md（两者功能相同，分别供 Claude Code 和 CodeBuddy CLI 读取）。

    策略：以较新者为准同步到另一方。若两者都存在且内容不同，以修改时间较新的为源。
    """
    claude_md = os.path.join(PROJECT_ROOT, "CLAUDE.md")
    codebuddy_md = os.path.join(PROJECT_ROOT, "CODEBUDDY.md")

    claude_exists = os.path.exists(claude_md)
    codebuddy_exists = os.path.exists(codebuddy_md)

    if not claude_exists and not codebuddy_exists:
        print("  ⚠️  CLAUDE.md 和 CODEBUDDY.md 均不存在，跳过同步")
        return

    # 只有一方存在：复制到另一方
    if claude_exists and not codebuddy_exists:
        shutil.copy2(claude_md, codebuddy_md)
        print("  ✅ CLAUDE.md → CODEBUDDY.md（新建）")
        return
    if codebuddy_exists and not claude_exists:
        shutil.copy2(codebuddy_md, claude_md)
        print("  ✅ CODEBUDDY.md → CLAUDE.md（新建）")
        return

    # 两者都存在：比较内容
    claude_content = read_text(claude_md)
    codebuddy_content = read_text(codebuddy_md)

    if claude_content == codebuddy_content:
        print("  → CLAUDE.md ↔ CODEBUDDY.md 已同步，跳过")
        return

    # 内容不同：以修改时间较新的为准
    claude_mtime = os.path.getmtime(claude_md)
    codebuddy_mtime = os.path.getmtime(codebuddy_md)

    if claude_mtime >= codebuddy_mtime:
        shutil.copy2(claude_md, codebuddy_md)
        print("  ✅ CLAUDE.md → CODEBUDDY.md（同步较新内容）")
    else:
        shutil.copy2(codebuddy_md, claude_md)
        print("  ✅ CODEBUDDY.md → CLAUDE.md（同步较新内容）")


# ── Install one agent ────────────────────────────────────────────────

def resolve_prompt(agent_dir, model=None):
    """Determine which prompt file to use for an Agent.
    
    Priority:
    1. --model <name> → prompt_<name>.md (copy from prompt.md if missing)
    2. --model robust or no --model, prompt_robust.md exists → prompt_robust.md
    3. fallback → prompt.md
    """
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
        # robust 优先：无 --model 时，若 prompt_robust.md 存在则使用
        robust = os.path.join(agent_dir, "prompt_robust.md")
        if os.path.exists(robust):
            print(f"  🛡️  检测到 prompt_robust.md，使用鲁棒版本")
            return robust, read_text(robust)
        path = os.path.join(agent_dir, "prompt.md")
        return path, read_text(path)


def resolve_skill_md(skill_dir, model=None):
    """Determine which SKILL.md file to use for a Skill.
    
    Priority:
    1. --model <name> → SKILL_<name>.md (copy from SKILL.md if missing)
    2. --model robust or no --model, SKILL_robust.md exists → SKILL_robust.md
    3. fallback → SKILL.md
    
    Returns: (source_path, model_label) where model_label is used for logging.
    """
    if model:
        variant = os.path.join(skill_dir, f"SKILL_{model}.md")
        base = os.path.join(skill_dir, "SKILL.md")
        if not os.path.exists(variant):
            if not os.path.exists(base):
                return None, None
            shutil.copy2(base, variant)
            print(f"  📋 已从 SKILL.md 复制 → SKILL_{model}.md")
        return variant, model
    else:
        # robust 优先
        robust = os.path.join(skill_dir, "SKILL_robust.md")
        if os.path.exists(robust):
            print(f"  🛡️  检测到 SKILL_robust.md，使用鲁棒版本")
            return robust, "robust"
        path = os.path.join(skill_dir, "SKILL.md")
        return path, None


def _resolve_agent_dir(agent_name):
    """优先从 source/agents/ 查找，回退到 source/（向后兼容）。"""
    new_path = os.path.join(AGENTS_DIR, agent_name)
    if os.path.isdir(new_path):
        return new_path
    old_path = os.path.join(SOURCE_DIR, agent_name)
    if os.path.isdir(old_path):
        return old_path
    return None


def install_agent(agent_name, model=None, alias=None):
    agent_dir = _resolve_agent_dir(agent_name)
    if agent_dir is None:
        print(f"  ⚠️  跳过：找不到 {agent_name}（source/agents/ 或 source/ 下均不存在）")
        return False

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

    # alias: 安装时使用不同的名称（如 meta-skill-harness-GLM-5.1）
    install_name = alias if alias else agent_name
    if alias:
        print(f"  🏷️  别名：{alias}")
        # 替换 prompt 中的 {{MODEL}} 占位符
        if model:
            prompt = prompt.replace("{{MODEL}}", model)

    desc = meta["description"]
    if alias and model:
        desc = f"{desc}（模型：{model}）"
    tools = meta.get("tools", ["read"])

    mcp_data = read_json(os.path.join(agent_dir, ".mcp.json")) or {}
    mcp_servers_cfg = mcp_data.get("mcpServers", {})
    mcp_names = list(mcp_servers_cfg.keys())

    for ide_dir, platform in IDE_TARGETS:
        header = HEADER_GENERATORS[platform](install_name, desc, tools, mcp_names, model=model)
        target = os.path.join(PROJECT_ROOT, ide_dir, f"{install_name}.md")
        os.makedirs(os.path.join(PROJECT_ROOT, ide_dir), exist_ok=True)
        
        expected_content = header + "\n" + prompt
        existing_content = read_text(target)
        
        if existing_content != expected_content:
            if existing_content is not None:
                # 避免大量无用日志，只提示内容真正发生改变的
                bak_path = f"{target}.bak"
                shutil.copy2(target, bak_path)
                write_text(target, expected_content)
                print(f"  ⚠️  检测到修改: 已更新 {ide_dir}/{install_name}.md (旧版已备份至 .bak)")
            else:
                write_text(target, expected_content)
                print(f"  ✅ {ide_dir}/{install_name}.md (新建)")
        else:
            print(f"  → {ide_dir}/{agent_name}.md (无变更)")

    update_agents_md(install_name, desc)
    print(f"  ✅ AGENTS.md（{agent_name} 章节）")

    if mcp_servers_cfg:
        merge_mcp(mcp_servers_cfg, agent_name)
        print(f"  ✅ .mcp.json（MCP 合并）")

    skills_dir = os.path.join(agent_dir, "skills")
    if os.path.isdir(skills_dir) and os.listdir(skills_dir):
        copy_skills(skills_dir)
        print(f"  ✅ skills 已同步")

    return True


# ── Install one Skill ─────────────────────────────────────────────────

# 安装 Skill 时排除的文件/目录（测试产物和临时文件）
_SKIP_INSTALL = {"bak", "tmp", "testcases.yaml", "ideal_state.md", "changelog.md", "learnings.jsonl", "status.json", ".DS_Store"}


def install_skill(skill_name, model=None, scope="project"):
    """将 source/skills/[name]/ 分发到 IDE 的 skills/ 目录。
    
    若 skill.json 中 install_to_ide 为 false，则跳过安装到 IDE 目录。
    这些 Skill 仅作为内部专用（由其他 Skill spawn subagent 时读取）。
    
    Args:
        model: 指定模型版本（使用 SKILL_<model>.md 替换 SKILL.md 安装）
        scope: "project"（项目级，默认）或 "user"（用户级 ~/.xxx/skills/）
    """
    skill_dir = os.path.join(SKILLS_DIR, skill_name)
    if not os.path.isdir(skill_dir):
        print(f"  ❌ {skill_name}：source/skills/ 下不存在")
        return False

    # 检查 install_to_ide 标志
    skill_json = read_json(os.path.join(skill_dir, "skill.json"))
    if skill_json and skill_json.get("install_to_ide") is False:
        print(f"  ⏭️  {skill_name}：install_to_ide=false，跳过 IDE 安装（内部专用）")
        return True  # 不算失败，只是跳过

    # 解析模型版本
    skill_md_path, model_label = resolve_skill_md(skill_dir, model)
    use_variant = model_label is not None  # 需要用变体替换 SKILL.md

    if model_label:
        print(f"  🎯 模型版本：{model_label} → 使用 {os.path.basename(skill_md_path)}")

    # 确定目标路径列表
    if scope == "user":
        ide_skills_list = _get_user_ide_skills_paths()
        if not ide_skills_list:
            print(f"  ⚠️  未检测到任何已安装的 IDE，跳过用户级安装")
            return False
    else:
        ide_skills_list = [
            os.path.join(PROJECT_ROOT, p) for p in
            [".cursor/skills", ".codebuddy/skills", ".claude/skills"]
        ]

    for target_root in ide_skills_list:
        target = os.path.join(target_root, skill_name)
        if os.path.exists(target):
            shutil.rmtree(target)

        rel_path = target.replace(os.path.expanduser("~"), "~") if scope == "user" else os.path.relpath(target, PROJECT_ROOT)
        print(f"  → 安装 {rel_path}/")
        
        # 复制时跳过测试产物和模型变体文件
        skip = set(_SKIP_INSTALL)
        # 跳过所有 SKILL_*.md 变体（只安装选中的版本）
        for f in os.listdir(skill_dir):
            if f.startswith("SKILL_") and f.endswith(".md"):
                skip.add(f)
        shutil.copytree(skill_dir, target, ignore=shutil.ignore_patterns(*skip))

        # 如果使用了模型变体，将其内容覆盖到目标的 SKILL.md
        if use_variant and skill_md_path:
            target_skill_md = os.path.join(target, "SKILL.md")
            shutil.copy2(skill_md_path, target_skill_md)

        print(f"  ✅ {rel_path}/ (已更新)")

    return True


# ── User-level install helpers ───────────────────────────────────────

USER_IDE_PATHS = {
    "Cursor":    {"skills": "~/.cursor/skills",    "agents": "~/.cursor/agents"},
    "CodeBuddy": {"skills": "~/.codebuddy/skills", "agents": "~/.codebuddy/agents"},
    "Claude":    {"skills": "~/.claude/skills",     "agents": "~/.claude/agents"},
}


def _get_user_ide_skills_paths():
    """探测用户主目录下已安装的 IDE，返回 skills 目录列表。"""
    paths = []
    for ide_name, dirs in USER_IDE_PATHS.items():
        expanded = os.path.expanduser(dirs["skills"])
        parent = os.path.dirname(expanded)  # e.g. ~/.cursor/
        if os.path.isdir(parent):
            os.makedirs(expanded, exist_ok=True)
            paths.append(expanded)
            print(f"  ✅ {ide_name}: {dirs['skills']}")
        else:
            print(f"  ⏭️  {ide_name}: {parent} 不存在，跳过")
    return paths


def _get_user_ide_agents_paths():
    """探测用户主目录下已安装的 IDE，返回 agents 目录列表。"""
    paths = []
    for ide_name, dirs in USER_IDE_PATHS.items():
        expanded = os.path.expanduser(dirs["agents"])
        parent = os.path.dirname(expanded)
        if os.path.isdir(parent):
            os.makedirs(expanded, exist_ok=True)
            paths.append((expanded, ide_name))
        # 不重复打印，skills 探测时已打印
    return paths


def install_agent_user(agent_name, model=None):
    """将 Agent 安装到用户级 IDE 目录。"""
    agent_dir = _resolve_agent_dir(agent_name)
    if agent_dir is None:
        print(f"  ⚠️  跳过：找不到 {agent_name}")
        return False

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
    mcp_names = list(mcp_data.get("mcpServers", {}).keys())

    ide_agent_paths = _get_user_ide_agents_paths()
    if not ide_agent_paths:
        print(f"  ⚠️  未检测到任何已安装的 IDE，跳过用户级安装")
        return False

    # 映射 IDE name → platform key
    ide_to_platform = {"Cursor": "cursor", "CodeBuddy": "codebuddy", "Claude": "claude"}

    for agents_dir_path, ide_name in ide_agent_paths:
        platform = ide_to_platform.get(ide_name)
        if not platform:
            continue
        header = HEADER_GENERATORS[platform](agent_name, desc, tools, mcp_names, model=model)
        target = os.path.join(agents_dir_path, f"{agent_name}.md")
        content = header + "\n" + prompt
        write_text(target, content)
        rel = target.replace(os.path.expanduser("~"), "~")
        print(f"  ✅ {rel} (已安装)")

    return True


# ── Main ─────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent & Platform Skills 安装脚本")
    parser.add_argument("agents", nargs="*", help="Agent/Skill 名称（不指定则安装全部）")
    parser.add_argument("--model", "-m", default=None,
                        help="指定模型版本（Agent: prompt_[model].md, Skill: SKILL_[model].md）")
    parser.add_argument("--alias", "-a", default=None,
                        help="安装时使用的别名（如 meta-skill-harness-GLM-5.1），{{MODEL}} 占位符会被替换为 --model 值")
    parser.add_argument("--scope", "-s", choices=["project", "user"], default="project",
                        help="安装范围：project（项目级，默认）或 user（用户级 ~/.xxx/）")
    parser.add_argument("--platform-skills", action="store_true",
                        help="安装所有 Platform Skills 到各 IDE skills 目录")
    parser.add_argument("--platform-skill", default=None, metavar="NAME",
                        help="安装指定的 Platform Skill（如 codebuddycli）")
    args = parser.parse_args()

    # ── 仅安装 Platform Skills ──
    if args.platform_skills or args.platform_skill:
        install_platform_skills(specific_skill=args.platform_skill)
        return 0

    # ── CLAUDE.md ↔ CODEBUDDY.md 同步（仅项目级全量安装时）──
    if not args.agents and args.scope == "project":
        print("📄 同步项目全局配置\n")
        sync_project_memory()
        print()

    # ── Agent / Skill 安装 ──
    if args.agents:
        # 指定了名称：按名称查找，先查 agents，再查 skills
        input_names = args.agents
        agent_names, skill_names = [], []
        for name in input_names:
            if os.path.isdir(os.path.join(SKILLS_DIR, name)):
                skill_names.append(name)
            elif _resolve_agent_dir(name):
                agent_names.append(name)
            else:
                print(f"❌ {name}：source/agents/ 和 source/skills/ 下均不存在")
    else:
        # 全量安装：分别扫描 source/agents/ 和 source/skills/
        agent_names = []
        if os.path.isdir(AGENTS_DIR):
            agent_names = sorted(
                d for d in os.listdir(AGENTS_DIR)
                if os.path.isdir(os.path.join(AGENTS_DIR, d))
                and not d.startswith(".")
            )

        skill_names = []
        if os.path.isdir(SKILLS_DIR):
            skill_names = sorted(
                d for d in os.listdir(SKILLS_DIR)
                if os.path.isdir(os.path.join(SKILLS_DIR, d))
                and not d.startswith(".")
            )

    scope = args.scope
    scope_label = "用户级 IDE 目录" if scope == "user" else "项目 IDE 目录"
    model_info = f"（model: {args.model}）" if args.model else ""

    # ── 用户级安装时先探测 IDE ──
    if scope == "user" and (agent_names or skill_names):
        print(f"🔍 探测已安装的 IDE...\n")

    # ── Agent 安装 ──
    ok, fail = 0, 0
    if agent_names:
        print(f"🔧 安装 Agent → {scope_label}{model_info}\n")
        for name in agent_names:
            agent_dir = _resolve_agent_dir(name)
            if agent_dir is None:
                print(f"❌ {name}：source/agents/ 或 source/ 下均不存在")
                fail += 1
                continue

            print(f"📦 {name}")
            if scope == "user":
                success = install_agent_user(name, model=args.model)
            else:
                success = install_agent(name, model=args.model, alias=args.alias)
            if success:
                ok += 1
            else:
                fail += 1
            print()

        print(f"{'='*40}")
        print(f"✅ Agent 安装完成：{ok} 成功, {fail} 失败")

    # ── Skill 安装 ──
    sok, sfail = 0, 0
    if skill_names:
        print(f"\n🔧 安装 Skill → {scope_label}{model_info}\n")
        for name in skill_names:
            print(f"📦 {name}")
            if install_skill(name, model=args.model, scope=scope):
                sok += 1
            else:
                sfail += 1
            print()
        print(f"{'='*40}")
        print(f"✅ Skill 安装完成：{sok} 成功, {sfail} 失败")

    # ── 全量安装时同时安装 Platform Skills（仅项目级）──
    if not args.agents and scope == "project":
        print()
        install_platform_skills()

    return 0 if (fail == 0 and sfail == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
