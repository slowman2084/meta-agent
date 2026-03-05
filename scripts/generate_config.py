#!/usr/bin/env python3
"""生成平台测试配置文件，正确处理 YAML 多行字符串"""

import yaml
import sys

def generate_config(agent_name: str, prompt_path: str, template_path: str, output_path: str):
    """读取模板和提示词，生成完整的配置文件"""

    # 读取 Agent 提示词
    with open(prompt_path, 'r', encoding='utf-8') as f:
        agent_prompt = f.read()

    # 读取模板配置
    with open(template_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 替换 custom_system_prompt 中的占位符
    placeholder = f"{{{{{agent_name}}}}}"
    if 'prompts' in config and 'custom_system_prompt' in config['prompts']:
        if placeholder in config['prompts']['custom_system_prompt']:
            config['prompts']['custom_system_prompt'] = agent_prompt
        else:
            print(f"Warning: Placeholder {placeholder} not found in template")

    # 写入输出文件
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False, width=float('inf'))

    print(f"Config generated: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python generate_config.py <agent_name> <prompt_path> <template_path> <output_path>")
        sys.exit(1)

    agent_name = sys.argv[1]
    prompt_path = sys.argv[2]
    template_path = sys.argv[3]
    output_path = sys.argv[4]

    generate_config(agent_name, prompt_path, template_path, output_path)
