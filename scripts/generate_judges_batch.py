#!/usr/bin/env python3
"""
批量生成 Judge 评分标准

功能：
1. 读取 testcases.yaml 中的所有 Input
2. 批量调用 meta-rubric-gen Sub Agent（并发 5 条）
3. 将每条用例的 Judge 结果保存到 tmp/judge_case_N.yaml
4. 支持失败重试（最多 3 次）

用法：
    ./venv/bin/python scripts/generate_judges_batch.py --agent cls-log-agent
    ./venv/bin/python scripts/generate_judges_batch.py --agent cls-log-agent --start 10 --end 20
"""

import sys
import os
import json
import yaml
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 启用行缓冲（实时输出）
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)


def load_testcases(agent_name: str) -> Dict[str, Any]:
    """加载测试用例文件"""
    yaml_path = project_root / "source" / agent_name / "testcases.yaml"
    
    if not yaml_path.exists():
        raise FileNotFoundError(f"测试用例文件不存在: {yaml_path}")
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return data


def load_ideal_state(agent_name: str) -> str:
    """加载理想态文件"""
    ideal_path = project_root / "source" / agent_name / "ideal_state.md"
    
    if not ideal_path.exists():
        print(f"⚠️  理想态文件不存在: {ideal_path}")
        return ""
    
    with open(ideal_path, 'r', encoding='utf-8') as f:
        return f.read()


def call_meta_rubric_gen_subagent(
    case_idx: int,
    input_text: str,
    agent_name: str,
    ideal_state: str
) -> List[Dict[str, Any]]:
    """
    调用 meta-rubric-gen Sub Agent（通过 Task 工具）
    
    注意：此函数需要在主进程中执行，因为 Task 工具只能通过 AI Agent 调用
    这里返回 None，实际调用由外部 AI Agent 完成
    """
    # 此函数仅用于生成调用提示词，实际调用由 AI Agent 执行
    prompt = f"""请为 cls-log-agent 的测试用例 **case {case_idx}** 生成 Judge 评分标准。

**Agent 名称**: {agent_name}

**理想态要求**:
{ideal_state[:500]}...

**Input**:
```
{input_text}
```

**任务要求**:
1. 基于理想态描述的要求，为这条 Input 生成符合 MECE 原则的 Judge 评分标准
2. 覆盖关键维度：真实性、便捷性、可信度、生动性、运行效率、实际价值
3. 结合 {agent_name} 的 MCP 工具能力设计评分标准
4. 输出格式为 YAML 列表，每条 rubric 包含 criterion/points/tags 三字段

**输出格式示例**:
```yaml
- criterion: "正确识别 Topic 名称并调用 GetTopicInfoByName 工具"
  points: 10
  tags:
    - axis:accuracy
    - type:positive
    - phase:tool_orchestration

- criterion: "手动拼接 SQL 而未调用 TextToSearchLogQuery 工具"
  points: -10
  tags:
    - axis:accuracy
    - type:negative
    - phase:tool_orchestration
```

请严格按照 YAML 列表格式输出，不要添加额外说明文字。"""
    
    return prompt


def save_judge_result(agent_name: str, case_idx: int, rubrics: List[Dict[str, Any]]) -> str:
    """保存 Judge 结果到临时文件"""
    tmp_dir = project_root / "source" / agent_name / "tmp" / "judges"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = tmp_dir / f"judge_case_{case_idx}.yaml"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(rubrics, f, allow_unicode=True, default_flow_style=False, indent=2)
    
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description='批量生成 Judge 评分标准',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  # 生成所有用例
  ./venv/bin/python scripts/generate_judges_batch.py --agent cls-log-agent
  
  # 仅生成 case 10-20
  ./venv/bin/python scripts/generate_judges_batch.py --agent cls-log-agent --start 10 --end 20
  
  # 仅生成单条用例
  ./venv/bin/python scripts/generate_judges_batch.py --agent cls-log-agent --case 5
        '''
    )
    
    parser.add_argument('--agent', required=True, help='Agent 名称')
    parser.add_argument('--start', type=int, default=None, help='起始用例索引（包含）')
    parser.add_argument('--end', type=int, default=None, help='结束用例索引（包含）')
    parser.add_argument('--case', type=int, default=None, help='仅生成指定用例')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("批量生成 Judge 评分标准")
    print("=" * 70)
    print(f"Agent: {args.agent}")
    print(f"范围: {args.start if args.start is not None else '全部'} - {args.end if args.end is not None else '全部'}")
    print("=" * 70)
    print()
    
    # 加载测试用例
    print("1️⃣ 加载测试用例...")
    testcases = load_testcases(args.agent)
    cases = testcases.get('cases', [])
    total_cases = len(cases)
    print(f"   ✅ 共 {total_cases} 条用例\n")
    
    # 加载理想态
    print("2️⃣ 加载理想态文件...")
    ideal_state = load_ideal_state(args.agent)
    if ideal_state:
        print(f"   ✅ 已加载（{len(ideal_state)} 字符）\n")
    else:
        print("   ⚠️  未找到理想态文件，将使用通用评分维度\n")
    
    # 确定处理范围
    if args.case is not None:
        indices = [args.case]
    else:
        start = args.start if args.start is not None else 0
        end = args.end if args.end is not None else total_cases - 1
        indices = list(range(start, min(end + 1, total_cases)))
    
    print(f"3️⃣ 准备生成 {len(indices)} 条用例的 Judge...")
    print(f"   用例索引: {indices}\n")
    
    # 生成调用提示词（输出给 AI Agent 使用）
    print("4️⃣ 生成调用提示词...")
    print("   以下是各用例的调用提示词，请 AI Agent 逐个执行：\n")
    
    prompts = []
    for idx in indices:
        if idx >= len(cases):
            print(f"   ⚠️  索引 {idx} 超出范围，跳过")
            continue
        
        input_text = cases[idx].get('Input', '')
        prompt = call_meta_rubric_gen_subagent(idx, input_text, args.agent, ideal_state)
        
        prompts.append({
            'case_idx': idx,
            'prompt': prompt,
            'input_preview': input_text[:100] + ('...' if len(input_text) > 100 else '')
        })
        
        print(f"   [{idx}] Input: {prompts[-1]['input_preview']}")
    
    print(f"\n   ✅ 已生成 {len(prompts)} 条调用提示词\n")
    
    # 输出提示词到文件（供 AI Agent 读取）
    prompts_path = project_root / "source" / args.agent / "tmp" / "judge_prompts.json"
    prompts_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(prompts_path, 'w', encoding='utf-8') as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)
    
    print(f"5️⃣ 提示词已保存到: {prompts_path}")
    print()
    print("=" * 70)
    print("✅ 准备完成")
    print("=" * 70)
    print()
    print("接下来请 AI Agent 执行以下步骤：")
    print("1. 读取提示词文件: source/cls-log-agent/tmp/judge_prompts.json")
    print("2. 逐个调用 meta-rubric-gen Sub Agent（并发 5 条）")
    print("3. 将生成的 rubrics 保存到: source/cls-log-agent/tmp/judges/judge_case_N.yaml")
    print("4. 运行合并脚本: ./venv/bin/python scripts/merge_judges_to_yaml.py --agent cls-log-agent")


if __name__ == "__main__":
    main()
