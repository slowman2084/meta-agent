#!/usr/bin/env python3
"""
状态索引工具 — 维护每个 Agent/Skill 的 status.json

提供快速查询单个 Agent 状态、更新字段、从磁盘产物自动同步、全局概览。

子命令:
  get      读取状态
  set      更新字段
  sync     从磁盘产物自动推断并更新状态
  summary  全局概览表

用法:
  ./venv/bin/python scripts/status_tool.py get source/agents/cls-log-agent
  ./venv/bin/python scripts/status_tool.py set source/agents/cls-log-agent phase iterate
  ./venv/bin/python scripts/status_tool.py sync source/agents/cls-log-agent
  ./venv/bin/python scripts/status_tool.py summary
"""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime

# 启用实时输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

SCRIPTS_DIR = Path(__file__).parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from learnings_tool import _load_learnings, _dedup_learnings
from context_tool import _find_latest_plan, _find_baseline, _find_latest_test

PROJECT_ROOT = SCRIPTS_DIR.parent
AGENTS_DIR = PROJECT_ROOT / "source" / "agents"
SKILLS_DIR = PROJECT_ROOT / "source" / "skills"
STATUS_FILE = "status.json"

DEFAULT_STATUS = {
    "name": "",
    "type": "agent",
    "phase": "created",
    "last_test_score": None,
    "baseline_score": None,
    "iterations_completed": 0,
    "last_activity": None,
    "active_plan": None,
    "total_learnings": 0,
}


# ── 辅助函数 ────────────────────────────────────────────────────────


def _read_status(target_dir: Path) -> dict:
    """读取 status.json，不存在则返回默认值。"""
    status_path = target_dir / STATUS_FILE
    if status_path.exists():
        try:
            return json.loads(status_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # 返回默认值
    status = dict(DEFAULT_STATUS)
    status["name"] = target_dir.name
    status["type"] = _detect_type(target_dir)
    return status


def _write_status(target_dir: Path, status: dict):
    """写入 status.json。"""
    status_path = target_dir / STATUS_FILE
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _detect_type(target_dir: Path) -> str:
    """检测目标是 agent 还是 skill。"""
    # 检查路径中是否有 source/skills/ 段落（而非简单匹配 "skills" 字串）
    parts = target_dir.resolve().parts
    for i, part in enumerate(parts):
        if part == "source" and i + 1 < len(parts) and parts[i + 1] == "skills":
            return "skill"
    return "agent"


def _parse_value(value_str: str):
    """解析命令行传入的值：数字转 int/float，null 转 None，其余为字符串。"""
    if value_str.lower() == "null" or value_str.lower() == "none":
        return None
    try:
        return int(value_str)
    except ValueError:
        pass
    try:
        return float(value_str)
    except ValueError:
        pass
    return value_str


def _sync_from_artifacts(target_dir: Path) -> dict:
    """从磁盘产物自动推断状态字段。"""
    status = _read_status(target_dir)
    status["name"] = target_dir.name
    status["type"] = _detect_type(target_dir)

    # ── Plan（复用 context_tool） ──
    plan = _find_latest_plan(target_dir)
    if plan:
        status["active_plan"] = plan.get("path")
        if "current_phase" in plan:
            status["phase"] = plan["current_phase"]
        if "current_iteration" in plan:
            try:
                status["iterations_completed"] = int(plan["current_iteration"])
            except (ValueError, TypeError):
                pass
    else:
        status["active_plan"] = None

    # ── Baseline（复用 context_tool） ──
    baseline = _find_baseline(target_dir)
    if baseline and "avg" in baseline:
        status["baseline_score"] = baseline["avg"]

    # ── Latest test score（复用 context_tool） ──
    latest = _find_latest_test(target_dir)
    if latest and "avg_score" in latest:
        status["last_test_score"] = latest["avg_score"]

    # ── Learnings count ──
    entries = _load_learnings(target_dir)
    deduped = _dedup_learnings(entries)
    status["total_learnings"] = len(deduped)

    # ── Last activity ──
    status["last_activity"] = datetime.now().astimezone().isoformat()

    return status


# ── 子命令实现 ──────────────────────────────────────────────────────


def cmd_get(args) -> int:
    """读取状态。"""
    target_dir = Path(args.target_dir)
    if not target_dir.is_dir():
        print(f"❌ 目录不存在: {target_dir}", flush=True)
        return 1

    status = _read_status(target_dir)

    if args.field:
        val = status.get(args.field)
        if val is None:
            print("null", flush=True)
        elif args.json:
            print(json.dumps(val, ensure_ascii=False), flush=True)
        else:
            print(val, flush=True)
        return 0

    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2), flush=True)
    else:
        print(f"=== Status: {status.get('name', '?')} ({status.get('type', '?')}) ===\n", flush=True)
        for key, val in status.items():
            print(f"  {key}: {val}", flush=True)
        print(flush=True)

    return 0


