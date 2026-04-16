#!/usr/bin/env python3
"""
产物清理工具 — 自动清理 tmp/ 目录下历史膨胀的测试和迭代产物
只保留最近N次有价值的执行结果，避免IDE索引卡顿和文件堆积。

用法:
  ./venv/bin/python scripts/cleanup_tool.py                      # 预览清理效果 (Dry Run)
  ./venv/bin/python scripts/cleanup_tool.py --force              # 实际执行删除
  ./venv/bin/python scripts/cleanup_tool.py source/agents/xxx    # 清理特定目标
"""

import sys
import os
import argparse
import shutil
from pathlib import Path

def _cleanup_dir(target_dir: Path, force: bool = False):
    tmp_dir = target_dir / "tmp"
    if not tmp_dir.is_dir():
        return 0, 0

    print(f"🧹 检查 {target_dir.name}...")
    
    # 获取所有的测试和迭代目录
    test_dirs = []
    for pattern in ("test_*", "evalooper_*", "iter_*"):
        test_dirs.extend(d for d in tmp_dir.glob(pattern) if d.is_dir())
        
    if not test_dirs:
        return 0, 0

    # 排序：按修改时间，最新的在前面
    test_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    
    # 策略：保留最新的 3 个测试目录
    KEEP_COUNT = 3
    to_keep = test_dirs[:KEEP_COUNT]
    to_delete = test_dirs[KEEP_COUNT:]
    
    deleted_count = 0
    reclaimed_bytes = 0
    
    for d in to_delete:
        # 计算大小
        size = sum(f.stat().st_size for f in d.glob('**/*') if f.is_file())
        reclaimed_bytes += size
        
        if force:
            shutil.rmtree(d)
            print(f"  🗑️  已删除: tmp/{d.name} ({size/1024:.1f} KB)")
        else:
            print(f"  🔍 待删除 [DRY RUN]: tmp/{d.name} ({size/1024:.1f} KB)")
            
        deleted_count += 1
        
    return deleted_count, reclaimed_bytes

def main():
    parser = argparse.ArgumentParser(description="清理历史无用产物")
    parser.add_argument("target", nargs="?", help="指定目录 (可选)", default=None)
    parser.add_argument("--force", action="store_true", help="强制执行删除 (否则为Dry Run)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    
    targets = []
    if args.target:
        targets.append(Path(args.target))
    else:
        for d in (project_root / "source" / "agents").iterdir():
            if d.is_dir() and not d.name.startswith("."):
                targets.append(d)
        for d in (project_root / "source" / "skills").iterdir():
            if d.is_dir() and not d.name.startswith("."):
                targets.append(d)
                
    total_deleted = 0
    total_bytes = 0
    
    print(f"={'='*40}")
    if not args.force:
        print("🛠️  DRY RUN 模式 (未实际删除，使用 --force 执行)")
    else:
        print("🔥 强力清扫模式")
    print(f"={'='*40}\n")
    
    for t in targets:
        dc, db = _cleanup_dir(t, args.force)
        total_deleted += dc
        total_bytes += db
        
    print(f"\n={'='*40}")
    print(f"总结: 共{'计划' if not args.force else '实际'}删除 {total_deleted} 个历史目录")
    print(f"节省空间: {total_bytes/1024/1024:.2f} MB")

if __name__ == "__main__":
    sys.exit(main())
