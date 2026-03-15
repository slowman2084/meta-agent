#!/usr/bin/env python3
"""
应用 calibration 决策修改 testcases.yaml 中的 Judge 字段（v3）。

核心策略：对于无法被 yaml.safe_load 直接解析的 Judge 字符串，
使用正则逐条提取 rubric 条目（criterion / points / tags），
修正后统一写回为标准 YAML 块标量格式。

用法：
  ./venv/bin/python scripts/apply_calibration_fixes_v3.py source/cls-log-agent/testcases.yaml [--dry-run]
"""

import sys
import re
import yaml
import json
import os
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)


def load_yaml(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def parse_judge_yaml(judge_str):
    """方案1：直接 yaml.safe_load"""
    if not judge_str or not isinstance(judge_str, str):
        return None
    try:
        parsed = yaml.safe_load(judge_str)
        if isinstance(parsed, list) and len(parsed) > 0:
            # 验证每条都是 dict 且含 criterion
            if all(isinstance(r, dict) and 'criterion' in r for r in parsed):
                return parsed
    except Exception:
        pass
    return None


def parse_judge_regex(judge_str):
    """方案2：正则解析 — 逐条提取 criterion/points/tags

    处理 criterion 值内部含裸引号的情况（YAML 解析器会失败的原因）。
    策略：
      1. 找到 `- criterion:` 开头的行
      2. criterion 值向下延续直到遇到 `  points:` 行
      3. 提取 points 和 tags
    """
    if not judge_str or not isinstance(judge_str, str):
        return None

    lines = judge_str.split('\n')
    rubrics = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 跳过注释和空行
        if not stripped or stripped.startswith('#') or stripped.startswith('==='):
            i += 1
            continue

        # 检测 rubric 条目开始
        # 模式1: "- criterion: ..." 
        m = re.match(r'^-\s+criterion:\s*(.*)', line)
        if m:
            criterion_val = m.group(1).strip()
            i += 1

            # 去掉外层引号（如果有）
            if criterion_val.startswith('"'):
                # criterion 值可能跨多行，但这里大部分是单行
                # 找到结束引号 — 从末尾开始找
                if criterion_val.endswith('"') and len(criterion_val) > 1:
                    criterion_val = criterion_val[1:-1]
                else:
                    # 跨行 criterion（罕见），向下收集直到找到结束引号
                    while i < len(lines):
                        next_line = lines[i].strip()
                        if next_line.endswith('"'):
                            criterion_val += ' ' + next_line[:-1]
                            i += 1
                            break
                        else:
                            criterion_val += ' ' + next_line
                            i += 1
            elif criterion_val.startswith("'") and criterion_val.endswith("'"):
                criterion_val = criterion_val[1:-1]

            # 处理 criterion 内部残留的转义
            criterion_val = criterion_val.replace('\\"', '"')
            criterion_val = criterion_val.replace("\\'", "'")

            # 提取 points
            points = 0
            if i < len(lines):
                pm = re.match(r'^\s+points:\s*(-?\d+)', lines[i])
                if pm:
                    points = int(pm.group(1))
                    i += 1

            # 提取 tags
            tags = []
            if i < len(lines) and re.match(r'^\s+tags:', lines[i]):
                i += 1
                while i < len(lines):
                    tm = re.match(r'^\s+-\s+([\w:]+)', lines[i])
                    if tm:
                        tags.append(tm.group(1))
                        i += 1
                    else:
                        break

            rubrics.append({
                'criterion': criterion_val,
                'points': points,
                'tags': tags
            })
            continue

        i += 1

    return rubrics if rubrics else None


def parse_judge(judge_str):
    """统一解析入口：先试 YAML，再试正则"""
    result = parse_judge_yaml(judge_str)
    if result:
        return result, 'yaml_list'

    result = parse_judge_regex(judge_str)
    if result:
        return result, 'regex'

    return None, 'failed'


def serialize_judge(rubrics):
    """将 rubric 列表序列化为标准 YAML 块标量"""
    return yaml.dump(
        rubrics,
        allow_unicode=True,
        default_flow_style=False,
        width=200,
        sort_keys=False
    ).strip()


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
        print("用法: ./venv/bin/python scripts/apply_calibration_fixes_v3.py <testcases.yaml> [--dry-run]")
        sys.exit(1)

    yaml_path = sys.argv[1]
    dry_run = '--dry-run' in sys.argv

    print("=" * 70, flush=True)
    print("Calibration 修正脚本 v3（正则解析 + 格式统一）", flush=True)
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
    print("2️⃣ 逐条解析 + 修正 rubric...\n", flush=True)

    stats = {
        'dec1': 0, 'dec5a': 0, 'dec5b': 0, 'dec5c': 0, 'dec5d': 0,
        'modified': 0, 'skipped': 0,
        'fmt_yaml': 0, 'fmt_regex': 0, 'fmt_failed': 0
    }

    for idx, case in enumerate(cases):
        judge_str = case.get('Judge', '')
        rubrics, fmt = parse_judge(judge_str)

        if rubrics is None:
            stats['fmt_failed'] += 1
            stats['skipped'] += 1
            print(f"   [{idx:2d}/{total}] ❌ 解析失败，跳过 (len={len(judge_str) if judge_str else 0})", flush=True)
            continue

        if fmt == 'yaml_list':
            stats['fmt_yaml'] += 1
        else:
            stats['fmt_regex'] += 1

        case_modified = False
        fix_log = []

        for criterion in rubrics:
            if fix_dec1_tsq(criterion):
                stats['dec1'] += 1
                case_modified = True
                fix_log.append('DEC1')
            if fix_dec5a_insight(criterion):
                stats['dec5a'] += 1
                case_modified = True
                fix_log.append('DEC5a')
            if fix_dec5b_uuid(criterion):
                stats['dec5b'] += 1
                case_modified = True
                fix_log.append('DEC5b')
            if fix_dec5d_time(criterion):
                stats['dec5d'] += 1
                case_modified = True
                fix_log.append('DEC5d')

        if add_dec5c_empty(rubrics):
            stats['dec5c'] += 1
            case_modified = True
            fix_log.append('DEC5c')

        if case_modified or fmt == 'regex':
            # 统一写回标准 YAML 块标量格式（即使没有修正内容，也把 regex 格式统一化）
            case['Judge'] = serialize_judge(rubrics)
            stats['modified'] += 1
            fixes_str = ','.join(fix_log) if fix_log else '格式统一'
            print(f"   [{idx:2d}/{total}] ✅ 已修正 ({fmt}) [{fixes_str}]", flush=True)
        else:
            print(f"   [{idx:2d}/{total}] ⏭️  无需修改 ({fmt})", flush=True)

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
    print(f"  格式 yaml_list: {stats['fmt_yaml']}", flush=True)
    print(f"  格式 regex:     {stats['fmt_regex']}", flush=True)
    print(f"  格式 failed:    {stats['fmt_failed']}", flush=True)
    print(f"  ──────────────────────────", flush=True)
    print(f"  DEC1  TSQ 限定:      {stats['dec1']} 处", flush=True)
    print(f"  DEC5a 洞察统一:      {stats['dec5a']} 处", flush=True)
    print(f"  DEC5b UUID 扣分:     {stats['dec5b']} 处", flush=True)
    print(f"  DEC5c 空结果新增:    {stats['dec5c']} 处", flush=True)
    print(f"  DEC5d 手算时间:      {stats['dec5d']} 处", flush=True)
    print("=" * 70, flush=True)

    if stats['fmt_failed'] > 0:
        print(f"⚠️  有 {stats['fmt_failed']} 条用例解析失败，请手动检查", flush=True)
    else:
        print("✅ 全部用例处理完成！", flush=True)


if __name__ == "__main__":
    main()
