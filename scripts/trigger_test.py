#!/usr/bin/env python3
"""
Skill 触发准确性测试脚本

用途：测试 Skill 的 description / trigger_keywords 是否能准确匹配用户意图
     （正向测试：应触发；反向测试：不应触发）

用法:
    ./venv/bin/python scripts/trigger_test.py <SkillName>
    ./venv/bin/python scripts/trigger_test.py <SkillName> --threshold 0.85
    ./venv/bin/python scripts/trigger_test.py <SkillName> --verbose
"""

import argparse
import json
import os
import sys

import yaml

# 启用实时输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(PROJECT_ROOT, "source", "skills")


def read_yaml(path):
    """读取 YAML 文件"""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_json(path):
    """读取 JSON 文件"""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def keyword_match(query, keywords, description):
    """基于关键词匹配判断 query 是否应触发 Skill

    简化的匹配逻辑：
    1. 检查 query 中是否包含任意 trigger_keyword（大小写不敏感）
    2. 检查 query 与 description 的语义重叠度（基于词汇共现）

    注意：这是一个基础实现。生产环境中建议用 LLM 做语义匹配。
    """
    query_lower = query.lower()

    # 1. 关键词精确匹配
    for kw in keywords:
        if kw.lower() in query_lower:
            return True, f"关键词匹配: '{kw}'"

    # 2. 简单的词汇共现匹配
    desc_words = set(description.lower().split())
    query_words = set(query_lower.split())
    overlap = desc_words & query_words
    # 去除常见停用词
    stopwords = {"的", "是", "在", "了", "和", "与", "a", "the", "is", "to", "for", "and", "or", "of", "in", "on"}
    overlap -= stopwords

    if len(overlap) >= 3:
        return True, f"词汇共现: {overlap}"

    return False, "无匹配"


def run_trigger_test(skill_name, threshold=0.9, verbose=False):
    """执行触发测试"""
    skill_dir = os.path.join(SKILLS_DIR, skill_name)

    print("=" * 70, flush=True)
    print(f"🎯 Skill 触发准确性测试: {skill_name}", flush=True)
    print("=" * 70, flush=True)
    print(flush=True)

    # ── 1. 读取 Skill 元数据 ──
    print("1️⃣  读取 Skill 元数据...", flush=True)

    skill_json = read_json(os.path.join(skill_dir, "skill.json"))
    if not skill_json:
        print(f"  ❌ 缺少 skill.json: {skill_dir}/skill.json", flush=True)
        return None

    description = skill_json.get("description", "")
    keywords = skill_json.get("trigger_keywords", [])
    print(f"  Description: {description[:80]}...", flush=True)
    print(f"  Keywords: {keywords}", flush=True)
    print(flush=True)

    # ── 2. 读取触发测试用例 ──
    print("2️⃣  读取触发测试用例...", flush=True)

    trigger_tests_path = os.path.join(skill_dir, "trigger_tests.yaml")
    tests = read_yaml(trigger_tests_path)
    if not tests:
        print(f"  ⚠️  缺少 trigger_tests.yaml: {trigger_tests_path}", flush=True)
        print(f"     请创建此文件定义正向和反向测试用例", flush=True)
        return None

    positive = tests.get("positive", [])
    negative = tests.get("negative", [])
    expected_rate = tests.get("expected_rate", threshold)

    print(f"  正向用例: {len(positive)} 条", flush=True)
    print(f"  反向用例: {len(negative)} 条", flush=True)
    print(f"  期望触发率: >= {expected_rate}", flush=True)
    print(flush=True)

    # ── 3. 执行正向测试 ──
    print("3️⃣  正向测试（应触发）...", flush=True)

    positive_hits = 0
    for i, query in enumerate(positive):
        matched, reason = keyword_match(query, keywords, description)
        status = "✅" if matched else "❌"
        positive_hits += int(matched)
        if verbose or not matched:
            print(f"  [{i+1}/{len(positive)}] {status} \"{query[:50]}\" — {reason}", flush=True)

    positive_rate = positive_hits / len(positive) if positive else 0
    print(f"\n  正向触发率: {positive_hits}/{len(positive)} = {positive_rate:.1%}", flush=True)
    print(flush=True)

    # ── 4. 执行反向测试 ──
    print("4️⃣  反向测试（不应触发）...", flush=True)

    negative_misses = 0
    for i, query in enumerate(negative):
        matched, reason = keyword_match(query, keywords, description)
        status = "✅" if not matched else "❌"
        negative_misses += int(not matched)
        if verbose or matched:
            print(f"  [{i+1}/{len(negative)}] {status} \"{query[:50]}\" — {reason}", flush=True)

    negative_rate = negative_misses / len(negative) if negative else 0
    false_positive_rate = 1 - negative_rate
    print(f"\n  反向排除率: {negative_misses}/{len(negative)} = {negative_rate:.1%}", flush=True)
    print(f"  误触发率: {false_positive_rate:.1%}", flush=True)
    print(flush=True)

    # ── 5. 汇总 ──
    overall = (positive_rate + negative_rate) / 2
    passed = positive_rate >= expected_rate and negative_rate >= expected_rate

    print("=" * 70, flush=True)
    result_emoji = "✅" if passed else "❌"
    print(f"{result_emoji} 触发测试结果: {'通过' if passed else '未通过'}", flush=True)
    print(f"   正向触发率: {positive_rate:.1%} (期望 >= {expected_rate:.0%})", flush=True)
    print(f"   反向排除率: {negative_rate:.1%} (期望 >= {expected_rate:.0%})", flush=True)
    print(f"   综合得分: {overall:.1%}", flush=True)
    print("=" * 70, flush=True)

    return {
        "skill_name": skill_name,
        "positive_rate": positive_rate,
        "negative_rate": negative_rate,
        "false_positive_rate": false_positive_rate,
        "overall": overall,
        "passed": passed,
        "details": {
            "positive_total": len(positive),
            "positive_hits": positive_hits,
            "negative_total": len(negative),
            "negative_misses": negative_misses,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="测试 Skill 的触发准确性",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 测试 pdf-markdown Skill 的触发准确性
  ./venv/bin/python scripts/trigger_test.py pdf-markdown

  # 设置更高的触发率阈值
  ./venv/bin/python scripts/trigger_test.py pdf-markdown --threshold 0.95

  # 详细输出每条用例的匹配结果
  ./venv/bin/python scripts/trigger_test.py pdf-markdown --verbose
        """,
    )
    parser.add_argument("skill_name", help="Skill 名称")
    parser.add_argument(
        "--threshold", type=float, default=0.9, help="触发率阈值（默认 0.9）"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument(
        "--output", "-o", help="将结果保存到 JSON 文件"
    )

    args = parser.parse_args()

    result = run_trigger_test(args.skill_name, threshold=args.threshold, verbose=args.verbose)

    if result is None:
        return 1

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n📄 结果已保存: {args.output}", flush=True)

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
