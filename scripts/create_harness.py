#!/usr/bin/env python3
"""
Skill Test Harness Agent 自动生成脚本

用途：从 source/skills/[SkillName]/ 自动生成对应的 Harness Agent
     source/skill-harness-[SkillName]/

用法:
    ./venv/bin/python scripts/create_harness.py <SkillName>
    ./venv/bin/python scripts/create_harness.py <SkillName> --force    # 覆盖已有
    ./venv/bin/python scripts/create_harness.py --list                 # 列出所有 Skill
    ./venv/bin/python scripts/create_harness.py --install <SkillName>  # 生成并安装
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime

# 启用实时输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(PROJECT_ROOT, "source")
SKILLS_DIR = os.path.join(SOURCE_DIR, "skills")

# ── Harness prompt.md 模板 ──────────────────────────────────────────

HARNESS_PROMPT_TEMPLATE = """\
# Skill Test Harness: {skill_name}

你是一个 Skill 测试执行器。你的唯一职责是：

1. 加载 Skill `{skill_name}`（通过 `use_skill` 工具）
2. 按照 Skill 的 SKILL.md 指引，处理用户的输入
3. 忠实执行 Skill 的工作流，不要自行发挥

## 约束

- 严格按照 Skill 指引执行，不要跳过步骤
- 如果 Skill 指引要求调用脚本，按指引调用
- 如果 Skill 指引要求生成文件，按指引生成
- 不要添加 Skill 指引之外的额外操作
- 如果执行过程中遇到错误，如实报告，不要掩盖

## 执行流程

1. 调用 `use_skill(command="{skill_name}")` 加载 Skill
2. Skill 的 SKILL.md 内容会注入上下文
3. 按 SKILL.md 的指引处理用户输入
4. 输出执行结果
"""

# ── 理想态模板 ──────────────────────────────────────────────────────

IDEAL_STATE_TEMPLATE = """\
# {skill_name} Skill 理想态

## 概述

{description}

## 理想态维度

### 1. 触发准确性（Trigger Accuracy）
- 当用户输入与 Skill 的触发关键词匹配时，Skill 应被正确加载
- 当用户输入与 Skill 无关时，Skill 不应被误触发

### 2. 工作流效率（Workflow Efficiency）
- Skill 加载后，应按 SKILL.md 的指引高效执行
- 不应有冗余步骤或无效操作

### 3. 执行成功率（Execution Success）
- 在正常条件下，Skill 执行成功率应 ≥ 95%
- 错误处理应清晰、可操作

### 4. 产物质量（Artifact Quality）
- 输出内容应完整、准确
- 若有文件产物，应保存到正确路径

### 5. 跨会话一致性（Cross-session Consistency）
- 相同输入多次执行，结果的结构和风格应保持一致
"""


def read_json(path):
    """读取 JSON 文件"""
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


def write_text(path, content):
    """写入文本文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def list_skills():
    """列出 source/skills/ 下的所有 Skill"""
    if not os.path.isdir(SKILLS_DIR):
        print("⚠️  source/skills/ 目录不存在")
        return []

    skills = []
    for name in sorted(os.listdir(SKILLS_DIR)):
        skill_dir = os.path.join(SKILLS_DIR, name)
        if not os.path.isdir(skill_dir):
            continue
        skill_json_path = os.path.join(skill_dir, "skill.json")
        skill_md_path = os.path.join(skill_dir, "SKILL.md")

        status = "✅" if os.path.exists(skill_json_path) and os.path.exists(skill_md_path) else "⚠️"
        harness_dir = os.path.join(SOURCE_DIR, f"skill-harness-{name}")
        harness_status = " → harness ✅" if os.path.isdir(harness_dir) else ""

        skills.append(name)
        print(f"  {status} {name}{harness_status}")

    return skills


