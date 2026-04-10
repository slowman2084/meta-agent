#!/usr/bin/env python3
"""
上下文恢复工具 — 自动扫描 Agent/Skill 目录生成会话上下文摘要

借鉴 gstack 的 Preamble 机制：新会话启动时自动加载最新状态、learnings、changelog。
供 iterate/test 的编排 Skill 在启动时调用，快速恢复上下文。

子命令:
  recover   生成完整上下文摘要（人类可读或 JSON）
  summary   一行状态摘要

用法:
  ./venv/bin/python scripts/context_tool.py recover source/agents/cls-log-agent
  ./venv/bin/python scripts/context_tool.py recover source/agents/cls-log-agent --json
  ./venv/bin/python scripts/context_tool.py summary source/agents/cls-log-agent
"""

import sys
import os
import argparse
import json
import re
from pathlib import Path
from datetime import datetime

# 启用实时输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

# 添加 scripts/ 到 path 以便导入 learnings_tool
SCRIPTS_DIR = Path(__file__).parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from learnings_tool import (
    _load_learnings,
    _dedup_learnings,
    _effective_confidence,
    _filter_learnings,
)


# ── 扫描函数 ────────────────────────────────────────────────────────


def _find_latest_plan(target_dir: Path) -> dict | None:
    """找到 tmp/ 下最新的 plan_*.md，解析 YAML frontmatter。"""
    tmp_dir = target_dir / "tmp"
    if not tmp_dir.is_dir():
        return None

    plans = sorted(tmp_dir.glob("plan_*.md"), reverse=True)
    if not plans:
        return None

    plan_path = plans[0]
    result = {"path": str(plan_path.relative_to(target_dir))}

    try:
        content = plan_path.read_text(encoding="utf-8")
        # 解析 YAML frontmatter（简单解析，不依赖 pyyaml）
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1]
                for line in fm_text.strip().split("\n"):
                    if ":" in line:
                        key, _, val = line.partition(":")
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key in (
                            "status", "current_phase", "current_step",
                            "current_iteration", "target_score", "max_iterations",
                            "agent_name", "platform", "model",
                        ):
                            # 尝试转换数字
                            if val.isdigit():
                                val = int(val)
                            elif val.replace(".", "").isdigit():
                                val = float(val)
                            result[key] = val
    except Exception:
        pass

    return result


def _find_baseline(target_dir: Path) -> dict | None:
    """查找 baseline_scores.json。"""
    tmp_dir = target_dir / "tmp"
    if not tmp_dir.is_dir():
        return None

    # 直接在 tmp/ 下查找
    baseline_path = tmp_dir / "baseline_scores.json"
    if not baseline_path.exists():
        # 在子目录中查找
        candidates = list(tmp_dir.glob("**/baseline_scores.json"))
        if not candidates:
            return None
        baseline_path = candidates[0]

    try:
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
        result = {"path": str(baseline_path.relative_to(target_dir))}
        if "avg" in data:
            result["avg"] = data["avg"]
        if "cases" in data and isinstance(data["cases"], dict):
            result["case_count"] = len(data["cases"])
        if "distribution" in data:
            dist = data["distribution"]
            result["distribution"] = {
                k: len(v) if isinstance(v, list) else v
                for k, v in dist.items()
            }
        return result
    except Exception:
        return None


def _find_latest_test(target_dir: Path) -> dict | None:
    """找到最近的测试结果目录，提取平均分。"""
    tmp_dir = target_dir / "tmp"
    if not tmp_dir.is_dir():
        return None

    # 查找 test_* 或 evalooper_* 目录
    test_dirs = []
    for pattern in ("test_*", "evalooper_*"):
        test_dirs.extend(
            d for d in tmp_dir.glob(pattern) if d.is_dir()
        )

    if not test_dirs:
        return None

    # 按名称排序取最新
    latest = sorted(test_dirs, key=lambda d: d.name, reverse=True)[0]
    result = {"dir": str(latest.relative_to(target_dir))}

    # 尝试读取评估报告
    report = latest / "评估报告.md"
    if report.exists():
        try:
            text = report.read_text(encoding="utf-8")
            # 提取平均分（常见格式: "平均分: 82.3" 或 "平均分 | 82.3"）
            avg_match = re.search(r"平均分[：:\s|]+(\d+\.?\d*)", text)
            if avg_match:
                result["avg_score"] = float(avg_match.group(1))
        except Exception:
            pass

    return result


