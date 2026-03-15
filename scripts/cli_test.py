#!/usr/bin/env python3
"""
CLI 批量测试脚本 — 通过 CodeBuddy CLI 调用 Agent 并捕获 JSON transcript

用法:
    ./venv/bin/python scripts/cli_test.py <agent_name>
    ./venv/bin/python scripts/cli_test.py <agent_name> --session my_test
    ./venv/bin/python scripts/cli_test.py <agent_name> --model glm-5.0-ioa
    ./venv/bin/python scripts/cli_test.py <agent_name> --cases 3 --timeout 300
    ./venv/bin/python scripts/cli_test.py <agent_name> --cli claude

流程:
    1. 自动检测 CLI 后端 (codebuddy / claude-internal)
    2. 读取 source/[agent]/testcases.yaml (或 .csv)
    3. 逐条调用 CLI (--output-format json), 捕获完整输出
    4. 保存 transcript + actual_output + input
    5. 输出测试摘要
"""

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(PROJECT_ROOT, "source")


def detect_cli_backend(force_cli: str = "") -> str:
    """自动检测 CLI 后端: codebuddy 或 claude-internal."""
    if force_cli:
        if force_cli in ("codebuddy", "claude"):
            return force_cli
        print(f"❌ 不支持的 CLI 后端: {force_cli}  (可选: codebuddy, claude)", flush=True)
        sys.exit(1)

    bundle_id = os.environ.get("__CFBundleIdentifier", "")
    if bundle_id == "com.tencent.codebuddycn":
        print("🔍 检测到 CodeBuddy IDE 环境", flush=True)
        return "codebuddy"

    for cli_name, backend in [("codebuddy", "codebuddy"), ("claude-internal", "claude")]:
        try:
            subprocess.run(["which", cli_name], capture_output=True, check=True)
            print(f"🔍 检测到 {cli_name} CLI", flush=True)
            return backend
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    print("❌ 未找到 codebuddy 或 claude-internal CLI", flush=True)
    sys.exit(1)


def read_testcases(agent_dir: str) -> list[dict]:
    """读取测试用例, 优先 YAML 回退 CSV."""
    yaml_path = os.path.join(agent_dir, "testcases.yaml")
    csv_path = os.path.join(agent_dir, "testcases.csv")

    if os.path.exists(yaml_path):
        try:
            import yaml
        except ImportError:
            print("❌ 缺少 PyYAML: ./venv/bin/pip install pyyaml", flush=True)
            sys.exit(1)
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or "cases" not in data:
            print(f"❌ YAML 格式错误: 缺少 'cases'", flush=True)
            sys.exit(1)
        cases = data["cases"]
        print(f"   📄 YAML 用例: {len(cases)} 条", flush=True)
        return cases
    elif os.path.exists(csv_path):
        cases = []
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                cases.append(dict(row))
        print(f"   📄 CSV 用例: {len(cases)} 条", flush=True)
        return cases
    else:
        print(f"❌ 找不到 testcases.yaml 或 testcases.csv", flush=True)
        sys.exit(1)


def build_cli_command(
    backend: str, agent_name: str, agent_dir: str,
    model: Optional[str], max_turns: int, output_format: str,
) -> list[str]:
    """构建 CLI 命令 (input 通过 stdin 传入)."""
    prompt_file = os.path.join(agent_dir, "prompt.md")
    mcp_config = os.path.join(agent_dir, ".mcp.json")

    if not os.path.exists(prompt_file):
        print(f"❌ 找不到: {prompt_file}", flush=True)
        sys.exit(1)

    if backend == "codebuddy":
        cmd = [
            "codebuddy", "-p",
            "--system-prompt-file", prompt_file,
            "--output-format", output_format,
            "--dangerously-skip-permissions",
            "--max-turns", str(max_turns),
        ]
    else:  # claude
        cmd = [
            "claude-internal", "-p",
            "--agent", agent_name,
            "--output-format", output_format,
            "--dangerously-skip-permissions",
            "--max-turns", str(max_turns),
        ]

    # MCP 配置
    if os.path.exists(mcp_config):
        try:
            with open(mcp_config, "r", encoding="utf-8") as f:
                mcp_data = json.load(f)
            if mcp_data.get("mcpServers"):
                cmd.extend(["--mcp-config", mcp_config])
                servers = list(mcp_data["mcpServers"].keys())
                print(f"   🔌 MCP: {servers}", flush=True)
        except json.JSONDecodeError:
            print(f"   ⚠️  MCP JSON 解析失败, 跳过", flush=True)

    if model:
        cmd.extend(["--model", model])

    return cmd


