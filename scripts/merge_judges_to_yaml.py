#!/usr/bin/env python3
"""
合并 Judge 结果到 YAML

功能：
1. 从 tmp/judges/ 目录读取所有 judge_case_N.yaml 文件
2. 将结果合并写入到 testcases.yaml 的对应位置

用法：
    ./venv/bin/python scripts/merge_judges_to_yaml.py --agent cls-log-agent
"""

import sys
import os
import yaml
import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 启用行缓冲（实时输出）
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)


def backup_yaml(yaml_path: Path) -> Path:
    """备份原 YAML 文件"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = yaml_path.parent / "bak" / f"testcases_{timestamp}.yaml.bak"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    
    shutil.copy2(yaml_path, backup_path)
    return backup_path


def load_judge_files(tmp_dir: Path) -> Dict[int, List[Dict[str, Any]]]:
    """加载所有 Judge 文件"""
    judges_dir = tmp_dir / "judges"
    
    if not judges_dir.exists():
        raise FileNotFoundError(f"Judge 目录不存在: {judges_dir}")
    
    judges = {}
    
    for yaml_file in sorted(judges_dir.glob("judge_case_*.yaml")):
        # 从文件名提取 case 索引
        filename = yaml_file.stem  # judge_case_N
        try:
            case_idx = int(filename.split('_')[-1])
        except ValueError:
            print(f"   ⚠️  无法解析文件名: {yaml_file.name}，跳过")
            continue
        
        with open(yaml_file, 'r', encoding='utf-8') as f:
            rubrics = yaml.safe_load(f)
        
        if isinstance(rubrics, list):
            judges[case_idx] = rubrics
            print(f"   ✅ 已加载 case {case_idx}（{len(rubrics)} 条 rubric）")
        else:
            print(f"   ⚠️  case {case_idx} 格式错误，跳过")
    
    return judges


def merge_judges_to_yaml(
    yaml_path: Path,
    judges: Dict[int, List[Dict[str, Any]]]
) -> int:
    """将 Judge 结果合并到 YAML 文件"""
    
    # 读取原 YAML
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    cases = data.get('cases', [])
    merged_count = 0
    
    # 合并
    for case_idx, rubrics in sorted(judges.items()):
        if case_idx >= len(cases):
            print(f"   ⚠️  case {case_idx} 超出范围，跳过")
            continue
        
        # 更新 Judge 字段
        cases[case_idx]['Judge'] = rubrics
        merged_count += 1
    
    # 写回
    data['cases'] = cases
    
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, indent=2, sort_keys=False)
    
    return merged_count


def main():
    parser = argparse.ArgumentParser(
        description='合并 Judge 结果到 YAML',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  ./venv/bin/python scripts/merge_judges_to_yaml.py --agent cls-log-agent
        '''
    )
    
    parser.add_argument('--agent', required=True, help='Agent 名称')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("合并 Judge 结果到 YAML")
    print("=" * 70)
    print(f"Agent: {args.agent}")
    print("=" * 70)
    print()
    
    # 路径设置
    yaml_path = project_root / "source" / args.agent / "testcases.yaml"
    tmp_dir = project_root / "source" / args.agent / "tmp"
    
    if not yaml_path.exists():
        print(f"❌ 测试用例文件不存在: {yaml_path}")
        sys.exit(1)
    
    # 加载 Judge 文件
    print("1️⃣ 加载 Judge 文件...")
    try:
        judges = load_judge_files(tmp_dir)
        print(f"   ✅ 共加载 {len(judges)} 条 Judge\n")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("   请先运行 generate_judges_batch.py 生成 Judge 文件")
        sys.exit(1)
    
    if not judges:
        print("❌ 未找到任何 Judge 文件")
        sys.exit(1)
    
    # 备份原文件
    print("2️⃣ 备份原 YAML 文件...")
    backup_path = backup_yaml(yaml_path)
    print(f"   ✅ 已备份到: {backup_path}\n")
    
    # 合并
    print("3️⃣ 合并 Judge 到 YAML...")
    merged_count = merge_judges_to_yaml(yaml_path, judges)
    print(f"   ✅ 已合并 {merged_count} 条 Judge\n")
    
    # 验证
    print("4️⃣ 验证合并结果...")
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    total_cases = len(data.get('cases', []))
    cases_with_judge = sum(1 for case in data['cases'] if case.get('Judge'))
    
    print(f"   ✅ 总用例数: {total_cases}")
    print(f"   ✅ 已有 Judge: {cases_with_judge}")
    print(f"   ✅ 完成率: {cases_with_judge / total_cases * 100:.1f}%\n")
    
    print("=" * 70)
    print("✅ 合并完成")
    print("=" * 70)
    print()
    print(f"文件路径: {yaml_path}")
    print(f"备份路径: {backup_path}")
    print()
    print("建议运行以下命令验证格式:")
    print(f"  ./venv/bin/python scripts/yaml_tool.py validate {yaml_path}")


if __name__ == "__main__":
    main()
