#!/usr/bin/env python3
"""
Learnings 工具 — per-agent/skill 结构化经验 JSONL 系统

借鉴 gstack 的 learnings.jsonl 设计：追加写入、读时去重+置信度衰减。
每个 Agent/Skill 目录下维护独立的 learnings.jsonl 文件。

子命令:
  log      追加一条 learning
  search   搜索/过滤（含置信度衰减 + 去重）
  count    统计 learnings 数量

用法:
  ./venv/bin/python scripts/learnings_tool.py log <target_dir> \\
      --type pitfall --key "missing-sampling-rate" \\
      --insight "Agent forgets SamplingRate when timerange > 24h" \\
      --confidence 8 --source observed

  ./venv/bin/python scripts/learnings_tool.py search <target_dir> \\
      --type pitfall --query "sampling" --top 5

  ./venv/bin/python scripts/learnings_tool.py count <target_dir>
"""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# 启用实时输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

VALID_TYPES = {"pitfall", "preference", "pattern", "optimization", "rubric-fix"}
VALID_SOURCES = {"observed", "inferred", "user-stated"}
LEARNINGS_FILE = "learnings.jsonl"
DECAY_INTERVAL_DAYS = 30  # 每 30 天衰减 1 点
NO_DECAY_SOURCES = {"user-stated"}  # 这些来源不衰减


# ── 核心函数（供 context_tool 等外部导入） ────────────────────────────


def _load_learnings(target_dir: Path) -> list[dict]:
    """读取 learnings.jsonl 的所有条目。"""
    jsonl_path = target_dir / LEARNINGS_FILE
    if not jsonl_path.exists():
        return []

    entries = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError:
                print(f"  ⚠️  第 {lineno} 行 JSON 解析失败，已跳过", flush=True)
    return entries


def _dedup_learnings(entries: list[dict]) -> list[dict]:
    """按 (key, type) 去重，保留最新条目（以 ts 为准）。

    去重在读取时执行，不修改原始文件——保持追加写入的安全性。
    """
    latest_map: dict[str, dict] = {}
    for entry in entries:
        dedup_key = f"{entry.get('key', '')}|{entry.get('type', '')}"
        existing = latest_map.get(dedup_key)
        if existing is None or entry.get("ts", "") > existing.get("ts", ""):
            latest_map[dedup_key] = entry
    return list(latest_map.values())