def extract_from_json_output(stdout: str) -> tuple[str, list[dict]]:
    """从 --output-format json 输出中提取 actual_output 和 transcript."""
    stdout = stdout.strip()
    if not stdout:
        return ("(empty output)", [])

    # 单个 JSON 对象 (--output-format json)
    try:
        data = json.loads(stdout)
        if isinstance(data, dict):
            result_text = data.get("result", "")
            if not result_text:
                msg = data.get("message", "")
                if isinstance(msg, str):
                    result_text = msg
                elif isinstance(msg, dict):
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        result_text = "\n".join(
                            c.get("text", "") for c in content
                            if isinstance(c, dict) and c.get("type") == "text"
                        )
                    elif isinstance(content, str):
                        result_text = content
            return (result_text or "(no result field)", [data])
    except json.JSONDecodeError:
        pass

    # 多行 JSON (stream-json)
    entries = []
    last_text = ""
    for line in stdout.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            entries.append(obj)
            if obj.get("type") == "result":
                last_text = obj.get("result", last_text)
        except json.JSONDecodeError:
            continue

    if entries:
        return (last_text or "(parsed, no result)", entries)

    # 纯文本回退
    lines = [l for l in stdout.strip().split("\n") if l.strip()]
    return ("\n".join(lines[-30:]) if lines else "(no output)", [])


def run_single_case(
    cmd_base: list[str], query: str, case_dir: str,
    timeout: int, case_idx: int,
) -> dict[str, Any]:
    """执行单条用例, 保存所有产物."""
    os.makedirs(case_dir, exist_ok=True)
    prefix = f"case_{case_idx}"

    with open(os.path.join(case_dir, f"{prefix}_input.txt"), "w", encoding="utf-8") as f:
        f.write(query)

    start = time.time()
    try:
        result = subprocess.run(
            cmd_base, input=query,
            capture_output=True, text=True,
            timeout=timeout, cwd=PROJECT_ROOT,
            env={**os.environ, "NO_COLOR": "1"},
        )
        elapsed = time.time() - start
        stdout = result.stdout or ""
        stderr = result.stderr or ""

        with open(os.path.join(case_dir, f"{prefix}_cli_output.json"), "w", encoding="utf-8") as f:
            f.write(stdout)
        if stderr.strip():
            with open(os.path.join(case_dir, f"{prefix}_stderr.txt"), "w", encoding="utf-8") as f:
                f.write(stderr)

        actual_output, transcript = extract_from_json_output(stdout)

        with open(os.path.join(case_dir, f"{prefix}_actual_output.txt"), "w", encoding="utf-8") as f:
            f.write(actual_output)

        has_transcript = False
        if transcript:
            with open(os.path.join(case_dir, f"{prefix}_transcript.jsonl"), "w", encoding="utf-8") as f:
                for entry in transcript:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            has_transcript = True

        return {
            "success": result.returncode == 0 and len(actual_output) > 10,
            "actual_output": actual_output,
            "elapsed": elapsed,
            "exit_code": result.returncode,
            "has_transcript": has_transcript,
        }
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        with open(os.path.join(case_dir, f"{prefix}_actual_output.txt"), "w", encoding="utf-8") as f:
            f.write(f"(timeout after {timeout}s)")
        return {"success": False, "actual_output": f"(timeout after {timeout}s)",
                "elapsed": elapsed, "exit_code": -1, "has_transcript": False}
    except Exception as e:
        elapsed = time.time() - start
        with open(os.path.join(case_dir, f"{prefix}_actual_output.txt"), "w", encoding="utf-8") as f:
            f.write(f"(error: {e})")
        return {"success": False, "actual_output": f"(error: {str(e)[:200]})",
                "elapsed": elapsed, "exit_code": -2, "has_transcript": False}