def _parse_changelog_tail(target_dir: Path, n: int = 3) -> list[dict]:
    """读取 changelog.md 最后 n 个 ## [...] 段落。"""
    changelog = target_dir / "changelog.md"
    if not changelog.exists():
        return []

    try:
        content = changelog.read_text(encoding="utf-8")
    except Exception:
        return []

    # 找所有 ## 开头的段落
    sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip().startswith("## ")]

    # 取最后 n 个
    recent = sections[-n:] if len(sections) >= n else sections
    recent.reverse()  # 最新在前

    results = []
    for section in recent:
        lines = section.split("\n")
        # 去掉 ## 前缀（不能用 lstrip，它按字符集匹配）
        header = re.sub(r"^#+\s*", "", lines[0]).strip()

        # 尝试提取标签和日期
        tag_match = re.search(r"\[([^\]]+)\]", header)
        tag = tag_match.group(1) if tag_match else ""

        date_match = re.search(r"\d{4}-\d{2}-\d{2}", section)
        date = date_match.group(0) if date_match else ""

        results.append({
            "header": header,
            "tag": tag,
            "date": date,
        })

    return results


def _get_top_learnings(target_dir: Path, top_n: int = 3) -> list[dict]:
    """获取 top N learnings（已去重+衰减）。"""
    entries = _load_learnings(target_dir)
    if not entries:
        return []

    deduped = _dedup_learnings(entries)
    filtered = _filter_learnings(deduped, min_conf=1.0)
    results = filtered[:top_n]

    return [
        {
            "key": e.get("key", ""),
            "type": e.get("type", ""),
            "confidence": e.get("confidence", 0),
            "effective_confidence": _effective_confidence(e),
            "insight": e.get("insight", ""),
        }
        for e in results
    ]


# ── 子命令实现 ──────────────────────────────────────────────────────


def cmd_recover(args) -> int:
    """生成完整上下文摘要。"""
    target_dir = Path(args.target_dir)
    if not target_dir.is_dir():
        print(f"❌ 目录不存在: {target_dir}", flush=True)
        return 1

    agent_name = target_dir.name
    target_type = "skill" if "skills" in str(target_dir) else "agent"
    learnings_top = args.learnings_top

    # 收集各维度信息
    plan = _find_latest_plan(target_dir)
    baseline = _find_baseline(target_dir)
    learnings = _get_top_learnings(target_dir, learnings_top)
    changelog = _parse_changelog_tail(target_dir, 3)
    latest_test = _find_latest_test(target_dir)

    if args.json:
        output = {
            "target": agent_name,
            "target_type": target_type,
            "plan": plan,
            "baseline": baseline,
            "learnings": learnings,
            "changelog_recent": changelog,
            "latest_test": latest_test,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2), flush=True)
        return 0

    # 人类可读输出
    print(f"=== Session Context: {agent_name} ({target_type}) ===\n", flush=True)

    # Plan
    if plan:
        status = plan.get("status", "?")
        phase = plan.get("current_phase", "?")
        step = plan.get("current_step", "?")
        iteration = plan.get("current_iteration", "?")
        max_iter = plan.get("max_iterations", "?")
        target = plan.get("target_score", "?")
        print(f"[Plan] status={status}, phase={phase}, step={step}, iter={iteration}/{max_iter}, target={target}", flush=True)
        print(f"       path: {plan.get('path', '?')}", flush=True)
    else:
        print("[Plan] (无活跃计划)", flush=True)

    # Baseline
    if baseline:
        avg = baseline.get("avg", "?")
        cases = baseline.get("case_count", "?")
        dist = baseline.get("distribution", {})
        dist_str = ", ".join(f"{k}:{v}" for k, v in dist.items()) if dist else ""
        print(f"[Baseline] avg={avg}, cases={cases}{(', ' + dist_str) if dist_str else ''}", flush=True)
    else:
        print("[Baseline] (无基线数据)", flush=True)

    # Learnings
    if learnings:
        print(f"[Learnings] {len(learnings)} relevant:", flush=True)
        for i, l in enumerate(learnings, 1):
            eff = l.get("effective_confidence", l.get("confidence", 0))
            insight = l.get("insight", "")
            if len(insight) > 70:
                insight = insight[:67] + "..."
            print(f"  {i}. [{l.get('type', '?')}] {l.get('key', '?')} (conf:{eff:.0f}): {insight}", flush=True)
    else:
        print("[Learnings] (无记录)", flush=True)

    # Changelog
    if changelog:
        print(f"[Changelog] last {len(changelog)}:", flush=True)
        for entry in changelog:
            date = f" ({entry['date']})" if entry.get("date") else ""
            print(f"  - {entry.get('header', '?')}{date}", flush=True)
    else:
        print("[Changelog] (无记录)", flush=True)

    # Latest Test
    if latest_test:
        avg = latest_test.get("avg_score", "?")
        print(f"[Latest Test] {latest_test.get('dir', '?')} — avg={avg}", flush=True)
    else:
        print("[Latest Test] (无测试记录)", flush=True)

    print(flush=True)
    return 0


