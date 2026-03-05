#!/usr/bin/env python3
"""
平台配置准备脚本 — 将 prompt.md 内容填入 YAML 配置占位符

用法:
    ./venv/bin/python scripts/prepare_config.py <AgentName> <output_dir>

脚本执行:
1. 读取 source/[AgentName]/prompt.md
2. 在 skills 目录中查找包含 {{AgentName}} 的 YAML 文件
3. 替换占位符为提示词内容
4. 写入 output_dir/config_snapshot.yaml
5. 验证无残留占位符
"""

import glob as glob_module
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(PROJECT_ROOT, "source")


def find_yaml_with_placeholder(agent_name):
    placeholder = "{{" + agent_name + "}}"

    search_dirs = [
        os.path.join(SOURCE_DIR, agent_name, "skills"),
        os.path.join(PROJECT_ROOT, ".cursor", "skills"),
        os.path.join(PROJECT_ROOT, ".codebuddy", "skills"),
        os.path.join(PROJECT_ROOT, ".claude", "skills"),
    ]

    for search_dir in search_dirs:
        if not os.path.isdir(search_dir):
            continue
        for pattern in ("**/*.yaml", "**/*.yml"):
            for path in glob_module.glob(
                os.path.join(search_dir, pattern), recursive=True
            ):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                if placeholder in content:
                    return path, content

    return None, None


def main():
    if len(sys.argv) != 3:
        print("用法: ./venv/bin/python scripts/prepare_config.py <AgentName> <output_dir>")
        sys.exit(1)

    agent_name = sys.argv[1]
    output_dir = sys.argv[2]

    prompt_path = os.path.join(SOURCE_DIR, agent_name, "prompt.md")
    if not os.path.exists(prompt_path):
        print(f"❌ 找不到提示词：{prompt_path}")
        sys.exit(1)

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_content = f.read()

    placeholder = "{{" + agent_name + "}}"
    yaml_path, yaml_content = find_yaml_with_placeholder(agent_name)

    if yaml_path is None:
        print(f"❌ 未找到包含 {placeholder} 的 YAML 配置文件")
        sys.exit(1)

    print(f"📄 模板：{yaml_path}")

    # 找到占位符所在行及其缩进级别
    lines = yaml_content.split('\n')
    result_lines = []
    placeholder_found = False
    
    for line in lines:
        if placeholder in line:
            # 找到占位符行的缩进
            indent = line[:len(line) - len(line.lstrip())]
            # 对提示词内容的每一行添加相同的缩进
            prompt_lines = prompt_content.split('\n')
            indented_lines = [
                (indent + pl) if pl.strip() else indent
                for pl in prompt_lines
            ]
            # 用缩进后的提示词行替换占位符行
            result_lines.extend(indented_lines)
            placeholder_found = True
        else:
            result_lines.append(line)
    
    if not placeholder_found:
        print(f"⚠️  未找到占位符 {placeholder}")
        sys.exit(1)
    
    result = '\n'.join(result_lines)

    if placeholder in result:
        print(f"⚠️  替换后仍有残留占位符 {placeholder}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "config_snapshot.yaml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"✅ 已写入：{output_path}")


if __name__ == "__main__":
    main()