def generate_summary(
    agent_name: str, session: str, backend: str,
    model: Optional[str], results: list[dict], cases: list[dict],
    output_dir: str,
) -> None:
    """生成 summary.md 报告."""
    path = os.path.join(output_dir, "summary.md")
    ok = sum(1 for r in results if r["success"])
    total = len(results)
    avg_t = sum(r["elapsed"] for r in results) / total if total else 0
    tc = sum(1 for r in results if r["has_transcript"])

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# CLI Test Report\n\n")
        f.write(f"- **Agent**: {agent_name}\n")
        f.write(f"- **CLI**: {backend}\n")
        f.write(f"- **Model**: {model or '(default)'}\n")
        f.write(f"- **Session**: {session}\n")
        f.write(f"- **Time**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **成功率**: {ok}/{total}\n")
        f.write(f"- **平均耗时**: {avg_t:.1f}s\n")
        f.write(f"- **Transcript**: {tc}/{total}\n\n")
        f.write(f"| # | Input (前40字) | 状态 | 耗时 | Transcript |\n")
        f.write(f"|---|---|---|---|---|\n")
        for i, (r, c) in enumerate(zip(results, cases)):
            inp = c.get("Input", "")[:40].replace("\n", " ").replace("|", "\\|")
            st = "✅" if r["success"] else "❌"
            f.write(f"| {i} | {inp} | {st} | {r['elapsed']:.1f}s | {'📝' if r['has_transcript'] else '—'} |\n")

    print(f"   📊 摘要: {path}", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="CLI 批量测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  ./venv/bin/python scripts/cli_test.py cls-log-agent
  ./venv/bin/python scripts/cli_test.py cls-log-agent --model glm-5.0-ioa --session iter_1
  ./venv/bin/python scripts/cli_test.py cls-log-agent --cases 3
  ./venv/bin/python scripts/cli_test.py cls-log-agent --cli claude
  ./venv/bin/python scripts/cli_test.py cls-log-agent --output-format stream-json
        """,
    )
    parser.add_argument("agent", help="Agent 名称 (如 cls-log-agent)")
    parser.add_argument("--session", default=None, help="Session ID (默认: 自动时间戳)")
    parser.add_argument("--timeout", type=int, default=300, help="单条超时秒数 (默认 300)")
    parser.add_argument("--cases", type=int, default=0, help="只测前 N 条 (默认: 全部)")
    parser.add_argument("--cli", default="", help="强制 CLI: codebuddy / claude")
    parser.add_argument("--model", default=None, help="指定模型")
    parser.add_argument("--max-turns", type=int, default=30, help="最大轮次 (默认 30)")
    parser.add_argument("--output-format", default="json",
                        choices=["json", "stream-json", "text"],
                        help="CLI 输出格式 (默认 json)")
    parser.add_argument("--dry-run", action="store_true", help="只显示命令不执行")
    args = parser.parse_args()

    agent_name = args.agent
    agent_dir = os.path.join(SOURCE_DIR, agent_name)
    if not os.path.isdir(agent_dir):
        print(f"❌ 目录不存在: source/{agent_name}/", flush=True)
        sys.exit(1)

    print("=" * 70, flush=True)
    print("CLI 批量测试", flush=True)
    print("=" * 70, flush=True)

    # 1️⃣ 检测 CLI
    print("\n1️⃣ 环境检测...", flush=True)
    backend = detect_cli_backend(args.cli)

    # 2️⃣ 读取用例
    print("\n2️⃣ 读取测试用例...", flush=True)
    cases = read_testcases(agent_dir)
    if args.cases > 0:
        cases = cases[: args.cases]
        print(f"   ✂️  截取前 {args.cases} 条", flush=True)

    # 3️⃣ 构建命令
    print("\n3️⃣ 构建 CLI 命令...", flush=True)
    cmd_base = build_cli_command(
        backend, agent_name, agent_dir,
        args.model, args.max_turns, args.output_format,
    )
    print(f"   命令: {' '.join(cmd_base)}", flush=True)

    if args.dry_run:
        print("\n🏁 [DRY-RUN] 以上为将执行的命令, 退出", flush=True)
        return 0

    # 4️⃣ 准备输出目录
    session = args.session or time.strftime("cli_%Y%m%d_%H%M%S")
    output_dir = os.path.join(agent_dir, "tmp", session)
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n   📂 输出: source/{agent_name}/tmp/{session}/", flush=True)

    # 5️⃣ 逐条执行
    print(f"\n4️⃣ 开始测试 ({len(cases)} 条用例)...\n", flush=True)
    results = []
    for i, case in enumerate(cases):
        query = case.get("Input", "").strip()
        if not query:
            print(f"   ⚠️  用例 {i}: Input 为空, 跳过", flush=True)
            results.append({"success": False, "actual_output": "(empty input)",
                            "elapsed": 0, "exit_code": -3, "has_transcript": False})
            continue

        print(f"   ▶ [{i}/{len(cases)-1}] {query[:60]}...", flush=True)
        r = run_single_case(cmd_base, query, output_dir, args.timeout, i)
        results.append(r)

        status = "✅" if r["success"] else "❌"
        preview = r["actual_output"][:80].replace("\n", " ")
        print(f"     {status} {r['elapsed']:.1f}s | exit={r['exit_code']} | transcript={'Y' if r['has_transcript'] else 'N'}", flush=True)
        print(f"     📝 {preview}", flush=True)
        print(flush=True)

    # 6️⃣ 汇总
    print("=" * 70, flush=True)
    ok = sum(1 for r in results if r["success"])
    print(f"5️⃣ 测试完成: {ok}/{len(results)} 成功", flush=True)

    generate_summary(agent_name, session, backend, args.model, results, cases, output_dir)

    print(f"\n   📂 所有产物: source/{agent_name}/tmp/{session}/", flush=True)
    print(f"   每条用例: case_N_input.txt / case_N_cli_output.json / case_N_actual_output.txt", flush=True)
    print("=" * 70, flush=True)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