def cmd_summary(args) -> int:
    """一行状态摘要。"""
    target_dir = Path(args.target_dir)
    if not target_dir.is_dir():
        print(f"❌ 目录不存在: {target_dir}", flush=True)
        return 1

    agent_name = target_dir.name

    # Plan
    plan = _find_latest_plan(target_dir)
    phase = plan.get("current_phase", "?") if plan else "no-plan"
    step = plan.get("current_step", "") if plan else ""
    iteration = plan.get("current_iteration", "") if plan else ""

    phase_str = phase
    if iteration:
        phase_str += f" iter{iteration}"

    # Baseline
    baseline = _find_baseline(target_dir)
    baseline_avg = baseline.get("avg", "—") if baseline else "—"

    # Latest test
    latest = _find_latest_test(target_dir)
    latest_avg = latest.get("avg_score", "—") if latest else "—"

    # Learnings count
    entries = _load_learnings(target_dir)
    deduped = _dedup_learnings(entries)
    learnings_count = len(deduped)

    print(f"{agent_name} | {phase_str} | baseline:{baseline_avg} → latest:{latest_avg} | {learnings_count} learnings", flush=True)
    return 0


# ── Main ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="上下文恢复工具 — 自动扫描 Agent/Skill 目录生成会话上下文摘要",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 恢复上下文（人类可读）
  ./venv/bin/python scripts/context_tool.py recover source/agents/cls-log-agent

  # 恢复上下文（JSON 格式，供编排 Skill 使用）
  ./venv/bin/python scripts/context_tool.py recover source/agents/cls-log-agent --json

  # 一行摘要
  ./venv/bin/python scripts/context_tool.py summary source/agents/cls-log-agent
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ── recover ──
    p_recover = subparsers.add_parser("recover", help="生成完整上下文摘要")
    p_recover.add_argument("target_dir", help="Agent/Skill 目录路径")
    p_recover.add_argument("--json", action="store_true", help="输出 JSON 格式")
    p_recover.add_argument("--learnings-top", type=int, default=3, help="包含的 top learnings 数量 (默认 3)")

    # ── summary ──
    p_summary = subparsers.add_parser("summary", help="一行状态摘要")
    p_summary.add_argument("target_dir", help="Agent/Skill 目录路径")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    handlers = {
        "recover": cmd_recover,
        "summary": cmd_summary,
    }

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