def cmd_set(args) -> int:
    """更新字段。"""
    target_dir = Path(args.target_dir)
    if not target_dir.is_dir():
        print(f"❌ 目录不存在: {target_dir}", flush=True)
        return 1

    status = _read_status(target_dir)
    field = args.field
    value = _parse_value(args.value)

    old_val = status.get(field)
    status[field] = value
    status["last_activity"] = datetime.now().astimezone().isoformat()

    _write_status(target_dir, status)
    print(f"✅ {target_dir.name}: {field} = {old_val} → {value}", flush=True)
    return 0


def cmd_sync(args) -> int:
    """从磁盘产物自动推断并更新状态。"""
    target_dir = Path(args.target_dir)
    if not target_dir.is_dir():
        print(f"❌ 目录不存在: {target_dir}", flush=True)
        return 1

    print(f"🔄 Syncing status for {target_dir.name}...", flush=True)
    status = _sync_from_artifacts(target_dir)
    _write_status(target_dir, status)

    print(f"✅ status.json updated:", flush=True)
    print(f"   phase={status.get('phase', '?')}", flush=True)
    print(f"   baseline={status.get('baseline_score', '—')}", flush=True)
    print(f"   last_test={status.get('last_test_score', '—')}", flush=True)
    print(f"   iterations={status.get('iterations_completed', 0)}", flush=True)
    print(f"   learnings={status.get('total_learnings', 0)}", flush=True)
    print(f"   plan={status.get('active_plan', '—')}", flush=True)
    return 0


def cmd_summary(args) -> int:
    """全局概览表。"""
    all_entries = []

    # 扫描 agents
    if AGENTS_DIR.is_dir():
        for d in sorted(AGENTS_DIR.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                status = _read_status(d)
                all_entries.append(status)

    # 扫描 skills
    if SKILLS_DIR.is_dir():
        for d in sorted(SKILLS_DIR.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                status = _read_status(d)
                all_entries.append(status)

    if not all_entries:
        print("📭 无 Agent/Skill 状态记录", flush=True)
        return 0

    if args.json:
        print(json.dumps(all_entries, ensure_ascii=False, indent=2), flush=True)
        return 0

    # 表格输出
    print("=== Agent/Skill Status Summary ===\n", flush=True)
    print(f" {'Name':<24} {'Type':<7} {'Phase':<12} {'Score':>6} {'Base':>6} {'Iters':>5} {'Learn':>5}  Last Activity", flush=True)
    print(f" {'─'*24} {'─'*7} {'─'*12} {'─'*6} {'─'*6} {'─'*5} {'─'*5}  {'─'*16}", flush=True)

    for s in all_entries:
        name = s.get("name", "?")[:24]
        stype = s.get("type", "?")[:7]
        phase = s.get("phase", "?")[:12]
        score = s.get("last_test_score")
        score_str = f"{score:.1f}" if score is not None else "—"
        base = s.get("baseline_score")
        base_str = f"{base:.1f}" if base is not None else "—"
        iters = s.get("iterations_completed", 0)
        learns = s.get("total_learnings", 0)
        activity = s.get("last_activity", "")
        if activity:
            # 只显示日期部分
            activity = activity[:10]

        print(f" {name:<24} {stype:<7} {phase:<12} {score_str:>6} {base_str:>6} {iters:>5} {learns:>5}  {activity}", flush=True)

    print(f"\n Total: {len(all_entries)} entries", flush=True)
    return 0


# ── Main ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="状态索引工具 — 维护每个 Agent/Skill 的 status.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  ./venv/bin/python scripts/status_tool.py get source/agents/cls-log-agent
  ./venv/bin/python scripts/status_tool.py set source/agents/cls-log-agent phase iterate
  ./venv/bin/python scripts/status_tool.py sync source/agents/cls-log-agent
  ./venv/bin/python scripts/status_tool.py summary
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ── get ──
    p_get = subparsers.add_parser("get", help="读取状态")
    p_get.add_argument("target_dir", help="Agent/Skill 目录路径")
    p_get.add_argument("--field", default=None, help="只读取指定字段")
    p_get.add_argument("--json", action="store_true", help="输出 JSON 格式")

    # ── set ──
    p_set = subparsers.add_parser("set", help="更新字段")
    p_set.add_argument("target_dir", help="Agent/Skill 目录路径")
    p_set.add_argument("field", help="字段名")
    p_set.add_argument("value", help="新值 (数字自动转换，null 转 None)")

    # ── sync ──
    p_sync = subparsers.add_parser("sync", help="从磁盘产物自动推断并更新状态")
    p_sync.add_argument("target_dir", help="Agent/Skill 目录路径")

    # ── summary ──
    p_summary = subparsers.add_parser("summary", help="全局概览表")
    p_summary.add_argument("--json", action="store_true", help="输出 JSON 格式")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    handlers = {
        "get": cmd_get,
        "set": cmd_set,
        "sync": cmd_sync,
        "summary": cmd_summary,
    }

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