def _effective_confidence(entry: dict, now: Optional[datetime] = None) -> float:
    """计算有效置信度（应用时间衰减）。

    规则：
    - observed / inferred: 每 30 天置信度 -1，最低为 0
    - user-stated: 永不衰减
    """
    if now is None:
        now = datetime.now(timezone.utc)

    confidence = entry.get("confidence", 5)
    source = entry.get("source", "observed")

    if source in NO_DECAY_SOURCES:
        return float(confidence)

    ts_str = entry.get("ts", "")
    if not ts_str:
        return float(confidence)

    try:
        # 支持带时区和不带时区的 ISO 格式
        ts = datetime.fromisoformat(ts_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        now_aware = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        days = max(0, (now_aware - ts).days)
        decay = days // DECAY_INTERVAL_DAYS
        return float(max(0, confidence - decay))
    except (ValueError, TypeError):
        return float(confidence)


def _filter_learnings(
    entries: list[dict],
    type_filter: Optional[str] = None,
    query: Optional[str] = None,
    tags: Optional[list[str]] = None,
    min_conf: float = 1.0,
    now: Optional[datetime] = None,
) -> list[dict]:
    """过滤 + 排序 learnings。

    管道：去重 → 衰减 → 过滤(type/query/tags/min_conf) → 排序(有效置信度↓, ts↓)
    """
    results = []
    for entry in entries:
        eff_conf = _effective_confidence(entry, now)

        # 最低置信度过滤
        if eff_conf < min_conf:
            continue

        # 类型过滤
        if type_filter and entry.get("type") != type_filter:
            continue

        # 关键词搜索（insight 字段，大小写不敏感）
        if query and query.lower() not in entry.get("insight", "").lower():
            continue

        # 标签过滤（要求全部匹配）
        if tags:
            entry_tags = set(entry.get("tags", []))
            if not all(t in entry_tags for t in tags):
                continue

        results.append((eff_conf, entry))

    # 排序：有效置信度降序，同分按 ts 降序
    results.sort(key=lambda x: (x[0], x[1].get("ts", "")), reverse=True)
    return [entry for _, entry in results]


# ── 子命令实现 ──────────────────────────────────────────────────────


def cmd_log(args) -> int:
    """追加一条 learning 到 JSONL 文件。"""
    target_dir = Path(args.target_dir)
    if not target_dir.is_dir():
        print(f"❌ 目录不存在: {target_dir}", flush=True)
        return 1

    # 验证参数
    if args.type not in VALID_TYPES:
        print(f"❌ 无效的 type: {args.type}（可选: {', '.join(sorted(VALID_TYPES))}）", flush=True)
        return 1

    if args.source not in VALID_SOURCES:
        print(f"❌ 无效的 source: {args.source}（可选: {', '.join(sorted(VALID_SOURCES))}）", flush=True)
        return 1

    if not 1 <= args.confidence <= 10:
        print(f"❌ confidence 必须在 1-10 之间，当前: {args.confidence}", flush=True)
        return 1

    # 构建 entry
    agent_name = target_dir.name
    entry = {
        "ts": datetime.now().astimezone().isoformat(),
        "agent": agent_name,
        "type": args.type,
        "key": args.key,
        "insight": args.insight,
        "confidence": args.confidence,
        "source": args.source,
    }

    # 可选字段
    if args.skill:
        entry["skill"] = args.skill
    if args.iteration is not None:
        entry["iteration"] = args.iteration
    if args.score_delta:
        entry["score_delta"] = args.score_delta
    if args.files:
        entry["files"] = [f.strip() for f in args.files.split(",")]
    if args.tags:
        entry["tags"] = [t.strip() for t in args.tags.split(",")]

    # 追加写入
    jsonl_path = target_dir / LEARNINGS_FILE
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"✅ Logged learning: {args.key} (type={args.type}, confidence={args.confidence}, source={args.source})", flush=True)
    print(f"   → {jsonl_path}", flush=True)
    return 0


def cmd_search(args) -> int:
    """搜索 learnings（含置信度衰减 + 去重）。"""
    target_dir = Path(args.target_dir)
    if not target_dir.is_dir():
        print(f"❌ 目录不存在: {target_dir}", flush=True)
        return 1

    entries = _load_learnings(target_dir)
    if not entries:
        print(f"📭 {target_dir.name}: 无 learnings 记录", flush=True)
        return 0

    # 去重
    deduped = _dedup_learnings(entries)

    # 解析 tags
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else None

    # 过滤 + 排序
    filtered = _filter_learnings(
        deduped,
        type_filter=args.type,
        query=args.query,
        tags=tags,
        min_conf=args.min_confidence,
    )

    # 限制条数
    top_n = args.top
    results = filtered[:top_n]

    if args.json:
        # JSON 输出
        output = []
        for entry in results:
            eff = _effective_confidence(entry)
            output.append({**entry, "_effective_confidence": eff})
        print(json.dumps(output, ensure_ascii=False, indent=2), flush=True)
        return 0

    # 表格输出
    agent_name = target_dir.name
    print(f"# Learnings for {agent_name} ({len(results)} results, {len(deduped)} unique, {len(entries)} total)\n", flush=True)

    if not results:
        print("  (无匹配结果)", flush=True)
        return 0

    # 表头
    print(f" {'#':>3}  {'Type':<14} {'Key':<28} {'Conf':>10}  Insight", flush=True)
    print(f" {'─'*3}  {'─'*14} {'─'*28} {'─'*10}  {'─'*40}", flush=True)

    for i, entry in enumerate(results, 1):
        eff = _effective_confidence(entry)
        orig = entry.get("confidence", "?")
        conf_str = f"{orig}(eff:{eff:.0f})" if eff != orig else str(orig)
        insight = entry.get("insight", "")
        if len(insight) > 60:
            insight = insight[:57] + "..."
        print(f" {i:>3}  {entry.get('type', '?'):<14} {entry.get('key', '?'):<28} {conf_str:>10}  {insight}", flush=True)

    return 0