def create_harness(skill_name, force=False):
    """为指定 Skill 创建 Harness Agent"""
    skill_dir = os.path.join(SKILLS_DIR, skill_name)
    harness_name = f"skill-harness-{skill_name}"
    harness_dir = os.path.join(SOURCE_DIR, harness_name)

    print(f"=" * 70, flush=True)
    print(f"🔧 创建 Skill Test Harness Agent: {harness_name}", flush=True)
    print(f"=" * 70, flush=True)
    print(f"  Skill 源: {skill_dir}", flush=True)
    print(f"  Harness 目标: {harness_dir}", flush=True)
    print(f"=" * 70, flush=True)
    print(flush=True)

    # ── 1. 验证 Skill 源目录 ──
    print("1️⃣  验证 Skill 源目录...", flush=True)

    if not os.path.isdir(skill_dir):
        print(f"  ❌ Skill 目录不存在: {skill_dir}", flush=True)
        return False

    skill_json_path = os.path.join(skill_dir, "skill.json")
    skill_md_path = os.path.join(skill_dir, "SKILL.md")

    if not os.path.exists(skill_json_path):
        print(f"  ❌ 缺少 skill.json: {skill_json_path}", flush=True)
        return False

    if not os.path.exists(skill_md_path):
        print(f"  ❌ 缺少 SKILL.md: {skill_md_path}", flush=True)
        return False

    skill_meta = read_json(skill_json_path)
    description = skill_meta.get("description", f"{skill_name} Skill")
    tools = skill_meta.get("tools", ["read"])
    print(f"  ✅ skill.json 已读取（tools: {tools}）", flush=True)
    print(f"  ✅ SKILL.md 存在", flush=True)
    print(flush=True)

    # ── 2. 检查目标目录 ──
    print("2️⃣  检查目标目录...", flush=True)

    if os.path.exists(harness_dir):
        if not force:
            print(f"  ⚠️  Harness 目录已存在: {harness_dir}", flush=True)
            print(f"     使用 --force 覆盖", flush=True)
            return False
        else:
            print(f"  🗑️  删除已有目录（--force）", flush=True)
            shutil.rmtree(harness_dir)

    print(f"  ✅ 目标目录可用", flush=True)
    print(flush=True)

    # ── 3. 创建目录结构 ──
    print("3️⃣  创建目录结构...", flush=True)

    for subdir in ["tmp", "bak", f"skills/{skill_name}", "references"]:
        os.makedirs(os.path.join(harness_dir, subdir), exist_ok=True)
        print(f"  📁 {subdir}/", flush=True)
    print(flush=True)

    # ── 4. 生成 agent.json ──
    print("4️⃣  生成 agent.json...", flush=True)

    agent_json = {
        "description": f"Skill Test Harness: {skill_name} — {description}",
        "tools": tools,
        "harness": {
            "skill_name": skill_name,
            "skill_source": f"source/skills/{skill_name}",
            "optimize_target": "SKILL.md",
            "prompt_is_readonly": True,
        },
    }
    write_json(os.path.join(harness_dir, "agent.json"), agent_json)
    print(f"  ✅ agent.json（含 harness 字段）", flush=True)
    print(flush=True)

    # ── 5. 生成 prompt.md ──
    print("5️⃣  生成 prompt.md...", flush=True)

    prompt_content = HARNESS_PROMPT_TEMPLATE.format(skill_name=skill_name)
    write_text(os.path.join(harness_dir, "prompt.md"), prompt_content)
    print(f"  ✅ prompt.md（Harness 模板）", flush=True)
    print(flush=True)

    # ── 6. 生成 ideal_state.md ──
    print("6️⃣  生成 ideal_state.md...", flush=True)

    # 如果 Skill 源目录已有 ideal_state.md，复制过来
    skill_ideal_state = os.path.join(skill_dir, "ideal_state.md")
    if os.path.exists(skill_ideal_state):
        shutil.copy2(skill_ideal_state, os.path.join(harness_dir, "ideal_state.md"))
        print(f"  ✅ 从 Skill 源复制 ideal_state.md", flush=True)
    else:
        ideal_state = IDEAL_STATE_TEMPLATE.format(
            skill_name=skill_name, description=description
        )
        write_text(os.path.join(harness_dir, "ideal_state.md"), ideal_state)
        print(f"  ✅ 生成默认 ideal_state.md", flush=True)
    print(flush=True)

    # ── 7. 生成 changelog.md ──
    print("7️⃣  生成 changelog.md...", flush=True)

    today = datetime.now().strftime("%Y-%m-%d")
    changelog = (
        f"# {harness_name} Changelog\n\n"
        f"## [创建] 初始版本（Harness Agent）\n\n"
        f"**创建时间：** {today}\n"
        f"**创建方式：** create_harness.py 自动生成\n"
        f"**被测 Skill：** {skill_name}\n"
        f"**Skill 描述：** {description}\n"
        f"**工具列表：** {', '.join(tools)}\n"
    )
    write_text(os.path.join(harness_dir, "changelog.md"), changelog)
    print(f"  ✅ changelog.md", flush=True)
    print(flush=True)

    # ── 8. 生成 .mcp.json ──
    print("8️⃣  生成 .mcp.json...", flush=True)

    # 如果 Skill 源有 .mcp.json，复制；否则空
    skill_mcp = os.path.join(skill_dir, ".mcp.json")
    if os.path.exists(skill_mcp):
        shutil.copy2(skill_mcp, os.path.join(harness_dir, ".mcp.json"))
        print(f"  ✅ 从 Skill 源复制 .mcp.json", flush=True)
    else:
        write_json(os.path.join(harness_dir, ".mcp.json"), {})
        print(f"  ✅ 空 .mcp.json", flush=True)
    print(flush=True)

    # ── 9. 复制 Skill 文件到 skills/ 子目录 ──
    print("9️⃣  复制 Skill 文件到 skills/ 子目录...", flush=True)

    target_skill_dir = os.path.join(harness_dir, "skills", skill_name)
    # 已在步骤 3 创建了目录，现在复制文件
    for item in os.listdir(skill_dir):
        src = os.path.join(skill_dir, item)
        dst = os.path.join(target_skill_dir, item)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        print(f"  → {item}", flush=True)
    print(flush=True)

    # ── 完成 ──
    print(f"=" * 70, flush=True)
    print(f"✅ Harness Agent 创建完成: source/{harness_name}/", flush=True)
    print(f"=" * 70, flush=True)
    print(flush=True)
    print(f"  生成的文件:", flush=True)
    for root_dir, dirs, files in os.walk(harness_dir):
        level = root_dir.replace(harness_dir, "").count(os.sep)
        indent = "  " * (level + 1)
        base = os.path.basename(root_dir)
        if level > 0:
            print(f"{indent}📁 {base}/", flush=True)
        for f in sorted(files):
            print(f"{indent}  📄 {f}", flush=True)

    print(flush=True)
    print(f"  后续步骤:", flush=True)
    print(f"  1. 生成测试用例（create_testcases 或手动编写 testcases.yaml）", flush=True)
    print(f"  2. 安装: ./venv/bin/python scripts/install.py {harness_name}", flush=True)
    print(f"  3. 测试: test_agent {harness_name}", flush=True)
    print(f"  4. 优化: evo_looper {harness_name}", flush=True)

    return True


