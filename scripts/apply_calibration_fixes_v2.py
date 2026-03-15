#!/usr/bin/env python3
"""
应用 calibration 决策修改 testcases.yaml 中的 Judge 字段（v2，支持转义字符串格式）。

用法：
  ./venv/bin/python scripts/apply_calibration_fixes_v2.py source/cls-log-agent/testcases.yaml [--dry-run]
"""

import sys
import re
import yaml
import json
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def parse_judge(judge_str):
    """解析 Judge 字符串为 rubric 列表，支持两种格式"""
    if not judge_str or not isinstance(judge_str, str):
        return None, 'empty'

    # 尝试直接 YAML 解析
    try:
        rubrics = yaml.safe_load(judge_str)
        if isinstance(rubrics, list) and len(rubrics) > 0:
            return rubrics, 'yaml_list'
    except Exception:
        pass

    # 尝试处理转义字符串格式（\n 和 \" 转义）
    try:
        # 先尝试用 JSON 解包（处理 \\n → \n, \\\" → "）
        unescaped = judge_str
        if '\\n' in judge_str:
            unescaped = judge_str.replace('\\n', '\n').replace('\\"', '"')
        
        # 再去掉注释行（# 开头），然后解析
        rubrics = yaml.safe_load(unescaped)
        if isinstance(rubrics, list) and len(rubrics) > 0:
            return rubrics, 'escaped_string'
    except Exception:
        pass

    return None, 'failed'


def serialize_judge_as_block(rubrics):
    """将 rubric 列表序列化为 YAML 块标量格式"""
    return yaml.dump(rubrics, allow_unicode=True, default_flow_style=False, width=200, sort_keys=False).strip()


# ==================== 修正函数 ====================

def fix_dec1_tsq(criterion):
    """DEC1: TextToSearchLogQuery 负向扣分项 — 仅复杂场景才扣分"""
    c = criterion.get('criterion', '')
    pts = criterion.get('points', 0)
    tags = criterion.get('tags', [])

    if pts >= 0:
        return False
    if 'type:negative' not in tags:
        return False

    # 匹配 TextToSearchLogQuery 负向项
    if 'TextToSearchLogQuery' not in c and 'texttosearchlogquery' not in c.lower():
        return False

    # 已修正
    if '窗口函数' in c or '复杂分析场景' in c:
        return False

    criterion['criterion'] = (
        "查询涉及窗口函数、多步聚合、CASE WHEN 分桶、CONCAT 拼接、正则匹配等复杂分析场景，"
        "但未调用 TextToSearchLogQuery 工具，而是自行构造复杂 SQL 后直接提交执行"
        "（简单 GROUP BY + COUNT 自行构造不在此列）"
    )
    if pts < -10:
        criterion['points'] = -10

    return True


def fix_dec5a_insight(criterion):
    """DEC5(a): 统一「下一步洞察」定义"""
    c = criterion.get('criterion', '')
    pts = criterion.get('points', 0)

    if pts <= 0:
        return False

    keywords = ['下一步洞察', '下一步行动建议', '下一步建议', '后续建议']
    if not any(kw in c for kw in keywords):
        return False

    # 已修正
    if '查询参数' in c and '泛化描述' in c:
        return False

    criterion['criterion'] = (
        "输出末尾包含至少一条可操作的下一步建议，需包含具体的查询参数"
        "（Topic 名称、时间段、字段名、过滤条件中至少一项），"
        "仅提供泛化描述（如'建议排查'、'需关注'、'建议进一步分析'）不满足要求"
    )

    return True


def fix_dec5b_uuid(criterion):
    """DEC5(b): UUID 冗余调用 -15 → -8"""
    c = criterion.get('criterion', '')
    pts = criterion.get('points', 0)
    tags = criterion.get('tags', [])

    if pts >= 0 or 'type:negative' not in tags:
        return False

    # 匹配 UUID 冗余调用
    if 'GetTopicInfoByName' not in c:
        return False
    if not any(kw in c for kw in ['冗余', 'UUID', '已显式提供', '已提供', '误判']):
        return False

    if pts == -8:
        return False

    criterion['points'] = -8
    criterion['criterion'] = (
        "调用了 GetTopicInfoByName 工具（用户已显式提供标准 UUID 格式的 TopicId，"
        "此调用属于冗余操作，降低执行效率但不影响结果正确性）"
    )

    return True


def fix_dec5d_time(criterion):
    """DEC5(d): 区分手算时间"""
    c = criterion.get('criterion', '')
    pts = criterion.get('points', 0)
    tags = criterion.get('tags', [])

    if pts >= 0 or 'type:negative' not in tags:
        return False

    time_kw = ['时间转换工具', '手动计算', '手算', '硬编码']
    ts_kw = ['时间戳', 'timestamp', '时间']

    if not (any(kw in c for kw in time_kw) and any(kw in c for kw in ts_kw)):
        return False

    # 已修正
    if '降级证据' in c:
        return False

    criterion['criterion'] = (
        "在工具调用链中无任何时间转换工具的调用记录，"
        "且推理过程中直接硬编码了预计算的时间戳数值"
        "（如无工具调用失败的降级证据），视为主动跳过时间工具"
    )

    return True