def cmd_count(args) -> int:
    """统计 learnings 数量。"""
    target_dir = Path(args.target_dir)
    if not target_dir.is_dir():
        print(f"❌ 目录不存在: {target_dir}", flush=True)
        return 1

    entries = _load_learnings(target_dir)
    deduped = _dedup_learnings(entries)

    # 按 type 统计
    type_counts: dict[str, int] = {}
    for entry in deduped:
        t = entry.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    type_summary = ", ".join(f"{t}:{c}" for t, c in sorted(type_counts.items()))

    if args.json:
        output = {
            "total_entries": len(entries),
            "unique_entries": len(deduped),
            "by_type": type_counts,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2), flush=True)
        return 0

    agent_name = target_dir.name
    print(f"{agent_name}: Total {len(entries)} entries ({len(deduped)} unique) — {type_summary or '(empty)'}", flush=True)
    return 0


# ── Main ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Learnings 工具 — per-agent/skill 结构化经验 JSONL 系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 记录一条 learning
  ./venv/bin/python scripts/learnings_tool.py log source/agents/cls-log-agent \\
      --type pitfall --key "missing-sampling-rate" \\
      --insight "Agent forgets SamplingRate when timerange > 24h" \\
      --confidence 8 --source observed

  # 搜索 learnings
  ./venv/bin/python scripts/learnings_tool.py search source/agents/cls-log-agent \\
      --type pitfall --top 5

  # 统计
  ./venv/bin/python scripts/learnings_tool.py count source/agents/cls-log-agent
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ── log ──
    p_log = subparsers.add_parser("log", help="追加一条 learning")
    p_log.add_argument("target_dir", help="Agent/Skill 目录路径 (如 source/agents/cls-log-agent)")
    p_log.add_argument("--type", required=True, choices=sorted(VALID_TYPES), help="类型")
    p_log.add_argument("--key", required=True, help="去重键 (如 missing-sampling-rate)")
    p_log.add_argument("--insight", required=True, help="经验描述")
    p_log.add_argument("--confidence", required=True, type=int, help="置信度 (1-10)")
    p_log.add_argument("--source", required=True, choices=sorted(VALID_SOURCES), help="来源")
    p_log.add_argument("--skill", default=None, help="产生此 learning 的 meta-skill 名称")
    p_log.add_argument("--iteration", type=int, default=None, help="迭代轮次")
    p_log.add_argument("--score-delta", default=None, help="分数变化 (如 +15.2)")
    p_log.add_argument("--files", default=None, help="相关文件，逗号分隔")
    p_log.add_argument("--tags", default=None, help="标签，逗号分隔")

    # ── search ──
    p_search = subparsers.add_parser("search", help="搜索 learnings（含置信度衰减 + 去重）")
    p_search.add_argument("target_dir", help="Agent/Skill 目录路径")
    p_search.add_argument("--type", default=None, choices=sorted(VALID_TYPES), help="按类型过滤")
    p_search.add_argument("--query", default=None, help="关键词搜索（insight 字段，大小写不敏感）")
    p_search.add_argument("--tags", default=None, help="按标签过滤（逗号分隔，要求全部匹配）")
    p_search.add_argument("--top", type=int, default=10, help="返回前 N 条 (默认 10)")
    p_search.add_argument("--min-confidence", type=float, default=1.0, help="最低有效置信度 (默认 1)")
    p_search.add_argument("--json", action="store_true", help="输出 JSON 格式")

    # ── count ──
    p_count = subparsers.add_parser("count", help="统计 learnings 数量")
    p_count.add_argument("target_dir", help="Agent/Skill 目录路径")
    p_count.add_argument("--json", action="store_true", help="输出 JSON 格式")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    handlers = {
        "log": cmd_log,
        "search": cmd_search,
        "count": cmd_count,
    }

    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