def main():
    parser = argparse.ArgumentParser(
        description="从 Skill 源文件自动生成 Skill Test Harness Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 列出所有可用 Skill
  ./venv/bin/python scripts/create_harness.py --list

  # 为 pdf-markdown Skill 创建 Harness Agent
  ./venv/bin/python scripts/create_harness.py pdf-markdown

  # 强制覆盖已有的 Harness Agent
  ./venv/bin/python scripts/create_harness.py pdf-markdown --force

  # 创建并安装
  ./venv/bin/python scripts/create_harness.py pdf-markdown --install
        """,
    )
    parser.add_argument("skill_name", nargs="?", help="Skill 名称（对应 source/skills/ 下的目录名）")
    parser.add_argument("--list", action="store_true", help="列出所有可用 Skill")
    parser.add_argument("--force", action="store_true", help="覆盖已有的 Harness Agent 目录")
    parser.add_argument("--install", action="store_true", help="创建后自动运行 install.py 安装")

    args = parser.parse_args()

    if args.list:
        print(f"📦 可用 Skill（source/skills/）:\n", flush=True)
        skills = list_skills()
        if not skills:
            print("  （无）", flush=True)
        return 0

    if not args.skill_name:
        parser.print_help()
        return 1

    success = create_harness(args.skill_name, force=args.force)

    if success and args.install:
        harness_name = f"skill-harness-{args.skill_name}"
        print(f"\n🔌 运行 install.py {harness_name}...\n", flush=True)
        install_script = os.path.join(PROJECT_ROOT, "scripts", "install.py")
        exit_code = os.system(f"{sys.executable} {install_script} {harness_name}")
        return exit_code >> 8  # os.system 返回的是 wait status

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
