#!/usr/bin/env python3
"""
设置 Agent Factory 运行上下文。

在 #test_agent 或 #evalooper 启动前调用，
写入 .agent_factory_context.json 供 hook 脚本读取。

用法:
  python3 scripts/set_context.py test_agent <agent_name> [session_id]
  python3 scripts/set_context.py evalooper <agent_name> <iteration>
  python3 scripts/set_context.py clear
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def main():
    project_root = Path(__file__).resolve().parent.parent
    context_file = project_root / ".agent_factory_context.json"

    if len(sys.argv) < 2:
        print("Usage: set_context.py <mode> <agent_name> [session_id|iteration]")
        print("       set_context.py clear")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "clear":
        if context_file.exists():
            context_file.unlink()
            print("Context cleared.")
        return

    if len(sys.argv) < 3:
        print(f"Error: agent_name required for mode '{mode}'")
        sys.exit(1)

    agent_name = sys.argv[2]

    ctx = {
        "mode": mode,
        "agent_name": agent_name,
        "created_at": datetime.now().isoformat(),
    }

    if mode == "test_agent":
        session_id = sys.argv[3] if len(sys.argv) > 3 else datetime.now().strftime("%Y%m%d_%H%M%S")
        ctx["session_id"] = session_id

    elif mode == "evalooper":
        iteration = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        ctx["iteration"] = iteration

    context_file.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Context set: mode={mode}, agent={agent_name}, file={context_file}")


if __name__ == "__main__":
    main()