def add_dec5c_empty(rubrics):
    """DEC5(c): 添加空结果 criterion"""
    for r in rubrics:
        if '空结果' in r.get('criterion', '') and '业务含义' in r.get('criterion', ''):
            return False

    rubrics.append({
        'criterion': (
            "当检索返回空结果时，Agent 对空结果的业务含义进行了分析"
            "（如区分'该时段确实无异常事件'和'采集可能中断'），"
            "并给出至少 2 种可能原因和对应排查建议"
        ),
        'points': 8,
        'tags': ['axis:value', 'type:positive']
    })

    return True


# ==================== 主流程 ====================

def main():
    if len(sys.argv) < 2:
        print("用法: ./venv/bin/python scripts/apply_calibration_fixes_v2.py <testcases.yaml>")
        sys.exit(1)

    yaml_path = sys.argv[1]
    dry_run = '--dry-run' in sys.argv

    print("=" * 70, flush=True)
    print("Calibration 修正脚本 v2（支持转义字符串格式）", flush=True)
    print("=" * 70, flush=True)
    print(f"目标: {yaml_path}", flush=True)
    if dry_run:
        print("⚠️  DRY RUN 模式 — 不会保存修改", flush=True)
    print("=" * 70, flush=True)
    print(flush=True)

    # 1. 加载
    print("1️⃣ 加载 YAML...", flush=True)
    data = load_yaml(yaml_path)
    cases = data.get('cases', [])
    total = len(cases)
    print(f"   ✅ 共 {total} 条用例\n", flush=True)

    # 2. 逐条修正
    print("2️⃣ 逐条修正 rubric...\n", flush=True)

    stats = {
        'dec1': 0, 'dec5a': 0, 'dec5b': 0, 'dec5c': 0, 'dec5d': 0,
        'modified': 0, 'skipped': 0, 'format_yaml': 0, 'format_escaped': 0, 'format_failed': 0
    }

    for idx, case in enumerate(cases):
        judge_str = case.get('Judge', '')
        rubrics, fmt = parse_judge(judge_str)

        if rubrics is None:
            stats['format_failed'] += 1
            stats['skipped'] += 1
            print(f"   [{idx:2d}/{total}] ❌ 解析失败，跳过", flush=True)
            continue

        if fmt == 'yaml_list':
            stats['format_yaml'] += 1
        else:
            stats['format_escaped'] += 1

        case_modified = False

        for criterion in rubrics:
            if fix_dec1_tsq(criterion):
                stats['dec1'] += 1
                case_modified = True
            if fix_dec5a_insight(criterion):
                stats['dec5a'] += 1
                case_modified = True
            if fix_dec5b_uuid(criterion):
                stats['dec5b'] += 1
                case_modified = True
            if fix_dec5d_time(criterion):
                stats['dec5d'] += 1
                case_modified = True

        if add_dec5c_empty(rubrics):
            stats['dec5c'] += 1
            case_modified = True

        if case_modified:
            # 统一写回为 YAML 块标量格式
            case['Judge'] = serialize_judge_as_block(rubrics)
            stats['modified'] += 1
            print(f"   [{idx:2d}/{total}] ✅ 已修正 (格式: {fmt})", flush=True)
        else:
            print(f"   [{idx:2d}/{total}] ⏭️  无需修改 (格式: {fmt})", flush=True)

    print(f"\n   ✅ 修正完成\n", flush=True)

    # 3. 保存
    if not dry_run:
        print("3️⃣ 保存...", flush=True)
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, width=200, sort_keys=False)
        fsize = os.path.getsize(yaml_path) / 1024
        print(f"   ✅ 已保存: {yaml_path} ({fsize:.1f} KB)\n", flush=True)
    else:
        print("3️⃣ DRY RUN — 未保存\n", flush=True)

    # 4. 汇总
    print("=" * 70, flush=True)
    print("📊 修正统计", flush=True)
    print("=" * 70, flush=True)
    print(f"  用例总数:       {total}", flush=True)
    print(f"  已修改:         {stats['modified']}", flush=True)
    print(f"  跳过:           {stats['skipped']}", flush=True)
    print(f"  格式 yaml_list: {stats['format_yaml']}", flush=True)
    print(f"  格式 escaped:   {stats['format_escaped']}", flush=True)
    print(f"  格式 failed:    {stats['format_failed']}", flush=True)
    print(f"  ──────────────────────────", flush=True)
    print(f"  DEC1  TSQ 限定:      {stats['dec1']} 处", flush=True)
    print(f"  DEC5a 洞察统一:      {stats['dec5a']} 处", flush=True)
    print(f"  DEC5b UUID 扣分:     {stats['dec5b']} 处", flush=True)
    print(f"  DEC5c 空结果新增:    {stats['dec5c']} 处", flush=True)
    print(f"  DEC5d 手算时间:      {stats['dec5d']} 处", flush=True)
    print("=" * 70, flush=True)
    print("✅ 全部完成", flush=True)


if __name__ == "__main__":
    main()
