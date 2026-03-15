#!/usr/bin/env python3
"""
将 testcases.yaml 中 Judge 字段的 JSON 字符串转换为 YAML 原生列表结构。

⚠️ 历史修补工具（一次性）：
    早期总控编排在将 meta-rubric-gen 输出的 rubrics 写入 testcases.yaml 时，
    错误地将 Python list 先 json.dumps() 序列化为字符串再塞入 Judge 字段，
    导致 YAML 中 Judge 的值是被引号包裹的 JSON 字符串而非原生列表。
    
    后续流程已修正：meta-rubric-gen 输出的 rubrics 数组会直接通过 yaml.dump()
    写为 YAML 原生列表，不会再产生 JSON 字符串格式的 Judge 字段。
    
    本脚本仅用于修补已存在的历史数据，新创建的 Agent 无需使用。

用途：统一 rubrics 的存储格式，从 JSON 字符串 → YAML 原生列表
依赖：pyyaml
"""

import sys
import json
import argparse
import os
import shutil
from datetime import datetime

# 启用实时输出
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

try:
    import yaml
except ImportError:
    print("❌ 缺少 pyyaml，请安装: pip install pyyaml", flush=True)
    sys.exit(1)


# === 自定义 YAML Dumper，确保输出格式美观 ===
class CustomDumper(yaml.Dumper):
    """自定义 Dumper：
    - 字符串默认不加引号（除非必要）
    - 列表项使用 block style
    """
    pass


def str_representer(dumper, data):
    """智能选择字符串表示方式"""
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    # 检查是否需要引号
    if data and (data[0] in ('{', '[', '"', "'", '*', '&', '!', '%', '@', '`')
                 or data.startswith('- ')
                 or ': ' in data
                 or data in ('true', 'false', 'null', 'yes', 'no', 'on', 'off')
                 or data.strip() != data):
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


CustomDumper.add_representer(str, str_representer)


def convert_judge_field(testcases_path: str, dry_run: bool = False) -> bool:
    """将 testcases.yaml 中 Judge 字段的 JSON 字符串转换为 YAML 原生结构"""

    print(f"1️⃣ 读取文件: {testcases_path}", flush=True)
    
    if not os.path.exists(testcases_path):
        print(f"   ❌ 文件不存在: {testcases_path}", flush=True)
        return False

    with open(testcases_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    data = yaml.safe_load(content)
    
    if not data or 'cases' not in data:
        print("   ❌ YAML 文件格式不正确，缺少 cases 字段", flush=True)
        return False
    
    cases = data['cases']
    print(f"   ✅ 读取到 {len(cases)} 条用例\n", flush=True)

    print("2️⃣ 检查并转换 Judge 字段...", flush=True)
    converted_count = 0
    already_native_count = 0
    empty_count = 0

    for i, case in enumerate(cases):
        judge = case.get('Judge', '')
        
        if not judge:
            empty_count += 1
            continue
        
        if isinstance(judge, list):
            # 已经是 YAML 原生列表
            already_native_count += 1
            continue
        
        if isinstance(judge, str):
            # 尝试解析 JSON 字符串
            try:
                parsed = json.loads(judge)
                if isinstance(parsed, list):
                    case['Judge'] = parsed
                    converted_count += 1
                    print(f"   [#{i+1}] ✅ JSON → YAML 原生列表 ({len(parsed)} 条 rubrics)", flush=True)
                else:
                    print(f"   [#{i+1}] ⚠️ JSON 解析成功但不是数组，跳过", flush=True)
            except json.JSONDecodeError:
                print(f"   [#{i+1}] ⚠️ 不是 JSON 字符串，保持原样", flush=True)
    
    print(f"\n   📊 统计: 转换 {converted_count} 条, 已是原生格式 {already_native_count} 条, 空值 {empty_count} 条\n", flush=True)

    if converted_count == 0:
        print("   ℹ️ 没有需要转换的字段", flush=True)
        return True

    if dry_run:
        print("   🔍 Dry run 模式，不写入文件", flush=True)
        return True

    # 更新 meta.notice
    if 'meta' in data and 'notice' in data['meta']:
        old_notice = data['meta']['notice']
        if 'JSON' in old_notice:
            data['meta']['notice'] = "每条 Judge 为 YAML 原生列表，包含正向加分项和负向扣分项。总分基准约100分/case，负向项为额外扣分。"
            print(f"   ✅ 更新了 meta.notice", flush=True)

    print("3️⃣ 备份原文件...", flush=True)
    bak_dir = os.path.join(os.path.dirname(testcases_path), 'bak')
    os.makedirs(bak_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    bak_path = os.path.join(bak_dir, f"testcases_{timestamp}.bak")
    shutil.copy2(testcases_path, bak_path)
    print(f"   ✅ 备份到: {bak_path}\n", flush=True)

    print("4️⃣ 写入转换后的文件...", flush=True)
    with open(testcases_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, Dumper=CustomDumper, allow_unicode=True, 
                  default_flow_style=False, sort_keys=False, width=120)
    
    file_size_kb = os.path.getsize(testcases_path) / 1024
    print(f"   ✅ 已写入: {testcases_path}", flush=True)
    print(f"   📦 大小: {file_size_kb:.2f} KB\n", flush=True)

    return True


def main():
    parser = argparse.ArgumentParser(
        description='将 testcases.yaml 中 Judge 字段的 JSON 字符串转换为 YAML 原生结构',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  # 转换指定文件
  python scripts/convert_judge_json_to_yaml.py source/cls-log-agent/testcases.yaml
  
  # Dry run（只检查不修改）
  python scripts/convert_judge_json_to_yaml.py source/cls-log-agent/testcases.yaml --dry-run
        '''
    )
    
    parser.add_argument('file', help='testcases.yaml 文件路径')
    parser.add_argument('--dry-run', action='store_true', help='只检查不修改文件')
    
    args = parser.parse_args()
    
    print("=" * 70, flush=True)
    print("Judge JSON → YAML 原生格式转换工具", flush=True)
    print("=" * 70, flush=True)
    print(f"目标文件: {args.file}", flush=True)
    print(f"模式: {'Dry Run' if args.dry_run else '实际转换'}", flush=True)
    print("=" * 70, flush=True)
    print(flush=True)
    
    success = convert_judge_field(args.file, dry_run=args.dry_run)
    
    if success:
        print("=" * 70, flush=True)
        print("✅ 转换完成", flush=True)
        print("=" * 70, flush=True)
        return 0
    else:
        print("=" * 70, flush=True)
        print("❌ 转换失败", flush=True)
        print("=" * 70, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
