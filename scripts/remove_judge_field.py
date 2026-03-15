#!/usr/bin/env python3
"""
去除 testcases.yaml 中所有 Judge 字段的内容
"""

import sys
import yaml
from pathlib import Path

def remove_judge_fields(yaml_path: str):
    """读取 YAML 文件，去除所有 Judge 字段，保存回原文件"""
    
    yaml_file = Path(yaml_path)
    if not yaml_file.exists():
        print(f"❌ 文件不存在: {yaml_path}", flush=True)
        return 1
    
    print(f"📖 读取文件: {yaml_path}", flush=True)
    
    # 读取 YAML 文件
    with open(yaml_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if 'cases' not in data:
        print(f"❌ YAML 文件中没有 'cases' 字段", flush=True)
        return 1
    
    total_cases = len(data['cases'])
    print(f"📊 总用例数: {total_cases}", flush=True)
    
    # 去除所有 Judge 字段
    removed_count = 0
    for i, case in enumerate(data['cases'], 1):
        if 'Judge' in case:
            del case['Judge']
            removed_count += 1
            print(f"  [{i}/{total_cases}] 已去除 Judge 字段", flush=True)
    
    print(f"\n✅ 共去除 {removed_count} 个 Judge 字段", flush=True)
    
    # 写回文件
    print(f"\n💾 保存到: {yaml_path}", flush=True)
    with open(yaml_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=120)
    
    print(f"✅ 完成！", flush=True)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python remove_judge_field.py <testcases.yaml路径>")
        sys.exit(1)
    
    yaml_path = sys.argv[1]
    sys.exit(remove_judge_fields(yaml_path))
